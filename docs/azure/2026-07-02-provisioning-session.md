# 🔧 Provisioning Session — 2 ก.ค. 2026

**Objective:** สร้าง PoC Azure resources, ทดสอบ Open WebUI, export database, cleanup
**Subscription:** Azure for Students
**Region:** Southeast Asia
**Workspace:** `/Users/supakorn.emch/Workspace/Haadthip/agent-planner`

---

## ✅ สิ่งที่ทำสำเร็จ

### 1. Provision Azure Resources (17 resources)

#### 📦 rg-entchat-poc-sea (11 resources)
| Resource | Name | Status |
|---|---|---|
| Resource Group | `rg-entchat-poc-sea` | ✅ |
| App Service Plan B2 Linux | `asp-entchat-poc-sea` | ✅ ~$25-33/mo |
| Web App — Open WebUI | `app-entchat-owui-poc-sea` | ✅ Running on `ghcr.io/open-webui/open-webui:main` |
| Web App — DocWise (placeholder) | `app-docwise-poc-sea` | ✅ `python:3.11-slim` |
| PostgreSQL Flexible Server B1ms | `psql-entchat-poc-sea` | ✅ ~$12/mo |
| Storage Account (shared) | `stentchatdoc001` | ✅ <$1/mo |
| AI Search **Free** tier | `srch-entchat-poc-sea` | ✅ $0 (ประหยัด ~$245/mo จากแผน S1) |
| AI Foundry Hub | `aif-entchat-poc-sea` | ✅ $0 |
| AI Foundry Project | `proj-entchat-poc-sea` | ✅ $0 (สร้างผ่าน ARM template) |
| Azure OpenAI | `oai-entchat-poc-sea` | ✅ Resource created แต่ deploy model ไม่ได้ (quota) |
| Key Vault | `aifentchkeyvault*` | ✅ Auto-created โดย Foundry Hub |

#### 🤖 rg-ir-poc-sea (6 resources)
| Resource | Name | Status |
|---|---|---|
| ML Workspace Basic | `mlw-ir-poc-sea` | ✅ $0 |
| Storage Account | `stirhaadthip001` | ✅ <$1/mo |
| + dependencies | KV, AppInsights, LogAnalytics | ✅ Auto-created |

### 2. PostgreSQL พร้อม Data

- Database `open_webui` → **Alembic migrations run สำเร็จ** → 30+ tables
- Firewall: `AllowAllAzureServices` (0.0.0.0) + IP local
- Password URL-encoded: `H%40adthipP0c05ef252e%21`

### 3. Open WebUI Boot สำเร็จ (HTTP 200)

**Bug ที่เจอระหว่างทาง + วิธีแก้:**
1. ❌ `@` ใน password ทำลาย URL parsing → ✅ URL-encode `H%40adthipP0c05ef252e%21`
2. ❌ PostgreSQL firewall ไม่มี Azure service rule → ✅ เพิ่ม `AllowAllAzureServices`
3. ❌ Database `open_webui` ไม่มี → ✅ `CREATE DATABASE open_webui`
4. ❌ Container startup time 230s ไม่พอ (embedding model download) → ✅ `WEBSITES_CONTAINER_START_TIME_LIMIT=1800`
5. ❌ Custom startup command พัง → ✅ clear startup command กลับเป็นค่า default

### 4. Database Export

| File | Size | Location |
|---|---|---|
| `data/open_webui_poc.dump` | 79 KB | Binary (pg_restore) |
| `data/open_webui_poc.sql` | 70 KB | SQL (human-readable) |

### 5. Provisioning Script

| File | Purpose |
|---|---|
| `scripts/provision-poc-resources.sh` | Script 295 lines — provision ครบทุก step + create DB + settings + model deployments (AIServices kind) |

### 6. 🎯 Key Discovery: AIServices Kind (ไม่ใช่ OpenAI Kind)

**Student subscription deploy model ได้** ถ้าใช้ resource kind `AIServices` แทน `OpenAI`

| Resource Kind | OpenAI | AIServices |
|---|---|---|
| CLI create | `--kind OpenAI` | `--kind AIServices` |
| Deploy GPT-5.4 series | ❌ `InsufficientQuota` | ✅ **ได้!** |
| Deploy DeepSeek | ❌ (ต้องขอ quota) | ❌ (ไม่มีใน catalog) |
| ราคา | เท่ากัน | เท่ากัน |

**Models deployed สำเร็จบน AIServices:**
- `gpt-5.4-nano` (OCR/Summarize)
- `gpt-5.4-mini` (mid-tier chat)
- `gpt-5.4` (general-purpose)

> ⚠️ DeepSeek-V4 ไม่มีใน AIServices resource — มีแค่ GPT series
> ต้องใช้ OpenAI resource kind + quota increase เพื่อ deploy DeepSeek

### 7. Cleanup (ลบทั้งหมด)

- `rg-entchat-poc-sea` → 11 resources ✅ ลบแล้ว
- `rg-ir-poc-sea` → 7 resources ✅ ลบแล้ว
- **Total cost saved:** ~$40-48/mo (ถ้าไม่ลบ)

---

## 📚 Files Created/Updated

| File | Change |
|---|---|
| `notes/2026-07-02-azure-resource-plan-final.md` | Updated status → "Verified & Complete" |
| `notes/2026-07-02-provisioning-session.md` | **NEW** — This file |
| `tasks/active.md` | Marked 3 tasks completed, added 2 new tasks |
| `data/open_webui_poc.dump` | **NEW** — PostgreSQL binary dump |
| `data/open_webui_poc.sql` | **NEW** — PostgreSQL SQL dump |
| `scripts/provision-poc-resources.sh` | **NEW** — Full provisioning script |

---

## ⚠️ Lessons Learned

1. **Student subscription limits:**
   - Azure OpenAI model deployment **ต้องขอ quota** (0 quota ทั้งหมด)
   - Storage account names unique ทั่วโลก → `stirpoc001` ถูกใช้แล้ว → เปลี่ยนเป็น `stirhaadthip001`
   - vCPU quota 6 cores (พอสำหรับ PoC เล็ก)

2. **Azure App Service + Container tips:**
   - ต้องตั้ง `WEBSITES_PORT` explicit
   - Container startup timeout default 230s → B2 RAM 3.5GB อาจช้า → ต้องเพิ่ม
   - อย่า override startup command ถ้าไม่แน่ใจ (container image ทำมาแล้ว)

3. **PostgreSQL Flexible Server:**
   - `--public-access 0.0.0.0` สร้าง firewall rule แค่ให้ Azure services เข้า → ต้องเพิม `AllowAllAzureServices` เอง
   - Database name ต้องมีอยู่แล้ว → Alembic migration **ไม่สร้าง database**
   - Password ที่มี `@` / `!` / `#` ต้อง URL-encode ก่อนใส่ใน DATABASE_URL

---

## 🔜 Next Steps (for next session)

1. แก้ Azure OpenAI quota — deploy GPT-5.4-nano + DeepSeek-V4-Pro
2. สร้าง DocWise container image จริง (OCR + Summarize pipeline)
3. ทดสอบ RAG / Vector Search เชื่อม AI Search Free tier
4. n8n workflow orchestration — วางแผน deployment
5. MCP Hub container — ตาม ADR-0001
