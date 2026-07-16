# EnterpriseChat — Domain Context

> ## 📝 Recent Changes (2026-07-14)
>
> ### ✅ LiteLLM: Cache + Pricing + API Fix
> - **Proxy cache**: `cache: True` (local, TTL 3600) → `cache_hit=True` ✅
> - **Azure cache pricing**: ตรงตลาด (90% off): nano=$0.02, mini=$0.08, 5.4=$0.25, 5.2=$0.18 /1M
> - **API version**: `AZURE_API_VERSION=2024-10-21` (GA) แก้ 404 Resource not found
> - **DOCKER_CUSTOM_IMAGE_NAME**: ลบ override → ใช้ digest จริง
>
> ### ✅ Teams SSO + User Manual
> - **Auth**: ใช้ `window.open()` → external browser (popup ใน Teams SDK ต้องเพิ่ม Pre-authorized clients ใน Entra)
> - **Manual**: เพิ่ม Knowledge attachment flow (More → Attach Knowledge), Calculator Tool, Feedback, CSV use case
>
> ### ✅ Public Web + Enterprise Doc Ingestion
> - `enterprise-docs-idx`: 792 chunks (corporate + hr-policies + haadthip-public-web)
> - `eexpense-faq-idx`: 42 FAQ docs
> - Cleanup: ลบ skillsets, indexers, datasources, KBs, blob containers เก่า
>
> ### ✅ Fixes Roundup
> - ACR pull: OCI image index (ARM64 Mac) → ต้องใช้ AMD64 sub-manifest digest ในการ deploy
> - LiteLLM model `text-embedding-3-large` หาย → re-add + add cache cost fields
> - Open WebUI database: `config` table key-value schema + alembic_version fix

## Glossary (abridged)

| Term | Definition |
|---|---|
| **Open WebUI** | Self-hosted AI chat UI (v0.10.2) — RAG, SSO, Tools, Functions |
| **LiteLLM** | LLM gateway/proxy (v1.83.3) — token tracking, cost limits, cache |
| **Azure AI Search** | `srch-entchat-poc-sand` — hybrid + vector + semantic search |
| **Azure AI Foundry** | `aif-entchat-poc-sand` — Azure OpenAI + AI Services (merged) |
| **Enterprise Search Tool** | Open WebUI tool — query `enterprise-docs-idx` (corpus/category filterable) |
| **Native Mode (Agentic)** | model จัดการ function calling loop เอง |
| **Pipe** | Open WebUI function type รับ query → search KB → LLM → ตอบ |
| **Tool** | Open WebUI function type ให้ model เรียกใช้ผ่าน function calling |

## Azure Infrastructure

| Resource | Name | SKU | Shared? |
|----------|------|-----|:-------:|
| App Service Plan | `asp-entchat-poc-sand` | B2 Linux | ✅ |
| Storage | `staentchatdoc` | Standard_LRS | ✅ |
| PostgreSQL | `psql-entchat-poc-sand` | B1ms, v18, 32GB | ✅ (3 DBs) |
| AI Search | `srch-entchat-poc-sand` | Standard | ✅ |
| AI Foundry | `aif-entchat-poc-sand` | S0 | ✅ |
| Web App — Open WebUI | `app-entchat-owui-poc-sand` | Container Linux | ❌ |
| Web App — LiteLLM | `app-litellm-poc-sand` | Container Linux | ❌ |
| ACR | `acrentchatpocsand` | Basic | ❌ |

### PostgreSQL
- **Host**: `psql-entchat-poc-sand.postgres.database.azure.com`
- **Admin**: `entchatadm` / `DocWiseP@ssw0rd2026!`
- **DBs**: `open_webui` (OWUI), `docwise`, `litellm`

### Model Deployments (AI Foundry)

| Name | Model | Use |
|------|-------|-----|
| `deploy-gpt-5.4-nano` | gpt-5.4-nano ($0.20/1M in) | KB query planning (cheapest) |
| `deploy-gpt-5.4-mini` | gpt-5.4-mini ($0.75/1M in) | General chat |
| `deploy-gpt-5.4` | gpt-5.4 ($2.50/1M in) | Pipe final answer |
| `deploy-gpt-5.2` | gpt-5.2 ($1.75/1M in) | Fallback |
| `deploy-embedding-3-large` | text-embedding-3-large (3072d) | Vector embeddings |

### AI Search Indexes

| Index | Docs | Type | Status |
|-------|:----:|------|--------|
| `enterprise-docs-idx` | 792 | Vector HNSW + Semantic | ✅ Main |
| `eexpense-faq-idx` | 42 | Vector HNSW + Semantic | ✅ E-Expense |

