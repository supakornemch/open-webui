---
title: "🚀 Create Procurement AI Agent — VISUAL STEP-BY-STEP GUIDE"
date: "2026-07-30"
status: "✅ Ready to Follow"
---

# 🚀 Create Procurement AI Agent — VISUAL STEP-BY-STEP

**ทำตามขั้นตอนนี้เพื่อสร้าง Agent พร้อมใช้งาน** (ใช้เวลา 10-15 นาที)

---

## ✅ STEP 1: เปิด Open WebUI และ Login

### 1.1 เปิดเบราว์เซอร์
```
ไปที่: http://localhost:3000
```

### 1.2 Ensure you're logged in
- ถ้าไม่ได้ login → กรอก username/password
- ต้องเห็นอักษร "DIO Supakorn" หรือ username ของคุณที่มุมบนขวา

---

## ✅ STEP 2: สร้าง Tool ใหม่

### 2.1 ไปที่ Workspace → Tools
```
1. คลิกเมนู "พื้นที่ทำงาน" (Workspace) ที่ด้านซ้าย
2. ในหน้า Workspace จะเห็นแท็บต่างๆ อย่าง "Models", "Tools", "Agents"
3. คลิกแท็บ "Tools" (หรือ "เครื่องมือ")
```

### 2.2 สร้าง Tool ใหม่
```
1. ในหน้า Tools หาปุ่ม "สร้าง" + dropdown menu
2. เลือก "Create Tool" หรือ "New Function Tool"
3. เต็มฟอร์ม:
   
   Name (ชื่อ):
   procurement_price_lookup
   
   Display Name (ชื่อแสดง):
   Procurement Price Lookup
   
   Description (คำอธิบาย):
   ค้นหาราคาและข้อมูลสินค้า Trade Marketing Materials
```

### 2.3 Copy-Paste Tool Code
```
1. ไปที่ไฟล์: tools/procurement-price-lookup.py
2. Copy ทั้งหมด (Ctrl+A, Ctrl+C)
3. Paste ลงใน "Code" field ของ Tool

   📝 Tool Code Location:
   requirements/procurement-ai-chat/tools/procurement-price-lookup.py
```

### 2.4 Define 3 Functions
```
Tool มี 3 ฟังก์ชั่น ที่ต้องตั้ง:

📌 Function 1: lookup_price
   Description: ค้นหาราคาสินค้า
   Parameters:
   - item_name (string, required) → "เสื้อยืด"
   - quantity (number, optional) → 100
   - category (string, optional) → "Garment"

📌 Function 2: get_item_details
   Description: ดูรายละเอียดสินค้า
   Parameters:
   - item_id (string, required) → "PRT-001"

📌 Function 3: list_categories
   Description: แสดงหมวดหมู่สินค้า
   Parameters:
   (ไม่มี parameters)
```

ℹ️ **Tips:**
- เปิด `tools/openwebui-tool-definition.json` เพื่อดูรายละเอียด parameters
- ถ้า UI ไม่ให้ add functions → ส่วนใหญ่ auto-detect จาก Python code

### 2.5 Save Tool
```
คลิก "Save" หรือ "Create"
✅ รอสักครู่ให้ Tool บันทึก
```

---

## ✅ STEP 3: สร้าง Agent ใหม่

### 3.1 ไปที่ Workspace → Agents
```
1. ไปที่หน้า Workspace (ซ้าย sidebar)
2. คลิกแท็บ "Agents" (หรือ "ตัวแทน")
```

### 3.2 สร้าง Agent ใหม่
```
1. หาปุ่ม "สร้าง" → "Create Agent"
2. เต็มข้อมูล:

   Name (ชื่อ):
   Procurement AI Assistant 🤖
   
   Description (คำอธิบาย):
   ผู้ช่วยตรวจสอบราคาสื่อการตลาด Trade Marketing Materials
   
   Model (โมเดล):
   gpt-5.4-mini
   
   System Prompt (ระบบคำสั่ง):
   [Copy ทั้งหมดจาก AGENT_PROMPT.md]
```

### 3.3 Copy System Prompt
```
1. ไปที่ไฟล์: AGENT_PROMPT.md
2. Copy ทั้งหมด (ทั้งส่วน markdown นั้น)
3. Paste ลงใน "System Prompt" field ของ Agent

📝 File Location:
requirements/procurement-ai-chat/AGENT_PROMPT.md
```

### 3.4 เลือก Model
```
1. ใน dropdown "Model" เลือกหนึ่งในนี้:
   
   ✅ gpt-5.4-mini  (แนะนำ - เร็ว + ราคาถูก)
   ✅ gpt-5.4       (ดีกว่า - reasoning ดีกว่า)
```

### 3.5 Attach Tool
```
1. เลื่อนลงไปหา "Tools" section
2. เห็น checkbox หรือ dropdown ของ tools ที่ available
3. ✅ เลือก "procurement_price_lookup"

⚠️ ต้องมี checkmark ✅ นะครับ
```

