# Genie — Enterprise AI Agent Setup

> พร้อมสำหรับ DIO Team Beta Testing 🚀  
> Platform: https://genie.haadthip.com

---

## 🎯 Agent 1: Genie — ปรึกษาเอกสารภายใน

### วิธีติดตั้ง

1. **เพิ่ม Tool:** `Admin Panel → Functions → + → paste`
   - ไฟล์: `config/tool-enterprise-search.py`
   - Save → Enable

2. **เพิ่ม Pipe:** `Admin Panel → Functions → + → paste`
   - ไฟล์: `config/pipe-enterprise-knowledge.py`
   - Save → Enable

3. **ตั้ง Model:** `Workspace → Models → Add Model`
   - Name: `Genie — Enterprise Knowledge`
   - Model ID: `genie-enterprise-knowledge`
   - Pipe: เลือก `Genie — Enterprise Knowledge (Pipe)`
   - 🔧 Tools: enable `search_internal_docs`, `search_hr_policies`
   - Save

4. **ใช้งาน:** เลือก `Genie — Enterprise Knowledge` เป็น model → ถามได้เลย

### ตัวอย่างคำถาม

| Domain | ตัวอย่าง |
|--------|---------|
| IT | "ตั้งค่า MFA ยังไง", "ต่อ VPN ไม่ได้ทำไง", "ตั้งอีเมลในมือถือ" |
| HR | "สิทธิ์ลากี่วัน", "เบิกค่าทำฟันยังไง", "กองทุนสำรองเลี้ยงชีพ", "OT ได้เท่าไหร่" |
| Policy | "นโยบาย PDPA", "จรรยาบรรณ", "วันหยุดปีนี้", "กฎการใช้รถบริษัท" |
| Open WebUI | "สร้าง Pipe ยังไง", "API สำหรับ chat completions", "ตั้ง SSO" |

---

## 🔧 Agent 2: Genie — HR ผู้ช่วย (Tool-based Agent)

สำหรับใช้กับ GPT-5.4-mini ใน Native/Agentic Mode:

```
Model: deploy-gpt-5.4-mini
Mode: Native (Agentic)
System Prompt:
  You are Genie HR, Haadthip's HR assistant. You help employees find
  information about policies, benefits, leave, training, and regulations.
  Always search documents before answering. Cite document names.

Tools Enabled:
  ✅ search_hr_policies
  ✅ search_internal_docs
```

---

## 📢 Announcement Template (DIO Team)

```
🚀 เปิด Beta Test: Genie — Enterprise AI Chat Platform

สวัสดีทีม DIO ครับ

ตอนนี้เรามี Platform AI Chat สำหรับใช้งานภายในแล้วที่:
👉 https://genie.haadthip.com

อยากชวนทุกคนมาลองใช้และให้ Feedback ครับ

📚 Genie รู้อะไรบ้าง?
- คู่มือ IT: MFA, VPN, Email, Meeting Room, DLP
- เอกสาร HR: ประกาศ, คำสั่ง, สวัสดิการ, ระเบียบ (122 ฉบับ)
- คู่มือ Open WebUI: API, Features, Tools

💬 ลองถามได้เลยเช่น:
- "ลากิจต้องยื่นกี่วันล่วงหน้า"
- "ตั้ง MFA ในมือถือยังไง"
- "เบิกค่าทำฟันได้เท่าไหร่"

🎯 อยากได้ Feedback:
1. ลองใช้แล้วเจอปัญหาอะไรบ้าง?
2. อยากให้เพิ่มเอกสารอะไร?
3. มี Use Case อะไรที่คิดว่า AI ช่วยงานได้จริง?

แจ้ง Feedback ได้ที่: [ช่องทาง/คนที่รับผิดชอบ]
```

---

## 📊 Corpus Coverage

| Corpus | Docs | Chunks | Topics |
|--------|------|--------|--------|
| corporate | 17 | 120 | Security, Email, Meeting, IT Policy, AGM |
| hr-policies | 122 | 654 | Policies, Orders, Benefits, Forms, Newsletters |
| openwebui-docs | 2 URLs | 371 | API Reference, Features Guide |

---

## 🔄 อัพเดท Documents

```bash
# เมื่อเพิ่มไฟล์ใหม่ใน documents/
cd EnterpriseChat
python3 scripts/preprocess-docs.py
export AZURE_SEARCH_KEY="..."
python3 scripts/upload-to-search.py

# อัพเดท Open WebUI docs
python3 scripts/ingest-openwebui-docs.py --upload
```
