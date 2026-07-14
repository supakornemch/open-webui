# 🔧 Session 4 — Provision Enterprise Chat + DocWise (Clean Provision)

**Date:** 2026-07-03
**Subscription:** Azure for Students (`0ae5656c-...`)
**Tenant:** `799d5882-...`
**Region:** Southeast Asia

---

## ✅ สิ่งที่ทำสำเร็จ

### Phase 1: Cleanup
- ไม่มี resources ค้าง (`rg-entchat-poc-sea` ไม่มีอยู่) → ข้าม cleanup

### Phase 2: Provision (11 Resources)

#### Shared Resources (`rg-entchat-poc-sea`)

| Resource | Name | Status |
|----------|------|--------|
| Resource Group | `rg-entchat-poc-sea` | ✅ |
| Storage Account | `stentchatdoc001` (Standard_LRS, Hot) | ✅ |
| App Service Plan | `asp-entchat-poc-sea` (B2 Linux) | ✅ |
| PostgreSQL Flexible Server | `psql-entchat-poc-sea` (B1ms, v16, 32GB) | ✅ |
| AI Search | `srch-entchat-poc-sea` (Free tier) | ✅ |
| AI Foundry Hub | `aif-entchat-poc-sea` | ✅ (auto-created KV + Storage) |
| AI Foundry Project | `proj-entchat-poc-sea` (ARM template) | ✅ |
| AI Services | `aisrv-entchat-poc-sea` (AIServices kind, S0) | ✅ |

#### Enterprise Chat (Open WebUI)

| Resource | Name | Status |
|----------|------|--------|
| Web App | `app-entchat-owui-poc-sea` (Open WebUI container) | ✅ |
| App Settings | 16 settings (DB, Entra OIDC, timeout) | ✅ |
| URL | `https://app-entchat-owui-poc-sea.azurewebsites.net` | ✅ HTTP 200 |

#### Model Deployments

| Deployment | Model | Version | Status |
|-----------|-------|---------|--------|
| `deploy-gpt-54-nano` | gpt-5.4-nano | 2026-03-17 | ✅ Succeeded |
| `deploy-gpt-54-mini` | gpt-5.4-mini | 2026-03-17 | ✅ Succeeded |
| `deploy-gpt-54` | gpt-5.4 | 2026-03-05 | ✅ Succeeded |

#### DocWise

| Resource | Name | Status |
|----------|------|--------|
| Web App | `app-docwise-poc-sea` (placeholder `python:3.11-slim`) | ✅ |
| App Settings | 12 settings (DB, AI, Search, Storage, GPT) | ✅ |
| Blob Container | `documents` บน `stentchatdoc001` | ✅ |
| URL | `https://app-docwise-poc-sea.azurewebsites.net` | ✅ HTTP 503 (placeholder, expected) |

#### PostgreSQL

| Item | Value |
|------|-------|
| Host | `psql-entchat-poc-sea.postgres.database.azure.com` |
| DBs | `open_webui` ✅, `docwise` ✅ |
| Firewall | AllowAllAzureServices + MyLocalIP (184.22.228.220) |

#### Entra ID (Reused from Session 3)

| Item | Value |
|------|-------|
| App Registration | `Open WebUI — PoC` (ID: `607d2089-...`) |
| Client Secret | **NEW** → `2KS8Q~ir.EXkZDtyOIHUOac3xOHsfJK.EZva.cXg` (หมด 2026-12) |
| SP | ✅ `90f4fdb1-...` |
| Email claim | ✅ |
| Admin consent | ✅ (openid, email, profile, offline_access) |
| Redirect URI | `https://app-entchat-owui-poc-sea.azurewebsites.net/oauth/microsoft/callback` |

### Phase 3: Verify
- ✅ Resource list: 11 items in RG
- ✅ Open WebUI: HTTP 200
- ✅ DocWise: HTTP 503 (placeholder)
- ✅ PostgreSQL: `open_webui` + `docwise` databases
- ✅ Model deployments: 3/3 Succeeded

---

## 🐛 Issues & Fixes

| Issue | Fix |
|-------|-----|
| AI Services soft-deleted (`aisrv-entchat-poc-sea`) | Purge ก่อนแล้วสร้างใหม่ |
| Entra ID Client Secret หมดอายุ | สร้าง secret ใหม่ `2KS8Q~ir...` |
| PostgreSQL local connection timeout | เพิ่ม firewall rule `MyLocalIP` |

## 📝 Files Updated

| File | Change |
|------|--------|
| `scripts/provision-poc-resources.sh` | Updated password + Entra ID credentials |
| `notes/2026-07-03-session4-provision.md` | **NEW** — This file |
| `tasks/active.md` | Updated session notes |

---

## 💰 Estimated Cost

| Service | Est. Monthly |
|---------|-------------|
| App Service Plan B2 | ~$25-33 |
| PostgreSQL B1ms | ~$12 |
| Storage (shared) | <$1 |
| AI Search (Free) | $0 |
| AI Services (pay-per-use) | tokens only |
| **Total (fixed)** | **~$37-46/mo** |

## 🔜 Next Steps (จาก active tasks)
1. ตั้งค่า DocWise pipeline (AI Content Understanding + LLM)
2. ทดสอบ demo end-to-end
3. จัดเตรียม DB backup
