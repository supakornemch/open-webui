#!/usr/bin/env bash
# =============================================================================
# 🚀 PoC Resource Provisioning Script
# Enterprise Chat & AI Document + IR Service
# Haadthip — DIO Team
# Region: Southeast Asia
# Date: 2026-07-02
# =============================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
LOCATION="southeastasia"
ADMIN_USER="entchatadm"
# ⚠️ Set PG_ADMIN_PASSWORD before running. URL_ENCODED must match (@ → %40, ! → %21).
RAW_PASSWORD="${PG_ADMIN_PASSWORD:?set PG_ADMIN_PASSWORD}"
URL_ENCODED_PASSWORD="${PG_ADMIN_PASSWORD_URLENC:?set PG_ADMIN_PASSWORD_URLENC (URL-encoded form)}"

# ── Subscription ─────────────────────────────────────────────────────────────
SUBSCRIPTION="82f65db7-e209-4eb1-98fe-3e56bc45607a"  # SUB-HTC-SANDBOX-DC
az account set --subscription "$SUBSCRIPTION"

# ── Entra ID (Azure AD) for Open WebUI SSO ──────────────────────────────────
# Set these to match your App Registration in Entra ID
# To create: az ad app create --display-name "Open WebUI — Sandbox PoC" \
#   --sign-in-audience "AzureADMyOrg" \
#   --web-redirect-uris "https://app-entchat-owui-poc-sand.azurewebsites.net/oauth/callback"
OWUI_APP_REG_NAME="Open WebUI — Sandbox PoC"
# ⚠️ Provide these via env from your Entra ID App Registration
ENTRA_CLIENT_ID="${ENTRA_CLIENT_ID:?set ENTRA_CLIENT_ID}"
ENTRA_CLIENT_SECRET="${ENTRA_CLIENT_SECRET:?set ENTRA_CLIENT_SECRET}"
ENTRA_TENANT_ID="${ENTRA_TENANT_ID:-}"
# Auto-detect tenant ID if not manually set
if [ -z "$ENTRA_TENANT_ID" ]; then
  ENTRA_TENANT_ID=$(az account show --query "tenantId" -o tsv 2>/dev/null || echo "")
fi
WEBUI_SECRET_KEY=$(openssl rand -hex 32)

echo "========================================"
echo "  PoC Azure Resource Provisioning"
echo "  Location : $LOCATION"
echo "  Date     : 2026-07-02"
echo "========================================"

# ── Step 1: Resource Groups ──────────────────────────────────────────────────
echo ""
echo "=== [1/10] Resource Groups ==="
az group create --name RG-ENTCHAT-POC-SAND-SEA --location $LOCATION -o table
# Note: rg-ir-poc-sea and IR resources are NOT included in this sandbox deployment

# ── Step 2: Storage Accounts ─────────────────────────────────────────────────
echo ""
echo "=== [2/10] Storage Accounts ==="
az storage account create \
  --name staentchatdoc \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --access-tier Hot \
  --min-tls-version TLS1_2 \
  -o table

# Note: Storage account names are GLOBALLY unique — retry with different name
# if the name "stirpoc001" is taken.
# IR Storage Account — not deployed in sandbox
# az storage account create \
#   --name stirhaadthip001 \
#   --resource-group <ir-rg> \
#   --location $LOCATION \
#   --sku Standard_LRS \
#   --kind StorageV2 \
#   --access-tier Hot \
#   --min-tls-version TLS1_2 \
#   -o table

# ── Step 3: App Service Plan ─────────────────────────────────────────────────
echo ""
echo "=== [3/10] App Service Plan (B2 Linux) ==="
az appservice plan create \
  --name asp-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --location $LOCATION \
  --sku B2 \
  --is-linux \
  -o table

# ── Step 4: PostgreSQL Flexible Server ───────────────────────────────────────
echo ""
echo "=== [4/10] PostgreSQL Flexible Server (B1ms) ==="
az postgres flexible-server create \
  --name psql-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --location $LOCATION \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --admin-user "$ADMIN_USER" \
  --admin-password "$RAW_PASSWORD" \
  --public-access 0.0.0.0 \
  --yes \
  -o table

