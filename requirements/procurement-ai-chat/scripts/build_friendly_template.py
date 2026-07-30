"""
สร้างไฟล์ Excel template ที่ "คนกรอกง่าย" สำหรับ Procurement Master Price

รันครั้งเดียวเพื่อสร้างไฟล์เปล่าพร้อม:
  - หัวคอลัมน์ภาษาไทย
  - Data Validation dropdown (คลิกเลือก ไม่ต้องพิมพ์)
  - สูตร auto-ID (คนไม่ต้องคิดรหัสเอง)
  - Conditional formatting เตือนเมื่อกรอกช่วงจำนวนผิด
  - ตัวอย่างข้อมูล seed ให้เห็นวิธีกรอก

การใช้งาน:
    python build_friendly_template.py
    → ได้ไฟล์ master-price-template.xlsx

โครงสร้าง sheet:
    อ่านก่อน         คำอธิบายวิธีกรอกสำหรับทีมจัดซื้อ
    POSM             อุปกรณ์ ณ จุดขาย
    Printing         งานพิมพ์การตลาด
    Garment          เสื้อผ้า/สิ่งทอ
    Premium          สินค้าพรีเมียม
    PrintRate        อัตราค่าบริการพิมพ์
    สินค้าพ่วง        ความสัมพันธ์ระหว่างสินค้า (item นี้พ่วงกับ item ไหน)
    ผู้ขาย            ทะเบียนผู้ขาย
    กฎราคา           กฎเพิ่ม/ลดราคา (สี, VAT)
    ตัวเลือก          รายการ dropdown (ระบบใช้ ไม่ต้องแก้)
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "source" / "master-price-template.xlsx"

DATA_ROWS = 400  # จำนวนแถวที่เตรียม dropdown/สูตรไว้ล่วงหน้า

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
ID_FILL = PatternFill("solid", fgColor="D9E1F2")
NOTE_FILL = PatternFill("solid", fgColor="FFF2CC")
WARN_FILL = PatternFill("solid", fgColor="FFC7CE")
WRAP = Alignment(wrap_text=True, vertical="top")

# หมวดสินค้า → prefix รหัสอัตโนมัติ
CATEGORY_SHEETS = {
    "POSM": "POSM",
    "Printing": "PRT",
    "Garment": "GAR",
    "Premium": "PRM",
    "PrintRate": "PRR",
}

# คอลัมน์มาตรฐานของ sheet หมวดสินค้า (เหมือนกันทุกหมวด → loader อ่านง่าย)
ITEM_COLUMNS = [
    ("รหัส", 10),            # A  auto formula
    ("ชื่อสินค้า", 40),        # B
    ("คำค้นหา (คั่นด้วย ;)", 26),  # C
    ("คิดราคาแบบ", 16),        # D  dropdown: ต่อชิ้น/ต่อตารางเมตร/ต่อชุด
    ("กว้าง(ซม.)", 11),        # E  สำหรับคิดพื้นที่
    ("สูง(ซม.)", 11),         # F
    ("จำนวนตั้งแต่", 13),       # G
    ("ถึง", 10),             # H
    ("ราคาต่อหน่วย(บาท)", 16),  # I
    ("ผู้ชนะ", 20),           # J  dropdown จาก sheet ผู้ขาย
    ("ผ่านสเปคไหม", 16),       # K  dropdown: ผ่าน/ไม่ตรงสเปค
    ("คิดราคาตามสีไหม", 15),    # L  dropdown: ใช่/ไม่ใช่ (Garment)
    ("ระยะเวลาผลิต(วัน)", 15),  # M
    ("หมายเหตุ", 34),         # N
]


def style_header(ws, headers):
    for col_idx, (name, width) in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "A2"


def add_list_dv(ws, col_letter, values, allow_blank=True):
    """เพิ่ม dropdown จาก list ค่าคงที่"""
    formula = '"' + ",".join(values) + '"'
    dv = DataValidation(type="list", formula1=formula, allow_blank=allow_blank)
    dv.add(f"{col_letter}2:{col_letter}{DATA_ROWS + 1}")
    ws.add_data_validation(dv)


def add_range_dv(ws, col_letter, source_range, allow_blank=True):
    """เพิ่ม dropdown ที่อ้างอิงช่วงเซลล์ในไฟล์เดียวกัน"""
    dv = DataValidation(type="list", formula1=source_range, allow_blank=allow_blank)
    dv.add(f"{col_letter}2:{col_letter}{DATA_ROWS + 1}")
    ws.add_data_validation(dv)


def build_category_sheet(wb, sheet_name, prefix):
    ws = wb.create_sheet(sheet_name)
    style_header(ws, ITEM_COLUMNS)

    # A: สูตร auto-ID — สร้างเฉพาะแถวที่มีชื่อสินค้า (B ไม่ว่าง)
    #    tier ต่อเนื่อง (B ว่าง) ปล่อยว่าง → loader จะ forward-fill รหัสจากแถวบน
    for r in range(2, DATA_ROWS + 2):
        cell = ws.cell(row=r, column=1)
        cell.value = (
            f'=IF(B{r}="","","{prefix}-"&TEXT(COUNTA($B$2:$B{r}),"000"))'
        )
        cell.fill = ID_FILL
        cell.font = Font(color="1F4E78", bold=True)

    # dropdowns
    add_list_dv(ws, "D", ["ต่อชิ้น", "ต่อตารางเมตร", "ต่อชุด"])
    add_range_dv(ws, "J", "ผู้ขาย!$B$2:$B$200")          # ผู้ชนะ ← ชื่อจาก sheet ผู้ขาย
    add_list_dv(ws, "K", ["ผ่าน", "ไม่ตรงสเปค"])
    add_list_dv(ws, "L", ["ใช่", "ไม่ใช่"])

    # conditional formatting: ถ้า "ถึง" < "จำนวนตั้งแต่" → แดง (กรอกช่วงกลับด้าน)
    rng = f"H2:H{DATA_ROWS + 1}"
    ws.conditional_formatting.add(
        rng,
        FormulaRule(formula=[f"AND($H2<>\"\",$G2<>\"\",$H2<$G2)"], fill=WARN_FILL),
    )
    # หมายเหตุ + คำค้น wrap
    for r in range(2, DATA_ROWS + 2):
        ws.cell(row=r, column=2).alignment = WRAP
        ws.cell(row=r, column=14).alignment = WRAP
    ws.auto_filter.ref = f"A1:N{DATA_ROWS + 1}"
    return ws


def build_relations_sheet(wb):
    ws = wb.create_sheet("สินค้าพ่วง")
    headers = [
        ("สินค้าหลัก", 42),
        ("สินค้าที่พ่วง", 42),
        ("ความสัมพันธ์", 20),
        ("อัตราส่วน", 12),
        ("หมายเหตุ", 40),
    ]
    style_header(ws, headers)
    # สินค้าหลัก/พ่วง เลือกจาก dropdown ชื่อสินค้าทั้งหมด (sheet ตัวเลือก)
    add_range_dv(ws, "A", "ตัวเลือก!$A$2:$A$2000")
    add_range_dv(ws, "B", "ตัวเลือก!$A$2:$A$2000")
    add_list_dv(
        ws,
        "C",
        ["ต้องใช้คู่กัน", "มักสั่งด้วยกัน", "ชุดแคมเปญ", "ใช้แทนกันได้", "อุปกรณ์เสริม"],
    )
    for r in range(2, DATA_ROWS + 2):
        ws.cell(row=r, column=5).alignment = WRAP
    ws.auto_filter.ref = f"A1:E{DATA_ROWS + 1}"
    return ws


def build_vendors_sheet(wb):
    ws = wb.create_sheet("ผู้ขาย")
    headers = [
        ("รหัสผู้ขาย", 12),
        ("ชื่อผู้ขาย", 44),
        ("ผู้ขายท้องถิ่น", 15),
        ("ติดต่อ", 30),
    ]
    style_header(ws, headers)
    for r in range(2, 201):
        cell = ws.cell(row=r, column=1)
        cell.value = f'=IF(B{r}="","","V"&TEXT(COUNTA($B$2:$B{r}),"00"))'
        cell.fill = ID_FILL
        cell.font = Font(color="1F4E78", bold=True)
    add_list_dv(ws, "C", ["ใช่", "ไม่ใช่"])
    ws.auto_filter.ref = "A1:D200"
    return ws


def build_rules_sheet(wb):
    ws = wb.create_sheet("กฎราคา")
    headers = [
        ("ชื่อกฎ", 22),
        ("ใช้กับหมวด", 16),
        ("เงื่อนไข", 26),
        ("ปรับราคา", 16),
        ("คำอธิบาย", 40),
    ]
    style_header(ws, headers)
    seed = [
        ["สีอ่อน", "Garment", "โทนสี = อ่อน", "+5 บาท/ชิ้น", "เสื้อสีอ่อน เพิ่มจากราคาฐาน 5 บาท"],
        ["สีกลาง", "Garment", "โทนสี = กลาง", "+10 บาท/ชิ้น", "เสื้อสีกลาง เพิ่มจากราคาฐาน 10 บาท"],
        ["สีเข้ม", "Garment", "โทนสี = เข้ม", "+20 บาท/ชิ้น", "เสื้อสีเข้ม เพิ่มจากราคาฐาน 20 บาท"],
        ["VAT", "ทุกหมวด", "เสมอ", "x1.07", "ราคาทุกรายการยังไม่รวม VAT 7%"],
        ["เร่งด่วน", "ทุกหมวด", "ต้องการภายใน 5-7 วัน", "เลือกผู้ขายท้องถิ่น", "งานด่วนให้เลือก vendor ท้องถิ่น"],
    ]
    for i, row in enumerate(seed, start=2):
        for j, val in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=val)
            if j == 5:
                c.alignment = WRAP
    ws.auto_filter.ref = "A1:E200"
    return ws


def build_options_sheet(wb):
    """รายการชื่อสินค้าทั้งหมด — ใช้เป็นแหล่ง dropdown ของ sheet สินค้าพ่วง.
    ดึงชื่อจากทุก sheet หมวดสินค้าอัตโนมัติด้วยสูตร."""
    ws = wb.create_sheet("ตัวเลือก")
    ws.cell(row=1, column=1, value="สินค้าทั้งหมด").font = Font(bold=True)
    ws.column_dimensions["A"].width = 46
    # รวมชื่อจาก 5 sheet ด้วย VSTACK (Excel 365). ถ้าเวอร์ชันเก่าใช้ loader เติมแทน
    ws.cell(
        row=2,
        column=1,
        value="=IFERROR(VSTACK(POSM!B2:B401,Printing!B2:B401,Garment!B2:B401,"
        "Premium!B2:B401,PrintRate!B2:B401),\"\")",
    )
    ws.sheet_state = "visible"
    return ws


def build_readme_sheet(wb):
    ws = wb.create_sheet("อ่านก่อน", 0)
    ws.column_dimensions["A"].width = 100
    lines = [
        ("วิธีกรอกไฟล์ราคากลาง (สำหรับทีมจัดซื้อ)", True),
        ("", False),
        ("1. เลือก sheet ตามหมวดสินค้า: POSM / Printing / Garment / Premium / PrintRate", False),
        ("2. ช่อง 'รหัส' (คอลัมน์แรก) ระบบสร้างให้อัตโนมัติ — ห้ามพิมพ์เอง", False),
        ("3. พิมพ์ 'ชื่อสินค้า' ให้ครบ แล้วรหัสจะขึ้นเอง", False),
        ("4. สินค้าที่มีหลายราคาตามจำนวน: กรอกชื่อแค่แถวแรก แถวถัดไปเว้นชื่อว่าง", False),
        ("   แล้วกรอกแค่ช่วงจำนวน + ราคา (ระบบเข้าใจว่าเป็นสินค้าตัวเดียวกัน)", False),
        ("5. ช่อง 'จำนวนตั้งแต่' / 'ถึง' กรอกตัวเลขล้วน เช่น 50 กับ 100 (ไม่ต้องพิมพ์ 50-100)", False),
        ("   ถ้าเป็นช่วงบนสุดไม่มีเพดาน ให้ใส่ 'ถึง' = 999999", False),
        ("6. ช่องที่มีลูกศร dropdown ให้คลิกเลือก ห้ามพิมพ์เอง (ผู้ชนะ/ผ่านสเปค/คิดราคาแบบ ฯลฯ)", False),
        ("7. ถ้าช่อง 'ถึง' ขึ้นสีแดง = กรอกช่วงกลับด้าน (ถึง น้อยกว่า ตั้งแต่) ให้แก้", False),
        ("8. เพิ่มผู้ขายใหม่ที่ sheet 'ผู้ขาย' ก่อน แล้วชื่อจะไปโผล่ใน dropdown 'ผู้ชนะ'", False),
        ("9. สินค้าที่ต้องสั่งคู่กัน (เช่น ป้ายไวนิล + ขาตั้ง) กรอกที่ sheet 'สินค้าพ่วง'", False),
        ("10. ราคาที่กรอกทั้งหมด = ราคายังไม่รวม VAT 7%", False),
        ("", False),
        ("หมายเหตุ: sheet 'ตัวเลือก' และ 'กฎราคา' ระบบใช้งาน ปกติไม่ต้องแก้", False),
    ]
    for i, (text, is_title) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=text)
        if is_title:
            c.font = Font(bold=True, size=14, color="1F4E78")
        else:
            c.font = Font(size=11)
        c.alignment = WRAP
    return ws


def seed_examples(wb):
    """ใส่ตัวอย่างข้อมูลจริงเล็กน้อยให้เห็นวิธีกรอก"""
    # POSM: ราคาเดียว
    ws = wb["POSM"]
    ws.append([None, "ถังใส่น้ำแข็ง-โค้ก(ทรงสี่เหลี่ยม)", "coke;coca-cola;ถังน้ำแข็ง",
               "ต่อชิ้น", None, None, 1, 999999, 42.5, "ผู้ขาย ก", "ผ่าน", "ไม่ใช่", "10-15", ""])
    # แก้ปัญหา append ไปทับสูตร A: ลบค่า A ของแถวที่เพิ่งเพิ่ม แล้วปล่อยให้สูตรเดิมทำงาน
    _restore_id_formula(ws, CATEGORY_SHEETS["POSM"])

    # Garment: หลาย tier + คิดราคาตามสี
    ws = wb["Garment"]
    ws.append([None, "เสื้อยืดคอกลม Cotton100% #32", "เสื้อยืด;t-shirt",
               "ต่อชิ้น", None, None, 50, 100, 85, "ผู้ขาย ข", "ผ่าน", "ใช่", "15", "เสื้อ 5 ไซซ์"])
    ws.append([None, None, None, None, None, None, 101, 500, 82, "ผู้ขาย ข", "ผ่าน", "ใช่", "15", ""])
    ws.append([None, None, None, None, None, None, 501, 1000, 78, "ผู้ขาย ข", "ผ่าน", "ใช่", "15", ""])
    _restore_id_formula(ws, CATEGORY_SHEETS["Garment"])

    # Printing: หลาย tier + สินค้าที่จะใช้ทำ relation
    ws = wb["Printing"]
    ws.append([None, "PP Board โค้ก 120x120 cm.", "pp board;พีพีบอร์ด",
               "ต่อชิ้น", 120, 120, 1, 500, 200, "ผู้ขาย ค", "ผ่าน", "ไม่ใช่", "15", ""])
    ws.append([None, None, None, None, None, None, 501, 1000, 190, "ผู้ขาย ค", "ผ่าน", "ไม่ใช่", "15", ""])
    ws.append([None, "X-Stand โครงอลูมิเนียม", "x-stand;เอ็กซ์สแตนด์",
               "ต่อชุด", None, None, 1, 999999, 450, "ผู้ขาย ค", "ผ่าน", "ไม่ใช่", "10", ""])
    ws.append([None, "ป้ายไวนิล Roll-up 85x200 cm.", "roll-up;ไวนิล;rollup",
               "ต่อชิ้น", 85, 200, 1, 999999, 320, "ผู้ขาย ค", "ผ่าน", "ไม่ใช่", "10", ""])
    _restore_id_formula(ws, CATEGORY_SHEETS["Printing"])

    # ผู้ขาย
    ws = wb["ผู้ขาย"]
    ws.append([None, "ผู้ขาย ก", "ใช่", ""])
    ws.append([None, "ผู้ขาย ข", "ใช่", ""])
    ws.append([None, "ผู้ขาย ค", "ไม่ใช่", ""])
    _restore_id_formula(ws, "V", is_vendor=True)

    # สินค้าพ่วง: X-Stand ↔ ป้ายไวนิล
    ws = wb["สินค้าพ่วง"]
    ws.append(["X-Stand โครงอลูมิเนียม", "ป้ายไวนิล Roll-up 85x200 cm.",
               "ต้องใช้คู่กัน", "1:1", "X-Stand ต้องมีป้ายไวนิลเสมอ"])
    ws.append(["เสื้อยืดคอกลม Cotton100% #32", "PP Board โค้ก 120x120 cm.",
               "มักสั่งด้วยกัน", "", "แคมเปญมักสั่งคู่กัน (ตัวอย่าง)"])


def _restore_id_formula(ws, prefix, is_vendor=False):
    """ws.append() เขียนทับสูตร A. คืนสูตร auto-ID ให้ทุกแถวข้อมูล"""
    max_row = ws.max_row
    for r in range(2, max_row + 1):
        cell = ws.cell(row=r, column=1)
        if is_vendor:
            cell.value = f'=IF(B{r}="","","V"&TEXT(COUNTA($B$2:$B{r}),"00"))'
        else:
            cell.value = f'=IF(B{r}="","","{prefix}-"&TEXT(COUNTA($B$2:$B{r}),"000"))'
        cell.fill = ID_FILL
        cell.font = Font(color="1F4E78", bold=True)


def main():
    wb = Workbook()
    wb.remove(wb.active)  # ลบ sheet เริ่มต้น

    for sheet_name, prefix in CATEGORY_SHEETS.items():
        build_category_sheet(wb, sheet_name, prefix)

    build_relations_sheet(wb)
    build_vendors_sheet(wb)
    build_rules_sheet(wb)
    build_options_sheet(wb)
    build_readme_sheet(wb)

    seed_examples(wb)

    wb.save(OUT_PATH)
    print(f"✓ สร้างไฟล์ template: {OUT_PATH}")
    print(f"  Sheets: {wb.sheetnames}")


if __name__ == "__main__":
    main()
