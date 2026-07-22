"""
แปลง Trade Marketing Materials price for Y2026.final.xlsx → JSON สำหรับ OWUI Knowledge

วิธีการใช้:
  python convert_excel_to_knowledge.py

Output:
  - procurement_knowledge.json  ← สำหรับ upload เข้า OWUI Knowledge
  - procurement_knowledge.md    ← Markdown format (LLM-friendly)

จากนั้นนำไฟล์ไป upload ใน OWUI:
  Admin Settings → Knowledge → + Knowledge → Upload Files
"""

import pandas as pd
import json
import math

XLSX_PATH = "Trade Marketing Materials price for Y2026.final.xlsx"


def safe_float(val):
    """แปลงค่าเป็น float หรือ 0 ถ้า NaN"""
    if pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def parse_posm_sheet(df):
    """แปลง Sheet 1.POSM(MKT) → items list"""
    items = []
    for idx in range(2, len(df)):
        row = df.iloc[idx]
        item_id = row.iloc[1]
        item_name = row.iloc[2]

        if pd.isna(item_id) or pd.isna(item_name):
            continue

        qty = int(safe_float(row.iloc[9]))
        approved_price = safe_float(row.iloc[24])
        approved_vendor = str(row.iloc[26]) if pd.notna(row.iloc[26]) else ""
        total_price = safe_float(row.iloc[25])

        vendors = {}
        for v in range(10, 24):
            vname = f"vendor {v - 9}"
            vprice = safe_float(row.iloc[v])
            if vprice > 0:
                vendors[vname] = vprice

        items.append({
            "id": f"POSM_{item_id}",
            "sheet": "1.POSM(MKT)",
            "category": "POSM",
            "item_name": str(item_name).strip(),
            "keywords": [str(item_name).strip()],
            "quantity": qty,
            "approved_price": approved_price,
            "approved_vendor": approved_vendor,
            "total_price": total_price,
            "vendors": vendors,
            "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
            "lead_time": "10-15 วันทำการหลังยืนยัน AW"
        })

        # สร้าง keywords เพิ่ม
        kw = str(item_name).strip()
        items[-1]["keywords"] = [
            kw,
            kw.replace("สติ๊ก", "สติก"),
            kw.replace("โค้ก", "โค้ก"),
        ]

    return items


def parse_printing_sheet(df):
    """แปลง Sheet 2.Printing(MKT) → items list"""
    items = []
    current_item = None

    for idx in range(2, len(df)):
        row = df.iloc[idx]
        item_id = row.iloc[1]
        item_name = row.iloc[2]
        qty = row.iloc[3]

        # Check header row
        if pd.isna(row.iloc[0]) or row.iloc[0] != "Printing-mkt":
            continue

        if pd.notna(item_id) and pd.notna(item_name):
            # New item
            if current_item:
                items.append(current_item)

            approved_price = safe_float(row.iloc[19])
            approved_vendor = str(row.iloc[20]) if pd.notna(row.iloc[20]) else ""

            current_item = {
                "id": f"PRINT_{item_id}",
                "sheet": "2.Printing(MKT)",
                "category": "งานพิมพ์การตลาด",
                "item_name": str(item_name).strip(),
                "keywords": [str(item_name).strip()],
                "price_tiers": [],
                "approved_price": approved_price,
                "approved_vendor": approved_vendor,
                "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
                "lead_time": "10-15 วันทำการหลังยืนยัน AW"
            }

            if safe_float(qty) > 0:
                vendors = {}
                for v in range(4, 19):
                    vname = f"vendor {(v - 3)}"
                    vprice = safe_float(row.iloc[v])
                    if vprice > 0:
                        vendors[vname] = vprice

                q = int(safe_float(qty))
                current_item["price_tiers"].append({
                    "min_qty": q,
                    "max_qty": q,
                    "unit_price": approved_price if approved_price > 0 else 0,
                    "vendors": vendors
                })

        elif current_item and pd.notna(qty):
            # Same item, different QTY tier
            if safe_float(qty) > 0:
                q = int(safe_float(qty))
                approved_price = safe_float(row.iloc[19])
                vendors = {}
                for v in range(4, 19):
                    vname = f"vendor {(v - 3)}"
                    vprice = safe_float(row.iloc[v])
                    if vprice > 0:
                        vendors[vname] = vprice

                current_item["price_tiers"].append({
                    "min_qty": q,
                    "max_qty": q,
                    "unit_price": approved_price if approved_price > 0 else 0,
                    "vendors": vendors
                })

    if current_item:
        items.append(current_item)

    return items


