# Procurement Price Chat

Procurement catalog (Trade Marketing Materials) — ตั้งแต่ Excel workbook ต้นทาง ถึง Azure AI Search + Open WebUI agent.

## โครงสร้าง

```
precurement-price-chat/
├── data/
│   ├── source/       # ไฟล์ต้นทาง (Excel workbook จาก Excel Master)
│   ├── exports/      # JSON กลางที่ convert จาก workbook (1 object/แถวราคา)
│   ├── masters/      # Excel Master (ไฟล์ที่ใช้กรอก + ingest) — 9 คอลัมน์ ไม่มี vendor
│   └── enrichment/   # cache LLM enrichment (key ด้วย source hash)
├── scripts/          # pipeline ทั้งหมด
├── docs/             # design, handoff, system prompt, skill, สไลด์
├── emails-pdf/       # อีเมลขอราคา/ตัวอย่างสื่อ (เอกสารอ้างอิง)
└── README.md
```

## คอลัมน์ Excel Master (9 คอลัมน์ — ไม่มี vendor)

`ปี | ลำดับ | รายการ | จำนวนขั้นต่ำ | จำนวนสูงสุด | การคิดราคา | ราคาที่ผ่านการประมูล | รายชื่อผู้ผ่านการประมูล | หมายเหตุ`

- ระดับสินค้า (แถวแรก): ปี/ลำดับ/รายการ/การคิดราคา/รายชื่อผู้ผ่านการประมูล/หมายเหตุ
- ระดับเรท (ทุกแถว): จำนวนขั้นต่ำ/สูงสุด + ราคาที่ผ่านการประมูล
- ผู้ชนะระบุผ่าน `รายชื่อผู้ผ่านการประมูล` (V5 / ชื่อ) — ไม่มีคอลัมน์ vendor-*

## Pipeline

```bash
# 1) workbook → items JSON (ใช้เปิดดู/ตรวจความถูกต้อง)
python3 scripts/convert_workbook_to_items_json.py

# 2) workbook → Excel Master (มีข้อมูล 518 rows / 5 sheets)
python3 scripts/convert_workbook_to_catalog_master.py

# 3) template เปล่า (สำหรับ Excel Master กรอกใหม่)
python3 scripts/create_catalog_master_empty.py

# 4) ingest ขึ้น Azure AI Search (ต้อง VPN + env)
set -a; source ../../docker/.env.owui; set +a
python3 scripts/ingest_catalog_master.py --dry-run            # ตรวจก่อน
python3 scripts/ingest_catalog_master.py --create-index --enrich --ingest --verify

# 5) regression test (E2E: hybrid search + filter + facts)
set -a; source ../../docker/.env.owui; set +a
E2E_EMBEDDING_KEY=<litellm key> python3 scripts/test_procurement_e2e.py
```

## Azure AI Search — schema (product-level, ไม่มี vendor fields)

1 doc = 1 logical product (`{ปี}:{หมวด}:{ลำดับ}`):

```jsonc
{
  "id", "logical_item_id", "year", "category",
  "product_name", "product_aliases", "product_type",
  "keywords", "keywords_text", "product_spec_text", "product_condition_text",
  "pricing_basis", "search_text", "notes_text",
  "award_vendors": ["Collection(Edm.String)"],   // จาก รายชื่อผู้ผ่านการประมูล
  "price_min", "price_max", "quantity_min_all", "quantity_max_all",
  "tiers[]": { "quantity_label", "quantity_min", "quantity_max",
               "quantity_is_exact", "awarded_price", "source_row" },
  "content_vector"   // 3072-dim
}
```

## Open WebUI Agent

- **Tool**: `procurement_price_search` (hybrid search, 5 items/รอบ, 3 รอบ/คำถาม, ไม่เดา category)
- **Knowledge (skill)**: `procurement-catalog-skill` — โครงสร้าง index + กติกาอ่านผล
- **Model**: `procurement-price-assistant` — base `genie.gpt-5.4-mini`
- ไฟล์อ้างอิง: `docs/procurement-assistant-system-prompt.md`, `docs/procurement-catalog-skill.md`