### Blob Containers (`staentchatdoc`)
- **Active**: `open-webui-files`, `cost-reports`, `documents`, `uploads`, `vhds`
- **Deleted**: `haadthip-ir`, `haadthip-public`, `mihcm-hr`, `sap-docs`

### Container Registry (`acrentchatpocsand`)
- **Images**: `owui-entchat-teams` (Open WebUI + teams-auth.html), `litellm-entchat` (LiteLLM + MCP packages)
- ⚠️ ARM64 build → OCI index → ต้องใช้ AMD64 sub-manifest digest เสมอ

## Open WebUI (Genie)

| Field | Value |
|-------|-------|
| URL | `genie.haadthip.com` / `app-entchat-owui-poc-sand.azurewebsites.net` |
| Image | `owui-entchat-teams@sha256:...` (v0.10.2 + teams-auth.html + screenshots) |
| Auth | Microsoft Entra ID SSO (OIDC) — auto signup enabled |
| DB | `postgresql://entchatadm:***@psql-...:5432/open_webui?sslmode=require` |
| LiteLLM | OpenAI API: `https://app-litellm-poc-sand.azurewebsites.net` |
| Teams Auth | `/teams-auth.html` — Teams SDK v2 + popup (ใน Teams) → fallback external browser |

### App Settings (key)
`WEBSITES_PORT=8080`, `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`, `WEBSITES_CONTAINER_START_TIME_LIMIT=1800`

### Tools in System
| Tool | Purpose |
|------|---------|
| Enterprise Search | ค้นหา `enterprise-docs-idx` — รองรับ filter corpus + category |
| Calculator | คำนวณนิพจน์คณิตศาสตร์ (+, -, *, /, sqrt, pow) |

### Prompts (16 รายการ)
`/sales-brief`, `/promo-analyze`, `/local-content`, `/production-plan`, `/maintenance-guide`, `/route-optimize`, `/hr-benefits`, `/it-helpdesk`, `/expense-check`, `/credit-collect`, `/search`, `/translate`, `/summarize`

## LiteLLM Proxy

| Field | Value |
|-------|-------|
| URL | `https://app-litellm-poc-sand.azurewebsites.net` |
| Image | `litellm-entchat@sha256:...` (v1.83.3-stable + MCP packages) |
| Dashboard | `/ui` (login: `admin` / `sk-litellm-poc-master-key`) |
| DB | `postgresql://entchatadm:***@psql-...:5432/litellm?sslmode=require` |
| Cache | `type: local`, `ttl: 3600` — `cache_hit=True` ✅ |
| API Version | `AZURE_API_VERSION=2024-10-21` (GA) |

### Cache Pricing (90% off input)

| Model | Input/1M | Cache/1M |
|-------|:-------:|:--------:|
| gpt-5.4-nano | $0.20 | **$0.02** |
| gpt-5.4-mini | $0.75 | **$0.08** |
| gpt-5.4 | $2.50 | **$0.25** |
| gpt-5.2 | $1.75 | **$0.18** |

### MCP Servers (baked in)
- PostgreSQL (`@modelcontextprotocol/server-postgres`)
- Filesystem (`@modelcontextprotocol/server-filesystem` — `/app/workspace`)
- Time (`@guanxiong/mcp-server-time`)
- Context7 (`@upstash/context7-mcp`)

## Entra ID App Registration

| Item | Value |
|------|-------|
| Display Name | `appreg-entchat-owui-poc` |
| Client ID | `4881351e-d1a0-4228-a084-a0d6ef717740` |
| Client Secret | `u498Q~ve1ae4W0ERSwoeD5LIWywq6kD2GRPqVase` (exp. 2027-01-01) |
| Tenant ID | `5045d9c3-3b0b-4315-8594-64118bbd7495` |
| App ID URI | `api://genie.haadthip.com/4881351e-...` |
| Scope | `access_as_user` |
| Pre-authorized clients | ✅ `1fec8e78-bce4-4aaf-ab1b-5451cc387264` (Teams) + `5e3ce6c0-2b1f-4285-8d4b-75ee78787346` (Teams) |
| Redirect URIs (Web) | 6 URLs (OWUI + LiteLLM + DocWise callbacks) |
| Redirect URIs (SPA) | `https://genie.haadthip.com/teams-auth.html` ✅ |

## Teams App — GenieHaadthipChat

| Field | Value |
|-------|-------|
| App ID | `06f1c5da-92d8-421d-9839-a528508550f6` |
| Version | 1.0.0 |
| Content URL | `https://genie.haadthip.com/teams-auth.html` |
| Valid Domains | `genie.haadthip.com` |

### SSO Flow (B — Teams SDK v2 enabled)
```
Teams iframe → teams-auth.html → Teams SDK init

  ├─ Silent SSO: getAuthToken() → token ได้ → redirect OWUI OAuth → session
  │
  ├─ User click → handleSignIn()
  │   ├─ Teams popup (authenticate) → Entra OAuth → callback → session
  │   └─ fallback → window.open() → external browser
  │
  └─ Poll 3s จนเจอ session → redirect /
```

