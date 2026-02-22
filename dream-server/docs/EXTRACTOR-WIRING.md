# Entity Extractor Wiring Pattern

## Overview

This document describes the entity extractor wiring pattern implemented in the M4 deterministic voice agent layer.

## Architecture

### Problem

Previously, entity extractors were defined in `livekit_adapter.py` and the FSM had a placeholder for entity extraction that simply stored raw text instead of properly extracting entities.

### Solution

1. **Centralized extractors module** (`deterministic/extractors.py`)
   - All extractor functions moved to a single module
   - Consistent API: `extractor(text: str) -> Optional[Any]`
   - Returns captured value or `None` if no match found

2. **Extractor registry pattern**
   - `DEFAULT_EXTRACTORS` dict maps entity types to extractor functions
   - FSMExecutor accepts extractors via constructor
   - Enables extensibility and testability

3. **Proper entity capture in FSM**
   - Uses registered extractors to capture entities from utterances
   - Falls back gracefully if no extractor found (no raw text fallback)

## Extractor Types

| Entity Type | Description | Return Value |
|-------------|-------------|--------------|
| `date` | Date references (today, tomorrow, weekday) | String or `None` |
| `time` | Time references (12:30 PM, afternoon) | String or `None` |
| `time_preference` | Time of day preference | `'morning'`, `'afternoon'`, `'evening'`, or `None` |
| `name` | User's name (my name is X) | Capitalized string or `None` |
| `phone` | Phone numbers | Formatted string or `None` |
| `email` | Email addresses | String or `None` |
| `yes_no` | Yes/no answers | `True`, `False`, or `None` |
| `number` | Integer values | Integer or `None` |

## Usage

### Creating FSM with Extractors

```python
from deterministic import FSMExecutor
from deterministic.extractors import DEFAULT_EXTRACTORS

# Create FSM with default extractors
fsm = FSMExecutor(
    flows_dir="./flows",
    extractors=DEFAULT_EXTRACTORS
)
```

### Custom Extractors

```python
from deterministic import FSMExecutor

def extract_custom_entity(text: str) -> Optional[str]:
    # Your custom extraction logic
    pass

custom_extractors = {
    "custom": extract_custom_entity,
    **DEFAULT_EXTRACTORS,  # Include defaults
}

fsm = FSMExecutor(
    flows_dir="./flows",
    extractors=custom_extractors
)
```

### Flow Definition with Entity Capture

```json
{
  "name": "hvac_service",
  "initial_state": "S1_greeting",
  "states": {
    "S2_gather_info": {
      "say": "ask_name",
      "capture": {
        "customer_name": "name",
        "phone": "phone"
      },
      "expect": ["provide_name"],
      "next": {
        "provide_name": "S3_confirm"
      }
    }
  }
}
```

## Files Modified

1. **CREATE**: `agents/voice/deterministic/extractors.py`
   - New module with all extractor functions
   - `DEFAULT_EXTRACTORS` registry dict

2. **MODIFY**: `agents/voice/deterministic/fsm.py`
   - Added `extractors` parameter to `__init__`
   - Updated `process_intent()` to use extractor registry
   - Removed raw text placeholder

3. **MODIFY**: `agents/voice/deterministic/livekit_adapter.py`
   - Removed duplicate extractor function definitions
   - Imports extractors from `deterministic.extractors` module
   - Re-exports `DEFAULT_EXTRACTORS` for backward compatibility

4. **MODIFY**: `agents/voice/agent_m4.py`
   - Imports `DEFAULT_EXTRACTORS` from extractors module
   - Passes extractors to FSMExecutor constructor

5. **MODIFY**: `agents/voice/test_server.py`
   - Imports `DEFAULT_EXTRACTORS` from extractors module
   - Passes extractors to FSMExecutor constructor

## Testing

Run the test server to verify extractor wiring:

```bash
python agents/voice/test_server.py
```

Test utterances with extractable entities:

```bash
curl -X POST http://localhost:8290/test/utterance \
  -H "Content-Type: application/json" \
  -d '{"utterance": "my name is John Smith", "session_id": "test-1"}'
```

Expected response:
```json
{
  "intent": "provide_name",
  "confidence": 0.92,
  "deterministic": true,
  "response": "Great, John. I've captured your name.",
  "latency_ms": 45.3,
  "flow_active": true
}
```

## Benefits

1. **Separation of concerns**: Extractors are independent from adapter logic
2. **Reusability**: Same extractors used across different components
3. **Testability**: Extractors can be tested in isolation
4. **Extensibility**: Easy to add new extractor types
5. **Maintainability**: Single source of truth for entity extraction logic

## Migration Guide

### Old Code

```python
# Extractors defined in livekit_adapter.py
from deterministic.livekit_adapter import LiveKitFSMAdapter

# FSM had raw text fallback
fsm = FSMExecutor(flows_dir)
adapter = LiveKitFSMAdapter(fsm, classifier)
```

### New Code

```python
# Import extractors from dedicated module
from deterministic.extractors import DEFAULT_EXTRACTORS

# Pass extractors to FSM
fsm = FSMExecutor(flows_dir, extractors=DEFAULT_EXTRACTORS)
adapter = LiveKitFSMAdapter(fsm, classifier, entity_extractors=DEFAULT_EXTRACTORS)
```

## Backward Compatibility

- `DEFAULT_EXTRACTORS` is still re-exported from `livekit_adapter` module
- Existing imports continue to work
- New code should import from `deterministic.extractors` directly
