#!/usr/bin/env bash
# ============================================================
# Setup LiteLLM MCP Servers via REST API
# ============================================================
# LiteLLM v1.83.3 loads MCP servers from the DB, not from config.yaml.
# This script registers stdio MCP servers via POST /v1/mcp/server.
# Servers persist in DB and survive restarts.
#
# Prerequisites:
#   - LiteLLM running (local or Azure)
#   - LITELLM_BASE_URL + LITELLM_MASTER_KEY set
#
# Usage:
#   LITELLM_BASE_URL=http://localhost:4000 \
#   LITELLM_MASTER_KEY=<your-litellm-master-key> \
#   ./scripts/setup-litellm-mcp.sh
# ============================================================

set -euo pipefail

: "${LITELLM_BASE_URL:?Set LITELLM_BASE_URL, e.g. http://localhost:4000}"
: "${LITELLM_MASTER_KEY:?Set LITELLM_MASTER_KEY}"

# ponytail: postgres MCP needs DB URL as CLI arg, not env var.
# Provide the Azure PG litellm connection string via DATABASE_URL (URL-encode @ as %40, ! as %21).
DATABASE_URL="${DATABASE_URL:?set DATABASE_URL (postgresql://USER:PASS@HOST:5432/litellm?sslmode=require)}"

# ponytail: filesystem MCP needs paths that exist in the container.
# /app always exists in LiteLLM image; add more paths if mounted.
FS_PATHS="${FS_PATHS:-/tmp /app}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
fail() { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

API="${LITELLM_BASE_URL}/v1/mcp/server"
AUTH="Authorization: Bearer ${LITELLM_MASTER_KEY}"

add_server() {
  local id="$1" ; shift
  local payload
  payload=$(python3 -c "
import json, sys
args = json.loads(sys.argv[1])
print(json.dumps({
    'server_id': sys.argv[2],
    'name': sys.argv[2],
    'transport': 'stdio',
    'command': 'npx',
    'args': args
}))
" "$@" "$id")

  info "Adding MCP server: ${id}..."
  # Try POST first; if exists, PUT to update
  local resp
  resp=$(curl -sS -X POST "$API" -H "$AUTH" -H "Content-Type: application/json" -d "$payload" 2>&1)
  if echo "$resp" | grep -q "already exists"; then
    info "  ${id} exists, updating..."
    curl -sS -X PUT "$API" -H "$AUTH" -H "Content-Type: application/json" -d "$payload" >/dev/null
    ok "${id} updated"
  elif echo "$resp" | grep -q "server_id"; then
    ok "${id} added"
  else
    echo "$resp" | head -3
    fail "Failed to add ${id}"
  fi
}

info "===== LiteLLM MCP Server Setup ====="
info "API: ${API}"
echo ""

# Build args JSON for each server
add_server "postgres" "$(python3 -c "import json; print(json.dumps(['-y','@modelcontextprotocol/server-postgres','${DATABASE_URL}']))")"
add_server "filesystem" "$(python3 -c "import json; print(json.dumps(['-y','@modelcontextprotocol/server-filesystem'] + '${FS_PATHS}'.split()))")"
add_server "time" "$(python3 -c "import json; print(json.dumps(['-y','@guanxiong/mcp-server-time']))")"
add_server "context7" "$(python3 -c "import json; print(json.dumps(['-y','@upstash/context7-mcp']))")"

echo ""
info "Servers registered. LiteLLM will load them within ~30s."
info "Verify: curl -s ${LITELLM_BASE_URL}/mcp-rest/tools/list -H '$AUTH' | python3 -m json.tool"
ok "Done."
