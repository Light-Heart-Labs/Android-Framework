# Dream Server -- Tests & Security Audit

**Date:** 2026-02-12
**Scope:** tests/, test-stack.sh, test-concurrency.py, test-rag-pipeline.py, test-tool-calling.py, privacy-shield/, privacy-shield-offline/, SECURITY.md, dashboard-api/main.py
**Auditor:** Claude Opus 4.6

---

## CRITICAL Issues

- **dashboard-api/main.py, lines 46-52** -- CRITICAL -- CORS is configured with `allow_origins=["*"]` combined with `allow_credentials=True`, which is an insecure combination that exposes authenticated sessions to any origin; browsers may reject this or allow cross-origin credential theft. Fix: restrict `allow_origins` to specific dashboard origins (e.g., `["http://localhost:3001"]`) or remove `allow_credentials=True`.

- **dashboard-api/main.py, entire file** -- CRITICAL -- No authentication or authorization on any API endpoint; every route including destructive mutations (`DELETE /api/models/{model_id}`, `POST /api/update`, `POST /api/privacy-shield/toggle`, `POST /api/models/{model_id}/download`, `POST /api/models/{model_id}/load`) is completely unauthenticated and accessible to anyone who can reach port 3002. Fix: add API key or token-based auth middleware, at minimum for all mutation endpoints.

- **test-rag-pipeline.py, lines 46-51** -- CRITICAL -- `test_document_upload` returns `True` (pass) on both HTTP errors (line 47: `return True, 0.5`) and exceptions (line 51: `return True, 0.3`), so the test can never fail regardless of what happens. Fix: remove the fallback `return True` paths; failures should return `(False, 0)`.

- **privacy-shield/pii_scrubber.py, line 30** -- CRITICAL -- The `ip_address` regex `r'\b[0-9a-fA-F:]{2,}\b'` is far too broad and matches any 2+ character hex-compatible string (e.g., "ab", "ff", "de", "10", "bad", "cafe"), causing massive false positives that corrupt normal text by replacing common substrings with PII tokens. Fix: replace with a proper IPv6 regex pattern (e.g., matching full or abbreviated IPv6 notation) rather than matching any short hex string.

- **privacy-shield-offline/pii_scrubber.py, line 30** -- CRITICAL -- Identical overly-broad `ip_address` regex issue as the online version. Fix: same as above.

---

## MODERATE Issues

- **dashboard-api/main.py, no rate limiting present** -- MODERATE -- No rate limiting on any endpoint; the API is susceptible to denial-of-service by flooding any endpoint, especially expensive ones like `/api/chat`, `/api/models/{model_id}/download`, and `/api/update`. Fix: add `slowapi` or a custom rate-limit middleware.

- **dashboard-api/main.py, lines 847-848** -- MODERATE -- Hardcoded default LiveKit credentials `api_key="devkey"` and `api_secret="secret"` are used when `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` env vars are unset; these are trivially guessable and generate valid tokens. Fix: refuse to generate tokens when credentials are defaults, or require explicit env vars with no fallback.

- **dashboard-api/main.py, lines 790-808** -- MODERATE -- `DELETE /api/models/{model_id}` uses substring matching (`model_id in item.name or item.name in model_id`) to locate model directories for deletion, which could match unintended directories if model IDs share substrings, enabling deletion of wrong models. Fix: use exact match or canonicalize the model ID against the known catalog before deletion.

- **dashboard-api/main.py, line 2421** -- MODERATE -- Server binds to `0.0.0.0` (all interfaces) by default, making all unauthenticated endpoints network-accessible. Fix: bind to `127.0.0.1` by default or require explicit opt-in for network exposure via env var.

- **dashboard-api/main.py, line 2364** -- MODERATE -- Error response from `POST /api/privacy-shield/toggle` leaks full `stderr` output from docker-compose to the client, which may expose internal paths, container names, or configuration details. Fix: sanitize error messages before returning to the client.

- **test-concurrency.py, lines 181-195** -- MODERATE -- The concurrency test collects results and prints statistics but never asserts a pass/fail threshold and never returns a non-zero exit code on failure; it always exits 0 regardless of success rate. Fix: add a threshold check (e.g., `sys.exit(1)` if success rate < 80%).

- **test-tool-calling.py, lines 149-157** -- MODERATE -- The tool-calling test prints results but never returns a non-zero exit code on failure; it always exits 0. Fix: add `sys.exit(1)` when any test fails.