# ── Step 5: PostgreSQL Firewall (Azure services) + Database ──────────────────
echo ""
echo "=== [5/10] PostgreSQL: Firewall + Database ==="
echo "  Adding Azure services firewall rule..."
az postgres flexible-server firewall-rule create \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --server-name psql-entchat-poc-sand \
  --name AllowAllAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0 \
  --query "name" -o tsv

echo "  Creating databases 'open_webui' and 'docwise'..."
# Requires psycopg2 installed (pip3 install psycopg2-binary)
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='psql-entchat-poc-sand.postgres.database.azure.com',
    user='$ADMIN_USER',
    password='$RAW_PASSWORD',
    dbname='postgres',
    sslmode='require',
    connect_timeout=10
)
conn.autocommit = True
cur = conn.cursor()
for db in ['open_webui', 'docwise']:
    cur.execute(f\"SELECT datname FROM pg_database WHERE datname = '{db}'\")
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE {db};')
        print(f'  ✅ Database {db} created')
    else:
        print(f'  ✅ Database {db} already exists')
cur.close()
conn.close()
"

# ── Step 6: Web Apps (Container) ─────────────────────────────────────────────
echo ""
echo "=== [6/10] Web Apps (Container) ==="
# Open WebUI
az webapp create \
  --name app-entchat-owui-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --plan asp-entchat-poc-sand \
  --deployment-container-image-name "ghcr.io/open-webui/open-webui:main" \
  -o table

# DocWise (placeholder — replace with your actual container image)
az webapp create \
  --name app-docwise-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --plan asp-entchat-poc-sand \
  --deployment-container-image-name "python:3.11-slim" \
  -o table

# ── Step 7: App Settings (Open WebUI) ────────────────────────────────────────
echo ""
echo "=== [7/10] Open WebUI App Settings ==="
DATABASE_URL_OWUI="postgresql://${ADMIN_USER}:${URL_ENCODED_PASSWORD}@psql-entchat-poc-sand.postgres.database.azure.com:5432/open_webui?sslmode=require"

az webapp config appsettings set \
  --name app-entchat-owui-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --settings \
    "DATABASE_URL=${DATABASE_URL_OWUI}" \
    "WEBUI_AUTH=True" \
    "ENABLE_SIGNUP=True" \
    "WEBSITES_PORT=8080" \
    "WEBSITES_CONTAINER_START_TIME_LIMIT=1800" \
    "WEBUI_URL=https://app-entchat-owui-poc-sand.azurewebsites.net" \
    "WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}" \
    "ENABLE_OAUTH_SIGNUP=true" \
    "OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true" \
    "MICROSOFT_CLIENT_ID=${ENTRA_CLIENT_ID}" \
    "MICROSOFT_CLIENT_SECRET=${ENTRA_CLIENT_SECRET}" \
    "MICROSOFT_CLIENT_TENANT_ID=${ENTRA_TENANT_ID}" \
    "MICROSOFT_REDIRECT_URI=https://app-entchat-owui-poc-sand.azurewebsites.net/oauth/callback" \
    "MICROSOFT_OAUTH_SCOPE=openid email profile offline_access" \
    "OPENID_PROVIDER_URL=https://login.microsoftonline.com/${ENTRA_TENANT_ID}/v2.0/.well-known/openid-configuration" \
  -o table

if [ "$ENTRA_CLIENT_ID" = "<REPLACE_WITH_CLIENT_ID>" ]; then
  echo "  ⚠️  Entra ID NOT configured — set ENTRA_CLIENT_ID / ENTRA_CLIENT_SECRET / ENTRA_TENANT_ID"
  echo "      in the Config section above, or create App Registration manually in Azure Portal."
else
  echo "  ✅ Entra ID OIDC configured for Open WebUI"
fi

# ── Step 7b: DocWise App Settings (placeholder — keys injected in Step 11) ────
# NOTE: AI endpoint, storage key, and search key are created later (Steps 8-10).
#       We set a base DATABASE_URL now; the rest is injected in Step 11.
echo ""
echo "=== [7b/10] DocWise — Base App Settings ==="

DATABASE_URL_DOCWISE="postgresql://${ADMIN_USER}:${URL_ENCODED_PASSWORD}@psql-entchat-poc-sand.postgres.database.azure.com:5432/docwise?sslmode=require"

az webapp config appsettings set \
  --name app-docwise-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --settings \
    "DATABASE_URL=${DATABASE_URL_DOCWISE}" \
    "WEBSITES_PORT=8000" \
    "WEBSITES_CONTAINER_START_TIME_LIMIT=1800" \
  -o table

# ── Step 8: AI Search (Free tier) ────────────────────────────────────────────
echo ""
echo "=== [8/10] Azure AI Search (Free tier) ==="
az search service create \
  --name srch-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --location $LOCATION \
  --sku free \
  -o table

# ── Step 9: AI Foundry Hub + Project ─────────────────────────────────────────
echo ""
echo "=== [9/10] Azure AI Foundry Hub + Project ==="

# Hub
az ml workspace create \
  --name aif-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --location $LOCATION \
  --kind hub \
  --display-name "Haadthip Enterprise Chat Hub (PoC)" \
  --description "AI Foundry Hub for Enterprise Chat & DocWise PoC" \
  -o json > /dev/null

HUB_ID=$(az ml workspace show \
  --name aif-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --query "id" -o tsv)

# Project via ARM template (workaround for ml ext v2.44 bug)
cat > /tmp/proj_arm.json << 'ARMEOF'
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "projectName": { "type": "string" },
    "location": { "type": "string" },
    "hubId": { "type": "string" }
  },
  "resources": [
    {
      "type": "Microsoft.MachineLearningServices/workspaces",
      "apiVersion": "2024-10-01-preview",
      "name": "[parameters('projectName')]",
      "location": "[parameters('location')]",
      "kind": "project",
      "identity": { "type": "SystemAssigned" },
      "properties": {
        "hubResourceId": "[parameters('hubId')]",
        "description": "AI Foundry Project for Enterprise Chat & DocWise PoC",
        "friendlyName": "Enterprise Chat & DocWise Project (PoC)"
      }
    }
  ]
}
ARMEOF

