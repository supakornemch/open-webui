#!/usr/bin/env bash
# ============================================================
# LiteLLM — Local POC Setup Script
# ============================================================
# Start/stop LiteLLM proxy for token tracking & cost monitoring
#
# Prerequisites:
#   - Docker & Docker Compose
#   - Azure AI Foundry API key
#
# Usage:
#   ./scripts/litellm-poc.sh start    # Start LiteLLM
#   ./scripts/litellm-poc.sh stop     # Stop LiteLLM
#   ./scripts/litellm-poc.sh logs     # Tail logs
#   ./scripts/litellm-poc.sh status   # Check status
#   ./scripts/litellm-poc.sh test     # Test chat completion
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/config/docker-compose.litellm.yml"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---- Config ----
: "${LITELLM_MASTER_KEY:=sk-litellm-poc-master-key}"
: "${AZURE_API_BASE:=https://aif-entchat-poc-sand.cognitiveservices.azure.com}"
: "${AZURE_SEARCH_SERVICE_NAME:=srch-entchat-poc-sand}"
: "${LITELLM_PORT:=4000}"
: "${LITELLM_UI_URL:=http://localhost:$LITELLM_PORT/ui}"

# ---- Functions ----

check_azure_key() {
    if [ -z "${AZURE_API_KEY:-}" ]; then
        echo -e "${RED}❌ AZURE_API_KEY is not set.${NC}"
        echo ""
        echo "   Set it with:"
        echo "     export AZURE_API_KEY=\"your-azure-foundry-api-key\""
        echo ""
        echo "   You can find it in Azure Portal → AI Foundry → Keys"
        exit 1
    fi
    echo -e "${GREEN}✅ AZURE_API_KEY is set${NC}"

    if [ -z "${DATABASE_URL:-}" ]; then
        echo -e "${YELLOW}⚠️  DATABASE_URL not set — model persistence & token tracking disabled.${NC}"
        echo "   For Azure PG:"
        echo "     export DATABASE_URL=\"postgresql://entchatadm:DocWiseP%40ssw0rd2026%21@psql-entchat-poc-sand.postgres.database.azure.com:5432/litellm?sslmode=require\""
    fi

    if [ -z "${AZURE_SEARCH_API_KEY:-}" ]; then
        echo -e "${YELLOW}⚠️  AZURE_SEARCH_API_KEY not set — vector store search disabled.${NC}"
        echo "   Get it with:"
        echo "     az search admin-key show --service-name srch-entchat-poc-sand --resource-group RG-ENTCHAT-POC-SAND-SEA --query primaryKey -o tsv"
    fi
}

start() {
    check_azure_key

    echo -e "${BLUE}🚀 Starting LiteLLM POC...${NC}"
    echo ""

    cd "$PROJECT_DIR"
    AZURE_API_KEY="$AZURE_API_KEY" \
    AZURE_API_BASE="$AZURE_API_BASE" \
    LITELLM_MASTER_KEY="$LITELLM_MASTER_KEY" \
    DATABASE_URL="${DATABASE_URL:-}" \
    AZURE_SEARCH_API_KEY="${AZURE_SEARCH_API_KEY:-}" \
    AZURE_SEARCH_SERVICE_NAME="$AZURE_SEARCH_SERVICE_NAME" \
        docker compose -f "$COMPOSE_FILE" up -d

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ LiteLLM is running!${NC}"
    echo ""
    echo -e "   ${YELLOW}API Endpoint:${NC}     http://localhost:$LITELLM_PORT"
    echo -e "   ${YELLOW}Swagger UI:${NC}      $LITELLM_UI_URL"
    echo -e "   ${YELLOW}Master Key:${NC}      $LITELLM_MASTER_KEY"
    echo ""
    echo -e "   ${BLUE}Test it:${NC}"
    echo "     curl -s http://localhost:$LITELLM_PORT/v1/models \\"
    echo "       -H \"Authorization: Bearer $LITELLM_MASTER_KEY\" | jq ."
    echo ""
    echo -e "   ${BLUE}Point Open WebUI to LiteLLM:${NC}"
    echo "     Admin Panel → Settings → Connections → OpenAI API"
    echo "     API Base:  http://localhost:$LITELLM_PORT/v1"
    echo "     API Key:   $LITELLM_MASTER_KEY"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

stop() {
    echo -e "${YELLOW}🛑 Stopping LiteLLM POC...${NC}"
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✅ Stopped${NC}"
}

logs() {
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" logs -f litellm
}

status() {
    cd "$PROJECT_DIR"
    echo -e "${BLUE}📊 LiteLLM Status${NC}"
    echo ""
    docker compose -f "$COMPOSE_FILE" ps

    echo ""
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$LITELLM_PORT/health" 2>/dev/null | grep -q 200; then
        echo -e "${GREEN}✅ LiteLLM is healthy${NC}"

        echo ""
        echo -e "${BLUE}Available models:${NC}"
        curl -s "http://localhost:$LITELLM_PORT/v1/models" \
            -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
            2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data.get('data', []):
    print(f\"  • {m['id']}\")" 2>/dev/null || echo "  (could not fetch models — is LiteLLM ready?)"
    else
        echo -e "${RED}❌ LiteLLM is not reachable${NC}"
    fi
}

test() {
    echo -e "${BLUE}🧪 Testing chat completion with gpt-5.4-nano...${NC}"
    echo ""

    curl -s "http://localhost:$LITELLM_PORT/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
        -d '{
          "model": "gpt-5.4-nano",
          "messages": [{"role": "user", "content": "Say hello in Thai"}],
          "max_tokens": 50
        }' | python3 -m json.tool 2>/dev/null || cat

    echo ""
    echo -e "${BLUE}📊 Check token usage:${NC}"
    echo "   docker logs litellm-poc | grep -i token"
}

# ---- Main ----

case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    test)
        test
        ;;
    *)
        echo "Usage: $0 {start|stop|logs|status|test}"
        echo ""
        echo "  start   — Start LiteLLM POC"
        echo "  stop    — Stop LiteLLM POC"
        echo "  logs    — Tail LiteLLM logs"
        echo "  status  — Check health + available models"
        echo "  test    — Send a test chat completion"
        exit 1
        ;;
esac
