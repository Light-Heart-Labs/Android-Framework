#!/usr/bin/env python3
"""
Deterministic classifier for offline voice agent
Handles intent classification using local models
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from .router import DeterministicRouter

logger = logging.getLogger(__name__)


class KeywordClassifier:
    """Simple keyword-based intent classifier for offline mode"""
    
    def __init__(self, keywords: Dict[str, List[str]]):
        """
        Args:
            keywords: Dict mapping intent names to keyword lists
        """
        self.keywords = keywords or {}
    
    def classify(self, text: str) -> tuple[str, float]:
        """Classify text by keyword matching"""
        text_lower = text.lower()
        best_intent = "fallback"
        best_score = 0.0
        
        for intent, kw_list in self.keywords.items():
            matches = sum(1 for kw in kw_list if kw.lower() in text_lower)
            if matches > 0:
                score = matches / len(kw_list)
                if score > best_score:
                    best_score = score
                    best_intent = intent
        
        return best_intent, best_score


class FSMExecutor:
    """Finite State Machine executor for deterministic flows"""
    
    def __init__(self, flows_dir: str):
        self.flows_dir = flows_dir
        self.flows: Dict[str, dict] = {}
        self.current_flow: Optional[str] = None
        self.current_state: Optional[str] = None
        self._load_flows()
    
    def _load_flows(self):
        """Load flow definitions from JSON files"""
        if not os.path.exists(self.flows_dir):
            logger.warning(f"Flows directory not found: {self.flows_dir}")
            return
        
        for filename in os.listdir(self.flows_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.flows_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        flow = json.load(f)
                        flow_name = flow.get('name', filename.replace('.json', ''))
                        self.flows[flow_name] = flow
                        logger.info(f"Loaded flow: {flow_name}")
                except Exception as e:
                    logger.error(f"Failed to load flow {filename}: {e}")
    
    def start_flow(self, flow_name: str) -> Optional[str]:
        """Start a flow and return initial response"""
        if flow_name not in self.flows:
            return None
        
        self.current_flow = flow_name
        flow = self.flows[flow_name]
        self.current_state = flow.get('initial_state', 'start')
        
        # Return initial greeting if defined
        states = flow.get('states', {})
        if self.current_state in states:
            return states[self.current_state].get('say')
        return None
    
    def process(self, text: str) -> Optional[str]:
        """Process user input and return response"""
        if not self.current_flow or not self.current_state:
            return None
        
        flow = self.flows[self.current_flow]
        states = flow.get('states', {})
        current = states.get(self.current_state, {})
        
        # Simple transition logic - look for next state
        transitions = current.get('transitions', {})
        for trigger, next_state in transitions.items():
            if trigger.lower() in text.lower() or trigger == '*':
                self.current_state = next_state
                if next_state in states:
                    return states[next_state].get('say')
        
        # No matching transition - return default or None
        return current.get('fallback_say')

class DeterministicClassifier:
    """Simple rule-based classifier for offline mode"""
    
    def __init__(self, flows_dir: str):
        self.flows_dir = flows_dir
        self.intents = {}
        self.patterns = {}
    
    async def initialize(self):
        """Load deterministic flows"""
        try:
            await self._load_flows()
            logger.info(f"Loaded {len(self.intents)} deterministic intents")
        except Exception as e:
            logger.warning(f"Failed to load deterministic flows: {e}")
    
    async def _load_flows(self):
        """Load flow definitions from JSON files"""
        if not os.path.exists(self.flows_dir):
            logger.warning(f"Flows directory not found: {self.flows_dir}")
            return
        
        for filename in os.listdir(self.flows_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.flows_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        flow = json.load(f)
                        intent_name = flow.get('intent', filename.replace('.json', ''))
                        self.intents[intent_name] = flow
                        
                        # Extract patterns
                        if 'patterns' in flow:
                            self.patterns[intent_name] = flow['patterns']
                except Exception as e:
                    logger.error(f"Failed to load flow {filename}: {e}")
    
    async def classify(self, text: str, confidence_threshold: float = 0.85) -> Tuple[str, float]:
        """
        Classify intent using rule-based matching
        Returns (intent, confidence)
        """
        text_lower = text.lower().strip()
        
        best_intent = "general"
        best_confidence = 0.0
        
        for intent_name, patterns in self.patterns.items():
            for pattern in patterns:
                if isinstance(pattern, str):
                    # Simple substring matching
                    if pattern.lower() in text_lower:
                        confidence = min(1.0, len(pattern) / len(text_lower))
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_intent = intent_name
                elif isinstance(pattern, dict):
                    # More complex pattern matching
                    keywords = pattern.get('keywords', [])
                    required_all = pattern.get('required_all', False)
                    
                    matches = 0
                    total_keywords = len(keywords)
                    
                    for keyword in keywords:
                        if keyword.lower() in text_lower:
                            matches += 1
                    
                    if required_all and matches == total_keywords:
                        confidence = 1.0
                    elif not required_all and matches > 0:
                        confidence = matches / total_keywords
                    else:
                        confidence = 0.0
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent_name
        
        # Apply threshold
        if best_confidence < confidence_threshold:
            return "general", 0.0
        
        return best_intent, best_confidence
    
    async def get_intent_info(self, intent: str) -> Optional[Dict]:
        """Get intent configuration"""
        return self.intents.get(intent)

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        classifier = DeterministicClassifier("./flows")
        await classifier.initialize()
        
        test_texts = [
            "I need to book a restaurant reservation",
            "What's the weather like",
            "Can you help me with my order",
            "Hello, how are you"
        ]
        
        for text in test_texts:
            intent, confidence = await classifier.classify(text)
            print(f"Text: '{text}' -> Intent: {intent} (confidence: {confidence})")
    
    asyncio.run(test())