# EnterpriseChat — Domain Context

> ## 📝 Recent Changes (2026-07-14)
>
> ### Cleanup — Pipeline & Blob Containers
> ได้ cleanup Azure resources ที่ไม่ใช้แล้ว:
> - **Blob containers**: `haadthip-investor-relations`, `haadthip-corporate`, `haadthip-hr-policies` — ลบไฟล์ทั้งหมด
> - **Indexes**: `haadthip-ir-idx`, `mihcm-hr-idx`, `haadthip-public-idx-v2` ❌
> - **Indexers**: `haadthip-ir-idxr`, `mihcm-hr-indexer` ❌ (ลบไปก่อนหน้านี้แล้ว)
> - **Skillsets**: `haadthip-ir-skillset`, `mihcm-hr-skillset`, `haadthip-public-skillset` ❌
> - **Data sources**: `haadthip-ir-ds`, `mihcm-hr-ds`, `haadthip-public-ds` ❌
> - **Knowledge sources**: `ir-docs-ks`, `mihcm-hr-ks`, `haadthip-ks` ❌
> - **Knowledge base**: `haadthip-kb` ❌
>
> **เหลือเฉพาะ indexes ที่ใช้งานอยู่:** `documents-index`, `docwise-docs-v2`, `eexpense-faq-idx`, `sap-docs-idx`
>
> > 🔜 **Next:** Custom Python ingestion (แทน index projection / skillset approach)
>
> ### Repository Structure
> - ย้าย PNGs ทั้งหมด → `screenshots/`
> - ย้าย PPTXs → `docs/presentations/`
> - ย้าย HTML → `docs/`
> - เพิ่ม `.gitignore` + `git init` (351 files, commit `3202ff4`)

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

| Corpus | Path | Files | Detail |
|--------|------|:----:|--------|
| Public Docs | `documents/haadthip-corporate/` | 19 | Security, Email, Meeting Room, IT Policy, Public Disclosure. 5 subdirs. |
| IR Docs | `documents/haadthip-investor-relations/` | 31 | Annual Reports, Financial Data, Company Disclosures. 3 subdirs. |
| HR Docs | `documents/haadthip-hr-policies/` | 125+ | HR policies, forms, manuals, regulations (.pdf/.doc/.xlsx/.jpg) |
| SAP HIP | `documents/sap-hip-manuals/` | 32 | SAP Hana Implementation Project manuals |

> 📖 ดูรายละเอียดไฟล์ได้ที่ `documents/*/README.md`
>
> **Note:** Pipelines สำหรับ haadthip-ir, haadthip-public, mihcm-hr ถูกลบจาก Azure Search แล้ว — จะใช้ custom Python ingestion แทน
>
> SAP index (`sap-docs-idx`) ยังอยู่ ✅ — index ไว้ด้วย old pipeline (DocumentExtractionSkill) ได้เฉพาะ text + Tcode, screenshots ไม่ได้ OCR

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

### Naming Convention

> ไว้ reference สำหรับสร้าง resource ใหม่ — ชื่อต้อง consistent