az deployment group create \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --template-file /tmp/proj_arm.json \
  --parameters projectName=proj-entchat-poc-sand location=$LOCATION hubId="$HUB_ID" \
  --query "properties.provisioningState" -o tsv

# ── Step 10: Azure AI Services (Foundry) + Model Deployments ────────────────
echo ""
echo "=== [10/10] Azure AI Services (AIServices) + Model Deployments ==="

# ⚠️ Use kind=AIServices (NOT OpenAI) — Student subscription has quota for
#    gpt-5.4-nano / gpt-5.4-mini / gpt-5.4 via AIServices kind but NOT via OpenAI kind.
#    Discovered 2026-07-02 via AI Foundry Portal.
AI_NAME="aif-entchat-poc-sand"

az cognitiveservices account create \
  --name $AI_NAME \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --location $LOCATION \
  --kind AIServices \
  --sku S0 \
  --yes \
  -o table

echo ""
echo "  Deploying models (may take 5-10 min each)..."
echo ""

# Deploy gpt-5.4-nano (OCER / Summarize — cheapest)
echo "  → Deploying gpt-5.4-nano..."
az cognitiveservices account deployment create \
  --name $AI_NAME \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --deployment-name deploy-gpt-54-nano \
  --model-name gpt-5.4-nano \
  --model-version "2026-03-17" \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 1 \
  -o table 2>&1 | tail -3

# Deploy gpt-5.4-mini (mid-tier chat / tasks)
echo "  → Deploying gpt-5.4-mini..."
az cognitiveservices account deployment create \
  --name $AI_NAME \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --deployment-name deploy-gpt-54-mini \
  --model-name gpt-5.4-mini \
  --model-version "2026-03-17" \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 1 \
  -o table 2>&1 | tail -3

