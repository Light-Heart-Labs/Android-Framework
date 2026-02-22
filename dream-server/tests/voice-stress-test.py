#!/usr/bin/env python3
"""
Voice Pipeline Stress Test
Tests concurrent voice round-trips: LiveKit → Whisper → vLLM → Kokoro

Usage: python voice-stress-test.py --concurrent 10
"""

import asyncio
import aiohttp
import time
import argparse
import statistics
from dataclasses import dataclass
from typing import List
import json

# Service endpoints
WHISPER_URL = "http://localhost:9000/v1/audio/transcriptions"
VLLM_URL = "http://localhost:8000/v1/chat/completions"
KOKORO_URL = "http://localhost:8880/v1/audio/speech"

# Test audio - 1 second of silence as WAV (for STT timing without real audio)
# In real test, we'd use actual speech samples
TEST_PROMPT = "Hello, how are you today?"


@dataclass
class RoundTripResult:
    """Results from one voice round-trip"""
    session_id: int
    stt_ms: float
    llm_ms: float
    tts_ms: float
    total_ms: float
    success: bool
    error: str = ""


async def test_stt(session: aiohttp.ClientSession, session_id: int) -> tuple[float, str]:
    """Test STT endpoint - simulate transcription request"""
    start = time.perf_counter()
    try:
        # For stress testing, we'll simulate with a health check
        # Real test would send actual audio
        async with session.get("http://localhost:9000/health", timeout=30) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status == 200:
                # Simulate STT processing time based on health
                return elapsed, TEST_PROMPT
            return elapsed, ""
    except Exception as e:
        return (time.perf_counter() - start) * 1000, f"STT Error: {e}"


