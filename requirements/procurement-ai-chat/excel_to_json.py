"""
Convert Trade Marketing Materials price for Y2026.final.xlsx → JSON (one per sheet)

Usage:
    python excel_to_json.py

Output:
    json/1.POSM(MKT).json
    json/2.Printing(MKT).json
    json/3.Garment.json
    json/4.สรุปPremium.json
    json/5.Printing-Rate.json          ← merged from Rate1-43 + Rate44-109
    knowledge/procurement-context.md   ← context summary for Procurement AI
"""

import json
import math
import os
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
XLSX_PATH = BASE_DIR / "Trade Marketing Materials price for Y2026.final.xlsx"
JSON_DIR = BASE_DIR / "json"
KNOWLEDGE_DIR = BASE_DIR / ".." / ".." / "knowledge" / "procurement"


def safe_float(val):
    """Convert to float or 0 if NaN."""
    if pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def clean_str(val):
    """Convert to stripped string or empty."""
    if pd.isna(val):
        return ""
    return str(val).strip()


# ── Sheet 1: POSM(MKT) ──────────────────────────────────────────────
def parse_posm(df):
    items = []
    for idx in range(2, len(df)):
        row = df.iloc[idx]
        item_id = clean_str(row.iloc[1])
        item_name = clean_str(row.iloc[2])

        if not item_id or not item_name:
            continue

        qty = int(safe_float(row.iloc[9]))
        approved_price = safe_float(row.iloc[24])
        approved_vendor = clean_str(row.iloc[26])
        total_price = safe_float(row.iloc[25])

        # Collect vendor prices from cols 10-23
        vendors = {}
        for v in range(10, 24):
            vprice = safe_float(row.iloc[v])
            if vprice > 0:
                vendors[f"vendor_{v - 9}"] = vprice

        items.append({
            "id": f"POSM_{item_id}",
            "category": "POSM",
            "item_name": item_name,
            "qty_y2026": qty,
            "approved_price_per_unit": approved_price,
            "approved_vendor": approved_vendor,
            "total_price": total_price,
            "vendor_prices": vendors,
            "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
            "lead_time": "10-15 วันทำการหลังยืนยัน AW",
        })
    return items


# ── Sheet 2: Printing(MKT) ──────────────────────────────────────────
def parse_printing_mkt(df):
    items = []
    current = None

    for idx in range(2, len(df)):
        row = df.iloc[idx]
        if clean_str(row.iloc[0]) != "Printing-mkt":
            continue

        item_id = clean_str(row.iloc[1])
        item_name = clean_str(row.iloc[2])
        qty = clean_str(row.iloc[3])

        if item_id and item_name:
            if current:
                items.append(current)

            current = {
                "id": f"PRINT_MKT_{item_id}",
                "category": "งานพิมพ์การตลาด",
                "item_name": item_name,
                "price_tiers": [],
                "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
                "lead_time": "10-15 วันทำการหลังยืนยัน AW",
            }

            if qty:
                vendors = {}
                for v in range(4, 19):
                    vp = safe_float(row.iloc[v])
                    if vp > 0:
                        vendors[f"vendor_{v - 3}"] = vp
                approved_price = safe_float(row.iloc[19])
                approved_vendor = clean_str(row.iloc[20])
                current["approved_price_per_unit"] = approved_price
                current["approved_vendor"] = approved_vendor
                current["price_tiers"].append({
                    "qty": qty,
                    "unit_price": approved_price if approved_price > 0 else 0,
                    "vendor_prices": vendors,
                })

        elif current and qty:
            vendors = {}
            for v in range(4, 19):
                vp = safe_float(row.iloc[v])
                if vp > 0:
                    vendors[f"vendor_{v - 3}"] = vp
            approved_price = safe_float(row.iloc[19])
            approved_vendor = clean_str(row.iloc[20])
            current["approved_price_per_unit"] = approved_price
            current["approved_vendor"] = approved_vendor
            current["price_tiers"].append({
                "qty": qty,
                "unit_price": approved_price if approved_price > 0 else 0,
                "vendor_prices": vendors,
            })

    if current:
        items.append(current)
    return items


