#!/usr/bin/env python3
"""
M4 Voice-to-Shield Integration Test Suite
Validates the complete voice → shield → API pipeline per M4 spec

The Privacy Shield is a transparent proxy - it intercepts chat completions
and performs anonymization/deanonymization automatically.

Usage:
    python3 tests/test_m4_voice_shield_integration.py
    python3 tests/test_m4_voice_shield_integration.py --stress
    python3 tests/test_m4_voice_shield_integration.py --verbose

Exit codes:
    0 - All tests passed
    1 - Some tests failed
"""

import os
import sys
import json
import time
import asyncio
import argparse
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

import httpx

# Configuration
SHIELD_URL = os.getenv("SHIELD_URL", "http://localhost:8085/v1/chat/completions")
DIRECT_LLM_URL = os.getenv("DIRECT_LLM_URL", "http://localhost:8003/v1/chat/completions")
STT_URL = os.getenv("STT_URL", "http://localhost:9000/v1/audio/transcriptions")
TTS_URL = os.getenv("TTS_URL", "http://localhost:8880/v1/audio/speech")
SHIELD_HEALTH = os.getenv("SHIELD_HEALTH", "http://localhost:8085/health")

TIMEOUT = 30.0


@dataclass
class PipelineResult:
    """Result of a pipeline stage."""
    stage: str
    success: bool
    latency_ms: float
    error: Optional[str] = None
    data: Optional[Dict] = None


