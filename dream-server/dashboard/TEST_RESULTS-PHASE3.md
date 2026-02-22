# Dream Server Dashboard Phase 3 Benchmark Results

**Test Date:** 2026-02-12 02:21 EST
**Test Environment:** Local Dream Server
**Model:** Qwen/Qwen2.5-32B-Instruct-AWQ

## Test 3.1: Latency Benchmarks


### Results

| Metric | Value |
|--------|-------|
| Requests | 20 |
| Min TTFT | 149ms |
| Max TTFT | 2773ms |
| Avg TTFT | 1743ms |
| p50 TTFT | 2081ms |
| p95 TTFT | 2773ms |

**Status: ❌ FAIL** (p95 TTFT > 1s)

---

## Test 3.2: Concurrent User Simulation

### 10 Concurrent Users
- Result: Testing 10 concurrent users (5 iterations)...
50/50 (100%)
- Status: ✅

### 25 Concurrent Users
- Result: Testing 25 concurrent users (5 iterations)...
125/125 (100%)
- Status: ✅ PASS (>95%)

### 50 Concurrent Users
- Result: Testing 50 concurrent users (3 iterations)...
150/150 (100%)
- Status: ✅ PASS (>90%)

---

## Test 3.3: Memory Leak Detection

Note: Full leak detection requires GPU monitoring (nvidia-smi)

- Baseline GPU VRAM: Failed to initialize NVML: Driver/library version mismatchMB
- VRAM monitoring not available in test environment
**Status: ⚠️ SKIPPED** (no GPU monitoring)

---

## Summary

| Test | Status | Key Metric |
|------|--------|------------|
| 3.1 Latency | ❌ FAIL | p95 TTFT: 2773ms |
| 3.2 10 Users | ✅ | Testing 10 concurrent users (5 iterations)...
50/50 (100%) |
| 3.2 25 Users | ✅ PASS | Testing 25 concurrent users (5 iterations)...
125/125 (100%) |
| 3.2 50 Users | ✅ PASS | Testing 50 concurrent users (3 iterations)...
150/150 (100%) |
| 3.3 Memory | ⚠️ SKIPPED | N/A |

**Test Completed:** 2026-02-12 02:22 EST
