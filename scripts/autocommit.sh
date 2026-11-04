#!/usr/bin/env bash
# Autocommit daemon for Lumen
# Loops every INTERVAL seconds (default 1800 = 30m)
# Performs secret check, commits changes, and pushes to remote.

INTERVAL="${AUTOCOMMIT_INTERVAL:-1800}"

echo "Starting Lumen autocommit loop (interval: ${INTERVAL}s)..."

while true; do
    sleep "$INTERVAL"
    
    # Check for secret patterns in staged changes before committing
    if git status --porcelain | grep -q '^[MARCD]'; then
        # Check for actual token patterns (Gemini, OpenAI, GitHub, Private Keys)
        if git diff --cached | grep -iE '(sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36}|AIzaSy[a-zA-Z0-9_-]{33}|BEGIN [A-Z ]*PRIVATE KEY)' > /dev/null 2>&1; then
            echo "[autocommit] [WARNING] Real secret pattern detected in staged changes! Aborting commit."
            continue
        fi

        TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        echo "[autocommit] [${TIMESTAMP}] Staging and committing changes..."
        git add -A
        git commit -m "chore(auto): checkpoint ${TIMESTAMP}" || true
        git push origin main || echo "[autocommit] [WARNING] git push failed"
    else
        echo "[autocommit] [$(date -u +"%Y-%m-%dT%H:%M:%SZ")] No changes to commit."
    fi
done
