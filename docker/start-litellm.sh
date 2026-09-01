#!/bin/sh
set -eu

nginx -t
nginx

# Start n8n in background if N8N_PORT or N8N_ENCRYPTION_KEY is defined
if [ -n "${N8N_ENCRYPTION_KEY:-}" ]; then
    echo "Starting n8n background service on port ${N8N_PORT:-5678}..."
    n8n start &
fi

exec docker/prod_entrypoint.sh "$@"