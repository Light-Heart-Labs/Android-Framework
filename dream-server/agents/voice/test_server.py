"""
M4 Voice Agent Test Server

Provides HTTP endpoints for testing the deterministic layer
without requiring browser/voice interaction.

Usage:
    python test_server.py
    
Endpoints:
    POST /test/utterance - Test intent classification + FSM routing
    GET /metrics - Get deterministic routing metrics
    GET /health - Health check
"""

import os
import sys
import json
import time
from typing import Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Add deterministic module to path
sys.path.insert(0, os.path.dirname(__file__))
from deterministic import (
    QwenClassifier,
    LiveKitFSMAdapter,
    FSMExecutor,
)
from deterministic.extractors import DEFAULT_EXTRACTORS

app = FastAPI(title="M4 Voice Agent Test Server")

# Global state
clf = None
adapter = None
fsm = None

class UtteranceRequest(BaseModel):
    utterance: str
    session_id: str = None
    flow_name: str = "hvac_service"

class TestResponse(BaseModel):
    intent: str
    confidence: float
    deterministic: bool
    response: str
    latency_ms: float
    flow_active: bool

@app.on_event("startup")
async def startup():
    """Initialize M4 components."""
    global clf, adapter, fsm
    
    print("Initializing M4 Deterministic Layer...")
    
    # Initialize classifier
    clf = QwenClassifier(
        base_url=os.getenv("LLM_URL", "http://localhost:8000/v1"),
        model=os.getenv("LLM_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ"),
        threshold=float(os.getenv("DETERMINISTIC_THRESHOLD", "0.85"))
    )
    
    # Initialize FSM with flows
    fsm = FSMExecutor(extractors=DEFAULT_EXTRACTORS)
    flows_dir = os.getenv("FLOWS_DIR", "./flows")
    if os.path.exists(flows_dir):
        # Load flows manually to handle "domain" vs "name" field
        import glob
        for flow_file in glob.glob(os.path.join(flows_dir, "*.json")):
            with open(flow_file) as f:
                flow = json.load(f)
                # Normalize: use "domain" as "name" if present
                flow_name = flow.get("name") or flow.get("domain")
                if flow_name:
                    flow["name"] = flow_name
                    fsm.flows[flow_name] = flow
        print(f"Loaded {len(fsm.flows)} flows from {flows_dir}")
    else:
        print(f"Warning: Flows directory not found: {flows_dir}")
    
    # Initialize adapter
    adapter = LiveKitFSMAdapter(
        fsm=fsm,
        classifier=clf,
        confidence_threshold=0.85,
        entity_extractors=DEFAULT_EXTRACTORS
    )
    
    print("M4 Test Server ready!")

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "m4_enabled": clf is not None,
        "flows_loaded": len(fsm.flows) if fsm else 0
    }

@app.post("/test/utterance", response_model=TestResponse)
async def test_utterance(req: UtteranceRequest):
    """Test a single utterance through M4 pipeline."""
    session_id = req.session_id or f"test-{int(time.time())}"
    
    # Start session if new
    if session_id not in adapter.active_sessions:
        await adapter.start_session(session_id, req.flow_name)
    
    # Process utterance
    start = time.time()
    result = await adapter.handle_utterance(session_id, req.utterance)
    latency = (time.time() - start) * 1000
    
    return TestResponse(
        intent=result.intent,
        confidence=result.confidence,
        deterministic=result.used_deterministic,
        response=result.text,
        latency_ms=result.latency_ms or latency,
        flow_active=result.flow_status == "in_progress" if result.flow_status else False
    )

@app.post("/test/flow")
async def test_flow(req: UtteranceRequest):
    """Test a complete flow with multiple utterances."""
    session_id = req.session_id or f"test-{int(time.time())}"
    
    # Define test sequence
    test_utterances = [
        "schedule a service",
        "my name is Todd",
        "tomorrow at 2pm",
        "yes confirm"
    ]
    
    results = []
    await adapter.start_session(session_id, req.flow_name)
    
    for utterance in test_utterances:
        start = time.time()
        result = await adapter.handle_utterance(session_id, utterance)
        latency = (time.time() - start) * 1000
        
        results.append({
            "utterance": utterance,
            "intent": result.intent,
            "confidence": result.confidence,
            "deterministic": result.used_deterministic,
            "response": result.text,
            "latency_ms": result.latency_ms or latency
        })
    
    # Get metrics
    metrics = adapter.get_metrics()
    
    return {
        "session_id": session_id,
        "flow_name": req.flow_name,
        "results": results,
        "metrics": metrics
    }

@app.get("/metrics")
def get_metrics():
    """Get M4 routing metrics."""
    if adapter:
        return adapter.get_metrics()
    return {"error": "Adapter not initialized"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8290)
