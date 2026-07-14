# Azure Container Apps Deployment Spec — Open WebUI + AI Search

> **Status:** Architecture Spec | **Last Updated:** 2026-07-03
> **Decision:** เลือก Azure Container Apps เหนือ AKS — ทีมดูแลน้อย, ในงบ $100/เดือน, scale-to-zero
> **Related:** [CONTEXT.md](../CONTEXT.md), [docs/adr/](./adr/)

---

## 1. Executive Summary

Deploy **Open WebUI** (AI chat interface) + **Azure AI Search** (RAG + Agentic Retrieval) บน **Azure Container Apps (Consumption Plan)** — fully managed, scale-to-zero, จ่ายตามใช้จริง, ทีมคนเดียวก็ดูแลไหว

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│            Azure Container Apps Environment                 │
│            (Managed VNet, Southeast Asia)                    │
│                                                             │
│  ┌──────────────────────┐                                  │
│  │ Open WebUI Container  │                                 │
│  │  ┌────────────────┐  │                                  │
│  │  │ openwebui:main │  │                                  │
│  │  │ CPU: 0.5 / 1.0 │  │                                  │
│  │  │ RAM: 1Gi / 2Gi │  │                                  │
│  │  │ Min: 0, Max: 3 │  │                                  │
│  │  └────────────────┘  │                                  │
│  │  Port: 8080          │                                  │
│  │  Ingress: ✅ TLS     │                                  │
│  └────────┬─────────────┘                                  │
│           │                                                 │
│  ┌────────┴─────────────────────────────────┐              │
│  │              Azure File Share             │              │
│  │         (Open WebUI storage)              │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┬──────────────┐
            ▼              ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ PostgreSQL   │  │ Azure Blob   │  │ Azure OpenAI │  │ Azure AI     │
│ Flex Server  │  │ Storage      │  │ Service      │  │ Search       │
│ B1ms, $15/mo │  │ LRS, <$1/mo  │  │ Pay-per-token│  │ Basic,~$73/mo│
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
       ▲                ▲                                ▲
       │   ┌──────────────┐                             │
       └───│  Key Vault   │─────────────────────────────┘
           │ (secrets)    │
           └──────────────┘