def parse_garment_sheet(df):
    """แปลง Sheet 3.Garment → items list"""
    items = []
    current_item = None

    for idx in range(2, len(df)):
        row = df.iloc[idx]
        item_id = row.iloc[1]
        item_name = row.iloc[2]

        if row.iloc[0] != "Garment":
            continue

        if pd.notna(item_id) and pd.notna(item_name):
            if current_item:
                items.append(current_item)

            approved_price = safe_float(row.iloc[13])
            approved_vendor = str(row.iloc[14]) if pd.notna(row.iloc[14]) else ""

            current_item = {
                "id": f"GARMENT_{item_id}",
                "sheet": "3.Garment",
                "category": "เสื้อและสิ่งทอ",
                "item_name": str(item_name).strip(),
                "keywords": [str(item_name).strip()],
                "price_tiers": [],
                "approved_price": approved_price,
                "approved_vendor": approved_vendor,
                "note": "สีอ่อน +5, สีกลาง +10, สีเข้ม +20 บาท",
                "lead_time": "15 วันทำการหลังยืนยัน AW"
            }

        qty_range = row.iloc[3]
        if pd.notna(qty_range):
            vendors = {}
            for v in range(4, 13):
                vname = f"vendor {(v - 3)}"
                vprice = safe_float(row.iloc[v])
                if vprice > 0:
                    vendors[vname] = vprice

            approved_price = safe_float(row.iloc[13])
            current_item["price_tiers"].append({
                "qty_range": str(qty_range).strip(),
                "unit_price": approved_price if approved_price > 0 else 0,
                "vendors": vendors
            })

    if current_item:
        items.append(current_item)

    return items


def parse_premium_sheet(df):
    """แปลง Sheet 4.สรุปPremium → items list"""
    items = []
    current_item = None

    for idx in range(2, len(df)):
        row = df.iloc[idx]
        item_id = row.iloc[1]
        item_name = row.iloc[2]

        if row.iloc[0] != "Premium-EA&HRC":
            continue

        if pd.notna(item_id) and pd.notna(item_name):
            if current_item:
                items.append(current_item)

            qty_y2025 = safe_float(row.iloc[4])
            price_y2025 = safe_float(row.iloc[5])
            supplier_y2025 = str(row.iloc[6]) if pd.notna(row.iloc[6]) else ""

            current_item = {
                "id": f"PREMIUM_{item_id}",
                "sheet": "4.สรุปPremium",
                "category": "Premium-EA&HRC",
                "item_name": str(item_name).strip(),
                "keywords": [str(item_name).strip()],
                "y2025": {"qty": qty_y2025, "price": price_y2025, "supplier": supplier_y2025},
                "price_tiers": [],
                "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
                "lead_time": "15-20 วันทำการหลังยืนยัน AW"
            }

        qty = row.iloc[7]
        if pd.notna(qty):
            approved_price = safe_float(row.iloc[17])
            approved_vendor = str(row.iloc[19]) if pd.notna(row.iloc[19]) else ""
            total_price = safe_float(row.iloc[18])

            current_item["price_tiers"].append({
                "qty": str(qty).strip(),
                "unit_price": approved_price if approved_price > 0 else 0,
                "vendor": approved_vendor,
                "total_price": total_price
            })

    if current_item:
        items.append(current_item)

    return items


