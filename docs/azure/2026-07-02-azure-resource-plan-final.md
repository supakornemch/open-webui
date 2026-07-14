# Azure Resource Plan — PoC Final (Verified & Complete)

**Updated:** 2 ก.ค. 2026 (Provisioned + Cleaned Up ✅)
**Deadline:** 14-15 ก.ค. 2026
**Region:** Southeast Asia (Singapore)
**Environment:** POC
**Data Size:** ~50 MB documents

---

## 🚀 ตารางสรุป — ส่ง Infra Team

### 1️⃣ Enterprise Chat & AI Document

| # | Resource Name | Service / SKU | Purpose | Cost/Mo |
|---|---|---|---|---|
| 1 | `rg-entchat-poc-sea` | Resource Group | Group all resources | $0 |
| 2 | `asp-entchat-poc-sea` | App Service Plan **B2 Linux** (2 vCPU, 3.5 GB) | Host 2 web app containers | ~$26 |
| 3 | `app-entchat-owui-poc-sea` | Web App for Containers (แชร์ ASP #2) | Open WebUI — Enterprise Chat UI | $0 |
| 4 | `app-docwise-poc-sea` | Web App for Containers (แชร์ ASP #2) | AI Document — OCR + Summarize | $0 |
| 5 | `psql-entchat-poc-sea` | PostgreSQL Flexible Server **B1ms** (1 vCore, 2 GiB, 10 GB) | Shared DB สำหรับ 2 apps | ~$13 |
| 6 | `stentchatdoc001` | Storage Account **Standard LRS Hot** | Shared file storage สำหรับ 2 apps (~50 MB) | <$1 |
| 7 | `aif-entchat-poc-sea` | Azure AI Foundry Hub | AI project hub — shared connections | $0 |
| 7.1 | `proj-entchat-poc-sea` | AI Foundry Project (ใต้ Hub #7) | จัดการ models, tools, deployments | $0 |
| 8 | `srch-entchat-poc-sea` | Azure AI Search **S1 Standard** (1 SU) | Vector store + RAG retrieval | ~$245 |
| 9 | `aisrv-entchat-poc-sea` | Azure AI Services (AIServices) | LLM host resource — **ใช้ `--kind AIServices` (ไม่ใช่ OpenAI)** | $0 |
| 20 | `appreg-entchat-owui-poc` | Microsoft Entra ID App Registration | Open WebUI — OAuth2/OIDC login | $0 |

> **หมายเหตุ:** #5 `psql-entchat-poc-sea` และ #6 `stentchatdoc001` ใช้ร่วมกันทั้ง 2 web apps (#3, #4)
>
> **หมายเหตุ:** Azure AI Content Understanding ไม่ต้องสร้าง resource แยก — เปิดใช้ได้ที่ **AI Foundry Portal → Discover → Tools** (pay-as-you-go)

---

### 2️⃣ Model Deployments (บน `oai-entchat-poc-sea`)

| # | Deployment Name | Model | Input / 1M tok | Output / 1M tok | Usage |
|---|---|---|---|---|---|
| 10 | `deploy-deepseek-v4-pro` | DeepSeek-V4-Pro | $1.74 | $3.48 | Complex reasoning |
| 11 | `deploy-deepseek-v4-flash` | DeepSeek-V4-Flash | $0.19 | $0.51 | General tasks (cost-efficient) |
| 12 | `deploy-gpt-5.4` | GPT-5.4 | $2.50 | $10.00 | Chat |
| 13 | `deploy-gpt-5.4-nano` | GPT-5.4-nano | $0.20 | $1.25 | OCR / Summarize |
| 14 | `deploy-gpt-5.4-mini` | GPT-5.4-mini | $0.75 | $4.50 | Mid-tier tasks |

> Token-based only — ไม่มีค่าคงที่

---

### 3️⃣ IR Service (Image Recognition)

| # | Resource Name | Service / SKU | Purpose | Cost/Mo |
|---|---|---|---|---|
| 15 | `rg-ir-poc-sea` | Resource Group | Group all resources | $0 |
| 16 | `mlw-ir-poc-sea` | ML Workspace **Basic** | AutoML training + deployment | $0 |
| 17 | `ep-ir-poc-sea` | Online Endpoint **Standard Managed** (CPU) | Object detection inference | ~$10–15 |
| 18 | `compute-ir-poc-sea` | Compute Cluster **On-demand** (scale to zero) | Training only | ~$0–5 |
| 19 | `stirpoc001` | Storage Account **Standard LRS** | Training data + model artifacts | <$1 |

---

### 4️⃣ Entra ID App Registration — Open WebUI Login

| # | Resource Name | Service | Purpose | Cost/Mo |
|---|---|---|---|---|
| 20 | `appreg-entchat-owui-poc` | Microsoft Entra ID App Registration | Open WebUI — OAuth2/OIDC login (SSO) | $0 |

#### ⚙️ การตั้งค่า App Registration

| ตั้งค่า | ค่า |
|---|---|
| **Display Name** | `Open WebUI — PoC` (หรือ `appreg-entchat-owui-poc`) |
| **Supported account types** | Single tenant — เนื่องจาก internal use only |
| **Redirect URI (Web)** | `https://app-entchat-owui-poc-sea.azurewebsites.net/oauth/microsoft/callback` |
| **Redirect URI (SPA)** | `https://app-entchat-owui-poc-sea.azurewebsites.net` |
| **Authentication protocol** | **OIDC** (OpenID Connect) — Microsoft-specific vars |
| **Client secret** | สร้างและเก็บไว้ใน Open WebUI env vars |
| **API Permissions** | `openid`, `email`, `profile`, `offline_access` (Microsoft Graph delegated) |
| **Token configuration** | เพิ่ม optional claim **`email`** สำหรับ ID tokens (จำเป็นสำหรับ Open WebUI) |

#### 🔗 Open WebUI Env Vars (เพิ่มใน `app-entchat-owui-poc-sea`)

> ⚠️ **อัปเดต 2026-07-02:** เปลี่ยนจาก generic OIDC vars (`OIDC_CLIENT_ID` ฯลฯ) ที่ Open WebUI **ไม่รู้จัก**
> ไปใช้ **Microsoft-specific vars** ตาม official docs: <https://docs.openwebui.com/features/authentication-access/auth/sso/>

```
WEBUI_URL=https://app-entchat-owui-poc-sea.azurewebsites.net
WEBUI_SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENABLE_OAUTH_SIGNUP=true
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true
MICROSOFT_CLIENT_ID=<client-id-from-app-registration>
MICROSOFT_CLIENT_SECRET=<client-secret>
MICROSOFT_CLIENT_TENANT_ID=<tenant-id>
MICROSOFT_REDIRECT_URI=https://app-entchat-owui-poc-sea.azurewebsites.net/oauth/microsoft/callback
MICROSOFT_OAUTH_SCOPE=openid email profile offline_access
OPENID_PROVIDER_URL=https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
```

> **หมายเหตุ:** App Registration ไม่ใช่ Azure resource แบบมีค่าใช้จ่าย — เป็น identity config ใน Entra ID เท่านั้น (ฟรี)
>
> **หมายเหตุ:** CAF ไม่มี abbreviation อย่างเป็นทางการสำหรับ App Reg — ใช้ `appreg-` ตาม community convention
>
> **หมายเหตุ:** ต้องเพิ่ม **email optional claim** ใน Token configuration ของ App Registration
> ไม่เช่นนั้น Open WebUI จะไม่สามารถ login ด้วย OIDC ได้ (ต้องมี email claim ใน ID token)
>
> **หมายเหตุ:** ถ้า DocWise ต้องการ login ด้วย → สร้าง App Reg แยก (เช่น `appreg-docwise-poc`)

---

## 💰 Cost Summary

| Project | Fixed Cost/Mo | Variable |
|---|---|---|
| Enterprise Chat & AI Document | **~$285** | + Content Understanding (usage) + LLM tokens |
| IR Service | **~$11–21** | + Training compute (on-demand) |
| App Registration | **$0** | — |
| **Total (fixed)** | **~$296–306/mo** | |

---

## 📌 Notes สำหรับ Infra Team

1. **Open WebUI** เชื่อม PostgreSQL ผ่าน env var `DATABASE_URL=postgresql://user:pass@psql-entchat-poc-sea.postgres.database.azure.com:5432/openwebui`
2. **AI Content Understanding** ไม่ต้องสร้าง resource แยก — เข้า AI Foundry Portal → Discover → Tools → deploy analyzer
3. **Foundry Hub** จะ auto-provision Key Vault + Storage ของตัวเอง (แยกจาก #6)
4. **IR Online Endpoint** แนะนำใช้ CPU SKU เล็กสุดที่รัน inference ได้ + scale to zero เพื่อประหยัด
5. **App Registration** (`appreg-entchat-owui-poc`) — สร้างใน Entra ID → set Redirect URI → รับ client ID + secret → config Open WebUI env vars
6. ชื่อ resources ทั้งหมดตาม **Azure CAF naming convention**: `<type>-<workload>-<env>-<region>`

---

## ✅ สิ่งที่ตรวจสอบแล้ว

| รายการ | สถานะ | รายละเอียด |
|---|---|---|
| App Service Plan B2 Linux | ⚠️ แก้ไขแล้ว | ราคาจริง **~$25.55/เดือน** (ไม่ใช่ $43) — ราคาอาจต่างตาม region SEA |
| PostgreSQL B1ms | ⚠️ แก้ไขแล้ว | Compute only **$12.41/เดือน** (1 vCore, 2 GiB) — ยังไม่รวม storage + backup |
| Storage Account LRS | ⚠️ แก้ไขแล้ว | 50 MB × $0.018/GB = **~$0.001 ≈ < $1** — แทบฟรี |
| Azure AI Foundry Hub | ⚠️ แก้ไขแล้ว | Hub เอง **ฟรี** — ไม่มี S0 tier แยก — Content Understanding เป็น pay-as-you-go ($0.01–5/1,000 pages) |
| Azure AI Search S1 | ✅ ถูกต้อง | **~$245.28/เดือน** (1 Search Unit) — confirmed |
| Azure ML Workspace | ✅ ถูกต้อง | Workspace Basic **ฟรี** — ค่า compute แยก |
| Online Endpoint | ✅ ถูกต้อง | ขึ้นอยู่กับ VM SKU — Standard_DS2_v2 ~$0.10/hr = ~$73/เดือนถ้า always-on แต่ POC ควรใช้ CPU เล็กกว่า |
| Key Vault | ✅ ลบแล้ว | ตามที่ขอ — ไม่รวมในแผน (Hub จะ auto-provision ของตัวเอง) |
| DeepSeek-V4-Pro | ✅ พร้อมใช้ | GA บน Azure AI Foundry — $1.74/$3.48 per 1M tokens |
| DeepSeek-V4-Flash | ✅ พร้อมใช้ | GA บน Azure AI Foundry — $0.19/$0.51 per 1M tokens |
| GPT-5.4 | ✅ พร้อมใช้ | GA — $2.50/$10.00 per 1M tokens |
| GPT-5.4-nano | ✅ พร้อมใช้ | GA (Mar 17, 2026) — $0.20/$1.25 per 1M tokens |
| GPT-5.4-mini | ✅ พร้อมใช้ | GA — $0.75/$4.50 per 1M tokens |
| GPT-5.5 / 5.5-nano | ⚠️ ลบออก | GPT-5.5 GA (Apr 24, 2026) แต่ **5.5-nano ยังไม่วางจำหน่าย** — เปลี่ยนเป็น GPT-5.4 series |
| Content Understanding | ✅ พร้อมใช้ | ย้ายเป็น **Foundry Tool** แยก — หาได้ที่ **Discover → Tools** ใน AI Foundry Portal — pay-as-you-go ($0.01–5/1,000 pages) |
| Foundry Project | ✅ เพิ่มแล้ว | Project (`proj-entchat-poc-sea`) สร้างภายใต้ Hub — ตัว Project เองฟรี — ใช้จัดการ deployments, models, tools แยกเป็น workstream |
| App Registration | ✅ เพิ่มแล้ว | `appreg-entchat-owui-poc` — Entra ID App Registration สำหรับ Open WebUI OIDC login — ฟรี |
| Deprecated resources | ✅ ตรวจแล้ว | **ไม่มี resource ใด deprecated** — ทั้งหมดพร้อมใช้งาน |

---

## ⚠️ ประเด็นที่ควรทราบ

1. **AI Search S1 ใหญ่เกินไปสำหรับ POC 50 MB?**
   - Free tier: 50 MB, 3 indexes, vector search ✅
   - ถ้า data ไม่เกิน 50 MB → ใช้ **Free tier ได้ฟรี** ประหยัด $245/เดือน
   - แต่ Free tier **ไม่สามารถ upgrade โดยตรง** — ต้องสร้าง resource ใหม่ถ้าจะเปลี่ยน
   - **แนะนำ:** เริ่มด้วย Free tier ก่อน ถ้า data เกินค่อยย้าย S1

2. **App Service Plan B2 Linux ~$25.55 เป็นราคา US region**
   - Region Southeast Asia อาจแพงขึ้น 10-30% → ประมาณ **$28–33**
   - ตรวจสอบที่ [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/) เลือก Southeast Asia

3. **IR Online Endpoint — ต้องระบุ VM SKU**
   - Standard_DS2_v2 (2 vCPU, 7 GB) ~$0.10/hr → ~$73/เดือนถ้า always-on
   - Standard_F2s (2 vCPU, 4 GB) ~$0.07/hr → ~$51/เดือน
   - **แนะนำ:** ใช้ SKU เล็กสุดที่รัน inference ได้ + scale to zero

4. **PostgreSQL B1ms — 2 GiB RAM อาจน้อยสำหรับ 2 แอพ**
   - Open WebUI + DocWise แชร์ DB เดียวกัน
   - ถ้าใช้พร้อมกันหนัก → พิจารณา **B2ms** ($99.28/เดือน) หรือ **GP vCore 2** แทน
   - **แนะนำ POC:** เริ่ม B1ms ก่อน จนกว่าจะมี performance issue

5. **App Registration — Redirect URI**
   - ต้องระบุ URL ตรงกับ Web App URL จริง
   - ถ้า deploy แล้ว URL เปลี่ยน → ต้องกลับมาแก้ Redirect URI ใน App Reg

---

## 📐 โครงสร้าง Azure AI Foundry — Hub vs Project

```
AI Foundry Hub (aif-entchat-poc-sea)
├── เป็น resource หลัก — จัดการ shared connections, compute, policies
├── Hub เองฟรี — ไม่มีค่าคงที่
├── สร้าง Key Vault + Storage อัตโนมัติเมื่อสร้าง Hub
│
└── Project (proj-entchat-poc-sea)
    ├── สร้างภายใต้ Hub — เป็น workstream แยก
    ├── Project เองฟรี
    ├── ใช้จัดการ: deployments, models, tools, data
    │
    └── Discover → Tools
        └── Azure AI Content Understanding
            ├── อยู่ใน Discover → Tools ใน AI Foundry Portal
            ├── เป็น Foundry Tool (managed API)
            ├── เลือก Deploy → สร้าง Analyzer (Read / Layout)
            └── ราคา: pay-as-you-go ($0.01–5/1,000 pages)
```

### สิ่งที่ควรทราบเกี่ยวกับ Hub + Project

| หัวข้อ | รายละเอียด |
|---|---|
| **Hub vs Project** | Hub = ระดับองค์กร (shared resources) → Project = ระดับทีม/งาน (scoped workstream) |
| **Hub สร้างอะไรอัตโนมัติ** | Key Vault + Storage Account (แยกจาก `stentchatdoc001` ที่เราสร้างเอง) |
| **Project ฟรีไหม** | ฟรี — ไม่มีค่าคงที่ จ่ายเฉพาะ resources ที่ใช้ใน project |
| **1 Hub = กี่ Projects** | ไม่จำกัด — แต่ POC นี้ใช้ 1 Hub : 1 Project พอ |
| **Content Understanding อยู่ไหน** | AI Foundry Portal → **Discover → Tools** → Azure AI Content Understanding |
| **ใช้ Content Understanding ยังไง** | เลือก Analyzer type (Read / Layout) → Deploy → ได้ endpoint + key → เรียก API |

---

## 🔐 Entra ID App Registration — โครงสร้าง

```
Microsoft Entra ID (Tenant)
│
└── App Registration (appreg-entchat-owui-poc)
    ├── Display Name: "Open WebUI — PoC"
    ├── Single Tenant (internal)
    ├── Redirect URIs:
    │   ├── Web:  https://app-entchat-owui-poc-sea.azurewebsites.net/oauth/callback
    │   └── SPA:  https://app-entchat-owui-poc-sea.azurewebsites.net
    ├── API Permissions: User.Read
    ├── Client ID + Client Secret → เก็บใน Open WebUI env vars
    │
    └── Users login flow:
        User → Open WebUI → redirect to Microsoft login
        → authenticate with Entra ID
        → callback to /oauth/callback
        → Open WebUI session created
```

---

## 📐 Naming Convention (ตาม Azure CAF)

```
<resource-type>-<workload>-<environment>-<region>[-<instance>]
```

- lowercase + hyphens เท่านั้น (ยกเว้น Storage Account ไม่มี hyphen)
- ตัวอย่าง: `psql-entchat-poc-sea`, `stentchatdoc001`, `mlw-ir-poc-sea`
- App Registration: ใช้ `appreg-` (community convention — CAF ไม่มี abbreviation อย่างเป็นทางการ)

### Abbreviations ที่ใช้

| Resource | Abbreviation | หมายเหตุ |
|---|---|---|
| Resource Group | `rg` | |
| App Service Plan | `asp` | |
| Web App / Container | `app` | |
| PostgreSQL Server | `psql` | |
| Storage Account | `st` | **ไม่มี hyphen** — global unique |
| Azure AI Search | `srch` | |
| Azure AI Foundry Hub | `aif` | |
| AI Foundry Project | `proj` | |
| Azure OpenAI | `oai` | |
| ML Workspace | `mlw` | |
| App Registration | `appreg` | Community convention (CAF ไม่มี official) |

---

## 🔗 References

- [App Service Linux Pricing](https://azure.microsoft.com/en-us/pricing/details/app-service/linux/)
- [PostgreSQL Flexible Server Pricing](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/)
- [Storage Account Blob Pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [AI Foundry / Content Understanding Pricing](https://azure.microsoft.com/en-us/pricing/details/content-understanding/)
- [AI Search Pricing](https://azure.microsoft.com/en-us/pricing/details/search/)
- [Azure ML Pricing](https://azure.microsoft.com/en-us/pricing/details/machine-learning/)
- [Azure OpenAI Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-openai/)
- [DeepSeek Foundry Models Pricing](https://azure.microsoft.com/en-us/pricing/details/ai-foundry-models/deepseek/)
- [Azure CAF Resource Naming](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- [Azure CAF Abbreviations](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations)
- [Azure Content Understanding Overview](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/overview)
- [What's New in Content Understanding — Build 2026](https://devblogs.microsoft.com/foundry/whats-new-in-azure-content-understanding-at-build-2026/)
- [Hubs and Hub-Based Project Overview](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/ai-resources)
- [App Registration Naming Convention (Microsoft Q&A)](https://learn.microsoft.com/en-us/answers/questions/2259155/suggestions-for-naming-convention-in-app-registrat)
