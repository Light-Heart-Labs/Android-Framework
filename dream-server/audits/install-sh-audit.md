# Audit Report: install.sh

**File:** `C:\Users\conta\OneDrive\Desktop\Android-Labs\dream-server\install.sh`
**Date:** 2026-02-12
**Scope:** Error handling gaps, security issues, broken logic, hardcoded values, missing validation

---

## CRITICAL

- **Line 245** -- `--tier` argument parsing does `shift 2` but never checks that `$2` exists; if `--tier` is the last argument, `TIER` is set to an empty string and the extra shift causes unexpected behavior. **Fix:** Add `[[ -z "${2:-}" ]] && error "--tier requires a value"` before assigning and shifting.

- **Line 574** -- `curl -fsSL https://get.docker.com | sh` pipes a remote script directly into `sh` with no integrity verification (no checksum, no GPG signature). A MITM or compromised CDN yields arbitrary code execution. **Fix:** Download the script first, verify its checksum against a known-good value, then execute.

- **Line 940** -- The `trap` sets an `EXIT` handler that runs `rm -rf` on a path derived from `$INSTALL_DIR`. If `INSTALL_DIR` were empty or manipulated, this could delete unintended files. The trap also overwrites any previously set handlers and persists for the entire remaining script, not just the download section. **Fix:** Validate `INSTALL_DIR` is non-empty, save/restore previous traps, and scope the trap more narrowly.

- **Lines 943-975** -- The `nohup bash -c "..."` block interpolates `$DOCKER_CMD`, `$INSTALL_DIR`, `$LLM_MODEL`, and other variables directly into a string passed to `bash -c`. If any value contains single quotes, spaces, or shell metacharacters, the command breaks or executes unintended code (shell injection). **Fix:** Write the background script to a temporary file with proper quoting, or pass variables as exported environment variables.

---

## MODERATE

- **Lines 65-66** -- Division by zero if `total` is `0` in `progress_bar()`, causing a bash arithmetic error and script abort under `set -e`. **Fix:** Add a guard: `[[ $total -eq 0 ]] && return 0`.

- **Lines 245 / 357-370** -- `--tier` value is never validated as a number at parse time; any string (e.g., `--tier foo`) passes silently and only fails later at the `case` on line 373 with a confusing error. **Fix:** Validate immediately: `[[ "$2" =~ ^[1-4]$ ]] || error "--tier must be 1-4"`.

- **Line 300** -- `source /etc/os-release` executes arbitrary shell code from that file in the installer's process; a compromised or unusual `os-release` could inject commands. **Fix:** Parse needed values with `grep`/`awk` instead of sourcing.

- **Line 358** -- Integer comparison `[[ $GPU_VRAM -ge 40000 ]]` will produce a bash error if `GPU_VRAM` is empty or non-numeric (e.g., when `detect_gpu` fails unexpectedly). **Fix:** Default to 0: `${GPU_VRAM:-0}`.

- **Line 410** -- `$((GPU_VRAM / 1024))` with `GPU_VRAM=0` displays misleading VRAM info; if `GPU_VRAM` holds a non-numeric value, bash errors out. **Fix:** Guard with a numeric check and display "N/A" when no GPU is detected.

- **Line 495** -- Minimum RAM formula `MIN_RAM=$((TIER * 16))` yields 16/32/48/64 GB for tiers 1-4, but tier 1 targets 8GB VRAM systems where 16 GB system RAM may be too aggressive, causing false warnings. **Fix:** Use a per-tier lookup table instead of a linear formula.

- **Line 577** -- `sudo usermod -aG docker $USER` relies on the `$USER` environment variable, which can be spoofed or unset. **Fix:** Use `$(whoami)` or `$(id -un)` for reliable identification.

- **Lines 585-586** -- The `read -p` prompt for `sudo docker` is outside the `$INTERACTIVE` guard; in `--non-interactive` mode with a fresh Docker install, the script hangs waiting for input. **Fix:** Wrap in `if $INTERACTIVE`, or default to `sudo docker` in non-interactive mode.

- **Lines 625-636** -- The `distribution` variable is set via a redundant subshell re-source of `/etc/os-release`, but the `case` on line 626 references `$ID`/`$VERSION_ID` from the earlier source on line 300. The redundant subshell is confusing and the two can diverge. **Fix:** Remove the subshell and derive `distribution` directly from the already-sourced variables.

- **Line 668** -- `cp -r "$SCRIPT_DIR/config"/* ... 2>/dev/null || true` silently swallows all errors including permission denied or disk full, meaning the install can produce an incomplete configuration without warning. **Fix:** Check for critical config files explicitly after copying and fail if missing.

- **Lines 716-719** -- Fallback secret generation (`head -c 32 /dev/urandom | xxd -p`) assumes `xxd` is installed. If both `openssl` and `xxd` are absent, secrets will be empty strings, leaving the installation unsecured. **Fix:** Add a third fallback (e.g., `od`), or verify the generated secret is non-empty.

- **Line 893** -- GGUF embedding model download has no integrity check (no checksum verification); a corrupted or tampered file would be silently used. **Fix:** Verify a SHA256 checksum after download.