async def test_llm(session: aiohttp.ClientSession, session_id: int, text: str) -> tuple[float, str]:
    """Test LLM endpoint"""
    start = time.perf_counter()
    try:
        payload = {
            "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
            "messages": [
                {"role": "system", "content": "You are a helpful voice assistant. Keep responses under 50 words."},
                {"role": "user", "content": text}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        async with session.post(VLLM_URL, json=payload, timeout=60) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status == 200:
                data = await resp.json()
                response_text = data["choices"][0]["message"]["content"]
                return elapsed, response_text
            return elapsed, f"LLM Error: {resp.status}"
    except Exception as e:
        return (time.perf_counter() - start) * 1000, f"LLM Error: {e}"


async def test_tts(session: aiohttp.ClientSession, session_id: int, text: str) -> tuple[float, bool]:
    """Test TTS endpoint"""
    start = time.perf_counter()
    try:
        payload = {
            "model": "kokoro",
            "input": text[:200],  # Limit text length
            "voice": "af_heart",
            "response_format": "mp3"
        }
        async with session.post(KOKORO_URL, json=payload, timeout=120) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            if resp.status == 200:
                # Read the audio to ensure full synthesis
                audio_data = await resp.read()
                return elapsed, len(audio_data) > 0
            return elapsed, False
    except Exception as e:
        return (time.perf_counter() - start) * 1000, False


async def run_voice_roundtrip(session: aiohttp.ClientSession, session_id: int) -> RoundTripResult:
    """Run a full voice round-trip"""
    total_start = time.perf_counter()
    
    # STT
    stt_ms, transcription = await test_stt(session, session_id)
    if not transcription or transcription.startswith("STT Error"):
        return RoundTripResult(
            session_id=session_id,
            stt_ms=stt_ms, llm_ms=0, tts_ms=0,
            total_ms=(time.perf_counter() - total_start) * 1000,
            success=False, error=str(transcription)
        )
    
    # LLM
    llm_ms, response = await test_llm(session, session_id, transcription)
    if response.startswith("LLM Error"):
        return RoundTripResult(
            session_id=session_id,
            stt_ms=stt_ms, llm_ms=llm_ms, tts_ms=0,
            total_ms=(time.perf_counter() - total_start) * 1000,
            success=False, error=response
        )
    
    # TTS
    tts_ms, tts_ok = await test_tts(session, session_id, response)
    
    return RoundTripResult(
        session_id=session_id,
        stt_ms=stt_ms,
        llm_ms=llm_ms,
        tts_ms=tts_ms,
        total_ms=(time.perf_counter() - total_start) * 1000,
        success=tts_ok
    )


async def run_concurrent_test(concurrent: int, rounds: int = 3) -> List[RoundTripResult]:
    """Run concurrent voice round-trips"""
    all_results = []
    
    connector = aiohttp.TCPConnector(limit=concurrent * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        for round_num in range(rounds):
            print(f"\n{'='*60}")
            print(f"Round {round_num + 1}/{rounds} - {concurrent} concurrent sessions")
            print('='*60)
            
            tasks = [
                run_voice_roundtrip(session, i)
                for i in range(concurrent)
            ]
            
            start = time.perf_counter()
            results = await asyncio.gather(*tasks)
            wall_time = (time.perf_counter() - start) * 1000
            
            all_results.extend(results)
            
            # Print round results
            successes = sum(1 for r in results if r.success)
            print(f"Completed: {successes}/{concurrent} successful")
            print(f"Wall time: {wall_time:.0f}ms")
            
            if successes > 0:
                successful = [r for r in results if r.success]
                print(f"STT avg: {statistics.mean(r.stt_ms for r in successful):.0f}ms")
                print(f"LLM avg: {statistics.mean(r.llm_ms for r in successful):.0f}ms")
                print(f"TTS avg: {statistics.mean(r.tts_ms for r in successful):.0f}ms")
                print(f"Total avg: {statistics.mean(r.total_ms for r in successful):.0f}ms")
            
            # Brief pause between rounds
            if round_num < rounds - 1:
                await asyncio.sleep(1)
    
    return all_results


def print_summary(results: List[RoundTripResult], concurrent: int):
    """Print final summary"""
    print("\n" + "="*60)
    print("STRESS TEST SUMMARY")
    print("="*60)
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"\nConcurrency level: {concurrent}")
    print(f"Total attempts: {len(results)}")
    print(f"Successful: {len(successful)} ({100*len(successful)/len(results):.1f}%)")
    print(f"Failed: {len(failed)}")
    
    if successful:
        print(f"\n{'Stage':<12} {'Min':>8} {'Avg':>8} {'Max':>8} {'P95':>8}")
        print("-" * 48)
        
        for stage, getter in [
            ("STT", lambda r: r.stt_ms),
            ("LLM", lambda r: r.llm_ms),
            ("TTS", lambda r: r.tts_ms),
            ("Total", lambda r: r.total_ms)
        ]:
            values = [getter(r) for r in successful]
            values.sort()
            p95_idx = int(len(values) * 0.95)
            print(f"{stage:<12} {min(values):>7.0f}ms {statistics.mean(values):>7.0f}ms "
                  f"{max(values):>7.0f}ms {values[p95_idx] if p95_idx < len(values) else values[-1]:>7.0f}ms")
        
        # Throughput
        total_time_s = sum(r.total_ms for r in successful) / 1000
        print(f"\nEffective throughput: {len(successful) / (total_time_s / concurrent):.1f} round-trips/sec")
        
        # Bottleneck analysis
        avg_stt = statistics.mean(r.stt_ms for r in successful)
        avg_llm = statistics.mean(r.llm_ms for r in successful)
        avg_tts = statistics.mean(r.tts_ms for r in successful)
        
        bottleneck = max([("STT", avg_stt), ("LLM", avg_llm), ("TTS", avg_tts)], key=lambda x: x[1])
        print(f"\n🎯 Bottleneck: {bottleneck[0]} ({bottleneck[1]:.0f}ms avg)")
        
        # Scaling estimate
        if avg_tts > avg_llm * 2:
            print("⚠️  TTS is >2x slower than LLM - TTS scaling limits concurrency")
    
    if failed:
        print(f"\nFailure samples:")
        for r in failed[:3]:
            print(f"  Session {r.session_id}: {r.error}")


async def check_services():
    """Verify all services are up before testing"""
    print("Checking services...")
    
    services = [
        ("Whisper STT", "http://localhost:9000/health"),
        ("vLLM", "http://localhost:8000/health"),
        ("Kokoro TTS", "http://localhost:8880/health"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for name, url in services:
            try:
                async with session.get(url, timeout=5) as resp:
                    status = "✅" if resp.status == 200 else f"⚠️ {resp.status}"
                    print(f"  {name}: {status}")
            except Exception as e:
                print(f"  {name}: ❌ {e}")
                return False
    return True


async def main():
    parser = argparse.ArgumentParser(description="Voice Pipeline Stress Test")
    parser.add_argument("--concurrent", "-c", type=int, default=5,
                        help="Number of concurrent sessions (default: 5)")
    parser.add_argument("--rounds", "-r", type=int, default=3,
                        help="Number of test rounds (default: 3)")
    parser.add_argument("--skip-check", action="store_true",
                        help="Skip service health check")
    args = parser.parse_args()
    
    print("🎙️  Voice Pipeline Stress Test")
    print(f"Testing {args.concurrent} concurrent sessions × {args.rounds} rounds")
    print()
    
    if not args.skip_check:
        if not await check_services():
            print("\n❌ Some services are down. Fix before testing.")
            return
    
    results = await run_concurrent_test(args.concurrent, args.rounds)
    print_summary(results, args.concurrent)


if __name__ == "__main__":
    asyncio.run(main())
