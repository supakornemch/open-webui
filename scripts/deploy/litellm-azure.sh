#!/usr/bin/env bash
# ============================================================
# Deploy LiteLLM to Azure Web App — app-litellm-poc-sand
# ============================================================
# Prerequisites:
#   - az cli logged in with Contributor (or Website Contributor) on RG
#   - AZURE_API_KEY env var set
#   - Docker running (for build & push to ACR)
#
# Usage:
#   export AZURE_API_KEY="your-azure-foundry-key"
#   ./scripts/deploy-litellm-azure.sh           # full deploy (build → push → config → restart)
#   ./scripts/deploy-litellm-azure.sh --status  # check status
#   ./scripts/deploy-litellm-azure.sh --logs    # tail logs
#   ./scripts/deploy-litellm-azure.sh --test    # test /v1/models endpoint
# ============================================================

set -euo pipefail

# ---- Config ----
RG="RG-ENTCHAT-POC-SAND-SEA"
APP_NAME="app-litellm-poc-sand"
ASP_NAME="asp-entchat-poc-sand"
IMAGE_TAG="litellm-entchat"
LITELLM_VERSION="v1.83.3-stable"
PORT=4000
AZURE_API_BASE="${AZURE_API_BASE:-https://aif-entchat-poc-sand.cognitiveservices.azure.com}"
LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-litellm-poc-master-key}"
PG_HOST="${PG_HOST:-psql-entchat-poc-sand.postgres.database.azure.com}"
PG_USER="${PG_USER:-entchatadm}"
PG_PASS="${PG_PASS:-DocWiseP@ssw0rd2026!}"
PG_DB="${PG_DB:-litellm}"
REGION="southeastasia"
SEARCH_SERVICE="${AZURE_SEARCH_SERVICE_NAME:-srch-entchat-poc-sand}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKERFILE="$PROJECT_DIR/docker/Dockerfile.litellm"

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

# ---- Preflight ----
check_deps() {
  command -v az >/dev/null 2>&1 || err "az cli not found. Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
  az account show >/dev/null 2>&1 || err "Not logged in. Run: az login"
  command -v docker >/dev/null 2>&1 || err "docker not found"
}

check_key() {
  if [[ -z "${AZURE_API_KEY:-}" ]]; then
    err "AZURE_API_KEY not set. Run: export AZURE_API_KEY=\"your-key\""
  fi
  if [[ -z "${AZURE_SEARCH_API_KEY:-}" ]]; then
    warn "AZURE_SEARCH_API_KEY not set — vector store search will fail. Get it from: az search admin-key show --service-name ${SEARCH_SERVICE} --resource-group ${RG}"
  fi
}

# ---- Step 1: Build Docker image ----
build_image() {
  info "Building LiteLLM Docker image..."
  docker build \
    -f "$DOCKERFILE" \
    --build-arg LITELLM_VERSION="$LITELLM_VERSION" \
    -t "$IMAGE_TAG:latest" \
    "$PROJECT_DIR"
  ok "Image built: ${IMAGE_TAG}:latest"
}

# ---- Step 2: Push to ACR (or use ghcr.io directly) ----
get_or_create_acr() {
  # Check if existing ACR is usable, otherwise create one
  ACR_NAME=$(az acr list --resource-group "$RG" --query "[0].name" -o tsv 2>/dev/null || echo "")

  if [[ -z "$ACR_NAME" ]]; then
    ACR_NAME="acrentchatpocsand"  # follow naming convention
    info "No ACR found. Creating: ${ACR_NAME}..."
    az acr create \
      --resource-group "$RG" \
      --name "$ACR_NAME" \
      --sku Basic \
      --location "$REGION" \
      --admin-enabled true \
      -o none
    ok "ACR created: ${ACR_NAME}.azurecr.io"
  fi

  ACR_LOGIN_SERVER=$(az acr show --resource-group "$RG" --name "$ACR_NAME" --query "loginServer" -o tsv)
  echo "$ACR_LOGIN_SERVER"
}

push_to_acr() {
  local acr_server="$1"
  local full_tag="${acr_server}/${IMAGE_TAG}:latest"

  info "Pushing image to ACR: ${full_tag}"
  docker tag "$IMAGE_TAG:latest" "$full_tag"

  az acr login --name "${acr_server%%.*}" -o none
  docker push "$full_tag"
  ok "Image pushed: ${full_tag}"
  echo "$full_tag"
}

