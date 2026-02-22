# Voice Pipeline Audit - dream-server

**Date:** 2026-02-12
**Scope:** livekit configs, voice agent hook, Voice.jsx, docker-compose services, deploy scripts, stress test
**Repository:** C:\Users\conta\OneDrive\Desktop\Android-Labs\dream-server

---

## CRITICAL

1. **`config\livekit\livekit.yaml`**, line 9
   **Severity:** CRITICAL
   **Description:** Hardcoded secret key `grace-livekit-dev-secret-key-32chars!` is committed to source control, constituting a credential leak.
   **Fix:** Remove the literal value and inject the secret via environment variable at deploy time (e.g., use `deploy-livekit.sh`'s templating approach with `${LIVEKIT_API_SECRET}`).

2. **`config\livekit\livekit.yaml`**, line 6
   **Severity:** CRITICAL
   **Description:** `node_ip` is hardcoded to private LAN address `192.168.0.122`, which will break any deployment not on that exact machine and cause WebRTC ICE candidates to advertise an unreachable IP.
   **Fix:** Remove the `node_ip` field entirely (let LiveKit auto-detect) or inject it via an environment variable / deploy-time template.

3. **`config\livekit\livekit.yaml`**, line 8-9 vs `docker-compose.yml` lines 373-374
   **Severity:** CRITICAL
   **Description:** The LiveKit config file uses key name `devkey` with secret `grace-livekit-dev-secret-key-32chars!`, but docker-compose passes `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` from `.env` to the voice agent. Meanwhile `compose/livekit.yaml` uses `devkey: secret` (a completely different secret). Credential mismatch will cause the voice agent to fail authentication against the LiveKit server.
   **Fix:** Ensure a single source of truth for the API key/secret pair. Generate `config/livekit/livekit.yaml` at startup from the same env vars used by the voice agent, or use `deploy-livekit.sh`'s templating pattern.

4. **`compose\livekit.yaml`**, line 12
   **Severity:** CRITICAL
   **Description:** API secret hardcoded as `devkey: secret` in plain text with no env var override mechanism. Same issue in `compose/livekit-cluster.yaml` line 14. These are referenced by alternate compose profiles that may be used in production.
   **Fix:** Use startup-time templating or a script to inject `${LIVEKIT_API_KEY}: ${LIVEKIT_API_SECRET}` as done in `deploy-livekit.sh`.

5. **`docker-compose.yml`**, lines 359-362
   **Severity:** CRITICAL
   **Description:** `livekit-voice-agent` service has `build.context: ./agents/voice` but no `agents/` directory exists anywhere in the repository (confirmed via filesystem glob). Docker build will fail immediately with "unable to prepare context".
   **Fix:** Create the `agents/voice/` directory with the agent Dockerfile and Python source, or update the build context path to point to an existing directory.

6. **`scripts\deploy-voice-agent.sh`**, line 17
   **Severity:** CRITICAL
   **Description:** `AGENT_DIR` is set to `${SCRIPT_DIR}/../agents/voice` which does not exist in the repo. The `docker build` on line 32 will fail.
   **Fix:** Align the path with the actual agent source directory, or create `agents/voice/` with the required files.

7. **`dashboard\src\hooks\useVoiceAgent.js`**, line 13
   **Severity:** CRITICAL
   **Description:** `API_BASE` fallback defaults to `http://localhost:3001` (the dashboard UI port), but the dashboard API (which serves `/api/voice/token`) runs on port 3002 (per `docker-compose.yml` line 536). All token requests and voice status checks from `useVoiceAgent` will hit the wrong service and fail.
   **Fix:** Change the fallback to `http://localhost:3002`, or unify with `Voice.jsx` line 31 which correctly falls back to `window.location.origin` (which works when the Vite dev proxy routes `/api` to 3002).

---

## MODERATE

8. **`docker-compose.yml`**, line 519
   **Severity:** MODERATE
   **Description:** `KOKORO_URL` env var on the `dashboard-api` service defaults to `http://kokoro-tts:8880` but the TTS container's Docker service name is `tts` (line 140) and its container_name is `dream-tts` (line 143). The DNS name `kokoro-tts` will not resolve on the `dream-network`.
   **Fix:** Change the default to `http://tts:8880`.

9. **`docker-compose.yml`**, line 377
   **Severity:** MODERATE
   **Description:** `STT_URL` for the voice agent is `http://whisper:9000/v1`, but the Whisper image (`onerahmet/openai-whisper-asr-webservice`) serves its API at root paths like `/asr`, not under `/v1`. The voice agent's STT requests will receive 404 responses.
   **Fix:** Change to `http://whisper:9000` (without the `/v1` suffix) and ensure the agent code uses the correct endpoint paths for this Whisper image.

10. **`docker-compose.yml`**, lines 339-340 vs `config\livekit\livekit.yaml`
    **Severity:** MODERATE
    **Description:** Docker-compose exposes port 7881 for WebRTC TCP fallback, but `config/livekit/livekit.yaml` does not define `tcp_port: 7881`. The `compose/livekit.yaml` file correctly includes it (line 8), but the config actually mounted by docker-compose (`config/livekit/livekit.yaml`) omits it. TCP-based WebRTC fallback will not function.
    **Fix:** Add `tcp_port: 7881` to the `rtc:` section of `config/livekit/livekit.yaml`.

11. **`config\livekit\livekit.yaml`**, line 5
    **Severity:** MODERATE
    **Description:** `use_external_ip: false` causes LiveKit to advertise internal Docker container IPs in SDP offers. Browsers on the host machine or LAN will be unable to establish WebRTC connections because the container-internal IP is unreachable. The cluster config (`compose/livekit-cluster.yaml` line 8) correctly uses `true`.
    **Fix:** Set `use_external_ip: true` in `config/livekit/livekit.yaml`.

12. **`dashboard\src\pages\Voice.jsx`** line 31 vs **`dashboard\src\hooks\useVoiceAgent.js`** line 13
    **Severity:** MODERATE
    **Description:** `Voice.jsx` derives `API_BASE` as `window.location.origin` (fallback `http://localhost:3002`), while `useVoiceAgent.js` derives `API_BASE` as `window.location.origin` (fallback `http://localhost:3001`). The two files in the same dashboard app use different hardcoded fallback ports, causing inconsistent behavior when env vars are not set and Vite proxy is not active.
    **Fix:** Unify both files to use the same API base URL derivation logic, ideally extracted into a shared constant or utility.

13. **`dashboard\src\hooks\useVoiceAgent.js`**, line 12
    **Severity:** MODERATE
    **Description:** `LIVEKIT_URL` defaults to `ws://` (unencrypted WebSocket). When the dashboard is served over HTTPS, browsers will block the mixed-content `ws://` connection. WebRTC signaling will fail silently or with a console error.
    **Fix:** Detect `window.location.protocol` and use `wss://` when the page is served over HTTPS (e.g., `const proto = location.protocol === 'https:' ? 'wss' : 'ws'`).

14. **`dashboard\src\hooks\useVoiceAgent.js`**, line 86
    **Severity:** MODERATE
    **Description:** `document.body.appendChild(audioElement)` appends a new HTML audio element to the DOM on every `TrackSubscribed` event but never removes it. The `TrackUnsubscribed` handler on line 92 calls `track.detach()` but does not remove the element from the DOM. Repeated connect/disconnect cycles will leak DOM nodes and potentially play orphaned audio.
    **Fix:** In the `TrackUnsubscribed` handler, also call `audioElementRef.current?.remove()` to clean up the DOM element. Also handle multiple subscriptions gracefully.

15. **`livekit.yaml`** (root), lines 1-10
    **Severity:** MODERATE
    **Description:** The root-level `livekit.yaml` only contains `agent.dispatch` and `room_defaults` configuration with no `port`, `keys`, or `rtc` block. It is not a valid standalone LiveKit server config. If any process or script accidentally mounts this file instead of `config/livekit/livekit.yaml`, the LiveKit server will fail to start.
    **Fix:** Either delete this file to avoid confusion, merge its agent dispatch settings into the canonical config under `config/livekit/`, or add a comment header warning that it is a fragment.

16. **`docker-compose.yml`**, line 388
    **Severity:** MODERATE
    **Description:** The `depends_on` for vllm has been commented out with a note about using an external `.143:8000` host, but `LLM_URL` on line 375 still defaults to `http://vllm:8000/v1` (the internal Docker service name). If vllm is not running in Docker, this URL will not resolve. If vllm is later re-enabled, the agent may start before it is healthy since the dependency is removed.
    **Fix:** Either update `LLM_URL` default to match the actual external endpoint, or restore the `depends_on` for vllm. Add retry/backoff logic in the agent for LLM connectivity.

17. **`tests\voice-stress-test.py`**, line 61
    **Severity:** MODERATE
    **Description:** LLM model name is hardcoded as `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` but the main `docker-compose.yml` defaults to `Qwen/Qwen2.5-32B-Instruct-AWQ` (the non-Coder variant). vLLM will return a model-not-found error, causing all LLM stages in the stress test to fail.
    **Fix:** Read the model name from an environment variable (e.g., `os.environ.get('LLM_MODEL', 'Qwen/Qwen2.5-32B-Instruct-AWQ')`) to match the deployed model.

18. **`tests\voice-stress-test.py`**, lines 19 and 46
    **Severity:** MODERATE
    **Description:** Whisper URL is hardcoded to `http://localhost:8001` but the main `docker-compose.yml` maps Whisper to port 9000 (`${WHISPER_PORT:-9000}:9000`). Port 8001 does not match any Whisper service definition. The STT health check and transcription requests will fail with connection refused.
    **Fix:** Change to `http://localhost:9000` or read from a `WHISPER_URL` / `WHISPER_PORT` environment variable.

19. **`scripts\deploy-voice-agent.sh`**, lines 8-13
    **Severity:** MODERATE
    **Description:** Default URLs use hardcoded IP `192.168.0.122` and non-standard ports: STT on 9101, TTS on 9102, LLM on 9100. These ports do not match any service definition in any docker-compose file (STT=9000, TTS=8880, LLM=8000). Running the script with defaults will produce connection failures for all three services.
    **Fix:** Update default ports to match docker-compose (STT=9000, TTS=8880, LLM=8000) and replace the hardcoded IP with a variable or `localhost`.

20. **`scripts\deploy-livekit.sh`**, lines 55-58
    **Severity:** MODERATE
    **Description:** Echo output tells the user to configure STT on port 9101, TTS on 9102, and LLM on 9100 at IP `192.168.0.122`. These ports do not match any service definition. Users following these printed instructions will get connection failures.
    **Fix:** Update the echo'd ports to match actual service ports (STT=9000, TTS=8880, LLM=8000) and use a variable for the IP.

---

## LOW

21. **`dashboard\src\pages\Voice.jsx`**, lines 139-140
    **Severity:** LOW
    **Description:** Dynamic Tailwind CSS class `bg-${color}-400` in the `AudioWaveform` component will be purged at build time because Tailwind's JIT compiler only detects complete class strings in source code. The waveform bars will have no background color.
    **Fix:** Use a lookup map of complete class strings (e.g., `const colorMap = { indigo: 'bg-indigo-400', red: 'bg-red-400' }`) and index into it.

22. **`dashboard\src\pages\Voice.jsx`**, line 143
    **Severity:** LOW
    **Description:** `Math.random()` is called inside the JSX render path for waveform bar heights, producing non-deterministic values on every React re-render. This causes erratic flickering rather than smooth animation.
    **Fix:** Generate the random heights once using `useMemo` or `useRef`, or drive the animation entirely via CSS keyframes.

23. **`dashboard\src\pages\Voice.jsx`**, lines 197-278
    **Severity:** LOW
    **Description:** `VoiceSettings` component manages `voice`, `speed`, and `wakeWord` in local state, but the "Save" button (line 270) just calls `onClose()` without persisting or propagating any values. All user-selected settings are silently discarded on close.
    **Fix:** Accept an `onSave` callback prop and invoke it with the current settings before closing, then wire the values into the voice agent hook or a context/store.

24. **`dashboard\src\hooks\useVoiceAgent.js`**, line 142
    **Severity:** LOW
    **Description:** `volume` is listed in the dependency array of the `connect` useCallback. Changing the volume slider creates a new `connect` function reference, which flows into `toggleListening`'s deps and may cause unnecessary re-renders or stale closure issues with the cleanup effect on line 221.
    **Fix:** Read `volume` from a ref inside the callback (e.g., `volumeRef.current`) instead of closing over the state variable.

25. **`dashboard\src\hooks\useVoiceAgent.js`**, lines 159-165
    **Severity:** LOW
    **Description:** `toggleListening` calls `await connect()` and then immediately sets `setIsListening(true)`. If `connect()` throws (caught internally, setting status to `error`), `isListening` will still be set to `true` on line 163 because the await completes (the error is caught inside `connect`). The UI will show a listening state while the connection is in error.
    **Fix:** Check `status` or the return value of `connect()` before setting `isListening(true)`, or set it inside the `RoomEvent.Connected` handler.

26. **`compose\livekit-cluster.yaml`**, lines 6-7
    **Severity:** LOW
    **Description:** RTC port range is `50000-50100` (only 100 ports) but `max_participants` is 50 per room and the config targets 20+ simultaneous conversations. Each participant can use multiple ports for ICE candidates. Under high load the port pool may be exhausted, causing ICE negotiation failures.
    **Fix:** Widen the range to match the non-cluster configs (e.g., `50000-60000`).

27. **`compose\livekit-cluster.yaml`**, line 14
    **Severity:** LOW
    **Description:** Comment says "Production keys -- override via environment" but there is no env var substitution syntax in the YAML; the key is hardcoded as `devkey: secret`. Environment override will not actually take effect without external templating.
    **Fix:** Use a startup entrypoint script that generates the YAML from env vars (as `deploy-livekit.sh` does), or use Docker Compose variable substitution in a wrapper.

28. **`docker-compose.yml`**, line 5
    **Severity:** LOW
    **Description:** `version: "3.8"` is deprecated in Docker Compose V2+ and generates a warning on every compose operation. Modern Compose infers the format automatically.
    **Fix:** Remove the `version` key entirely.

29. **`docker-compose.yml`**, line 500 (`dashboard-api` service)
    **Severity:** LOW
    **Description:** `dashboard-api` uses `network_mode: host` which bypasses the `dream-network` entirely. This means it cannot reach other services by their Docker DNS names (e.g., `tts`, `whisper`, `livekit`). It must use `localhost` and host-mapped ports, which is fragile and breaks if port mappings change.
    **Fix:** Consider removing `network_mode: host` and instead joining `dream-network` while exposing port 3002. Update internal URLs to use Docker service names.

30. **`docker-compose.yml`**, lines 127-128 (whisper service)
    **Severity:** LOW
    **Description:** Whisper is in the `default` and `voice` profiles, but the Voice services banner in `Voice.jsx` (line 123) tells users to run `docker compose --profile voice up -d`. If the user only uses `--profile voice`, the `livekit` service (which is in profiles `default` and `livekit`) will not start, and neither will `vllm` (no profile). The voice pipeline will be incomplete.
    **Fix:** Either put all voice-required services under a single `voice` profile, or update the UI instructions to specify all needed profiles.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 7     |
| MODERATE | 13    |
| LOW      | 10    |
| **Total**| **30**|

**Top priority fixes:**
1. Remove all hardcoded secrets from YAML configs (issues 1, 3, 4)
2. Create the missing `agents/voice/` directory or fix build context paths (issues 5, 6)
3. Fix the API port mismatch in `useVoiceAgent.js` (issue 7)
4. Fix the TTS service DNS name mismatch in dashboard-api (issue 8)
5. Fix the STT URL path mismatch for Whisper (issue 9)
