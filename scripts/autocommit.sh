#!/usr/bin/env bash
#!/usr/bin/env bash
set -u
INTERVAL="${AUTOCOMMIT_INTERVAL:-1800}"
SECRET_PATTERN='(?i)(sk-[a-z0-9]{32,}|ghp_[a-z0-9]{36}|AIzaSy[a-z0-9_-]{33}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'

while true; do
  sleep "$INTERVAL"
  if [[ "$(git branch --show-current)" != "main" ]]; then
    echo "[autocommit] Refusing to checkpoint outside main."
    continue
  fi

  git add -A
  if git diff --cached --quiet; then
    continue
  fi

  if git diff --cached --name-only | grep -Ei '(^|/)(\.env($|\.)|node_modules/|\.venv/|venv/|dist/|build/)|^(data|backend/data|frontend/data)/' >/dev/null; then
    echo "[autocommit] Refusing checkpoint: protected path staged."
    continue
  fi
  if git diff --cached --unified=0 | grep -Eiq "$SECRET_PATTERN"; then
    echo "[autocommit] Refusing checkpoint: secret-like content detected."
    continue
  fi

  timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  git commit -m "chore(auto): checkpoint ${timestamp}" || continue
  git push origin main || echo "[autocommit] Push failed; checkpoint remains local."
done