# ---- Step 3: Configure Web App ----
configure_webapp() {
  local full_image="$1"

  info "Configuring Web App: ${APP_NAME}"
  echo ""

  # Set container image
  info "Setting container image: ${full_image}"
  az webapp config container set \
    --resource-group "$RG" \
    --name "$APP_NAME" \
    --container-image-name "$full_image" \
    --container-registry-url "https://${full_image%%/*}" \
    -o none || err "Failed to set container image (check Contributor role)"
  ok "Container image set"

  # Set port
  info "Setting WEBSITES_PORT=${PORT}..."
  az webapp config appsettings set \
    --resource-group "$RG" \
    --name "$APP_NAME" \
    --settings WEBSITES_PORT="$PORT" \
    -o none || err "Failed to set WEBSITES_PORT"
  ok "WEBSITES_PORT=${PORT}"

  # Set env vars
  info "Setting environment variables..."

  # URL-encode password for DATABASE_URL (@ → %40, ! → %21)
  local pg_pass_encoded
  pg_pass_encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${PG_PASS}'))")
  local database_url="postgresql://${PG_USER}:${pg_pass_encoded}@${PG_HOST}:5432/${PG_DB}?sslmode=require"

  az webapp config appsettings set \
    --resource-group "$RG" \
    --name "$APP_NAME" \
    --settings \
      AZURE_API_KEY="$AZURE_API_KEY" \
      AZURE_API_BASE="$AZURE_API_BASE" \
      LITELLM_MASTER_KEY="$LITELLM_MASTER_KEY" \
      DATABASE_URL="$database_url" \
      AZURE_SEARCH_API_KEY="${AZURE_SEARCH_API_KEY:-}" \
      AZURE_SEARCH_SERVICE_NAME="$SEARCH_SERVICE" \
      PROXY_BASE_URL="https://${APP_NAME}.azurewebsites.net" \
    -o none || err "Failed to set app settings"
  ok "AZURE_API_BASE=${AZURE_API_BASE}"
  ok "LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}"
  ok "AZURE_API_KEY=*** (hidden)"
  ok "DATABASE_URL=postgresql://...@${PG_HOST}:5432/${PG_DB}"
  ok "AZURE_SEARCH_SERVICE_NAME=${SEARCH_SERVICE}"

  # Startup timeout (generous for cold starts)
  info "Setting startup timeout..."
  az webapp config appsettings set \
    --resource-group "$RG" \
    --name "$APP_NAME" \
    --settings WEBSITES_CONTAINER_START_TIME_LIMIT=180 \
    -o none 2>/dev/null || true
  ok "WEBSITES_CONTAINER_START_TIME_LIMIT=180"
}

# ---- Step 4: Restart ----
restart_app() {
  info "Restarting web app..."
  az webapp restart \
    --resource-group "$RG" \
    --name "$APP_NAME" \
    -o none
  ok "Web app restarted"
}

# ---- Full deploy ----
deploy() {
  check_key
  echo ""
  info "===== LiteLLM Azure Deployment ====="
  info "App: ${APP_NAME}"
  info "RG:  ${RG}"
  info "Image: ${IMAGE_TAG}:latest"
  echo ""

  # Build
  build_image
  echo ""

  # Push to ACR
  local acr_server
  acr_server=$(get_or_create_acr)
  local full_image
  full_image=$(push_to_acr "$acr_server")
  echo ""

  # Configure
  configure_webapp "$full_image"
  echo ""

  # Restart
  restart_app
  echo ""

  # Wait and verify
  info "Waiting for LiteLLM to start (~30s)..."
  sleep 30
  verify
}

# ---- Verify ----
verify() {
  echo ""
  info "Verifying deployment..."

  local hostname
  hostname=$(az webapp show --resource-group "$RG" --name "$APP_NAME" --query "defaultHostName" -o tsv 2>/dev/null || echo "unknown")

  ok "URL:         https://${hostname}"
  ok "LiteLLM UI:  https://${hostname}/ui"
  ok "API:         https://${hostname}/v1"
  echo ""
  info "To test:"
  echo "  curl https://${hostname}/v1/chat/completions \\"
  echo "    -H 'Authorization: Bearer ${LITELLM_MASTER_KEY}' \\"
  echo "    -H 'Content-Type: application/json' \\"
  echo "    -d '{\"model\":\"gpt-5.4-nano\",\"messages\":[{\"role\":\"user\",\"content\":\"สวัสดี\"}]}'"
}

# ---- Status ----
show_status() {
  local hostname status image_fx
  hostname=$(az webapp show --resource-group "$RG" --name "$APP_NAME" --query "defaultHostName" -o tsv 2>/dev/null || echo "unknown")
  status=$(az webapp show --resource-group "$RG" --name "$APP_NAME" --query "state" -o tsv 2>/dev/null || echo "unknown")
  image_fx=$(az resource show --resource-group "$RG" --name "$APP_NAME" --resource-type "Microsoft.Web/sites" --api-version 2022-09-01 --query "properties.siteConfig.linuxFxVersion" -o tsv 2>/dev/null || echo "unknown")

  info "LiteLLM — ${APP_NAME}"
  echo "  URL:        https://${hostname}"
  echo "  Status:     ${status}"
  echo "  Image:      ${image_fx}"
  echo "  LiteLLM UI: https://${hostname}/ui"
  echo "  API:        https://${hostname}/v1"
}

# ---- Logs ----
show_logs() {
  az webapp log tail \
    --resource-group "$RG" \
    --name "$APP_NAME"
}

# ---- Test ----
test_endpoint() {
  local hostname
  hostname=$(az webapp show --resource-group "$RG" --name "$APP_NAME" --query "defaultHostName" -o tsv 2>/dev/null || echo "unknown")

  info "Testing: https://${hostname}/v1/models"
  echo ""
  curl -sS "https://${hostname}/v1/models" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    -H "Content-Type: application/json" | python3 -m json.tool 2>/dev/null || \
    warn "Request failed — check if app is running and credentials are correct"
}

# ---- Main ----
check_deps

case "${1:-deploy}" in
  deploy|"")
    deploy
    ;;
  --status|-s)
    show_status
    ;;
  --logs|-l)
    show_logs
    ;;
  --test|-t)
    test_endpoint
    ;;
  *)
    echo "Usage: $0 [--status|--logs|--test]"
    echo ""
    echo "  (default)  deploy   — Build, push, configure, and deploy"
    echo "  --status   (-s)     — Show deployment status"
    echo "  --logs    (-l)     — Tail logs"
    echo "  --test    (-t)     — Test /v1/models endpoint"
    exit 1
    ;;
esac