## Recurring Issues

| # | Problem | Fix |
|---|---------|-----|
| 1 | `@` `!` ใน DATABASE_URL | URL-encode: `@`→`%40`, `!`→`%21` |
| 2 | Container startup timeout | `WEBSITES_CONTAINER_START_TIME_LIMIT=1800` |
| 3 | OCI image index (multi-platform) | ใช้ AMD64 sub-manifest digest (`docker buildx imagetools inspect` → `grep -B2 "linux/amd64"`) |
| 4 | `DOCKER_CUSTOM_IMAGE_NAME` override digest | ลบ app setting นี้ — ใช้ digest ใน `linuxFxVersion` |
| 5 | Alembic migration `42e2978c7933` not found | `TRUNCATE alembic_version` + create `config(key TEXT PK, value JSON, updated_at BIGINT)` |
| 6 | LiteLLM Azure 404 (`api-version=2025-06-01`) | Set `AZURE_API_VERSION=2024-10-21` |
| 7 | LiteLLM `cache_hit=None` | Add `cache: True` / `cache_params.type: local` ใน config |
| 8 | LiteLLM model cost no cache discount | Add `cache_read_input_token_cost=input*0.1` (90% off) ต่อ model |
| 9 | MSI auth for ACR | SystemAssigned MI + `AcrPull` role + `acrUseManagedIdentityCreds: true` |

## Docker Compose Files

| File | What | When to use |
|------|------|-------------|
| **`docker-compose.local.yml`** | ✅ **Custom OWUI** (teams-auth) + LiteLLM (SQLite) | **Local dev — default** |
| `docker-compose.litellm.yml` | LiteLLM standalone (Azure PG) | Run LiteLLM separately |
| `docker-compose.openwebui.yml` | OWUI stock standalone | LiteLLM already running elsewhere |
| `docker-compose.full.yml` | ⚠️ Deprecated → ใช้ local.yml แทน | ❌ |

**Secrets:** ทั้งหมดใช้ `docker.env` (ยกเว้นที่ override ด้วย env vars)
```bash
# 🚀 Local dev (recommended)
docker compose -f config/docker-compose.local.yml up -d --build

# LiteLLM แยก (ถ้าต้องการ)
docker compose -f config/docker-compose.litellm.yml up -d
```

## Folder Guide

```
EnterpriseChat/
├── CONTEXT.md              ← ไฟล์นี้
├── README.md               ← Project overview
├── .gitignore
│
├── deploy/                 ← Docker, Compose, Deploy scripts
│   ├── docker/
│   │   ├── Dockerfile.teams
│   │   ├── Dockerfile.litellm
│   │   ├── docker-compose.local.yml
│   │   ├── docker-compose.litellm.yml
│   │   └── docker.env          ← Secrets (gitignored)
│   ├── litellm/
│   │   └── litellm_config*.yaml
│   └── scripts/
│       └── deploy-litellm-azure.sh
│
├── src/                   ← Open WebUI Functions
│   ├── pipes/             ← Knowledge base query pipes
│   ├── tools/             ← Enterprise Search, Calculator tools
│   ├── filters/           ← Token tracking filter
│   └── auth/              ← teams-auth.html (Teams SSO)
│
├── docs/                  ← Documentation, presentations
│   ├── genie-setup-manual.html/pdf
│   ├── genie-user-guide.pdf
│   ├── walkthrough-presentation.html
│   └── presentations/
│
├── scripts/               ← Ingestion & utility scripts
├── knowledge/             ← Source documents
│   ├── corporate/
│   └── hr-policies/
├── data/                  ← JSONL, exports, OWUI local data
└── assets/
    ├── screenshots/       ← UI screenshots (105+ files)
    └── icons/             ← Azure SVG icons
```

## Architecture Flow

```
User → genie.haadthip.com (App Gateway)
  → app-entchat-owui-poc-sand (Open WebUI)
    → app-litellm-poc-sand (LiteLLM Proxy /v1)
      → aif-entchat-poc-sand (Azure AI Foundry — GPT + Embeddings)
      → srch-entchat-poc-sand (Azure AI Search — enterprise-docs-idx)
    → psql-entchat-poc-sand (PostgreSQL — open_webui / litellm)
```

## Estimated Monthly Cost

| Service | Est. |
|---------|:----:|
| App Service B2 | ~$25-33 |
| PostgreSQL B1ms | ~$12 |
| AI Search Standard | ~$245 |
| Others (Storage, PE, DNS) | <$5 |
| **Total** | **~$290-310/mo** |
