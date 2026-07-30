#!/usr/bin/env python3
"""Transform the raw Y2026 auction workbook into a RAG/pandas-friendly price book.

Output: one flat fact table (1 row = 1 item x 1 quantity tier) plus lookup sheets.
Each fact row carries a self-contained `rag_text` sentence so rows can be embedded
individually without needing neighbouring rows for context.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

VENDOR_RE = re.compile(r"^vendor\s*\d+$", re.IGNORECASE)
NUMERIC_RE = re.compile(r"^-?[\d,]+(?:\.\d+)?$")

# Sheets to read from the raw workbook, and the category code assigned to each.
SOURCE_SHEETS = {
    "1.POSM(MKT)": "POSM",
    "2.Printing(MKT)": "Printing",
    "3.Garment": "Garment",
    "4.สรุปPremium": "Premium",
    "5.Printing-Rate1-43": "PrintRate",
    "5.Printing-Rate44-109": "PrintRate",
}

CATEGORY_LABELS = {
    "POSM": "สื่อ POSM",
    "Printing": "งานพิมพ์ (Printing MKT)",
    "Garment": "เสื้อผ้า (Garment)",
    "Premium": "ของพรีเมียม (Premium)",
    "PrintRate": "เรทงานพิมพ์ (Printing Rate)",
}

# name, width, header comment
FACT_COLUMNS = [
    ("item_id", 14),
    ("category", 12),
    ("category_th", 22),
    ("item_no", 9),
    ("item_name", 46),
    ("spec", 40),
    ("size_w_cm", 11),
    ("size_h_cm", 11),
    ("qty_label", 14),
    ("qty_min", 10),
    ("qty_max", 10),
    ("unit_price_thb", 15),
    ("winner_vendor", 20),
    ("vendor_count", 13),
    ("price_min_thb", 14),
    ("price_max_thb", 14),
    ("price_avg_thb", 14),
    ("price_2025_thb", 15),
    ("vendor_quotes_json", 34),
    ("notes", 40),
    ("rag_text", 90),
]

PRICE_RULES = [
    ("VAT", "ทุกหมวด", "เสมอ", "x1.07", "ราคาทุกรายการยังไม่รวม VAT 7% ต้องแจ้งลูกค้าทุกครั้ง"),
    ("สีอ่อน", "Garment", "โทนสีอ่อน", "+5 บาท/ชิ้น", "เสื้อสีอ่อน บวกเพิ่มจากราคาฐาน"),
    ("สีกลาง", "Garment", "โทนสีกลาง", "+10 บาท/ชิ้น", "เสื้อสีกลาง บวกเพิ่มจากราคาฐาน"),
    ("สีเข้ม", "Garment", "โทนสีเข้ม", "+20 บาท/ชิ้น", "เสื้อสีเข้ม บวกเพิ่มจากราคาฐาน"),
    ("ระยะเวลาผลิต", "ทุกหมวด", "ทุกใบเสนอราคา", "แจ้ง 5-17 วัน", "ต้องแจ้งระยะเวลาผลิตพร้อมราคาทุกครั้ง"),
    ("รอไฟล์ AW", "ทุกหมวด", "งานพิมพ์ที่ต้องใช้อาร์ตเวิร์ก", "เริ่มนับวันผลิตหลังได้ไฟล์ AW", "ยืนยันวันส่งได้เมื่อได้รับไฟล์ AW ครบ"),
    ("งานเร่งด่วน", "ทุกหมวด", "ต้องการภายใน 5-7 วัน", "เลือกผู้ขายท้องถิ่น", "งานด่วนให้เลือก vendor ท้องถิ่นเพื่อลดเวลาขนส่ง"),
]

README_LINES = [
    ("ไฟล์ราคากลาง Y2026 — โครงสร้างสำหรับ AI (RAG + pandas)", True),
    ("", False),
    ("ออกแบบใหม่จากไฟล์ประมูลเดิม โดยยุบทุกหมวดมาไว้ในตารางเดียว", False),
    ("", False),
    ("SHEET ที่มี", True),
    ("  price_book   ตารางหลัก 1 แถว = 1 สินค้า x 1 ช่วงจำนวน (ใช้ pandas query ได้ตรง ๆ)", False),
    ("  items        ทะเบียนสินค้า 1 แถว = 1 สินค้า (ไม่ซ้ำ) ใช้ค้นหาชื่อ/รหัส", False),
    ("  vendors      รายชื่อผู้ขายที่ชนะประมูล + จำนวนรายการที่ชนะ", False),
    ("  price_rules  กฎการคิดราคาที่ AI ต้องใช้ประกอบทุกคำตอบ", False),
    ("  glossary     คำพ้อง/คำที่ผู้ใช้มักพิมพ์ ใช้ช่วย mapping คำค้นหา", False),
    ("", False),
    ("กติกาสำคัญของ sheet price_book", True),
    ("  1. ไม่มี merged cell ไม่มีหัวตารางซ้อน อ่านด้วย pd.read_excel ได้ทันที", False),
    ("  2. ทุกแถวเติมค่าซ้ำครบ (item_id / item_name) ไม่ต้อง forward-fill", False),
    ("  3. qty_min / qty_max เป็นตัวเลข ใช้กรองช่วงจำนวนได้ (qty_max ว่าง = ไม่จำกัดเพดาน)", False),
    ("  4. unit_price_thb = ราคาที่ผ่านการประมูล (ราคาที่ใช้ตอบลูกค้า) ยังไม่รวม VAT", False),
    ("  5. ราคาเสนอของผู้ขายทุกรายเก็บเป็น JSON ใน vendor_quotes_json ไม่กระจายเป็นคอลัมน์", False),
    ("  6. rag_text = ประโยคสรุปครบในตัว 1 แถว ใช้ทำ embedding ได้เลย", False),
    ("", False),
    ("ตัวอย่าง pandas", True),
    ("  df = pd.read_excel(path, sheet_name='price_book')", False),
    ("  # ราคาเสื้อโปโล 300 ตัว", False),
    ("  m = df.item_name.str.contains('โปโล') & (df.qty_min <= 300)", False),
    ("  m &= (df.qty_max >= 300) | df.qty_max.isna()", False),
    ("  df.loc[m, ['item_name','qty_label','unit_price_thb','winner_vendor']]", False),
    ("", False),
    ("การอัปเดตราคา", True),
    ("  แก้เฉพาะคอลัมน์ unit_price_thb / winner_vendor / notes ได้เลย", False),
    ("  เพิ่มสินค้าใหม่ = เพิ่มแถวต่อท้าย ใส่ item_id ใหม่ แล้วรัน build_price_book.py --refresh-rag", False),
]

# `term` must appear in item_name/spec verbatim — it is what the tool searches for.
# Words users type go in `synonyms`. Getting these backwards makes the entry dead.
GLOSSARY = [
    ("เสื้อยืด", "t-shirt;ทีเชิ้ต;เสื้อคอกลม", "Garment"),
    ("เสื้อโปโล", "polo;โปโล;เสื้อคอปก", "Garment"),
    ("ธงปีกนก", "ธงญี่ปุ่น;feather flag;ธงชายธง;beach flag", "PrintRate"),
    ("สติกเกอร์", "sticker;สติ๊กเกอร์;ฉลาก", "PrintRate"),
    ("PP Board", "โฟมบอร์ด;foam board;ป้ายโฟม;พีพีบอร์ด;พลาสวูด;plaswood", "PrintRate"),
    ("Shelf Talker", "ป้ายราคา;ป้ายชั้นวาง;price card;ป้ายแขวน", "PrintRate"),
    ("Vacuum", "ตู้เย็น;สติกเกอร์ตู้เย็น;cooler", "PrintRate"),
    ("ร่ม", "umbrella;ร่มสนาม;ร่มเสาข้าง", "POSM"),
    ("แก้วกระดาษ", "paper cup;แก้วน้ำ", "Premium"),
    ("ไดคัท", "ไดคัด;diecut;die cut", "PrintRate"),
    ("Wrap Around", "ล้อมกอง;ป้ายล้อมกอง", "PrintRate"),
    ("ประกาศนียบัตร", "เกียรติบัตร;certificate;วุฒิบัตร", "PrintRate"),
    ("โปสเตอร์", "poster;ใบปิด", "PrintRate"),
    ("ถังใส่น้ำแข็ง", "ถังน้ำแข็ง;ice bucket;ถังแช่", "POSM"),
    ("หนังสือคู่มือ", "คู่มือ;booklet", "PrintRate"),
]


def norm(text) -> str:
    if text is None:
        return ""
    s = unicodedata.normalize("NFC", str(text))
    return re.sub(r"\s+", " ", s).strip()


def to_num(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = norm(value).replace(",", "")
    if not s or not NUMERIC_RE.match(s):
        return None
    return float(s)


def tidy_num(value):
    """Return int when the float is whole, so Excel shows 700 not 700.0."""
    if value is None:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 4)


def parse_qty(label: str):
    """'1,001-3,000' -> (1001, 3000); '5000' -> (5000, 5000); '5,001+' -> (5001, None)."""
    s = norm(label).replace(",", "").replace("ชิ้น", "")
    if not s:
        return None, None
    if s.startswith(("น้อยกว่า", "ไม่เกิน", "ต่ำกว่า")):
        hi = to_num(re.sub(r"[^\d.]", "", s))
        return (1, tidy_num(hi)) if hi else (None, None)
    if s.startswith(("มากกว่า", "ตั้งแต่")):
        lo = to_num(re.sub(r"[^\d.]", "", s))
        return tidy_num(lo), None
    if s.endswith(("+", "ขึ้นไป")):
        lo = to_num(s.rstrip("+ขึ้นไป "))
        return tidy_num(lo), None
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)$", s)
    if m:
        return tidy_num(float(m.group(1))), tidy_num(float(m.group(2)))
    v = to_num(s)
    return (tidy_num(v), tidy_num(v)) if v is not None else (None, None)


def split_name(raw: str):
    """Source names cram spec detail after a newline or ' - '. Keep line 1 as the name."""
    text = unicodedata.normalize("NFC", str(raw or ""))
    parts = [p.strip(" -–") for p in text.split("\n") if p.strip(" -–")]
    if not parts:
        return "", ""
    return norm(parts[0]), norm(" | ".join(parts[1:]))


def find_size(text: str):
    m = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:cm|ซม)", text)
    if m:
        return tidy_num(float(m.group(1))), tidy_num(float(m.group(2)))
    return None, None


@dataclass
class SheetMap:
    header_row: int
    item_no: int | None = None
    name: int | None = None
    qty: int | None = None
    price: int | None = None
    winner: int | None = None
    price_2025: int | None = None
    vendors: dict[int, str] = field(default_factory=dict)


def map_sheet(ws) -> SheetMap | None:
    """Locate the header row and the columns we care about, by header text."""
    for row_idx in range(1, min(ws.max_row, 12) + 1):
        headers = {c: norm(v) for c, v in enumerate(next(ws.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True)))}
        lowered = {c: h.lower() for c, h in headers.items()}
        has_name = any(h in ("รายการ", "รายากร") for h in headers.values())
        has_qty = any(l.startswith("qty") for l in lowered.values())
        if not (has_name and has_qty):
            continue

        sm = SheetMap(header_row=row_idx)
        for col, head in headers.items():
            low = lowered[col]
            if head in ("Item", "ลำดับ") and sm.item_no is None:
                sm.item_no = col
            elif head in ("รายการ", "รายากร") and sm.name is None:
                sm.name = col
            elif low.startswith("qty") and sm.qty is None:
                sm.qty = col
            elif VENDOR_RE.match(head):
                sm.vendors[col] = head
            elif "ราคาที่ผ่าน" in head and sm.price is None:
                sm.price = col
            elif "รายชื่อผู้ผ่าน" in head and sm.winner is None:
                sm.winner = col
            elif head == "History 2025":
                sm.price_2025 = col + 1  # merged label spans qty + price
            elif "price y2025" in low:
                sm.price_2025 = col
        # Premium has both 'QTY' and 'QTY Y2026'; prefer the Y2026 plan qty.
        for col, head in headers.items():
            if head.lower() == "qty y2026":
                sm.qty = col
        if sm.name is not None and sm.qty is not None and sm.price is not None:
            return sm
    return None


def reattach_orphan_tiers(rows: list[tuple], sm: "SheetMap") -> list[tuple]:
    """Move a nameless priced tier that sits under a rule-only add-on past the next item.

    The sheet states add-ons like 'ฐานกากบาทสำหรับธงปีกนก' as a name plus a pricing
    rule, with no tier and no price of their own, and then puts the *next* item's first
    tier on a nameless row. Read in order, that tier attaches to the add-on and quotes
    the next item's price under the add-on's name.
    """

    def at(row, idx):
        return row[idx] if idx is not None and idx < len(row) else None

    def has(row, idx):
        return bool(norm(at(row, idx)))

    out = list(rows)
    i = 1
    while i < len(out) - 1:
        row, nxt, prev = out[i], out[i + 1], out[i - 1]
        nameless_priced_tier = (
            not has(row, sm.name)
            and not has(row, sm.item_no)
            and has(row, sm.qty)
            and to_num(at(row, sm.price)) is not None
        )
        prev_is_rule_only = (
            has(prev, sm.name)
            and not has(prev, sm.qty)
            and to_num(at(prev, sm.price)) is None
        )
        if nameless_priced_tier and prev_is_rule_only and has(nxt, sm.item_no):
            out[i], out[i + 1] = nxt, row
            i += 2
            continue
        i += 1
    return out


def unmerge_notes(ws, min_col: int) -> None:
    """Copy vertically merged note text down its range, for note columns only.

    openpyxl reports only the top-left cell of a merge, so a rule spanning two rows
    (one per add-on) reaches only the first and the second looks unexplained. Scoped to
    note columns: filling a merged *name* block would repeat the name on every tier row,
    which the row loop would read as a new variant.
    """
    for rng in list(ws.merged_cells.ranges):
        if rng.max_row == rng.min_row or rng.min_col < min_col:
            continue
        value = ws.cell(rng.min_row, rng.min_col).value
        if value is None:
            continue
        ws.unmerge_cells(str(rng))
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                ws.cell(r, c).value = value


def read_rows(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True)
    records: list[dict] = []

    for sheet_name, category in SOURCE_SHEETS.items():
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        sm = map_sheet(ws)
        if sm is None:
            continue
        if sm.winner is not None:
            unmerge_notes(ws, sm.winner + 1)  # sm.winner is 0-based, openpyxl is 1-based

        seq = 0
        sub = 0
        last_qty_min = None
        last_price_note = ""
        cur_no = cur_name = cur_spec = ""
        sheet_rows = reattach_orphan_tiers(
            list(ws.iter_rows(min_row=sm.header_row + 1, values_only=True)), sm
        )
        for row in sheet_rows:
            def cell(idx):
                return row[idx] if idx is not None and idx < len(row) else None

            raw_name_cell = cell(sm.name)
            raw_name = norm(raw_name_cell)
            raw_no = norm(cell(sm.item_no))
            qty_label = norm(cell(sm.qty))
            price = to_num(cell(sm.price))
            price_note = "" if price is not None else norm(cell(sm.price))

            if raw_no and not NUMERIC_RE.match(raw_no.replace(".", "")):
                continue  # footnote row, e.g. '*หมายเหตุ ...'

            row_qty_min, _ = parse_qty(qty_label)

            if raw_no:
                cur_no, sub = raw_no, 0
                seq += 1
                cur_name, cur_spec = split_name(raw_name_cell)
                last_qty_min = None
            elif raw_name.startswith(("-", "*")):
                # Spec detail continuing the item above.
                cur_spec = norm(f"{cur_spec} | {raw_name.lstrip('-* ')}".strip(" |"))
            elif raw_name:
                # A name on a row whose qty tier keeps climbing is spec text bleeding
                # into the name column; a reset/absent tier means a real variant.
                climbing = (
                    row_qty_min is not None
                    and last_qty_min is not None
                    and row_qty_min > last_qty_min
                )
                if climbing:
                    cur_spec = norm(f"{cur_spec} | {raw_name.lstrip('-* ')}".strip(" |"))
                else:
                    sub += 1
                    cur_name, cur_spec = split_name(raw_name_cell)

            if row_qty_min is not None:
                last_qty_min = row_qty_min

            if not cur_name:
                continue
            # Keep priced rows, rows whose "price" is a text rule, and the first row of
            # every item/variant so add-on services with no own price stay in the catalog.
            if price is None and not price_note and not (raw_no or raw_name):
                continue

            quotes = {}
            for col, label in sm.vendors.items():
                v = to_num(cell(col))
                if v is not None:
                    quotes[label] = tidy_num(v)

            winner = ""
            notes_bits = []
            if sm.winner is not None:
                for value in row[sm.winner:]:
                    text = norm(value)
                    if not text or NUMERIC_RE.match(text):
                        continue
                    # Only 'vendor N' is a winner; anything else is a pricing rule that
                    # belongs in notes, not in a field the agent quotes as the supplier.
                    if not winner and VENDOR_RE.match(text):
                        winner = text
                    elif text not in notes_bits:
                        notes_bits.append(text)

            if price_note:
                last_price_note = price_note
            elif price is None:
                # Add-on services share one rule stated on the first row of the block.
                price_note = last_price_note
            if price_note:
                notes_bits.insert(0, price_note)

            qty_min, qty_max = parse_qty(qty_label)
            w_cm, h_cm = find_size(f"{cur_name} {cur_spec}")
            values = list(quotes.values())
            item_no = cur_no or str(seq)
            suffix = f".{sub}" if sub else ""

            records.append(
                {
                    "item_id": f"{category}-{item_no.replace(' ', '')}{suffix}",
                    "category": category,
                    "category_th": CATEGORY_LABELS.get(category, category),
                    "item_no": item_no,
                    "item_name": cur_name,
                    "spec": cur_spec,
                    "size_w_cm": w_cm,
                    "size_h_cm": h_cm,
                    "qty_label": qty_label or (str(tidy_num(qty_min)) if qty_min else ""),
                    "qty_min": qty_min,
                    "qty_max": qty_max,
                    "unit_price_thb": tidy_num(price),
                    "winner_vendor": winner,
                    "vendor_count": len(values) or None,
                    "price_min_thb": tidy_num(min(values)) if values else None,
                    "price_max_thb": tidy_num(max(values)) if values else None,
                    "price_avg_thb": round(sum(values) / len(values), 2) if values else None,
                    "price_2025_thb": tidy_num(to_num(cell(sm.price_2025))),
                    "vendor_quotes_json": json.dumps(quotes, ensure_ascii=False) if quotes else "",
                    "notes": " | ".join(notes_bits),
                }
            )
    return records


def drop_placeholders(records: list[dict]) -> list[dict]:
    """An item's header row has no price when its tiers follow below; keep only the tiers."""
    priced = {r["item_id"] for r in records if r["unit_price_thb"] is not None}
    return [r for r in records if r["unit_price_thb"] is not None or r["item_id"] not in priced]