# ── Sheet 3: Garment ────────────────────────────────────────────────
def parse_garment(df):
    items = []
    current = None

    for idx in range(2, len(df)):
        row = df.iloc[idx]
        if clean_str(row.iloc[0]) != "Garment":
            continue

        item_id = clean_str(row.iloc[1])
        item_name = clean_str(row.iloc[2])
        qty_range = clean_str(row.iloc[3])

        if item_id and item_name:
            if current:
                items.append(current)
            current = {
                "id": f"GARMENT_{item_id}",
                "category": "เสื้อและสิ่งทอ",
                "item_name": item_name,
                "price_tiers": [],
                "note": "สีอ่อน +5, สีกลาง +10, สีเข้ม +20 บาท",
                "lead_time": "15 วันทำการหลังยืนยัน AW",
            }

        if current and qty_range:
            vendors = {}
            for v in range(4, 13):
                vp = safe_float(row.iloc[v])
                if vp > 0:
                    vendors[f"vendor_{v - 3}"] = vp
            approved_price = safe_float(row.iloc[13])
            approved_vendor = clean_str(row.iloc[14])
            current["approved_price_per_unit"] = approved_price
            current["approved_vendor"] = approved_vendor
            current["price_tiers"].append({
                "qty_range": qty_range,
                "unit_price": approved_price if approved_price > 0 else 0,
                "vendor_prices": vendors,
            })

    if current:
        items.append(current)
    return items


# ── Sheet 4: สรุปPremium ────────────────────────────────────────────
def parse_premium(df):
    items = []
    current = None

    for idx in range(2, len(df)):
        row = df.iloc[idx]
        if clean_str(row.iloc[0]) != "Premium-EA&HRC":
            continue

        item_id = clean_str(row.iloc[1])
        item_name = clean_str(row.iloc[2])
        qty = clean_str(row.iloc[7])

        if item_id and item_name:
            if current:
                items.append(current)

            qty_y2025 = int(safe_float(row.iloc[4]))
            price_y2025 = safe_float(row.iloc[5])
            supplier_y2025 = clean_str(row.iloc[6])

            current = {
                "id": f"PREMIUM_{item_id}",
                "category": "Premium-EA&HRC",
                "item_name": item_name,
                "y2025": {
                    "qty": qty_y2025,
                    "price_per_unit": price_y2025,
                    "supplier": supplier_y2025,
                },
                "price_tiers": [],
                "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
                "lead_time": "15-20 วันทำการหลังยืนยัน AW",
            }

        if current and qty:
            vendors = {}
            for v in range(8, 17):
                vp = safe_float(row.iloc[v])
                if vp > 0:
                    vendors[f"vendor_{v - 7}"] = vp
            approved_price = safe_float(row.iloc[17])
            total_price = safe_float(row.iloc[18])
            approved_vendor = clean_str(row.iloc[19])
            current["approved_price_per_unit"] = approved_price
            current["approved_vendor"] = approved_vendor
            current["price_tiers"].append({
                "qty": qty,
                "unit_price": approved_price if approved_price > 0 else 0,
                "total_price": total_price,
                "vendor_prices": vendors,
            })

    if current:
        items.append(current)
    return items


