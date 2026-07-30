# Procurement AI Chat — ระบบตอบราคาสื่อการตลาดอัตโนมัติ

## ที่มา

ระบบนี้ถูกออกแบบมาเพื่อตอบคำถามการขอราคาสื่อการตลาด (Trade Marketing Materials) ของบริษัท **HaadThip Public Company Limited** โดยใช้ LLM AI Chat ที่มีความรู้จากไฟล์ Excel Master ราคา Y2026 และเข้าใจรูปแบบการติดต่อทางอีเมล

---

## ข้อมูลนำเข้า

### 1. `data/source/Trade Marketing Materials price for Y2026.final.xlsx`
ไฟล์ Excel Master ราคาสื่อการตลาดประจำปี 2026

### 2. `data/source/email_samples.zip`
ตัวอย่างอีเมลคำขอราคา 22 ไฟล์ สำหรับใช้อ้างอิงรูปแบบการสื่อสาร

### 3. ✅ `docs/requirement-confirmation.md` — ยืนยัน Requirement จากทีม DIO
เอกสารยืนยันความต้องการระบบ (Procurement System Requirements Discussion) ลงวันที่ 16 กรกฎาคม 2569

**Key Requirements ที่เกี่ยวข้อง:**
- **กลุ่มสินค้า**: วัสดุส่งเสริมการขาย (Trade Marketing Materials) — Phase 1
- **กลุ่มผู้ใช้หลัก**: ฝ่ายขาย, ฝ่ายการตลาด, ฝ่ายกิจกรรมพิเศษ
- **ช่องทาง**: Email (หลัก), Line (ยืนยันผ่าน Email)
- **รูปแบบ**: Text-Based Information — ระบุรูปแบบสินค้า, ขนาด, ปริมาณ
- **ความสามารถ**: คำนวณพื้นที่ (ตร.ม.), ราคาและ Supplier แบบเฉพาะเจาะจง
- **Access Control**: Role-Based (RBAC)

ดูรายละเอียดเต็มได้ที่ `docs/requirement-confirmation.md`

---

## 📊 โครงสร้างไฟล์ Excel (7 Sheets)

### Sheet 1: `1.POSM(MKT)` — POSM Materials
| รายละเอียด | ค่า |
|---|---|
| จำนวนรายการ | ~25 items |
| Columns | `Item`, `รายการ`, `History 2023`, `History 2024`, `History 2025`, `QTY`, `Vendor 1-14`, `ราคาที่ผ่านการประมูล`, `รายชื่อผู้ผ่านการประมูล` |
| Total | 17,374,700 บาท |

**ตัวอย่าง Item:** ถังใส่น้ำแข็ง-โค้ก, กล่องทิชชู-โค้ก, ผ้ากันเปื้อน, ร่ม, Rack, RGB, Mega Rack, Station

### Sheet 2: `2.Printing(MKT)` — งานพิมพ์การตลาด
| รายละเอียด | ค่า |
|---|---|
| จำนวนรายการ | ~37 items |
| Columns | `Item`, `รายการ`, `QTY`, `vendor 1-15`, `ราคาที่ผ่านการประมูล`, `รายชื่อผู้ผ่านการประมูล` |
| QTY Tier Structure | แต่ละ item มีหลาย QTY tier (500, 1000, 2000, 3000) → ราคาลดลงตามปริมาณ |

**ตัวอย่าง Item:** โคมไฟ, PP Board, แบนเนอร์, แผ่นริจิ, สติ๊กเกอร์ 37x28 cm., ผ้าปูโต๊ะ, ธงราว

### Sheet 3: `3.Garment` — เสื้อ/สิ่งทอ
| รายละเอียด | ค่า |
|---|---|
| จำนวนรายการ | ~16 items |
| Columns | `Item`, `รายการ`, `QTY Y2026`, `Vendor 1-9`, `ราคาที่ผ่านการประมูล`, `รายชื่อผู้ผ่านการประมูล` |
| QTY Tier | 50-100, 101-500, 501-1000, 1001-1500, 1501-2000, 2001-3000, 3001-5000 |
| **Special Rule** | สีอ่อน +5, สีกลาง +10, สีเข้ม +20 บาท |

**ตัวอย่าง Item:** เสื้อยืด, เสื้อโปโล (TC/Micro), เสื้อแจ็คเก็ต, เสื้อคอกลมพิมพ์ลาย, หมวก, ค่าปัก

### Sheet 4: `4.สรุปPremium` — สรุป Premium EA&HRC
| รายละเอียด | ค่า |
|---|---|
| จำนวนรายการ | ~12 items |
| Columns | `Item`, `รายการ`, `QTY`, `QTY Y2025`, `Price Y2025`, `Supplier 2025`, `QTY Y2026`, `vendor 1-9`, `ราคาที่ผ่านการประมูล`, `รายชื่อผู้ผ่านการประมูล` |
| มีข้อมูล Y2025 เทียบ | สำหรับดู trend ราคา |

