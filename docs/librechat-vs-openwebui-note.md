# 📝 LibreChat vs Open WebUI — เปรียบเทียบ & การติดตั้ง LibreChat ท้องถิ่น

> บันทึกเมื่อ: 2 กรกฎาคม 2026

---

## 🆚 สรุปเปรียบเทียบ

| หัวข้อ | LibreChat | Open WebUI |
|---|---|---|
| **License** | ✅ **MIT** (เสรี 100%, ใช้เชิงพาณิชย์ได้) | ⚠️ Custom License (ต้อง preserve branding) |
| **Tech Stack** | React + Node.js + MongoDB | Svelte + Python (FastAPI) |
| **Database** | MongoDB | SQLite / PostgreSQL |
| **จุดเน้น** | Multi-provider cloud AI, Agents, Code Interpreter | Local models (Ollama), Enterprise RAG, Workspace |
| **Azure Readiness** | ✅ **ดีเยี่ยม** — first-class Azure OpenAI endpoint, Azure Marketplace, Azure Blob, Bicep/Terraform IaC | ⚠️ รองรับผ่าน OpenAI-compatible หรือ community guide |
| **Azure AI Foundry v1** | ✅ รองรับ | ❌ [ยังไม่รองรับ Entra ID auth](https://github.com/open-webui/open-webui/issues/24761) |
| **GitHub Stars** | ~40K | ~143K |
| **RAG** | Basic (ผ่าน RAG API + pgvector) | ✅ แข็งแรงกว่า (9 vector DBs, hybrid search, reranking) |
| **Enterprise Auth** | ✅ OIDC/Entra ID | ✅ OIDC/Entra ID + SSO |
| **SCIM** | ❌ ไม่มี | ❌ ยังไม่รองรับ Entra ID native |

---

## ☁️ Azure Backbone — LibreChat เหนือกว่า

เมื่อใช้ **Azure เป็น backbone หลัก** LibreChat มีข้อได้เปรียบ:

1. **Azure OpenAI endpoint** → first-class citizen รองรับ multi-region, model groups, Assistants API
2. **Azure Marketplace** → [official listing](https://marketplace.microsoft.com/en-us/product/cloud-infrastructure-services.librechat) one-click deploy
3. **Azure Blob Storage** → native CDN/storage support
4. **IaC templates** → Bicep / Terraform + GitHub Actions
5. **Azure Entra ID** → OAuth2/OIDC official docs

---

## 🐳 การติดตั้ง LibreChat ท้องถิ่น (Local Docker)

### สิ่งที่ติดตั้ง
- **Repo:** https://github.com/danny-avila/LibreChat
- **Path:** `~/Workspace/LibreChat-app/`
- **Port:** `3080` (LibreChat UI) / `4000` (Admin Panel)

### วิธีรัน

```bash
cd ~/Workspace/LibreChat-app

# ครั้งแรก — create directories
mkdir -p images uploads logs data-node meili_data_v1.35.1

# รัน
docker compose up -d

# เช็กสถานะ
docker compose ps

# ดู log
docker logs LibreChat -f

# หยุด
docker compose down
```

### การตั้งค่า
- **`.env`** → อยู่ที่ `~/Workspace/LibreChat-app/.env`
- ตั้ง `MONGO_URI=mongodb://mongodb:27017/LibreChat` (สำหรับ Docker)
- `ADMIN_PANEL_SESSION_SECRET` ต้องมี (generate ด้วย `openssl rand -hex 32`)
- `MEILI_MASTER_KEY` ต้องมีสำหรับ Meilisearch

### การเข้าถึง
| บริการ | URL |
|---|---|
| LibreChat UI | http://localhost:3080 |
| Admin Panel | http://localhost:4000 |

### การใช้ Azure OpenAI
- ไปที่ Settings → เลือก Azure OpenAI → ใส่ Endpoint + API Key
- หรือตั้งค่าผ่าน `librechat.yaml` (recommended สำหรับ production)

---

## 🔗 แหล่งอ้างอิง

- [LibreChat Azure OpenAI Config](https://www.librechat.ai/docs/configuration/librechat_yaml/ai_endpoints/azure)
- [LibreChat Azure Marketplace](https://marketplace.microsoft.com/en-us/product/cloud-infrastructure-services.librechat)
- [LibreChat Azure Entra ID](https://www.librechat.ai/docs/configuration/authentication/OAuth2-OIDC/azure)
- [LibreChat Azure Blob Storage](https://www.librechat.ai/docs/configuration/cdn/azure)
- [LibreChat Container Apps (Bicep)](https://www.elumenotion.com/journal/librechatbicep/)
- [LibreChat Terraform + GitHub Actions](https://philipwelz.com/how-to-deploy-librechat-your-own-gpt-on-azure-with-terraform-and-github-actions)
- [Open WebUI Official Comparison](https://docs.openwebui.com/alternatives/librechat/)
- [Open WebUI Azure OpenAI Tutorial](https://docs.openwebui.com/tutorials/integrations/llm-providers/azure-openai/)