```

---

## 3. Why Container Apps (ไม่ใช่ AKS)?

| เหตุผล | Detail |
|---|---|
| **ทีมเล็ก** | ดูแลคนเดียวได้ ไม่ต้องรู้ Kubernetes |
| **Scale-to-zero** | ไม่มี traffic = ไม่มี bill (ยกเว้น DB) |
| **Managed TLS** | ฟรี certificate จาก DigiCert, auto-renew |
| **No node patching** | Azure จัดการ infrastructure ทั้งหมด |
| **Per-second billing** | จ่ายเฉพาะตอนใช้จริง |
| **Free grant** | 180K vCPU-sec + 360K GiB-sec/เดือน |
| **ในงบ $100** | ✅ แน่นอน |

---

## 4. Container App Specifications

### 4.1 Open WebUI Container App

| Parameter | Value |
|---|---|
| **Image** | `ghcr.io/open-webui/open-webui:main` |
| **Plan** | Consumption |
| **CPU** | 0.5 core |
| **Memory** | 1.0 GiB |
| **Min Replicas** | 0 (scale to zero) |
| **Max Replicas** | 3 |
| **Scale Rule** | HTTP scaling: 100 concurrent requests/replica |
| **Ingress** | External, port 8080 |
| **Domain** | `chat.yourdomain.com` |
| **TLS** | Managed certificate (free) |

> **Min Replicas = 0** คือหัวใจ — ถ้าไม่มีใครใช้ตอนกลางคืน/วันหยุด, container apps ทั้งหยุด run, จ่ายเฉพาะ PostgreSQL ~$15/เดือน

---

## 5. Shared Services

### 5.1 PostgreSQL Flexible Server

| Parameter | Value |
|---|---|
| **Tier** | Burstable B1ms |
| **vCores** | 1 |
| **Memory** | 2 GiB |
| **Storage** | 32 GB |
| **Backup** | 7 days |
| **Network** | Public (allow Azure services) |
| **SSL** | Required |

**Databases:**

| Database | Service |
|---|---|
| `openwebui` | Open WebUI |

### 5.2 Azure Blob Storage

| Parameter | Value |
|---|---|
| **Kind** | StorageV2 |
| **Replication** | LRS |
| **Tier** | Hot |
| **Containers** | `openwebui-uploads` |
| **Use** | S3-compatible API (Open WebUI) |

### 5.3 Azure Key Vault

| Parameter | Value |
|---|---|
| **Use** | เก็บ secrets (DB passwords, OpenAI API key, encryption key) |

### 5.4 Azure OpenAI Service

| Parameter | Value |
|---|---|
| **Model** | GPT-4o mini (cheapest for POC) |
| **Deployment** | 10K TPM rate limit |

### 5.5 Azure AI Search (RAG + Agentic Retrieval)

> ⚠️ **ต้องใช้ Basic tier ขึ้นไป** — Free tier ไม่รองรับ semantic ranker, vector search, skillsets, และ agentic retrieval

| Parameter | Value |
|---|---|
| **Tier** | Basic (ขั้นต่ำสำหรับ RAG/Agentic) |
| **Search Units** | 1 SU (1 partition + 1 replica) |
| **Storage** | 2 GB |
| **Max Indexes** | 15 |
| **Semantic Ranker** | Standard (required for agentic retrieval) |
| **Indexes** | `haadthip-docs` (vector + semantic) |
| **Knowledge Base** | `haadthip-kb` (agentic retrieval orchestrator) |
| **Ingestion** | Python script + Blob indexer (scheduled) |

| SKU | Cost/mo | Semantic | Vector | Agentic | เหมาะกับ |
|---|---|---|---|---|---|
| **Free** | $0 | ❌ | ❌ | ❌ | Dev/testing only |
| **Basic** | ~$73 | ✅ | ✅ | ✅ | POC / Small Production |
| **Standard S1** | ~$250/SU | ✅ | ✅ | ✅ | Production |
| **Standard S2** | ~$1,000/SU | ✅ | ✅ | ✅ | Enterprise |

---

## 6. Domain & TLS Setup

Azure Container Apps ให้ **free managed TLS** — ไม่ต้อง Key Vault สำหรับ cert, ไม่ต้อง cert-manager:

```
chat.yourdomain.com     CNAME →  openwebui.xxxxx.southeastasia.azurecontainerapps.io
```

พร้อม TXT verification สำหรับ DigiCert

---

## 7. Environment Variables

### Open WebUI

```bash
DATABASE_URL=postgresql://openwebui_user:<pwd>@enterprisechat-pg.postgres.database.azure.com:5432/openwebui
OPENAI_API_BASE=https://<your-azure-oi>.openai.azure.com/
OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://enterprisechat-kv.vault.azure.net/secrets/openai-api-key/)
OPENAI_API_VERSION=2025-03-01-preview
WEBUI_SECRET_KEY=@Microsoft.KeyVault(SecretUri=https://enterprisechat-kv.vault.azure.net/secrets/webui-secret-key/)
STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=https://enterprisechatstg.blob.core.windows.net
S3_BUCKET_NAME=openwebui-uploads
S3_ACCESS_KEY_ID=@Microsoft.KeyVault(SecretUri=https://enterprisechat-kv.vault.azure.net/secrets/storage-access-key/)
S3_SECRET_ACCESS_KEY=@Microsoft.KeyVault(SecretUri=https://enterprisechat-kv.vault.azure.net/secrets/storage-secret-key/)
```

---

## 8. Cost Breakdown — Realistic Monthly (POC)

### Active ใช้จริง 8 ชม./วัน × 22 วันทำการ = 176 ชม./เดือน

| Resource | Calculation | Cost |
|---|---|---|
| **Open WebUI vCPU** | 0.5 core × 176h × 3600s × $0.000024 | ~$7.60 |
| **Open WebUI Memory** | 1 GiB × 176h × 3600s × $0.000003 | ~$1.90 |
| **Free Grant** | 180K vCPU-sec + 360K GiB-sec | -$9.50 |
| **PostgreSQL B1ms** | 24/7 | ~$15.00 |
| **AI Search Basic** | 1 SU × 24/7 | ~$73.00 |
| **Blob Storage** | ~5 GB | ~$1.00 |
| **Key Vault** | Secrets + operations | ~$1.00 |
| **Azure OpenAI** | GPT-5.4-nano, ~10K tokens/day | ~$10.00 |
| **text-embedding-3-large** | Batch embeddings, ~1M tokens/mo | ~$0.13 |
| **Total** | | **~$100/month** ✅ |

---

## 9. Idle (Scale-to-Zero) — กลางคืน/วันหยุด

| Resource | Cost |
|---|---|
| Container Apps | $0 (scale to zero) |
| PostgreSQL | ~$15 |
| AI Search Basic | ~$73 (24/7 — ไม่มี scale-to-zero) |
| Blob + Key Vault | ~$2 |
| **Idle Total** | **~$90/เดือน** |

> 🎯 อยู่ในงบ $100 พอดี

---

## 10. Deployment Steps

### Phase 1 — Infrastructure

```bash
# === VARIABLES ===
LOCATION="southeastasia"
RG="rg-enterprisechat-poc"
LOCATION="southeastasia"

# 1. Create resource group
az group create --name $RG --location $LOCATION

# 2. PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group $RG \
  --name enterprisechat-pg \
  --location $LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 16 \
  --admin-user pgadmin \
  --admin-password <your-admin-password>

# Create database
az postgres flexible-server db create \
  --resource-group $RG \
  --server-name enterprisechat-pg \
  --database-name openwebui

# 3. Storage Account
az storage account create \
  --resource-group $RG \
  --name enterprisechatstg \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

az storage container create \
  --name openwebui-uploads \
  --account-name enterprisechatstg

# 4. Key Vault
az keyvault create \
  --resource-group $RG \
  --name enterprisechat-kv \
  --location $LOCATION

# Store secrets
az keyvault secret set --vault-name enterprisechat-kv --name openwebui-db-password --value "<password>"
az keyvault secret set --vault-name enterprisechat-kv --name openai-api-key --value "<api-key>"
az keyvault secret set --vault-name enterprisechat-kv --name webui-secret-key --value "$(openssl rand -hex 32)"
```

### Phase 2 — Container Apps Environment

```bash
# 5. Create Container Apps Environment
az containerapp env create \
  --resource-group $RG \
  --name enterprisechat-env \
  --location $LOCATION

# Get environment FQDN
ENV_DOMAIN=$(az containerapp env show \
  --resource-group $RG \
  --name enterprisechat-env \
  --query "properties.staticIp" -o tsv)
```

### Phase 3 — Open WebUI Container App

```bash
# 6. Create Open WebUI Container App
az containerapp create \
  --resource-group $RG \
  --environment enterprisechat-env \
  --name open-webui \
  --image ghcr.io/open-webui/open-webui:main \
  --cpu 0.5 --memory 1.0Gi \
  --min-replicas 0 --max-replicas 3 \
  --scale-rule-type http \
  --scale-rule-http-concurrency 100 \
  --target-port 8080 \
  --ingress external \
  --transport auto \
  --env-vars \
    DATABASE_URL="postgresql://openwebui_user:changeme@enterprisechat-pg.postgres.database.azure.com:5432/openwebui" \
    OPENAI_API_BASE="https://<azure-oi>.openai.azure.com/" \
    OPENAI_API_VERSION="2025-03-01-preview" \
    STORAGE_PROVIDER=s3 \
    S3_ENDPOINT_URL="https://enterprisechatstg.blob.core.windows.net" \
    S3_BUCKET_NAME=openwebui-uploads \
  --secrets \
    openai-api-key=keyvaultref:https://enterprisechat-kv.vault.azure.net/secrets/openai-api-key \
    webui-secret=keyvaultref:https://enterprisechat-kv.vault.azure.net/secrets/webui-secret-key \
    s3-access-key=keyvaultref:https://enterprisechat-kv.vault.azure.net/secrets/storage-access-key \
    s3-secret-key=keyvaultref:https://enterprisechat-kv.vault.azure.net/secrets/storage-secret-key

# 7. Bind custom domain
owui_FQDN=$(az containerapp show -n open-webui -g $RG --query "properties.configuration.ingress.fqdn" -o tsv)

# NOTE: DNS:
#   CNAME chat → $owui_FQDN
#   TXT   asuid.chat → $VERIFY_ID (same verification ID for same environment)

az containerapp hostname add --hostname chat.yourdomain.com -g $RG -n open-webui
az containerapp hostname bind --hostname chat.yourdomain.com -g $RG -n open-webui --environment enterprisechat-env --validation-method CNAME
```

---

## 11. Cost Summary

| Scenario | Usage Pattern | Monthly Cost |
|---|---|---|
| **Minimal** | Scale-to-zero, ใช้เฉพาะช่วง dev | **~$90** |
| **Typical POC** | 8h/วัน, 22 วัน/เดือน | **~$100** ✅ |
| **Active daily** | 12h/วัน, 30 วัน/เดือน | **~$108** |
| **24/7 on** | Always running, no scale-to-zero | **~$125** |
| **POC with pgvector** | แทน AI Search ด้วย pgvector (ใช้ DB เดิม) | **~$27** ✅ |

> 🎯 **Typical POC อยู่ในงบ $100 พอดี** | ต้องการลดอีก → pgvector ($27/mo) | ต้องการ agentic → AI Search Basic ($100/mo)

---

## 12. Scaling Path — POC → Medium

| Component | POC | Medium |
|---|---|---|
| **Open WebUI** | 0.5 CPU, 1 GiB, 0-3 replicas | 1.0 CPU, 2 GiB, 1-5 replicas |
| **PostgreSQL** | B1ms (Burstable) | Standard_D2s_v3 (General Purpose) |
| **Blob** | LRS | GRS + Private Endpoint |
| **AI Search** | Basic (1 SU) | Standard S1 (1-3 SU) |
| **LLM** | OpenAI GPT-4o mini | GPT-4o / Ollama on GPU Container App |
| **GPU** | ไม่ใช้ | Consumption-GPU-NC8as-T4 profile |
| **Domain** | Managed TLS | Managed TLS (unchanged) |
| **Secrets** | Key Vault | Key Vault + Managed Identity |

> ถ้าต้อง scale ใหญ่เกิน Container Apps → migrate ขึ้น AKS ภายหลังด้วย K8s manifests

---

## 13. File Layout

```
/
├── CONTEXT.md
├── docs/
│   ├── adr/
│   │   ├── 0001-ingress-app-routing-gateway-api.md
│   │   ├── 0002-shared-postgresql-flexible-server.md
│   │   ├── 0003-azure-blob-object-storage.md
│   │   ├── 0004-node-pool-strategy.md
│   │   └── 0005-llm-backend-hybrid.md
│   ├── aks-deployment-spec.md          # AKS version (เดิม, reference)
│   └── aca-deployment-spec.md          # Container Apps version (THIS DOC) ✅
├── scripts/
│   ├── 01-create-infra.sh
│   ├── 02-deploy-openwebui.sh
│   ├── 03-setup-ai-search.sh
│   └── 99-cleanup.sh
└── README.md
```

---

## 14. Comparison: AKS vs Container Apps (At a Glance)

| | AKS | Container Apps |
|---|---|---|
| **Cost (POC)** | ~$565-1,090/เดือน | **~$35-108/เดือน** |
| **Teamsize** | ต้องรู้ K8s (1-2 คน) | **รู้แค่ Docker + Azure (0.5 คน)** |
| **Scale-to-zero** | ❌ | ✅ |
| **Free TLS** | ❌ (ต้องตั้งเอง) | ✅ |
| **Node patching** | ต้องทำเอง | ✅ Azure managed |
| **GPU** | ✅ NCas_T4 node pool | ✅ GPU consumption profile |
| **AI Search** | ✅ External service (same cost) | ✅ External service (same cost) |
| **Upgrade** | K8s version upgrade ทุก 12-18 เดือน | ❌ ไม่ต้อง upgrade |
| **Flexibility** | ✅ ควบคุมทุกอย่าง | ⚠️ Azure abstraction |
| **Future migration** | — | → AKS ได้ถ้าต้องการ |
| **Recommended** | Medium+ Production | **POC / Small Team** ✅ |