| หมวด | Pattern | ตัวอย่าง |
|------|---------|---------|
| **Resource Group** | `{RG}-{PROJECT}-{ENV}-{REGION}` | `RG-ENTCHAT-POC-SAND-SEA` |
| **Azure Resource** | `{prefix}-{project}-{purpose}-{env}` | `srch-entchat-poc-sand`, `app-entchat-owui-poc-sand`, `psql-entchat-poc-sand`, `aif-entchat-poc-sand` |
| **Storage Account** | `sta{project}{purpose}` (max 24 chars, flat) | `staentchatdoc` |
| **Container Registry** | `acr{project}{env}{region}` | `acrentchatpocsand` |
| **Private Endpoint** | `PVE-{RESOURCE}-{PROJECT}-{ENV}` | `PVE-AIF-ENTCHAT-SAND`, `PVE-SRCH-ENTCHAT-SAND` |
| **VNet / Subnet** | `{type}-{PROJECT}-{ENV}-{REGION}` | `VNET-HTC-SANBOX-SEA`, `SNET-HTC-SANDBOX-WEB-SEA` |
| | | |
| **Docker Image** | `{registry}/{name}:{tag}` | `acrentchatpocsand.azurecr.io/litellm-entchat:latest` |
| **Docker Image name** | `{purpose}-entchat` | `litellm-entchat`, `owui-entchat` (unused) |
| | | |
| **PostgreSQL DB** | lowercase snake_case | `open_webui`, `docwise`, `litellm` |
| **Blob Container** | lowercase kebab-case | `haadthip-investor-relations`, `open-webui-files`, `documents` |
| **Search Index** | `{purpose}-idx` | `haadthip-investor-relations-idx`, `eexpense-faq-idx`, `sap-docs-idx` |
| **Data Source** | `{purpose}-ds` | `haadthip-investor-relations-ds`, `sap-docs-ds` |
| **Skillset** | `{purpose}-skillset` | `haadthip-investor-relations-skillset`, `haadthip-public-skillset` |
| **Indexer** | `{purpose}-idxr` | `haadthip-investor-relations-idxr`, `mihcm-hr-indexer` |
| **Knowledge Source** | `{purpose}-ks` | `sap-docs-ks`, `ir-docs-ks` |
| **Knowledge Base** | `{purpose}-kb` | `haadthip-kb` |
| | | |
| **Open WebUI Pipe** | `pipe-{corpus}-knowledge` | `pipe-haadthip-knowledge`, `pipe-sap-knowledge`, `pipe-hr-knowledge`, `pipe-eexpense-knowledge` |
| **Open WebUI Tool** | `tool-{project}-knowledge-search` | `tool-haadthip-knowledge-search` |

> 💡 `purpose` = ย่อ Corpus/Function เช่น `owui`=Open WebUI, `ir`=Investor Relations  
> 💡 `env` = `poc` (PoC), `sand` (Sandbox), `dev`, `prod`  
> 💡 `region` = `-sea` (Southeast Asia) ต่อท้าย resource group / resource name  
> 💡 Storage account \& ACR ชื่อสั้นกว่าเพราะ global uniqueness constraint

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

### LiteLLM Models (mapped via LiteLLM config)

| Model Name | Azure Deployment | Use |
|-----------|-----------------|-----|
| `gpt-5.4-nano` | `deploy-gpt-5.4-nano` | KB query planning (cheapest) |
| `gpt-5.4-mini` | `deploy-gpt-5.4-mini` | General chat |
| `gpt-5.4` | `deploy-gpt-5.4` | Pipe final answer (best quality) |
| `gpt-5.2` | `deploy-gpt-5.2` | Fallback |
| `text-embedding-3-large` | `deploy-embedding-3-large` | Vector embeddings 3072d |

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
| `kb_name` | `haadthip-kb` (ถูกลบแล้ว) | Knowledge Base name |
| `ks_names` | `sap-docs-ks` | Knowledge Sources |
| `azure_endpoint` | `https://aif-entchat-poc-sand.cognitiveservices.azure.com` | Azure OpenAI endpoint |
| `azure_api_key` | from `OPENAI_API_KEY` env | OpenAI key |
| `deployment_name` | `deploy-gpt-5.4` | LLM for final answer |

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
	        ks_names: str = Field(default="sap-docs-ks")

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
| `haadthip-investor-relations` | ✅ **Cleaned up** (ไฟล์ถูกลบ 2026-07-14) — เคยมี 31 IR PDFs |
| `haadthip-corporate` | ✅ **Cleaned up** (ไฟล์ถูกลบ 2026-07-14) — เคยมี 19 docs |
| `haadthip-hr-policies` | ✅ **Cleaned up** (ไฟล์ถูกลบ 2026-07-14) — เคยมี 125 files |
| `open-webui-files` | ❌ ยังไม่ได้สร้าง — ต้องสร้างก่อนใช้ MI |

> ⚠️ Pipelines ที่เกี่ยวข้อง (haadthip-ir, haadthip-public, mihcm-hr) ถูกลบออกจาก Search service แล้ว — Custom Python ingestion แทน

### Agentic Retrieval Knowledge Base (format reference)

> KB `haadthip-kb` + KS `haadthip-ks`, `ir-docs-ks`, `mihcm-hr-ks` ถูกลบแล้ว  
> `sap-docs-ks` ยังอยู่ ✅  
> ข้อมูลด้านล่างเป็น format reference สำหรับ custom ingestion ต่อไป