def build_rag_text(r: dict) -> str:
    bits = [f"[{r['item_id']}] {r['item_name']}"]
    if r["spec"]:
        bits.append(f"รายละเอียด: {r['spec']}")
    bits.append(f"หมวด: {r['category_th']}")
    if r["qty_min"] and r["qty_max"] and r["qty_min"] != r["qty_max"]:
        bits.append(f"ช่วงจำนวน {r['qty_label']} ชิ้น")
    elif r["qty_max"] is None and r["qty_min"]:
        bits.append(f"จำนวน {r['qty_min']} ชิ้นขึ้นไป")
    elif r["qty_min"]:
        bits.append(f"ที่จำนวน {r['qty_min']} ชิ้น")
    if r["unit_price_thb"] is None:
        bits.append("ไม่มีราคาต่อหน่วยตายตัว ต้องอ้างอิงตามกฎในหมายเหตุ")
    else:
        bits.append(f"ราคาต่อหน่วย {r['unit_price_thb']} บาท (ยังไม่รวม VAT 7%)")
    if r["winner_vendor"]:
        bits.append(f"ผู้ชนะประมูล: {r['winner_vendor']}")
    if r["vendor_count"] and r["vendor_count"] > 1:
        bits.append(f"มีผู้เสนอราคา {r['vendor_count']} ราย ต่ำสุด {r['price_min_thb']} สูงสุด {r['price_max_thb']} บาท")
    if r["price_2025_thb"]:
        bits.append(f"ราคาปี 2025 อยู่ที่ {r['price_2025_thb']} บาท")
    if r["notes"]:
        bits.append(f"หมายเหตุ: {r['notes']}")
    return " | ".join(bits)


