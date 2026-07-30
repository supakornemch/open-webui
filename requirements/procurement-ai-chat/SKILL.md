---
name: procurement-ai-chat
description: Work on the HaadThip Procurement AI price-lookup agent — its Open WebUI tool, the Y2026 price book workbook, and the agent instruction. Use when adding or fixing tool functions, regenerating the price book from the raw auction file, debugging wrong or missing prices, changing pricing rules, or updating the agent prompt.
---

# Procurement AI Chat

Agent ตอบราคาสื่อการตลาด (Trade Marketing Materials) Y2026 ของ HaadThip ใน Open WebUI
ทำงานบน 3 ชิ้นที่ต้องสอดคล้องกัน: **workbook → tool → instruction**

## สถาปัตยกรรม

```
Trade Marketing Materials price for Y2026.final.xlsx   ← ไฟล์ประมูลดิบ (แก้ไม่ได้)
        │  scripts/build_price_book.py
        ▼
price-book-Y2026.xlsx        ← flat 1 row = 1 item x 1 tier + rag_text
        │  upload เข้า OWUI Files
        ▼
tool-procurement-price-lookup-v4.py   ← หาไฟล์จากชื่อ → id → bytes → pandas
        ▼
AGENT_PROMPT.md              ← system prompt ที่ agent ใช้
```

ไฟล์:
- [scripts/build_price_book.py](scripts/build_price_book.py) — transform
- [data/source/price-book-Y2026.xlsx](data/source/price-book-Y2026.xlsx) — 188 items / 516 rows / 6 sheets
- [tools/tool-procurement-price-lookup-v4.py](tools/tool-procurement-price-lookup-v4.py) — tool ที่ใช้จริง
- [AGENT_PROMPT.md](AGENT_PROMPT.md) — instruction
- [docs/agent_skill_instruction.md](docs/agent_skill_instruction.md) — คู่มือเชิงลึกฉบับเดิม (ตัวเลขบางส่วนล้าสมัย)

## Workbook layout

sheet `price_book` เป็น fact table ห้ามมี merged cell หรือหัวตารางซ้อน:

| กลุ่ม | คอลัมน์ |
|---|---|
| identity | `item_id`, `category`, `category_th`, `item_no`, `item_name`, `spec` |
| filter | `qty_min`, `qty_max`, `size_w_cm`, `size_h_cm` |
| คำตอบ | `unit_price_thb`, `winner_vendor` |
| บริบท | `vendor_count`, `price_min/max/avg_thb`, `price_2025_thb`, `vendor_quotes_json`, `notes` |
| embedding | `rag_text` |

sheet อื่น: `items` (ทะเบียนไม่ซ้ำ), `vendors`, `price_rules`, `glossary`, `อ่านก่อน`

`qty_max` ว่าง = ไม่จำกัดเพดาน · `unit_price_thb` ว่าง = ไม่มีราคาตายตัว ให้อ่าน `notes`

## กฎที่พลาดบ่อย

**อย่า hardcode ค่าที่อยู่ใน workbook**
ค่าสี (+5/+10/+20) อยู่ sheet `price_rules` · คำพ้องอยู่ sheet `glossary`
tool อ่านสองอันนี้ตอน runtime — ถ้าเอาไปเขียนในโค้ดจะหลุด sync กับที่ทีมจัดซื้อแก้

**อย่าอ้างตำแหน่งคอลัมน์เป็นเลข**
เวอร์ชันเก่าใช้ `row.iloc[24]` แล้วพังเงียบ ๆ เมื่อคอลัมน์เลื่อน ให้อ้างชื่อคอลัมน์เสมอ

**ไฟล์ประมูลดิบมี trap 2 อย่าง** ถ้าต้องแก้ `build_price_book.py`
- spec ของสินค้าไหลไปอยู่ในคอลัมน์ชื่อของแถว tier — แยกด้วยกฎ "ถ้า tier ยังไล่ขึ้น = spec ต่อเนื่อง, ถ้า tier รีเซ็ต/ว่าง = variant ใหม่"
- แถวหัวรายการที่ไม่มีราคาแต่มี tier ตามด้านล่าง = placeholder ต้องตัดออก (`drop_placeholders`)

**การอัปเดตราคา** — upload xlsx ใหม่ที่ชื่อ match `file_pattern` (default `price-book*.xlsx`)
tool เลือกไฟล์ที่ upload ใหม่สุด cache ผูกกับ file id + created_at ไม่ต้อง restart

## คำสั่งที่ใช้บ่อย

```bash
# regenerate workbook + jsonl จากไฟล์ประมูล
python3 scripts/build_price_book.py

# ตรวจว่า transform ยังครบ (POSM 25 / Printing 13 / Garment 16 / Premium 15 / PrintRate 119)
python3 -c "
import pandas as pd
df=pd.read_excel('data/source/price-book-Y2026.xlsx',sheet_name='price_book')
print(df.groupby('category').agg(rows=('item_id','size'), items=('item_id','nunique')))
print('no price:', df.unit_price_thb.isna().sum())"

# ทดสอบ tool ใน container
docker cp tools/tool-procurement-price-lookup-v4.py open-webui-local:/tmp/t.py
docker exec open-webui-local python -c "
import asyncio,sys; sys.path.insert(0,'/tmp')
from t import Tools
print(asyncio.run(Tools().health_check()))"
```

## ข้อควรระวังของข้อมูล

- **9 รายการไม่มีราคา** — `Garment-9`..`Garment-16` (สกรีน/ปัก) ใช้ราคาซัพฯที่ชนะประมูลเสื้อ, `PrintRate-58.1` (ฐานน้ำ) อ้างตามธงที่ได้ซัพฯ อย่าเดาราคาแทน
- **vendor ส่วนใหญ่เป็น label** `Vendor 9` / `vendor 12` ไม่ใช่ชื่อบริษัท ชื่อจริงมีเฉพาะบางแถว
- **ราคาไม่รวม VAT 7%** ทุกรายการ ต้องแจ้งทุกครั้ง
- **lead time 5-17 วัน** มาจากการวิเคราะห์อีเมลลูกค้า **ไม่ได้มาจากไฟล์ประมูล** — ยังไม่ยืนยันกับทีมจัดซื้อ
- `PrintRate` มี vendor ครบ 364/367 แถว (เอกสารเก่าเขียนว่าไม่มี — ไม่จริงแล้ว)

## Deploy

Tool ต้อง paste เข้า Admin → Functions ด้วยมือ — browser automation กับ SPA ตัวนี้ timeout เสมอ
ขั้นตอนละเอียดอยู่ใน [SETUP_VISUAL_GUIDE.md](SETUP_VISUAL_GUIDE.md)