**URL Pattern (OData-style):**
```
PUT  {endpoint}/knowledgesources('{name}')?api-version=2026-04-01
PUT  {endpoint}/knowledgebases('{name}')?api-version=2026-04-01
POST {endpoint}/knowledgebases('{name}')/retrieve?api-version=2026-04-01
```

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `knowledgesources` | PUT/POST | Create knowledge source wrapper around a search index |
| `knowledgebases` | PUT/POST | Create KB with multiple KS + model config |
| `knowledgebases/{name}/retrieve` | POST | Agentic retrieval query |

> ⚠️ `api-version=2026-04-01` (GA, stable) — `2026-05-01-preview` มี bug "Could not reach model endpoint" ใน SEA region

### Managed Identity & Endpoint

| Resource MI | Role to Assign | Target |
|-------------|---------------|--------|
| Search Service (`0080ceef`) | `Cognitive Services OpenAI User` | `aif-entchat-poc-sand` (AI Services) |
| Open WebUI Web App (pending) | `Storage Blob Data Contributor` | `staentchatdoc` (Storage) |

> **Endpoint format:** KB/Pipeline ต้องใช้ `cognitiveservices.azure.com` (ไม่ใช่ `api.cognitive.microsoft.com`)  
> Allowed suffixes: `openai.azure.com`, `cognitiveservices.azure.com`, `services.ai.azure.com`, `models.ai.azure.com`

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

## Architecture Decisions (ADR)

| # | Decision | Context |
|---|----------|---------|
| 1 | **Ingress** — Application Routing Gateway API (Istio) | Azure-managed ingress with TLS termination |
| 2 | **Database** — Shared Azure PostgreSQL Flexible Server | Single PG for all services (open_webui, docwise, litellm) |
| 3 | **Object Storage** — Azure Blob Storage | Open WebUI files, document uploads |
| 4 | **Node Pool** — System + Workload + GPU (on-demand) | AKS node pool strategy (reference for future) |
| 5 | **LLM Backend** — Hybrid (Azure OpenAI + Ollama) | Cloud models for production, Ollama for local dev |
| 6 | **Platform** — Container Apps over AKS | Managed K8s less overhead for small team $100/mo budget |

> 📖 Full context: `docs/adr/0001`–`0006`

## Provisioning Sessions

| Session | Date | Scope |
|---------|------|-------|
| Resource Request | 2026-07-01 | Initial Azure resource request for 2-week demo |
| Resource Plan Final | 2026-07-02 | Verified PoC plan with cost breakdown |
| Provisioning — Session 2 | 2026-07-02 | First round of resource provisioning |
| Session 4 — Clean Provision | 2026-07-03 | Re-provision EnterpriseChat + DocWise |
| Session 5 — Agentic Retrieval + MI | 2026-07-03 | KB setup, Managed Identity configuration |
| Session 6 — Index Fix | 2026-07-03 | `content` field facetable fix, endpoint debugging |

> 📖 Full notes: `docs/azure/2026-07-01`–`2026-07-03`

## Deployment Specs

| Doc | Scope | Status |
|-----|-------|--------|
| `docs/aca-deployment-spec.md` | Azure Container Apps architecture + provisioning steps | Reference (actual infra used App Service) |
| `docs/aks-deployment-spec.md` | AKS architecture (future migration path) | Reference |

## E-Expense FAQ Search

E-Expense FAQ ใช้ hybrid search (BM25 + vector 3072d + semantic ranker) บน index `eexpense-faq-idx`  
42 documents จาก 27 root questions, 11 หมวดหมู่  
Pipeline: flatten → embed → upload → chatbot engine (state machine)

> 📖 Architecture detail: `docs/eexpense-search-architecture.md`  
> 🔗 Scripts: `scripts/flatten-eexpense-qa.py`, `scripts/ingest-eexpense-faq.py`, `scripts/eexpense-chatbot.py`

## Walkthrough Presentation

| File | Description |
|------|-------------|
| `docs/walkthrough-presentation.html` | HTML walkthrough deck (used in 2026-07-09 session) |
| `docs/walkthrough-agenda-2026-07-09.md` | User walkthrough agenda — agenda for the live session |
| `docs/architecture-view.html` | Visual architecture diagram (open in browser) |
| `docs/presentations/EnterpriseChat-Chatbot-UseCases.pptx` | Chatbot use cases slide deck |
| `docs/presentations/EnterpriseChat-Walkthrough-2026-07-09.pptx` | Walkthrough presentation |

---

## Recurring Issues (quick reference)