def main():
    xls = pd.ExcelFile(XLSX_PATH)

    all_items = []

    # Sheet 1: POSM
    df = pd.read_excel(XLSX_PATH, sheet_name="1.POSM(MKT)", header=None)
    all_items.extend(parse_posm_sheet(df))
    print(f"POSM: {len([i for i in all_items if i['sheet']=='1.POSM(MKT)'])} items")

    # Sheet 2: Printing
    df = pd.read_excel(XLSX_PATH, sheet_name="2.Printing(MKT)", header=None)
    all_items.extend(parse_printing_sheet(df))
    print(f"Printing-MKT: {len([i for i in all_items if i['sheet']=='2.Printing(MKT)'])} items")

    # Sheet 3: Garment
    df = pd.read_excel(XLSX_PATH, sheet_name="3.Garment", header=None)
    all_items.extend(parse_garment_sheet(df))
    print(f"Garment: {len([i for i in all_items if i['sheet']=='3.Garment'])} items")

    # Sheet 4: Premium
    df = pd.read_excel(XLSX_PATH, sheet_name="4.สรุปPremium", header=None)
    all_items.extend(parse_premium_sheet(df))
    print(f"Premium: {len([i for i in all_items if i['sheet']=='4.สรุปPremium'])} items")

    # === Export JSON ===
    with open("procurement_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON: procurement_knowledge.json ({len(all_items)} items)")

    # === Export Markdown (LLM-friendly) ===
    with open("procurement_knowledge.md", "w", encoding="utf-8") as f:
        f.write("# Procurement Master Price Y2026\n\n")
        f.write(f"จำนวน {len(all_items)} รายการ จาก 5 หมวดหมู่\n\n")

        for sheet_name in ["1.POSM(MKT)", "2.Printing(MKT)", "3.Garment", "4.สรุปPremium"]:
            sheet_items = [i for i in all_items if i["sheet"] == sheet_name]
            if not sheet_items:
                continue

            cat = sheet_items[0].get("category", sheet_name)
            f.write(f"---\n\n## {cat} ({sheet_name})\n\n")

            for item in sheet_items:
                f.write(f"### {item['item_name']}\n\n")
                f.write(f"- **รหัส**: {item['id']}\n")
                f.write(f"- **คำค้น**: {', '.join(item['keywords'][:3])}\n")

                price_tiers = item.get("price_tiers", [])
                if price_tiers:
                    f.write("\n#### ราคาตามจำนวน\n")
                    f.write("| จำนวน | ราคาต่อหน่วย |\n")
                    f.write("|:-----:|:----------:|\n")
                    for tier in price_tiers:
                        qty_label = tier.get("qty") or tier.get("qty_range") or f"{tier.get('min_qty')}-{tier.get('max_qty')}"
                        price = tier.get("unit_price", 0)
                        f.write(f"| {qty_label} | {price:.2f} บาท |\n")

                if item.get("approved_price", 0) > 0:
                    f.write(f"\n- **ราคาที่ผ่านการประมูล**: {item['approved_price']:.2f} บาท\n")
                if item.get("approved_vendor"):
                    f.write(f"- **ผู้ชนะประมูล**: {item['approved_vendor']}\n")
                if item.get("vendors"):
                    f.write(f"- **จำนวนผู้เสนอราคา**: {len(item['vendors'])} ราย\n")

                f.write(f"\n- **หมายเหตุ**: {item.get('note', '')}\n")
                f.write(f"\n")

    print(f"✅ Markdown: procurement_knowledge.md")
    print("\n🎉 พร้อมนำไปใช้งาน!")
    print("   → Upload procurement_knowledge.json เข้า OWUI Knowledge")
    print("   → หรือใช้ procurement_knowledge.md เป็นเอกสารอ้างอิง")


if __name__ == "__main__":
    main()
