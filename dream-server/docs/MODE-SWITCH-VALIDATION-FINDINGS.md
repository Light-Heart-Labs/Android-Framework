# Dream Server Mode Switch — Validation Findings

**Date:** 2026-02-15  
**Discovered By:** Android-16  
**Status:** Fixes in progress

---

## Overview

Android-16 discovered 3 configuration gaps during Mode Switch validation testing. These findings prevent seamless cloud→local→hybrid transitions and need resolution before M5 Dream Server can be considered production-ready.

---

## Finding 1: Model Path Mismatch

**Issue:** The mode switch scripts reference `Qwen2.5-32B-Instruct-AWQ` but the actual model deployed on .143 is `Qwen2.5-Coder-32B-Instruct-AWQ`.

**Impact:** Mode switch fails to activate correct local model profile.

**Fix Required:**
- Update `dream-server/scripts/mode-local.sh` to reference correct model path
- Update `dream-server/scripts/mode-hybrid.sh` to reference correct model path
- Verify `dream-server/compose/local.yml` and `compose/hybrid.yml` use correct model name

**Files to Check:**
```bash
grep -r "Qwen2.5-32B-Instruct" dream-server/scripts/
grep -r "Qwen2.5-32B-Instruct" dream-server/compose/
```

---

## Finding 2: Docker Compose Command Syntax

**Issue:** Mode switch scripts use `docker-compose` (legacy Python CLI) but modern Docker installations use `docker compose` (Go-based plugin).

**Impact:** Scripts fail on systems with newer Docker versions that don't have the legacy `docker-compose` binary.

**Fix Required:**
- Update all mode switch scripts to use `docker compose` (space, not hyphen)
- Add fallback detection for legacy `docker-compose` if backward compatibility needed

**Files to Update:**
- `dream-server/scripts/mode-cloud.sh`
- `dream-server/scripts/mode-local.sh`
- `dream-server/scripts/mode-hybrid.sh`

**Example Fix:**
```bash
# Before (legacy)
docker-compose -f compose/local.yml up -d

# After (modern)
docker compose -f compose/local.yml up -d
```

---

## Finding 3: Missing Non-Interactive Flag

**Issue:** Mode switch scripts don't support `-y` / `--yes` non-interactive flag. In automation/server contexts, prompts block execution.

**Impact:** Cannot use mode switch in scripts, CI/CD, or unattended setups.

**Fix Required:**
- Add `-y` flag support to all mode switch scripts
- When `-y` is passed, skip confirmation prompts
- Default to current behavior (interactive) when flag absent

**Implementation Pattern:**
```bash
#!/bin/bash
NON_INTERACTIVE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    -y|--yes)
      NON_INTERACTIVE=true
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# Later in script...
if [[ "$NON_INTERACTIVE" == false ]]; then
  read -p "Switch to local mode? This will restart services. [y/N] " confirm
  [[ $confirm == [yY] ]] || exit 0
fi
```

---

## Verification Checklist

After fixes applied, validate:

- [ ] `dream-server mode local` activates without model path errors
- [ ] `dream-server mode hybrid` activates without model path errors
- [ ] Scripts work with both `docker-compose` and `docker compose` installations
- [ ] `dream-server mode local -y` runs without prompts
- [ ] `dream-server mode hybrid --yes` runs without prompts
- [ ] Interactive mode still prompts for confirmation (default behavior preserved)

---

## Related Documentation

- `dream-server/docs/MODE-SWITCH.md` — User-facing mode switch documentation
- `dream-server/scripts/mode-switch.sh` — Main mode switch entry point
- `dream-server/docs/WINDOWS-TROUBLESHOOTING-GUIDE.md` — May need updates if Windows Docker behavior differs

---

## Owner

**Fix Implementation:** Android-16 (zero-cost local iteration)  
**Documentation:** Todd (this document)  
**Review:** Android-17 (cloud-model architecture review before merge)

---

*Part of M1 (Zero-Cloud) → M5 (Dream Server) mission chain.*
