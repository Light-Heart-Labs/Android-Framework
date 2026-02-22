#!/bin/bash
# scrub-livekit-secrets.sh
# Removes hardcoded LiveKit secrets from git history using BFG Repo-Cleaner
# WARNING: This rewrites history - all collaborators must reclone
#
# Usage: ./scripts/scrub-livekit-secrets.sh [secrets-file]
#   secrets-file: Path to file containing secrets (one per line)
#   Defaults to .secrets-to-scrub in repo root (must be in .gitignore)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SECRETS_FILE="${1:-${REPO_ROOT}/.secrets-to-scrub}"

echo "=== LiveKit Secrets Git History Scrub ==="
echo "WARNING: This will rewrite git history!"
echo ""

# Validate secrets file exists
if [[ ! -f "$SECRETS_FILE" ]]; then
    echo "ERROR: Secrets file not found: $SECRETS_FILE"
    echo ""
    echo "Create a file with secrets to scrub (one per line):"
    echo "  echo 'your-secret-key' > .secrets-to-scrub"
    echo "  echo 'another-secret' >> .secrets-to-scrub"
    echo ""
    echo "IMPORTANT: Add .secrets-to-scrub to .gitignore!"
    exit 1
fi

# Load secrets from file - handle NUL bytes and long lines safely
if [[ ! -s "$SECRETS_FILE" ]]; then
    echo "ERROR: Secrets file is empty: $SECRETS_FILE"
    exit 1
fi

# Read file line by line safely, handling potential NUL bytes
SECRETS=()
while IFS= read -r -d $'\n' line || [[ -n "$line" ]]; do
    # Skip NUL bytes and empty lines
    if [[ -n "$line" ]] && [[ "$line" != *$'\0'* ]]; then
        SECRETS+=("$line")
    fi
done < "$SECRETS_FILE"

# Validate secrets were loaded
if [[ ${#SECRETS[@]} -eq 0 ]]; then
    echo "ERROR: No secrets found in $SECRETS_FILE"
    exit 1
fi

echo "Secrets to remove from history (loaded from $SECRETS_FILE):"
for secret in "${SECRETS[@]}"; do
    if [[ -n "$secret" ]]; then
        echo "  - ${secret:0:20}..."
    fi
done
echo ""

# Check if BFG is installed
if ! command -v bfg &> /dev/null; then
    echo "BFG not found. Installing..."
    
    # Download BFG
    BFG_VERSION="1.14.0"
    BFG_JAR="bfg-${BFG_VERSION}.jar"
    BFG_URL="https://repo1.maven.org/maven2/com/madgag/bfg/${BFG_VERSION}/${BFG_JAR}"
    
    if [[ ! -f "/tmp/${BFG_JAR}" ]]; then
        curl -L -o "/tmp/${BFG_JAR}" "${BFG_URL}"
    fi
    
    # Create wrapper script
    cat > /tmp/bfg << 'EOF'
#!/bin/bash
java -jar /tmp/bfg-1.14.0.jar "$@"
EOF
    chmod +x /tmp/bfg
    export PATH="/tmp:$PATH"
fi

echo "Creating sensitive-data.txt..."
> /tmp/sensitive-data.txt
for secret in "${SECRETS[@]}"; do
    if [[ -n "$secret" ]]; then
        echo "${secret}" >> /tmp/sensitive-data.txt
    fi
done

echo ""
echo "Files that will be scrubbed:"
git log --all --pretty=format: --name-only | sort -u | grep -E "(livekit|config)" || true
echo ""

echo "Step 1: Create backup branch"
git branch backup-before-secret-scrub-$(date +%Y%m%d) || true

echo ""
echo "Step 2: Run BFG to remove secrets"
echo "Command: bfg --replace-text /tmp/sensitive-data.txt"

# Run BFG
cd "$REPO_ROOT"
bfg --replace-text /tmp/sensitive-data.txt

echo ""
echo "Step 3: Clean up and garbage collect"
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "=== Scrub Complete ==="
echo ""
echo "NEXT STEPS:"
echo "1. Review changes: git log --oneline -5"
echo "2. Force push: git push --force-with-lease origin main"
echo "3. Notify all collaborators to reclone the repo"
echo "4. Rotate any exposed LiveKit credentials immediately"
echo "5. Delete $SECRETS_FILE when done"
echo ""
echo "Backup branch created: backup-before-secret-scrub-$(date +%Y%m%d)"