- **test_installer.py, lines 40-510** -- MODERATE -- Every test in this file (TestInstallerTiers, TestHardwareDetection, TestSecurityChecks, TestBootstrapMode, TestOfflineMode, TestIntegrationScenarios, TestErrorHandling, TestDownloadLogic) uses inline hardcoded values and asserts those values against themselves; no actual installer functions are imported or called. These tests verify only that Python arithmetic and string operations work, not real installer behavior. Fix: import and call actual installer logic, or mock real subprocess/system calls.

- **tests/ directory** -- MODERATE -- No tests exist for any mutation endpoint: `POST /api/models/{id}/download`, `POST /api/models/{id}/load`, `DELETE /api/models/{id}`, `POST /api/workflows/{id}/enable`, `DELETE /api/workflows/{id}`, `POST /api/update`, `POST /api/privacy-shield/toggle`, `POST /api/chat`, `POST /api/setup/persona`, `POST /api/setup/complete`. Fix: add integration tests for all write/mutation endpoints.

- **tests/ directory** -- MODERATE -- No tests validate that PII scrubbing actually works correctly; neither `test_m4_voice_shield_integration.py` nor any other test asserts that specific PII types (email, SSN, phone) are scrubbed and restored. The M4 test checks `has_placeholders` but only logs a warning, never fails. Fix: add unit tests with known PII inputs asserting expected scrubbed output.

- **privacy-shield/proxy.py, lines 36-67** -- MODERATE -- The `sessions` dictionary grows unbounded in memory with no eviction or TTL; each unique IP or auth header creates a permanent session entry containing PII mappings, eventually causing OOM on long-running deployments. Fix: add LRU eviction or TTL-based cleanup for the sessions dict.

- **privacy-shield/proxy.py, line 62** -- MODERATE -- Session key uses Python's built-in `hash()` on the Authorization header; `hash()` is not stable across Python restarts (due to hash randomization) and is collision-prone for security-sensitive keying. Fix: use `hashlib.sha256` for stable, collision-resistant session keys.

- **privacy-shield-offline/proxy.py, lines 56-86** -- MODERATE -- Same unbounded `sessions` dict and unstable `hash()` session key issues as the online version.

- **privacy-shield/pii_scrubber.py, lines 26-33** -- MODERATE -- No detection for common PII categories: names, physical addresses, dates of birth, passport numbers, or driver's license numbers. Only email, phone, SSN, IP, API keys, and credit cards are covered. Fix: add name/address detection patterns or integrate with spaCy NER for person/location entity detection.

- **privacy-shield-offline/pii_scrubber.py, lines 26-33** -- MODERATE -- Same missing PII detection categories as the online version.

---

## LOW Issues

- **dashboard-api/main.py, line 1205** -- LOW -- `workflow_executions` endpoint accepts a `limit` query parameter with no upper bound; a client could request `limit=999999999` to force n8n to return massive data. Fix: clamp `limit` to a reasonable max (e.g., 100).

- **dashboard-api/main.py, line 949** -- LOW -- `N8N_API_KEY` defaults to empty string and is passed as a header only when truthy; if unset, all n8n API calls are unauthenticated, which is fine for localhost but risky if the dashboard is network-exposed per line 2421. Fix: warn on startup if N8N_API_KEY is unset while binding to 0.0.0.0.

- **dashboard-api/main.py, line 2090** -- LOW -- The `/api/update` check action returns raw `result.stdout + result.stderr` to the client, potentially leaking internal file paths and system information. Fix: sanitize or summarize the output before returning.

- **test_installer.py, lines 59-72** -- LOW -- `test_tier_2_detection_prosumer` test name says "Tier 2: Prosumer with 12GB VRAM" but the assertion is `tier == 3` because the boundary logic puts 12GB into Tier 3; the test name is misleading. Fix: rename to "Tier 3" or adjust the boundary description.

- **test_endpoints.py, line 115** -- LOW -- `test_workflow_catalog` asserts `len(data["workflows"]) > 0`; if the workflow catalog is legitimately empty, the test fails even though the API is functioning correctly. Fix: test response structure rather than requiring non-empty content.

- **test_endpoints.py, line 135** -- LOW -- `test_workflow_categories` asserts `len(data["categories"]) > 0` which will fail when no categories are defined, even if the API is correct. Fix: validate the field exists rather than requiring content.

