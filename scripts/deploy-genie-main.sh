#!/usr/bin/env bash
set -euo pipefail

# Genie Main Deployment Script
# Deploys the new production Genie AI model (Pipe-based) to QAS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Configuration
ACR_NAME="${ACR_NAME:-acrentchatqas}"
RESOURCE_GROUP="${RESOURCE_GROUP:-RG-INCUBATION-AI-QAS-SEA}"
APP_SERVICE="${APP_SERVICE:-app-entchat-owui-qas}"
IMAGE_TAG="${IMAGE_TAG:-genie-v1.0.0}"
FULL_IMAGE="${ACR_NAME}.azurecr.io/entchat-owui:${IMAGE_TAG}"

# Pre-flight checks
log_info "Pre-flight checks..."

if ! command -v docker &> /dev/null; then
    log_error "docker not found. Install Docker first."
    exit 1
fi

if ! command -v az &> /dev/null; then
    log_error "az CLI not found. Install Azure CLI first."
    exit 1
fi

# Check Docker buildx for multi-platform
if ! docker buildx version &> /dev/null; then
    log_error "docker buildx not available. Update Docker to latest version."
    exit 1
fi

# Check Azure login
if ! az account show &> /dev/null; then
    log_error "Not logged in to Azure. Run: az login"
    exit 1
fi

log_success "Pre-flight checks passed"

# Step 1: Build image (AMD64 only for Azure App Service)
log_info "Building Docker image for linux/amd64..."
docker buildx build \
    --platform linux/amd64 \
    -f docker/Dockerfile.owui \
    -t "$FULL_IMAGE" \
    --load \
    .

log_success "Image built: $FULL_IMAGE"

# Step 2: Tag and push
log_info "Pushing image to ACR..."
az acr login --name "$ACR_NAME"
docker push "$FULL_IMAGE"
log_success "Image pushed to ACR"

# Step 3: Get current image (for rollback reference)
CURRENT_IMAGE=$(az webapp config container show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_SERVICE" \
    --query "[0].value" -o tsv 2>/dev/null || echo "unknown")

log_info "Current image: $CURRENT_IMAGE"
log_info "New image: $FULL_IMAGE"

# Step 4: Deploy to App Service
log_info "Deploying to App Service..."
az webapp config container set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_SERVICE" \
    --docker-custom-image-name "$FULL_IMAGE"

log_success "Deployment initiated"

# Step 5: Wait for deployment
log_info "Waiting for container to restart (30s)..."
sleep 30

# Step 6: Health check
log_info "Health check..."
WEBAPP_URL="https://${APP_SERVICE}.azurewebsites.net"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${WEBAPP_URL}/" || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    log_success "Health check passed (HTTP $HTTP_CODE)"
else
    log_error "Health check failed (HTTP $HTTP_CODE)"
    log_error "Check logs: az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_SERVICE"
    exit 1
fi

# Summary
echo ""
log_success "═══════════════════════════════════════════════════════"
log_success "Genie Main v1.0.0 deployed successfully to QAS"
log_success "═══════════════════════════════════════════════════════"
echo ""
log_info "Next steps:"
echo "  1. Login to https://genie-qas.haadthip.com"
echo "  2. Go to Workspace → Functions"
echo "  3. Configure 'genie_main_pipe' valves:"
echo "     - FABRIC_ENDPOINT, LLM_BASE_URL, LLM_API_KEY, etc."
echo "  4. Go to Workspace → Models → Create"
echo "  5. Create model 'genieai' with base_model='genie_main_pipe'"
echo "  6. Paste system prompt from docs/genie-main-promotion-plan.md"
echo "  7. Test with: 'ดูให้หน่อยว่าฉันเข้าถึงข้อมูลอะไรได้จาก Fabric'"
echo ""
log_info "Rollback command (if needed):"
echo "  az webapp config container set \\"
echo "    --resource-group $RESOURCE_GROUP \\"
echo "    --name $APP_SERVICE \\"
echo "    --docker-custom-image-name $CURRENT_IMAGE"
echo ""
