# Handoff: Procurement Price Assistant & Genie QAS Operations

- **Date:** 2026-09-11
- **Workspace:** `/Users/supakorn.emch/Workspace/Haadthip/EnterpriseChat`
- **Target Environment:** Azure QAS (`SUB-HTC-QAS-DC`, `RG-INCUBATION-AI-QAS-SEA`)
- **Key URLs:**
  - Genie WebUI: `https://genie-qas.haadthip.com` (Requires VPN)
  - OWUI App Service: `https://app-entchat-owui-qas.azurewebsites.net`
  - LiteLLM Gateway: `https://app-litellm-qas.azurewebsites.net`
  - Azure AI Search: `https://srch-entchat-qas.search.windows.net` (Index: `procurement-catalog-v1`)

---

## 1. Executive Summary
This session finalized the Confluence project hub documentation, updated and synchronized the Procurement Price Assistant tool (`procurement_price_search` v3.3) and Pipe (`procurement_price_pipe` v1.2) to QAS PostgreSQL, fixed upstream model routing & auth, verified full 13/13 E2E test regressions, built an 8-slide executive presentation for the 14:00 procurement meeting, resolved GPT-5.6 Luna tool-calling compatibility issues, enabled prompt caching across all base models, and verified prompt cache hits on `deploy-gpt-5.6-luna`.

---

## 2. Completed Work & State Changes

### A. Procurement Tool & Pipe Synchronization (QAS)
- **Tool:** Updated `procurement_price_search` to **v3.3** in QAS Open WebUI DB (`open_webui`).
- **Pipe:** Updated `procurement_price_pipe` to **v1.2** with valve `LLM_MODEL = 'deploy-gpt-5.6-luna'`.
- **Database & Upstream Fix:**
  - Fixed LiteLLM Virtual Key connection in Open WebUI config (`openai.api_keys` set to `litellm-vkey-entchat-qas` value, `openai.api_base_urls` pointing to `https://app-litellm-qas.azurewebsites.net/v1`).
  - Cleaned up orphaned group access grants (`dbebf665-efe0-4fdc-bbfe-4138173b8530`).
  - Active RBAC permission group remains: `procurement-team` (`read` on assistant, pipe, and tool).

### B. E2E Regression Verification
- Executed `features/procurement/scripts/qas_procurement_regression.py` directly against live QAS OWUI & LiteLLM:
  - **Result:** **13/13 passed (100%)**
  - Verified exact match, Thai/English language switching, typos (`รมโค้ก`, `โคมไฟสำเรจรูป`), quantity tiers (Arch 60x70 5 units vs 15 units), below-MOQ warning (Ice bucket & Umbrella), and zero-result handling (`iPhone 15 Pro Max`).

### C. GPT-5.6 Luna & Tool-Calling Fix
- **Issue:** Switching to `deploy-gpt-5.6-luna` threw `BadRequestError: Function tools with reasoning_effort are not supported for deploy-gpt-5.6-luna in /v1/chat/completions`.
- **Resolution:** Removed `reasoning_effort: "medium"` from `custom_params` of `procurement-price-assistant` and `procurement-price-assistant-api` in DB while preserving `prompt_cache_key`.
- **Result:** Live tool calling via Luna works cleanly with 100% regression pass rate.

### D. Prompt Caching Verification on LiteLLM QAS
- Added `custom_params: {"prompt_cache_key": "genie-qas"}` across all 17 base models (`genie.deploy-*`).
- Tested live prompt caching on `deploy-gpt-5.6-luna`:
  - Request 1 (Cache Write): `cache_write_tokens: 2711`, `cached_tokens: 0`
  - Request 2 & 3 (Cache Hit): `cached_tokens: 2704` (99.7% hit rate), `cache_write_tokens: 7`
  - Cache read cost: `$0.10 / 1M tokens` (90% discount).

