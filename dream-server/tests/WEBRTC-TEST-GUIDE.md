# WebRTC Voice Test Guide

**Purpose:** Validate the full voice pipeline with real audio through a browser.

Synthetic HTTP stress tests passed (100 concurrent, 100% success). This test validates:
1. WebRTC audio streaming works
2. Voice Activity Detection (VAD) triggers correctly
3. Real speech is transcribed accurately
4. LLM responses are coherent
5. TTS audio plays back in browser

## Prerequisites

- [ ] Dream Server running on .122 (or target machine)
- [ ] Dashboard accessible at `http://192.168.0.122:3001`
- [ ] Voice services healthy (check `/api/voice/status`)
- [ ] Browser with microphone access (Chrome/Firefox recommended)
- [ ] Quiet environment for testing

## Quick Health Check

```bash
# From any machine on the network
curl http://192.168.0.122:3002/api/voice/status
```

Expected response:
```json
{
  "available": true,
  "services": {
    "stt": {"name": "Whisper", "status": "healthy", "port": 9000},
    "tts": {"name": "Kokoro", "status": "healthy", "port": 8880},
    "livekit": {"name": "LiveKit", "status": "healthy", "port": 7880}
  },
  "message": "Voice ready"
}
```

## Test Procedure

### 1. Open Dashboard Voice Page

1. Navigate to `http://192.168.0.122:3001/voice`
2. Grant microphone permission when prompted
3. Verify connection status shows "Connected"

### 2. Basic Voice Test

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Click the mic button | Button turns red/active |
| 2 | Say "Hello, how are you today?" | Transcription appears in UI |
| 3 | Wait for response | LLM response + TTS playback |
| 4 | Click mic to stop | Button returns to idle |

### 3. Latency Measurement

Time the following:
- **STT latency:** End of speech → transcription appears
- **LLM latency:** Transcription appears → response text appears
- **TTS latency:** Response text → audio starts playing
- **Total E2E:** End of speech → audio starts

**Acceptable thresholds:**
- STT: < 500ms
- LLM: < 2000ms
- TTS: < 500ms
- Total E2E: < 3000ms

### 4. VAD Validation

Test voice activity detection:

| Test | Action | Expected |
|------|--------|----------|
| Silence | Stay quiet for 5s | No false triggers |
| Background noise | Type on keyboard | No false triggers |
| Soft speech | Whisper a phrase | Should trigger (or not, depending on threshold) |
| Normal speech | Speak normally | Triggers immediately |
| Interruption | Speak while TTS playing | TTS should stop |

### 5. Multi-Turn Conversation

1. Ask: "What's the capital of France?"
2. Wait for response
3. Follow up: "What's its population?"
4. Verify context is maintained (should know you're asking about Paris)

### 6. Error Handling

| Test | Action | Expected |
|------|--------|----------|
| Network drop | Disconnect WiFi mid-speech | Graceful error message |
| Long silence | Hold mic for 30s without speaking | Timeout or graceful handling |
| Very long input | Speak for 60+ seconds | Should handle or truncate gracefully |

## Recording Results

### Test Session Info

- **Date:** _______________
- **Tester:** _______________
- **Browser:** _______________
- **Network:** Local LAN / Remote / VPN

### Results

| Test | Pass/Fail | Notes |
|------|-----------|-------|
| Dashboard loads | | |
| Mic permission granted | | |
| Connection established | | |
| Basic voice works | | |
| Transcription accurate | | |
| LLM response coherent | | |
| TTS plays back | | |
| Latency acceptable | | |
| VAD no false triggers | | |
| Multi-turn works | | |
| Interruption works | | |

### Latency Measurements

| Metric | Value |
|--------|-------|
| STT | ___ms |
| LLM | ___ms |
| TTS | ___ms |
| Total E2E | ___ms |

### Issues Found

1. _______________
2. _______________
3. _______________

## Troubleshooting

### No audio input detected
- Check browser microphone permissions
- Try a different browser
- Verify mic works in other apps

### Connection failed
- Check LiveKit is running: `curl http://localhost:7880`
- Check token endpoint: `curl -X POST http://localhost:3002/api/voice/token -H "Content-Type: application/json" -d '{"room":"test","identity":"user"}'`

### Transcription wrong/empty
- Check Whisper service: `curl http://localhost:9000/health`
- Try speaking louder/clearer
- Check VAD threshold settings

### No audio playback
- Check browser audio permissions
- Verify TTS service: `curl http://localhost:8880/health`
- Check browser console for errors

### High latency
- Check GPU utilization during inference
- Verify vLLM is using GPU (not CPU)
- Check network latency if remote

---

**After testing:** Update STATUS.md with results and any issues found.
