# Procurement Catalog — Knowledge Reference (attach as OWUI Knowledge collection)

## Index
- Azure AI Search index: `procurement-catalog-v1` (one document per logical product)
- 179 products, 518 quantity-tier rows, from Excel Master Y2026
- Hybrid + semantic retrieval via tool `procurement_price_search` (hybrid = BM25 keyword + vector fused by Azure RRF; semantic rerank is optional on top)

## Document structure (fields the tool returns)
- `logical_item_id` = {ปี}:{Category}:{ลำดับ} เช่น `2026:Printing-Rate:1`
- `product_name`, `product_type`, `category` — ข้อมูลสินค้า
- `pricing_basis` — หน่วยคิดราคา เช่น "ต่อตรม.", "ต่อชิ้น" (ถ้ามี)
- `price_min` / `price_max` — ช่วงราคา awarded ข้ามทุก tier (อ่านตรงๆ ห้ามคำนวณ)
- `quantity_min_all` / `quantity_max_all` — ช่วงจำนวนที่รับได้ทั้งสินค้า
- `tiers[]` — แต่ละเรทราคา:
  - `quantity_label`, `quantity_min`, `quantity_max` — ช่วงจำนวนของเรทนี้
  - `awarded_price` — ราคาที่ผ่านการประมูลของเรทนี้ (authoritative จาก workbook)
- `award_vendors` — รายชื่อผู้ผ่านการประมูล (ระดับสินค้า)
- `product_spec_text`, `product_condition_text` — สเปค / เงื่อนไขของสินค้า
- `notes_text` — หมายเหตุ (เช่น "ราคาต่ำสุดแต่ไม่ตรงสเปค")

## How to read results
1. ผู้ใช้ถามราคา → tool `search_procurement_prices(query=...)`
2. แม้ผู้ใช้ระบุจำนวน (เช่น "500 ชิ้น") ให้ค้นหาสินค้าโดยไม่ส่ง `quantity` ก่อน; เมื่อระบุสินค้าได้แล้ว จึงส่ง `quantity=500` ให้ tool จับคู่ tier แบบ deterministic
3. อ่านราคาจาก `tiers[].awarded_price` (เรทที่ตรง) หรือ `price_min/max`
4. หากถามผู้ผ่านการประมูล → ดู `award_vendors` ระดับสินค้า (catalog นี้ไม่มี quote ราย vendor)
5. ถ้าหลายสินค้าคล้ายกัน → เทียบ `product_spec_text` / `product_condition_text` แล้วถามกลับ

## Quantity tier matching rule
- exact: `quantity_min == quantity_max` (เช่น 5000/5000 = ราคาต่อชิ้นที่ 5000 พอดี)
- range: `quantity_min..quantity_max` (เช่น 1..10)
- open-ended: `quantity_max` null หรือ "-" (เช่น 11+ = 11 ขึ้นไป)
- tool filter: `tiers/any(t: t/quantity_min le N and (t/quantity_max ge N or t/quantity_max eq null))`

## Search limits (บังคับ)
- **ไม่เกิน 5 items / รอบ** — tool ตัดผลที่ `max_results` (สูงสุด 5) ให้เสมอ
- **ไม่เกิน 3 รอบการค้นหา** ต่อ 1 คำถาม — ถ้าครบ 3 รอบแล้วยังไม่พบ ให้บอกผู้ใช้ว่าไม่พบและหยุด (อย่าค้นซ้ำ)
- แต่ละรอบคือการเรียก tool 1 ครั้ง (เช่น exact → wildcard) — ห้ามเรียก tool ซ้ำเกิน 3 ครั้ง

## Category rule (สำคัญ)
- **ห้ามเดา `category`** — ส่ง `category` เฉพาะเมื่อผู้ใช้ระบุหมวดชัดเจน (เช่น "หมวดเสื้อ", "งานพิมพ์", "POSM") เท่านั้น
- ถ้าไม่แน่ใจว่าสินค้าอยู่หมวดไหน → **ปล่อย category ว่าง** ให้ค้นทั้ง index
- ตัวอย่างที่เคยผิด: "PP Board 85x190" อยู่ใน Printing-MKT (ไม่ใช่ POSM) — ถ้า LLM เดา category=POSM จะ filter ทิ้งแล้วไม่เจอทั้งที่ index มีข้อมูล

## Data contract (ห้ามละเมิด)
- Workbook (Excel Master) คือ source of truth สำหรับ ราคา, จำนวน, vendor, award
- **ห้ามสร้าง/คำนวณราคา** — ใช้ `awarded_price` / `price_min/max` จาก index ตรงๆ
- award ≠ ราคาต่ำสุดได้ (มี `notes_text` "ราคาต่ำสุดแต่ไม่ตรงสเปค") — ตอบตามจริง
- จำนวนไม่ตรง tier → บอกเรทที่มีอยู่ ถามผู้ใช้ อย่าประมาณราคา
