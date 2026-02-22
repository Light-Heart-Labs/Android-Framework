# Docker Compose Audit: dream-server

**Scope:** `docker-compose.yml`, `docker-compose.bootstrap.yml`, `docker-compose.edge.yml`, `docker-compose.offline.yml`
**Date:** 2026-02-12

---

## PORT CONFLICTS (between files sharing default env vars)

- **docker-compose.yml** line 23 / **docker-compose.offline.yml** line 27 -- **MODERATE** -- Both bind `${VLLM_PORT:-8000}:8000`; if both stacks are run on the same host (even on different Docker networks), the host port collides.
- **docker-compose.yml** line 78 / **docker-compose.edge.yml** line 85 / **docker-compose.offline.yml** line 132 -- **MODERATE** -- All three files bind `${WEBUI_PORT:-3000}:8080`; running any two stacks simultaneously without overriding the env var causes a bind failure.
- **docker-compose.yml** line 114 / **docker-compose.edge.yml** line 118 / **docker-compose.offline.yml** line 168 -- **MODERATE** -- Whisper port `${WHISPER_PORT:-9000}:9000` defaults collide across all three files.
- **docker-compose.yml** line 155 / **docker-compose.offline.yml** line 211 -- **MODERATE** -- TTS port `${TTS_PORT:-8880}:8880` defaults collide between standard and offline stacks.
- **docker-compose.yml** line 204 / **docker-compose.edge.yml** line 198 / **docker-compose.offline.yml** line 368 -- **MODERATE** -- n8n port `${N8N_PORT:-5678}:5678` defaults collide across three files.
- **docker-compose.yml** line 238 / **docker-compose.offline.yml** line 288 -- **MODERATE** -- Qdrant ports 6333/6334 default to the same host ports in both files.
- **docker-compose.yml** line 267 / **docker-compose.offline.yml** line 254 -- **MODERATE** -- Embeddings port `${EMBEDDINGS_PORT:-8090}:80` defaults collide between standard and offline.
- **docker-compose.yml** line 303 / **docker-compose.offline.yml** line 319 -- **MODERATE** -- LiteLLM port `${LITELLM_PORT:-4000}:4000` defaults collide.
- **docker-compose.yml** lines 339-340 / **docker-compose.offline.yml** lines 404-405 -- **MODERATE** -- LiveKit ports 7880 and 7881 defaults collide between standard and offline.

---

## SECURITY ISSUES

- **docker-compose.yml** line 523 -- **CRITICAL** -- `docker.sock` is mounted into `dashboard-api`; even though it is `:ro`, any container escape or vulnerability in the dashboard-api process grants full Docker daemon control (container creation, host filesystem access, etc.).
- **docker-compose.yml** line 507 -- **CRITICAL** -- `dashboard-api` uses `network_mode: host`, which bypasses all Docker network isolation; the container shares the host's entire network namespace, negating container segmentation.
- **docker-compose.yml** line 524 -- **MODERATE** -- `dashboard-api` mounts the entire project directory `./:/dream-server:ro`, which exposes `.env` files (containing secrets like `WEBUI_SECRET`, `LITELLM_KEY`, `LIVEKIT_API_SECRET`, `N8N_PASS`) to the container filesystem.
- **docker-compose.yml** line 71 -- **LOW** -- `OPENAI_API_KEY=not-needed` is a hardcoded dummy key; if Open WebUI leaks this value in logs or error messages it could cause confusion, and it circumvents any future validation.
- **docker-compose.offline.yml** line 116 -- **LOW** -- Same `OPENAI_API_KEY=not-needed` hardcoded dummy key issue.
- **docker-compose.offline.yml** line 65 -- **MODERATE** -- Ollama image uses `ollama/ollama:latest` (unpinned tag) while every other image across all four files is version-pinned; this breaks reproducibility and could silently introduce breaking changes.
- **docker-compose.edge.yml** line 79 -- **MODERATE** -- `WEBUI_AUTH` defaults to `false`, meaning the web UI is accessible without any authentication by default on the edge configuration.
- **docker-compose.edge.yml** line 190 -- **MODERATE** -- `N8N_BASIC_AUTH_ACTIVE` defaults to `false`, leaving the workflow automation engine completely unauthenticated on edge deployments.
- **docker-compose.offline.yml** lines 442, 313 -- **MODERATE** -- `LIVEKIT_API_KEY` and `LITELLM_KEY` fall back to static default values (`devkey`, `sk-dream-offline`) rather than using the `:?` required-variable syntax, meaning the service can silently start with insecure placeholder credentials.

---

## SERVICE DEPENDENCY ISSUES

- **docker-compose.yml** lines 385-392 -- **CRITICAL** -- `livekit-voice-agent` has a comment stating "vllm removed -- using .143:8000 externally while .122 GPU is down" but the `LLM_URL` env var defaults to `http://vllm:8000/v1` (the internal service name); if the external host is unreachable or the env var is not overridden, the agent will fail at runtime with no startup error from Docker.
- **docker-compose.yml** lines 567-568 -- **MODERATE** -- `dashboard` depends on `dashboard-api` but uses the simple form (`- dashboard-api`) instead of `condition: service_healthy`, so it can start before the API is actually ready despite the API having a healthcheck defined.
- **docker-compose.offline.yml** lines 458-466 -- **MODERATE** -- `livekit-voice-agent` depends on `vllm`, `whisper`, `tts`, and `livekit` all with `condition: service_healthy`, but all four of those services are gated behind profiles (`default`, `voice`, `livekit`); if profiles are not activated consistently, Docker Compose will error or silently skip dependencies.
- **docker-compose.yml** lines 440-442 -- **MODERATE** -- `openclaw` depends on `vllm` with `condition: service_healthy`, but `openclaw` is in the `openclaw` profile while `vllm` has no profile (always starts); this works but creates an implicit coupling that is not obvious and could break if `vllm` is ever put behind a profile.
- **docker-compose.edge.yml** lines 54-56 -- **LOW** -- `model-bootstrap` depends on `ollama` with `condition: service_healthy` but has no healthcheck of its own and no restart policy; if the `ollama pull` command fails (e.g., network issue), there is no retry mechanism and the failure is silent.