HDR_FILL = PatternFill("solid", fgColor="1F4E5F")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
TITLE_FONT = Font(bold=True, size=12, color="1F4E5F")


def style_header(ws, widths: list[tuple[str, int]], freeze="A2"):
    for idx, (name, width) in enumerate(widths, start=1):
        cell = ws.cell(row=1, column=idx, value=name)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = Alignment(vertical="center", horizontal="left")
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = freeze
    ws.auto_filter.ref = f"A1:{get_column_letter(len(widths))}1"


def write_workbook(records: list[dict], out_path: Path):
    wb = openpyxl.Workbook()

    # --- README -------------------------------------------------------------
    ws = wb.active
    ws.title = "อ่านก่อน"
    ws.column_dimensions["A"].width = 108
    for i, (line, is_head) in enumerate(README_LINES, start=1):
        c = ws.cell(row=i, column=1, value=line)
        c.font = TITLE_FONT if is_head else Font(size=10)
        c.alignment = Alignment(vertical="top")

    # --- price_book ---------------------------------------------------------
    ws = wb.create_sheet("price_book")
    style_header(ws, FACT_COLUMNS, freeze="F2")
    keys = [name for name, _ in FACT_COLUMNS]
    for row_idx, rec in enumerate(records, start=2):
        rec["rag_text"] = build_rag_text(rec)
        for col_idx, key in enumerate(keys, start=1):
            value = rec.get(key)
            cell = ws.cell(row=row_idx, column=col_idx, value=value if value != "" else None)
            if key in ("unit_price_thb", "price_min_thb", "price_max_thb", "price_avg_thb", "price_2025_thb"):
                cell.number_format = "#,##0.00"
            elif key in ("qty_min", "qty_max", "vendor_count"):
                cell.number_format = "#,##0"
            elif key in ("rag_text", "notes", "spec", "vendor_quotes_json"):
                cell.alignment = Alignment(wrap_text=False, vertical="top")

    # --- items --------------------------------------------------------------
    items: dict[str, dict] = {}
    for r in records:
        it = items.setdefault(
            r["item_id"],
            {
                "item_id": r["item_id"],
                "category": r["category"],
                "item_name": r["item_name"],
                "spec": r["spec"],
                "tier_count": 0,
                "min_unit_price_thb": None,
                "max_unit_price_thb": None,
                "winner_vendor": r["winner_vendor"],
            },
        )
        it["tier_count"] += 1
        price = r["unit_price_thb"]
        if price is not None:
            lo, hi = it["min_unit_price_thb"], it["max_unit_price_thb"]
            it["min_unit_price_thb"] = price if lo is None else min(lo, price)
            it["max_unit_price_thb"] = price if hi is None else max(hi, price)

    item_cols = [
        ("item_id", 14), ("category", 12), ("item_name", 50), ("spec", 46),
        ("tier_count", 11), ("min_unit_price_thb", 18), ("max_unit_price_thb", 18), ("winner_vendor", 22),
    ]
    ws = wb.create_sheet("items")
    style_header(ws, item_cols, freeze="D2")
    for i, it in enumerate(items.values(), start=2):
        for j, (key, _) in enumerate(item_cols, start=1):
            c = ws.cell(row=i, column=j, value=it.get(key) or None)
            if "price" in key:
                c.number_format = "#,##0.00"

    # --- vendors ------------------------------------------------------------
    wins: dict[str, int] = {}
    for r in records:
        if r["winner_vendor"]:
            wins[r["winner_vendor"]] = wins.get(r["winner_vendor"], 0) + 1
    vendor_cols = [("vendor_name", 40), ("win_row_count", 15), ("is_local", 12), ("contact", 30)]
    ws = wb.create_sheet("vendors")
    style_header(ws, vendor_cols)
    yes_no = DataValidation(type="list", formula1='"ใช่,ไม่ใช่"', allow_blank=True)
    ws.add_data_validation(yes_no)
    for i, (name, count) in enumerate(sorted(wins.items(), key=lambda kv: -kv[1]), start=2):
        ws.cell(row=i, column=1, value=name)
        ws.cell(row=i, column=2, value=count)
        yes_no.add(ws.cell(row=i, column=3))

    # --- price_rules --------------------------------------------------------
    rule_cols = [("rule_name", 16), ("applies_to", 14), ("condition", 30), ("adjustment", 24), ("description", 62)]
    ws = wb.create_sheet("price_rules")
    style_header(ws, rule_cols)
    for i, rule in enumerate(PRICE_RULES, start=2):
        for j, value in enumerate(rule, start=1):
            ws.cell(row=i, column=j, value=value)

    # --- glossary -----------------------------------------------------------
    gl_cols = [("term", 20), ("synonyms", 46), ("category_hint", 16)]
    ws = wb.create_sheet("glossary")
    style_header(ws, gl_cols)
    for i, row in enumerate(GLOSSARY, start=2):
        for j, value in enumerate(row, start=1):
            ws.cell(row=i, column=j, value=value)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def main():
    here = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(here / "data/source/Trade Marketing Materials price for Y2026.final.xlsx"))
    ap.add_argument("--out", default=str(here / "data/source/price-book-Y2026.xlsx"))
    ap.add_argument("--jsonl", default=str(here / "data/source/price-book-Y2026.jsonl"))
    args = ap.parse_args()

    records = drop_placeholders(read_rows(Path(args.src)))
    write_workbook(records, Path(args.out))

    with open(args.jsonl, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps({"id": r["item_id"], "text": r["rag_text"], "metadata": {
                k: r[k] for k in ("category", "item_name", "qty_min", "qty_max", "unit_price_thb", "winner_vendor")
            }}, ensure_ascii=False) + "\n")

    by_cat: dict[str, int] = {}
    for r in records:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    print(f"rows: {len(records)}")
    for k, v in sorted(by_cat.items()):
        print(f"  {k:<10} {v}")
    print(f"xlsx  -> {args.out}")
    print(f"jsonl -> {args.jsonl}")


if __name__ == "__main__":
    main()
