# EnterpriseChat — Domain Context

## Glossary

| Term | Definition |
|---|---|
| **Open WebUI** | Self-hosted AI interface platform (open-source) สำหรับคุยกับ LLMs ผ่าน Ollama หรือ OpenAI-compatible APIs พร้อม RAG capabilities |
| **Azure AI Search** | Managed search-as-a-service — full-text + vector + hybrid search + semantic ranker + agentic retrieval (Knowledge Base) |
| **Azure Container Apps** | Fully managed serverless container platform — scale-to-zero, per-second billing, built-in TLS, no Kubernetes to manage |
| **Container Apps Environment** | Shared boundary สำหรับ container apps หลายตัว — จัดการ networking, logs, shared configuration |
| **Consumption Plan** | Billing model แบบ pay-per-use — จ่ายเฉพาะ vCPU-sec + GiB-sec ที่ใช้จริง |
| **Scale-to-Zero** | Container apps หยุด run เมื่อไม่มี traffic = $0 cost |
| **LLM Backend** | Provider ที่ให้ AI model capabilities — Azure OpenAI (cloud) หรือ Ollama (self-hosted) |
| **Managed TLS** | ฟรี SSL/TLS certificate จาก Azure Container Apps (DigiCert-backed), auto-issue + auto-renew |
| **IR Document** | Investor Relations document — สิ่งพิมพ์ของบริษัทเพื่อสื่อสารกับนักลงทุน ได้แก่ annual report, financial statement, SET/SEC filing, press release |
| **Document Type (doc_type)** | ชนิดของ IR document ตามวัตถุประสงค์ทางกฎหมาย/การเผยแพร่: `annual-report`, `form-56-1`, `financial-data`, `company-disclosure`, `press-release` |
| **Subject Area (category)** | หัวข้อ/เนื้อหาเชิงธุรกิจที่ document หรือ chunk กล่าวถึง: `financial`, `governance`, `business`, `sustainability`, `risk`, `company-profile` |
| **Report Year (report_year)** | ปีงบการเงินที่รายงานครอบคลุม (สำหรับ annual reports, financial data) |
| **Index Projection** | Azure AI Search mechanism ที่ 1 blob → N search documents (one per chunk) — ใช้ใน skillset ที่มี split skill |
| **Azure AI Document Intelligence** | Managed AI service for PDF/Office/image text extraction — prebuilt layout model outputs markdown with table structure, headings, figures preserved |
| **Layout Model** | Prebuilt model ใน Document Intelligence — extracts text + tables as markdown `| col | col |`, headings as `##`, figures as `<figure><figcaption>` |
| **Unified Ingestion** | `scripts/unified-ingestion.py` — single Python script for ALL corpuses + ALL file types (.pdf/.doc/.docx/.xls/.xlsx/.jpg/.png/.pptx) → AI Search |
| **E-Expense** | Haadthip internal expense management system — การขอแผนการเดินทาง, เบิกทดรองจ่าย, เคลียร์ค่าใช้จ่าย, ค่ารักษาพยาบาล |
| **E-Expense FAQ Index** | Azure AI Search index (`eexpense-faq-idx`) — 42 flattened FAQ documents from E-Expense chatbot Q&A decision tree, hybrid search (BM25 + vector 3072d + semantic) |
| **E-Expense Chatbot** | FAQ chatbot engine (`scripts/eexpense-chatbot.py`) — hybrid search + state machine for multi-turn clarification |
| **MiHCM** | Haadthip HR system (https://haadthip.mihcm.com) — source of HR documents: policies, forms, manuals, regulations, announcements |
| **Open WebUI Pipe** | Open WebUI function type ที่ทำหน้าที่เป็น "model" — รับ query → ค้นหา KB → เรียก LLM → คืนคำตอบ โดย Open WebUI มองเห็นเป็น Model ตัวหนึ่ง |
| **Open WebUI Tool** | Open WebUI function type (`class Tools`) — expose function ให้ model เรียกผ่าน Native/Agentic Mode (function calling) ต่างจาก Pipe ตรงที่ model เป็นคนตัดสินใจเองว่าจะเรียกเมื่อไหร่ |
| **Open WebUI Function** | Code (Python) ที่ register ใน Open WebUI — มี 3 type: `pipe` (ทำตัวเป็น model), `tool` (เรียกผ่าน function calling), `filter` (middleware), `action` (ปุ่ม UI) |
| **Open WebUI Model** | Record ในตาราง `model` ของ Open WebUI PostgreSQL — เก็บ metadata, capabilities, params (รวมถึง tool definitions ถ้ามี) |
| **Native Mode (Agentic Mode)** | Default ตั้งแต่ Open WebUI v0.10+ — model จัดการ agentic loop เอง (คิด→เรียก tool→รับผล→คิด→...→ตอบ) โดยที่ dev ไม่ต้องเขียน loop เอง ใช้ function calling แบบ native ของ model |
| **Floating Agent** | AI ที่ทำงานอัตโนมัติแบบ multi-step — วางแผน → เรียก tool → สังเกตผล → วางแผนต่อ → ... → รายงานผล โดยไม่ต้องมีคนคอยบอกทีละขั้น |

---

## Document Corpus

Source documents อยู่ใน `documents/` 3 กลุ่ม:

### 1. `documents/haadthip-public/` — General Corporate Docs (23 ไฟล์)

| Category | Path | Description | Docs | Visibility |
|----------|------|-------------|------|------------|
| Security | `01-security/` | MFA, VPN, session management | 6 | 🔒 Internal |
| Email | `02-email/` | Exchange / O365 setup & management | 8 | 🔒 Internal |
| Meeting Room | `03-meeting-room/` | Board meeting room booking & usage | 4 | 🔒 Internal |
| IT Policy | `04-it-policy/` | DLP endpoint policy | 2 | 🔒 Internal |
| Public Disclosure | `05-public-disclosure/` | SET/SEC regulatory filings | 4 | ✅ Public |

> 📌 18 docs ถูก index ใน `haadthip-public-idx-v2` (via blob container `haadthip-public`)

### 2. `documents/sap-hip/` — SAP HIP Manuals (32 ไฟล์)

SAP Hana Implementation Project (HIP) manuals — คำแนะนำการใช้งาน SAP สำหรับสาขา:

| Detail | Value |
|--------|-------|
| Source | `documents/sap-hip/` |
| Container | `sap-docs` (blob) |
| Total files | 32 (19 หลัก + 13 ใน `file-pdf/`) |
| Total size | ~12.69 MB |
| Content | Thai text instructions + SAP UI screenshots (minimal extractable text) |
| TCodes | `mb52`, `/n/hip/fiar06`, `/n/hip/fiaa02`, `/n/hip/fiar15`, etc. |
| Pipeline | DS: `sap-docs-ds` → Skillset: `sap-docs-skillset` → Index: `sap-docs-idx` → Indexer: `sap-docs-idxr` |
| KS | `sap-docs-ks` (`searchIndex → sap-docs-idx`, semantic: `sap-docs-semantic`) |

> ⚠️ **Known limitation**: Most content is embedded in screenshots — DocumentExtractionSkill ได้เฉพาะ text + Tcode (ไม่รวม OCR text รูปภาพ)

### Key Characteristics

- **Languages**: English + Thai mix. Public disclosures are EN only. IR docs are mostly EN.
- **Formats**: PDF, DOCX, PPTX.
- **Visibility**: haadthip-public 01–04 internal, 05 public. SAP docs internal. IR docs ✅ Public (from company website).

### 3. `documents/haadthip-ir/` — Investor Relations Documents (31 ไฟล์, ~274 MB)

**Source:** https://www.haadthip.com/en/investor-relations/document/annual-reports  
**Downloaded:** 2026-07-06  
**Language:** EN (หลัก), TH (Form 56-1 ปี 2012-2020)  
**Format:** PDF

| Subdirectory | Description | Files | Size |
|-------------|-------------|:----:|:----:|
| `01-annual-reports/` | One Report (Form 56-1) + Annual Reports 2012–2025 | 24 | 233 MB |
| `02-financial-data/` | Earning Results + Fact Sheet Q1/2026 | 2 | 40 MB |
| `03-company-disclosures/` | MD&A, F45, AGM Minutes, Director Change | 5 | 776 KB |

**Key files for ingestion:**
- `htc-one-report2025-en.pdf` (29 MB) — **ข้อมูลธุรกิจล่าสุด** ครอบคลุมทุกด้าน
- `htc-earning-results-q1-2026.pdf` (3.1 MB) — การเงินไตรมาสล่าสุด
- `htc-mda-q1-2026.pdf` (308 KB) — MD&A คำอธิบายผลประกอบการ

> 📖 ดูรายละเอียดเพิ่มเติมที่ `documents/haadthip-ir/README.md`

### PoC Ingestion Priority

For the **chat from AI search** PoC, recommended order:

1. `haadthip-ir/01-annual-reports/htc-one-report2025-en.pdf` — latest & broadest (replaces 2024)
2. `haadthip-ir/02-financial-data/htc-earning-results-q1-2026.pdf` — latest financials
3. `haadthip-ir/02-financial-data/htc-factsheet-3m2026.pdf` — key metrics snapshot
4. `05-public-disclosure/htc-one-report-2024-en.pdf` — 2024 reference (258 pages)
5. `05-public-disclosure/htc-sustainability-report-2024-en.pdf` — ESG + rich graphics (145 pages)
6. `haadthip-ir/03-company-disclosures/htc-mda-q1-2026.pdf` — management analysis

See `documents/haadthip-public/README.md` and `documents/haadthip-ir/README.md` for full details.

---

## E-Expense FAQ Search

### Overview

นำ Q&A chatbot E-Expense (จาก Excel 2 sheets: คำถาม + คำตอบ) มา flatten จาก Decision Tree เป็น FAQ documents แล้ว upload เข้า Azure AI Search สำหรับ hybrid search (BM25 + vector + semantic)

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Excel Q&A   │────▶│  Flatten Script  │────▶│  eexpense-faq.jsonl │
│  (Decision   │     │  (Trace paths)   │     │  (42 docs)          │
│   Tree)      │     └──────────────────┘     └────────┬────────────┘
└──────────────┘                                       │
                                                       ▼
                                             ┌──────────────────┐
                                             │  Embed + Upload  │
                                             │  (text-embedding │
                                             │   3-large, 3072d)│
                                             └────────┬─────────┘
                                                      │
                                                      ▼
┌──────────────────┐                      ┌─────────────────────┐
│  Chatbot Engine  │◀─────────────────────│  Azure AI Search    │
│  (FAQ + State    │    Hybrid Search     │  eexpense-faq-idx   │
│   Machine)       │    BM25+Vector+Sem   │                     │
└──────────────────┘                      └─────────────────────┘
```

### Files

| File | Purpose |
|---|---|
| `scripts/flatten-eexpense-qa.py` | Parse Excel → Trace decision tree paths → Output JSONL |
| `scripts/create-eexpense-index.py` | Create `eexpense-faq-idx` with full schema |
| `scripts/ingest-eexpense-faq.py` | Embed documents (text-embedding-3-large) + upload |
| `scripts/eexpense-chatbot.py` | Chatbot engine: hybrid search + state machine |
| `scripts/setup-eexpense-search.sh` | All-in-one pipeline script |
| `data/eexpense-faq.jsonl` | 42 flattened FAQ documents |
| `docs/eexpense-search-architecture.md` | Full architecture reference |

### Index Schema (`eexpense-faq-idx`)

| Field | Type | Purpose |
|---|---|---|
| `id` | `Edm.String` (Key) | Unique doc ID: `{rootQ}_{ansId}_{hash}` |
| `question` | `Edm.String` (`th.lucene`) | Enriched: root question + conditions |
| `answer` | `Edm.String` (`th.lucene`) | Full answer text |
| `shortAnswer` | `Edm.String` (`th.lucene`) | 1-sentence summary |
| `category` | `Edm.String` | 11 categories, filterable + facetable |
| `keywords` | `Collection(Edm.String)` | Search keywords |
| `conditions` | `Collection(Edm.String)` | Branching conditions, filterable |
| `contextQuestions` | `Collection(Edm.String)` | Breadcrumb trail of questions |
| `sourceId` | `Edm.String` | Original ANS id from Excel |
| `choiceType` | `Edm.String` | `button` or `info` |
| `contentVector` | `Collection(Edm.Single)` | 3072d embedding (text-embedding-3-large) |

**Vector Search:** HNSW, cosine similarity, m=4, efConstruction=400, efSearch=500  
**Semantic Config:** `eexpense-semantic-config` (title: question, content: answer + keywords)

### Flattening Strategy

จาก Decision Tree (33 Q-nodes → 27 roots, 39 answers):

```
Q1: ขอล่วงหน้ากี่วัน? → Q2: มีทดรองจ่ายไหม?
  ├─ A: มี → ANS1
  └─ B: ไม่มี → ANS2
```

Flatten เป็น 2 documents โดย:
- **Root question** เป็น main topic (ไม่ใช่ branching node)
- **Conditions** เก็บ array ของ choices ที่ต้องเลือก
- **Unique ID** ใช้ `{rootQ}_{ansId}_{hash}` ป้องกัน collision (Q2/Q4/Q16 ถามเหมือนกันแต่ root ต่างกัน)
- เฉพาะ Q nodes ที่ไม่มีใครชี้มาเท่านั้นเป็น entry point (27 จาก 33)

### Categories (11 หมวดหมู่, 42 docs)

| Category | Count |
|---|---|
| ค่าอาหาร/เบี้ยเลี้ยง | 12 |
| การแก้ไข/ยกเลิกเอกสาร | 6 |
| ผู้ร่วมเดินทาง | 5 |
| แผนการเดินทาง | 4 |
| การขอทดรองจ่าย | 3 |
| สิทธิ์การเบิก | 3 |
| การอนุมัติ | 2 |
| Cost Center | 2 |
| ข้อมูลระบบ | 2 |
| ไฟล์แนบ | 2 |
| ประวัติเอกสาร | 1 |

### Search Strategy

```
User Query
    ├──▶ Quick Keyword Lookup (QUICK_MAP, no API call)
    ├──▶ BM25 Full-Text Search (th.lucene analyzer)
    │        +
    ├──▶ Vector Search (text-embedding-3-large, cosine)
    │        ▼
    │    RRF Fusion → Semantic Ranker
    ▼
  State Machine
    ├── 1 result, no conditions → Direct Answer
    ├── Multiple variants → Ask Clarification (buttons)
    └── No results → Fallback Response
```

### Deployment

```bash
# Full pipeline
export AZURE_SEARCH_KEY="..."
export AZURE_OPENAI_API_KEY="..."
./scripts/setup-eexpense-search.sh

# Or step-by-step
python3 scripts/flatten-eexpense-qa.py --excel "path/to/excel.xlsx"
python3 scripts/create-eexpense-index.py --force
python3 scripts/ingest-eexpense-faq.py --reset

# Test chatbot
python3 scripts/eexpense-chatbot.py
```

**Deployed:** 2026-07-07 — 42 documents in `eexpense-faq-idx` on `srch-entchat-poc-sand`

---

## Related Links

- **Haad Thip IR site:** https://www.haadthip.com/en/investor-relations/document/annual-reports
- **SET factsheet (HTC):** https://www.set.or.th/en/market/product/stock/quote/htc/factsheet
- **SEC iDisclose (HTC):** https://market.sec.or.th/public/idisc/en/Viewmore/fs-norm?uniqueIDReference=0000000697&searchSymbol=HTC

---

## Azure Infrastructure — Enterprise Chat PoC

### Subscription

- **Name:** SUB-HTC-SANDBOX-DC
- **ID:** `82f65db7-e209-4eb1-98fe-3e56bc45607a`
- **Tenant:** `5045d9c3-3b0b-4315-8594-64118bbd7495`
- **Region:** Southeast Asia (`southeastasia`)

### Resource Group: `RG-ENTCHAT-POC-SAND-SEA`

| Resource | Name | SKU / Tier | Type | Shared? |
|----------|------|-----------|------|---------|
| App Service Plan | `asp-entchat-poc-sand` | B2 Linux (2 vCPU, 3.5 GB) | linux, Basic | ✅ |
| Storage Account | `staentchatdoc` | Standard_LRS | StorageV2, Hot | ✅ |
| PostgreSQL | `psql-entchat-poc-sand` | Standard_B1ms, v18, 32GB | Flexible Server | ✅ (2 DBs) |
| AI Search | `srch-entchat-poc-sand` | **Standard** | Search Service | ✅ |
| AI Foundry Hub + AI Services | `aif-entchat-poc-sand` | S0 (AIServices) | Hub + AIServices (merged) | ✅ |
| AI Foundry Project | `proj-entchat-poc-sand` | Basic (free) | Project (under Hub) | ✅ |
| Web App — Open WebUI | `app-entchat-owui-poc-sand` | Container (linux) | app,linux,container | ❌ |
| Web App — DocWise | `app-docwise-poc-sand` | Container (linux) | app,linux,container | ❌ |
| Private Endpoints | `PVE-*` | — | Private Endpoints + NICs | — |
| Private DNS Zones | `privatelink.*` | — | DNS zones for PE | — |

> ⚠️ Container Registry (`crentchatpocsea`) และ IR resources ไม่ได้ถูก re-provision ใน Sandbox

### PostgreSQL

| Item | Value |
|------|-------|
| Host | `psql-entchat-poc-sand.postgres.database.azure.com` |
| Admin | `entchatadm` |
| Password | `DocWiseP@ssw0rd2026!` (URL-encode @ as %40, ! as %21) |
| Databases | `open_webui` (Open WebUI), `docwise` (DocWise) |
| Version | 18 |
| Firewall | Private Endpoint (no public access) |

### Model Deployments (บน `aif-entchat-poc-sand`)

| Deployment | Model | Version | Use |
|-----------|-------|---------|-----|
| `deploy-gpt-5.4-nano` | gpt-5.4-nano | 2026-03-17 | KB agentic retrieval (query planning) — cheapest |
| `deploy-gpt-5.4-mini` | gpt-5.4-mini | 2026-03-17 | General-purpose chat (Open WebUI direct) |
| `deploy-gpt-5.4` | gpt-5.4 | 2026-03-05 | **Pipe LLM generation** (better quality for Thai + citations) |
| `deploy-gpt-5.2` | gpt-5.2 | 2025-12-11 | Fallback/legacy |
| `deploy-embedding-3-large` | text-embedding-3-large | 1 | Vector embeddings |

> 💡 **KB ใช้ `deploy-gpt-5.4-nano`** สำหรับ query planning (agentic reasoning) — ถูกสุด, ~29K reasoning tokens/query  
> 💡 **Pipe ใช้ `deploy-gpt-5.4`** สำหรับ final answer generation — คุณภาพดีกว่า nano สำหรับภาษาไทย + การอ้างอิงเอกสาร

> ⚠️ DeepSeek models **NOT** available on AIServices kind — GPT series only.

### Container Registry

- **Name:** `acrentchatpocsand` (Basic, Southeast Asia)
- **Admin:** ❌ Not enabled
- **Images:** `litellm-entchat:latest` (LiteLLM custom image with baked-in config)
- **Role:** User `supakorn.em@haadthip.com` has `AcrPush` (push/pull OK, can't enable admin or assign roles)

### Open WebUI

- **URL:** https://app-entchat-owui-poc-sand.azurewebsites.net
- **Container:** `ghcr.io/open-webui/open-webui:main` (port 8080)
- **Auth:** SSO with Microsoft Entra ID (OIDC) — auto signup enabled
- **File Storage:** Azure Blob Storage (`staentchatdoc`) — **MI not yet configured**
  - Container `open-webui-files` hasn't been created yet
  - Need to: create container, enable SystemAssigned MI on Web App, assign `Storage Blob Data Contributor`
- **DATABASE_URL:** `postgresql://entchatadm:DocWiseP%40ssw0rd2026%21@psql-entchat-poc-sand.postgres.database.azure.com:5432/open_webui?sslmode=require`
  - ⚠️ Password ต้อง URL-encode: `@` → `%40`, `!` → `%21`

### LiteLLM Proxy

> 📐 ดูภาพรวมที่ [Architecture](#architecture-ที่แนะนำ)

- **URL:** https://app-litellm-poc-sand.azurewebsites.net
- **Container:** `acrentchatpocsand.azurecr.io/litellm-entchat:latest` (custom, linux/amd64, port 4000)
- **Dockerfile:** `config/Dockerfile.litellm` — extends `ghcr.io/berriai/litellm:v1.83.3-stable`, embeds `config/litellm_config.yaml`, CMD `--config /app/config.yaml --port 4000`
- **Deploy Script:** `scripts/deploy-litellm-azure.sh`
- **Managed Identity:** SystemAssigned `a23bb0fd` (มี `AcrPull` บน ACR → image pull ผ่าน MI ✅)
- **Config:** เหมือน `app-docwise-poc-sand` — MI pull ACR + `acrUseManagedIdentityCreds: true`
- **Database:** `psql-entchat-poc-sand / litellm` (สร้างใหม่)
- **App Settings สำคัญ:**
  - `DATABASE_URL` = `postgresql://entchatadm:***@psql-entchat-poc-sand.postgres.database.azure.com:5432/litellm?sslmode=require`
  - `MICROSOFT_CLIENT_ID` = `4881351e-d1a0-4228-a084-a0d6ef717740` (ตัวเดียวกับ OWUI)
  - `MICROSOFT_CLIENT_SECRET` = `***`
  - `MICROSOFT_TENANT` = `5045d9c3-3b0b-4315-8594-64118bbd7495`
  - `PROXY_BASE_URL` = `https://app-litellm-poc-sand.azurewebsites.net`
- **SSO:** Entra ID (pending: เพิ่ม redirect URI `https://app-litellm-poc-sand.azurewebsites.net/sso/callback` ใน App Registration)
- **Endpoints:**
  - API: `/v1` — OpenAI-compatible
  - UI: `/ui` — Dashboard (login: `admin` / `sk-litellm-poc-master-key`)

**Build & Push (หลังจากแก้ code):**

```bash
docker build --platform linux/amd64 -f config/Dockerfile.litellm -t litellm-entchat:latest config/
az acr login -n acrentchatpocsand
docker tag litellm-entchat:latest acrentchatpocsand.azurecr.io/litellm-entchat:latest
docker push acrentchatpocsand.azurecr.io/litellm-entchat:latest
az webapp restart -g RG-ENTCHAT-POC-SAND-SEA -n app-litellm-poc-sand
```

**Verify:**

```bash
curl https://app-litellm-poc-sand.azurewebsites.net/v1/models \
  -H "Authorization: Bearer sk-litellm-poc-master-key"
```

#### Local Open WebUI (Docker)

ใช้ Docker Compose สำหรับรัน Open WebUI บน local machine — มี 2 แบบ:

| File | Description | Services |
|------|-------------|----------|
| `config/docker-compose.openwebui.yml` | Open WebUI อย่างเดียว — ต่อ LiteLLM ที่รันอยู่แล้ว | Open WebUI |
| `config/docker-compose.full.yml` | Full stack — Open WebUI + LiteLLM + PostgreSQL | Open WebUI + LiteLLM + PostgreSQL |

**Quick Start (Full Stack):**
```bash
export AZURE_API_KEY="<your-key>"
docker compose -f config/docker-compose.full.yml up -d
# Open WebUI: http://localhost:3000
# LiteLLM UI:  http://localhost:4000/ui
```

**Quick Start (Open WebUI only — ต้องมี LiteLLM รันอยู่แล้ว):**
```bash
docker compose -f config/docker-compose.openwebui.yml up -d
# Open WebUI: http://localhost:3000
# (เชื่อมต่อไป LiteLLM ที่ localhost:4000 อัตโนมัติ)
```

### Open WebUI — Token Tracking Limitation ⚠️

Open WebUI มี **Analytics Dashboard** (`Admin Panel → Analytics`) สำหรับ monitor token usage แต่มีข้อจำกัดสำคัญ:

**ปัญหา:** Analytics dashboard แสดง token usage เป็น **0** สำหรับ API clients (Azure Foundry, Continue.dev, curl ฯลฯ) — ใช้งานได้เฉพาะการแชทผ่าน **Web UI** เท่านั้น

**Root cause:** Analytics pipeline ต้องใช้ `chat_id`, `session_id`, `message_id` — ซึ่ง API clients ไม่ส่งมา (จัดการ conversation state เอง) → `event_emitter` เป็น `None` → streaming handler fallback ไป passthrough branch ที่ไม่มีการ track usage และไม่เขียน DB

| เส้นทาง | Token Tracked | DB Write |
|---------|:------------:|:--------:|
| Web UI (เบราว์เซอร์) | ✅ Yes | ✅ Yes |
| API Client (Azure Foundry ฯลฯ) | ❌ No | ❌ No |

**สถานะ:** Issue [#21675](https://github.com/open-webui/open-webui/issues/21675) ยัง **OPEN** อยู่ (pinned) — มี PR [#25650](https://github.com/open-webui/open-webui/pull/25650) merge เข้า `dev` branch (29 มิ.ย. 2569) แต่ยังไม่ออกใน `main`/`latest` และถึงจะออกก็แก้แค่ให้ outlet filters ทำงานกับ API calls ได้ — ไม่ได้เพิ่ม API calls เข้า analytics dashboard โดยตรง

#### วิธีแก้ไขชั่วคราว: Filter Function `filter-token-tracker.py` 🔧

ใช้ Filter Function เพื่อ track token usage ได้ทันที — ไม่ต้องอัปเกรด Open WebUI หรือเพิ่ม infrastructure:

**ไฟล์:** `config/filter-token-tracker.py`

**ความสามารถ:**
| Feature | `:main` (current) | `:dev` (future) |
|---------|:---:|:---:|
| Track request (inlet) — ทุก channel | ✅ | ✅ |
| Track response tokens (outlet) — Web UI | ✅ | ✅ |
| Track response tokens (outlet) — **API calls** | ❌ | ✅ |
| Extract actual `usage` from OpenAI response | ✅ | ✅ |
| Latency tracking | ✅ | ✅ |
| Structured JSON logging to Docker logs | ✅ | ✅ |

**วิธีติดตั้ง:**
1. Open WebUI → Admin Panel → Functions → **Add Function**
2. วางโค้ดจาก `config/filter-token-tracker.py`
3. Save → เปิด toggle ให้ทำงาน
4. ดู logs: `docker logs open-webui | grep TOKEN-TRACK`

**Valves (ปรับแต่งได้):**
| Valve | Default | Description |
|-------|---------|-------------|
| `enabled` | `true` | เปิด/ปิด token tracking |
| `log_level` | `"info"` | `"info"` = summary, `"debug"` = full body |

**วิธีดู Usage:** ดู Docker logs หรือใช้ `docker logs -f open-webui | grep TOKEN-TRACK` สำหรับ real-time monitoring

**ข้อจำกัดใน `:main` branch:** `outlet()` ยังไม่ทำงานสำหรับ direct API calls → output token tracking สำหรับ Azure Foundry จะเป็น 0 จนกว่าจะอัปเกรดเป็น `:dev` — แต่ `inlet()` ทำงานได้ทันทีและให้ข้อมูล request + estimated input tokens + latency

#### คำแนะนำระยะยาว: ใช้ LiteLLM Proxy 🚀

**[LiteLLM](https://docs.litellm.ai/)** เป็น proxy สำหรับ LLM providers — รองรับ OpenAI, Azure, Anthropic, และอื่นๆ 100+ providers ด้วย interface แบบ unified OpenAI-compatible API

**ประโยชน์ที่ได้:**
- ✅ **Token tracking + Cost tracking** — แยกตาม user, team, model, project
- ✅ **Budget limits** — ตั้ง limit การใช้ token ต่อ user/team (hard cap)
- ✅ **Dashboard** — มี UI สำหรับ monitor usage, cost, latency
- ✅ **Rate limiting** — กัน API abuse
- ✅ **Load balancing** — กระจาย request ข้าม multiple deployments
- ✅ **Logging** — เก็บทุก request/response สำหรับ audit

**Architecture ที่แนะนำ:**

```
                         Azure (RG-ENTCHAT-POC-SAND-SEA, Southeast Asia)
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                                                                             │
 │  ┌──────────────────────────┐        ┌──────────────────────────┐          │
 │  │     Open WebUI           │        │       Open WebUI         │          │
 │  │     (Azure Web App)      │        │     (Local Docker)       │          │
 │  │  app-entchat-owui-poc    │        │   localhost:3000         │          │
 │  │  Entra ID SSO ✓          │        │   No SSO (signup)       │          │
 │  │  PostgreSQL ✓            │        │   SQLite (local)        │          │
 │  └──────────┬───────────────┘        └──────────┬───────────────┘          │
 │             │                                   │                          │
 │             │  OpenAI API (/v1)                  │  OpenAI API (/v1)        │
 │             │                                   │                          │
 │             ▼                                   ▼                          │
 │  ┌─────────────────────────────────────────────────────────────────┐       │
 │  │                        LiteLLM Proxy                             │       │
 │  │                   app-litellm-poc-sand                           │       │
 │  │                   (Azure Web App, Port 4000)                     │       │
 │  │                                                                  │       │
 │  │  ▪ Image: acr...azurecr.io/litellm-entchat:latest (linux/amd64) │       │
 │  │  ▪ Auth: Master Key + Entra ID SSO (pending redirect URI)       │       │
 │  │  ▪ DB:   psql-entchat-poc-sand / litellm                        │       │
 │  │  ▪ MI:   SystemAssigned (ACR pull ✓)                            │       │
 │  │                                                                  │       │
 │  │  Models proxied:                                                 │       │
 │  │    gpt-5.4-nano  gpt-5.4-mini  gpt-5.4  gpt-5.2  embedding-3   │       │
 │  │                                                                  │       │
 │  │  UI:     /ui           (Dashboard: token usage, cost, keys)      │       │
 │  │  API:    /v1           (OpenAI-compatible endpoint)              │       │
 │  └───────────────────────┬─────────────────────────────────────────┘       │
 │                          │                                                  │
 │                          │  Azure OpenAI API (/v1)                          │
 │                          │  api-key: MI (planned)                           │
 │                          ▼                                                  │
 │  ┌─────────────────────────────────────────────────────────────────┐       │
 │  │                     Azure AI Foundry                              │       │
 │  │                 aif-entchat-poc-sand                              │       │
 │  │          https://aif-entchat-poc-sand.cognitiveservices.azure.com │       │
 │  │                                                                  │       │
 │  │  Deployments:                                                    │       │
 │  │    deploy-gpt-5.4-nano      GPT-5.4 Nano   (query planning)      │       │
 │  │    deploy-gpt-5.4-mini      GPT-5.4 Mini   (general chat)        │       │
 │  │    deploy-gpt-5.4           GPT-5.4        (Pipe final answer)   │       │
 │  │    deploy-gpt-5.2           GPT-5.2        (fallback/legacy)     │       │
 │  │    deploy-embedding-3-large Text Embed 3   (vector 3072d)        │       │
 │  └─────────────────────────────────────────────────────────────────┘       │
 │                                                                             │
 │  ┌───────────────────────┐    ┌──────────────────────┐                      │
 │  │  Azure AI Search      │    │  PostgreSQL           │                      │
 │  │  srch-entchat-poc-sand│    │  psql-entchat-poc-sand│                      │
 │  │  KB: haadthip-kb      │    │  DBs: open_webui      │                      │
 │  │       sap-docs-ks     │    │       docwise         │                      │
 │  │       ir-docs-ks      │    │       litellm  (new!) │                      │
 │  │       mihcm-hr-ks     │    │                       │                      │
 │  └───────────────────────┘    └──────────────────────┘                      │
 │                                                                             │
 └─────────────────────────────────────────────────────────────────────────────┘

Flow:
  User/API Client → Open WebUI ──/v1/chat/completions──▶ LiteLLM ──Azure API──▶ AI Foundry (GPT)
                                        │
                                  Token tracking
                                  Cost monitoring
                                  Key management
                                  Rate limiting
```

### End-to-End Communication

| จาก | ไป | Protocol | Auth |
|-----|-----|----------|------|
| User Browser | Open WebUI (`:443`) | HTTPS | Entra ID SSO (OIDC) |
| Open WebUI | LiteLLM (`:443/v1`) | HTTPS | `Bearer sk-litellm-poc-master-key` |
| LiteLLM | Azure AI Foundry | HTTPS | `api-key` (key-based) |
| LiteLLM | PostgreSQL (`:5432`) | TLS | `entchatadm` / password |
| LiteLLM | ACR (image pull) | HTTPS | Managed Identity |

### Deployment URLs

| Service | URL | Auth |
|---------|-----|------|
| **Open WebUI** | https://app-entchat-owui-poc-sand.azurewebsites.net | Entra ID SSO |
| **LiteLLM API** | https://app-litellm-poc-sand.azurewebsites.net/v1 | `Bearer <master-key>` |
| **LiteLLM UI** | https://app-litellm-poc-sand.azurewebsites.net/ui | `admin` / master-key (or Entra SSO) |
| **AI Foundry** | https://aif-entchat-poc-sand.cognitiveservices.azure.com | `api-key` |

### LiteLLM Models

| Model Name | Azure Deployment | Use Case |
|-----------|-----------------|----------|
| `gpt-5.4-nano` | `deploy-gpt-5.4-nano` | KB query planning (cheapest) |
| `gpt-5.4-mini` | `deploy-gpt-5.4-mini` | General-purpose chat |
| `gpt-5.4` | `deploy-gpt-5.4` | Pipe final answer (best quality) |
| `gpt-5.2` | `deploy-gpt-5.2` | Fallback/legacy |
| `text-embedding-3-large` | `deploy-embedding-3-large` | Vector embeddings (3072d) |

> **Open WebUI → LiteLLM model mapping:** Open WebUI ใช้ OpenAI API connection ต่อไปที่ LiteLLM `/v1` — model ทั้ง 5 ตัวจะโผล่ใน dropdown ให้เลือกใช้ได้

**Deployment Options:**
- **Docker:** `docker run -p 4000:4000 ghcr.io/berriai/litellm:main-latest`
- **Azure Container Apps:** Deploy เป็น container app ใน environment เดียวกับ Open WebUI
- **Kubernetes:** ใช้ Helm chart สำหรับ production

> 💡 **Recommendation:** ควรเพิ่ม LiteLLM เข้ามาในโปรเจคก่อนขึ้น production — เพื่อให้มี visibility ด้าน token usage/cost และสามารถควบคุม budget ได้

#### Local POC Setup (Docker)

**ไฟล์ที่เกี่ยวข้อง:**
| File | Purpose |
|------|---------|
| `config/litellm_config.yaml` | LiteLLM configuration — models, keys, settings |
| `config/docker-compose.litellm.yml` | Docker Compose — LiteLLM + PostgreSQL |
| `scripts/litellm-poc.sh` | Convenience script — start/stop/status/test |

**เริ่มใช้งาน:**

```bash
# 1. Set Azure Foundry API key
export AZURE_API_KEY="<your-azure-foundry-key>"

# 2. (Optional) Set LiteLLM master key — defaults to sk-litellm-poc-master-key
export LITELLM_MASTER_KEY="sk-your-master-key"

# 3. Start LiteLLM
./scripts/litellm-poc.sh start

# 4. Check status + available models
./scripts/litellm-poc.sh status

# 5. Test a chat completion
./scripts/litellm-poc.sh test
```

**ชี้ Open WebUI ไปที่ LiteLLM:**
1. Admin Panel → Settings → Connections → OpenAI API
2. ตั้งค่า:
   - **API Base:** `http://localhost:4000/v1`
   - **API Key:** `sk-litellm-poc-master-key` (หรือค่าที่ตั้งใน `LITELLM_MASTER_KEY`)

**ดู Token Usage:**
- **LiteLLM UI Dashboard:** http://localhost:4000/ui
- **Docker Logs:** `docker logs -f litellm-poc | grep -i token`
- **Available Models:** `curl -s http://localhost:4000/v1/models -H "Authorization: Bearer sk-litellm-poc-master-key"`

---

### Open WebUI Pipe Models

มี 2 Pipe models ใน Open WebUI (ทั้งคู่ใช้โค้ด v2.0 เดียวกัน):

| Model ID | Name | Type | Status |
|----------|------|------|--------|
| `haadthip-enterprise-assistant` | Haadthip Enterprise Assistant | Model record (`model` table) | ✅ Working |
| `pipe-haadthip-assistant` | Haadthip Enterprise Assistant (Pipe) | Function record (`function` table) | ✅ Working |

**Architecture:** ทั้งสองตัวใช้โค้ดเดียวกันจาก `config/pipe-haadthip-knowledge.py` (v2.0):
1. `pipe()` → สกัด query จาก messages
2. `_retrieve()` → เรียก KB retrieve API (Agentic Retrieval) ทั้ง 3 KS
3. `_generate()` → ส่งผลค้นหา + system prompt ให้ Azure OpenAI (`deploy-gpt-5.4`) สรุป

**Valves (configurable in Admin > Functions):**
| Valve | Default | Description |
|-------|---------|-------------|
| `search_endpoint` | `https://srch-entchat-poc-sand.search.windows.net` | AI Search endpoint |
| `search_api_key` | from `AZURE_SEARCH_ADMIN_KEY` env | Search admin key |
| `kb_name` | `haadthip-kb` | Knowledge Base name |
| `ks_names` | `haadthip-ks,sap-docs-ks,ir-docs-ks` | Knowledge Sources |
| `azure_endpoint` | `https://aif-entchat-poc-sand.cognitiveservices.azure.com` | Azure OpenAI endpoint |
| `azure_api_key` | from `OPENAI_API_KEY` env | OpenAI key |
| `deployment_name` | `deploy-gpt-5.4` | LLM for final answer (use gpt-5.4, not nano) |
| `api_version` | `2024-12-01-preview` | Azure OpenAI API version |

**Critical: Pipe Model Configuration Rules**
1. **`params` ต้องไม่มี `tools`** — tools array เก่า (จาก tool-based approach) ทำให้เกิด error `Missing required parameter: 'tools[0].type'`
2. **`meta.capabilities.builtin_tools` ต้องเป็น `false`** — Pipe จัดการ logic เอง ไม่ต้องให้ Open WebUI inject tools
3. **`base_model_id` ไม่ควรเป็น `deploy-gpt-5.4-nano`** — ใช้ `deploy-gpt-5.4-mini` หรือ `deploy-gpt-5.4` (แต่ Pipe ใช้ valve `deployment_name` ของตัวเองอยู่แล้ว)

**Correct model record format (`model` table):**
```json
{
  "id": "haadthip-enterprise-assistant",
  "base_model_id": "deploy-gpt-5.4-mini",
  "params": "{\"system\": \"...\", \"temperature\": 0.7}",
  "meta": "{\"capabilities\": {\"citations\": true, \"status_updates\": true}}"
}
```
- ❌ `params` ต้องไม่มี `"tools": [...]`
- ❌ `meta.capabilities` ต้องไม่มี `"builtin_tools": true`

### Floating Agent / Native Mode (Agentic Mode)

Open WebUI v0.10+ รองรับ **Native Mode** (Agentic Mode) — model จัดการ agentic loop เองผ่าน function calling:

```
User: "MFA บน Android ทำไง"

GPT คิด → เรียก tool: search_knowledge("MFA Android")
         → ได้ผลลัพธ์: 3 เอกสาร
GPT คิด → แค่นี้พอตอบ → ตอบกลับผู้ใช้
```

**ไม่ต้องเขียน loop เอง** — ระบบจัดการ ReAct loop (Reasoning + Acting) ให้อัตโนมัติ

#### Pipe vs Tool — เมื่อไหร่ใช้อะไร

| | Pipe (`class Pipe`) | Tool (`class Tools`) |
|---|---|---|
| **ใครคุม flow** | Dev กำหนด linear flow | Model ตัดสินใจเอง (agentic) |
| **Loop** | ต้องเขียนเอง (retrieve→generate→return) | ระบบจัดการให้ (think→act→observe→...) |
| **Multi-tool** | ต้อง implement เอง | เพิ่ม tool ทีละตัว, model เลือกใช้เอง |
| **ใช้พร้อม web search** | ไม่ได้ (pipe ควบคุมทั้งหมด) | ได้ — เปิด `search_web` tool พร้อม KB tool |
| **เปลี่ยน model** | ต้องแก้ valve ใน pipe | เปลี่ยนจาก UI ได้เลย |
| **โค้ดที่ต้องเขียน** | ~380 บรรทัด (full pipe) | ~40 บรรทัด (แค่ tool) |
| **ใช้เมื่อไหร่** | ต้องการควบคุมทุกขั้นตอนเป๊ะๆ, non-OpenAI model | ต้องการความยืดหยุ่น, multi-tool, ให้ model ตัดสินใจ |

#### วิธีเปลี่ยนจาก Pipe เป็น Tool

**ของเดิม**: `config/pipe-haadthip-knowledge.py` (380 บรรทัด) — search + generate รวมในไฟล์เดียว

**ของใหม่**: สร้าง Tool แยก (search อย่างเดียว) — model `deploy-gpt-5.4-mini` เป็นคน generate

```python
"""
title: Haadthip Knowledge Search (Tool)
"""
import json, os, httpx
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        search_endpoint: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net")
        search_api_key: str = Field(
            default=os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""))
        kb_name: str = Field(default="haadthip-kb")
        ks_names: str = Field(default="haadthip-ks,sap-docs-ks,ir-docs-ks")

    def __init__(self):
        self.valves = self.Valves()

    async def search_knowledge(self, query: str) -> str:
        """ค้นหาข้อมูลจากคลังความรู้ของหาดทิพย์ (HR, SAP, IR, IT Policy)"""
        ks_names = [s.strip() for s in self.valves.ks_names.split(",") if s.strip()]
        ks_params = [
            {"knowledgeSourceName": ks, "kind": "searchIndex"} for ks in ks_names
        ]

        url = (
            f"{self.valves.search_endpoint}"
            f"/knowledgebases('{self.valves.kb_name}')"
            f"/retrieve?api-version=2026-04-01"
        )

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(url, json={
                "intents": [{"search": query, "type": "semantic"}],
                "knowledgeSourceParams": ks_params,
                "maxOutputSizeInTokens": 8000,
            }, headers={
                "Content-Type": "application/json",
                "api-key": self.valves.search_api_key,
            })
            resp.raise_for_status()
            data = resp.json()

        # Extract text results
        docs = []
        for item in data.get("response", []):
            for c in item.get("content", []):
                if c.get("type") == "text":
                    try:
                        results = json.loads(c["text"])
                        for d in (results if isinstance(results, list) else []):
                            title = d.get("title", "?")
                            content = d.get("content", "")[:500]
                            docs.append(f"[{title}] {content}")
                    except (json.JSONDecodeError, TypeError):
                        pass

        return "\n\n".join(docs[:8]) if docs else "ไม่พบเอกสารในคลังความรู้"
```

**ขั้นตอน setup ใน Open WebUI:**

1. Admin → Functions → **Add** → วางโค้ดด้านบน → Save
2. ไปที่ Workspace → Models → เลือก `deploy-gpt-5.4-mini`
3. Advanced → Function Calling → **Native** (ค่า default)
4. กด 🔧 ในแชท → เปิด tool `search_knowledge` (เปิด `search_web` พร้อมกันได้)

#### Architecture หลังเปลี่ยนเป็น Tool-based

```
User ถามใน Open WebUI
       │
       ▼
  deploy-gpt-5.4-mini (Native Mode)
       │
       ├─── คิดว่าต้อง search KB ──→ Tool: search_knowledge() ──→ Azure AI Search KB
       │                                                              │
       │                              ◄─────── results ───────────────┘
       │
       ├─── คิดว่าต้อง search web ──→ Tool: search_web() (built-in)
       │
       ▼
  รวมผล + สรุป → ตอบผู้ใช้
```

> 💡 **ข้อดี**: model เลือก tool เอง, ใช้หลาย tool พร้อมกันได้, เปลี่ยน model จาก UI, ไม่ต้อง maintain loop logic
> 💡 **ข้อเสีย**: ควบคุม prompt/system message ได้น้อยกว่า Pipe (ใช้ default system prompt ของ Open WebUI), ถ้าต้องการ custom citation format ต้องใช้ Pipe

### Blob Containers (บน `staentchatdoc`)

| Container | Purpose |
|-----------|---------|
| `documents` | DocWise file storage (empty / not yet used) |
| `uploads` | Public blob access |
| `haadthip-ir` | ❌ ยังไม่ได้สร้าง — สำหรับ IR documents ingestion |
| `open-webui-files` | ❌ ยังไม่ได้สร้าง — ต้องสร้างก่อนใช้ MI |

> ⚠️ AI Search pipelines (index, datasource, skillset, indexer) และ Knowledge Bases ยังไม่ได้สร้างใน Sandbox นี้

### AI Search Pipeline

> ⚠️ **Pipelines ด้านล่างนี้เป็นของ old setup (`rg-entchat-poc-sea`) — ยังไม่ได้ re-create ใน Sandbox**
> ต้องตั้งค่าใหม่: AI Search datasource → index → skillset → indexer → knowledge source → knowledge base

| Component | Name | Description |
|-----------|------|-------------|
| Data Source | `haadthip-public-ds` | Points to `haadthip-public` blob container |
| Skillset | `haadthip-public-skillset` | Document Extraction (PDF text extraction) |
| Index (v2) | `haadthip-public-idx-v2` | `facetable: false` on content field — fixes term-too-large error |
| Indexer (v2) | `haadthip-public-idxr-v2` | Runs the pipeline — **18/18 docs indexed, 0 failures** ✅ |
| **SAP Data Source** | `sap-docs-ds` | Points to `sap-docs` blob container |
| **SAP Skillset** | `sap-docs-skillset` | Document Extraction (text + Tcode extraction) |
| **SAP Index** | `sap-docs-idx` | Same schema, semantic: `sap-docs-semantic` |
| **SAP Indexer** | `sap-docs-idxr` | **32/32 docs indexed** ✅ |
| Knowledge Source | `haadthip-ks` | `kind: searchIndex` → `haadthip-public-idx-v2` |
| **SAP Knowledge Source** | `sap-docs-ks` | `kind: searchIndex` → `sap-docs-idx` |
| **IR Knowledge Source** | `ir-docs-ks` | (planned) `kind: searchIndex` → `haadthip-ir-idx` |
| Knowledge Base | `haadthip-kb` | Multi-KS: `[haadthip-ks, sap-docs-ks, ir-docs-ks]` + LLM query planning |

> ⚠️ **Basic tier limits:** Content extracted max 524,288 chars per doc, file max 16 MB.  
> `htc-sustainability-report-2024-en.pdf` (25 MB) — indexed metadata only, not content.

### Azure AI Foundry — Hub/Project Architecture

```
┌──────────────────────────────────────────────────┐
│ Azure AI Foundry (Management & Governance)        │
│  Hub: aif-entchat-poc-sand                         │
│   ├── Connection: haadthip-ai-services (shared)   │
│   │    Type: azure_ai_services, auth: aad (MI)    │
│   └── Project: proj-entchat-poc-sand (associated)  │
└──────────────────────┬───────────────────────────┘
                       │ Hub connection
                       ▼
┌──────────────────────────────────────────────────┐
│ Azure AI Services (Model Inference)               │
│  aif-entchat-poc-sand (AIServices, S0)            │
│   ├── deploy-gpt-54-nano  (gpt-5.4-nano)          │
│   ├── deploy-gpt-54-mini  (gpt-5.4-mini) ◄── KB  │
│   └── deploy-gpt-54       (gpt-5.4)               │
│  Endpoint: aif-entchat-poc-sand.cognitiveservices.azure.com            │
└──────────────────────┬───────────────────────────┘
                       │ model inference
                       ▼
┌──────────────────────────────────────────────────┐
│ Azure AI Search — Agentic Retrieval               │
│  KB: haadthip-kb                                  │
│   ├── resourceUri: cognitiveservices.azure.com    │
│   ├── auth: SystemAssigned MI (apiKey: null)      │
│   └── knowledgeSources: [haadthip-ks]             │
└──────────────────────────────────────────────────┘
```

> 🔑 **Why `cognitiveservices.azure.com` not `services.ai.azure.com`?**  
> `services.ai.azure.com` เป็น Foundry **management API** (ใช้สำหรับ `/api/projects/...`)  
> ไม่รองรับ OpenAI inference path `/openai/deployments/.../chat/completions`  
> KB ต้องใช้ `cognitiveservices.azure.com` สำหรับ model inference จริง

### Agentic Retrieval — Knowledge Base

**URL Pattern (OData-style):**
```
PUT  {endpoint}/knowledgesources('{name}')?api-version=2026-04-01
PUT  {endpoint}/knowledgebases('{name}')?api-version=2026-04-01
POST {endpoint}/knowledgebases('{name}')/retrieve?api-version=2026-04-01
```

**Knowledge Source (`haadthip-ks`):**
```json
{
  "name": "haadthip-ks",
  "kind": "searchIndex",
  "searchIndexParameters": {
    "searchIndexName": "haadthip-public-idx-v2",
    "semanticConfigurationName": "haadthip-semantic",
    "sourceDataFields": [
      {"name": "metadata_storage_name"},
      {"name": "content"},
      {"name": "category"}
    ],
    "searchFields": [
      {"name": "metadata_storage_name"},
      {"name": "content"}
    ]
  }
}
```

**Knowledge Base (`haadthip-kb`):**
```json
{
  "name": "haadthip-kb",
  "knowledgeSources": [
    {"name": "haadthip-ks"},    // Haadthip public docs (18 docs)
    {"name": "sap-docs-ks"}     // SAP HIP manuals (32 docs)
  ],
  "models": [{
    "kind": "azureOpenAI",
    "azureOpenAIParameters": {
      "resourceUri": "https://aif-entchat-poc-sand.cognitiveservices.azure.com",
      "deploymentId": "deploy-gpt-54-nano",
      "modelName": "gpt-5.4-nano"
    }
  }]
}
```

> ⚠️ **API Version**: ใช้ `2026-04-01` **(GA stable)** — `2026-05-01-preview` มี bug "Could not reach model endpoint" เวลา model ถูกเรียกใช้งาน return results แล้ว (search ทำงานได้, แต่ model inference พัง) ไม่อยู่ใน Southeast Asia region

**Retrieve:**
```json
POST {endpoint}/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01
{
  "intents": [{"search": "What is Haadthip?", "type": "semantic"}],
  "knowledgeSourceParams": [
    {"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}
  ],
  "maxOutputSizeInTokens": 5000         // ≥ 5000 required (2026-04-01)
  // NOTE: 2026-05-01-preview ไม่มี maxOutputSizeInTokens
}
```

**Auth:** System Managed Identity — `apiKey: null, authIdentity: null` → auto-uses Search Service MI

### cURL Quick Reference

```bash
# 🔹 Retrieve (English)
curl -s -X POST "https://srch-entchat-poc-sand.search.windows.net/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01" \
  -H "Content-Type: application/json" \
  -H "api-key: YOUR_ADMIN_KEY" \
  -d '{
    "intents": [{"search": "What is Haadthip company?", "type": "semantic"}],
    "knowledgeSourceParams": [{"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}],
    "maxOutputSizeInTokens": 5000
  }'

# 🔹 Retrieve with inline az key
curl -s -X POST "https://srch-entchat-poc-sand.search.windows.net/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01" \
  -H "Content-Type: application/json" \
  -H "api-key: $(az search admin-key show --service-name srch-entchat-poc-sand --resource-group RG-ENTCHAT-POC-SAND-SEA --query primaryKey -o tsv)" \
  -d '{
    "intents": [{"search": "What is Haadthip company?", "type": "semantic"}],
    "knowledgeSourceParams": [{"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"}],
    "maxOutputSizeInTokens": 5000
  }'

# 🔹 Retrieve with SAP focus (multi-KS explicit)
curl -s -X POST "https://srch-entchat-poc-sand.search.windows.net/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01" \
  -H "Content-Type: application/json" \
  -H "api-key: YOUR_ADMIN_KEY" \
  -d '{
    "intents": [{"search": "\u0e27\u0e34\u0e18\u0e35\u0e14\u0e36\u0e07\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e25\u0e39\u0e01\u0e2b\u0e19\u0e35\u0e49\u0e08\u0e32\u0e01 SAP", "type": "semantic"}],
    "knowledgeSourceParams": [
      {"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"},
      {"knowledgeSourceName": "sap-docs-ks", "kind": "searchIndex"}
    ],
    "maxOutputSizeInTokens": 5000
  }'

# 🔹 SAP Tcode query
curl -s -X POST "https://srch-entchat-poc-sand.search.windows.net/knowledgebases('haadthip-kb')/retrieve?api-version=2026-04-01" \
  -H "Content-Type: application/json" \
  -H "api-key: YOUR_ADMIN_KEY" \
  -d '{
    "intents": [{"search": "SAP Tcode mb52 stock report", "type": "semantic"}],
    "knowledgeSourceParams": [
      {"knowledgeSourceName": "haadthip-ks", "kind": "searchIndex"},
      {"knowledgeSourceName": "sap-docs-ks", "kind": "searchIndex"}
    ],
    "maxOutputSizeInTokens": 5000
  }'

# 🔹 Direct search in SAP index
curl -s "https://srch-entchat-poc-sand.search.windows.net/indexes/haadthip-public-idx-v2/docs?api-version=2024-07-01&search=*&\$top=20&\$select=metadata_storage_name" \
  -H "api-key: $(az search admin-key show --service-name srch-entchat-poc-sand --resource-group RG-ENTCHAT-POC-SAND-SEA --query primaryKey -o tsv)"

# 🔹 Check KB config
curl -s "https://srch-entchat-poc-sand.search.windows.net/knowledgebases('haadthip-kb')?api-version=2026-04-01" \
  -H "api-key: YOUR_ADMIN_KEY" | python3 -m json.tool

# 🔹 Check Knowledge Source config
curl -s "https://srch-entchat-poc-sand.search.windows.net/knowledgesources('haadthip-ks')?api-version=2026-04-01" \
  -H "api-key: YOUR_ADMIN_KEY" | python3 -m json.tool

# 🔹 List all Knowledge Sources
curl -s "https://srch-entchat-poc-sand.search.windows.net/knowledgesources?\$top=1000&\$count=true&api-version=2026-04-01" \
  -H "api-key: YOUR_ADMIN_KEY" | python3 -m json.tool
```

### Managed Identity — Search Service → AI Services

| Item | Value |
|------|-------|
| Search Service MI | ❌ **Not configured** — needs SystemAssigned |
| RBAC Role | `Cognitive Services OpenAI User` (to assign) |
| Scope | `aif-entchat-poc-sand` |
| KB auth | Currently uses API key (no MI yet) |

### Managed Identity — Open WebUI → Storage Account

| Item | Value |
|------|-------|
| Web App MI | ❌ **Not configured** — needs SystemAssigned |
| RBAC Role | `Storage Blob Data Contributor` (to assign) |
| Scope | `staentchatdoc` (to configure) |

Chain: `Search Service (MI)` → `Cognitive Services OpenAI User` → `AIServices (aif-entchat-poc-sand)`

### AI Services — Endpoint Format Note

AIServices resource มี 2 endpoint formats:
- `https://{region}.api.cognitive.microsoft.com/` (legacy — API key only)
- `https://{name}.cognitiveservices.azure.com/` (สำหรับ Managed Identity auth)

Agentic retrieval Knowledge Base ต้องใช้ `cognitiveservices.azure.com` suffix เท่านั้น:
```
✅ https://aif-entchat-poc-sand.cognitiveservices.azure.com/
❌ https://southeastasia.api.cognitive.microsoft.com/
```
Allowed suffixes: `openai.azure.com`, `cognitiveservices.azure.com`, `services.ai.azure.com`, `models.ai.azure.com`

### Entra ID — App Registration

| Item | Value |
|------|-------|
| Display Name | `Open WebUI — Sandbox PoC` |
| Client ID | `4881351e-d1a0-4228-a084-a0d6ef717740` |
| Client Secret | `u498Q~ve1ae4W0ERSwoeD5LIWywq6kD2GRPqVase` (expires 2027-01-01) |
| Tenant ID | `5045d9c3-3b0b-4315-8594-64118bbd7495` |
| SP Object ID | `<REPLACE>` |
| Redirect URI | `https://app-entchat-owui-poc-sand.azurewebsites.net/oauth/callback` |

---

## Recurring Issues (from provisioning sessions)

### 1. Password URL encoding in connection strings
`@` → `%40`, `!` → `%21` ใน PostgreSQL DATABASE_URL

### 2. Container startup timeout
Default 230s ไม่พอสำหรับ Open WebUI (downloads embedding models) → ตั้ง `WEBSITES_CONTAINER_START_TIME_LIMIT=1800`

### 3. PostgreSQL database ไม่ auto-create
Alembic migrations **ไม่สร้าง database** ต้อง `CREATE DATABASE open_webui` และ `CREATE DATABASE docwise` ก่อน deploy

### 4. Entra ID: SP ไม่ auto-create
App Registration ใหม่ → ต้อง `az ad sp create --id <client-id>` ไม่งั้น OIDC login จะ 401 loop

### 5. Entra ID: Email claim จำเป็น
ต้องเพิ่ม `email` optional claim ใน ID token — ไม่เช่นนั้น Open WebUI reject login

### 6. AI Search: Free → Basic upgrade ไม่ได้โดยตรง
ต้องลบแล้วสร้างใหม่ — delete ใช้เวลา 5-15 นาที background operation
Workaround: สร้างชื่อใหม่ เช่น `srch-*-poc-sea-01` ถ้ารอไม่ได้

### 7. Agentic Retrieval REST API — OData-style URL
Endpoint ใช้ **OData-style** path ไม่ใช่ RESTful:
```
✅ {endpoint}/knowledgesources('{name}')?api-version=2026-04-01
❌ {endpoint}/knowledge-sources/{name}?api-version=2026-04-01
```
เช่นเดียวกันสำหรับ `knowledgebases('{name}')` และ `knowledgebases('{name}')/retrieve`

### 7b. API Version — ใช้ GA (2026-04-01) ไม่ใช่ Preview
**Problem:** `2026-05-01-preview` → error "Could not reach the model endpoint" เมื่อ model ถูกเรียก (search ทำงานได้ แต่ model inference พัง)
**Symptom:** query ที่มี search result → model call fail; query ที่ไม่มี search result (0 hits) → ไม่ error เพราะไม่ต้องเรียก model
**Fix:** ใช้ `api-version=2026-04-01` (GA, stable)
**Note:** `2026-05-01-preview` เปลี่ยน parameter name — ไม่มี `maxOutputSizeInTokens`, ใช้ `retrievalReasoningEffort` (object format `{"kind": "medium"}`) แต่ model endpoint เชื่อมต่อไม่ได้ใน SEA region

### 8. AI Services soft-delete
ลบแล้วสร้างชื่อเดิม → error `FlagMustBeSetForRestore` → ต้อง purge ก่อน:
```bash
az cognitiveservices account purge --name <name> --location southeastasia --resource-group <rg>
```

### 9. AI Services endpoint suffix
Knowledge Base ต้องใช้ `cognitiveservices.azure.com` suffix (ไม่ใช่ `api.cognitive.microsoft.com`):
```
✅ https://{name}.cognitiveservices.azure.com/
❌ https://{region}.api.cognitive.microsoft.com/
```
Allowed suffixes: `openai.azure.com`, `cognitiveservices.azure.com`, `services.ai.azure.com`, `models.ai.azure.com`

### 10. Managed Identity — SP ต้องสร้างก่อน assign role
Enable MI บน Search Service แล้ว → ต้องรอสักครู่ หรือสร้าง SP ก่อน:
```bash
az ad sp create --id <principal-id>  # ถ้า role assignment error "Cannot find user"
```
แล้วค่อย `az role assignment create --assignee <principal-id> --role "Cognitive Services OpenAI User" --scope <ai-resource-id>`

### 11. Index: `content` field ห้ามมี facetable/sortable/filterable
**Problem:** ไฟล์ใหญ่ (AGM minutes, One Report) index ไม่สำเร็จ — error "Field 'content' contains a term that is too large to process. The max length for UTF-8 encoded terms is 32766 bytes."
**Root cause:** `facetable: true` บน `content` field → entire field ถูก index เป็น single term
**Fix:** สร้าง index ใหม่ — ตั้ง `facetable: false` บน `content` field
```json
{"name": "content", "type": "Edm.String", "searchable": true, "facetable": false, ...}
```
**Note:** Azure AI Search **ไม่อนุญาตให้แก้ไข field definition** ของ index ที่มีอยู่ — ต้องลบหรือสร้าง index ใหม่
**Discovered:** 2026-07-03 (Session 6)

### 12. services.ai.azure.com ≠ model inference endpoint
**Problem:** KB ใช้ `https://aif-entchat-poc-sand.services.ai.azure.com` → error "Could not reach the model endpoint"
**Root cause:** `services.ai.azure.com` เป็น **Foundry management API** (ใช้ path `/api/projects/{project}`) ไม่รองรับ OpenAI inference path `/openai/deployments/.../chat/completions`
**Fix:** ใช้ `cognitiveservices.azure.com` สำหรับ KB model inference:
```
✅ https://aif-entchat-poc-sand.cognitiveservices.azure.com  (inference — ใช้งานได้)
❌ https://aif-entchat-poc-sand.services.ai.azure.com        (management API — KB ใช้ไม่ได้)
```
**Note:** Foundry Hub connection (`azure_ai_services` type) → AI Services ก็เพียงพอสำหรับ governance — KB inference ต้องวิ่งผ่าน `cognitiveservices.azure.com` อยู่ดี
**Discovered:** 2026-07-03 (Session 6)

### 13. maxOutputSizeInTokens ต้อง ≥ 5000
**Problem:** retrieve request error "Configuration max output size must be greater than 5000"
**Fix:** ตั้ง `maxOutputSizeInTokens` อย่างน้อย 5000

### 14. Knowledge Base Managed Identity: ละ apiKey + authIdentity
**Problem:** API error "Cannot create an abstract class" เมื่อใส่ `authIdentity: { identityType: "SystemAssigned" }`
**Correct pattern:** ละทั้ง `apiKey` และ `authIdentity` — ระบบใช้ SystemAssigned MI อัตโนมัติ:
```json
{
  "azureOpenAIParameters": {
    "resourceUri": "https://{name}.cognitiveservices.azure.com",
    "deploymentId": "deploy-gpt-54-mini",
    "modelName": "gpt-5.4-mini"
    // no apiKey, no authIdentity → auto SystemAssigned MI
  }
}
```

### 15. Open WebUI: DATABASE_URL password mismatch → infinite pagination loop
**Problem:** `+layout.svelte` fetch `chats/?page=84 → 85 → 86 → ...` ไม่หยุด
**Root cause:** App Service `DATABASE_URL` มี password ผิด (`EntChatP0c05ef252e` แทนที่จะเป็น `DocWiseP@ssw0rd2026!`) → chat messages เขียน DB ไม่ได้ → `psycopg.OperationalError: password authentication failed` → frontend retry วน infinite loop
**Fix:** แก้ DATABASE_URL ใน App Service app settings:
```bash
az webapp config appsettings set \
  --name app-entchat-owui-poc-sand \
  --resource-group RG-ENTCHAT-POC-SAND-SEA \
  --settings "DATABASE_URL=postgresql://entchatadm:DocWiseP%40ssw0rd2026%21@psql-entchat-poc-sand.postgres.database.azure.com:5432/open_webui?sslmode=require"
```
**Note:** DNS resolve `psql-entchat-poc-sand.postgres.database.azure.com` → private endpoint IP `172.28.69.4` ภายใน VNet — ต้องใช้ password ที่ตรงกับ PostgreSQL server จริง
**Verified:** 2026-07-07

### 16. Open WebUI: Model params tools[0].type error
**Problem:** Chat API return `{"detail": "Missing required parameter: 'tools[0].type'."}`
**Root cause:** Model record (`model` table) มี `params.tools` array เก่าที่ไม่มี `type` field — Open WebUI validation เจอ tools array ที่มีแค่ `id` + `name` แต่ขาด `type` (เช่น `"type": "function"`)
```json
// ❌ Broken (old tool-based config)
"params": {"tools": [{"id": "b62851a8-...", "name": "Haadthip Docs"}]}

// ✅ Fixed — remove tools entirely for Pipe models
"params": {"system": "...", "temperature": 0.7}
```
**Fix:** ลบ `tools` ออกจาก `params` column ใน `model` table:
```sql
UPDATE model SET params = (params::jsonb - 'tools')::text WHERE id = 'haadthip-enterprise-assistant';
```
**Note:** Pipe models handle knowledge retrieval internally — ไม่ต้องพึ่ง Open WebUI function calling tools
**Discovered:** 2026-07-07

### 17. Open WebUI: Pipe model capabilities ต้องไม่เปิด builtin_tools
**Problem:** Pipe model ทำงานไม่ถูกต้องเพราะ Open WebUI พยายาม inject tools
**Root cause:** `meta.capabilities.builtin_tools: true` ทำให้ Open WebUI validation layer คาดหวัง tools parameter
**Fix:**
```sql
UPDATE model SET meta = jsonb_set(meta::jsonb, '{capabilities,builtin_tools}', 'false')::text WHERE id = 'haadthip-enterprise-assistant';
```
**Correct capabilities for Pipe models:**
```json
{"citations": true, "status_updates": true}
```
- ❌ `builtin_tools: true` — Pipe handles tools internally
- ❌ `code_interpreter: true` — not needed
- ❌ `image_generation: true` — not needed
- ✅ `citations: true` — for showing source documents
- ✅ `status_updates: true` — for showing "กำลังค้นหา..." progress
**Discovered:** 2026-07-07

### 18. Open WebUI: Analytics token usage เป็น 0 สำหรับ API clients (Azure Foundry)
**Problem:** Analytics Dashboard แสดง token usage = 0 สำหรับโมเดลที่ใช้ผ่าน API (Azure Foundry) — ขึ้นเฉพาะ chats ที่ใช้ผ่าน Web UI
**Root cause:** Analytics pipeline ต้องใช้ `chat_id`, `session_id`, `message_id` — API clients ไม่ส่ง → `event_emitter` เป็น None → ไม่ track usage, ไม่เขียน DB
**Status:** Issue [#21675](https://github.com/open-webui/open-webui/issues/21675) ยัง OPEN — PR [#25650](https://github.com/open-webui/open-webui/pull/25650) merge เข้า `dev` branch (29 มิ.ย. 2569) แต่ยังไม่ released และแก้แค่ outlet filters ไม่ใช่ analytics โดยตรง
**Recommendation:** ใช้ **LiteLLM** เป็น proxy คั่นระหว่าง Open WebUI และ Azure Foundry — LiteLLM มี token tracking, cost monitoring, budget limits ในตัว (ดูรายละเอียดที่หัวข้อ [Open WebUI — Token Tracking Limitation](#open-webui--token-tracking-limitation-️))
**Discovered:** 2026-07-08

---

## Directory Structure

```
EnterpriseChat/
├── CONTEXT.md                         ← This file (domain glossary + infra + architecture)
├── architecture-view.html             ← Visual architecture diagram (open in browser)
├── EnterpriseChat-Walkthrough-*.pptx  ← User walkthrough presentation
│
├── config/
│   ├── hub-ai-services-connection.yaml  ← Foundry Hub → AI Services connection
│   ├── pipe-haadthip-knowledge.py       ← Open WebUI Pipe v2.0 (Agentic Retrieval + LLM)
│   ├── pipe-corporate-knowledge.py      ← Corporate IT/Policy KB pipe
│   ├── pipe-sap-knowledge.py            ← SAP HIP manuals KB pipe
│   ├── pipe-ir-knowledge.py             ← Investor Relations KB pipe
│   ├── pipe-hr-knowledge.py             ← HR knowledge KB pipe
│   ├── pipe-eexpense-knowledge.py       ← E-Expense FAQ KB pipe
│   ├── tool-haadthip-knowledge-search.py← Open WebUI KB search tool (Native Mode)
│   ├── eexpense-faq-tool.py             ← E-Expense hybrid search tool
│   ├── filter-token-tracker.py          ← Open WebUI Filter: token usage tracker
│   ├── litellm_config.yaml              ← LiteLLM proxy config (5 Azure Foundry models)
│   ├── Dockerfile.litellm               ← LiteLLM custom image (embeds config.yaml)
│   ├── docker-compose.litellm.yml       ← LiteLLM + PostgreSQL (local POC)
│   ├── docker-compose.openwebui.yml     ← Open WebUI standalone (local)
│   └── docker-compose.full.yml          ← Full stack: Open WebUI + LiteLLM
│
├── scripts/
│   ├── deploy-litellm-azure.sh          ← Deploy LiteLLM to Azure Web App
│   ├── litellm-poc.sh                   ← LiteLLM local POC: start/stop/status/test
│   ├── create-walkthrough-pptx.js       ← Generate walkthrough presentation
│   ├── provision-poc-resources.sh       ← Full provisioning script
│   ├── setup-auto-ingest.sh             ← Auto-ingest pipeline (general docs)
│   ├── setup-haadthip-ir-pipeline.sh    ← IR docs: data source + index + skillset + indexer + KS
│   ├── ingest-blob-to-search-v2.py      ← Blob → AI Search ingestion (general)
│   ├── ingest-haadthip-ir-v2.py         ← IR docs: chunk + classify subject + embed + index
│   ├── unified-ingestion.py             ← Unified ingestion: all corpuses + all file types
│   ├── download-ir-docs.sh              ← Download IR PDFs from Haadthip website
│   ├── flatten-eexpense-qa.py           ← E-Expense: Excel Decision Tree → FAQ JSONL
│   ├── create-eexpense-index.py         ← E-Expense: Create AI Search index
│   ├── ingest-eexpense-faq.py           ← E-Expense: Embed + upload documents
│   ├── eexpense-chatbot.py              ← E-Expense: Chatbot engine (search + state machine)
│   └── setup-eexpense-search.sh         ← E-Expense: All-in-one pipeline
│
├── docs/
│   ├── walkthrough-agenda-2026-07-09.md ← User walkthrough agenda
│   ├── aca-deployment-spec.md           ← ACA deployment architecture
│   ├── aks-deployment-spec.md           ← AKS deployment architecture
│   ├── ai-search-context.md             ← AI Search setup notes
│   ├── ai-search-ingestion-guide.md
│   ├── eexpense-search-architecture.md  ← E-Expense FAQ Search architecture
│   ├── librechat-vs-openwebui-note.md
│   ├── neuronhub-page-by-page-review.md
│   ├── neuronhub-vendor-review.md
│   ├── หาดทิพย์ NeuronHub_Presentation.pdf
│   ├── artifacts/                       ← Design artifacts (philosophy, renders)
│   ├── adr/                             ← Architecture Decision Records
│   └── azure/                           ← Provisioning session notes
│       ├── 2026-07-01-azure-resource-request.md
│       ├── 2026-07-02-azure-resource-plan-final.md
│       ├── 2026-07-02-provisioning-session.md
│       ├── 2026-07-03-session4-provision.md
│       └── 2026-07-03-session5-agentic-retrieval.md
│
├── documents/                           ← Source documents (4 subdirectories)
│   ├── haadthip-public/                 ← Corporate IT docs (23 files)
│   ├── sap-hip/                         ← SAP HIP manuals (32 files)
│   ├── haadthip-ir/                     ← Investor Relations (31 files)
│   └── mihcm-hr/                        ← HR documents
│
├── data/                                ← Data files (dumps, JSONL, Postman)
│   ├── open_webui_poc.dump / .sql       ← PostgreSQL backups
│   ├── eexpense-faq.jsonl               ← E-Expense: 42 FAQ documents
│   └── postman-*                        ← API testing collections
│
├── screenshots/                         ← Screenshots (organized)
│   ├── architecture.png                 ← Architecture diagram capture
│   ├── openwebui.png                    ← Open WebUI interface
│   ├── litellm-dashboard.png            ← LiteLLM dashboard (logged in)
│   ├── litellm-ui.png                   ← LiteLLM login page
│   ├── sessions/                        ← Session screenshots (25 files)
│   └── mihcm/                           ← MiHCM screen captures
│
└── icons/                               ← Azure architecture SVG icons (11 files)
```

│       └── 03-company-disclosures/← MD&A, F45, AGM Minutes, Press Releases
├── arch-diagram.html
├── n8n-openwebui-architecture.docx
└── ...
```

---

## Estimated Cost

| Service | Est. Monthly |
|---------|-------------|
| App Service Plan B2 | ~$25-33 |
| PostgreSQL B1ms | ~$12 |
| Storage (shared) | <$1 |
| AI Search (Standard) | ~$245 |
| AI Services (pay-per-use) | tokens only |
| Private Endpoints + DNS | minimal |
| **Total (fixed)** | **~$290-310/mo** |