- **voice-stress-test.py, line 46** -- LOW -- The STT stage in the stress test substitutes a health check for actual audio transcription (`test_stt` just hits `/health`), meaning it never tests real STT performance under load. Fix: send an actual audio file for meaningful stress testing.

- **test-integration.sh, line 190** -- LOW -- Whisper is tested on port 9001 but other test files (m2-voice-test.py, test-stt-full.sh, dashboard-api/main.py) use port 9000; inconsistent port usage means tests may target the wrong service. Fix: standardize the Whisper port across all tests.

- **test_m4_voice_shield_integration.py, lines 33-36** -- LOW -- Hardcodes `192.168.0.122` as the test server IP across all URLs; this will fail on any other network without modification. Fix: use environment variables with `localhost` defaults.

- **privacy-shield-offline/proxy.py, line 109** -- LOW -- Regex `r'^https?://10\.\.\.'` has a literal triple dot instead of the intended `10\.` prefix match for the 10.x.x.x private subnet range. This means 10.x.x.x addresses are incorrectly rejected as external despite being private. Fix: change to `r'^https?://10\.'`.

- **privacy-shield/requirements.txt, lines 4-5** -- LOW -- Lists `presidio-analyzer>=2.2.0` and `presidio-anonymizer>=2.2.0` as dependencies but the code never imports or uses them; only regex-based scrubbing is implemented. This adds ~500MB to the container image for unused packages. Fix: remove unused dependencies or actually integrate Presidio for improved PII detection.

- **privacy-shield/pii_scrubber.py, line 39** -- LOW -- Uses MD5 for token hash generation; while not a direct vulnerability (used only for deterministic mapping), it signals weak cryptographic practice. Fix: use `hashlib.sha256` for consistency with modern standards.

- **privacy-shield-offline/pii_scrubber.py, line 39** -- LOW -- Same MD5 usage issue as the online version.

- **privacy-shield/Dockerfile, line 14** -- LOW -- Creates `/data` directory for "session persistence" but the application stores all session data in-memory only; data is lost on restart. Fix: either implement file-based session persistence or remove the unused directory.

- **privacy-shield/Dockerfile** -- LOW -- No `COPY --chown` used; files are copied as root before the `USER 1000:1000` directive. While functional (files are readable), using `--chown=1000:1000` on COPY provides defense-in-depth.

- **privacy-shield-offline/Dockerfile, lines 26 and 30** -- LOW -- Uses `python` instead of `python3` in HEALTHCHECK CMD and CMD; depending on the image, `python` may not be aliased correctly. Fix: use `python3` explicitly for consistency.

- **SECURITY.md, line 172** -- LOW -- Documents that "vLLM has no authentication by default" and recommends LiteLLM as gateway, but never mentions that dashboard-api (port 3002) also has no authentication and exposes destructive endpoints. Fix: add dashboard-api to the security guidance.

- **SECURITY.md** -- LOW -- No mention of the privacy shield's in-memory PII storage as a security concern; if the container is compromised, all session PII mappings (emails, SSNs, phone numbers, etc.) are exposed in plaintext in process memory. Fix: document the threat model for PII data at rest in memory.

- **test-concurrency.sh, line 50** -- LOW -- Average time per request is calculated as `TOTAL_TIME / CONCURRENT_REQUESTS` but since requests run in parallel, this metric is misleading (it divides wall-clock time by request count rather than measuring per-request latency). Fix: measure and report individual request latencies.

- **validate-agent-templates.py, line 91** -- LOW -- Template validation uses only response length (`len(content) > 50 and len(content) < 2000`) as the pass/fail criterion with no content relevance check; a gibberish response of the right length passes. Fix: add basic content validation (e.g., check for expected keywords per template type).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 5     |
| MODERATE | 14    |
| LOW      | 19    |
| **Total**| **38**|

**Top priorities:**
1. Add authentication to dashboard-api (CRITICAL)
2. Fix CORS wildcard + credentials combination (CRITICAL)
3. Fix the overly-broad IPv6/hex regex in PII scrubber -- both versions (CRITICAL)
4. Fix test-rag-pipeline.py test that can never fail (CRITICAL)
5. Add rate limiting to dashboard-api (MODERATE)
6. Add session eviction to privacy shield proxy (MODERATE)
7. Fix hardcoded LiveKit dev credentials (MODERATE)
