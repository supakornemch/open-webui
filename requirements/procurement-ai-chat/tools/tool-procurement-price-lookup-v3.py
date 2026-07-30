"""
title: Procurement Price Lookup
author: Haadthip DIO
version: 3.0
required_open_webui_version: 0.5.0

Reads the flat price book workbook with pandas at call time — no embedded data.

The workbook (price-book-Y2026.xlsx, sheet `price_book`) is already normalised to
one row per item x quantity tier, so lookups are plain DataFrame filters instead of
per-sheet parsers with hardcoded column indices. Regenerate it from the raw auction
file with scripts/build_price_book.py.

Updating prices: overwrite the xlsx in place. The cache keys on file mtime, so the
next query picks it up with no restart and no valve change.
"""

import json
import os
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field

# Surcharges live in the workbook's price_rules sheet; this is the parsing contract.
COLOR_RULE_PREFIX = "สี"


class Tools:
    class Valves(BaseModel):
        excel_path: str = Field(
            default="/app/backend/data/procurement/price-book-Y2026.xlsx",
            description="Path to the price book workbook inside the container",
        )
        vat_note: str = Field(
            default="ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
            description="Disclaimer appended to every price answer",
        )
        lead_time_note: str = Field(
            default="ระยะเวลาผลิต 5-17 วันทำการ นับจากวันที่ได้รับไฟล์ AW ครบ",
            description="Lead time statement appended to every price answer",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._df: Optional[pd.DataFrame] = None
        self._rules: Optional[pd.DataFrame] = None
        self._synonyms: dict[str, str] = {}
        self._cache_key: Optional[tuple] = None

    # ── data loading ────────────────────────────────────────────────────────

    def _load(self) -> pd.DataFrame:
        """Read the workbook, re-reading only when the file changes on disk."""
        path = self.valves.excel_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"ไม่พบไฟล์ราคา: {path}")

        stat = os.stat(path)
        key = (path, stat.st_mtime, stat.st_size)
        if self._df is not None and self._cache_key == key:
            return self._df

        df = pd.read_excel(path, sheet_name="price_book")
        df["_name_lower"] = df["item_name"].fillna("").str.lower()
        df["_spec_lower"] = df["spec"].fillna("").str.lower()

        try:
            self._rules = pd.read_excel(path, sheet_name="price_rules")
        except ValueError:
            self._rules = None

        self._synonyms = {}
        try:
            gl = pd.read_excel(path, sheet_name="glossary")
            for _, row in gl.iterrows():
                term = str(row.get("term", "")).strip()
                if not term:
                    continue
                for syn in str(row.get("synonyms", "")).split(";"):
                    syn = syn.strip().lower()
                    if syn:
                        self._synonyms[syn] = term
        except ValueError:
            pass

        self._df = df
        self._cache_key = key
        return df

    def _color_surcharge(self, color_type: str) -> float:
        """Read the Garment colour surcharge from price_rules rather than hardcoding."""
        if self._rules is None or not color_type:
            return 0.0
        target = COLOR_RULE_PREFIX + color_type.strip().lstrip(COLOR_RULE_PREFIX)
        for _, row in self._rules.iterrows():
            if str(row.get("rule_name", "")).strip() != target:
                continue
            digits = "".join(c for c in str(row.get("adjustment", "")) if c.isdigit() or c == ".")
            return float(digits) if digits else 0.0
        return 0.0

    def _resolve(self, keyword: str) -> str:
        k = keyword.strip().lower()
        return self._synonyms.get(k, keyword).lower()

    def _candidates(self, df: pd.DataFrame, keyword: str) -> pd.DataFrame:
        """Match on name, then fall back to spec, then to all keyword tokens."""
        term = self._resolve(keyword)
        hit = df[df["_name_lower"].str.contains(term, regex=False)]
        if not hit.empty:
            return hit

        hit = df[df["_spec_lower"].str.contains(term, regex=False)]
        if not hit.empty:
            return hit

        tokens = [t for t in term.split() if len(t) > 1]
        if tokens:
            mask = pd.Series(True, index=df.index)
            for t in tokens:
                mask &= df["_name_lower"].str.contains(t, regex=False)
            hit = df[mask]
            if not hit.empty:
                return hit
        return df.iloc[0:0]

    @staticmethod
    def _pick_tier(rows: pd.DataFrame, quantity: int) -> Optional[pd.Series]:
        """Row whose tier contains the quantity; blank bounds mean unbounded."""
        lo = rows["qty_min"].fillna(0)
        hi = rows["qty_max"].fillna(float("inf"))
        band = rows[(lo <= quantity) & (hi >= quantity)]
        if not band.empty:
            return band.iloc[0]
        # Quantity above every tier: fall back to the largest tier available.
        priced = rows[rows["unit_price_thb"].notna()]
        if priced.empty:
            return rows.iloc[0] if not rows.empty else None
        return priced.sort_values("qty_min").iloc[-1]

    @staticmethod
    def _clean(value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if pd.isna(value):
            return None
        return value

    # ── tools ───────────────────────────────────────────────────────────────

    async def lookup_price(
        self,
        item_name: str,
        quantity: int,
        color_type: Optional[str] = None,
    ) -> str:
        """
        ค้นหาราคาสินค้าสื่อการตลาดจากไฟล์ราคากลาง Y2026

        ใช้เมื่อผู้ใช้สอบถามราคาสินค้าสื่อส่งเสริมการขาย (POSM, งานพิมพ์,
        เสื้อ/สิ่งทอ, พรีเมี่ยม, เรทงานพิมพ์)

        Parameters:
        - item_name: ชื่อรายการ (เช่น "เสื้อโปโล", "ธงปีกนก ไซด์ M", "สติ๊กเกอร์ PVC")
        - quantity: จำนวนที่ต้องการ (เช่น 500, 15000)
        - color_type: (เฉพาะเสื้อ/สิ่งทอ) "อ่อน", "กลาง", หรือ "เข้ม"

        Returns:
        - JSON string ที่มีราคาต่อหน่วย ราคารวม ผู้ขาย และช่วงจำนวนที่ใช้
        """
        try:
            df = self._load()
        except Exception as exc:
            return json.dumps(
                {"found": False, "error": f"ไม่สามารถโหลดไฟล์ราคา: {exc}"},
                ensure_ascii=False,
            )

        rows = self._candidates(df, item_name)
        if rows.empty:
            return json.dumps(
                {
                    "found": False,
                    "message": f"ไม่พบรายการ '{item_name}' ในไฟล์ราคากลาง",
                    "hint": "ลองใช้ search_items เพื่อดูชื่อที่ใกล้เคียง",
                },
                ensure_ascii=False,
            )

        # Prefer the item with the most tiers, so a specific variant beats a stray match.
        best_id = rows["item_id"].value_counts().idxmax()
        item_rows = rows[rows["item_id"] == best_id]
        tier = self._pick_tier(item_rows, quantity)
        if tier is None:
            return json.dumps(
                {"found": False, "message": f"ไม่พบช่วงจำนวนที่ตรงกับ {quantity}"},
                ensure_ascii=False,
            )

        unit = self._clean(tier.get("unit_price_thb"))
        notes = self._clean(tier.get("notes"))

        if unit is None:
            return json.dumps(
                {
                    "found": True,
                    "item_name": tier.get("item_name"),
                    "item_id": tier.get("item_id"),
                    "unit_price": None,
                    "message": "รายการนี้ไม่มีราคาต่อหน่วยตายตัว",
                    "note": notes or "ต้องอ้างอิงราคาตามกฎในไฟล์ราคากลาง",
                },
                ensure_ascii=False,
            )

        unit = float(unit)
        surcharge = 0.0
        if color_type and str(tier.get("category")) == "Garment":
            surcharge = self._color_surcharge(color_type)
            unit += surcharge

        others = self._clean(tier.get("vendor_quotes_json"))
        result = {
            "found": True,
            "item_id": tier.get("item_id"),
            "item_name": tier.get("item_name"),
            "category": tier.get("category"),
            "spec": self._clean(tier.get("spec")),
            "quantity": quantity,
            "unit_price": round(unit, 4),
            "total_price": round(unit * quantity, 2),
            "vendor": self._clean(tier.get("winner_vendor")),
            "tier_info": self._clean(tier.get("qty_label")),
            "color_adjustment": f"+{surcharge:g} บาท (สี{color_type})" if surcharge else "",
            "vat_note": self.valves.vat_note,
            "lead_time": self.valves.lead_time_note,
        }
        if notes:
            result["note"] = notes
        if others:
            result["other_vendor_quotes"] = others
        return json.dumps(result, ensure_ascii=False)

    async def search_items(self, keyword: str) -> str:
        """
        ค้นหาชื่อสินค้าที่ใกล้เคียง ใช้เมื่อไม่แน่ใจชื่อเรียกที่ถูกต้อง

        Parameters:
        - keyword: คำค้น เช่น "ธง", "สติ๊กเกอร์", "เสื้อ"
        """
        try:
            df = self._load()
        except Exception as exc:
            return json.dumps({"error": f"ไม่สามารถโหลดไฟล์ราคา: {exc}"}, ensure_ascii=False)

        rows = self._candidates(df, keyword)
        if rows.empty:
            return json.dumps({"count": 0, "items": []}, ensure_ascii=False)

        out = []
        for item_id, grp in rows.groupby("item_id", sort=False):
            priced = grp[grp["unit_price_thb"].notna()]
            first = grp.iloc[0]
            entry = {
                "item_id": item_id,
                "item_name": first["item_name"],
                "category": first["category"],
                "tiers": int(len(grp)),
            }
            if not priced.empty:
                entry["price_range"] = (
                    f"{priced['unit_price_thb'].min():g}-{priced['unit_price_thb'].max():g} บาท"
                )
            out.append(entry)
            if len(out) >= 15:
                break
        return json.dumps({"count": len(out), "items": out}, ensure_ascii=False)

    async def get_item_details(self, item_name: str) -> str:
        """
        ดูรายละเอียดและทุกช่วงราคาของสินค้าหนึ่งรายการ

        Parameters:
        - item_name: ชื่อรายการที่ต้องการดูรายละเอียด
        """
        try:
            df = self._load()
        except Exception as exc:
            return json.dumps({"error": f"ไม่สามารถโหลดไฟล์ราคา: {exc}"}, ensure_ascii=False)

        rows = self._candidates(df, item_name)
        if rows.empty:
            return json.dumps(
                {"found": False, "message": f"ไม่พบรายการ '{item_name}'"}, ensure_ascii=False
            )

        best_id = rows["item_id"].value_counts().idxmax()
        item_rows = rows[rows["item_id"] == best_id]
        head = item_rows.iloc[0]
        tiers = [
            {
                "qty_label": self._clean(r["qty_label"]),
                "qty_min": self._clean(r["qty_min"]),
                "qty_max": self._clean(r["qty_max"]),
                "unit_price": self._clean(r["unit_price_thb"]),
                "vendor": self._clean(r["winner_vendor"]),
            }
            for _, r in item_rows.iterrows()
        ]
        return json.dumps(
            {
                "found": True,
                "item_id": best_id,
                "item_name": head["item_name"],
                "category": head["category"],
                "spec": self._clean(head["spec"]),
                "size_cm": (
                    f"{self._clean(head['size_w_cm'])}x{self._clean(head['size_h_cm'])}"
                    if self._clean(head["size_w_cm"])
                    else None
                ),
                "tiers": tiers,
                "notes": self._clean(head["notes"]),
                "vat_note": self.valves.vat_note,
                "lead_time": self.valves.lead_time_note,
            },
            ensure_ascii=False,
        )

    async def list_categories(self) -> str:
        """แสดงหมวดหมู่สินค้าทั้งหมดพร้อมจำนวนรายการ"""
        try:
            df = self._load()
        except Exception as exc:
            return json.dumps({"error": f"ไม่สามารถโหลดไฟล์ราคา: {exc}"}, ensure_ascii=False)

        out = [
            {
                "category": cat,
                "category_th": grp["category_th"].iloc[0],
                "items": int(grp["item_id"].nunique()),
                "rows": int(len(grp)),
            }
            for cat, grp in df.groupby("category", sort=False)
        ]
        return json.dumps({"categories": out, "total_items": int(df["item_id"].nunique())},
                          ensure_ascii=False)

    async def health_check(self) -> str:
        """ตรวจสอบว่าไฟล์ราคาโหลดได้และมีข้อมูลครบ"""
        try:
            df = self._load()
        except Exception as exc:
            return json.dumps({"status": "error", "detail": str(exc)}, ensure_ascii=False)

        stat = os.stat(self.valves.excel_path)
        return json.dumps(
            {
                "status": "ok",
                "path": self.valves.excel_path,
                "rows": int(len(df)),
                "items": int(df["item_id"].nunique()),
                "categories": int(df["category"].nunique()),
                "synonyms": len(self._synonyms),
                "rules": 0 if self._rules is None else int(len(self._rules)),
                "file_modified": pd.Timestamp(stat.st_mtime, unit="s").isoformat(),
            },
            ensure_ascii=False,
        )
