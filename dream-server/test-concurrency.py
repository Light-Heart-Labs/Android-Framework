#!/usr/bin/env python3
"""
Concurrency Test - 5 Parallel Requests
Tests system under load with concurrent API calls
"""

import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

VLLM_URL = "http://localhost:8000"
DASHBOARD_URL = "http://localhost:3002"

class ConcurrencyTester:
    def __init__(self):
        self.results = []
        self.lock = threading.Lock()
        
    def log(self, message):
        print(f"[CONCURRENCY] {message}")
        
    def single_vllm_request(self, request_id):
        """Single vLLM request for concurrency testing"""
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": f"Request {request_id}: What is 2+2?"}
                ],
                "max_tokens": 50
            }
            
            start_time = time.time()
            response = requests.post(f"{VLLM_URL}/v1/chat/completions", 
                                   json=payload, timeout=30)
            latency = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    'request_id': request_id,
                    'status': 'SUCCESS',
                    'latency': latency,
                    'response': response.json()
                }
            else:
                return {
                    'request_id': request_id,
                    'status': 'HTTP_ERROR',
                    'latency': latency,
                    'error': response.status_code
                }
                
        except Exception as e:
            return {
                'request_id': request_id,
                'status': 'EXCEPTION',
                'latency': time.time() - start_time,
                'error': str(e)
            }
            
    def single_dashboard_request(self, request_id):
        """Single dashboard API request"""
        try:
            start_time = time.time()
            response = requests.get(f"{DASHBOARD_URL}/api/status", timeout=10)
            latency = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    'request_id': request_id,
                    'endpoint': 'dashboard',
                    'status': 'SUCCESS',
                    'latency': latency
                }
            else:
                return {
                    'request_id': request_id,
                    'endpoint': 'dashboard',
                    'status': 'HTTP_ERROR',
                    'latency': latency,
                    'error': response.status_code
                }
                
        except Exception as e:
            return {
                'request_id': request_id,
                'endpoint': 'dashboard',
                'status': 'EXCEPTION',
                'latency': time.time() - start_time,
                'error': str(e)
            }
            
    def test_concurrent_vllm(self):
        """Test 5 concurrent vLLM requests"""
        self.log("Testing 5 concurrent vLLM requests...")
        
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.single_vllm_request, i) for i in range(1, 6)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
        total_time = time.time() - start_time
        
        return results, total_time
        
    def test_mixed_load(self):
        """Test mixed load: 3 vLLM + 2 dashboard requests"""
        self.log("Testing mixed load: 3 vLLM + 2 dashboard requests...")
        
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit 3 vLLM requests
            vllm_futures = [executor.submit(self.single_vllm_request, i) for i in range(1, 4)]
            
            # Submit 2 dashboard requests
            dashboard_futures = [executor.submit(self.single_dashboard_request, i) for i in range(4, 6)]
            
            # Collect all results
            all_futures = vllm_futures + dashboard_futures
            for future in as_completed(all_futures):
                result = future.result()
                results.append(result)
                
        total_time = time.time() - start_time
        
        return results, total_time
        
    def analyze_results(self, results, total_time):
        """Analyze concurrency test results"""
        success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
        total_requests = len(results)
        
        if success_count > 0:
            latencies = [r['latency'] for r in results if r['status'] == 'SUCCESS']
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            avg_latency = min_latency = max_latency = 0
            
        return {
            'total_requests': total_requests,
            'successful_requests': success_count,
            'success_rate': (success_count / total_requests) * 100,
            'total_time': total_time,
            'avg_latency': avg_latency,
            'min_latency': min_latency,
            'max_latency': max_latency
        }
        
    def run_all(self):
        """Run all concurrency tests"""
        self.log("Starting Concurrency Tests")
        
        # Test 1: 5 concurrent vLLM requests
        vllm_results, vllm_total = self.test_concurrent_vllm()
        vllm_analysis = self.analyze_results(vllm_results, vllm_total)
        
        # Test 2: Mixed load
        mixed_results, mixed_total = self.test_mixed_load()
        mixed_analysis = self.analyze_results(mixed_results, mixed_total)
        
        return {
            'vllm_concurrent': {
                'results': vllm_results,
                'analysis': vllm_analysis
            },
            'mixed_load': {
                'results': mixed_results,
                'analysis': mixed_analysis
            }
        }

if __name__ == "__main__":
    tester = ConcurrencyTester()
    results = tester.run_all()
    
    print("\nConcurrency Test Results:")
    
    for test_name, data in results.items():
        analysis = data['analysis']
        print(f"\n{test_name.replace('_', ' ').title()}:")
        print(f"  Total Requests: {analysis['total_requests']}")
        print(f"  Successful: {analysis['successful_requests']}")
        print(f"  Success Rate: {analysis['success_rate']:.1f}%")
        print(f"  Total Time: {analysis['total_time']:.3f}s")
        print(f"  Avg Latency: {analysis['avg_latency']:.3f}s")
        print(f"  Min/Max Latency: {analysis['min_latency']:.3f}s / {analysis['max_latency']:.3f}s")