"""
Convert Excel/JSON data → natural-language text chunks optimized for vector search (RAG).

Each chunk is a self-contained paragraph describing ONE product.
Format: Thai natural language, ~200-400 chars, with keywords and specs.

Usage:
    python excel_to_text_chunks.py

Output:
    knowledge/procurement-chunks.txt     ← upload to OWUI Knowledge Base
    json/procurement-chunks.json         ← structured version
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "data" / "generated" / "json"
OUT_DIR = ROOT / ".." / ".." / "knowledge" / "procurement"

SHEETS = [
    ("1.POSM(MKT).json", "POSM", "อุปกรณ์สื่อการตลาด ณ จุดขาย"),
    ("2.Printing(MKT).json", "งานพิมพ์การตลาด", "งานพิมพ์ขนาดใหญ่"),
    ("3.Garment.json", "เสื้อและสิ่งทอ", "เสื้อผ้าเครื่องแต่งกาย"),
    ("4.สรุปPremium.json", "Premium", "สินค้าพรีเมียม"),
    ("5.Printing-Rate.json", "งานพิมพ์อัตราค่าบริการ", "อัตราค่าบริการพิมพ์"),
]


def chunk_posm(item, idx):
    """POSM → natural language chunk."""
    name = item["item_name"]
    qty = item.get("qty_y2026", 0)
    price = item.get("approved_price_per_unit", 0)
    vendor = item.get("approved_vendor", "")
    lead = item.get("lead_time", "10-15 วันทำการ")
    note = item.get("note", "ราคาไม่รวม VAT 7%")

    lines = [
        f"#{idx} | {name}",
        f"หมวดหมู่: POSM (อุปกรณ์สื่อการตลาด ณ จุดขาย)",
        f"รหัส: {item['id']}",
    ]
    if qty:
        lines.append(f"จำนวนสั่งผลิตปี 2026: {qty:,} ชิ้น")
    if price:
        lines.append(f"ราคาประมูลต่อหน่วย: {price:,.2f} บาท")
    if vendor:
        lines.append(f"ผู้ชนะการประมูล: {vendor}")
    lines.append(f"ระยะเวลาผลิต: {lead}")
    lines.append(f"หมายเหตุ: {note}")

    # Keywords for search
    keywords = extract_keywords(name)
    lines.append(f"คำค้น: {', '.join(keywords)}")
    lines.append(f"คำอธิบาย: {name} เป็นอุปกรณ์ POSM สำหรับใช้ในร้านค้าและจุดขาย สั่งผลิตปี 2026 จำนวน {qty:,} ชิ้น ราคาประมูล {price:,.2f} บาทต่อหน่วย โดย {vendor}")

    return "\n".join(lines)


def chunk_printing(item, idx):
    """Printing(MKT) → natural language chunk."""
    name = item["item_name"]
    price = item.get("approved_price_per_unit", 0)
    vendor = item.get("approved_vendor", "")
    tiers = item.get("price_tiers", [])
    lead = item.get("lead_time", "10-15 วันทำการ")

    lines = [
        f"#{idx} | {name}",
        f"หมวดหมู่: งานพิมพ์การตลาด (Marketing Printing)",
        f"รหัส: {item['id']}",
    ]
    if tiers:
        lines.append("ราคาตามจำนวน:")
        for t in tiers[:5]:
            q = t.get("qty", "?")
            p = t.get("unit_price", 0)
            lines.append(f"  - จำนวน {q}: ราคา {p:,.2f} บาท/หน่วย")
    if price:
        lines.append(f"ราคาต่ำสุด: {price:,.2f} บาท/หน่วย")
    if vendor:
        lines.append(f"ผู้ชนะการประมูล: {vendor}")
    lines.append(f"ระยะเวลาผลิต: {lead}")
    lines.append(f"หมายเหตุ: ราคาไม่รวม VAT 7%")

    keywords = extract_keywords(name)
    lines.append(f"คำค้น: {', '.join(keywords)}")

    return "\n".join(lines)


def chunk_garment(item, idx):
    """Garment → natural language chunk."""
    name = item["item_name"]
    price = item.get("approved_price_per_unit", 0)
    vendor = item.get("approved_vendor", "")
    tiers = item.get("price_tiers", [])
    lead = item.get("lead_time", "15 วันทำการ")
    note = item.get("note", "")

    lines = [
        f"#{idx} | {name}",
        f"หมวดหมู่: เสื้อและสิ่งทอ (Garment)",
        f"รหัส: {item['id']}",
    ]
    if tiers:
        lines.append("ราคาตามจำนวน:")
        for t in tiers[:5]:
            r = t.get("qty_range", "?")
            p = t.get("unit_price", 0)
            lines.append(f"  - จำนวน {r} ตัว: ราคา {p:,.2f} บาท/ตัว")
    if price:
        lines.append(f"ราคาต่ำสุด: {price:,.2f} บาท/ตัว")
    if vendor:
        lines.append(f"ผู้ชนะการประมูล: {vendor}")
    lines.append(f"ระยะเวลาผลิต: {lead}")
    if note:
        lines.append(f"หมายเหตุ: {note}")
    lines.append("ค่าสีเพิ่ม: สีอ่อน +5 บาท, สีกลาง +10 บาท, สีเข้ม +20 บาท/ตัว")

    keywords = extract_keywords(name)
    lines.append(f"คำค้น: {', '.join(keywords)}")

    return "\n".join(lines)


def chunk_premium(item, idx):
    """Premium → natural language chunk."""
    name = item["item_name"]
    price = item.get("approved_price_per_unit", 0)
    vendor = item.get("approved_vendor", "")
    y2025 = item.get("y2025", {})
    lead = item.get("lead_time", "15-20 วันทำการ")

    lines = [
        f"#{idx} | {name}",
        f"หมวดหมู่: Premium (สินค้าพรีเมียม EA&HRC)",
        f"รหัส: {item['id']}",
    ]
    if y2025.get("price_per_unit", 0) > 0:
        lines.append(f"ราคาปี 2025: {y2025['price_per_unit']:,.2f} บาท (ซัพพลายเออร์: {y2025.get('supplier', 'N/A')})")
    if price:
        lines.append(f"ราคาประมูลปี 2026: {price:,.2f} บาท/หน่วย")
    if vendor:
        lines.append(f"ผู้ชนะการประมูล: {vendor}")
    lines.append(f"ระยะเวลาผลิต: {lead}")
    lines.append(f"หมายเหตุ: ราคาไม่รวม VAT 7%")

    keywords = extract_keywords(name)
    lines.append(f"คำค้น: {', '.join(keywords)}")

    return "\n".join(lines)


def chunk_printing_rate(item, idx):
    """Printing-Rate → natural language chunk."""
    name = item["item_name"]
    price = item.get("approved_price_per_unit", 0)
    tiers = item.get("price_tiers", [])

    lines = [
        f"#{idx} | {name}",
        f"หมวดหมู่: อัตราค่าบริการพิมพ์ (Printing Rate)",
        f"รหัส: {item['id']}",
        f"ประเภท: {classify_printing_item(name)}",
    ]
    if tiers:
        lines.append("ราคาตามจำนวน:")
        for t in tiers[:4]:
            q = t.get("qty", "?")
            p = t.get("unit_price", 0)
            lines.append(f"  - จำนวน {q}: ราคา {p:,.2f} บาท/หน่วย")
    elif price:
        lines.append(f"ราคา: {price:,.2f} บาท/หน่วย")
    lines.append(f"หมายเหตุ: ราคาไม่รวม VAT 7%")

    keywords = extract_keywords(name)
    lines.append(f"คำค้น: {', '.join(keywords)}")

    return "\n".join(lines)


def classify_printing_item(name):
    """Classify Printing-Rate item into sub-category for better search."""
    n = name.lower()
    if "arch" in n: return "ป้าย Arch (โค้ง)"
    if "wrap around" in n: return "ป้าย Wrap Around (ล้อมกอง)"
    if "ธงปีกนก" in n or "beach flag" in n: return "ธงปีกนก (Beach Flag)"
    if "pp board" in n: return "ป้าย PP Board"
    if "สติ๊กเกอร์" in n or "sticker" in n: return "สติ๊กเกอร์"
    if "coupon" in n: return "Coupon"
    if "หนังสือ" in n or "คู่มือ" in n: return "หนังสือ/คู่มือ"
    if "เคลือบ" in n: return "บริการเคลือบ"
    if "โปสเตอร์" in n: return "โปสเตอร์"
    if "standee" in n: return "Standee"
    if "tent card" in n: return "Tent Card"
    if "ฐานน้ำ" in n or "ฐานกากบาท" in n: return "ฐาน/อุปกรณ์เสริม"
    if "ใบประกาศ" in n or "certificate" in n: return "ประกาศนียบัตร"
    if "hand prop" in n: return "Hand Prop"
    if "shelf" in n: return "Shelf Talker/Strip"
    if "สายรัด" in n or "bib" in n: return "สายรัดข้อมือ"
    return "งานพิมพ์ทั่วไป"


def extract_keywords(name):
    """Extract search keywords from item name."""
    kw = set()
    n = name.lower()

    # Dimensions
    import re
    dims = re.findall(r'(\d+\s*[x×]\s*\d+)', n)
    for d in dims:
        kw.add(d.replace(" ", ""))
    dims2 = re.findall(r'(\d+)\s*(cm|mm|นิ้ว|ml|ลิตร|l|oz|ออนซ์|แกรม|g)', n)
    for num, unit in dims2:
        kw.add(f"{num}{unit}")

    # Sizes
    for size in ['s', 'm', 'l', 'xl', 'xxl', 'ไซด์ s', 'ไซด์ m', 'ไซด์ l', 'ไซด์ xl']:
        if size in n:
            kw.add(size.upper())

    # Materials
    for mat in ['pp board', 'pvc', ' acrylic', 'ไฟเบอร์', 'fiber', 'ผ้า', 'cotton', ' polyester',
                'อาร์ตการ์ด', 'อาร์ตมัน', 'ปอนด์', 'สติ๊กเกอร์', 'sticker']:
        if mat in n:
            kw.add(mat.strip())

    # Common synonyms
    synonyms = {
        'โค้ก': ['coke', 'coca-cola', 'โคคา-โคล่า', 'โคคา'],
        'พิมพ์': ['print', 'ปริ้น', 'พิมพ์'],
        'เคลือบ': ['laminate', 'coating'],
    }
    for key, syns in synonyms.items():
        if key in n:
            kw.update(syns[:2])

    return sorted(kw)[:10]


# ── Main ────────────────────────────────────────────────────────────
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks = []
    chunk_id = 0

    for filename, cat_en, cat_th in SHEETS:
        path = JSON_DIR / filename
        if not path.exists():
            print(f"  ⚠ Missing: {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        print(f"\n📄 {cat_en} ({cat_th}) — {len(items)} items")

        for item in items:
            chunk_id += 1

            if cat_en == "POSM":
                chunk = chunk_posm(item, chunk_id)
            elif cat_en == "งานพิมพ์การตลาด":
                chunk = chunk_printing(item, chunk_id)
            elif cat_en == "เสื้อและสิ่งทอ":
                chunk = chunk_garment(item, chunk_id)
            elif cat_en == "Premium":
                chunk = chunk_premium(item, chunk_id)
            elif cat_en == "งานพิมพ์อัตราค่าบริการ":
                chunk = chunk_printing_rate(item, chunk_id)
            else:
                continue

            all_chunks.append({
                "id": chunk_id,
                "category": cat_th,
                "item_name": item.get("item_name", ""),
                "content": chunk,
            })

    # Write text file (upload to Knowledge Base)
    txt_path = OUT_DIR / "procurement-chunks.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(c["content"])
            f.write("\n\n---\n\n")

    # Write structured JSON
    json_path = JSON_DIR / "procurement-chunks.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {chunk_id} chunks generated")
    print(f"   Text: {txt_path} ({txt_path.stat().st_size:,} bytes)")
    print(f"   JSON: {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"\n   Upload {txt_path.name} to OWUI Knowledge Base for RAG search")


if __name__ == "__main__":
    main()