### 3.6 Save Agent
```
คลิก "Save" หรือ "Create" ที่มุมขวาล่าง
✅ รอให้ Agent บันทึก (อาจใช้เวลา 5-10 วิ)
```

---

## ✅ STEP 4: ทดสอบ Agent

### 4.1 ไปที่ Chat
```
1. คลิก "แชทใหม่" (New Chat) ที่ด้านบนซ้าย
2. เลือก Agent: "Procurement AI Assistant 🤖"
   (จาก Model dropdown)
```

### 4.2 ทดสอบคำถาม 3 ข้อ

#### Test 1️⃣ — ค้นหาราคา
```
พิมพ์:
ราคาเสื้อยืดเท่าไหร่ถ้าอยากได้ 100 ตัว สีเข้ม?

คาดหวัง:
Agent จะตอบค่ะ
- เสื้อยืด (สีเข้ม) ×100 ตัว
- ราคา: XXX,XXX บาท
- Vendor: [ชื่อ]
```

#### Test 2️⃣ — แสดงหมวดหมู่
```
พิมพ์:
มีหมวดสินค้าอะไรบ้างในระบบ?

คาดหวัง:
- POSM
- Printing
- Garment
- Premium
```

#### Test 3️⃣ — ดูรายละเอียด
```
พิมพ์:
ช่วยดูรายละเอียดสินค้า PRT-001 หน่อย

คาดหวัง:
- ชื่อสินค้า
- ราคาต่าง tier
- Vendor ที่มี
- สินค้าที่เกี่ยวข้อง
```

---

## ❌ Troubleshooting

### ⚠️ "Tool not found" หรือ "Function calling failed"
```
ตรวจสอบ:
1. ✅ Tool ชื่อ "procurement_price_lookup" มีไหม? (Tools page)
2. ✅ Tool มี 3 functions หรือเปล่า?
3. ✅ Agent attach tool ไหม? (Agents page → edit → check Tools)
4. ✅ Click "Save" ให้ชัวร์ทีแรก
```

**แก้:** ให้ลบและสร้าง Tool/Agent ใหม่

---

### ⚠️ "Item not found" เมื่อค้นหาราคา
```
สาเหตุ: ชื่อสินค้าไม่ตรงกับในระบบ

แก้:
- ลองชื่ออื่น เช่น "ป้าย" แทน "ป้ายไวนิล"
- ถาม Agent "มีสินค้าอะไรบ้าง?"
- เปิด Excel: data/source/master-price-template.xlsx
  ดูชื่อสินค้าที่ถูกต้อง
```

---

### ⚠️ Agent ไม่เรียก Tool
```
สาเหตุ: System Prompt ไม่มี instructions ให้เรียก tool

ตรวจสอบ:
1. ✅ AGENT_PROMPT.md มี "วิธีการ" section?
2. ✅ มี "lookup_price" หรือ "get_item_details" หรือเปล่า?

ถ้าไม่มี:
1. Edit Agent
2. ไป "System Prompt" field
3. Replace ทั้งหมด ด้วยเนื้อหาจาก AGENT_PROMPT.md (ล่าสุด)
4. Save
```

---

## ✅ Verification Checklist

- [ ] Tool "procurement_price_lookup" ถูก create
- [ ] Tool มี 3 functions: lookup_price, get_item_details, list_categories
- [ ] Agent "Procurement AI Assistant 🤖" ถูก create
- [ ] Agent มี System Prompt จาก AGENT_PROMPT.md
- [ ] Agent มี Tool "procurement_price_lookup" attached
- [ ] Test 1: ค้นหาราคา ✅ ได้คำตอบ
- [ ] Test 2: แสดงหมวดหมู่ ✅ ได้คำตอบ
- [ ] Test 3: ดูรายละเอียด ✅ ได้คำตอบ

---

## 🎉 Success!

ถ้าผ่านทั้ง 3 tests → **Agent พร้อมใช้งานแล้ว!**

🎯 ตอนนี้คุณสามารถ:
- ถามราคาสินค้า ได้
- ดูรายละเอียดสินค้า ได้
- ขอคำแนะนำสินค้าที่เกี่ยวข้อง ได้

---

## 📞 Help

- **ยังมีปัญหา?** ดูไฟล์ `AGENT_SETUP.md` (more detailed)
- **อยากรู้เพิ่มเติม?** ดู `QUICK_SETUP.md`
- **ต้องรีเซต?** ลบและสร้าง Agent/Tool ใหม่ตามขั้นตอนนี้

---

**ทำสำเร็จ?** ลองใช้ Agent ของคุณแล้ว! 🚀

ตัวอย่างคำถาม:
- "ป้ายไวนิล 1 แผ่น ราคาเท่าไหร่?"
- "มีเสื้อโปโลไหม?"
- "ช่วยบอกราคาเก้าอี้ผู้บริหารในหมวด Premium"
