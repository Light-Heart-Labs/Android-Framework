# Dream Server M1 Sandbox Audit

## Bugs and Issues Found

Base path: `C:/Users/conta/OneDrive/Desktop/Lighthouse-AI/dream-server/`

---

### MODEL CONFIG MISMATCHES

- **config/openclaw/pro.json**, line 7 -- **CRITICAL** -- Model name `Qwen/Qwen2.5-32B-Instruct` (non-quantized FP16) mismatches every other config and profile that uses `Qwen/Qwen2.5-32B-Instruct-AWQ`; the pro.yml profile also specifies the non-AWQ variant but with `dtype bfloat16` and no `--quantization` flag, yet the context window is set to 32768 in the JSON while litellm config says 8192 for the same model. Fix: decide on one model ID per tier and make openclaw JSON `contextWindow` match the vLLM `--max-model-len`.

- **config/openclaw/openclaw-offline.json**, line 27 -- **MODERATE** -- `contextWindow` is set to 4096, but the vLLM profile for prosumer (which runs the same AWQ model) uses `--max-model-len 16384`, and the litellm offline config says `max_tokens: 8192`. This inconsistency means OpenClaw will reject requests that vLLM could actually serve. Fix: align `contextWindow` to the actual vLLM `--max-model-len` value.

- **config/openclaw/entry.json**, line 15 -- **MODERATE** -- Entry tier configures `contextWindow: 8192` but entry.yml profile sets `--max-model-len 16384`. The agent config is unnecessarily restrictive. Fix: set `contextWindow` to 16384 to match the profile.

- **config/litellm/config.yaml**, line 12 -- **MODERATE** -- `max_tokens: 8192` for `local-qwen` is ambiguous (litellm uses this as max output tokens, not context length), while the actual vLLM `--max-model-len` varies by tier profile (8192 to 32768). Fix: clarify this is `max_output_tokens` or remove it and let vLLM enforce limits.

---

### vLLM CONFIG / VRAM ALLOCATION ISSUES

- **config/profiles/prosumer.yml**, line 12 -- **MODERATE** -- `gpu-memory-utilization` is 0.92, which is aggressively high for a 32B AWQ model on 28-47GB VRAM; combined with Whisper, Kokoro TTS, and embeddings also needing GPU memory, this will likely cause OOM. Fix: reduce to 0.85 or lower, or document that other GPU services should be on CPU.

- **config/profiles/entry.yml**, line 13 -- **LOW** -- `gpu-memory-utilization` at 0.90 for a 14B AWQ on 20-27GB class cards leaves minimal headroom for other GPU-resident services (Whisper, embeddings). Fix: reduce to 0.85 and add a comment about shared GPU memory.

---

### n8n WORKFLOW VALIDITY

- **workflows/05-voice-to-voice.json**, line 51 -- **CRITICAL** -- The LLM request sends `model: 'local'` but vLLM requires the exact model name (e.g., `Qwen/Qwen2.5-32B-Instruct-AWQ`); this will return a 404 or model-not-found error. Fix: use the full model name or route through the LiteLLM proxy which supports the `default` alias.

- **workflows/06-rag-demo.json**, line 128 -- **CRITICAL** -- Same issue: `model: 'local'` is sent to vLLM which does not recognize this alias. Fix: use `Qwen/Qwen2.5-32B-Instruct-AWQ` or route through the LiteLLM proxy.

- **workflows/07-code-assistant.json**, line 33 -- **CRITICAL** -- Same issue: `model: 'local'` sent directly to vLLM. Fix: use the actual model name.

- **workflows/08-m4-deterministic-voice.json**, line 68 -- **CRITICAL** -- The LLM Fallback node requests model `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` but every other config loads `Qwen/Qwen2.5-32B-Instruct-AWQ` (note: "Coder" variant is a different model). Fix: change to `Qwen/Qwen2.5-32B-Instruct-AWQ` to match the deployed model.

- **workflows/08-m4-deterministic-voice.json**, line 9 -- **MODERATE** -- Webhook Trigger uses `typeVersion: 1` (old) while all other workflows use `typeVersion: 2`; the v1 webhook lacks `responseMode` so it cannot return results to the caller. Fix: upgrade to `typeVersion: 2` and add `"responseMode": "responseNode"`.

- **workflows/08-m4-deterministic-voice.json**, line 108 -- **MODERATE** -- The Respond node uses `typeVersion: 1` while all other workflows use `typeVersion: 1.1`; additionally, the workflow has no `responseMode` on the trigger, so the Respond node will never actually send a response. Fix: upgrade both nodes and add `responseMode`.

- **workflows/08-m4-deterministic-voice.json**, line 87 -- **MODERATE** -- The `httpRequest` node uses `typeVersion: 4.1` while all other workflows use `4.2`; the older version has a different body format (`body` object vs `jsonBody` string), which may cause the request to be malformed. Fix: upgrade to `typeVersion: 4.2` with `specifyBody: "json"` and `jsonBody`.

- **workflows/05-voice-to-voice.json**, lines 7-11 -- **MODERATE** -- The Voice Input webhook lacks `responseMode: "responseNode"`, so the Return Audio respondToWebhook node at the end of the chain will silently fail to send the audio back to the caller. Fix: add `"responseMode": "responseNode"` to the webhook parameters.

