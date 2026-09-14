#!/bin/bash
set -euo pipefail

# Only do work in Claude Code on the web; local sessions are untouched.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# --- server (Python) ---
if [ ! -x "server/.venv/bin/python" ]; then
  python3.12 -m venv server/.venv
fi
server/.venv/bin/pip install --upgrade pip
server/.venv/bin/pip install -e './server[dev]'

# --- web (TypeScript/React) ---
( cd web && npm install )

{
  echo "export PATH=\"$CLAUDE_PROJECT_DIR/server/.venv/bin:\$PATH\""
} >> "$CLAUDE_ENV_FILE"
