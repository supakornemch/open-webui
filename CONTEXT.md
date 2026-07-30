# EnterpriseChat — Domain Context

> ## 📝 Recent Changes (2026-07-21)
>
> ### ✅ Custom Azure AI Search Vector DB Backend
> - **VECTOR_DB=azure-ai-search**: แทนที่ ChromaDB ด้วย Azure AI Search เป็น RAG vector store
> - **Index auto-create**: สร้าง index schema อัตโนมัติตอน insert ครั้งแรก (HNSW, dimension-detect)
> - **Search types**: รองรับ 4 โหมด — vector, fulltext, hybrid, semantic (ตั้งค่าผ่าน `AZURE_SEARCH_TYPE`)
> - **Namespace consolidation** (`AZURE_SEARCH_NAMESPACE_MODE=true`): รวม KBs/files/memories ลง shared indexes แค่ 3 ตัว (`owui-knowledge`, `owui-files`, `owui-memory`) — หลีกเลี่ยง 200-index limit
> - **Semantic search**: optional (`AZURE_ENABLE_SEMANTIC_SEARCH=true`) — auto-create semantic config บน index
> - **Implementation**: `app/patches/client.py` (+ `type.py`, `factory.py`)
>
> ### ✅ Teams Auth v5 — notifySuccess + open browser + signin loop fix
> - **notifySuccess**: เรียก `appInitialization.notifySuccess()` หลัง `initialize()` — กัน "There was a problem reaching this app" timeout
> - **ปุ่มเปิดเบราว์เซอร์ภายนอก**: ใช้ `microsoftTeams.app.openLink()` ใน Teams → fallback `window.open()`
> - **Signin success รัว ๆ**: guard `authCompleted` + `clearStaleTokenCookie()` — กัน polling/successCallback เรียกซ้ำ
> - **Cache-bust**: redirect ใช้ `/?ts=<timestamp>` ป้องกัน cache session เก่า
>
> ### ✅ Teams Auth v4 — SDK popup + session polling
> - **Auth flow**: เปลี่ยนจาก `window.open()` (Teams block) → `microsoftTeams.authentication.authenticate()` (Teams SDK จัดการ popup ให้)
> - **Polling**: poll `/api/v1/auths/` ทุก 2 วิ + เช็ค `token` cookie โดยตรง (httponly=false)
> - **Session check**: ตรวจ `data.token` ใน response body (แม่นยำกว่าแค่ `resp.ok`)
> - **Fallback**: ถ้า Teams SDK ไม่ available → `window.open()` ปกติ
> - **Timeout**: หยุด poll หลัง 3 นาที
> - **nginx**: CSP `frame-ancestors` + proxy OWUI :8081 ผ่าน :8080
>
> ### ✅ LiteLLM: Cache + Pricing + API Fix
> - **Proxy cache**: `cache: True` (local, TTL 3600) → `cache_hit=True` ✅
> - **Azure cache pricing**: ตรงตลาด (90% off): nano=$0.02, mini=$0.08, 5.4=$0.25, 5.2=$0.18 /1M
> - **API version**: `AZURE_API_VERSION=2024-10-21` (GA) แก้ 404 Resource not found
> - **DOCKER_CUSTOM_IMAGE_NAME**: ลบ override → ใช้ digest จริง
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

### VNet Integration

| Item | Value |
|------|-------|
| VNet | `VNET-HTC-SANBOX-SEA` (in `RG-HTC-SANDBOX-SEA`) |
| Subnet | `SNET-HTC-SANDBOX-APP-SEA` |
| OWUI | ✅ VNet-integrated (`app-entchat-owui-poc-sand`) |
| LiteLLM | ✅ VNet-integrated (`app-litellm-poc-sand`) |
| DocWise | ✅ VNet-integrated (`app-docwise-poc-sea`) |