**ตัวอย่าง Item:** ผ้าเบอร์วิ่ง, แก้วกระดาษ, ร่ม, Menu Stand, เก้าอี้ผู้กำกับ, Bean Bag, Bar mat, ป้ายเคาน์เตอร์คิวอาร์โค้ด

### Sheet 5: `5.Printing-Rate1-43` — อัตรางานพิมพ์ รายการ 1-43
| รายละเอียด | ค่า |
|---|---|
| จำนวนรายการ | ~43 items |
| Columns | `ลำดับ`, `รายการ`, `QTY Y2026`, `vendor 1-12`, `ราคาที่ผ่านการประมูล`, `รายชื่อผู้ผ่านการประมูล` |
| 2,990 rows | แต่ละ item มีหลาย QTY tier |
| QTY Tier | 1-10, 11-20, 21-50, 51-100, 101-500, 501-1000, 1001-2000 |

**ตัวอย่าง Item:** Arch PP Board ขนาดต่างๆ, Wrap Around, โฟมบอร์ดไดคัท, POP UP, PVC Banner, X-Stand, Roll-up

### Sheet 6: `5.Printing-Rate44-109` — อัตรางานพิมพ์ รายการ 44-109
| รายละเอียด | ค่า |
|---|---|
| จำนวนรายการ | รายการ 44-109 |
| Columns | `ลำดับ`, `รายการ`, `QTY Y2026`, `vendor 1-15`, `ราคาที่ผ่านการประมูล`, `รายชื่อผู้ผ่านการประมูล` |
| Metadata | Vendor ID mapping, Timestamps (audit log จากระบบประมูล) |

**ตัวอย่าง Item:** Shelf Talker, Sticker Cool Zone, Price tag A3, ป้ายไวนิล, Wrap Around Top Shelf, Hand prop, ธงปีกนก S/M/L/XL

### Sheet 7: `GVMetadata`
Metadata สำหรับระบบ GV (base64 encoded)

---

## 📧 รูปแบบ Email Workflow

### บุคคลหลักในระบบ
| ชื่อ | บทบาท | แผนก |
|---|---|---|
| Watinee Jongwilaikasem (น้องสาว/น้องน้อง) | **Procurement Officer** — คนตอบราคา | จัดซื้อ |
| Laddawan Puttakoon (น้องจุ๊บ) | **Procurement Officer** — คนตอบราคา | จัดซื้อ |
| Pattarawat Makrak (น้องเบส/คุณเบสท์) | **Marketing** — คนขอราคา | การตลาด |
| Paritmon Khwantong (พี่ก้อย) | **Marketing** — คนขอราคา | การตลาด |
| Pattana Sangkul | **Planning & Budget** — คนขอราคา | วางแผนและงบประมาณ |
| Densri Kalanuson | มักถูก CC ทุกอีเมล | — |

### รูปแบบการขอราคา (4 Patterns)

#### Pattern A: ขอราคาจาก Item มาตรฐาน
```
Subject: ขอราคาผลิตสติกเกอร์ Minute Maid ขนาด 37x28 cm.
→ ระบุ: รายการ, จำนวน, Deadline
→ ตอบ: ราคาต่อหน่วย × จำนวน
```

#### Pattern B: ขอราคาจาก Spec เฉพาะ
```
Subject: ขอราคา Sales Kit สำหรับงาน MARK Project
→ ระบุ: Spec ละเอียด (ขนาด, กระดาษ, การเข้าเล่ม)
→ ต้อง map spec กับ item ใน Excel
```

#### Pattern C: ขอราคาจากแคมเปญ (หลาย items)
```
Subject: ขอราคาสื่อสำหรับผลิตแคมเปญ Fanta x Bus, FIFA และ Ramadan
→ มีไฟล์แนบ Excel หรือ Google Drive Link
→ ต้อง extract รายการจากไฟล์แนบ
```

#### Pattern D: ขอราคา POSM
```
Subject: ขอราคาป้ายราคา RGB พลาสวูด
→ ตรงกับ Sheet POSM → item "RGB"
```

### ข้อมูลที่ต้อง Extraction จาก Email
1. **รายการสินค้า** (Item name/Description)
2. **จำนวน** (QTY)
3. **Spec** (ขนาด, วัสดุ, จำนวนหน้า, แบบ)
4. **Deadline** (วันที่ต้องการของ)
5. **Google Drive Link** (สำหรับไฟล์ AI/Artwork)
6. **ชื่อแคมเปญ** (เช่น MARK Project, Minute Maid, Fanta x Bus)
7. **ผู้ขอ** (สำหรับตอบกลับ)