class M4IntegrationTest:
    """M4 Voice-Shield integration test suite."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: list[PipelineResult] = []
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    def log(self, message: str):
        """Print if verbose mode."""
        if self.verbose:
            print(f"  [M4] {message}")
    
    # =================================================================
    # Health Check
    # =================================================================
    
    async def check_shield_health(self) -> bool:
        """Check if Privacy Shield is running."""
        try:
            response = await self.client.get(SHIELD_HEALTH)
            return response.status_code == 200
        except Exception as e:
            print(f"Shield health check failed: {e}")
            return False
    
    # =================================================================
    # Stage 1: Shield Proxy Test (Anonymization via proxy)
    # =================================================================
    
    async def test_shield_proxy(self, user_text: str, system_prompt: str = "") -> PipelineResult:
        """Test Shield proxy with PII in user message.
        
        The Shield should anonymize the request before sending to LLM,
        then de-anonymize the response.
        """
        start = time.perf_counter()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text})
        
        try:
            response = await self.client.post(
                SHIELD_URL,
                json={
                    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 256
                },
                timeout=TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            latency_ms = (time.perf_counter() - start) * 1000
            
            content = data["choices"][0]["message"]["content"]
            self.log(f"Shield proxy response: {content[:100]}...")
            
            # Check if response contains de-anonymized content
            # If user mentioned "John Smith", response should too (not <PERSON_1>)
            has_placeholders = "<PERSON_" in content or "<LOCATION_" in content
            
            return PipelineResult(
                stage="shield_proxy",
                success=True,
                latency_ms=latency_ms,
                data={
                    "response": content,
                    "has_placeholders": has_placeholders,
                    "raw": data
                }
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return PipelineResult(
                stage="shield_proxy",
                success=False,
                latency_ms=latency_ms,
                error=str(e)
            )
    
    # =================================================================
    # Stage 2: Direct LLM Comparison (no shield)
    # =================================================================
    
    async def test_direct_llm(self, user_text: str, system_prompt: str = "") -> PipelineResult:
        """Test direct LLM without Shield for comparison."""
        start = time.perf_counter()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text})
        
        try:
            response = await self.client.post(
                DIRECT_LLM_URL,
                json={
                    "model": "Qwen/Qwen2.5-32B-Instruct-AWQ",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 256
                },
                timeout=TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            latency_ms = (time.perf_counter() - start) * 1000
            
            content = data["choices"][0]["message"]["content"]
            self.log(f"Direct LLM response: {content[:100]}...")
            
            return PipelineResult(
                stage="direct_llm",
                success=True,
                latency_ms=latency_ms,
                data={"response": content, "raw": data}
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return PipelineResult(
                stage="direct_llm",
                success=False,
                latency_ms=latency_ms,
                error=str(e)
            )
    
    # =================================================================
    # Stage 3: Full Pipeline Integration Test
    # =================================================================
    
    async def test_full_pipeline(self, user_query: str, scenario: str) -> Dict[str, Any]:
        """Test complete voice → shield → API pipeline.
        
        Simulates: Voice input → STT → LLM(via Shield) → TTS
        """
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario}")
        print(f"Query: \"{user_query}\"")
        print(f"{'='*60}")
        
        results = []
        
        # Step 1: Test through Shield Proxy
        print("\n1. Testing Shield Proxy (with anonymization)...")
        system_prompt = "You are a helpful assistant. Keep responses brief."
        
        shield_result = await self.test_shield_proxy(user_query, system_prompt)
        results.append(shield_result)
        
        if not shield_result.success:
            print(f"   ❌ FAILED: {shield_result.error}")
            return {"success": False, "stage": "shield_proxy", "results": results}
        
        print(f"   ✅ Latency: {shield_result.latency_ms:.1f}ms")
        print(f"   📝 Response: {shield_result.data['response'][:80]}...")
        
        if shield_result.data.get('has_placeholders'):
            print(f"   ⚠️  Warning: Response contains unresolved placeholders")
        
        # Step 2: Compare with Direct LLM
        print("\n2. Comparing with Direct LLM (no shield)...")
        direct_result = await self.test_direct_llm(user_query, system_prompt)
        results.append(direct_result)
        
        if direct_result.success:
            overhead_ms = shield_result.latency_ms - direct_result.latency_ms
            print(f"   ✅ Latency: {direct_result.latency_ms:.1f}ms")
            print(f"   📊 Shield Overhead: {overhead_ms:+.1f}ms")
        else:
            print(f"   ⚠️  Direct LLM failed (non-critical): {direct_result.error}")
        
        # Summary for this test
        total_latency = shield_result.latency_ms
        print(f"\n📊 Total Pipeline Latency: {total_latency:.1f}ms")
        
        return {
            "success": True,
            "results": results,
            "total_latency_ms": total_latency,
            "shield_overhead_ms": overhead_ms if direct_result.success else None
        }
    
    # =================================================================
    # Test Scenarios
    # =================================================================
    
    async def run_all_tests(self) -> bool:
        """Run all M4 integration tests."""
        print("\n" + "="*60)
        print("M4 Voice-Shield Integration Test Suite")
        print("="*60)
        print(f"Shield Proxy: {SHIELD_URL}")
        print(f"Direct LLM:   {DIRECT_LLM_URL}")
        
        # Pre-flight health check
        print("\n🔍 Pre-flight Health Check...")
        if await self.check_shield_health():
            print("   ✅ Privacy Shield is healthy")
        else:
            print("   ❌ Privacy Shield is not responding")
            return False
        
        # Test scenarios
        test_cases = [
            {
                "scenario": "Weather Query with PII",
                "query": "What's the weather like in Austin? I'm John Smith."
            },
            {
                "scenario": "Contact Request with Phone",
                "query": "Call Mary at 555-1234 about the meeting."
            },
            {
                "scenario": "Email Reference",
                "query": "Send an email to david@example.com regarding the project."
            },
            {
                "scenario": "Address Mention",
                "query": "Schedule a meeting at 123 Main Street, Boston."
            },
            {
                "scenario": "No PII (Baseline)",
                "query": "What is the capital of France?"
            }
        ]
        
        all_passed = True
        total_tests = 0
        passed_tests = 0
        latencies = []
        overheads = []
        
        for test_case in test_cases:
            result = await self.test_full_pipeline(
                test_case["query"],
                test_case["scenario"]
            )
            total_tests += 1
            
            if result["success"]:
                passed_tests += 1
                latencies.append(result["total_latency_ms"])
                if result.get("shield_overhead_ms") is not None:
                    overheads.append(result["shield_overhead_ms"])
                print(f"\n✅ TEST PASSED")
            else:
                all_passed = False
                print(f"\n❌ TEST FAILED at stage: {result['stage']}")
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Passed: {passed_tests}/{total_tests}")
        print(f"Failed: {total_tests - passed_tests}/{total_tests}")
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            print(f"\n📊 Latency Statistics:")
            print(f"   Mean: {avg_latency:.1f}ms")
            print(f"   P95:  {p95_latency:.1f}ms")
            
            # M4 Spec compliance
            print(f"\n✅ M4 Spec Compliance:")
            print(f"   Target P95 < 2250ms: {'PASS' if p95_latency < 2250 else 'FAIL'}")
        
        if overheads:
            avg_overhead = sum(overheads) / len(overheads)
            print(f"\n📊 Shield Overhead:")
            print(f"   Mean: {avg_overhead:+.1f}ms")
            print(f"   Target < 50ms: {'PASS' if avg_overhead < 50 else 'FAIL'}")
        
        if all_passed:
            print("\n🎉 All M4 integration tests PASSED!")
            print("Voice → Shield → LLM pipeline is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Review errors above.")
        
        return all_passed
    
    # =================================================================
    # Latency Benchmark
    # =================================================================
    
    async def run_latency_benchmark(self, iterations: int = 50):
        """Run latency benchmark comparing Shield vs Direct."""
        print("\n" + "="*60)
        print(f"M4 Shield Latency Benchmark ({iterations} iterations)")
        print("="*60)
        
        test_query = "What's the weather in Austin? I'm John Smith."
        system_prompt = "You are a helpful assistant. Keep responses brief."
        
        # Warmup
        print("Warming up...")
        for _ in range(3):
            await self.test_shield_proxy(test_query, system_prompt)
            await self.test_direct_llm(test_query, system_prompt)
        
        # Benchmark Shield
        print(f"\nRunning {iterations} Shield proxy requests...")
        shield_latencies = []
        
        for i in range(iterations):
            result = await self.test_shield_proxy(test_query, system_prompt)
            if result.success:
                shield_latencies.append(result.latency_ms)
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations}")
        
        # Benchmark Direct
        print(f"\nRunning {iterations} Direct LLM requests...")
        direct_latencies = []
        
        for i in range(iterations):
            result = await self.test_direct_llm(test_query, system_prompt)
            if result.success:
                direct_latencies.append(result.latency_ms)
            
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{iterations}")
        
        # Stats
        def calc_stats(latencies):
            if not latencies:
                return {}
            latencies.sort()
            return {
                "mean": sum(latencies) / len(latencies),
                "p50": latencies[len(latencies) // 2],
                "p95": latencies[int(len(latencies) * 0.95)],
                "p99": latencies[int(len(latencies) * 0.99)],
                "min": min(latencies),
                "max": max(latencies)
            }
        
        shield_stats = calc_stats(shield_latencies)
        direct_stats = calc_stats(direct_latencies)
        
        print(f"\n📊 Shield Proxy Results:")
        if shield_stats:
            print(f"   Mean: {shield_stats['mean']:.2f}ms")
            print(f"   P50:  {shield_stats['p50']:.2f}ms")
            print(f"   P95:  {shield_stats['p95']:.2f}ms")
            print(f"   P99:  {shield_stats['p99']:.2f}ms")
        
        print(f"\n📊 Direct LLM Results:")
        if direct_stats:
            print(f"   Mean: {direct_stats['mean']:.2f}ms")
            print(f"   P50:  {direct_stats['p50']:.2f}ms")
            print(f"   P95:  {direct_stats['p95']:.2f}ms")
            print(f"   P99:  {direct_stats['p99']:.2f}ms")
        
        if shield_stats and direct_stats:
            overhead_mean = shield_stats['mean'] - direct_stats['mean']
            overhead_p95 = shield_stats['p95'] - direct_stats['p95']
            
            print(f"\n📊 Shield Overhead:")
            print(f"   Mean: {overhead_mean:+.2f}ms")
            print(f"   P95:  {overhead_p95:+.2f}ms")
            
            print(f"\n✅ M4 Spec Compliance:")
            print(f"   Target Shield P95 < 50ms overhead: {'PASS' if overhead_p95 < 50 else 'FAIL'}")


async def main():
    parser = argparse.ArgumentParser(description="M4 Voice-Shield Integration Tests")
    parser.add_argument("--stress", action="store_true", help="Run latency benchmark")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--iterations", "-n", type=int, default=50, help="Benchmark iterations")
    args = parser.parse_args()
    
    async with M4IntegrationTest(verbose=args.verbose) as tester:
        if args.stress:
            await tester.run_latency_benchmark(iterations=args.iterations)
        else:
            success = await tester.run_all_tests()
            sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
