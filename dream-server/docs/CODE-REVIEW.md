# Dream Server — Code Review Results

*Reviewed by: Claude Code via Todd*
*Date: 2026-02-09*

---

## 1. Executive Summary

### Overall Assessment: **Needs Work Before Release**

This is an impressive turnkey local AI stack with excellent hardware guidance and clear documentation. The project demonstrates strong product thinking and user empathy. However, there are **critical security and robustness issues** that must be addressed before public release.

### Top 3 Strengths

1. **Outstanding Hardware Guidance** — The HARDWARE-GUIDE.md is exceptionally valuable, providing real-world performance data and specific buying recommendations across budget tiers.

2. **Progressive Disclosure UX** — The tiered approach (setup.sh for quick start, install.sh for full wizard) with optional profiles shows excellent understanding of different user needs.

3. **Clean Architecture** — Docker Compose with profiles, health checks, and proper service dependencies demonstrates solid infrastructure thinking.

### Top 3 Concerns

1. **Security — Hardcoded Default Passwords** — Multiple services use obvious default passwords like "changeme" and "dreamserver".

2. **Missing Critical File** — docker-compose.yml references `/data/hermes_tool_template.jinja` which doesn't exist.

3. **Inconsistent Installation Flows** — Two separate installers with overlapping functionality creates confusion.

---

## 2. Critical Issues (Must Fix Before Release)

### 2.1 Missing File: hermes_tool_template.jinja
- **Location:** docker-compose.yml:31
- **Impact:** vLLM container will fail to start with tool-calling enabled
- **Fix:** Include the template file or remove the chat-template argument

### 2.2 Hardcoded Insecure Passwords
- **Locations:** docker-compose.yml:58, 118, 155 and install.sh:474
- **Impact:** Immediate security compromise if exposed to network
- **Fix:** Force secret generation on first run, add prominent warnings

### 2.3 install.sh Generates Incompatible docker-compose.yml
- **Impact:** Users following QUICKSTART.md will have different setup than install.sh users
- **Fix:** Make install.sh copy/configure existing docker-compose.yml instead of generating one

### 2.4 No Validation of .env.example Existence
- **Impact:** User gets cryptic errors when Docker Compose tries to use undefined variables
- **Fix:** Add explicit check before copy

### 2.5 Docker Installation May Require Re-login
- **Impact:** Subsequent docker commands fail with permission errors
- **Fix:** Check group membership and prompt user

### 2.6 Race Condition in Health Checks
- **Impact:** False negatives where healthy services report as failed
- **Fix:** Check container status before URL health check

### 2.7 Port Conflicts Not Handled
- **Impact:** Services fail to start if ports are in use
- **Fix:** Pre-flight port availability check

---

## 3. Important Improvements (Should Fix)

1. Add error handling/traps in bash scripts
2. Improve GPU detection parsing robustness
3. Add model download progress visibility
4. Validate VRAM vs model size
5. Check Docker Compose version
6. Standardize Whisper port (9000 vs 9001 inconsistency)
7. Add backup/migration documentation
8. Add resource limits to containers
9. Add log rotation
10. Use sed with backup in setup.sh

---

## 4. Nice to Have (v1.1)

- Interactive model selection
- Monitoring/observability (Prometheus + Grafana)
- Automatic update checker
- Web-based setup UI
- Multi-model documentation
- Rate limiting via nginx
- TLS/HTTPS support
- Cloud backup integration
- Performance benchmarking
- Community model registry

---

## 5. Documentation Gaps

1. **Missing TROUBLESHOOTING.md** (referenced but doesn't exist)
2. No upgrade path documented
3. Incomplete n8n workflow files (05-scheduled-summarizer.json missing)
4. No security best practices doc
5. No performance tuning guide
6. Unclear data persistence documentation
7. No contributing guidelines
8. **LICENSE file missing** (README says MIT)
9. No FAQ
10. OpenClaw config examples missing

---

## 6. Summary of Critical Path to v1.0

### Must Fix (Blocking)
1. ✅ Add missing hermes_tool_template.jinja or remove reference
2. ✅ Fix default passwords — generate on first run
3. ✅ Create TROUBLESHOOTING.md
4. ✅ Reconcile install.sh vs setup.sh inconsistencies
5. ✅ Add error handling to bash scripts

### Should Fix (High Priority)
6. ✅ Add port conflict detection
7. ✅ Improve GPU detection robustness
8. ✅ Add .env.example validation
9. ✅ Fix Docker group membership handling
10. ✅ Add resource limits to containers

### Documentation (Complete)
11. ✅ Add LICENSE file
12. ✅ Create SECURITY.md
13. ✅ Add missing n8n workflow or remove reference
14. ✅ Add OpenClaw config examples

---

## Final Recommendation

**Very strong v0.9** that needs focused work on security and robustness for **solid v1.0**.

**Estimated work to ship:** 2-3 days for critical fixes, 1 week for high-priority improvements.

**The biggest wins:**
1. Fix security defaults (2 hours)
2. Consolidate installers (1 day)
3. Add missing files and docs (1 day)

**Ship it** (after fixes)! 🚀
