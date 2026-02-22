#!/usr/bin/env python3
"""
Tool Calling Validation Test
Tests LLM ability to call tools/functions properly
"""

import requests
import json
import time

VLLM_URL = "http://localhost:8000"

class ToolCallTester:
    def __init__(self):
        self.results = []
        
    def log(self, message):
        print(f"[TOOLS] {message}")
        
    def test_function_calling(self):
        """Test function calling capability"""
        try:
            payload = {
                "messages": [
                    {
                        "role": "user", 
                        "content": "What's the weather in New York? Use the weather tool."
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "Get current weather for a location",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "location": {"type": "string"}
                                },
                                "required": ["location"]
                            }
                        }
                    }
                ],
                "max_tokens": 200
            }
            
            start_time = time.time()
            response = requests.post(f"{VLLM_URL}/v1/chat/completions", 
                                   json=payload, timeout=30)
            latency = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if tool call was made
                message = data['choices'][0]['message']
                has_tool_call = 'tool_calls' in message and len(message.get('tool_calls', [])) > 0
                
                return has_tool_call, latency, message
            else:
                return False, latency, None
                
        except Exception as e:
            return False, 0, None
            
    def test_tool_response(self):
        """Test tool response handling"""
        try:
            # Simulate a tool call response
            payload = {
                "messages": [
                    {"role": "user", "content": "What's 15 * 23?"},
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "calc_1",
                                "type": "function",
                                "function": {
                                    "name": "calculate",
                                    "arguments": "{\"expression\": \"15 * 23\"}"
                                }
                            }
                        ]
                    },
                    {
                        "role": "tool",
                        "content": "345",
                        "tool_call_id": "calc_1"
                    }
                ],
                "max_tokens": 100
            }
            
            start_time = time.time()
            response = requests.post(f"{VLLM_URL}/v1/chat/completions", 
                                   json=payload, timeout=30)
            latency = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                answer = data['choices'][0]['message']['content']
                contains_result = "345" in answer
                
                return contains_result, latency
            else:
                return False, latency
                
        except Exception as e:
            return False, 0
            
    def run_all(self):
        """Run all tool calling tests"""
        self.log("Starting Tool Calling Validation Tests")
        
        tests = [
            ("Function Calling", self.test_function_calling),
            ("Tool Response", self.test_tool_response)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            self.log(f"Testing {test_name}...")
            
            if test_name == "Function Calling":
                success, latency, message = test_func()
                results.append({
                    'test': test_name,
                    'status': 'PASS' if success else 'FAIL',
                    'latency': f"{latency:.3f}s",
                    'details': str(message) if message else "No tool call made"
                })
            else:
                success, latency = test_func()
                results.append({
                    'test': test_name,
                    'status': 'PASS' if success else 'FAIL',
                    'latency': f"{latency:.3f}s"
                })
                
            self.log(f"  {'✓' if success else '✗'} {test_name} ({latency:.3f}s)")
            
        return results

if __name__ == "__main__":
    tester = ToolCallTester()
    results = tester.run_all()
    
    print("\nTool Calling Test Results:")
    for result in results:
        print(f"  {result['test']}: {result['status']} ({result['latency']})")
        if 'details' in result:
            print(f"    Details: {result['details']}")