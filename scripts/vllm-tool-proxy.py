#!/usr/bin/env python3
"""
Android Framework — vLLM Tool Call Proxy (v4)

Bridges OpenClaw with local vLLM instances by handling three incompatibilities:

1. OpenClaw always requests streaming (stream: true), but tool call extraction
   requires seeing the full response. The proxy forces non-streaming when tools
   are present, extracts tool calls, then re-wraps the response as SSE.

2. Some models output tool calls as text (in <tools> tags, bare JSON, or
   multi-line JSON) instead of OpenAI's structured tool_calls format. The proxy
   detects and converts these automatically.

3. vLLM returns extra fields that OpenClaw doesn't expect. The proxy strips
   them for clean OpenAI-compatible responses.

Safety: Aborts after MAX_TOOL_CALLS to prevent runaway loops.

Usage:
    python3 vllm-tool-proxy.py --port 8003 --vllm-url http://localhost:8000

Point your openclaw.json baseUrl to this proxy (e.g., http://localhost:8003/v1),
NOT directly to vLLM.

Changelog:
    v4 — SSE re-wrapping, response cleaning, loop protection, multi-line JSON
    v3 — Bare JSON extraction
    v2 — <tools> tag extraction
    v1 — Initial proxy
"""
import argparse
import json
import logging
import os
import re
import uuid
from flask import Flask, request, Response
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration via environment variables or CLI args
VLLM_URL = os.environ.get('VLLM_URL', 'http://localhost:8000')

# Max tool calls per conversation — safety net for infinite loops.
# Counts tool result messages; aborts if exceeded.
MAX_TOOL_CALLS = int(os.environ.get('MAX_TOOL_CALLS', '500'))

TOOLS_REGEX = re.compile(r'<tools>(.*?)</tools>', re.DOTALL)


def has_tools(body):
    """Check if the request includes tool definitions."""
    return body and body.get('tools')


def count_tool_results(messages):
    """Count tool result messages in the conversation history."""
    if not messages:
        return 0
    count = 0
    for msg in messages:
        role = msg.get('role', '')
        if role == 'tool' or msg.get('tool_call_id'):
            count += 1
    return count


def check_tool_loop(body):
    """Check if we've hit the max tool calls limit.
    Returns error response dict if limit exceeded, None otherwise."""
    messages = body.get('messages', [])
    tool_count = count_tool_results(messages)

    if tool_count >= MAX_TOOL_CALLS:
        logger.warning(f'Tool call limit exceeded: {tool_count} >= {MAX_TOOL_CALLS}')
        return {
            'id': 'chatcmpl-loop-abort',
            'object': 'chat.completion',
            'created': 0,
            'model': body.get('model', 'unknown'),
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': f'Tool call safety limit reached ({tool_count} calls). '
                               f'The conversation may be stuck in a loop. '
                               f'Try simplifying your request or starting a new session.'
                },
                'finish_reason': 'stop'
            }]
        }
    return None


def parse_single_tool_call(text):
    """Try to parse a single tool call from text. Returns dict or None."""
    text = text.strip()
    if not text:
        return None
    try:
        call = json.loads(text)
        if isinstance(call, dict) and 'name' in call:
            args = call.get('arguments', {})
            if isinstance(args, dict):
                args = json.dumps(args)
            return {
                'id': f'chatcmpl-tool-{uuid.uuid4().hex[:16]}',
                'type': 'function',
                'function': {'name': call['name'], 'arguments': args}
            }
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def clean_response_for_openclaw(resp_json):
    """Strip vLLM-specific fields for clean OpenAI-compatible output.

    vLLM returns extra fields (prompt_logprobs, reasoning_content, etc.)
    that OpenClaw's OpenAI SDK layer doesn't expect. Leaving them in
    can cause parse errors or confusing behavior.
    """
    try:
        # Clean top-level vLLM-specific fields
        for field in ["prompt_logprobs", "prompt_token_ids", "kv_transfer_params",
                       "service_tier", "system_fingerprint"]:
            resp_json.pop(field, None)

        for choice in resp_json.get("choices", []):
            # Clean choice-level fields
            for field in ["stop_reason", "token_ids"]:
                choice.pop(field, None)

            msg = choice.get("message", {})
            # Remove fields OpenClaw doesn't expect
            for field in ["reasoning", "reasoning_content", "refusal",
                          "annotations", "audio", "function_call"]:
                msg.pop(field, None)
            # Ensure tool_calls is absent (not empty list) when no tools
            if not msg.get("tool_calls"):
                msg.pop("tool_calls", None)

        # Clean usage fields
        usage = resp_json.get("usage", {})
        if usage:
            usage.pop("prompt_tokens_details", None)
    except Exception as e:
        logger.error(f"Error cleaning response: {e}")