- **Line 958** -- Nested quoting for the Python one-liner inside `bash -c` inside `nohup bash -c` is extremely fragile. The `snapshot_download` call uses escaped single quotes that break if the model name contains special characters. **Fix:** Write the Python command to a separate script file and invoke that.

- **Lines 722-767** -- The `.env` file with secrets is created with default umask before `chmod 600` is applied on line 769, leaving a brief race window where other users could read the secrets. **Fix:** Set umask before writing: `(umask 077; cat > "$INSTALL_DIR/.env" << ENV_EOF ... ENV_EOF)`.

- **Line 6 / throughout** -- `set -e` is used but many commands rely on `|| true` to suppress errors, creating an inconsistent error-handling model. Commands that should legitimately fail are silently suppressed, while commands that must hard-fail might be accidentally caught. **Fix:** Consider `set -euo pipefail` and replace blanket `|| true` with proper `if` blocks.

---

## LOW

- **Line 14** -- Log file path `/tmp/dream-server-install.log` is world-readable and predictable, enabling symlink attacks or information leakage. **Fix:** Use `mktemp` (e.g., `LOG_FILE=$(mktemp /tmp/dream-server-install-XXXXXX.log)`) and restrict permissions with `chmod 600`.

- **Line 263** -- Bare `clear` without `2>/dev/null || true` (unlike line 45) will fail and abort under `set -e` if stdout is not a terminal (e.g., piped execution). **Fix:** Change to `clear 2>/dev/null || true`.

- **Line 272** -- Splash screen hardcodes `v2.0.0` instead of using the `$VERSION` variable defined on line 11, creating a maintenance risk where the two values drift apart. **Fix:** Replace the hardcoded string with `$VERSION`.

- **Line 341** -- `grep -oP '\d+'` uses Perl regex (`-P`), which is unavailable on some systems (minimal Docker images, BSD grep). **Fix:** Use `grep -oE '[0-9]+'` for portability.

- **Line 437** -- `show_install_menu()` displays options 1/2/3 but the script never reads or acts on the menu selection; the menu is purely decorative and the script always falls through to individual prompts. **Fix:** Read the menu choice and branch accordingly (option 1 enables all, option 2 enables core only, option 3 falls through to individual prompts).

- **Line 607** -- Docker Compose v1 fallback logic `${DOCKER_CMD%-*}-compose` uses a fragile parameter expansion. **Fix:** Explicitly set `DOCKER_COMPOSE_CMD="docker-compose"` and only prepend `sudo` if needed.

- **Line 613** -- `sudo apt-get install -y docker-compose-plugin` assumes Debian/Ubuntu; this will fail on Fedora, RHEL, Arch, etc. **Fix:** Detect the package manager and use the appropriate command, or document the limitation.

- **Line 637** -- `gpg --dearmor` will fail silently (due to `|| true`) if the keyring file already exists from a previous run, leaving the NVIDIA repo unsigned. **Fix:** Add the `--yes` flag or delete the existing keyring file before writing.

- **Line 751** -- `LIVEKIT_API_KEY=dreamserver` is a hardcoded, predictable API key. If LiveKit is exposed on the network, anyone can authenticate. **Fix:** Generate a random API key like the other secrets.

- **Line 766** -- `TIMEZONE=America/New_York` is hardcoded instead of detected from the system. **Fix:** Auto-detect with `timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo "UTC"`.

- **Lines 839-841** -- `sed -i` tries to blank out `BRAVE_API_KEY`, `ANTHROPIC_API_KEY`, and `OPENAI_API_KEY` in `.env`, but these keys were never written by the generator (lines 722-767), so the sed commands are no-ops. **Fix:** Either add these keys to the template or remove the dead sed commands.

- **Lines 972-973** -- Error message correctly escapes `\$MAX_RETRIES` for the subshell, but `$DOCKER_COMPOSE_CMD` on the next line is interpolated at write-time, meaning the restart hint becomes stale if the user later changes their compose command. Minor coherence issue.

- **Line 1041** -- Dashboard URL is shown as `http://localhost:3001` but port 3001 is never defined in `.env`, never checked for availability in `PORTS_TO_CHECK` (line 536), and no service is clearly mapped to it. **Fix:** Add port 3001 to port checks and `.env`, or remove the dashboard reference.

- **Lines 1048-1049** -- Summary shows Whisper on port 9001 and TTS on port 9002, but `.env` defines them as 9000 and 8880 respectively (lines 738-739), and port checks use 9000/8880. The summary displays wrong ports. **Fix:** Use the correct port variables from `.env`.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 4     |
| MODERATE | 15    |
| LOW      | 14    |
| **Total**| **33**|

### Top priorities for remediation:
1. Fix shell injection in the nohup background download block (lines 943-975)
2. Add integrity verification for the Docker install script (line 574)
3. Validate `--tier` argument and guard against missing `$2` (line 245)
4. Scope and safeguard the `trap` handler (line 940)
5. Fix the race condition on `.env` secret file creation (lines 722-769)
