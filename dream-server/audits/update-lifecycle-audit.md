# Dream Server Update & Lifecycle Audit

**Scope:** `dream-update.sh`, `dream-backup.sh`, `dream-restore.sh`, `migrations/`, `manifest.example.json`, `manifest.example-major.json`
**Date:** 2026-02-12
**Focus areas:** Update flow safety, rollback correctness, migration ordering/idempotency, version comparison bugs, backup completeness, data loss scenarios, error handling gaps, race conditions.

---

## dream-update.sh

- **Line 81** | **CRITICAL** | The `-v`/`--version` flag does not validate that `$2` exists; if the user runs `dream-update.sh -v` with no following argument, `shift 2` will either fail under `set -u` or silently assign the next flag as the version string. **Fix:** Guard with `[[ -z "${2:-}" ]]` check before assignment.

- **Lines 484-487** | **CRITICAL** | Version comparison uses simple string equality (`==`) instead of semantic version comparison; version `2.1.0` is not recognized as newer than `2.0.9`, and a `v` prefix on the GitHub tag (e.g., `v2.1.0` vs `2.1.0`) will cause every run to believe an update is available. **Fix:** Strip leading `v` from both versions and implement a proper semver comparison function.

- **Lines 525-529** | **CRITICAL** | The comment says "Don't rollback on migration failure -- we haven't changed anything yet", but migrations DO mutate state: `migrate-v0.2.0.sh` appends to `.env`. If a migration partially succeeds (first variable added, second fails), the system is left dirty with no rollback attempt. **Fix:** Trigger rollback from backup on migration failure.

- **Line 100** | **CRITICAL** | `get_latest_version()` parses the GitHub API response with a fragile `grep`/`sed` pipeline and does not strip a leading `v` prefix from the tag. If the repo tags versions as `v2.1.0`, the version string will never match the `.version` file format, causing every run to detect a false update. **Fix:** Add `sed 's/^v//'` to normalize the version tag.

- **Line 211** | **MODERATE** | `migrations_url` is constructed but never used for directory listing -- the manifest drives the list of migrations. This is dead code that could mislead future maintainers. **Fix:** Remove the unused variable.

- **Lines 225-245** | **MODERATE** | Migration scripts are downloaded from the internet and executed immediately (`chmod +x` then run) with no integrity verification (no checksum, no signature). A compromised CDN or MITM could inject arbitrary code. **Fix:** Add SHA-256 checksum verification from the manifest before executing.

- **Lines 138-154** | **MODERATE** | `needs_migration()` only checks whether major or minor versions differ. A downgrade (e.g., `3.0.0` to `2.0.0`) will trigger upgrade-only migrations, which could corrupt data. There is no downgrade guard anywhere. **Fix:** Assert `to_version > from_version` and abort or warn on downgrade.

- **Manifest integration (no specific line)** | **MODERATE** | The manifest's `min_version` field (e.g., `"min_version": "2.5.0"` in `manifest.example-major.json`) is never read or enforced. A user on `1.0.0` could jump to `3.0.0`, skipping required intermediate migrations. **Fix:** Read `min_version` from the manifest and abort if `current_version` is below it.

- **Manifest integration (no specific line)** | **MODERATE** | The manifest's `pre_update_warning` and `breaking_changes` fields are never read or displayed. Users get no warning before a major breaking update. **Fix:** Parse and display these fields, requiring explicit confirmation for breaking changes.

- **Lines 363-364** | **LOW** | Health check waits a fixed 10 seconds, which may be too short for heavy containers (e.g., Qdrant loading a large index). **Fix:** Use a polling loop with exponential backoff up to a configurable timeout.

- **Line 453** | **LOW** | `trap cleanup EXIT` is set inside `main()`, so if an error occurs before that line (e.g., during argument parsing that creates temp files), cleanup will not fire. **Fix:** Move the trap to the top-level scope before `main` is called.

---

## dream-backup.sh

- **Lines 169-179** | **CRITICAL** | `rsync -a --delete` is used to copy data into the backup directory. The `--delete` flag removes files in the destination not present in the source. If a backup directory is reused (e.g., same-second timestamp in a fast loop), it could silently destroy data from a prior backup run. **Fix:** Remove `--delete` for backup operations; it is only appropriate for restore.

- **Lines 155-180** | **MODERATE** | Data is copied while containers are running, so databases (Qdrant, n8n SQLite) may be in an inconsistent state due to torn writes. The script never stops or pauses containers before copying. **Fix:** Offer a `--stop-containers` option or use `docker exec` to trigger application-level flushes before copying.

- **Lines 238-260** | **MODERATE** | Retention policy uses `find ... -name "*-*-*"` which could match non-backup directories. `sort -z -r` sorts on the full path, not the basename, so ordering may be wrong if `BACKUP_ROOT` is overridden. **Fix:** Sort on basename only and use a stricter pattern like `[0-9]*-[0-9]*`.

- **Lines 263-280, 323-329** | **MODERATE** | `apply_retention()` runs before `compress_backup()` in `do_backup()`. Retention scans for directories but compressed `.tar.gz` backups are files, so compressed backups are never counted by retention and accumulate without limit. **Fix:** Run `apply_retention` after compression and have retention also scan for `.tar.gz` files.

