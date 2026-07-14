# EnterpriseChat — User Walkthrough Agenda

**Date:** 9 July 2026 · **Duration:** ~45-60 min · **Audience:** End Users

---

## Part 0: Prep (before session)

| # | Task | Detail |
|---|------|--------|
| 1 | เพิ่ม redirect URI | Portal → App Registration `Open WebUI — Sandbox PoC` → Add `https://app-litellm-poc-sand.azurewebsites.net/sso/callback` |
| 2 | Restart LiteLLM | `az webapp restart -g RG-ENTCHAT-POC-SAND-SEA -n app-litellm-poc-sand` |
| 3 | Verify both up | OWUI: `https://app-entchat-owui-poc-sand.azurewebsites.net` · LiteLLM UI: `https://app-litellm-poc-sand.azurewebsites.net/ui` |
| 4 | เปิด tabs เตรียมไว้ | OWUI · LiteLLM UI · architecture-view.html |

---

## Part 1: Overview (5 min)

### 1.1 What is EnterpriseChat?

```
User (Browser) ──▶ Open WebUI ──▶ LiteLLM ──▶ Azure AI Foundry (GPT-5.x)
                         │              │
                    Entra ID SSO    Token Tracking
                    PostgreSQL      Cost Monitoring
```

| Layer | What | Why |
|-------|------|-----|
| **Open WebUI** | Chat UI (เหมือน ChatGPT แต่องค์กร) | พนักงานคุยกับ AI ได้ผ่านเบราว์เซอร์ |
| **LiteLLM Proxy** | ตัวกลางคั่นระหว่าง UI กับ AI | วัด token usage, คุม cost, จัดการ keys |
| **Azure AI Foundry** | GPT-5.4 models (Nano/Mini/5.4/5.2) | สมอง AI จริงๆ |

### 1.2 Key Numbers

- 5 AI Models (GPT-5.4 Nano → GPT-5.4 ใหญ่สุด)
- 4 Knowledge Bases (Corporate / SAP / IR / HR)
- 3 Databases (open_webui / docwise / litellm)
- 1 SSO (Entra ID — login ด้วย @haadthip.com)

---

## Part 2: Live Demo — Open WebUI (15 min)

### 2.1 Login

> **URL:** https://app-entchat-owui-poc-sand.azurewebsites.net
> **Auth:** Click "Sign in with Microsoft" → ใช้ @haadthip.com account

### 2.2 Basic Chat

| Step | Action | Show |
|------|--------|------|
| 1 | New Chat → พิมพ์ "สวัสดี คุณคือใคร" | Basic response |
| 2 | เลือก model `gpt-5.4-mini` จาก dropdown | Model switching |
| 3 | ถามภาษาไทย: "ช่วยอธิบายขั้นตอนการขอ MFA หน่อย" | Thai language + KB search |

### 2.3 Knowledge Base Search (Pipes)

| Pipe | ใช้ถามเรื่อง | ตัวอย่างคำถาม |
|------|------------|-------------|
| **Haadthip Knowledge** | IT Policy, MFA, VPN, Email, Meeting Room | "วิธี setup MFA ในโทรศัพท์ใหม่" |
| **SAP Knowledge** | SAP HIP manuals, Tcodes | "Tcode สำหรับบันทึกบัญชีลูกหนี้" |
| **IR Knowledge** | Investor Relations, Annual Report | "บริษัทมีผู้ถือหุ้นใหญ่กี่ราย" |
| **HR Knowledge** | งานบุคคล, สวัสดิการ, กฏระเบียบ | "นโยบายวันลาพักร้อนประจำปี" |

**วิธีใช้:** พิมพ์ `/` ในช่องแชท → เลือก Pipe ที่ต้องการ → ถามคำถาม

### 2.4 E-Expense FAQ

> ถามเรื่อง: แผนเดินทาง, เบิกทดรองจ่าย, เคลียร์ค่าใช้จ่าย, ค่ารักษาพยาบาล

"ขออนุมัติแผนเดินทางต่างประเทศต้องทำยังไง"

---

## Part 3: LiteLLM Dashboard (10 min)

