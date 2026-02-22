# M4 Deterministic Voice Agent

Mission 4 implementation: Reduces LLM dependence through intent classification and deterministic routing.

## Quick Start

```bash
# Run with deterministic layer enabled
DETERMINISTIC_ENABLED=true python agent_m4.py dev

# Run without deterministic layer (baseline)
DETERMINISTIC_ENABLED=false python agent_m4.py dev
```

## How It Works

```
User Speech → STT → Intent Classifier → [Decision]
                                          ↓
                              ┌───────────┴───────────┐
                         High conf (≥0.85)      Low conf (<0.85)
                              ↓                       ↓
                         FSM Executor              LLM Fallback
                         (Deterministic)          (Full model)
                              ↓                       ↓
                              └───────────┬───────────┘
                                          ↓
                                        TTS → User
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DETERMINISTIC_ENABLED` | `true` | Enable M4 layer |
| `DETERMINISTIC_THRESHOLD` | `0.85` | Confidence threshold for routing |
| `FLOWS_DIR` | `./flows` | Directory containing flow definitions |

## Architecture

### Components

1. **Intent Classifier** (`deterministic/classifier.py`)
   - `KeywordClassifier` — Rule-based (current)
   - `DistilBERTClassifier` — Neural (placeholder for Todd's research)
   - `QwenClassifier` — LLM-based (structured output)

2. **FSM Executor** (`deterministic/fsm.py`)
   - JSON flow definitions
   - State machine execution
   - Entity capture
   - Template-based NLG

3. **Deterministic Router** (`deterministic/router.py`)
   - Routes requests: FSM vs LLM
   - Confidence-based decision
   - Metrics collection

### Integration Hook

The `before_llm` method in `M4VoiceAgent` intercepts requests:

```python
async def before_llm(self, text: str) -> Optional[str]:
    decision = await self.router.route(text, context, session_id)
    
    if decision.target == RoutingTarget.DETERMINISTIC:
        return decision.response_text  # Skip LLM
    
    return None  # Continue to LLM
```

## Flow Definitions

Example HVAC service flow:

```json
{
  "name": "hvac_service",
  "initial_state": "S1_greeting",
  "states": {
    "S1_greeting": {
      "say": "welcome_message",
      "expect": ["schedule_service", "emergency"],
      "next": {
        "schedule_service": "S2_gather_info",
        "emergency": "S1_emergency"
      }
    }
  },
  "templates": {
    "welcome_message": "Hello! How can I help?"
  }
}
```

## Metrics

The router tracks:
- Total routes
- Deterministic vs fallback rate
- Average latency
- Intent distribution

Access via logs or `router.get_metrics()`.

## Performance Targets

| Metric | Baseline (LLM) | M4 Target | Improvement |
|--------|---------------|-----------|-------------|
| Latency | 1000ms | 560ms | 1.8x faster |
| LLM Calls | 100% | 20% | 80% reduction |
| Accuracy | 98% | 95% | 3% tradeoff |

## Future Work

1. Replace `KeywordClassifier` with Todd's DistilBERT
2. Add more domain flows (restaurant, tech support)
3. Implement A/B testing framework
4. Add visual flow editor

## Files

- `agent_m4.py` — M4-enabled voice agent
- `deterministic/` — Core deterministic layer
- `flows/` — Conversation flow definitions

## Mission Connection

- **M4:** Deterministic Voice Agents (primary)
- **M2:** Voice Agents (integration)
- **M5:** Dream Server (product feature)