def extract_tools_from_content(response_json):
    """Post-process: if tool_calls is empty but content has tool JSON, extract it.

    Handles three formats models use to output tool calls as text:
    1. <tools>{"name": "...", "arguments": {...}}</tools>
    2. Bare JSON: {"name": "...", "arguments": {...}}
    3. Multi-line JSON: one tool call per line
    """
    try:
        choices = response_json.get('choices', [])
        for choice in choices:
            msg = choice.get('message', {})
            content = msg.get('content', '') or ''
            tool_calls = msg.get('tool_calls') or []

            if tool_calls or not content.strip():
                continue

            extracted_calls = []

            # Strategy 1: <tools> tag extraction
            matches = TOOLS_REGEX.findall(content)
            if matches:
                for match in matches:
                    for line in match.strip().split('\n'):
                        call = parse_single_tool_call(line)
                        if call:
                            extracted_calls.append(call)

            # Strategy 2: Bare JSON (entire content is one tool call)
            if not extracted_calls:
                stripped = content.strip()
                call = parse_single_tool_call(stripped)
                if call:
                    extracted_calls.append(call)

            # Strategy 3: Multi-line JSON (one tool call per line)
            if not extracted_calls:
                lines = content.strip().split('\n')
                for line in lines:
                    call = parse_single_tool_call(line)
                    if call:
                        extracted_calls.append(call)

            if extracted_calls:
                logger.info(f'Extracted {len(extracted_calls)} tool call(s) from content')
                # Clean the content — remove extracted JSON
                cleaned = TOOLS_REGEX.sub('', content).strip()
                remaining_lines = []
                for line in cleaned.split('\n'):
                    if not parse_single_tool_call(line):
                        remaining_lines.append(line)
                cleaned = '\n'.join(remaining_lines).strip()

                msg['content'] = cleaned if cleaned else None
                msg['tool_calls'] = extracted_calls
                choice['finish_reason'] = 'tool_calls'
    except Exception as e:
        logger.error(f'Error in post-processing: {e}')


def convert_to_sse_stream(resp_json):
    """Convert a non-streaming chat completion response to SSE format.

    This is the key fix: OpenClaw always sends stream:true (hardcoded).
    We force non-streaming to vLLM for tool extraction, then convert
    the JSON response back to SSE chunks that the OpenAI SDK expects.
    """
    import time

    def generate():
        model = resp_json.get("model", "unknown")
        resp_id = resp_json.get("id", "chatcmpl-converted")
        created = resp_json.get("created", int(time.time()))

        for choice in resp_json.get("choices", []):
            msg = choice.get("message", {})
            content_text = msg.get("content")
            tool_calls = msg.get("tool_calls")
            finish_reason = choice.get("finish_reason", "stop")

            # First chunk: role
            first_chunk = {
                "id": resp_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "logprobs": None,
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(first_chunk)}\n\n"

            # Content chunks
            if content_text:
                content_chunk = {
                    "id": resp_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": content_text},
                        "logprobs": None,
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(content_chunk)}\n\n"

            # Tool call chunks
            if tool_calls:
                for i, tc in enumerate(tool_calls):
                    tc_chunk = {
                        "id": resp_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "tool_calls": [{
                                    "index": i,
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": tc["function"]["name"],
                                        "arguments": tc["function"]["arguments"]
                                    }
                                }]
                            },
                            "logprobs": None,
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(tc_chunk)}\n\n"

            # Finish chunk
            finish_chunk = {
                "id": resp_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "logprobs": None,
                    "finish_reason": finish_reason
                }]
            }
            yield f"data: {json.dumps(finish_chunk)}\n\n"

        # Usage chunk
        usage = resp_json.get("usage")
        if usage:
            usage_chunk = {
                "id": resp_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [],
                "usage": usage
            }
            yield f"data: {json.dumps(usage_chunk)}\n\n"

        yield "data: [DONE]\n\n"

    return generate()


# ═══════════════════════════════════════════════════════════════
# Request Handlers
# ═══════════════════════════════════════════════════════════════