**⚠️ VNet blocks all outbound internet.** This means:
- OAuth/OIDC flows (SSO to `login.microsoftonline.com`) → **fail** unless NSG outbound rule allows it
- Both OWUI `/oauth/microsoft/login` and LiteLLM `/sso/callback` need outbound HTTPS to `login.microsoftonline.com`
- Infra team must add NSG outbound rule for `login.microsoftonline.com` (Azure service tag or FQDN)
- PostgreSQL and AI Search use `publicAccess: Disabled` → accessible only via VNet private endpoints
- Direct Azure AI Foundry API calls from OWUI/LiteLLM are unaffected (Azure service endpoints)

### PostgreSQL
- **Host**: `psql-entchat-poc-sand.postgres.database.azure.com`
- **Admin**: `entchatadm` / `<in docker/.env — PG admin password>`
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
| Image | `owui-entchat-teams@sha256:...` (v0.10.2 + teams-auth.html + screenshots + Azure AI Search backend) |
| Auth | Microsoft Entra ID SSO (OIDC) — auto signup enabled |
| DB | `postgresql://entchatadm:***@psql-...:5432/open_webui?sslmode=require` |
| LiteLLM | OpenAI API: `https://app-litellm-poc-sand.azurewebsites.net` |
| Teams Auth | `/teams-auth.html` — Teams SDK v2 + popup + notifySuccess + ปุ่มเปิด browser ภายนอก |
| **Vector DB** | **Azure AI Search** (`srch-entchat-poc-sand`) — custom `AzureAISearchClient` |
| **Search type** | `AZURE_SEARCH_TYPE=hybrid` (vector+BM25) |
| **Namespace mode** | `AZURE_SEARCH_NAMESPACE_MODE=true` — shared indexes |
| **Semantic** | `AZURE_ENABLE_SEMANTIC_SEARCH=false` (optional, เพิ่ม cost)

### App Settings (key)
`WEBSITES_PORT=8080`, `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`, `WEBSITES_CONTAINER_START_TIME_LIMIT=1800`

### Vector DB Config (Azure AI Search)
| Setting | Value |
|---------|-------|
| `VECTOR_DB` | `azure-ai-search` |
| `AZURE_SEARCH_ENDPOINT` | `https://srch-entchat-poc-sand.search.windows.net` |
| `AZURE_SEARCH_ADMIN_KEY` | (secret — for CRUD operations) |
| `AZURE_SEARCH_TYPE` | `hybrid` (vector / fulltext / hybrid / semantic) |
| `AZURE_SEARCH_NAMESPACE_MODE` | `true` (shared indexes) |
| `AZURE_ENABLE_SEMANTIC_SEARCH` | `false` |
| `AZURE_SEARCH_API_VERSION` | `2024-07-01` |

### Vector DB Architecture
```
srch-entchat-poc-sand  (Azure AI Search, Standard tier)
├── owui-knowledge     ← ทุก Knowledge Base (filter by collection_key)
├── owui-files         ← ไฟล์แนบในแชท (filter by collection_key)
├── owui-memory        ← User memory (filter by collection_key)
├── enterprise-docs-idx ← Enterprise Search Tool (792+ chunks)
└── docwise-docs-v2    ← DocWise
```

**Custom client**: `app/patches/client.py` — implement `VectorDBBase` 10 methods
- Auto-create index schema with HNSW vector profile
- `collection_key` field สำหรับ OData server-side filter ใน namespace mode
- Schema auto-heal: ตรวจจับ index ที่ไม่มี `collection_key` แล้ว recreate

### Chunk Strategy & RAG Config

