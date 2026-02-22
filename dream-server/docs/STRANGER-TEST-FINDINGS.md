# Dream Server — Stranger Test Findings

*Todd's "10-minute install" audit — 2026-02-09*

## Test Scenario

Pretend I've never seen the codebase. Clone → follow README → working AI in 10 minutes.

---

## Friction Points Found

### 1. 🔴 QUICKSTART.md Commands Don't Exist

**Problem:** QUICKSTART says:
```bash
./setup.sh check
./setup.sh deploy
```

But `setup.sh` doesn't have `check` or `deploy` subcommands — it just wraps `install.sh`.

**Fix:** Either:
- Update QUICKSTART to say `./install.sh` (the real command)
- Or add subcommand parsing to setup.sh to match docs

---

### 2. 🟡 README vs QUICKSTART Inconsistency

**Problem:**
- README says: `./install.sh`
- QUICKSTART says: `./setup.sh`

A stranger doesn't know which to use.

**Fix:** Pick one and use it everywhere. Recommend: `./install.sh` (it's the real tool).

---

### 3. 🟡 Repo Structure Confusion

**Problem:** Users have to:
```bash
git clone https://github.com/Light-Heart-Labs/Lighthouse-AI.git
cd Lighthouse-AI/dream-server
```

Dream Server is buried in a larger repo. Strangers might not find it.

**Fix Options:**
- **A:** Create dedicated `dream-server` repo (best for marketing)
- **B:** Add prominent "Looking for Dream Server? →" in Android-Labs README
- **C:** Create installer that pulls just the dream-server folder

---

### 4. 🟡 No Model Download Progress

**Problem:** First run downloads ~20GB model. User sees:
```
Pulling vllm...
```

Then... nothing. They don't know if it's working or hung.

**Fix:** Add note in QUICKSTART: "First download takes 10-30 minutes depending on internet speed. Watch progress with `docker compose logs -f vllm`"

---

### 5. 🟢 .env Generation

**Checked:** `install.sh` generates `.env` from template ✅
No friction here.

---

### 6. 🟡 No Post-Install Validation

**Problem:** After install, how do I know it actually works?

**Fix:** Add `./dream-cli test` or `./status.sh --test` that:
1. Checks all services are up
2. Sends a test prompt to vLLM
3. Reports "✅ Dream Server is ready!"

---

### 7. 🟢 Hardware Detection

**Checked:** Auto-detects GPU, RAM, suggests tier ✅
This is good UX.

---

### 8. 🟡 No Estimated Time

**Problem:** User doesn't know how long install takes.

**Fix:** Add to top of QUICKSTART:
> **Time Estimate:** 5-10 minutes (plus 10-30 minutes for model download on first run)

---

## Priority Fixes

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 🔴 High | QUICKSTART commands wrong | 10 min | Blockers first |
| 🟡 Medium | README/QUICKSTART consistency | 15 min | Reduces confusion |
| 🟡 Medium | Post-install validation | 30 min | "It works!" confidence |
| 🟡 Low | Model download progress note | 5 min | Sets expectations |
| 🟡 Low | Time estimate | 2 min | Sets expectations |

---

## Recommended Actions

1. **Fix QUICKSTART commands** — replace `./setup.sh check/deploy` with `./install.sh`
2. **Add validation step** — `./dream-cli status --test` or similar
3. **Add time estimates** — be honest about model download
4. **Distribution decision** — separate repo vs buried in Android-Labs

---

*This is what a stranger hits. Fix these, and the 10-minute promise becomes real.*
