# Genie Main — Promotion Plan from POC to Production

**Date**: 2026-09-16  
**Target**: Promote `genieai-poc-rbac` → `genieai` (main production assistant)  
**Approach**: Pipe-based model for full REST API + UI support

---

## Created Artifacts

### 1. **Genie Main Pipe** — `app/openwebui/functions/genie_main_pipe.py`

Production-ready Pipe combining:
- ✅ Delegated Fabric query tool (read-only SQL with permission preflight)
- ✅ System prompt from `genieai-poc-rbac` (v10)
- ✅ REST API one-call support (no multi-turn manual tool loop)
- ✅ Tool loop orchestration inside Pipe (up to 8 rounds)
- ✅ Prompt cache key `genie-qas` for fast responses

**Key differences from POC**:
- Native Tool model → Pipe model (REST API compatible)
- Tool schema embedded in Pipe code
- `query_fabric` description explicitly mentions discovery query
- MAX_TOOL_ROUNDS increased from 6 → 8

---

## System Prompt (from POC v10)

```text
คุณคือ "Haadthip AI" ผู้ช่วย AI สำหรับพนักงานและผู้ใช้งานของบริษัท หาดทิพย์ จำกัด (มหาชน) 
ให้บริการถามตอบทั่วไป ช่วยค้นคว้า อธิบาย วิเคราะห์ สรุป เขียน และช่วยแก้ปัญหา 
โดยตอบอย่างถูกต้อง ใช้งานได้จริง และเหมาะกับบริบทของผู้ใช้

## ภาษาและบุคลิก
- ตอบภาษาเดียวกับผู้ใช้เป็นหลัก: ภาษาไทยสำหรับคำถามภาษาไทย และภาษาอังกฤษสำหรับคำถามภาษาอังกฤษ
- ภาษาไทยให้สุภาพ เป็นกันเอง กระชับ แต่มีรายละเอียดพอให้ลงมือทำได้ 
  ใช้คำศัพท์เทคนิคภาษาอังกฤษในวงเล็บเมื่อช่วยให้เข้าใจชัดขึ้น
- เริ่มจากคำตอบที่ตรงคำถามก่อน แล้วค่อยเสริมเหตุผล ขั้นตอน ตัวอย่าง หรือข้อควรระวังตามความจำเป็น
- ถ้าคำถามกำกวมและมีผลต่อคำตอบ ให้ถามกลับเฉพาะประเด็นสำคัญ; 
  ถ้าพอมีสมมติฐานที่ปลอดภัย ให้ตอบภายใต้สมมติฐานนั้นและระบุสมมติฐานสั้นๆ

## ขอบเขตและแหล่งข้อมูล

1. คำถามความรู้ทั่วไปที่ไม่ขึ้นกับเวลา: ตอบจากความรู้ของโมเดลได้ 
   แต่ห้ามสร้างข้อเท็จจริง ตัวเลข ชื่อบุคคล แหล่งอ้างอิง หรือผลลัพธ์ที่ไม่มีหลักฐาน

2. คำถามที่ต้องการข้อมูลล่าสุด ข่าว ราคา กฎหมาย ซอฟต์แวร์ เอกสารออนไลน์ หรือเหตุการณ์ปัจจุบัน: 
   ใช้ web search เมื่อมีเครื่องมือ และอ้างอิงแหล่งข้อมูลที่น่าเชื่อถือ โดยระบุวันที่หรือช่วงเวลาที่เกี่ยวข้อง

3. คำถามเกี่ยวกับบริษัท หาดทิพย์ นโยบาย คู่มือ HR, IT, SAP, E-Expense หรือเอกสารภายใน: 
   ค้นจาก knowledge ที่แนบมา/มีสิทธิ์เข้าถึงก่อนตอบ อ้างอิงชื่อเอกสารหรือส่วนที่พบเมื่อเป็นไปได้ 
   ห้ามเดาจากความรู้ทั่วไปแทนข้อมูลบริษัท

4. **คำถามตัวเลข ยอดขาย เป้าหมาย ลูกค้า สินค้า เครดิต ตู้แช่ หรือข้อมูลใน Microsoft Fabric**: 
   **ใช้ tool `query_fabric` เสมอ** และใช้เฉพาะผล query จริง เริ่มจากตรวจ table/schema เมื่อไม่แน่ใจ
   
   **เมื่อผู้ใช้ถามว่า "เข้าถึงข้อมูลอะไรได้" หรือ "ดูให้หน่อยว่าฉันเข้าถึงข้อมูลอะไรได้จาก Fabric"**:
   เรียก `query_fabric` ทันทีด้วย SQL:
   ```sql
   SELECT TOP 10 table_schema, table_name 
   FROM INFORMATION_SCHEMA.TABLES 
   WHERE table_schema NOT IN ('sys', 'INFORMATION_SCHEMA')
   ORDER BY table_schema, table_name
   ```
   แล้วสรุปให้ผู้ใช้เห็นรายการตาราง พร้อมบอกว่าถ้าต้องการดูข้อมูลจริงให้ถามคำถามเฉพาะเจาะจงได้

5. ถ้าผู้ใช้แนบไฟล์หรือให้ข้อความมา ให้ยึดข้อมูลนั้นเป็นหลักสำหรับงานที่ขอ 
   ตรวจข้อจำกัดของไฟล์ก่อนสรุป และแยกสิ่งที่มาจากไฟล์ออกจากข้อสังเกตของคุณ

6. หากแหล่งข้อมูลขัดแย้งกัน ให้บอกความขัดแย้ง แสดงว่าแต่ละข้อมูลมาจากไหน และอย่าเลือกคำตอบเองโดยไม่อธิบายเหตุผล

7. ถ้าไม่พบข้อมูลหรือไม่มีสิทธิ์เข้าถึง ให้บอกตรงๆ ว่าไม่พบ/ไม่สามารถตรวจสอบได้ 
   และบอกสิ่งที่ผู้ใช้ควรส่งเพิ่มหรือแหล่งที่ควรตรวจ ไม่แต่งคำตอบขึ้นมา

## Fabric Query Rules (Delegated Permission)

- **ห้ามสร้างตัวเลขเอง** — ทุกตัวเลขต้องมาจาก `query_fabric` จริงเท่านั้น
- **ห้าม SELECT *** — ระบุ column ชัดเจนเสมอ
- **ใช้ schema.table** — เช่น `dbo.dim_customer`, `sales.fact_orders`
- **เริ่มจาก discovery** — ถ้าไม่รู้ว่ามีตารางอะไร ให้ query INFORMATION_SCHEMA.TABLES ก่อน
- **Permission preflight** — ระบบเช็คสิทธิ์อัตโนมัติ ถ้าไม่มีสิทธิ์จะบอกตารางที่ไม่สามารถเข้าถึงได้
- **Max 20 rows per query** — ใช้ pagination (offset) ถ้าต้องการมากกว่า

## หากไม่มี Fabric token

ถ้าผู้ใช้ยังไม่ได้ sign in ด้วย Microsoft OAuth หรือไม่มี delegated token:
- บอกตรงๆ ว่า "กรุณา sign out และ sign in อีกครั้งผ่าน Microsoft Entra ID เพื่อเข้าถึงข้อมูล Fabric"
- **ห้ามสร้างตัวเลข/ข้อมูลปลอมแทน**

## Response Style

- กระชับ ตรงประเด็น ใช้งานได้จริง
- ไม่เล่าประวัติ/ขั้นตอนที่ผู้ใช้ไม่ถาม
- ถ้าเป็นข้อมูลตัวเลข: แสดงเป็นตารางหรือ JSON อย่างเป็นระเบียบ
- ถ้าเป็นคำอธิบาย: ให้เหตุผลและตัวอย่างสั้นๆ
```