- **Lines 188-194** | **MODERATE** | The config backup list does not include `dream-backup.sh` or `dream-restore.sh` themselves. After a restore, you may have mismatched script versions relative to the restored data. **Fix:** Add all `dream-*.sh` scripts to the config backup list.

- **Lines 126-150** | **LOW** | The backup manifest is built via string interpolation in a heredoc, not via `jq`. If `description` or `hostname` contain double quotes or backslashes, the resulting JSON will be malformed. **Fix:** Use `jq` to build the manifest JSON safely.

---

## dream-restore.sh

- **Lines 256-268** | **CRITICAL** | `rsync -a --delete` during restore deletes data in the target directory not present in the backup. If a backup is of type `user-data` (which omits some service directories), restoring it will silently wipe service data that was not included in the backup. **Fix:** Only use `--delete` for `full` backup restores, or remove `--delete` entirely and warn about leftover files.

- **Lines 356-359, 411** | **CRITICAL** | The `-s` flag is mapped to `--stop-containers`, but `dream-update.sh` line 415 invokes `dream-restore.sh -f -s "$BACKUP_ID"` relying on specific argument ordering. If positional parsing order changes, `$BACKUP_ID` could be consumed as a flag value. **Fix:** Use long flags explicitly in the update script (`--force --stop-containers`).

- **Lines 319-380** | **MODERATE** | `do_restore()` does not create a safety backup of the current state before overwriting. If the restore itself fails partway (e.g., disk full after first rsync), the system is left in a half-restored, half-current state with no recovery path. **Fix:** Create an automatic pre-restore snapshot.

- **Lines 295-316** | **LOW** | `verify_restore()` always returns 0 even when critical paths are missing (lines 314-315), so the restore reports success even when verification found problems. **Fix:** Return 1 when critical paths are missing.

- **Lines 240-253** | **LOW** | `stop_containers()` greps `docker compose ls --quiet` for the directory basename. If `COMPOSE_PROJECT_NAME` was overridden, this check fails to find running containers and silently skips the stop. **Fix:** Use `docker compose -f "$DREAM_DIR/docker-compose.yml" ps -q` instead.

---

## migrations/migrate-v0.2.0.sh

- **Line 10** | **CRITICAL** | The script references `$INSTALL_DIR` which is never set or exported by the caller (`dream-update.sh`). `dream-update.sh` uses `DREAM_DIR`, not `INSTALL_DIR`. Under the script's `set -e` (without `set -u`), `INSTALL_DIR` expands to empty, making `ENV_FILE="/.env"`. Since `/.env` does not exist, the entire migration silently does nothing. **Fix:** Have `dream-update.sh` export `INSTALL_DIR="$DREAM_DIR"` before calling migration scripts, or update migrations to use `DREAM_DIR`.

- **Line 6** | **MODERATE** | Uses `set -e` but not `set -u` or `set -o pipefail`, inconsistent with the parent scripts. Unset variable references silently expand to empty rather than failing. **Fix:** Use `set -euo pipefail` for consistency.

- **Lines 1-29** | **MODERATE** | There is no migration state tracking. `dream-update.sh` has no record of which migrations have completed, so a re-run of the update will re-execute all migrations blindly. The README mentions a `.migration-state` file, but this is never implemented. **Fix:** Implement migration state tracking as described in the README.

---

## manifest.example.json

- **Line 4** | **MODERATE** | `min_version` is `2.0.0` and `version` is `2.1.0` (a minor bump), but the migrations array is empty and the notes say "patch release". The `needs_migration()` function in `dream-update.sh` would flag this as requiring migration (minor version changed) but find no migration scripts, creating contradictory signals. **Fix:** Align `needs_migration()` logic with the manifest: if the manifest declares no migrations, skip them regardless of version delta.

---

## manifest.example-major.json

- **Lines 26-28** | **MODERATE** | Migration scripts listed in the manifest (`migrate-v2-to-v3-database.sh`, `migrate-v2-to-v3-env.sh`) do not exist in the `migrations/` directory. There is no pre-flight validation that referenced migration scripts can be downloaded before the update begins. A user attempting this update would fail mid-flight after state has already been modified. **Fix:** Validate all migration scripts exist (or are downloadable) before beginning any destructive state changes.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 8     |
| MODERATE | 14    |
| LOW      | 5     |
| **Total**| **27**|

### Top-priority items requiring immediate attention

1. **Migration environment variable mismatch** (`migrate-v0.2.0.sh` line 10) -- all migrations are silently no-ops because `INSTALL_DIR` is never set by the caller.
2. **No rollback on migration failure** (`dream-update.sh` lines 525-529) -- partial migration leaves system dirty.
3. **Restore with `--delete` can wipe non-backed-up data** (`dream-restore.sh` lines 256-268) -- data loss on partial-type restores.
4. **Version comparison is string-only** (`dream-update.sh` lines 484-487) -- false positives on `v`-prefixed tags, no semver ordering.
5. **`min_version` is never enforced** -- users can skip required intermediate migrations.
6. **`rsync --delete` in backup** (`dream-backup.sh` lines 169-179) -- destructive flag is inappropriate for backup operations.
7. **No integrity checks on downloaded migration scripts** (`dream-update.sh` lines 225-245) -- remote code execution risk.
8. **Backup runs against live databases** (`dream-backup.sh` lines 155-180) -- potential for inconsistent snapshots.