---

## VOLUME AND FILESYSTEM ISSUES

- **docker-compose.edge.yml** lines 219-225 -- **MODERATE** -- Named volumes (`ollama-models`, `ollama-data`, `webui-data`, etc.) are declared at the bottom but never referenced by any service; all services use bind mounts (`./data/...`) instead, making these volume declarations dead code that could confuse operators.
- **docker-compose.yml** line 20 / **docker-compose.offline.yml** line 24 -- **LOW** -- vLLM's model cache is mounted at `./models:/root/.cache/huggingface` but the container runs commands as root (no `user:` directive); the `read_only: true` flag is set but the volume mount itself is writable, so vLLM can write into the host's `./models` directory as root, creating files owned by root on the host.
- **docker-compose.yml** line 112 / **docker-compose.edge.yml** line 116 / **docker-compose.offline.yml** line 166 -- **LOW** -- Whisper cache volume `./data/whisper:/root/.cache` is mounted, but the container runs as `user: "1000:1000"` while the path is `/root/.cache`; unless the image remaps this path, the non-root user may lack write permissions to the cache directory.
- **docker-compose.edge.yml** line 30 -- **LOW** -- Ollama data volume mounts to `/root/.ollama` but the container is set to `user: "1000:1000"` (line 17); the non-root user will likely not have write access to `/root/.ollama` unless the image handles this.
- **docker-compose.offline.yml** lines 75-76 -- **LOW** -- Ollama volumes map `./data/ollama:/models` and `./config/ollama:/root/.ollama`, but the standard compose maps `./models/ollama:/models`; using different host paths for models between files means models downloaded in one configuration are invisible to the other.

---

## HEALTHCHECK ISSUES

- **docker-compose.yml** line 405 -- **MODERATE** -- `livekit-voice-agent` healthcheck uses `python -c "import requests; ..."` which requires the `requests` library to be installed in the container image; if the image uses `urllib` only (as the offline variant does), or `requests` is not bundled, the healthcheck will always fail and the service will be marked unhealthy.
- **docker-compose.offline.yml** line 480 -- **MODERATE** -- `livekit-voice-agent` healthcheck uses `python` and `import requests` while every other offline service healthcheck uses `python3` and `urllib.request`; this inconsistency means the agent container must have both `python` (as a symlink or separate binary) and the `requests` package, unlike all sibling containers.
- **docker-compose.offline.yml** line 93 -- **CRITICAL** -- Ollama healthcheck uses `python3 -c "import urllib.request; ..."` but the `ollama/ollama` image is a Go binary with no Python installed; this healthcheck will always fail, marking the service permanently unhealthy and blocking any dependent service (like `open-webui` on line 136).
- **docker-compose.bootstrap.yml** lines 15-20 -- **LOW** -- The bootstrap override replaces the healthcheck timing (interval/timeout/retries/start_period) but does not override the `test` command itself; the inherited `curl -f http://localhost:8000/health` from the base file will still work, but the missing explicit `test:` key makes the intent unclear and fragile.

---

## ENVIRONMENT VARIABLE GAPS

- **docker-compose.edge.yml** lines 72-81 -- **MODERATE** -- Edge `open-webui` is missing `user`, `security_opt`, `read_only`, and `tmpfs` directives that are present in the standard and offline versions, resulting in the container running as root with a writable filesystem.
- **docker-compose.edge.yml** lines 57-58 -- **LOW** -- Edge `model-bootstrap` has `OLLAMA_HOST=ollama:11434` as a plain environment variable, but the Ollama CLI expects the `OLLAMA_HOST` variable to be in the format `http://host:port`; the bare `ollama:11434` form may fail depending on the Ollama client version.
- **docker-compose.yml** line 519 -- **LOW** -- `dashboard-api` references `KOKORO_URL=http://kokoro-tts:8880` but no service named `kokoro-tts` exists in any of the four compose files; the hostname will not resolve unless an external container is manually attached to the network.
- **docker-compose.offline.yml** line 126 -- **LOW** -- `ENABLE_OLLAMA_API=false` is set in the offline Open WebUI config, but the service also sets `OLLAMA_BASE_URL=http://ollama:11434` and depends on the `ollama` service; disabling the Ollama API while depending on Ollama is contradictory.

---

## DEPRECATED / MISCELLANEOUS

- **All four files** (line 5 in each) -- **LOW** -- The `version: "3.8"` key is deprecated in Docker Compose V2 and is ignored; while harmless, it adds noise and may confuse users into thinking they are using Compose V1 file format features.
- **docker-compose.yml** line 507 -- **MODERATE** -- `dashboard-api` uses `network_mode: host` which places it outside the `dream-network`; it cannot reach other services by their Docker Compose service names (e.g., `vllm`, `livekit`) unless those services also expose ports on the host, creating an implicit requirement that all referenced services must have host-port mappings.

---

## SUMMARY

| Severity | Count |
|----------|-------|
| CRITICAL | 4     |
| MODERATE | 22    |
| LOW      | 12    |
| **Total**| **38**|