- **workflows/02-document-qa.json**, lines 214-225 -- **MODERATE** -- The upload path skips the "Extract Text" node entirely; the connection goes directly from "Upload Document" to "Chunk Text", leaving the `moveBinaryData` node (id: `extract-text`) orphaned and unconnected. Fix: either wire Extract Text into the chain or remove it.

- **workflows/daily-digest.json**, lines 133-138 -- **LOW** -- The "Merge Triggers" node exists and receives input from "Manual Trigger", but it is a merge node with only one input connected (index 0); a merge node typically needs two inputs. The manual trigger path may stall waiting for a second input. Fix: remove the merge node and connect Manual Trigger directly to the RSS nodes.

---

### QDRANT CONFIG ISSUES

- **workflows/02-document-qa.json**, line 83 -- **CRITICAL** -- The Qdrant point ID is computed as `Date.now() + Math.random()` which produces a floating-point number; Qdrant requires point IDs to be either unsigned integers or UUIDs. This will cause a 400 error on every upsert. Fix: use `Math.floor(Date.now() * 1000 + Math.random() * 1000)` or generate a UUID.

- **workflows/02-document-qa.json**, line 83 -- **MODERATE** -- The embedding vector is accessed as `$json[0]`, but the TEI `/embed` endpoint returns `{ data: [{ embedding: [...] }] }` or a flat array depending on version; this expression may yield `undefined` if the response structure differs. Fix: verify the TEI response format and use the correct path (e.g., `$json.data[0].embedding` or `$json[0]`).

- **workflows/document-qa.json**, line 33 -- **MODERATE** -- The Qdrant collection is created with `vectors.size: 384` (for BGE-small), but the embedding model configured in the offline config is `BAAI/bge-base-en-v1.5` which produces 768-dimensional vectors. Dimension mismatch will cause upsert failures. Fix: set `size: 768` to match bge-base, or switch the embedding model to bge-small.

---

### TOOL CALLING / AGENT IMPLEMENTATION BUGS

- **agents/voice/agent_m4.py**, line 112 -- **CRITICAL** -- The `before_llm` method signature (`async def before_llm(self, text: str) -> Optional[str]`) does not match the LiveKit Agents SDK v1.4+ API; the `Agent` base class does not define a `before_llm` hook. This method will never be called, meaning the entire M4 deterministic routing layer is bypassed. Fix: use the correct LiveKit SDK hook (likely override `on_user_speech_committed` or use middleware).

- **agents/voice-offline/agent.py**, lines 64-70 -- **CRITICAL** -- `create_llm` calls `llm.LLM(...)` but `llm` is imported from `livekit.agents` as a module (`from livekit.agents import ... llm`). The `llm.LLM` class does not exist in this module; the correct import is `from livekit.plugins.openai import LLM`. Fix: use `from livekit.plugins.openai import LLM` as done in `create_stt` and `create_tts` methods below.

- **agents/voice/agent_m4.py**, lines 97-110 -- **MODERATE** -- `on_enter` returns a string, but in the LiveKit Agents SDK, `on_enter` is not expected to return a value for speech output; the returned greeting text is silently discarded. Fix: use `self.session.generate_reply()` as done in `agent.py` line 101.

- **agents/voice/agent.py**, lines 254-274 -- **MODERATE** -- `session.start()` is called before `ctx.connect()`, but in the LiveKit Agents SDK, the room must be connected first before starting the session; the session needs an active room connection to function. Fix: swap the order -- call `ctx.connect()` first, then `session.start()`.

- **agents/voice/agent.py**, line 129 -- **LOW** -- `api_key` defaults to empty string `""` via `os.environ.get("VLLM_API_KEY", "")`, but the OpenAI plugin may reject an empty string as invalid. Fix: use `"not-needed"` or `"sk-no-auth"` as done in the offline agent.

---

### AGENT-TO-AGENT COMMUNICATION ISSUES

- **agents/voice/deterministic/flows/hvac_appointment.json** vs **agents/voice/flows/hvac_service.json** -- **MODERATE** -- Two different flow schemas exist for the same HVAC domain: `hvac_appointment.json` uses an `"on"/"nlg"` schema with `"S0_greeting"` as initial state, while `hvac_service.json` uses a `"say"/"templates"/"expect"/"next"` schema with `"S1_greeting"`. The FSMExecutor in `fsm.py` only understands the `say/expect/next` schema. The `hvac_appointment.json` flow will be loaded but will not execute correctly, producing "I'm not sure what to say" for every state. Fix: convert `hvac_appointment.json` to the `say/expect/next` schema or add a schema adapter.

- **agents/voice/agent_m4.py**, line 201 -- **MODERATE** -- `FLOWS_DIR` defaults to `"/app/flows"` (hardcoded Docker path) on line 201, but line 60 sets it to `os.path.join(os.path.dirname(__file__), "flows")` (relative). The `create_m4_adapter()` function uses a different `os.getenv` call that defaults to `"/app/flows"` overriding the module-level default. Fix: use the same default in both places.