# ── Sheet 5: Printing-Rate (merged 1-43 + 44-109) ───────────────────
def parse_printing_rate(df, start_item=1):
    """Parse a printing-rate sheet.  Rate44-109 has a 3-row header offset."""
    items = []
    current = None

    # Detect header row AND column offset
    # Some sheets have a leading NaN column (e.g., Rate1-43: col0=nan, col1=ลำดับ)
    # Others start at col0 (e.g., Rate44-109: col0=ลำดับ)
    header_idx = 0
    col_offset = 0
    for r in range(min(5, len(df))):
        row_vals = [clean_str(c) for c in df.iloc[r].tolist()]
        row_str = " ".join(row_vals)
        if "\u0e25\u0e33\u0e14\u0e31\u0e1a" in row_str and "\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23" in row_str:
            header_idx = r
            # Find which column has "ลำดับ"
            for c, val in enumerate(row_vals):
                if "\u0e25\u0e33\u0e14\u0e31\u0e1a" in val:
                    col_offset = c
                    break
            break

    data_start = header_idx + 1
    item_counter = start_item

    # Column indices (adjusted by col_offset)
    COL_ITEM_NO = col_offset       # item number
    COL_ITEM_NAME = col_offset + 1  # description
    COL_QTY = col_offset + 2        # qty
    COL_VENDOR_START = col_offset + 3  # first vendor column

    for idx in range(data_start, len(df)):
        row = df.iloc[idx]
        item_no = clean_str(row.iloc[COL_ITEM_NO])
        item_name = clean_str(row.iloc[COL_ITEM_NAME])
        qty = clean_str(row.iloc[COL_QTY])

        # New item row
        if item_name:
            if current:
                items.append(current)

            # Determine vendor column range by counting non-NaN after qty
            vendors = {}
            num_vendors = 0
            for v in range(3, len(row)):
                vp = safe_float(row.iloc[v])
                if vp > 0:
                    num_vendors += 1

            # Recollect vendors properly
            vendors = {}
            for v in range(COL_VENDOR_START, len(row)):
                vp = safe_float(row.iloc[v])
                if vp > 0:
                    vendors[f"vendor_{v - COL_VENDOR_START + 1}"] = vp

            # Find approved (min) price
            min_price = min(vendors.values()) if vendors else 0

            current = {
                "id": f"PRINT_RATE_{item_counter}",
                "category": "\u0e07\u0e32\u0e19\u0e1e\u0e34\u0e21\u0e1e\u0e4c\u0e2d\u0e31\u0e15\u0e23\u0e32\u0e04\u0e48\u0e32\u0e1a\u0e23\u0e34\u0e01\u0e32\u0e23",
                "item_name": item_name,
                "price_tiers": [],
                "approved_price_per_unit": min_price,
                "note": "\u0e23\u0e32\u0e04\u0e32\u0e44\u0e21\u0e48\u0e23\u0e27\u0e21\u0e20\u0e32\u0e29\u0e35\u0e21\u0e39\u0e25\u0e04\u0e48\u0e32\u0e40\u0e1e\u0e34\u0e48\u0e21 7%",
            }

            if qty:
                current["price_tiers"].append({
                    "qty": qty,
                    "unit_price": min_price,
                    "vendor_prices": vendors,
                })
            item_counter += 1

        elif current and qty:
            vendors = {}
            for v in range(COL_VENDOR_START, len(row)):
                vp = safe_float(row.iloc[v])
                if vp > 0:
                    vendors[f"vendor_{v - COL_VENDOR_START + 1}"] = vp
            min_price = min(vendors.values()) if vendors else 0
            current["approved_price_per_unit"] = min_price
            current["price_tiers"].append({
                "qty": qty,
                "unit_price": min_price,
                "vendor_prices": vendors,
            })

    if current:
        items.append(current)
    return items, item_counter