| Setting | Value |
|---------|-------|
| `CHUNK_SIZE` | `1000` (default) |
| `CHUNK_OVERLAP` | `100` (default) |
| Splitter | `RecursiveCharacterTextSplitter` |
| Tokenizer | `tiktoken` / `cl100k_base` |
| `RAG_TOP_K` | `3` (default) |
| Markdown header split | Enabled (by OWUI default) |
| PDF extraction | Azure Document Intelligence `prebuilt-read` |
| Embedding model | `text-embedding-3-large` (3072d) via Azure AI Foundry |

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
| Dashboard | `/ui` (login: `admin` / `<LITELLM_MASTER_KEY — see docker/.env>`) |
| DB | `postgresql://entchatadm:***@psql-...:5432/litellm?sslmode=require` |
| Cache | `type: local`, `ttl: 3600` — `cache_hit=True` ✅ |
| API Version | `AZURE_API_VERSION=2024-10-21` (GA) |
| SSO | Microsoft Entra ID — config ใน `litellm-config.yaml` |

### Cache Pricing (90% off input)

| Model | Input/1M | Cache/1M |
|-------|:-------:|:--------:|
| gpt-5.4-nano | $0.20 | **$0.02** |
| gpt-5.4-mini | $0.75 | **$0.08** |
| gpt-5.4 | $2.50 | **$0.25** |
| gpt-5.2 | $1.75 | **$0.18** |

### SSO Settings (in `litellm-config.yaml`)
```yaml
general_settings:
  sso_settings:
    - sso_type: "microsoft"
      client_id: os.environ/MICROSOFT_CLIENT_ID
      client_secret: os.environ/MICROSOFT_CLIENT_SECRET
      tenant: os.environ/MICROSOFT_TENANT
```
- SSO login initiated from admin UI (`/ui`) — no standalone `/sso` endpoint
- Callback: `/sso/callback` — token exchange requires outbound HTTPS to `login.microsoftonline.com` (VNet must allow)

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
| Client Secret | `<MICROSOFT_CLIENT_SECRET — see docker/.env>` (exp. 2027-01-01) |
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

### SSO Flow (v4 — Teams SDK popup + polling)
```
Teams iframe → teams-auth.html → Teams SDK init

  ├─ checkSession() → 200 + {token} → redirect /
  │
  └─ User click → handleSignIn()
      ├─ microsoftTeams.authentication.authenticate(url: /oauth/microsoft/login)
      │   Teams SDK จัดการ popup (ไม่โดน Teams iframe block)
      │
      ├─ Popup: Microsoft login → OWUI set `token` cookie (httponly=false)
      │   → OWUI redirect popup → /auth
      │
      └─ Parent: poll /api/v1/auths/ ทุก 2 วิ (+ check document.cookie)
          → เจอ session → redirect /

  Fallback (non-Teams browser): window.open() + polling เหมือนเดิม
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
| 10 | Azure AI Search index schema missing `collection_key` | Client auto-heals: ตรวจจับ schema mismatch → delete + recreate index |
| 11 | Azure AI Search propagation delay (new field) | `insert()` sleeps 3s after creating shared index with `collection_key` |
| 12 | OWUI v0.10.2 internal API is async | ใช้ `SessionLocal()` + raw SQL แทน `get_db()` + ORM สำหรับ bulk operations |
| 13 | VNet blocks outbound → SSO/OAuth fails | Infra team ต้อง add NSG outbound rule ให้ `login.microsoftonline.com` (Azure service tag `AzureActiveDirectory` หรือ FQDN) |
| 14 | DocWise 500/502 — `IndentationError` in `admin_views.py:302` | Python syntax error ป้องกัน Django app load — ต้อง fix source + rebuild Docker image |
| 15 | ASP B2 overload (92% CPU, 91% mem, 3 apps) | Scale up เป็น B3 หรือแยก ASP ต่อ app |
| 16 | OWUI alembic_version ตารางว่าง → migrations พัง | INSERT 48 migration version IDs ด้วยตนเอง (ไม่งั้น OWUI พยายามรัน migration ซ้ำบน tables ที่มีอยู่แล้ว) |

## Docker Compose Files

| File | What | When to use |
|------|------|-------------|
| **`docker/compose.yml`** | ✅ **Custom OWUI** (teams-auth) + LiteLLM (SQLite) | **Local dev — default** |

**Secrets:** ทั้งหมดใช้ `docker/.env` (gitignored, เทียบกับ `docker/.env.example`)
```bash
# 🚀 Local dev
docker compose -f docker/compose.yml up -d --build
```

## Folder Guide

```
EnterpriseChat/
├── CONTEXT.md              ← ไฟล์นี้
├── README.md               ← Project overview
├── .gitignore
│
├── app/                    ← Files copied into Docker image
│   ├── patches/            ← OWUI source patches (Azure AI Search VECTOR_DB backend)
│   │   ├── client.py       ← AzureAISearchClient (VectorDBBase impl)
│   │   ├── type.py         ← Patched VectorType enum
│   │   └── factory.py      ← Patched Vector factory
│   ├── auth/               ← Teams SSO (teams-auth.html, teams-auth-bridge.html)
│   └── static/             ← Static assets (genie-setup-manual.html)
│
├── docker/                 ← Docker build & deploy config
│   ├── Dockerfile.owui
│   ├── Dockerfile.litellm
│   ├── compose.yml         ← Main local dev compose
│   ├── nginx.conf          ← nginx reverse proxy config
│   ├── litellm-config.yaml
│   ├── litellm-config.local.yaml
│   └── .env                ← Secrets (gitignored)
│
├── functions/              ← Open WebUI functions (paste into admin panel)
│   ├── tools/              ← Enterprise Search, Calculator, etc.
│   ├── pipes/              ← Knowledge base query pipes
│   └── filters/            ← Token tracking filter
│
├── screenshots/            ← UI screenshots (served in container)
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
└── data/                  ← JSONL, exports, OWUI local data
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

