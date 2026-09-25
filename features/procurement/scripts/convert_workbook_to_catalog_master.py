#!/usr/bin/env python3
"""Convert real rows from the original workbook into the new Catalog Master format.

Source sheets (parsed with the same logic as convert_workbook_to_items_json.py):
  - 2.Printing(MKT)      -> Category "Printing-MKT"
  - 4.สรุปPremium          -> Category "Premium"
  - 5.Printing-Rate1-43   -> Category "Printing-Rate"
  - 5.Printing-Rate44-109 -> Category "Printing-Rate"  (header row 5)

Output: one sheet per category (new format):
  ปี | Category | ลำดับ | รายการ | จำนวนขั้นต่ำ | จำนวนสูงสุด | การคิดราคา | vendor-<name>... |
  ราคาที่ผ่านการประมูล | รายชื่อผู้ผ่านการประมูล | หมายเหตุ

Categories with data (Printing-MKT / Printing-Rate) are filled from the
workbook; categories without data (POSM / Garment / Premium) get EMPTY
sheets (headers + blank bordered rows) for the Excel Master to fill in.

Vendor names: the source workbook only has numbered vendor columns
("Vendor 1".."Vendor 15", "vendor1".."vendor9"). Real company names are not
present in the source, so vendor columns are named `vendor-<Category>-<n>`
(e.g. vendor-Printing-Rate-9). Once a Vendor Master maps n -> real name, only
the header text needs to change; prices/award logic stay identical.

VENDOR_NAME_MAP below contains the mappings that are derivable from the source
itself (verified against the note text):
  - Printing-Rate vendor 9 = บจก.กราฟฟิกเน็กซ์
    every row whose note says "ราคาของ บจก.กราฟฟิกเน็กซ์ ต่ำสุด แต่ไม่ตรงตามสเปค"
    has vendor 9 as the minimum quote (verified across all rows).
  - Printing-MKT vendor 5 = หจก.ตรังพริ้นติ้งแอนด์ดีไซน์
    note "หจก.ตรังพริ้นติ้งแอนด์ดีไซน์ เสนอราคาไม่ตรงตามตัวอย่างสเปค" sits in the
    same merged award cell as the "vendor 5" award reference (single occurrence).

Supplier 2025 in 4.สรุปPremium is NOT used for mapping: it is a per-item
supplier name with no tie to a vendor column number.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from convert_workbook_to_items_json import SHEET_CONFIG, build_sheet_items, present

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/source/Trade Marketing Materials price for Y2026.final.xlsx"
OUTPUT = ROOT / "data/masters/Procurement-Pricing-Assistant-Master-2026.xlsx"

YEAR = 2026
CATEGORIES = ["POSM", "Printing-MKT", "Printing-Rate", "Garment", "Premium"]
SHEETS = [
    # All item sheets from the legacy workbook (every category).
    # GVMetadata is metadata-only and intentionally excluded.
    "1.POSM(MKT)",
    "2.Printing(MKT)",
    "3.Garment",
    "4.สรุปPremium",
    "5.Printing-Rate1-43",
    "5.Printing-Rate44-109",
]

# Source workbook sheet used to derive the vendor columns of each category
# (vendor count differs per sheet: POSM 14, Printing-MKT 15, Garment 9, ...).
CATEGORY_SOURCE_SHEET = {
    "POSM": "1.POSM(MKT)",
    "Printing-MKT": "2.Printing(MKT)",
    "Printing-Rate": "5.Printing-Rate1-43",
    "Garment": "3.Garment",
    "Premium": "4.สรุปPremium",
}

# Number of blank data rows pre-created in empty sheets.
EMPTY_SHEET_ROWS = 300

# Real vendor names derivable from the source (see module docstring for the
# evidence behind each mapping). Key: (category, vendor column number).
VENDOR_NAME_MAP = {
    ("Printing-Rate", 9): "บจก.กราฟฟิกเน็กซ์",
    ("Printing-MKT", 5): "หจก.ตรังพริ้นติ้งแอนด์ดีไซน์",
}

COMMON_HEADERS = ["ปี", "ลำดับ", "รายการ", "ระยะเวลา", "จำนวนขั้นต่ำ", "จำนวนสูงสุด", "การคิดราคา"]
TRAILING_HEADERS = ["ราคาที่ผ่านการประมูล", "รายชื่อผู้ผ่านการประมูล", "หมายเหตุ"]

# --- express lead times --------------------------------------------
# Each product+quantity tier expands into 4 rows: normal + 3 express durations.
# Each product+quantity tier has one row; ระยะเวลา is blank by default
# (fill in like "5 วัน", "3 วัน", "7 วัน", "15 วัน").
DURATIONS = [""]

# --- styles -------------------------------------------------------------
HEADER_FILL = PatternFill("solid", start_color="1F4E79", end_color="1F4E79")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
BODY_FONT = Font(name="Arial", size=10)
NOTE_ALIGN = Alignment(vertical="top", wrap_text=True)
HEADER_ALIGN = Alignment(vertical="center", horizontal="center", wrap_text=True)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
RED_FILL = PatternFill("solid", start_color="FFC7CE", end_color="FFC7CE")
RED_FONT = Font(name="Arial", size=10, color="9C0006")
GREEN_FILL = PatternFill("solid", start_color="C6EFCE", end_color="C6EFCE")
GREEN_FONT = Font(name="Arial", size=10, color="006100")


def vendor_number(label: str) -> str | None:
    """'Vendor 7' / 'vendor9' -> '7'."""
    match = re.search(r"\d+", label)
    return match.group(0) if match else None


def vendor_column_name(category: str, number: str) -> str:
    """Canonical vendor column header for (category, vendor number).

    The original vendor number is kept in the header so Excel Master can map
    back to the old workbook's V1..V16 columns:
      - named:     vendor-<n>-<ชื่อจริง>  (e.g. vendor-5-หจก.ตรังพริ้นติ้งแอนด์ดีไซน์)
      - unnamed:   vendor-<Category>-<n> (e.g. vendor-Printing-MKT-9)
    """
    real = VENDOR_NAME_MAP.get((category, int(number)))
    return f"vendor-{number}-{real}" if real else f"vendor-{category}-{number}"


def normalize_award_vendor(raw: str | None, category: str) -> str:
    """Awarded vendor cell ('vendor 5') -> canonical name.

    If the vendor number has a real name in VENDOR_NAME_MAP the real name is
    used, otherwise the numbered placeholder (Printing-Rate-5).
    """
    if not raw:
        return ""
    number = vendor_number(str(raw))
    if not number:
        return ""
    real = VENDOR_NAME_MAP.get((category, int(number)))
    return real if real else f"{category}-{number}"


_LEADING_NUMBER = re.compile(r"^(\d+(?:[.,]\d+)?)")


def parse_vendor_cell(value: object) -> tuple[float | None, str | None, str | None]:
    """Split a raw vendor quote cell into (price, spec, flag_note).

    Source cells are not always clean numbers:
      - 350\\n(36*36cm)      -> price 350, spec "(36*36cm)"
      - 115  (ผ้าUT100 )      -> price 115, spec "(ผ้าUT100)"
      - 8.30/500, 290/490/690 (price per quantity / multi-tier)
                             -> ambiguous: price None, note "ราคา/จำนวน..."
      - 42.5                -> price 42.5
      - empty / non-numeric -> all None
    """
    if value is None:
        return None, None, None
    if isinstance(value, bool):
        return None, None, None
    if isinstance(value, (int, float)):
        return float(value), None, None
    text = str(value).replace("\xa0", " ").strip()
    if not text:
        return None, None, None
    # any "/" means price-per-quantity or multi-tier list -> ambiguous, do not guess
    if "/" in text:
        return None, None, text
    match = _LEADING_NUMBER.match(text.replace(",", ""))
    if not match:
        return None, None, None
    price = float(match.group(1).replace(",", "."))
    spec = text[match.end():].strip()
    return price, (spec or None), None


def split_quantity(quantity: dict[str, Any]) -> tuple[Any, Any]:
    """Split tier quantity into (quantity_min, quantity_max) per Excel Master convention.

      exact 5000  -> (5000, 5000)
      range 1-10  -> (1, 10)
      open 11+    -> (11, "-")   ("-" = no upper bound, Excel Master may leave blank)
      missing     -> (None, None)
    """
    qmin = quantity.get("min")
    qmax = quantity.get("max")
    if qmin is None:
        return None, None
    return qmin, (qmax if qmax is not None else "-")


def category_vendor_columns(category: str) -> list[str]:
    """Vendor column names for a category, read from the source workbook header.

    The source sheet of the category defines how many vendor columns it uses
    (e.g. POSM has 14, Garment has 9). Named columns (VENDOR_NAME_MAP) keep
    their real names; others become vendor-<Category>-<n>.
    """
    sheet_name = CATEGORY_SOURCE_SHEET[category]
    wb = openpyxl.load_workbook(SOURCE, data_only=True, read_only=True)
    ws = wb[sheet_name]
    config = SHEET_CONFIG[sheet_name]
    header_row = config["header_row"]
    columns: list[str] = []
    for column in range(1, ws.max_column + 1):
        header = ws.cell(row=header_row, column=column).value
        if not isinstance(header, str):
            continue
        match = re.fullmatch(r"vendor\s*(\d+)", header, re.IGNORECASE)
        if not match:
            continue
        columns.append(vendor_column_name(category, match.group(1)))
    return columns


def build_master_rows() -> list[dict[str, object]]:
    workbook = openpyxl.load_workbook(SOURCE, data_only=True, read_only=False)
    rows: list[dict[str, object]] = []
    for sheet_name in SHEETS:
        config = SHEET_CONFIG[sheet_name]
        ws = workbook[sheet_name]
        logical_items = build_sheet_items(ws, config)
        category = config["category"]
        for item in logical_items:
            # vendor spec/flag notes across ALL tiers -> product-level Note on the
            # first row (continuation rows are blank, forward-filled by ingest).
            # No vendor price columns are exported; only the notes survive.
            product_vendor_notes: list[str] = []
            for tier in item["quantity_tiers"]:
                for quote in tier["vendor_prices"]:
                    number = vendor_number(quote["vendor"])
                    if not number:
                        continue
                    col_name = vendor_column_name(category, number)
                    _price, spec, flag_note = parse_vendor_cell(quote["price"])
                    if spec:
                        product_vendor_notes.append(f"[{col_name}: สเปค {spec}]")
                    if flag_note:
                        product_vendor_notes.append(
                            f"[{col_name}: ราคา/จำนวน {flag_note} รอ Excel Master ยืนยัน]"
                        )
            product_vendor_notes = list(dict.fromkeys(product_vendor_notes))

            first_tier = True
            for tier in item["quantity_tiers"]:
                qty_min, qty_max = split_quantity(tier["quantity"])
                for dur_idx, duration in enumerate(DURATIONS):
                    row: dict[str, object] = {
                        "ปี": YEAR,
                        "Category": category,
                        "ลำดับ": item["item_number"] if first_tier and dur_idx == 0 else None,
                        "รายการ": item["name"] if first_tier and dur_idx == 0 else None,
                        "ระยะเวลา": duration,
                        "จำนวนขั้นต่ำ": qty_min,
                        "จำนวนสูงสุด": qty_max,
                        "การคิดราคา": "ต่อชิ้น" if first_tier and dur_idx == 0 else None,
                        "ราคาที่ผ่านการประมูล": tier["awarded_price"] if duration == "" else None,
                    }
                    awarded_raw = tier["awarded_vendor"]
                    award_name = normalize_award_vendor(awarded_raw, category)
                    # product-level columns: first row of the product only
                    if first_tier and dur_idx == 0:
                        row["รายชื่อผู้ผ่านการประมูล"] = award_name or None
                        notes = [str(n) for n in tier["award_notes"] if present(n)]
                        notes.extend(product_vendor_notes)
                        row["หมายเหตุ"] = "; ".join(notes) if notes else None
                    rows.append(row)
                first_tier = False
    return rows


def build_workbook(rows: list[dict[str, object]]) -> openpyxl.Workbook:
    # One sheet per category. Categories with data get their real rows;
    # categories without data (POSM / Garment / Premium) get an EMPTY sheet
    # (headers + blank bordered rows) for the Excel Master to fill in.
    by_category: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_category.setdefault(str(row["Category"]), []).append(row)

    def vendor_sort_key(key: str) -> tuple[int, int, str]:
        rest = key[len("vendor-"):]
        if rest.isdigit():  # numbered placeholder vendor-<Category>-<n>
            parts = rest.split("-", 1)
            return (1, int(parts[1]), parts[0])
        return (0, 0, rest)  # named vendors (vendor-<ชื่อจริง>) first

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # drop default sheet

    # No vendor columns: only the product/award columns below.
    build_legend_sheet(wb)  # Legend is the FIRST sheet
    for category in CATEGORIES:
        cat_rows = by_category.get(category, [])

        headers = [*COMMON_HEADERS, *TRAILING_HEADERS]
        last_col = len(headers)
        col_of = {header: i + 1 for i, header in enumerate(headers)}
        col_year = col_of["ปี"]
        col_item = col_of["ลำดับ"]
        col_duration = col_of["ระยะเวลา"]
        col_qty_min = col_of["จำนวนขั้นต่ำ"]
        col_qty_max = col_of["จำนวนสูงสุด"]
        col_award_price = col_of["ราคาที่ผ่านการประมูล"]
        col_note = col_of["หมายเหตุ"]

        ws = wb.create_sheet(category)

        # header
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = HEADER_ALIGN
            cell.border = BORDER

        # data (or blank rows for empty sheets)
        data_rows = cat_rows if cat_rows else [{} for _ in range(EMPTY_SHEET_ROWS)]
        for r, row in enumerate(data_rows, start=2):
            for header, value in row.items():
                if header == "Category":
                    continue  # sheet name is the category
                if value is None or (isinstance(value, str) and value == ""):
                    continue
                cell = ws.cell(row=r, column=col_of[header], value=value)
                cell.font = BODY_FONT
                cell.border = BORDER
                # wrap long text (รายการ/รายชื่อ/หมายเหตุ/การคิดราคา) — Alt+Enter
                # = newline in cell value; wrap_text=True shows it on multiple lines
                cell.alignment = NOTE_ALIGN if header == "หมายเหตุ" else (
                    Alignment(vertical="top", wrap_text=True)
                    if header in {"รายการ", "รายชื่อผู้ผ่านการประมูล", "การคิดราคา"}
                    else Alignment(vertical="top")
                )
                if header == "การคิดราคา" or header == "ราคาที่ผ่านการประมูล":
                    cell.number_format = "#,##0.00"
            for col in range(1, last_col + 1):
                ws.cell(row=r, column=col).border = BORDER

        last_row = len(data_rows) + 1

        # widths
        width_map = {
            col_year: 8,
            col_item: 8,
            col_of["รายการ"]: 48,
            col_duration: 14,
            col_qty_min: 12,
            col_qty_max: 12,
            col_of["การคิดราคา"]: 12,
            col_award_price: 16,
            col_of["รายชื่อผู้ผ่านการประมูล"]: 34,
            col_note: 42,
        }
        for col, width in width_map.items():
            ws.column_dimensions[get_column_letter(col)].width = width

        # freeze header row + columns A-G
        ws.freeze_panes = "H2"
        ws.auto_filter.ref = f"A1:{get_column_letter(last_col)}{last_row}"

        # dropdowns
        dv_year = DataValidation(
            type="list", formula1='"2025,2026"', allow_blank=True, showErrorMessage=True,
            errorTitle="Year ไม่ถูกต้อง", error="Year ต้องเป็น 2025 หรือ 2026 เท่านั้น",
        )
        ws.add_data_validation(dv_year)
        dv_year.add(f"A2:A{last_row}")

        # conditional formatting
        award_price_letter = get_column_letter(col_award_price)
        qty_min_letter = get_column_letter(col_qty_min)
        item_letter = get_column_letter(col_item)
        year_letter = get_column_letter(col_year)

        # 1) red: tier row (has quantity_min) but no awarded price
        ws.conditional_formatting.add(
            f"{award_price_letter}2:{award_price_letter}{last_row}",
            FormulaRule(
                formula=[f'AND({qty_min_letter}2<>"",{award_price_letter}2="")'],
                fill=RED_FILL, font=RED_FONT,
            ),
        )
        # 2) red: duplicate Item within the same Year
        ws.conditional_formatting.add(
            f"{item_letter}2:{item_letter}{last_row}",
            FormulaRule(
                formula=[
                    f'AND(${item_letter}2<>"",COUNTIFS(${year_letter}$2:${year_letter}${last_row},${year_letter}2,'
                    f'${item_letter}$2:${item_letter}${last_row},${item_letter}2)>1)'
                ],
                fill=RED_FILL, font=RED_FONT,
            ),
        )

    # Legend is created FIRST (before category sheets) so it stays sheet index 0
    return wb


def build_legend_sheet(wb: openpyxl.Workbook) -> None:
    ws = wb.create_sheet("Legend", index=0)  # first sheet
    ws.sheet_properties.tabColor = "1F4E79"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 88

    # title
    ws.merge_cells("A1:D1")
    ws["A1"] = "🛒 Procurement Catalog Master — คำอธิบายคอลัมน์ & กติกา"
    ws["A1"].font = Font(name="Arial", bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", start_color="1F4E79", end_color="1F4E79")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # subtitle
    ws.merge_cells("A2:D2")
    ws["A2"] = "ไฟล์ 1 sheet ต่อหมวด · 1 แถว = 1 เรทราคา (tier) · กรอกตามกติกาเพื่อให้ระบบอ่านตรง ๆ ไม่ต้องเดา"
    ws["A2"].font = Font(name="Arial", italic=True, size=10, color="6B7266")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["คอลัมน์", "ชนิด", "บังคับ", "ความหมาย / ตัวอย่าง"]
    for col, text in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col, value=text)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center")

    GREEN_HL = PatternFill("solid", start_color="E2EFDA", end_color="E2EFDA")
    GREEN_FONT = Font(name="Arial", size=10, color="375623", bold=True)
    GOLD_HL = PatternFill("solid", start_color="FFF2CC", end_color="FFF2CC")
    GOLD_FONT = Font(name="Arial", size=10, color="7F6000", bold=True)
    RED_HL = PatternFill("solid", start_color="FCE4E4", end_color="FCE4E4")
    RED_FONT_HL = Font(name="Arial", size=10, color="C00000", bold=True)

    legend = [
        ("ปี", "number", "✔", "ปีของราคาชุดนี้ (2025 / 2026) — logical_item_id = {ปี}:{หมวด}:{ลำดับ}", None),
        ("ลำดับ", "text", "✔", "เลข item เริ่ม 1 ใหม่ทุกหมวด — ใส่แถวแรกของ item เท่านั้น, เรทต่อเนื่องเว้นว่าง", None),
        ("รายการ", "text", "✔", "ชื่อ/สเปคสินค้า — ใส่แถวแรกของ item เท่านั้น, เรทต่อเนื่องเว้นว่าง (ห้าม merge cell)", None),
        ("ระยะเวลา", "text", "✔", "รอบจัดส่ง — ใส่จำนวนวัน เช่น 5 วัน, 3 วัน, 7 วัน, 15 วัน", GOLD_HL),
        ("จำนวนขั้นต่ำ", "number", "✔", "ขั้นต่ำของเรท — 500 = 500+ (ขึ้นไป) · range 1 · exact 5000 (ต้อง min=max)", GOLD_HL),
        ("จำนวนสูงสุด", "number", "✘", "สูงสุดของเรท — ว่าง = ขึ้นไป (500+) · exact = ค่าเดียวกับ min (5000/5000)", GOLD_HL),
        ("การคิดราคา", "text", "✘", "หน่วยคิดราคา เช่น ต่อชิ้น, ต่อตัว, ต่อ ตรม., ต่อป้าย — งานพิมพ์คิดต่อ ตรม.", GREEN_HL),
        ("ราคาที่ผ่านการประมูล", "number", "✔", "ราคาต่อหน่วยที่ชนะ (จาก workbook) — ใส่ทุกแถวเรท · ระบบอ่านตรง ๆ ไม่คำนวณ", None),
        ("รายชื่อผู้ผ่านการประมูล", "text", "✘", "ผู้ชนะการประมูล (V5 / ชื่อ) — ระดับสินค้า ใส่แถวแรกเท่านั้น · คั่นหลายเจ้าด้วย ,", GREEN_HL),
        ("หมายเหตุ", "text", "✘", "หมายเหตุ award เช่น 'ราคาต่ำสุดแต่ไม่ตรงสเปค' — ระดับสินค้า ใส่แถวแรกเท่านั้น", None),
    ]
    for r, (name, kind, req, desc, hl) in enumerate(legend, start=5):
        row_fill = hl
        row_font = BODY_FONT
        if name == "ระยะเวลา":
            row_font = Font(name="Arial", size=10, color="7F6000", bold=True)
        elif name == "ราคาที่ผ่านการประมูล":
            row_font = Font(name="Arial", size=10, color="1F4E79", bold=True)
        cells = [name, kind, req, desc]
        for c, value in enumerate(cells, start=1):
            cell = ws.cell(row=r, column=c, value=value)
            cell.font = row_font
            cell.border = BORDER
            cell.alignment = NOTE_ALIGN if c == 4 else Alignment(vertical="center", horizontal="center" if c in (2, 3) else "left")
            if row_fill:
                cell.fill = row_fill

    # rules — highlighted
    start = 5 + len(legend) + 1
    rules = [
        ("กติกา (ห้ามละเมิด)", True, None),
        ("1. แยก sheet ต่อหมวด (POSM / Printing-MKT / Printing-Rate / Garment / Premium)", False, None),
        ("2. ปี/ลำดับ/รายการ/การคิดราคา/รายชื่อผู้ผ่านการประมูล/หมายเหตุ — แถวแรกของ item ใส่, เรทต่อเนื่องเว้นว่าง (script forward-fill)", False, None),
        ("3. ห้าม merge cell ทุกกรณี — เว้นว่างแทน", False, RED_HL),
        ("4. ห้ามมีแถวว่างคั่นกลางระหว่าง item", False, RED_HL),
        ("5. ระยะเวลา: ตอนนี้ใส่ '5 วัน' ทุกแถว (1 product = N rows 5 วัน เท่านั้น) — ถ้าเพิ่ม express ภายหลัง ให้ copy rows แล้วเปลี่ยน ระยะเวลา + กรอกราคา", False, GOLD_HL),
        ("6. จำนวน: เปิด = 500+ (min=500, max ว่าง) · range = 1/10 · exact = 5000/5000 (ต้อง min=max)", False, GOLD_HL),
        ("7. ราคา award อ่านจากคอลัมน์ ราคาที่ผ่านการประมูล ตรง ๆ (ไม่คำนวณ min ให้ — ข้อมูลจริงมี award ≠ min)", False, GREEN_HL),
        ("8. conditional format: แดง = tier ขาดราคา award / ลำดับซ้ำในปีเดียวกัน", False, None),
        ("9. ไม่มีคอลัมน์ vendor-* — ระบุผู้ชนะผ่าน รายชื่อผู้ผ่านการประมูล (V5 / ชื่อ) เท่านั้น", False, GREEN_HL),
    ]
    for i, (text, is_title, hl) in enumerate(rules):
        cell = ws.cell(row=start + i, column=1, value=text)
        ws.merge_cells(start_row=start + i, start_column=1, end_row=start + i, end_column=4)
        if is_title:
            cell.font = Font(name="Arial", bold=True, size=11, color="FFFFFF")
            cell.fill = PatternFill("solid", start_color="C00000", end_color="C00000")
            cell.alignment = Alignment(vertical="center")
            ws.row_dimensions[start + i].height = 20
        else:
            cell.font = Font(name="Arial", size=10, color=("7F6000" if hl is GOLD_HL else ("C00000" if hl is RED_HL else ("375623" if hl is GREEN_HL else "000000"))))
            cell.fill = hl if hl else PatternFill()
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BORDER


def main() -> None:
    rows = build_master_rows()
    wb = build_workbook(rows)
    wb.save(OUTPUT)

    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    print(f"Rows (tiers): {len(rows)}")
    from collections import Counter
    per_cat = Counter(str(row["Category"]) for row in rows)
    for cat, count in per_cat.items():
        print(f"  {cat}: {count} tier row(s)")
    print("No vendor columns (award via รายชื่อผู้ผ่านการประมูล only)")


if __name__ == "__main__":
    main()
