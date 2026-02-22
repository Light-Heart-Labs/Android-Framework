#!/usr/bin/env python3
"""
Deterministic router for offline voice agent
Routes conversations based on classified intents
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DeterministicRouter:
    """Routes conversations based on deterministic flows"""

    def __init__(self, flows_dir: str = None, classifier=None, fsm=None, fallback_threshold: float = 0.85):
        self.flows_dir = flows_dir
        self.classifier = classifier
        self.fsm = fsm
        self.fallback_threshold = fallback_threshold
        self.flows = {}
        self.current_flows = {}  # Track active flows per session
    
    async def initialize(self):
        """Load flow definitions"""
        import os
        if not os.path.exists(self.flows_dir):
            logger.warning(f"Flows directory not found: {self.flows_dir}")
            return
        
        for filename in os.listdir(self.flows_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.flows_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        flow = json.load(f)
                        flow_name = filename.replace('.json', '')
                        self.flows[flow_name] = flow
                except Exception as e:
                    logger.error(f"Failed to load flow {filename}: {e}")
    
    async def get_response(self, session_id: str, intent: str, user_input: str, context: Dict[str, Any] = None) -> str:
        """Get response based on flow and current state"""
        if intent not in self.flows:
            return self.get_fallback_response(user_input)
        
        flow = self.flows[intent]
        
        # Initialize session if new
        if session_id not in self.current_flows:
            self.current_flows[session_id] = {
                "intent": intent,
                "current_step": 0,
                "data": {},
                "started": datetime.now(timezone.utc).isoformat()
            }
        
        session = self.current_flows[session_id]
        
        # Get current step
        steps = flow.get("steps", [])
        current_step = session["current_step"]
        
        if current_step >= len(steps):
            # Flow completed
            response = flow.get("completion_message", "Thank you! Is there anything else I can help you with?")
            del self.current_flows[session_id]  # Clean up
            return response
        
        step = steps[current_step]
        
        # Validate required fields
        if "validation" in step:
            validation = step["validation"]
            if validation.get("type") == "regex":
                import re
                pattern = validation.get("pattern", ".*")
                if not re.match(pattern, user_input, re.IGNORECASE):
                    return validation.get("error_message", "I didn't understand that. Please try again.")
        
        # Store user response
        if "field" in step:
            session["data"][step["field"]] = user_input
        
        # Get next response
        response = step.get("response", "Thank you for your input.")
        
        # Advance to next step
        session["current_step"] += 1
        
        return response
    
    def get_fallback_response(self, user_input: str) -> str:
        """Get fallback response for unmatched intents"""
        return "I understand you're asking about that, but I'm running in offline mode and can only help with tasks I have specific flows for. Would you like me to help with something else, or can you try rephrasing your request?"
    
    def reset_session(self, session_id: str):
        """Reset session state"""
        if session_id in self.current_flows:
            del self.current_flows[session_id]
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get current session info"""
        return self.current_flows.get(session_id, {})
    
    def list_available_flows(self) -> List[str]:
        """List available flow names"""
        return list(self.flows.keys())

# Example flows
EXAMPLE_FLOWS = {
    "restaurant_reservation": {
        "steps": [
            {
                "response": "I'd be happy to help you book a restaurant reservation. What date would you like?",
                "field": "date"
            },
            {
                "response": "What time would you prefer?",
                "field": "time"
            },
            {
                "response": "How many people will be dining?",
                "field": "party_size"
            },
            {
                "response": "Do you have any dietary restrictions or special requests?",
                "field": "special_requests"
            }
        ],
        "completion_message": "Perfect! I've collected all the details for your reservation. In a real system, I would now process this booking."
    }
}

if __name__ == "__main__":
    import asyncio
    
    async def test():
        router = DeterministicRouter("./flows")
        await router.initialize()
        
        print("Available flows:", router.list_available_flows())
    
    asyncio.run(test())