# ── Context Generator ───────────────────────────────────────────────
def generate_context(sheets_data):
    """Generate a markdown context file for Procurement AI."""
    lines = [
        "# Procurement AI — Context: Trade Marketing Materials Price Y2026",
        "",
        f"อัปเดตล่าสุด: 2026-07-24",
        f"แหล่งข้อมูล: Trade Marketing Materials price for Y2026.final.xlsx",
        "",
    ]

    total_items = 0
    for sheet_name, items in sheets_data.items():
        if not items:
            continue
        total_items += len(items)
        cat = items[0].get("category", sheet_name)
        lines.append(f"## {cat} ({sheet_name})")
        lines.append(f"จำนวนรายการ: {len(items)}")
        lines.append("")

        for item in items:
            lines.append(f"### {item['item_name']}")
            lines.append(f"- รหัส: `{item['id']}`")

            if item.get("approved_price_per_unit", 0) > 0:
                lines.append(f"- ราคาประมูล: **{item['approved_price_per_unit']:.2f} บาท/หน่วย**")
            if item.get("approved_vendor"):
                lines.append(f"- ผู้ชนะประมูล: {item['approved_vendor']}")
            if item.get("qty_y2026"):
                lines.append(f"- จำนวน Y2026: {item['qty_y2026']:,} ชิ้น")

            tiers = item.get("price_tiers", [])
            if tiers:
                lines.append("")
                lines.append("| จำนวน | ราคา/หน่วย | จำนวนผู้เสนอราคา |")
                lines.append("|:------:|:----------:|:------------------:|")
                for t in tiers:
                    qty_label = t.get("qty") or t.get("qty_range", "-")
                    price = t.get("unit_price", 0)
                    n_vendors = len(t.get("vendor_prices", {}))
                    lines.append(f"| {qty_label} | {price:.2f} บาท | {n_vendors} ราย |")

            if item.get("y2025"):
                y25 = item["y2025"]
                lines.append(f"- **Y2025**: QTY {y25['qty']:,} | ราคา {y25['price_per_unit']:.2f} บาท | {y25['supplier']}")

            lines.append(f"- หมายเหตุ: {item.get('note', '')}")
            if item.get("lead_time"):
                lines.append(f"- Lead Time: {item['lead_time']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Summary
    lines.insert(5, f"รวมทั้งหมด: **{total_items} รายการ**")
    lines.insert(6, "")

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────
def main():
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    sheets_data = {}

    # Sheet 1: POSM
    print("📄 Processing 1.POSM(MKT) ...")
    df = pd.read_excel(XLSX_PATH, sheet_name="1.POSM(MKT)", header=None)
    items = parse_posm(df)
    sheets_data["1.POSM(MKT)"] = items
    out = JSON_DIR / "1.POSM(MKT).json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   → {len(items)} items → {out.name}")

    # Sheet 2: Printing(MKT)
    print("📄 Processing 2.Printing(MKT) ...")
    df = pd.read_excel(XLSX_PATH, sheet_name="2.Printing(MKT)", header=None)
    items = parse_printing_mkt(df)
    sheets_data["2.Printing(MKT)"] = items
    out = JSON_DIR / "2.Printing(MKT).json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   → {len(items)} items → {out.name}")

    # Sheet 3: Garment
    print("📄 Processing 3.Garment ...")
    df = pd.read_excel(XLSX_PATH, sheet_name="3.Garment", header=None)
    items = parse_garment(df)
    sheets_data["3.Garment"] = items
    out = JSON_DIR / "3.Garment.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   → {len(items)} items → {out.name}")

    # Sheet 4: สรุปPremium
    print("📄 Processing 4.สรุปPremium ...")
    df = pd.read_excel(XLSX_PATH, sheet_name="4.สรุปPremium", header=None)
    items = parse_premium(df)
    sheets_data["4.สรุปPremium"] = items
    out = JSON_DIR / "4.สรุปPremium.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   → {len(items)} items → {out.name}")

    # Sheet 5: Printing-Rate (merge Rate1-43 + Rate44-109)
    print("📄 Processing 5.Printing-Rate (1-43 + 44-109) ...")
    df1 = pd.read_excel(XLSX_PATH, sheet_name="5.Printing-Rate1-43", header=None)
    items1, next_id = parse_printing_rate(df1, start_item=1)

    df2 = pd.read_excel(XLSX_PATH, sheet_name="5.Printing-Rate44-109", header=None)
    items2, _ = parse_printing_rate(df2, start_item=next_id)

    items = items1 + items2
    sheets_data["5.Printing-Rate"] = items
    out = JSON_DIR / "5.Printing-Rate.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   → {len(items)} items → {out.name}")

    # Generate context file
    print("\n📝 Generating context for Procurement AI ...")
    context_md = generate_context(sheets_data)
    context_path = KNOWLEDGE_DIR / "procurement-context.md"
    context_path.write_text(context_md, encoding="utf-8")
    print(f"   → {context_path}")

    # Also save context in the json dir for easy access
    local_context = JSON_DIR / "procurement-context.md"
    local_context.write_text(context_md, encoding="utf-8")
    print(f"   → {local_context}")

    # Summary
    total = sum(len(v) for v in sheets_data.values())
    print(f"\n✅ Done! {total} items from {len(sheets_data)} sheets")
    print(f"   JSON files: {JSON_DIR}/")
    print(f"   Context:    {context_path}")


if __name__ == "__main__":
    main()