- **agents/voice-offline/agent.py**, lines 87-88 -- **MODERATE** -- `llm.ChatContext().append(role="system", text=...)` uses the `llm` module (from `livekit.agents`) but `ChatContext` may not exist in newer SDK versions, or the `append` API signature may differ. Fix: verify against the installed SDK version and use the appropriate chat context builder.

- **agents/voice-offline/agent.py**, line 116 -- **MODERATE** -- The TTS model is set to `"tts-1"` (OpenAI model name) but the local Kokoro TTS service expects `"kokoro"` as the model name, as correctly configured in `agent.py` line 178. Fix: change `model="tts-1"` to `model="kokoro"`.

- **agents/voice-offline/agent.py**, line 39 -- **LOW** -- STT URL defaults to `http://whisper:9000/v1` (with `/v1` suffix), but the online agent uses `http://localhost:8001` (no suffix). The whisper-asr service typically serves at the root, and the `/v1` suffix is only needed for OpenAI-compatible endpoints. Fix: verify the actual Whisper service endpoint and align.

---

### LITELLM PROXY CONFIG

- **config/litellm/offline-config.yaml**, line 72 -- **MODERATE** -- `master_key: "sk-dream-offline"` is hardcoded in the config file; this key is used for LiteLLM admin access but is not referenced by any agent or workflow. Any request without this key will be rejected if auth is enabled. Fix: document the key in .env or disable auth for local-only mode.

- **config/litellm/offline-config.yaml**, line 20 -- **LOW** -- The fallback model `qwen-7b-local` routes to `http://ollama:11434/v1` with model name `openai/qwen2.5:7b`, but Ollama's OpenAI-compatible endpoint expects just `qwen2.5:7b` without the `openai/` prefix. Fix: remove the `openai/` prefix.

---

### FRONTEND-BACKEND INTEGRATION GAPS

- **dashboard/src/pages/Models.jsx**, line 72 -- **LOW** -- VRAM percentage calculation `(gpu.vramUsed / gpu.vramTotal)` will produce `NaN` if `gpu.vramTotal` is 0 or undefined, causing the progress bar to break. Fix: add a guard `(gpu.vramTotal > 0 ? gpu.vramUsed / gpu.vramTotal : 0)`.

- **dashboard/src/pages/Workflows.jsx**, line 39 -- **LOW** -- `fetchWorkflows` does not set an error state on failure (`catch` only logs); the user sees an empty page with no feedback. Fix: call `setError('Failed to load workflows')` in the catch block.

- **workflows/catalog.json**, line 5 -- **LOW** -- The M4 deterministic voice workflow file reference is `08-m4-deterministic-voice.json`, but the workflow itself does not have `"active": false` set (the field is missing entirely), while all other workflows explicitly set it. Fix: add `"active": false` for consistency.

---

### MISCELLANEOUS

- **scripts/validate-models.py**, line 38 -- **MODERATE** -- The base path is hardcoded to `/home/michael/.openclaw/workspace/Lighthouse-AI/dream-server`, which will fail on any other machine or deployment. Fix: derive from `__file__` or environment variable.

- **agents/voice/deterministic/classifier.py**, line 234 -- **LOW** -- When the QwenClassifier threshold check fails (confidence < threshold), the intent is overwritten to `"fallback"` but the original confidence is preserved, making it impossible to distinguish "low confidence on a real intent" from "classifier error" (which also returns `"fallback", 0.0`). Fix: preserve the original intent in a separate field or only override confidence.

- **agents/voice-offline/requirements.txt**, line 12 -- **LOW** -- `livekit-plugins-openai` is commented out as "disabled for offline", but `agent.py` lines 105-106 import `from livekit.plugins.openai import STT` and `TTS`, which will fail at runtime. Fix: uncomment `livekit-plugins-openai` or use a different import.

- **agents/voice/deterministic/flows/hvac_service.json**, line 1 -- **LOW** -- This file contains only the text `hvac_appointment.json` (a filename string, not valid JSON). It appears to be a corrupt or placeholder file that was intended to be a symlink or redirect. Fix: replace with proper flow JSON or delete and rely on the copy in `agents/voice/flows/hvac_service.json`.

- **lib/progress.sh**, line 24 -- **LOW** -- `draw_progress_bar` divides by `$total` without checking if `$total` is zero, causing a divide-by-zero error on line 24 (`filled=$((width * current / total))`). The zero check on line 19 only guards the percent calculation. Fix: add `[[ $total -eq 0 ]] && return` at the start of the function.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 9     |
| MODERATE | 19    |
| LOW      | 11    |
| **Total**| **39**|

### Critical issues requiring immediate attention:
1. Three n8n workflows send `model: 'local'` to vLLM (404 errors)
2. M4 workflow references wrong model variant (`Coder` instead of base)
3. `before_llm` hook in agent_m4.py is never called (M4 layer fully bypassed)
4. Offline agent `create_llm` references nonexistent `llm.LLM` class (crash on startup)
5. Qdrant point ID is a float (400 error on every upsert)
6. Pro tier model name mismatch (FP16 vs AWQ) across configs
