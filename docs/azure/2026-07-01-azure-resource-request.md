# Azure Resource Request — สำหรับ Demo 2-Week

**Deadline**: 14-15 ก.ค. 2026
**Region**: Southeast Asia (Singapore) — ตาม EnterpriseChat architecture spec
**Budget**: ~$25-35/month (POC scale — Container Apps Consumption Plan)

---

## Required Azure Resources

### 1. Enterprise Chat (Open WebUI บน ACA)

| Resource | Purpose | SKU / Tier |
|----------|---------|------------|
| Azure Container Apps Environment | Host Open WebUI container | Consumption Plan (scale-to-zero) |
| Azure PostgreSQL Flexible Server | Open WebUI database | B1ms Burstable |
| Azure Blob Storage | File uploads / object storage | Standard LRS |
| Azure Key Vault | Manage secrets (API keys, DB creds) | Standard |

### 2. DocWise (Document OCR + Summarization)

| Resource | Purpose | SKU / Tier |
|----------|---------|------------|
| Azure AI Content Understanding | OCR + content extraction | Pay-as-you-go |
| (Blob Storage from above can be reused) | Document storage | — |

### 3. LLM Access

| Option | Notes |
|--------|-------|
| **Personal API Key** (OpenAI / Claude) | ใช้ก่อนได้ทันที สำหรับ POC |
| Azure OpenAI (request later) | ต้องขอ access approval อาจช้า |

---

## Estimated Cost (POC)

| Service | Est. Monthly |
|---------|-------------|
| Container Apps (Consumption) | ~$5-10 |
| PostgreSQL B1ms | ~$10-15 |
| Blob Storage | ~$1-2 |
| Key Vault | ~$1-2 |
| AI Content Understanding | ~$3-5 (usage-based) |
| **Total** | **~$25-35/month** |

อ้างอิงจาก EnterpriseChat ADR — architecture ถูกออกแบบให้ cost-efficient ในช่วง POC

---

## Step-by-step Request

1. ขอ **Azure subscription** (POC) + Contributor access
2. ขอ **Azure OpenAI access** (ถ้าจะใช้ — หรือใช้ personal API key ไปก่อน)
3. ขอ approve budget ~$35/month

เมื่อได้ access แล้ว provisioning steps:
- `az containerapp up` / Azure Portal — deploy Open WebUI
- `az postgres flexible-server create` — database
- `az storage account create` — blob storage
- `az keyvault create` — secrets
- `az cognitiveservices account create` — AI Content Understanding

---

## Timeline Dependency

```
Week 1 (1-8 ก.ค.): ขอ resource → รอ approve → provision infra
Week 2 (8-14 ก.ค.): Build & configure demo → ทดสอบ
14-15 ก.ค.: Demo คุณริกกี้ 🎯
```
