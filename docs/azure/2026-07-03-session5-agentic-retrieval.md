# 🔧 Session 5 — Agentic Retrieval + Managed Identity

**Date:** 2026-07-03
**Subscription:** Azure for Students
**Region:** Southeast Asia

---

## ✅ สิ่งที่ทำสำเร็จ

### 1. AI Search: Free → Basic Upgrade
- ลบ `srch-entchat-poc-sea` (Free) → สร้างใหม่เป็น `srch-entchat-poc-sea-01` (Basic)
- ⚠️ Free → Basic upgrade ไม่ได้โดยตรง — ต้องลบแล้วสร้างใหม่
- Delete operation ใช้เวลา > 2 นาที background — ต้องใช้ชื่อ `-01` เพราะชื่อเดิมยังติด

### 2. Document Ingestion Pipeline
- สร้าง Data Source `haadthip-public-ds` (Blob → `haadthip-public` container)
- สร้าง Skillset `haadthip-public-skillset` (Document Extraction skill)
- สร้าง Index `haadthip-public-idx` (semantic config: `haadthip-semantic`)
- สร้าง Indexer `haadthip-public-idxr` → รันแล้ว 18 docs indexed
- ⚠️ `htc-sustainability-report-2024-en.pdf` (25MB) เกิน Basic tier limit (16MB)
- ⚠️ `htc-one-report-2024-en.pdf` ถูก truncate content ที่ 524,288 chars

### 3. Agentic Retrieval — Knowledge Base
**Key Discovery: API URL เป็น OData-style ไม่ใช่ RESTful**
```http
✅ PUT {endpoint}/knowledgesources('{name}')?api-version=2026-04-01
❌ PUT {endpoint}/knowledge-sources/{name}?api-version=2026-04-01
```

**Knowledge Source** `haadthip-ks`:
- `kind: searchIndex`
- `searchIndexName: haadthip-public-idx`
- `sourceDataFields: metadata_storage_name, content, category`
- `searchFields: metadata_storage_name, content`

**Knowledge Base** `haadthip-kb`:
- Source: `haadthip-ks`
- Model: `deploy-gpt-54-mini` (gpt-5.4-mini)
- Endpoint: `https://aisrv-entchat-poc-sea.cognitiveservices.azure.com/` (⚠️ ใช้ `cognitiveservices.azure.com` ไม่ใช่ `api.cognitive.microsoft.com`)

### 4. Managed Identity Auth
- ✅ Enable SystemAssigned MI on `srch-entchat-poc-sea-01`
- ✅ Role: `Cognitive Services OpenAI User` → scope `aisrv-entchat-poc-sea`
- ✅ KB config: remove `apiKey` → ใช้ MI auth แทน
- ⚠️ ตอน role assignment ต้อง `az ad sp create --id <principal-id>` ก่อน

### 5. Retrieve Test Results

| Query | Results | Time |
|-------|---------|------|
| "วิธีการตั้งค่า MFA" | 3 docs (MFA docs) | 245ms |
| "VPN" | 1 doc (VPN guide) | 118ms |
| "นโยบาย DLP" | 1 doc (DLP policy) | 104ms |

---

## 🐛 Issues & Fixes

| Issue | Fix |
|-------|-----|
| AI/Knowledge-sources REST API 404 | ใช้ OData-style URL: `knowledgesources('name')` |
| Knowledge Base model resourceUri error | ใช้ `cognitiveservices.azure.com` suffix |
| Role assignment "Cannot find user" | `az ad sp create --id <principal-id>` |
| Knowledge Source fields empty | เพิ่ม `sourceDataFields`, `searchFields` |

---

## 🔗 References

- [Knowledge Sources API](https://learn.microsoft.com/en-us/rest/api/searchservice/knowledge-sources/create-or-update?view=rest-searchservice-2026-04-01)
- [Knowledge Bases API](https://learn.microsoft.com/en-us/rest/api/searchservice/knowledge-bases/create-or-update?view=rest-searchservice-2026-04-01)
- [Knowledge Retrieval API](https://learn.microsoft.com/en-us/rest/api/searchservice/knowledge-retrieval/retrieve?view=rest-searchservice-2026-04-01)
- [API Versions](https://learn.microsoft.com/en-us/rest/api/searchservice/search-service-api-versions)
