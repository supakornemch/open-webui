"""
title: Procurement Price Lookup
author: Haadthip DIO
version: 4.0
required_open_webui_version: 0.5.0

Resolves the price workbook through the Open WebUI Files API — list by name, take
the id, download the bytes — then parses it with pandas. No data in the tool, no
mounted path to keep in sync.

Two resolution paths, tried in order:
  1. In-process: query the Files model + Storage directly. No token needed since the
     tool already runs inside the OWUI backend.
  2. HTTP: GET /api/v1/files/search then /api/v1/files/{id}/content, using api_key.
     Needed only if the tool runs outside the backend process.

Updating prices: upload a new xlsx whose name matches `file_pattern` in OWUI Files.
The newest match wins, so the next query uses it with no valve change and no restart.
"""

import asyncio
import io
import json
import os
import re
import urllib.request
from typing import Optional
from urllib.parse import quote

import pandas as pd
from pydantic import BaseModel, Field

COLOR_RULE_PREFIX = "สี"
SHEET = "price_book"
PUNCT_RE = re.compile(r"[\s\-_.()\[\]/+,]")
DIM_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)")


def _norm_dims(text: str) -> str:
    """'16 x 24' and '16x24' are the same size; the workbook spaces them freely."""
    return DIM_RE.sub(lambda m: f"{m.group(1)}x{m.group(2)}", str(text).lower())


def _squash(text: str) -> str:
    """Drop punctuation and spacing so hyphenation stops blocking a match."""
    return PUNCT_RE.sub("", _norm_dims(text))


def _swap_dims(text: str) -> Optional[str]:
    """'90x60' -> '60x90'. Users quote dimensions in either order."""
    m = DIM_RE.search(text)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    if a == b:
        return None
    return text[: m.start()] + f"{b}x{a}" + text[m.end() :]


