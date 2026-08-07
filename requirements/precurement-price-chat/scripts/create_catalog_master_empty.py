#!/usr/bin/env python3
"""Create an EMPTY Catalog Master template (no data, headers + blank rows).

One sheet per category (POSM / Printing-MKT / Printing-Rate / Garment /
Premium-EA&HRC) with the standard headers, blank bordered rows to fill in,
freeze A-F + header, wrap text, and a Legend sheet. Vendor columns are
numbered placeholders vendor-<Category>-<n> (no real names).

Run: python3 scripts/create_catalog_master_empty.py
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/masters/Catalog_Master_TEMPLATE.xlsx"

YEARS = [2025, 2026]
CATEGORIES = ["POSM", "Printing-MKT", "Printing-Rate", "Garment", "Premium"]
# vendor column count per category (source workbook)
VENDOR_COUNT = {"POSM": 14, "Printing-MKT": 15, "Printing-Rate": 15, "Garment": 9, "Premium": 9}

COMMON_HEADERS = ["ปี", "ลำดับ", "รายการ", "ระยะเวลา", "จำนวนขั้นต่ำ", "จำนวนสูงสุด", "การคิดราคา"]
TRAILING_HEADERS = ["ราคาที่ผ่านการประมูล", "รายชื่อผู้ผ่านการประมูล", "หมายเหตุ"]

EMPTY_ROWS = 1200  # blank rows to fill (300 products × 4 durations)

HEADER_FILL = PatternFill("solid", start_color="1F4E79", end_color="1F4E79")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
BODY_FONT = Font(name="Arial", size=10)
NOTE_ALIGN = Alignment(vertical="top", wrap_text=True)
HEADER_ALIGN = Alignment(vertical="center", horizontal="center", wrap_text=True)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
RED_FILL = PatternFill("solid", start_color="FFC7CE", end_color="FFC7CE")
RED_FONT = Font(name="Arial", size=10, color="9C0006")


def build_sheet(ws, category: str, headers: list[str]) -> None:
    last_col = len(headers)
    col_of = {h: i + 1 for i, h in enumerate(headers)}
    col_year = col_of["ปี"]
    col_item = col_of["ลำดับ"]
    col_duration = col_of["ระยะเวลา"]
    col_qty_min = col_of["จำนวนขั้นต่ำ"]
    col_award_price = col_of["ราคาที่ผ่านการประมูล"]

    # header
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = BORDER

    # blank bordered rows
    last_row = EMPTY_ROWS + 1
    for r in range(2, last_row + 1):
        for col in range(1, last_col + 1):
            cell = ws.cell(row=r, column=col)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = (
                NOTE_ALIGN
                if headers[col - 1] == "หมายเหตุ"
                else Alignment(vertical="top", wrap_text=True)
            )
            if headers[col - 1] in ("การคิดราคา", "ราคาที่ผ่านการประมูล") or str(headers[col - 1]).startswith("vendor-"):
                cell.number_format = "#,##0.00"

    # widths
    width_map = {
        col_year: 8, col_item: 8, col_of["รายการ"]: 48,
        col_duration: 14,
        col_qty_min: 12, col_of["จำนวนสูงสุด"]: 12, col_of["การคิดราคา"]: 12,
        col_award_price: 16, col_of["รายชื่อผู้ผ่านการประมูล"]: 34,
        col_of["หมายเหตุ"]: 42,
    }
    for h in headers:
        if str(h).startswith("vendor-"):
            width_map[col_of[h]] = 22
    for col, w in width_map.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.freeze_panes = "H2"  # freeze header + columns A-G
    ws.auto_filter.ref = f"A1:{get_column_letter(last_col)}{last_row}"

    dv_year = DataValidation(type="list", formula1='"2025,2026"', allow_blank=True,
                             showErrorMessage=True, errorTitle="ปีไม่ถูกต้อง",
                             error="ปีต้องเป็น 2025 หรือ 2026")
    ws.add_data_validation(dv_year)
    dv_year.add(f"A2:A{last_row}")

    # red: tier row has จำนวนขั้นต่ำ but no ราคาที่ผ่านการประมูล
    ws.conditional_formatting.add(
        f"{get_column_letter(col_award_price)}2:{get_column_letter(col_award_price)}{last_row}",
        FormulaRule(formula=[f'AND({get_column_letter(col_qty_min)}2<>"",{get_column_letter(col_award_price)}2="")'],
                    fill=RED_FILL, font=RED_FONT),
    )
    # red: duplicate ลำดับ within same ปี
    ws.conditional_formatting.add(
        f"{get_column_letter(col_item)}2:{get_column_letter(col_item)}{last_row}",
        FormulaRule(formula=[f'AND(${get_column_letter(col_item)}2<>"",COUNTIFS(${get_column_letter(col_year)}$2:${get_column_letter(col_year)}${last_row},${get_column_letter(col_year)}2,${get_column_letter(col_item)}$2:${get_column_letter(col_item)}${last_row},${get_column_letter(col_item)}2)>1)'],
                    fill=RED_FILL, font=RED_FONT),
    )


def build_legend(wb: Workbook) -> None:
    ws = wb.create_sheet("Legend", index=0)
    ws.sheet_properties.tabColor = "1F4E79"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 78
    ws["A1"] = "Procurement Catalog Master — คำอธิบายคอลัมน์"
    ws["A1"].font = Font(name="Arial", bold=True, size=13, color="1F4E79")
    for col, text in enumerate(["คอลัมน์", "ชนิด", "บังคับ", "ความหมาย / ตัวอย่าง"], start=1):
        cell = ws.cell(row=3, column=col, value=text)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER

    legend = [
        ("ปี", "number", "✔", "ปีของราคาชุดนี้ (2025 / 2026) — logical_item_id = {ปี}:{หมวด}:{ลำดับ}"),
        ("ลำดับ", "text", "✔", "เลข item เริ่ม 1 ใหม่ทุกหมวด — ใส่แถวแรกของ item เท่านั้น, เรทต่อเนื่องเว้นว่าง"),
        ("รายการ", "text", "✔", "ชื่อ/สเปคสินค้า — ใส่แถวแรกของ item เท่านั้น (ห้าม merge)"),
        ("ระยะเวลา", "text", "✔", "รอบจัดส่ง — ใส่จำนวนวัน เช่น 5 วัน, 3 วัน, 7 วัน, 15 วัน"),
        ("จำนวนขั้นต่ำ", "number", "✔", "ขั้นต่ำของเรท — exact (5000) / range (1) / เปิด (500+ = ใส่ 500, สูงสุดว่าง)"),
        ("จำนวนสูงสุด", "number", "✘", "สูงสุดของเรท — exact = ค่าเดียวกับ min (5000/5000); เปิด = ว่างหรือ -"),
        ("การคิดราคา", "text", "✘", "หน่วยคิดราคา เช่น ต่อชิ้น, ต่อตัว, ต่อตรม., ต่อป้าย"),
        ("vendor-<หมวด>-<n>", "number", "✘", "ราคา quote ของ vendor (เลข n = V1…V16 ในไฟล์เดิม) — ว่าง = ไม่เสนอราคา, อย่าใส่ 0"),
        ("ราคาที่ผ่านการประมูล", "number", "✔", "ราคาต่อหน่วยที่ชนะ (จาก workbook) — tier ที่มีขั้นต่ำต้องมีค่านี้"),
        ("รายชื่อผู้ผ่านการประมูล", "text", "✘", "ชื่อ/เลข vendor ที่ผ่านการประมูล คั่นด้วย , — ระดับสินค้า: ใส่แถวแรกเท่านั้น"),
        ("หมายเหตุ", "text", "✘", "หมายเหตุ award เช่น 'ราคาต่ำสุดแต่ไม่ตรงสเปค' — ระดับสินค้า: ใส่แถวแรกเท่านั้น"),
    ]
    for r, row in enumerate(legend, start=4):
        for c, value in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = NOTE_ALIGN

    rules = [
        "กติกา:",
        "1. แยก sheet ต่อหมวด (POSM / Printing-MKT / Printing-Rate / Garment / Premium)",
        "2. ปี/ลำดับ/รายการ/ระยะเวลา/การคิดราคา/รายชื่อผู้ผ่านการประมูล/หมายเหตุ — ระดับสินค้า ใส่แถวแรก, เรทต่อเนื่องเว้นว่าง (script forward-fill)",
        "3. จำนวนขั้นต่ำ/สูงสุด + ราคา vendor + ราคาที่ผ่านการประมูล — ระดับเรท ใส่ทุกแถว",
        "4. ระยะเวลา: ตอนนี้ใส่ '5 วัน' ทุกแถว — ถ้าเพิ่ม express durations ภายหลังให้ copy rows แล้วเปลี่ยน ระยะเวลา + กรอกราคา",
        "5. ห้าม merge cell · ห้ามแถวว่างคั่นกลางระหว่าง item",
        "5. quantity: เปิด = 500+ (min=500, max ว่าง) · range = 1/10 · exact = 5000/5000 (ต้อง min=max)",
        "6. vendor ไม่เสนอราคา = ว่าง (อย่าใส่ 0) · 0 คือราคาจริง",
        "7. freeze คอลัมน์ A–F · ข้อความยาวขึ้นบรรทัดใหม่ได้ (Alt+Enter)",
        "8. conditional format: แดง = tier ขาดราคา award / ลำดับซ้ำในปีเดียวกัน",
    ]
    start = 4 + len(legend) + 1
    for i, text in enumerate(rules):
        cell = ws.cell(row=start + i, column=1, value=text)
        cell.font = Font(name="Arial", bold=(i == 0), size=10, color="1F4E79" if i == 0 else "000000")
        ws.merge_cells(start_row=start + i, start_column=1, end_row=start + i, end_column=4)


def main() -> None:
    wb = Workbook()
    wb.remove(wb.active)
    build_legend(wb)  # Legend is the FIRST sheet
    for category in CATEGORIES:
        vendor_headers = [f"vendor-{category}-{n}" for n in range(1, VENDOR_COUNT[category] + 1)]
        headers = [*COMMON_HEADERS, *vendor_headers, *TRAILING_HEADERS]
        build_sheet(wb.create_sheet(category), category, headers)
    wb.save(OUTPUT)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