> **URL:** https://app-litellm-poc-sand.azurewebsites.net/ui
> **Login:** `admin` / `sk-litellm-poc-master-key` (หรือ Entra SSO ถ้า setup แล้ว)

### 3.1 What you see

| Tab | Shows |
|-----|-------|
| **Dashboard** | Total requests, tokens, cost (ภาพรวม) |
| **Models** | 5 models available (Nano → Embedding) |
| **Keys** | API keys สำหรับต่อจากภายนอก (เช่น Continue.dev, Claude Code) |
| **Users** | ใครใช้เท่าไหร่ |
| **Logs** | ทุก request ที่ผ่าน — ใคร, โมเดลอะไร, กี่ token, latency |

### 3.2 Why LiteLLM matters

- ✅ **Token tracking** — รู้ว่าใครใช้เท่าไหร่ (แก้ปัญหา Analytics Dashboard ใน OWUI ที่โชว์ 0)
- ✅ **Cost monitoring** — รู้ค่าใช้จ่ายต่อคน/ทีม/เดือน
- ✅ **Key management** — แจก API key ให้ Dev ใช้จากภายนอก โดยไม่ต้องให้ Azure key จริง
- ✅ **Rate limiting** — กันคนใช้หนักเกิน
- ✅ **Audit log** — ทุก request ถูกบันทึก

---

## Part 4: Integration Patterns (10 min)

### 4.1 For End Users (Web Browser)

```
เปิด Browser → app-entchat-owui-poc-sand → Login Entra ID → แชทได้เลย
```

ไม่ต้อง install อะไร — มีแค่ browser + account @haadthip.com

### 4.2 For Developers / Tools

| Tool | How to Connect | API Key |
|------|---------------|---------|
| **Continue.dev** (VS Code) | ตั้ง provider เป็น OpenAI → URL: `app-litellm-poc-sand/v1` | ไปขอ key จาก LiteLLM UI |
| **Claude Code / Cursor** | OpenAI-compatible endpoint → `app-litellm-poc-sand/v1` | LiteLLM API key |
| **Custom App / Script** | `curl https://app-litellm-poc-sand/v1/chat/completions` | Bearer token |

### 4.3 Model Selection Guide

| Model | Cost | Use When |
|-------|------|----------|
| `gpt-5.4-nano` | $ (ถูกสุด) | Simple queries, KB search, quick lookups |
| `gpt-5.4-mini` | $$ | General chat, everyday use |
| `gpt-5.4` | $$$ | Complex reasoning, Thai documents, final answers |
| `gpt-5.2` | $$ | Fallback |
| `text-embedding-3-large` | $ | Vector search (behind the scenes) |

---

## Part 5: Q&A + Next Steps (5-10 min)

### FAQ Prep

| Question | Answer |
|----------|--------|
| "ข้อมูลองค์กรปลอดภัยไหม?" | ใช่ — อยู่ใน Azure Thailand, Private Endpoint, Azure เท่านั้น (ไม่ส่งข้อมูลออกนอก) |
| "ใช้มือถือได้ไหม?" | ได้ — Open WebUI เป็น Web App responsive |
| "เพิ่มเอกสารใหม่ยังไง?" | ทีม IT/Admin อัปโหลดผ่าน ingestion pipeline → ใช้ได้ทันที |
| "ถ้า AI ตอบผิด?" | AI อาจ hallucinate — ควร verify ข้อมูลสำคัญกับต้นทาง |
| "คนนอกเข้าได้ไหม?" | ไม่ได้ — ต้องมี @haadthip.com account ผ่าน SSO |

### Next Steps

- [ ] เพิ่ม users ทดลองใช้ (Internal User group)
- [ ] เก็บ feedback: โมเดลไหนใช้ดี? KB ไหนหาย?
- [ ] เตรียม production deployment plan

---

## Appendix: Quick Reference

| Resource | URL |
|----------|-----|
| Open WebUI | https://app-entchat-owui-poc-sand.azurewebsites.net |
| LiteLLM API | https://app-litellm-poc-sand.azurewebsites.net/v1 |
| LiteLLM Dashboard | https://app-litellm-poc-sand.azurewebsites.net/ui |
| Architecture Diagram | `architecture-view.html` (local file) |
| Full Docs | `CONTEXT.md` (project root) |