---

## 🤖 แนวทาง Implement LLM AI Chat

### Architecture Suggestion

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  User Input  │────▶│  Intent       │────▶│  Entity       │
│  (Email/Text)│     │  Classifier    │     │  Extractor    │
└─────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Response    │◀────│  Price        │◀────│  Sheet/Item   │
│  Generator   │     │  Calculator   │     │  Matcher      │
└─────────────┘     └──────────────┘     └──────────────┘
```

### 5 ขั้นตอนหลัก

1. **Intent Classification** — ระบุว่าเป็นคำขอราคา ใบเสนอราคา หรือสอบถามข้อมูล
2. **Entity Extraction** — ดึงชื่อรายการ จำนวน Spec Deadline จากข้อความ
3. **Sheet/Item Matching** — จับคู่รายการกับ sheet และ item ที่ถูกต้อง
4. **Price Lookup & Tier Matching** — หาราคาต่อหน่วยตาม QTY tier
5. **Response Generation** — สร้างข้อความตอบกลับในรูปแบบ email

### Key Matching Rules

#### QTY Tier Matching
```python
def find_price_tier(tiers, qty):
    for tier in sorted(tiers, key=lambda x: x['min_qty']):
        if tier['min_qty'] <= qty <= tier['max_qty']:
            return tier['unit_price']
    return tiers[-1]['unit_price']  # fallback to highest tier
```

#### Item Matching Priority
1. **Exact match** — ชื่อรายการตรงกัน
2. **Fuzzy match** — ชื่อใกล้เคียง (สติกเกอร์ ≈ สติ๊กเกอร์)
3. **Spec-based match** — ขนาด+วัสดุตรงกัน
4. **Cross-sheet match** — ตรวจสอบทุก sheet

#### Special Business Rules
- ราคาที่แจ้ง **ไม่รวมภาษีมูลค่าเพิ่ม 7%** — ทุกรายการ
- ระยะเวลาผลิต **10-15 วันทำการ** หลังยืนยัน AW
- กรณีเร่งด่วน (5-7 วัน) → พิจารณา supplier ท้องถิ่น
- **Garment**: สีอ่อน +5, สีกลาง +10, สีเข้ม +20 บาท/ตัว
- **หมายเหตุ**: ถ้า vendor ต่ำสุดไม่ตรง spec → เลือก vendor ถัดไป

### Data Preparation for RAG

#### Option 1: Flatten to JSON
แปลงแต่ละ item (รวมทุก QTY tier) เป็น document สำหรับ vector search:
```json
{
  "id": "PRINTING_12",
  "sheet": "2.Printing(MKT)",
  "category": "Printing-MKT",
  "item_name": "สติ๊กเกอร์ 37x28 cm.",
  "description": "สติ๊กเกอร์ 37x28 cm.",
  "qty_tiers": [
    {"min": 300, "max": 300, "price": 19},
    {"min": 501, "max": 500, "price": 18.5},
    {"min": 1001, "max": 1000, "price": 12},
    {"min": 3001, "max": 3000, "price": 10}
  ],
  "approved_price": 10,
  "approved_vendor": "vendor 7"
}
```

#### Option 2: SQLite/Structured DB
สร้างตาราง `items`, `price_tiers`, `vendors` สำหรับ query ที่แน่นอน

### Recommended Tech Stack
| Component | Recommendation |
|---|---|
| Vector Embedding | `bge-m3` หรือ `intfloat/multilingual-e5-large` |
| Vector DB | ChromaDB หรือ Qdrant |
| LLM | GPT-4 / Claude (มี function calling) |
| Function Calling | สำหรับ price calculation, QTY tier lookup |
| Language | Python (FastAPI/Flask) |

### Thai Language Handling
- **Synonym Mapping** ที่จำเป็น:
  - สติกเกอร์ = สติ๊กเกอร์ = Sticker
  - ไวนิล = Vinyl
  - PP Board = พีพีบอร์ด
  - โฟมบอร์ด = Foam Board
  - ไดคัท = Diecut
  - AW = Artwork
  - PR = Purchase Requisition

### Example Prompt Template
```
คุณคือผู้ช่วยตอบราคาสื่อการตลาด (Trade Marketing Procurement AI) ของบริษัท HaadThip

ความสามารถของคุณ:
1. ค้นหาราคาสินค้าจาก Master Price Y2026
2. คำนวณราคาตามจำนวนที่ต้องการ (เลือก QTY tier ที่ถูกต้อง)
3. แจ้งระยะเวลาผลิต (10-15 วันทำการหลังยืนยัน AW)
4. แจ้งหมายเหตุ: ราคาไม่รวม VAT 7%