class Tools:
    class Valves(BaseModel):
        file_pattern: str = Field(
            default="price-book*.xlsx",
            description="Filename pattern in OWUI Files. Newest match is used.",
        )
        base_url: str = Field(
            default="http://localhost:8080",
            description="OWUI base URL, used only for the HTTP fallback",
        )
        api_key: str = Field(
            default="",
            description="OWUI API key. Only needed if in-process access is unavailable.",
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
        self._source: str = ""

    # ── file resolution ─────────────────────────────────────────────────────

    async def _resolve_internal(self) -> Optional[tuple[str, str, int, bytes]]:
        """Find the file via the Files model and read it straight off Storage."""
        try:
            from open_webui.models.files import Files
            from open_webui.storage.provider import Storage
        except ImportError:
            return None

        matches = await Files.search_files(
            user_id=None, filename=self.valves.file_pattern, skip=0, limit=1000
        )
        if not matches:
            return None

        newest = max(matches, key=lambda f: f.created_at or 0)
        path = await asyncio.to_thread(Storage.get_file, newest.path)
        data = await asyncio.to_thread(lambda: open(path, "rb").read())
        return newest.id, newest.filename, newest.created_at or 0, data

    def _resolve_http(self) -> tuple[str, str, int, bytes]:
        """Same lookup over HTTP, for when the tool runs outside the backend."""
        if not self.valves.api_key:
            raise RuntimeError(
                "เข้าถึงไฟล์ภายในไม่ได้ และยังไม่ได้ตั้งค่า api_key สำหรับเรียกผ่าน HTTP"
            )

        base = self.valves.base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {self.valves.api_key}"}

        url = f"{base}/api/v1/files/search?filename={quote(self.valves.file_pattern)}&content=false"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            listing = json.loads(r.read())
        if not listing:
            raise FileNotFoundError(f"ไม่พบไฟล์ที่ตรงกับ '{self.valves.file_pattern}' ใน OWUI Files")

        newest = max(listing, key=lambda f: f.get("created_at") or 0)
        fid = newest["id"]
        url = f"{base}/api/v1/files/{fid}/content"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
            data = r.read()
        return fid, newest.get("filename", ""), newest.get("created_at") or 0, data

    async def _load(self) -> pd.DataFrame:
        """Resolve the newest matching file and parse it, caching on file identity."""
        resolved = await self._resolve_internal()
        if resolved is not None:
            source = "internal"
        else:
            resolved = await asyncio.to_thread(self._resolve_http)
            source = "http"

        fid, filename, created_at, data = resolved
        key = (fid, created_at, len(data))
        if self._df is not None and self._cache_key == key:
            return self._df

        buf = io.BytesIO(data)
        sheets = pd.ExcelFile(buf).sheet_names
        if SHEET not in sheets:
            raise ValueError(
                f"ไฟล์ '{filename}' ไม่มี sheet '{SHEET}' (พบ: {', '.join(map(str, sheets))})"
            )

        df = pd.read_excel(io.BytesIO(data), sheet_name=SHEET)
        df["_name_lower"] = df["item_name"].fillna("").str.lower().map(_norm_dims)
        df["_spec_lower"] = df["spec"].fillna("").str.lower().map(_norm_dims)
        df["_name_squashed"] = df["item_name"].fillna("").map(_squash)

        self._rules = (
            pd.read_excel(io.BytesIO(data), sheet_name="price_rules")
            if "price_rules" in sheets
            else None
        )

        self._synonyms = {}
        if "glossary" in sheets:
            gl = pd.read_excel(io.BytesIO(data), sheet_name="glossary")
            for _, row in gl.iterrows():
                term = str(row.get("term", "")).strip()
                if not term:
                    continue
                for syn in str(row.get("synonyms", "")).split(";"):
                    syn = syn.strip().lower()
                    if syn:
                        self._synonyms[syn] = term

        self._df = df
        self._cache_key = key
        self._source = f"{source}:{filename}"
        return df

    # ── matching ────────────────────────────────────────────────────────────

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

    def _synonym_terms(self, keyword: str) -> list[str]:
        """Search terms to try, best first.

        Users rarely type a bare glossary word — it arrives as "ป้ายโฟมบอร์ดไดคัด 45x45",
        so a whole-keyword lookup alone never fires. Thai also runs words together
        without spaces, so the canonical term is tried on its own too.
        """
        lowered = keyword.strip().lower()
        terms = [lowered]

        if lowered in self._synonyms:
            terms.insert(0, self._synonyms[lowered].lower())
            return terms

        # Longest synonym first, so a specific phrase wins over a substring of it.
        for syn in sorted(self._synonyms, key=len, reverse=True):
            if syn not in lowered:
                continue
            canonical = self._synonyms[syn].lower()
            # 'โปโล' is a synonym of 'เสื้อโปโล'; substituting inside it yields junk.
            if canonical in lowered:
                break
            terms.insert(0, lowered.replace(syn, canonical))
            terms.insert(1, canonical)
            break
        return terms

    def _match_one(self, df: pd.DataFrame, term: str) -> pd.DataFrame:
        """Name, then spec, then squashed name, then every token in the name."""
        hit = df[df["_name_lower"].str.contains(term, regex=False)]
        if not hit.empty:
            return hit

        hit = df[df["_spec_lower"].str.contains(term, regex=False)]
        if not hit.empty:
            return hit

        # 'กล่องทิชชูโค้ก' should reach 'กล่องทิชชู-โค้ก'; the workbook punctuates freely.
        squashed = _squash(term)
        if squashed:
            hit = df[df["_name_squashed"].str.contains(squashed, regex=False)]
            if not hit.empty:
                return hit

        # Keep only tokens some name actually contains, else one stray word
        # ("สีอ่อน", which lives in spec) zeroes out the whole AND.
        tokens = [
            t
            for t in term.split()
            if len(t) > 1 and df["_name_lower"].str.contains(t, regex=False).any()
        ]
        if tokens:
            mask = pd.Series(True, index=df.index)
            for t in tokens:
                mask &= df["_name_lower"].str.contains(t, regex=False)
            hit = df[mask]
            if not hit.empty:
                return hit
        return df.iloc[0:0]

    def _candidates(self, df: pd.DataFrame, keyword: str) -> pd.DataFrame:
        for term in self._synonym_terms(keyword):
            term = _norm_dims(term)
            hit = self._match_one(df, term)
            if not hit.empty:
                return hit
            swapped = _swap_dims(term)
            if swapped:
                hit = self._match_one(df, swapped)
                if not hit.empty:
                    return hit
        return df.iloc[0:0]

    @staticmethod
    def _pick_tier(rows: pd.DataFrame, quantity: int) -> tuple[Optional[pd.Series], bool]:
        """Row whose tier contains the quantity; blank bounds mean unbounded.

        Second element is True when the quantity fell outside every tier and the
        price is therefore a nearest-tier fallback, not a quoted price.
        """
        lo = rows["qty_min"].fillna(0)
        hi = rows["qty_max"].fillna(float("inf"))
        band = rows[(lo <= quantity) & (hi >= quantity)]
        if not band.empty:
            return band.iloc[0], False
        priced = rows[rows["unit_price_thb"].notna()]
        if priced.empty:
            return (rows.iloc[0] if not rows.empty else None), False
        nearest = priced.sort_values("qty_min").iloc[0 if quantity < lo.min() else -1]
        return nearest, True

    @staticmethod
    def _clean(value):
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        return value

    def _fail(self, exc: Exception) -> str:
        return json.dumps({"found": False, "error": f"ไม่สามารถโหลดไฟล์ราคา: {exc}"},
                          ensure_ascii=False)

    # ── tools ───────────────────────────────────────────────────────────────

    async def lookup_price(
        self,
        item_name: str,
        quantity: int,
        color_type: Optional[str] = None,
    ) -> str:
        """
        ค้นหาราคาสินค้าสื่อการตลาดจากไฟล์ราคากลางที่อัปโหลดไว้ใน OWUI Files

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
            df = await self._load()
        except Exception as exc:
            return self._fail(exc)

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
        tier, out_of_range = self._pick_tier(item_rows, quantity)
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
                    "item_id": tier.get("item_id"),
                    "item_name": tier.get("item_name"),
                    "unit_price": None,
                    "message": "รายการนี้ไม่มีราคาต่อหน่วยตายตัว",
                    "note": notes or "ต้องอ้างอิงราคาตามกฎในไฟล์ราคากลาง",
                    "source_file": self._source,
                },
                ensure_ascii=False,
            )

        unit = float(unit)
        surcharge = 0.0
        if color_type and str(tier.get("category")) == "Garment":
            surcharge = self._color_surcharge(color_type)
            unit += surcharge

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
            "source_file": self._source,
        }
        if notes:
            result["note"] = notes
        if out_of_range:
            result["quantity_out_of_range"] = (
                f"จำนวน {quantity:,} อยู่นอกช่วงที่ประมูลไว้ ราคานี้มาจากช่วง '{self._clean(tier.get('qty_label'))}' "
                "ไม่ใช่ราคาที่ยืนยันได้ ต้องขอใบเสนอราคาจากฝ่ายจัดซื้อ"
            )
        others = self._clean(tier.get("vendor_quotes_json"))
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
            df = await self._load()
        except Exception as exc:
            return self._fail(exc)

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
            df = await self._load()
        except Exception as exc:
            return self._fail(exc)

        rows = self._candidates(df, item_name)
        if rows.empty:
            return json.dumps(
                {"found": False, "message": f"ไม่พบรายการ '{item_name}'"}, ensure_ascii=False
            )

        best_id = rows["item_id"].value_counts().idxmax()
        item_rows = rows[rows["item_id"] == best_id]
        head = item_rows.iloc[0]
        width = self._clean(head["size_w_cm"])
        return json.dumps(
            {
                "found": True,
                "item_id": best_id,
                "item_name": head["item_name"],
                "category": head["category"],
                "spec": self._clean(head["spec"]),
                "size_cm": f"{width}x{self._clean(head['size_h_cm'])}" if width else None,
                "tiers": [
                    {
                        "qty_label": self._clean(r["qty_label"]),
                        "qty_min": self._clean(r["qty_min"]),
                        "qty_max": self._clean(r["qty_max"]),
                        "unit_price": self._clean(r["unit_price_thb"]),
                        "vendor": self._clean(r["winner_vendor"]),
                    }
                    for _, r in item_rows.iterrows()
                ],
                "notes": self._clean(head["notes"]),
                "vat_note": self.valves.vat_note,
                "lead_time": self.valves.lead_time_note,
                "source_file": self._source,
            },
            ensure_ascii=False,
        )

    async def list_categories(self) -> str:
        """แสดงหมวดหมู่สินค้าทั้งหมดพร้อมจำนวนรายการ"""
        try:
            df = await self._load()
        except Exception as exc:
            return self._fail(exc)

        return json.dumps(
            {
                "categories": [
                    {
                        "category": cat,
                        "category_th": grp["category_th"].iloc[0],
                        "items": int(grp["item_id"].nunique()),
                        "rows": int(len(grp)),
                    }
                    for cat, grp in df.groupby("category", sort=False)
                ],
                "total_items": int(df["item_id"].nunique()),
                "source_file": self._source,
            },
            ensure_ascii=False,
        )

    async def health_check(self) -> str:
        """ตรวจสอบว่าหาไฟล์ราคาใน OWUI Files เจอและ parse ได้"""
        try:
            df = await self._load()
        except Exception as exc:
            return json.dumps(
                {"status": "error", "pattern": self.valves.file_pattern, "detail": str(exc)},
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "status": "ok",
                "source": self._source,
                "file_id": self._cache_key[0] if self._cache_key else None,
                "rows": int(len(df)),
                "items": int(df["item_id"].nunique()),
                "categories": int(df["category"].nunique()),
                "synonyms": len(self._synonyms),
                "rules": 0 if self._rules is None else int(len(self._rules)),
            },
            ensure_ascii=False,
        )

    async def list_price_files(self) -> str:
        """แสดงไฟล์ราคาทั้งหมดที่อัปโหลดไว้ใน OWUI Files พร้อมวันที่ เพื่อตรวจว่าใช้ไฟล์ล่าสุด"""
        try:
            from open_webui.models.files import Files

            matches = await Files.search_files(
                user_id=None, filename=self.valves.file_pattern, skip=0, limit=1000
            )
            files = [
                {"id": f.id, "filename": f.filename, "created_at": f.created_at}
                for f in matches
            ]
        except ImportError:
            try:
                _, filename, created_at, _ = await asyncio.to_thread(self._resolve_http)
                files = [{"filename": filename, "created_at": created_at}]
            except Exception as exc:
                return self._fail(exc)

        files.sort(key=lambda f: f.get("created_at") or 0, reverse=True)
        for i, f in enumerate(files):
            ts = f.get("created_at")
            if ts:
                f["uploaded"] = pd.Timestamp(ts, unit="s").isoformat()
            f["in_use"] = i == 0
        return json.dumps(
            {"pattern": self.valves.file_pattern, "count": len(files), "files": files},
            ensure_ascii=False,
        )
