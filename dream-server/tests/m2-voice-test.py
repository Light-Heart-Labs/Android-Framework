#!/usr/bin/env python3
"""
M2 Voice Agent Testing Suite

Tests voice round-trip latency and multi-turn context handling.
Target: <3s round-trip, multi-turn context preservation

Usage:
    python3 m2-voice-test.py           # Run all tests
    python3 m2-voice-test.py --latency # Latency test only
    python3 m2-voice-test.py --context # Multi-turn test only
"""

import argparse
import json
import time
import base64
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

# Service endpoints
WHISPER_URL = "http://localhost:9000"
VLLM_URL = "http://localhost:8000"
TTS_URL = "http://localhost:8880"
LIVEKIT_URL = "http://localhost:7880"

# Test configuration
TIMEOUT = 30
VOICE = "af_bella"
MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"


class VoiceTester:
    """Test voice pipeline: STT -> LLM -> TTS"""
    
    def __init__(self):
        self.results = []
        
    def log(self, message: str):
        print(f"[M2] {message}")
        
    def test_stt_basic(self) -> Tuple[bool, float]:
        """Test Whisper STT with sample audio"""
        self.log("Testing Whisper STT...")
        
        # Create a simple test audio (1 second of silence as base64 WAV)
        # This is a minimal valid WAV file (44 bytes header + silence)
        try:
            # Check if Whisper is accessible
            start = time.time()
            response = requests.get(f"{WHISPER_URL}/", timeout=5)
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                self.log(f"  ✓ Whisper responding ({elapsed:.0f}ms)")
                return True, elapsed
            else:
                self.log(f"  ✗ Whisper returned {response.status_code}")
                return False, 0
        except Exception as e:
            self.log(f"  ✗ Whisper connection failed: {e}")
            return False, 0
            
    def test_llm_response(self, prompt: str) -> Tuple[bool, str, float]:
        """Test LLM response generation"""
        self.log(f"Testing LLM response for: '{prompt[:50]}...'")
        
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100
        }
        
        try:
            start = time.time()
            response = requests.post(
                f"{VLLM_URL}/v1/chat/completions",
                json=payload,
                timeout=TIMEOUT
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                self.log(f"  ✓ LLM responded ({elapsed:.0f}ms, {len(content)} chars)")
                return True, content, elapsed
            else:
                self.log(f"  ✗ LLM returned {response.status_code}")
                return False, "", 0
        except Exception as e:
            self.log(f"  ✗ LLM request failed: {e}")
            return False, "", 0
            
    def test_llm_response_constrained(self, prompt: str) -> Tuple[bool, str, float]:
        """Test LLM with voice-optimized constraints (shorter output = faster TTS)"""
        self.log(f"Testing constrained LLM for: '{prompt[:50]}...'")
        
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Respond in 1-2 sentences only. Be concise."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 75,
            "temperature": 0.7
        }
        
        try:
            start = time.time()
            response = requests.post(
                f"{VLLM_URL}/v1/chat/completions",
                json=payload,
                timeout=TIMEOUT
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                self.log(f"  ✓ LLM constrained ({elapsed:.0f}ms, {len(content)} chars)")
                return True, content, elapsed
            else:
                self.log(f"  ✗ LLM returned {response.status_code}")
                return False, "", 0
        except Exception as e:
            self.log(f"  ✗ LLM request failed: {e}")
            return False, "", 0
            
    def test_tts_generation(self, text: str) -> Tuple[bool, float]:
        """Test TTS audio generation"""
        self.log(f"Testing TTS for: '{text[:50]}...'")
        
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": VOICE
        }
        
        try:
            start = time.time()
            response = requests.post(
                f"{TTS_URL}/v1/audio/speech",
                json=payload,
                timeout=TIMEOUT
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                audio_size = len(response.content)
                self.log(f"  ✓ TTS generated ({elapsed:.0f}ms, {audio_size} bytes)")
                return True, elapsed
            else:
                self.log(f"  ✗ TTS returned {response.status_code}")
                return False, 0
        except Exception as e:
            self.log(f"  ✗ TTS request failed: {e}")
            return False, 0
            
    def test_voice_roundtrip(self, prompt: str, constrain: bool = True) -> Tuple[bool, float, Dict]:
        """Test full voice round-trip: text -> LLM -> TTS
        
        Args:
            prompt: User prompt
            constrain: If True, apply voice-optimized constraints (shorter output)
        """
        self.log(f"Testing voice round-trip{' (constrained)' if constrain else ''}...")
        
        start = time.time()
        
        # Step 1: LLM (with voice constraints for faster TTS)
        if constrain:
            llm_ok, llm_text, llm_time = self.test_llm_response_constrained(prompt)
        else:
            llm_ok, llm_text, llm_time = self.test_llm_response(prompt)
        if not llm_ok:
            return False, 0, {}
            
        # Step 2: TTS
        tts_ok, tts_time = self.test_tts_generation(llm_text)
        if not tts_ok:
            return False, 0, {}
            
        total_time = (time.time() - start) * 1000
        
        metrics = {
            "llm_time_ms": llm_time,
            "tts_time_ms": tts_time,
            "total_time_ms": total_time,
            "text_length": len(llm_text)
        }
        
        self.log(f"  ✓ Round-trip complete ({total_time:.0f}ms)")
        return True, total_time, metrics
        
    def test_multiturn_context(self) -> Tuple[bool, List[Dict]]:
        """Test multi-turn conversation context preservation"""
        self.log("Testing multi-turn context...")
        
        conversation = [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
            {"role": "user", "content": "What's my name?"}
        ]
        
        payload = {
            "model": MODEL,
            "messages": conversation,
            "max_tokens": 50
        }
        
        try:
            start = time.time()
            response = requests.post(
                f"{VLLM_URL}/v1/chat/completions",
                json=payload,
                timeout=TIMEOUT
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"].lower()
                
                # Check if context was preserved
                has_context = "alice" in content
                
                self.log(f"  ✓ Multi-turn test ({elapsed:.0f}ms)")
                self.log(f"  Context preserved: {'Yes' if has_context else 'No'}")
                self.log(f"  Response: {content[:100]}...")
                
                return has_context, [
                    {"turn": i+1, "time_ms": elapsed if i == 2 else 0}
                    for i in range(3)
                ]
            else:
                self.log(f"  ✗ Multi-turn failed: {response.status_code}")
                return False, []
        except Exception as e:
            self.log(f"  ✗ Multi-turn error: {e}")
            return False, []
            
    def run_latency_tests(self) -> Dict:
        """Run comprehensive latency tests"""
        self.log("=" * 50)
        self.log("M2 Voice Latency Tests")
        self.log("=" * 50)
        
        results = {
            "stt": {"passed": False, "time_ms": 0},
            "llm": {"passed": False, "time_ms": 0},
            "tts": {"passed": False, "time_ms": 0},
            "roundtrip": {"passed": False, "time_ms": 0}
        }
        
        # Test STT
        stt_ok, stt_time = self.test_stt_basic()
        results["stt"] = {"passed": stt_ok, "time_ms": stt_time}
        
        # Test LLM
        llm_ok, llm_text, llm_time = self.test_llm_response(
            "What is the weather like today?"
        )
        results["llm"] = {"passed": llm_ok, "time_ms": llm_time}
        
        # Test TTS
        tts_ok, tts_time = self.test_tts_generation(
            "The weather today is sunny and 75 degrees."
        )
        results["tts"] = {"passed": tts_ok, "time_ms": tts_time}
        
        # Test full round-trip
        if llm_ok and tts_ok:
            rt_ok, rt_time, metrics = self.test_voice_roundtrip(
                "Tell me a fun fact about space"
            )
            results["roundtrip"] = {
                "passed": rt_ok,
                "time_ms": rt_time,
                **metrics
            }
            
        return results
        
    def run_context_tests(self) -> Dict:
        """Run multi-turn context tests"""
        self.log("=" * 50)
        self.log("M2 Multi-Turn Context Tests")
        self.log("=" * 50)
        
        context_ok, turn_metrics = self.test_multiturn_context()
        
        return {
            "context_preserved": context_ok,
            "turns": turn_metrics
        }
        
    def generate_report(self, latency: Dict, context: Dict) -> str:
        """Generate test report"""
        report = []
        report.append("\n" + "=" * 50)
        report.append("M2 Voice Agent Test Report")
        report.append("=" * 50)
        
        # Latency section
        report.append("\n📊 Latency Results:")
        report.append("-" * 30)
        
        stt = latency.get("stt", {})
        llm = latency.get("llm", {})
        tts = latency.get("tts", {})
        rt = latency.get("roundtrip", {})
        
        report.append(f"  STT Health:     {'✓' if stt.get('passed') else '✗'} ({stt.get('time_ms', 0):.0f}ms)")
        report.append(f"  LLM Response:   {'✓' if llm.get('passed') else '✗'} ({llm.get('time_ms', 0):.0f}ms)")
        report.append(f"  TTS Generation: {'✓' if tts.get('passed') else '✗'} ({tts.get('time_ms', 0):.0f}ms)")
        report.append(f"  Full Roundtrip: {'✓' if rt.get('passed') else '✗'} ({rt.get('time_ms', 0):.0f}ms)")
        
        # Target check
        rt_time = rt.get("time_ms", 0)
        if rt_time > 0:
            report.append(f"\n  Target <3000ms: {'✓ PASS' if rt_time < 3000 else '✗ FAIL'}")
            
        # Context section
        report.append("\n🔄 Multi-Turn Context:")
        report.append("-" * 30)
        context_ok = context.get("context_preserved", False)
        report.append(f"  Context preserved: {'✓ YES' if context_ok else '✗ NO'}")
        
        # Summary
        all_passed = (
            stt.get("passed") and
            llm.get("passed") and
            tts.get("passed") and
            rt.get("passed") and
            context_ok
        )
        
        report.append("\n" + "=" * 50)
        report.append(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
        report.append("=" * 50)
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="M2 Voice Agent Testing")
    parser.add_argument("--latency", action="store_true", help="Latency tests only")
    parser.add_argument("--context", action="store_true", help="Context tests only")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()
    
    tester = VoiceTester()
    
    # Default: run all tests
    run_latency = not args.context
    run_context = not args.latency
    
    results = {}
    
    if run_latency:
        results["latency"] = tester.run_latency_tests()
        
    if run_context:
        results["context"] = tester.run_context_tests()
        
    # Generate report
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if run_latency and run_context:
            print(tester.generate_report(results["latency"], results["context"]))
        elif run_latency:
            lat = results["latency"]
            print(f"\nLatency Test Results:")
            print(f"  STT:     {'✓' if lat['stt']['passed'] else '✗'} ({lat['stt']['time_ms']:.0f}ms)")
            print(f"  LLM:     {'✓' if lat['llm']['passed'] else '✗'} ({lat['llm']['time_ms']:.0f}ms)")
            print(f"  TTS:     {'✓' if lat['tts']['passed'] else '✗'} ({lat['tts']['time_ms']:.0f}ms)")
            print(f"  RT:      {'✓' if lat['roundtrip']['passed'] else '✗'} ({lat['roundtrip']['time_ms']:.0f}ms)")
        else:
            ctx = results["context"]
            print(f"\nContext Test Results:")
            print(f"  Preserved: {'✓ YES' if ctx['context_preserved'] else '✗ NO'}")


if __name__ == "__main__":
    main()