ข้อมูลที่มี:
- POSM(MKT): สื่อ ณ จุดขาย
- Printing(MKT): งานพิมพ์
- Garment: เสื้อและสิ่งทอ
- สรุปPremium: ของพรีเมี่ยม
- Printing-Rate: อัตรางานพิมพ์

เมื่อได้รับคำถาม:
1. วิเคราะห์ว่ารายการอยู่ในหมวดหมู่ใด
2. ค้นหา Item ที่ตรงกับรายการ
3. ตรวจสอบจำนวน (QTY) → เลือก Tier ที่ถูกต้อง
4. ตอบราคาต่อหน่วยและราคารวม
5. แจ้งระยะเวลาผลิตและหมายเหตุ
```

### Pain Points & Solutions

| Pain Point | Solution |
|---|---|
| ชื่อสินค้าไม่ตรงกัน (สติกเกอร์ ≠ สติ๊กเกอร์) | Synonym mapping + fuzzy matching |
| QTY tier ซับซ้อน แต่ละ item มี tier ต่างกัน | Price tier lookup function |
| หลาย sheet มี item คล้ายกัน | LLM classify sheet ก่อน |
| ข้อมูล vendor กระจายใน columns | Flatten เป็น rows |
| หมายเหตุพิเศษ (สีเสื้อ, VAT, ระยะเวลา) | Rule-based post-processing |
| Deadline มีผลต่อ supplier | ถ้าเร่งด่วน → supplier ท้องถิ่น |
| ไฟล์แนบ/Google Drive มีรายละเอียด | ต้องให้มนุษย์ upload หรือ extract content |

---

## โครงสร้างโฟลเดอร์

```
procurement-ai-chat/
├── README.md                       เอกสารวิเคราะห์หลัก (ไฟล์นี้)
├── docs/                           เอกสารประกอบทั้งหมด
│   ├── requirement-confirmation.md      ✅ ยืนยัน Requirement จากทีม DIO
│   ├── requirement-confirmation-email.pdf
│   ├── sheet-analysis.md                วิเคราะห์แต่ละ Sheet แบบเจาะลึก
│   ├── solution-comparison.md           เทียบแนวทาง RAG vs Tool
│   ├── diagrams.md                      แผนภาพสถาปัตยกรรม
│   ├── owui-agent-guideline.md          🌟 Guideline สร้าง Agent ใน OWUI
│   ├── agent_skill_instruction.md       Skill instruction สำหรับ agent
│   └── procurement_knowledge_for_rag.md
├── data/
│   ├── source/                     ไฟล์ต้นฉบับ (แก้ด้วยมือ/ได้รับมา)
│   │   ├── Trade Marketing Materials price for Y2026.final.xlsx
│   │   ├── master-price-template.xlsx   template คนกรอกง่าย (สร้างจาก build_friendly_template.py)
│   │   ├── email_samples.zip
│   │   ├── email_samples_extracted.txt
│   │   └── emails-pdf/                   ตัวอย่างอีเมล PDF 22 ไฟล์
│   └── generated/                  ผลลัพธ์จากสคริปต์ (สร้างใหม่ได้)
│       ├── json/                        JSON ต่อ sheet + chunks
│       ├── email-samples-md/            อีเมลแปลงเป็น Markdown
│       └── email-samples-structured/    อีเมลแปลงเป็น JSON
├── scripts/                        สคริปต์ Python (path อ้างอิง ROOT อัตโนมัติ)
│   ├── build_friendly_template.py       สร้าง Excel template คนกรอกง่าย
│   ├── load_master.py                   transformation: friendly xlsx → ตาราง normalized
│   ├── convert_excel_to_knowledge.py    แปลง Excel → JSON/MD สำหรับ Knowledge
│   ├── excel_to_json.py                 แปลง Excel → JSON ต่อ sheet
│   ├── excel_to_text_chunks.py          แปลง → text chunks สำหรับ RAG
│   ├── update_tool_data.py              อัปเดต tool + system prompt บน OWUI
│   ├── run_regression.py                รัน regression tests
│   └── regression-tests.csv
├── tools/                          OWUI tool files
│   ├── tool-procurement-price-lookup.py
│   └── tool-procurement-excel-live.py
└── owui/                           OWUI API + snapshots
    ├── owui-api.postman_collection.json
    └── snapshots/
```

> สคริปต์ทุกตัวใช้ `ROOT = Path(__file__).resolve().parents[1]` อ้าง path จึงรันจากที่ไหนก็ได้
> เช่น `python scripts/load_master.py` หรือ `python scripts/build_friendly_template.py`
