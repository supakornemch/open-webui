"""
Transformation loader — อ่าน Excel ที่ "คนกรอกง่าย" → ตาราง normalized สำหรับ pandas agent

หน้าที่:
  รับภาระ normalize แทนคน — คนกรอกในภาษาคน (dropdown ไทย, layout คุ้นเคย)
  สคริปต์นี้แปลงเป็น 5 ตารางที่ agent query ได้ตรงๆ

  friendly Excel (หลาย sheet, wide, ไทย)
        │
        ▼  load_master()
  ┌──────────────────────────────────────────┐
  │ items          catalog หลัก (1 แถว/สินค้า) │
  │ price_tiers    ราคาตามช่วงจำนวน (long)      │
  │ item_relations การพ่วง (map ชื่อ → รหัส)    │
  │ vendors        ทะเบียนผู้ขาย                │
  │ rules          กฎราคา (สี, VAT)            │
  └──────────────────────────────────────────┘

การใช้งาน:
    from load_master import load_master, lookup_price
    db = load_master()  # อ่าน data/source/master-price-template.xlsx โดยปริยาย
    db["items"]        # DataFrame
    lookup_price(db, "เสื้อยืด", qty=300, color_tone="เข้ม")

    # หรือรันตรงเพื่อ export + ทดสอบ:
    python scripts/load_master.py [path/to/master-price-template.xlsx]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = ROOT / "data" / "source" / "master-price-template.xlsx"

CATEGORY_SHEETS = ["POSM", "Printing", "Garment", "Premium", "PrintRate"]
CATEGORY_PREFIX = {
    "POSM": "POSM",
    "Printing": "PRT",
    "Garment": "GAR",
    "Premium": "PRM",
    "PrintRate": "PRR",
}

# หัวคอลัมน์ไทย → ชื่อ field ภายใน (ตาม ITEM_COLUMNS ใน build_friendly_template.py)
ITEM_FIELD_MAP = {
    "ชื่อสินค้า": "item_name",
    "คำค้นหา (คั่นด้วย ;)": "keywords",
    "คิดราคาแบบ": "pricing_unit",
    "กว้าง(ซม.)": "width_cm",
    "สูง(ซม.)": "height_cm",
    "จำนวนตั้งแต่": "min_qty",
    "ถึง": "max_qty",
    "ราคาต่อหน่วย(บาท)": "unit_price",
    "ผู้ชนะ": "winning_vendor",
    "ผ่านสเปคไหม": "spec_status",
    "คิดราคาตามสีไหม": "color_pricing",
    "ระยะเวลาผลิต(วัน)": "lead_time_days",
    "หมายเหตุ": "note",
}

PRICING_UNIT_MAP = {"ต่อชิ้น": "piece", "ต่อตารางเมตร": "sqm", "ต่อชุด": "set"}
SPEC_MAP = {"ผ่าน": True, "ไม่ตรงสเปค": False}
YESNO_MAP = {"ใช่": True, "ไม่ใช่": False}
COLOR_SURCHARGE = {"อ่อน": 5, "กลาง": 10, "เข้ม": 20}  # ตาม sheet กฎราคา (Garment)


def _norm(s: str) -> str:
    """normalize ชื่อสินค้าไว้ fuzzy match: ตัดวรรค วงเล็บ ตัวพิมพ์"""
    if not isinstance(s, str):
        return ""
    s = s.lower()
    s = re.sub(r"[()\[\]（）\s\-_.,/]+", "", s)
    return s


def _read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    """อ่าน sheet (data_only เพื่อเอาค่าที่สูตรคำนวณแล้ว) แล้ว rename เป็น field ภายใน"""
    df = pd.read_excel(path, sheet_name=sheet, dtype=object)
    df = df.rename(columns={k: v for k, v in ITEM_FIELD_MAP.items() if k in df.columns})
    return df


def _resolve_ids(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """
    คำนวณ item_id เองแบบ deterministic — ไม่พึ่งค่าสูตรใน Excel
    (openpyxl อ่านสูตรได้ค่า cached เท่านั้น; คำนวณเองปลอดภัยกว่า)

    กฎ: แถวที่มี item_name = สินค้าใหม่ → เพิ่มลำดับ
        แถวที่ item_name ว่าง = tier ต่อเนื่อง → ใช้ id ของสินค้าล่าสุด (forward-fill)
    """
    ids = []
    counter = 0
    last_id = None
    for name in df["item_name"]:
        has_name = isinstance(name, str) and name.strip() != ""
        if has_name:
            counter += 1
            last_id = f"{prefix}-{counter:03d}"
        ids.append(last_id)
    df = df.copy()
    df.insert(0, "item_id", ids)
    return df


def load_master(path: str | Path) -> dict[str, pd.DataFrame]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    item_rows = []
    tier_rows = []
    vendor_quote_rows = []
    name_to_id: dict[str, str] = {}
    norm_to_id: dict[str, str] = {}

    for sheet in CATEGORY_SHEETS:
        try:
            df = _read_sheet(path, sheet)
        except ValueError:
            continue  # sheet ไม่มี
        if "item_name" not in df.columns:
            continue

        df = df.dropna(how="all")
        if df.empty:
            continue
        df = _resolve_ids(df, CATEGORY_PREFIX[sheet])

        # forward-fill ข้อมูลระดับสินค้า (คนกรอกแค่แถวแรกของแต่ละสินค้า)
        item_level = ["item_name", "keywords", "pricing_unit", "width_cm",
                      "height_cm", "color_pricing", "lead_time_days"]
        for col in item_level:
            if col in df.columns:
                df[col] = df.groupby("item_id")[col].ffill()

        for item_id, g in df.groupby("item_id", sort=False):
            first = g.iloc[0]
            item_rows.append({
                "item_id": item_id,
                "category": sheet,
                "item_name": _s(first.get("item_name")),
                "item_name_normalized": _norm(_s(first.get("item_name"))),
                "keywords": _s(first.get("keywords")),
                "pricing_unit": PRICING_UNIT_MAP.get(_s(first.get("pricing_unit")), "piece"),
                "width_cm": _f(first.get("width_cm")),
                "height_cm": _f(first.get("height_cm")),
                "color_pricing": YESNO_MAP.get(_s(first.get("color_pricing")), False),
                "lead_time_days": _s(first.get("lead_time_days")),
                "vat_included": False,
            })
            name_to_id[_s(first.get("item_name"))] = item_id
            norm_to_id[_norm(_s(first.get("item_name")))] = item_id

            for _, row in g.iterrows():
                mn, mx, price = _f(row.get("min_qty")), _f(row.get("max_qty")), _f(row.get("unit_price"))
                if price is None:
                    continue
                tier_rows.append({
                    "item_id": item_id,
                    "min_qty": int(mn) if mn is not None else 1,
                    "max_qty": int(mx) if mx is not None else 999999,
                    "unit_price": price,
                    "winning_vendor": _s(row.get("winning_vendor")),
                    "spec_pass": SPEC_MAP.get(_s(row.get("spec_status")), True),
                })
                vendor_quote_rows.append({
                    "item_id": item_id,
                    "min_qty": int(mn) if mn is not None else 1,
                    "vendor_name": _s(row.get("winning_vendor")),
                    "quoted_price": price,
                    "is_winner": True,
                    "spec_pass": SPEC_MAP.get(_s(row.get("spec_status")), True),
                })

    items = pd.DataFrame(item_rows)
    price_tiers = pd.DataFrame(tier_rows)
    vendor_quotes = pd.DataFrame(vendor_quote_rows)

    # ── relations: map ชื่อสินค้า → item_id ──
    relations = _load_relations(path, name_to_id, norm_to_id)
    vendors = _load_vendors(path)
    rules = _load_rules(path)

    return {
        "items": items,
        "price_tiers": price_tiers,
        "vendor_quotes": vendor_quotes,
        "item_relations": relations,
        "vendors": vendors,
        "rules": rules,
    }


def _load_relations(path, name_to_id, norm_to_id) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name="สินค้าพ่วง", dtype=object).dropna(how="all")
    except ValueError:
        return pd.DataFrame(columns=["item_id", "related_item_id", "relation_type",
                                     "ratio", "note", "unmatched"])
    rows = []
    for _, r in df.iterrows():
        main_name = _s(r.get("สินค้าหลัก"))
        rel_name = _s(r.get("สินค้าที่พ่วง"))
        if not main_name and not rel_name:
            continue
        mid = _match_id(main_name, name_to_id, norm_to_id)
        rid = _match_id(rel_name, name_to_id, norm_to_id)
        rows.append({
            "item_id": mid,
            "related_item_id": rid,
            "relation_type": _s(r.get("ความสัมพันธ์")),
            "ratio": _s(r.get("อัตราส่วน")),
            "note": _s(r.get("หมายเหตุ")),
            # ถ้า map ชื่อไม่เจอ → ติดธงไว้เตือน (คนพิมพ์ชื่อไม่ตรง)
            "unmatched": (mid is None) or (rid is None),
        })
    return pd.DataFrame(rows)


def _match_id(name, name_to_id, norm_to_id):
    if not name:
        return None
    if name in name_to_id:
        return name_to_id[name]
    return norm_to_id.get(_norm(name))  # fuzzy: ตัดวรรค/วงเล็บ


def _load_vendors(path) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name="ผู้ขาย", dtype=object).dropna(how="all")
    except ValueError:
        return pd.DataFrame(columns=["vendor_name", "is_local", "contact"])
    df = df.rename(columns={"ชื่อผู้ขาย": "vendor_name", "ผู้ขายท้องถิ่น": "is_local",
                            "ติดต่อ": "contact"})
    df = df[df["vendor_name"].notna()].copy()
    if "is_local" in df.columns:
        df["is_local"] = df["is_local"].map(lambda v: YESNO_MAP.get(_s(v), False))
    return df[[c for c in ["vendor_name", "is_local", "contact"] if c in df.columns]]


def _load_rules(path) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name="กฎราคา", dtype=object).dropna(how="all")
    except ValueError:
        return pd.DataFrame()
    return df.rename(columns={"ชื่อกฎ": "rule_name", "ใช้กับหมวด": "applies_to",
                              "เงื่อนไข": "condition", "ปรับราคา": "adjustment",
                              "คำอธิบาย": "description"})


# ── helpers ──
def _s(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _f(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ตัวอย่างฟังก์ชัน query ที่ pandas agent จะเรียกใช้
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def find_items(db, text: str) -> pd.DataFrame:
    """ค้นสินค้าจากชื่อ/คำค้น (exact → substring → normalized)"""
    items = db["items"]
    q = text.strip()
    qn = _norm(q)
    mask = (
        items["item_name"].str.contains(re.escape(q), case=False, na=False)
        | items["keywords"].str.contains(re.escape(q), case=False, na=False)
        | items["item_name_normalized"].str.contains(re.escape(qn), na=False)
    )
    return items[mask]


def lookup_price(db, text: str, qty: int, color_tone: str | None = None,
                 with_vat: bool = False) -> dict:
    """
    คืนราคาต่อหน่วย + ราคารวม ตาม item + จำนวน + (สีสำหรับ Garment)
    แสดงการทำงานของ transformation: join items ↔ price_tiers + apply rules
    """
    matches = find_items(db, text)
    if matches.empty:
        return {"error": f"ไม่พบสินค้าที่ตรงกับ '{text}'"}

    item = matches.iloc[0]
    item_id = item["item_id"]
    tiers = db["price_tiers"]
    t = tiers[(tiers["item_id"] == item_id) &
              (tiers["min_qty"] <= qty) & (qty <= tiers["max_qty"])]
    if t.empty:  # เกินเพดาน tier → ใช้ tier สูงสุด
        t = tiers[tiers["item_id"] == item_id].sort_values("min_qty").tail(1)
    if t.empty:
        return {"error": f"ไม่พบราคาสำหรับ '{item['item_name']}'"}

    row = t.iloc[0]
    unit = float(row["unit_price"])
    surcharge = 0
    if item["color_pricing"] and color_tone in COLOR_SURCHARGE:
        surcharge = COLOR_SURCHARGE[color_tone]
        unit += surcharge

    total = unit * qty
    if with_vat:
        total *= 1.07

    # หา item พ่วง
    rel = db["item_relations"]
    paired = rel[rel["item_id"] == item_id]

    return {
        "item_id": item_id,
        "item_name": item["item_name"],
        "category": item["category"],
        "qty": qty,
        "tier": f"{int(row['min_qty'])}-{int(row['max_qty'])}",
        "unit_price": round(unit, 2),
        "color_surcharge": surcharge,
        "total": round(total, 2),
        "vat_included": with_vat,
        "winning_vendor": row["winning_vendor"],
        "lead_time_days": item["lead_time_days"],
        "paired_items": paired["related_item_id"].dropna().tolist(),
    }


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    db = load_master(path)

    print("=== สรุปตาราง normalized ===")
    for name, df in db.items():
        print(f"  {name:16s} {len(df):4d} แถว")

    # เตือน relation ที่ map ชื่อไม่เจอ
    rel = db["item_relations"]
    if not rel.empty and rel["unmatched"].any():
        print("\n⚠ สินค้าพ่วงที่จับคู่ชื่อไม่เจอ (ตรวจการพิมพ์ชื่อ):")
        print(rel[rel["unmatched"]][["item_id", "related_item_id", "relation_type"]])

    print("\n=== ตัวอย่าง query: เสื้อยืด 300 ตัว สีเข้ม (รวม VAT) ===")
    import json
    print(json.dumps(lookup_price(db, "เสื้อยืด", 300, color_tone="เข้ม", with_vat=True),
                     ensure_ascii=False, indent=2))

    print("\n=== ตัวอย่าง query: X-Stand 1 ชุด (ดู item พ่วง) ===")
    print(json.dumps(lookup_price(db, "X-Stand", 1), ensure_ascii=False, indent=2))

    # export normalized เป็นไฟล์เดียวหลาย sheet
    out = ROOT / "data" / "generated" / "master-price-normalized.xlsx"
    with pd.ExcelWriter(out) as w:
        for name, df in db.items():
            df.to_excel(w, sheet_name=name, index=False)
    print(f"\n✓ export ตาราง normalized → {out}")


if __name__ == "__main__":
    main()
