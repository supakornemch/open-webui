"""
title: Procurement Price Lookup (Excel Live)
author: Haadthip DIO
version: 2.0
required_open_webui_version: 0.5.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Procurement Price Lookup — Excel Live Download
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Downloads Excel from Azure Blob (SAS URL) → pandas parse → deterministic lookup.
Requires: pandas, openpyxl, httpx (added to Dockerfile.teams).

User Update Flow:
  1. Procurement uploads new Excel via OWUI Files
  2. Admin updates valve "file_id" (or regenerates SAS URL)
  3. Next query → auto-downloads new Excel → uses new prices
"""

import json
import io
from typing import Optional

import pandas as pd
import httpx
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        excel_url: str = Field(
            default="https://staentchatdoc.blob.core.windows.net/open-webui-files/procurement-prices/latest.xlsx?...",
            description="SAS URL to Excel — FIXED path, overwrite blob to update prices. No valve change needed!",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._cache = {}  # {sheet_name: DataFrame}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DATA LOADING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load(self) -> dict:
        """Download Excel from Blob → parse with pandas → cache"""
        if self._cache:
            return self._cache

        url = self.valves.excel_url
        if not url:
            raise ValueError("excel_url valve is empty — set SAS URL")

        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()

        xls = pd.ExcelFile(io.BytesIO(resp.content))
        dfs = {}
        for sn in xls.sheet_names:
            if any(k in sn for k in ["POSM", "Printing(MKT)", "Garment", "Premium"]):
                dfs[sn] = pd.read_excel(io.BytesIO(resp.content), sheet_name=sn, header=None)
        self._cache = dfs
        return dfs

    @staticmethod
    def _s(v, t="float"):
        """Safe cell value extraction"""
        if pd.isna(v):
            return None
        try:
            return float(v) if t == "float" else str(v).strip()
        except (ValueError, TypeError):
            return str(v).strip() if t == "str" else None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN TOOL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def lookup_price(
        self, item_name: str, quantity: int, color_type: Optional[str] = None
    ) -> str:
        """
        ค้นหาราคาจาก Excel Master (download สดจาก Blob → pandas)

        ใช้เมื่อผู้ใช้สอบถามราคาสินค้าสื่อการตลาด
        - item_name: ชื่อรายการ (เช่น "สติ๊กเกอร์", "ถังใส่น้ำแข็ง-โค้ก", "เสื้อยืด")
        - quantity: จำนวนที่ต้องการ
        - color_type: (เฉพาะเสื้อ) "อ่อน", "กลาง", "เข้ม"
        """
        try:
            dfs = self._load()
        except Exception as e:
            return json.dumps(
                {"found": False, "error": f"ไม่สามารถโหลดไฟล์ราคา: {e}"},
                ensure_ascii=False,
            )

        for sheet_name, df in dfs.items():
            cat_map = {
                "1.POSM(MKT)": "POSM",
                "2.Printing(MKT)": "Printing-mkt",
                "3.Garment": "Garment",
                "4.สรุปPremium": "Premium-EA&HRC",
            }
            cat = cat_map.get(sheet_name, "")
            if not cat:
                continue

            current_item = ""
            tiers = []

            for idx in range(2, len(df)):
                row = df.iloc[idx]

                # Check category column
                if str(row.iloc[0]) != cat:
                    continue

                # Check if new item row (has item ID + name)
                item_id = row.iloc[1]
                item_name_cell = self._s(row.iloc[2], "str") if pd.notna(row.iloc[2]) else ""
                if isinstance(item_name_cell, str) and (
                    item_name_cell.startswith("*") or "เนื่องจาก" in item_name_cell
                ):
                    continue

                if pd.notna(item_id) and item_name_cell:
                    # Save previous item's tiers
                    if current_item and tiers:
                        # We've already processed this item; continue
                        pass

                    # Start new item
                    current_item = item_name_cell.split("\n")[0].strip()[:80]

                    if item_name.lower() not in current_item.lower():
                        current_item = ""  # Not the item we're looking for
                        tiers = []
                        continue

                    tiers = []

                    # ── POSM: single price ──
                    if sheet_name == "1.POSM(MKT)":
                        p = self._s(row.iloc[24])
                        v = self._s(row.iloc[26], "str")
                        if p:
                            return json.dumps(
                                {
                                    "found": True,
                                    "item": current_item,
                                    "unit": p,
                                    "total": p * quantity,
                                    "vendor": str(v) if v else "",
                                    "source": "Excel Live (POSM)",
                                },
                                ensure_ascii=False,
                            )

                    # ── Premium: single-ish price ──
                    elif sheet_name == "4.สรุปPremium":
                        p = self._s(row.iloc[17])
                        v = self._s(row.iloc[19], "str")
                        if p:
                            return json.dumps(
                                {
                                    "found": True,
                                    "item": current_item,
                                    "unit": p,
                                    "total": p * quantity,
                                    "vendor": str(v) if v else "",
                                    "source": "Excel Live (Premium)",
                                },
                                ensure_ascii=False,
                            )

                    continue  # Go to next row for tier data

                # ── Tier rows (QTY + price) ──
                if not current_item:
                    continue

                # Printing(MKT): QTY in col 3, price in col 19
                if sheet_name == "2.Printing(MKT)":
                    qty_cell = row.iloc[3]
                    if pd.notna(qty_cell):
                        p = self._s(row.iloc[19])
                        v = self._s(row.iloc[20], "str")
                        if p and float(qty_cell) > 0:
                            tiers.append(
                                {
                                    "tier": int(float(qty_cell)),
                                    "unit": p,
                                    "vendor": str(v) if v else "",
                                }
                            )

                # Garment: QTY range in col 3, price in col 13
                elif sheet_name == "3.Garment":
                    qty_range = self._s(row.iloc[3], "str") if pd.notna(row.iloc[3]) else ""
                    if qty_range and "-" in qty_range:
                        parts = qty_range.replace(",", "").split("-")
                        if len(parts) == 2:
                            p = self._s(row.iloc[13])
                            v = self._s(row.iloc[14], "str")
                            if p:
                                tiers.append(
                                    {
                                        "lo": int(parts[0]),
                                        "hi": int(parts[1]),
                                        "unit": p,
                                        "vendor": str(v) if v else "",
                                    }
                                )

            # ── After scanning all rows, match QTY tier ──
            if not tiers or not current_item:
                continue

            # Printing tier matching (exact QTY)
            if sheet_name == "2.Printing(MKT)":
                best = tiers[0]
                for t in sorted(tiers, key=lambda x: x["tier"]):
                    if t["tier"] <= quantity:
                        best = t
                return json.dumps(
                    {
                        "found": True,
                        "item": current_item,
                        "unit": best["unit"],
                        "total": best["unit"] * quantity,
                        "vendor": best.get("vendor", ""),
                        "tier": best["tier"],
                        "source": "Excel Live (Printing)",
                    },
                    ensure_ascii=False,
                )

            # Garment tier matching (range QTY + color)
            elif sheet_name == "3.Garment":
                adj = {"อ่อน": 5, "กลาง": 10, "เข้ม": 20}.get(color_type, 0)
                for t in tiers:
                    if t["lo"] <= quantity <= t["hi"]:
                        return json.dumps(
                            {
                                "found": True,
                                "item": current_item,
                                "unit": t["unit"] + adj,
                                "total": (t["unit"] + adj) * quantity,
                                "vendor": t.get("vendor", ""),
                                "color_adj": f"+{adj}" if adj else "",
                                "source": "Excel Live (Garment)",
                            },
                            ensure_ascii=False,
                        )

        return json.dumps(
            {"found": False, "message": f"ไม่พบ '{item_name}' ในระบบ"},
            ensure_ascii=False,
        )

    async def health_check(self) -> str:
        """ตรวจสอบว่า Tool พร้อมใช้งาน"""
        try:
            dfs = self._load()
            total_items = sum(len(df) for df in dfs.values())
            return json.dumps(
                {
                    "status": "ok",
                    "sheets": len(dfs),
                    "rows": total_items,
                    "engine": "pandas + httpx",
                    "source": "Azure Blob (SAS)",
                }
            )
        except Exception as e:
            return json.dumps({"status": "error", "detail": str(e)})