### E. User & Group Management
- User batch provisioning directly via SQL was removed to avoid schema incompatibilities that caused 500 error on `/api/v1/users/`.
- The users overview endpoint is fully restored (`HTTP 200`).
- Target users for trial:
  1. `DIO Aroonporn Wongpruek` (`aroonporn@haadthip.com`)
  2. `DIO Supakorn Emchannon` (`supakorn.em@haadthip.com`)
  3. `Patcharee Puttasang` (`patcharee.put@haadthip.com`)
  4. `Densri Kalanuson` (`densri.ka@haadthip.com`)
  5. `DIO Sumalee Noonang` (`sumalee@haadthip.com`)
  6. `DIO Jutarat Siripongprapan` (`jutarat@haadthip.com`)
  7. `Tanita Karnjanakuldumrong` (`tanita@haadthip.com`)
  8. `Phanuchat Prasarnsong` (`phanuchat@haadthip.com`)
- Recommended workflow: Users sign in with Microsoft SSO on `genie-qas.haadthip.com`, then admin adds them to the `procurement-team` group via UI or SQL.

### F. Jira & Confluence
- **Jira DID-119:** Closed and transitioned to `Done` (superseded by DID-120).
- **Confluence (Space INCUBATION):** All 5 core documents verified:
  - Hub: [2883649](https://dio-haadthip.atlassian.net/wiki/spaces/INCUBATION/pages/2883649)
  - User Guide: [3342365](https://dio-haadthip.atlassian.net/wiki/spaces/INCUBATION/pages/3342365)
  - Architecture Spec: [3375129](https://dio-haadthip.atlassian.net/wiki/spaces/INCUBATION/pages/3375129)
  - Trial Spec: [2850817](https://dio-haadthip.atlassian.net/wiki/spaces/INCUBATION/pages/2850817)
  - Runbook: [3342387](https://dio-haadthip.atlassian.net/wiki/spaces/INCUBATION/pages/3342387)

---

## 3. Persistent Artifacts & Locations
- **Presentation Deck HTML (HaadThip Brand):**
  `/Users/supakorn.emch/Workspace/Haadthip/presentation/procurement-assistant-deck.html`
- **OpenDesign Project:** `procurement-assistant-presentation-9bb9`
- **Regression Harness:**
  `features/procurement/scripts/qas_procurement_regression.py`
- **Regression Results JSON:**
  `features/procurement/scripts/qas-regression-results.json`
- **Confluence Knowledge Management Lessons:**
  Updated in skill `productivity/confluence-knowledge-management`

---

## 4. Pending / Next Action Items (The Frontier)
1. **Meeting at 14:00:**
   - Present `procurement-assistant-deck.html`
   - Conduct live interactive demo on `https://genie-qas.haadthip.com` (VPN required) using model `procurement-price-assistant` (backed by GPT-5.6 Luna).
2. **User Onboarding after First Sign-in:**
   - As procurement users log in via Microsoft SSO, assign them to `procurement-team` group.
3. **1-Week Trial Tracking (11 – 18 Sep 2026):**
   - Collect user queries, accuracy feedback, and thumbs up/down reactions in OWUI.
4. **DID-120 Implementation:**
   - Proceed with extracting the shared domain module per ADR-0001 when scheduled.

---

## 5. Known Pitfalls & Rules
- **GPT-5.6 Luna Tool Calling:** NEVER pass `reasoning_effort` when using tools in `/v1/chat/completions`.
- **Open WebUI User Insert:** Do not insert bare records into PostgreSQL `"user"` table without standard OAuth attributes; let users sign in first via SSO.
- **VNet Constraint:** Outbound internet is restricted from App Service; all model calls route through LiteLLM.

---

## 6. Suggested Skills for Next Session
- `productivity/atlassian-jira` — For tracking DID-120 and trial feedback tickets.
- `productivity/confluence-knowledge-management` — For maintaining space docs and handover updates.
- `software-development/docwise-dev` / `software-development/containerized-app-stacks` — For backend architecture and deployment.