| # | Problem | Fix |
|---|---------|-----|
| 1 | `@` `!` in DATABASE_URL breaks connection | URL-encode: `@`→`%40`, `!`→`%21` |
| 2 | Container startup timeout (230s) | Set `WEBSITES_CONTAINER_START_TIME_LIMIT=1800` |
| 3 | PostgreSQL DB not auto-created | `CREATE DATABASE open_webui / docwise / litellm` before deploy |
| 4 | Entra ID SP not auto-created | `az ad sp create --id <client-id>` |
| 5 | Entra ID email claim missing | Add `email` optional claim in ID token |
| 6 | Search Free→Basic upgrade | Delete & recreate (5-15 min), or create with new name |
| 7 | KB REST uses OData-style path | `knowledgesources('{name}')` not `/knowledge-sources/{name}` |
| 8 | `2026-05-01-preview` KB bug in SEA | Use `api-version=2026-04-01` (GA) |
| 9 | AI Services soft-delete block | `az cognitiveservices account purge` before re-create |
| 10 | Endpoint suffix matters | KB/Pipe ใช้ `cognitiveservices.azure.com` ไม่ใช่ `api.cognitive.microsoft.com` |
| 11 | MI role assignment fails | `az ad sp create --id <principal-id>` first, then assign role |
| 12 | Index `content` field too large | Set `facetable: false, sortable: false, filterable: false` on content field |
| 13 | KB retrieve `maxOutputSizeInTokens` | Must be ≥ 5000 |
| 14 | KB MI auth error | Omit both `apiKey` and `authIdentity` → auto SystemAssigned MI |
| 15 | OWUI infinite page loop | Check DATABASE_URL password matches PostgreSQL |
| 16 | OWUI `tools[0].type` error | Remove `tools` from model `params` JSON |
| 17 | OWUI Pipe model tool injection | Set `capabilities.builtin_tools: false` in model `meta` |
| 18 | OWUI analytics 0 for API calls | Use LiteLLM proxy for token tracking |

---

## 📁 Folder Guide — อะไรไว้ไหน

```
EnterpriseChat/
├── CONTEXT.md              ← ไฟล์นี้ — Domain glossary, infra, architecture, folder guide
├── .gitignore              ← Git ignore rules
│
├── config/                 ← 🛠️ Configuration & Code
│                               Open WebUI Functions (pipe/tool/filter),
│                               Docker configs, LiteLLM config, Compose files
│                               → ไว้เพิ่ม config ใหม่ของ services, functions, compose
│
├── scripts/                ⚡ Scripts (deploy, ingest, setup)
│                               Python, Shell, JS — deploy, ingest, setup, utility scripts
│                               → ไว้เพิ่ม ingestion scripts, deployment scripts
│
├── docs/                   📖 Documentation
│   ├── adr/                → Architecture Decision Records
│   ├── azure/              → Provisioning session notes
│   ├── artifacts/          → Design renders, poster, philosophy
│   └── presentations/      → .pptx slide decks
│                               → ไว้เพิ่ม note, spec, decision doc, presentation
│
├── documents/              📄 Source Documents (local copies)
│   ├── haadthip-ir/        → Investor Relations (PDFs from company website)
│   ├── haadthip-public/    → Corporate IT / Policy / Public disclosure
│   ├── mihcm-hr/           → HR policies, forms, manuals (from MiHCM)
│   └── sap-hip/            → SAP HIP manuals
│                               → ไว้เพิ่มไฟล์ต้นฉบับที่ต้องการ ingest เข้า Search
│
├── data/                   📦 Data files (exports, collections, DB dumps)
│                               JSONL, Postman collections, SQL dumps
│                               → ไว้เพิ่ม exported data, test fixtures
│
├── screenshots/            🖼️ Screenshots & walkthrough captures
│   ├── sessions/           → Session screenshots
│   └── mihcm/              → MiHCM screen captures
│                               → ไว้เพิ่ม screenshot ที่ถ่ายตอน dev/test
│
└── icons/                  🎨 Azure architecture SVG icons
                                ใช้ใน architecture diagram / docs
                                → ไว้เพิ่ม icon ถ้าต้องการ service ใหม่
```

### หลักการ