---

## Deployment Steps

### 1. Build & Push Image

```bash
cd docker
docker build --platform linux/amd64 \
  -f Dockerfile.owui \
  -t acrentchatqas.azurecr.io/entchat-owui:genie-v1.0.0 .

docker push acrentchatqas.azurecr.io/entchat-owui:genie-v1.0.0
```

### 2. Deploy to QAS App Service

```bash
az webapp config container set \
  --resource-group RG-INCUBATION-AI-QAS-SEA \
  --name app-entchat-owui-qas \
  --docker-custom-image-name acrentchatqas.azurecr.io/entchat-owui:genie-v1.0.0
```

### 3. Configure Function in Open WebUI

Navigate to: https://genie-qas.haadthip.com/workspace/functions

**Valves** (Function settings):
```yaml
FABRIC_ENDPOINT: ypmukualhmkuhbmumqiyxplusu-ytem5s6jyj6e5cg2lqqkuiiufq.datawarehouse.fabric.microsoft.com
DEFAULT_DATABASE: LH_OTC_TEST
ODBC_DRIVER: ODBC Driver 18 for SQL Server
ALLOWED_TENANT_ID: 5045d9c3-3b0b-4315-8594-64118bbd7495
LLM_BASE_URL: <LiteLLM base URL from env>
LLM_API_KEY: <LiteLLM key from env>
LLM_MODEL: genie.deploy-gpt-5.6-luna
MAX_TOOL_ROUNDS: 8
DEFAULT_LIMIT: 20
CONNECT_TIMEOUT: 15
```

### 4. Create Production Model Preset

Navigate to: https://genie-qas.haadthip.com/workspace/models/create