## OWUI Knowledge Bases (on Azure AI Search)

| Index | Docs | Type | Source |
|-------|:----:|------|--------|
| `owui-knowledge` | 231 | HNSW vector (3072d) | All KBs consolidated (filtered by `collection_key`) |
| `owui-files` | 251 | HNSW vector (3072d) | Chat file attachments |
| `owui-memory` | 0 | HNSW vector (3072d) | User memory (not yet used) |
| `enterprise-docs-idx` | 792 | HNSW + Semantic | Enterprise Search Tool index |
| `docwise-docs-v2` | — | HNSW | DocWise document index |

**KB `2187df46` (Corporate Public Disclosure)**: มี 2 ไฟล์ — `README.md` + `htc-agm2024-minutes-en.pdf`

## Estimated Monthly Cost

| Service | Est. |
|---------|:----:|
| App Service B2 | ~$25-33 |
| PostgreSQL B1ms | ~$12 |
| AI Search Standard | ~$245 |
| Others (Storage, PE, DNS) | <$5 |
| **Total** | **~$290-310/mo** |

## Git Strategy

- **Branch model**
  - `main`: production — branch ที่ deploy จริง
  - `qas`: QA + UAT — branch สำหรับ QA testing และทดสอบก่อน deploy
  - `release/mvp`: feature integration — branch รวมงานพัฒนาหลัก
  - `feature/<topic>`: งานใหม่หรือ refactor ขนาดใหญ่
  - `fix/<topic>` หรือ `hotfix/<topic>`: แก้ bug / urgent patch
  - `chore/<topic>`: docs, dependency, maintenance ที่ไม่ใช่ feature

- **Flow**
  `feature/*` → `release/mvp` → `qas` → `main` (release)

- **Workflow**
  1. เริ่มจาก branch ล่าสุดของ `release/mvp` ก่อน: `git checkout release/mvp && git pull`
  2. สร้าง branch ใหม่: `git checkout -b feature/<topic>`
  3. Commit ให้เล็กและกระชับ โดยใช้ prefix แบบ `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`
  4. Push branch และเปิด Pull Request ไปยัง `release/mvp`
  5. Merge ด้วย squash สำหรับ branch เล็ก/ปานกลาง
  6. `release/mvp` → merge เข้า `qas` (QA + UAT testing)
  7. `qas` → merge เข้า `main` (release) + tag `vX.Y.Z`