| งานประเภท | วางที่ |
|-----------|--------|
| 🔧 Configuration / Function code | `config/` |
| ⚡ Script รันครั้งเดียว / deploy / ingest | `scripts/` |
| 📝 Documentation / note / ADR | `docs/` |
| 📄 ไฟล์ต้นทางที่ต้องการให้ AI Search รู้จัก | `documents/` |
| 📊 Dataset / export / collection | `data/` |
| 🖼️ Screenshot / ภาพถ่าย | `screenshots/` |
| 🎨 SVG icon / asset | `icons/` |
```

---

## Microsoft Teams App — Genie

### Overview

แอป **Genie (GenieHaadthipChat)** ถูก register ใน Teams Developer Portal สำหรับให้พนักงานหาดทิพย์เปิดใช้งาน Genie AI Assistant ได้โดยตรงภายใน Microsoft Teams

### Configuration

| Field | Value |
|-------|-------|
| **App Name** | GenieHaadthipChat |
| **App ID** | `06f1c5da-92d8-421d-9839-a528508550f6` |
| **Version** | 1.0.0 |
| **Developer** | บริษัท หาดทิพย์ จำกัด (มหาชน) |
| **Website** | https://www.haadthip.com |
| **Privacy Policy** | https://www.haadthip.com/privacy-policy |
| **Terms of Use** | https://www.haadthip.com/terms-of-use |
| **Entra ID Client ID** | `4881351e-d1a0-4228-a084-a0d6ef717740` |
| **SSO App ID URI** | `api://genie.haadthip.com/4881351e-d1a0-4228-a084-a0d6ef717740` |
| **Content URL (Personal Tab)** | https://genie.haadthip.com |
| **Valid Domains** | `genie.haadthip.com` |

### Developer Portal Links

| Section | URL |
|---------|-----|
| Dashboard | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/dashboard |
| Branding | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/branding |
| App Features | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/app-features |
| Domains | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/domains |
| Basic Info | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/details |
| Single Sign-On | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/single-sign-on |
| App Validation | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/validation |
| Publish to Org | https://dev.teams.microsoft.com/apps/06f1c5da-92d8-421d-9839-a528508550f6/publish-org |

### Icons

| Icon | File | Size |
|------|------|------|
| Color Icon | `icons/haadthip-color-icon-192.png` | 192×192 px |
| Outline Icon | `icons/haadthip-outline-icon-32.png` | 32×32 px |
| Logo Source | `icons/haadthip-logo.svg` | SVG from Wikimedia Commons |
| **Design** | โลโก้หาดทิพย์ (ขาว) + "Enterprise Chat" (ขาว) บนพื้นกรมท่า `#002F6C` + เส้นแดง `#ED2024` ล่างสุด |

**Brand Colors:**
| Color | Hex | Usage |
|-------|-----|-------|
| Navy Blue | `#002F6C` | Accent color, icon background |
| Red | `#ED2024` | Logo accent (Coca-Cola red) |
| Green | `#007D47` | Logo accent |

### SSO Setup Note

การตั้งค่า SSO ใน Teams Developer Portal (`api://genie.haadthip.com/4881351e-d1a0-4228-a084-a0d6ef717740`) ต้องไปตั้งค่าฝั่ง **Entra ID App Registration** เพิ่มด้วย:
1. เข้าไปที่ App Registration → `4881351e-d1a0-4228-a084-a0d6ef717740`
2. **Expose an API** → ตั้ง `Application ID URI` = `api://genie.haadthip.com/4881351e-d1a0-4228-a084-a0d6ef717740`
3. เพิ่ม **Scope** เช่น `access_as_user` สำหรับ Teams app
4. **Authentication** → เพิ่ม Redirect URI:
   - `https://token.botframework.com/.auth/web/redirect` (for Bot SSO)
   - หรือ Single-page Application URI = `https://genie.haadthip.com`

### Publish Steps

1. ✅ **App Validation** — รันตรวจสอบ error/warning ก่อน publish
2. **Publish to Org** — ส่งให้ IT Admin อนุมัติผ่าน [Teams Admin Center](https://admin.teams.microsoft.com/)
3. Admin → Teams apps → Manage apps → ค้นหา "GenieHaadthipChat" → Set to **Allowed**
4. ผู้ใช้ติดตั้งจาก "Built for your org" ใน Teams Apps

> ⚠️ Privacy/Terms URLs ปัจจุบันใช้ placeholder (`https://www.haadthip.com/privacy-policy`, `https://www.haadthip.com/terms-of-use`) — ต้องสร้างหน้า real ก่อน publish จริง

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