**Model Configuration**:
```yaml
Model ID: genieai
Name: Genie AI
Base Model: genie_main_pipe (select from Function dropdown)
System Prompt: <paste system prompt from above>
Capabilities:
  - file_context: true
  - vision: true
  - citations: true
  - status_updates: true
  - usage: true
  - memory: true
  - builtin_tools: true
  - web_search: false (enable via defaultFeatureIds if needed)
Knowledge:
  - ข้อมูลทั่วไป (ID: 66f0caec-14e6-4567-9764-e699b3f48c64)
Tool IDs: [] (empty — Pipe handles tools internally)
Builtin Tools:
  - subagents: false
  - calendar: false
Custom Params:
  - prompt_cache_key: genie-qas
  - compact_token_threshold: 550000
```

### 5. Set as Default Model

In Admin Panel → Settings → General:
- Default Model: `genieai`

### 6. Archive POC Model (Optional)

Keep `genieai-poc-rbac` for comparison but update description:
```
[DEPRECATED] POC version — use `genieai` instead (Pipe-based, REST API compatible)
```

---

## Testing Checklist

### UI Testing
- [ ] Login via Microsoft Entra ID (OAuth)
- [ ] Create new chat with `genieai` model
- [ ] Ask: "ดูให้หน่อยว่าฉันเข้าถึงข้อมูลอะไรได้จาก Fabric"
  - Should call `query_fabric` with INFORMATION_SCHEMA query
  - Should return table list or permission error
- [ ] Ask quantitative question: "ยอดขายเดือนนี้เท่าไหร่"
  - Should attempt discovery → query → answer
- [ ] Ask general question: "SAP คืออะไร"
  - Should answer from knowledge/model without Fabric call
- [ ] Verify citations and status updates display

### REST API Testing
```bash
curl -X POST https://genie-qas.haadthip.com/api/chat/completions \
  -H "Authorization: Bearer $OWUI_QAS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "genieai",
    "messages": [
      {"role": "user", "content": "ดูให้หน่อยว่าฉันเข้าถึงข้อมูลอะไรได้จาก Fabric"}
    ]
  }'
```

Expected:
- ✅ Single response with final answer
- ✅ No `tool_calls` in response (all handled inside Pipe)
- ✅ Response includes table list or permission explanation

---

## Migration Path for Existing Users

**Announcement** (send via Teams/Email):
```
🎉 Genie AI อัปเกรด v1.0!

อัปเดตสำคัญ:
✅ REST API ใช้งานได้เต็มรูปแบบ (one-call completion)
✅ Fabric query ตอบได้เร็วขึ้น (tool loop ภายใน)
✅ Discovery query: ถาม "เข้าถึงข้อมูลอะไรได้" แล้วได้คำตอบทันที
✅ Permission preflight: เช็คสิทธิ์ก่อนรัน query จริง

การเปลี่ยนแปลง:
- Model ID เปลี่ยนจาก `genieai-poc-rbac` → `genieai`
- POC model ยังใช้งานได้แต่ไม่แนะนำ (จะถูก archive ในอนาคต)
- Chat เดิมยังเปิดได้ แต่ chat ใหม่ให้เลือก `genieai`

ทดสอบได้ที่: https://genie-qas.haadthip.com
```

---

## Rollback Plan

If issues occur:

1. **UI rollback**: Change default model back to `genieai-poc-rbac`
2. **API rollback**: Clients can specify `"model": "genieai-poc-rbac"` in requests
3. **Image rollback**:
   ```bash
   az webapp config container set \
     --resource-group RG-INCUBATION-AI-QAS-SEA \
     --name app-entchat-owui-qas \
     --docker-custom-image-name acrentchatqas.azurecr.io/entchat-owui:<previous-tag>
   ```

---

## Success Metrics

Track for 2 weeks post-deployment:

- [ ] 95%+ of Fabric queries complete successfully (vs timeout/error)
- [ ] Average response time < 8s for queries with tool calls
- [ ] Zero "fabricated data" incidents (all numbers come from real queries)
- [ ] REST API usage increases (evidence: API call logs)
- [ ] User satisfaction survey: 4/5+ rating

---

## Known Limitations

1. **Max 20 rows per query** — users need to use pagination for larger datasets
2. **No write operations** — read-only by design
3. **Delegated token required** — users must login via Entra ID
4. **Single database** — currently hardcoded to `LH_OTC_TEST`
5. **Tool loop cap at 8 rounds** — complex multi-query tasks may need decomposition

---

## Future Enhancements (Post v1.0)

- [ ] Multi-database support (switch between LH_OTC_TEST, PROD, etc.)
- [ ] Query result caching (same query within 5min = cached result)
- [ ] Streaming responses for long-running queries
- [ ] Chart generation from query results (Plotly/Matplotlib)
- [ ] Export to Excel/CSV directly from chat
- [ ] Query history & saved queries per user
- [ ] Permission-based model routing (different models for different roles)

---

**Prepared by**: Hermes Agent (DIO)  
**Review required**: Supakorn EM (DIO Lead), QAS Admin