# Deploy gpt-5.4 (general-purpose chat)
echo "  → Deploying gpt-5.4..."
az cognitiveservices account deployment create \
  --name $AI_NAME \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --deployment-name deploy-gpt-54 \
  --model-name gpt-5.4 \
  --model-version "2026-03-05" \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 1 \
  -o table 2>&1 | tail -3

echo ""
echo "  ✅ Models deployed: gpt-5.4-nano, gpt-5.4-mini, gpt-5.4"
echo "  ⚠️  DeepSeek models NOT available on AIServices kind (only GPT series)"

# ML Workspace (IR Service) — not deployed in sandbox
# az ml workspace create \
#   --name mlw-ir-poc-sea \
#   --resource-group <ir-rg> \
#   --location $LOCATION \
#   --display-name "Haadthip IR Workspace (PoC)" \
#   --description "Azure ML Workspace for IR (Inventory Recognition) Service" \
#   -o json > /dev/null
# echo "✅  ML Workspace created"

# ── Step 11: DocWise — Full App Settings + Storage Container ──────────────────
echo ""
echo "=== [11/11] DocWise — Inject AI/Storage/Search Keys ==="

# Retrieve AI Services endpoint + key
AI_ENDPOINT=$(az cognitiveservices account show \
  --name aif-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --query "properties.endpoint" -o tsv)
AI_KEYS=$(az cognitiveservices account keys list \
  --name aif-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --query "key1" -o tsv)

# Retrieve Storage key
STORAGE_KEY=$(az storage account keys list \
  --account-name staentchatdoc \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --query "[0].value" -o tsv)

# Retrieve AI Search key
SEARCH_KEY=$(az search admin-key show \
  --service-name srch-entchat-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --query "primaryKey" -o tsv)

az webapp config appsettings set \
  --name app-docwise-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --settings \
    "AZURE_AI_ENDPOINT=${AI_ENDPOINT}" \
    "AZURE_AI_KEY=${AI_KEYS}" \
    "AZURE_AI_SEARCH_ENDPOINT=https://srch-entchat-poc-sand.search.windows.net" \
    "AZURE_AI_SEARCH_KEY=${SEARCH_KEY}" \
    "AZURE_STORAGE_ACCOUNT_NAME=staentchatdoc" \
    "AZURE_STORAGE_ACCOUNT_KEY=${STORAGE_KEY}" \
    "AZURE_STORAGE_CONTAINER_NAME=documents" \
    "GPT_DEPLOYMENT_NAME=deploy-gpt-54-nano" \
    "GPT_MODEL_NAME=gpt-5.4-nano" \
  -o table

# Create 'documents' blob container for DocWise
echo "  Creating 'documents' blob container..."
az storage container create \
  --account-name staentchatdoc \
  --name documents \
  --auth-mode key \
  --account-key "$STORAGE_KEY" \
  --query "name" -o tsv

echo "  ✅ DocWise app settings + storage container ready"

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  ✅ ALL RESOURCES PROVISIONED"
echo "========================================"
echo ""
echo "  📦 RG-ENTCHAT-POC-SAND-SEA"
az resource list --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --query "sort_by([].{name:name, type:type}, &name)" -o table 2>/dev/null
echo ""
echo "  🤖 IR resources — not deployed in sandbox"
echo "     (Skipped: stirhaadthip001, mlw-ir-poc-sea)"
echo ""
echo "  🔑 PostgreSQL"
echo "     Host: psql-entchat-poc-sand.postgres.database.azure.com"
echo "     User: $ADMIN_USER"
echo "     Pass: $RAW_PASSWORD"
echo "     DB  : open_webui, docwise"
echo ""
echo "  🌐 Open WebUI: https://app-entchat-owui-poc-sand.azurewebsites.net"
echo "  📄 DocWise   : https://app-docwise-poc-sand.azurewebsites.net"
echo ""
echo "========================================"
