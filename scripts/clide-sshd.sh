#!/usr/bin/env bash
# CLIDE SSH Server - start the agent SSH daemon
set -e

cd "$(dirname "$0")/.."

# Load .env if present
if [ -f .env ]; then
    set -a; source .env; set +a
fi

# Activate virtualenv
if [ -d nyx-env ]; then
    source nyx-env/bin/activate
fi

# Ensure forge package is importable
export PYTHONPATH="$PWD:$PYTHONPATH"

echo "Starting CLIDE SSH server on ${CLIDE_SSH_HOST:-0.0.0.0}:${CLIDE_SSH_PORT:-2222}"
exec python3 -m ssh.server