@app.route('/v1/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy(path):
    url = f'{VLLM_URL}/v1/{path}'

    if request.method == 'OPTIONS':
        return Response('', status=204)

    if path not in ('chat/completions', 'responses'):
        return forward_request(url)

    try:
        body = request.get_json()
    except Exception:
        body = None

    # Check for tool call loop
    if body and has_tools(body):
        loop_response = check_tool_loop(body)
        if loop_response:
            return Response(json.dumps(loop_response), status=200, mimetype='application/json')

    # Track if client originally requested streaming
    was_streaming = body.get("stream", False) if body else False

    # Force non-streaming when tools are present so we can extract tool calls
    if body and has_tools(body) and was_streaming:
        logger.info("Forcing non-streaming for tool call post-processing (will re-wrap as SSE)")
        body["stream"] = False
        body.pop("stream_options", None)

    is_streaming = body.get("stream", False) if body else False

    # Always strip stream_options when stream is false (vLLM 0.14+ rejects this combo)
    if body and not body.get("stream", False) and "stream_options" in body:
        logger.info("Stripping stream_options from non-streaming request")
        body.pop("stream_options", None)

    headers = {k: v for k, v in request.headers if k.lower() not in ('host', 'content-length')}

    if is_streaming:
        return stream_response(url, headers, body)
    elif was_streaming and body and has_tools(body):
        # Client wanted streaming but we forced non-streaming for tool extraction.
        # Get the response, fix it, then re-wrap as SSE.
        return forward_fix_and_rewrap_sse(url, headers, body)
    else:
        return forward_with_body_and_fix(url, headers, body)


def forward_fix_and_rewrap_sse(url, headers, body):
    """Forward non-streaming, fix tool calls, then re-wrap as SSE for streaming clients."""
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=300)
        try:
            resp_json = resp.json()
            if body and has_tools(body):
                extract_tools_from_content(resp_json)
            clean_response_for_openclaw(resp_json)

            # Log summary for debugging
            choices = resp_json.get("choices") or [{}]
            msg = choices[0].get("message", {})
            logger.info(f"SSE-REWRAP: content={str(msg.get('content', ''))[:120]}, "
                        f"tool_calls={len(msg.get('tool_calls', []))}, "
                        f"finish={choices[0].get('finish_reason')}")

            return Response(
                convert_to_sse_stream(resp_json),
                status=200,
                mimetype='text/event-stream',
                headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
            )
        except Exception as e:
            logger.error(f'SSE rewrap parse error: {e}')
            return Response(resp.content, status=resp.status_code)
    except Exception as e:
        logger.error(f'SSE rewrap forward error: {e}')
        return Response(json.dumps({'error': str(e)}), status=502, mimetype='application/json')


def forward_request(url):
    """Forward non-chat requests (e.g., /v1/models) as-is."""
    headers = {k: v for k, v in request.headers if k.lower() not in ('host', 'content-length')}
    try:
        resp = requests.request(
            method=request.method, url=url, headers=headers,
            data=request.get_data(), stream=True, timeout=300
        )
        excluded = {'content-encoding', 'transfer-encoding', 'content-length'}
        resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
        return Response(resp.iter_content(chunk_size=1024), status=resp.status_code, headers=resp_headers)
    except Exception as e:
        logger.error(f'Forward error: {e}')
        return Response(json.dumps({'error': str(e)}), status=502, mimetype='application/json')


def forward_with_body_and_fix(url, headers, body):
    """Forward non-streaming requests, extract tool calls, and clean response."""
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=300)
        try:
            resp_json = resp.json()
            if body and has_tools(body):
                extract_tools_from_content(resp_json)
            clean_response_for_openclaw(resp_json)

            # Log summary for debugging
            choices = resp_json.get("choices") or [{}]
            msg = choices[0].get("message", {})
            logger.info(f"RESPONSE: content={str(msg.get('content', ''))[:120]}, "
                        f"finish={choices[0].get('finish_reason')}")

            return Response(
                json.dumps(resp_json),
                status=resp.status_code,
                mimetype='application/json'
            )
        except Exception:
            return Response(resp.content, status=resp.status_code)
    except Exception as e:
        logger.error(f'Forward error: {e}')
        return Response(json.dumps({'error': str(e)}), status=502, mimetype='application/json')


def stream_response(url, headers, body):
    """Pure streaming passthrough (no tool extraction)."""
    def generate():
        try:
            with requests.post(url, headers=headers, json=body, stream=True, timeout=300) as resp:
                for chunk in resp.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
        except Exception as e:
            logger.error(f'Stream error: {e}')
            error_data = json.dumps({"error": str(e)})
            yield f'data: {error_data}\n\n'
    return Response(generate(), mimetype='text/event-stream')


# ═══════════════════════════════════════════════════════════════
# Health & Info
# ═══════════════════════════════════════════════════════════════

@app.route('/health')
def health():
    return {'status': 'ok', 'vllm_url': VLLM_URL, 'max_tool_calls': MAX_TOOL_CALLS}


@app.route('/')
def root():
    return {
        'service': 'Android Framework — vLLM Tool Call Proxy',
        'version': 'v4',
        'vllm_url': VLLM_URL,
        'features': [
            'Extract tool calls from <tools> tags in content',
            'Extract tool calls from bare JSON in content',
            'Extract tool calls from multi-line JSON in content',
            'Force non-streaming when tools present for extraction',
            'Re-wrap non-streaming responses as SSE for OpenClaw',
            'Strip vLLM-specific fields for clean OpenAI format',
            f'Safety limit: abort after {MAX_TOOL_CALLS} tool calls'
        ]
    }


# ═══════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Android Framework — vLLM Tool Call Proxy')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PROXY_PORT', '8003')),
                        help='Port to listen on (default: 8003, env: PROXY_PORT)')
    parser.add_argument('--vllm-url', type=str, default=VLLM_URL,
                        help='vLLM base URL (default: http://localhost:8000, env: VLLM_URL)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()
    VLLM_URL = args.vllm_url
    logger.info(f'Starting Android Framework vLLM Tool Call Proxy v4')
    logger.info(f'Listening on {args.host}:{args.port} -> {VLLM_URL}')
    app.run(host=args.host, port=args.port, threaded=True)
