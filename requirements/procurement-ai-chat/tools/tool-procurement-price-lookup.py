"""
title: Procurement Price Lookup (Excel Direct)
author: Haadthip
version: 1.0
required_open_webui_version: 0.5.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Procurement Price Lookup Tool (No Azure AI Search)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Reads Trade Marketing Materials price Excel directly using pandas.
No external dependencies beyond pandas (included in OWUI).

Data loaded ONCE on tool init → stays in memory (~5MB).
All lookups are <100ms — pure Python dict/DataFrame access.

Setup:
  1. Place Excel file in OWUI container (e.g. /app/data/prices.xlsx)
  2. Admin Settings → Functions → Add Tool → paste this file
  3. Workspace → Models → select model → enable this tool
"""

import json
import os
import re
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        excel_path: str = Field(
            default="/app/data/Trade Marketing Materials price for Y2026.final.xlsx",
            description="Path to Excel file inside OWUI container",
        )
        synonym_json: str = Field(
            default='{"สติกเกอร์":"สติ๊กเกอร์", "สติ๊กเกอร์":"สติ๊กเกอร์", "ป้ายแขวน":"Shelf Talker", "PP Board":"PP Board", "ไวนิล":"ไวนิล", "พีพีบอร์ด":"PP Board", "โฟมบอร์ด":"Foam Board", "wrap around":"Wrap Around", "arch":"Arch"}',
            description="Synonym mapping (JSON string)",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._data = {}        # {sheet_name: DataFrame}
        self._synonyms = {}    # {variant: canonical}
        self._initialized = False
        self._catalog = []     # Flat catalog for search

    def _init(self):
        """Lazy init — load Excel once"""
        if self._initialized:
            return

        path = self.valves.excel_path
        if not os.path.exists(path):
            # Try relative path
            path = os.path.join(os.path.dirname(__file__), "prices.xlsx")

        xls = pd.ExcelFile(path)
        self._data = {s: pd.read_excel(path, sheet_name=s, header=None)
                      for s in xls.sheet_names}

        # Parse synonyms
        try:
            self._synonyms = json.loads(self.valves.synonym_json)
        except json.JSONDecodeError:
            self._synonyms = {}

        # Build flat catalog for keyword search
        self._build_catalog()

        self._initialized = True

    def _build_catalog(self):
        """Build flat searchable catalog from all sheets"""
        self._catalog = []

        for sheet, df in self._data.items():
            if 'POSM' in sheet:
                parser = self._parse_posm
            elif 'Printing(MKT)' in sheet:
                parser = self._parse_printing_mkt
            elif 'Garment' in sheet:
                parser = self._parse_garment
            elif 'Premium' in sheet:
                parser = self._parse_premium
            elif 'Printing-Rate' in sheet:
                parser = self._parse_printing_rate
            else:
                continue

            items = parser(df)
            for item in items:
                item['sheet'] = sheet
                self._catalog.append(item)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SHEET PARSERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _safe(v, as_type='float'):
        if pd.isna(v): return None
        try:
            return float(v) if as_type == 'float' else str(v).strip()
        except:
            return str(v).strip() if as_type == 'str' else None

    def _parse_posm(self, df):
        items = []
        for idx in range(2, len(df)):
            row = df.iloc[idx]
            if str(row.iloc[0]) != 'POSM': continue
            name = self._safe(row.iloc[2], 'str')
            if not name or name.startswith('*'): continue
            price = self._safe(row.iloc[24])
            vendor = self._safe(row.iloc[26], 'str') or ''
            if price:
                items.append({
                    'item_name': name,
                    'category': 'POSM',
                    'unit_price': price,
                    'vendor': vendor,
                    'qty_tiers': [{'min_qty': 1, 'max_qty': 999999, 'unit_price': price}]
                })
        return items

    def _parse_printing_mkt(self, df):
        items = []
        current = None
        for idx in range(2, len(df)):
            row = df.iloc[idx]
            if str(row.iloc[0]) != 'Printing-mkt': continue
            # Check if new item
            c1 = row.iloc[1]
            c2 = self._safe(row.iloc[2], 'str') or ''
            if c2.startswith('*') or 'เนื่องจาก' in c2: continue
            if pd.notna(c1) and c2:
                if current: items.append(current)
                current = {'item_name': c2, 'category': 'Printing-MKT', 'qty_tiers': []}
                # Get approved price (col 19) and vendor (col 20)
                p = self._safe(row.iloc[19])
                v = self._safe(row.iloc[20], 'str') or ''
                if p: current['unit_price'] = p; current['vendor'] = v
            if current and pd.notna(row.iloc[3]):
                q = int(self._safe(row.iloc[3]) or 0)
                p = self._safe(row.iloc[19])
                v = self._safe(row.iloc[20], 'str') or ''
                if q > 0 and p:
                    current['qty_tiers'].append({'min_qty': q, 'max_qty': 999999, 'unit_price': p, 'vendor': v})
        if current: items.append(current)
        return items

    def _parse_garment(self, df):
        items = []
        current = None
        for idx in range(2, len(df)):
            row = df.iloc[idx]
            if str(row.iloc[0]) != 'Garment': continue
            c1 = row.iloc[1]
            c2 = self._safe(row.iloc[2], 'str') or ''
            if c2.startswith('*'): continue
            if pd.notna(c1) and c2:
                if current: items.append(current)
                current = {'item_name': c2.split('\n')[0], 'category': 'Garment',
                           'qty_tiers': [], 'color_adjust': {'อ่อน': 5, 'กลาง': 10, 'เข้ม': 20}}
                p = self._safe(row.iloc[13]); v = self._safe(row.iloc[14], 'str') or ''
                if p: current['unit_price'] = p; current['vendor'] = v
            if current and pd.notna(row.iloc[3]):
                rng = self._safe(row.iloc[3], 'str')
                if rng and '-' in rng:
                    parts = rng.replace(',', '').split('-')
                    if len(parts) == 2:
                        try:
                            lo, hi = int(parts[0]), int(parts[1])
                            p = self._safe(row.iloc[13])
                            v = self._safe(row.iloc[14], 'str') or ''
                            if p:
                                current['qty_tiers'].append(
                                    {'min_qty': lo, 'max_qty': hi, 'unit_price': p, 'vendor': v})
                        except ValueError:
                            pass
        if current: items.append(current)
        return items

    def _parse_premium(self, df):
        items = []
        current = None
        for idx in range(2, len(df)):
            row = df.iloc[idx]
            if str(row.iloc[0]) != 'Premium-EA&HRC': continue
            c1 = row.iloc[1]; c2 = self._safe(row.iloc[2], 'str') or ''
            if pd.notna(c1) and c2:
                if current: items.append(current)
                current = {'item_name': c2, 'category': 'Premium', 'qty_tiers': []}
                p = self._safe(row.iloc[17]); v = self._safe(row.iloc[19], 'str') or ''
                if p: current['unit_price'] = p; current['vendor'] = v
            if current and pd.notna(row.iloc[7]):
                q = self._safe(row.iloc[7], 'str')
                p = self._safe(row.iloc[17])
                v = self._safe(row.iloc[19], 'str') or ''
                if q and p: current['qty_tiers'].append(
                    {'qty_label': q, 'unit_price': p, 'vendor': v})
        if current: items.append(current)
        return items

    def _parse_printing_rate(self, df):
        items = []
        current = None
        for idx in range(4 if df.shape[0] > 4 else 0, len(df)):
            row = df.iloc[idx]
            c1 = row.iloc[1]; c2 = self._safe(row.iloc[2], 'str') or ''
            if pd.isna(c1) and not c2: continue
            if pd.notna(c1) and c2:
                if current: items.append(current)
                current = {'item_name': c2.split('\n')[0], 'category': 'Printing-Rate', 'qty_tiers': []}
                p = self._safe(row.iloc[16] if row.shape[0] > 16 else row.iloc[-3])
                v = self._safe(row.iloc[17] if row.shape[0] > 17 else row.iloc[-2], 'str') or ''
                if p: current['unit_price'] = p; current['vendor'] = v
            if current and pd.notna(row.iloc[3]):
                rng = self._safe(row.iloc[3], 'str')
                p_col = 16 if row.shape[0] > 16 else row.shape[0] - 3
                p = self._safe(row.iloc[p_col])
                v = self._safe(row.iloc[p_col + 1], 'str') or ''
                if rng and '-' in rng and p:
                    parts = rng.replace(',', '').split('-')
                    if len(parts) == 2:
                        try:
                            lo, hi = int(parts[0]), int(parts[1])
                            current['qty_tiers'].append(
                                {'min_qty': lo, 'max_qty': hi, 'unit_price': p, 'vendor': v})
                        except ValueError:
                            pass
        if current: items.append(current)
        return items

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SEARCH & MATCH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _match_item(self, keyword: str) -> Optional[dict]:
        """Find best matching item by keyword"""
        keyword = keyword.lower().strip()

        # Expand via synonyms
        candidates = [keyword]
        for syn, canon in self._synonyms.items():
            if syn in keyword:
                candidates.append(keyword.replace(syn, canon))

        best_score = 0
        best_item = None

        for item in self._catalog:
            name = item['item_name'].lower()
            for kw in candidates:
                if kw in name:
                    score = len(kw) / len(name)  # Longer match relative to name = better
                    if score > best_score:
                        best_score = score
                        best_item = item

        return best_item

    def _match_tier(self, item: dict, qty: int) -> dict:
        """Find best QTY tier"""
        tiers = item.get('qty_tiers', [])
        if not tiers:
            return {'unit_price': item.get('unit_price', 0), 'vendor': item.get('vendor', '')}

        # Sort by min_qty ascending
        sorted_tiers = sorted(tiers, key=lambda t: t.get('min_qty', 0))
        best = sorted_tiers[0]

        for tier in sorted_tiers:
            mi = tier.get('min_qty', 0)
            if mi <= qty:
                best = tier

        return best

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN TOOL — called by LLM via function calling
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def lookup_price(
        self,
        item_name: str,
        quantity: int,
        color_type: Optional[str] = None,
    ) -> str:
        """
        ค้นหาราคาสินค้าสื่อการตลาดจาก Master Price Excel

        ใช้เมื่อผู้ใช้สอบถามราคาสินค้าสื่อส่งเสริมการขาย (POSM, งานพิมพ์,
        เสื้อ/สิ่งทอ, พรีเมี่ยม) โดยต้องระบุชื่อสินค้าและจำนวน

        Parameters:
        - item_name: ชื่อรายการ (เช่น "สติ๊กเกอร์ 37x28 cm.", "เสื้อยืด",
          "ถังใส่น้ำแข็ง-โค้ก")
        - quantity: จำนวนที่ต้องการ (เช่น 500, 15000)
        - color_type: (เฉพาะเสื้อ/สิ่งทอ) "อ่อน", "กลาง", หรือ "เข้ม"

        Returns:
        - JSON string ที่มีข้อมูลราคา
        """
        self._init()

        # Search item
        item = self._match_item(item_name)
        if not item:
            return json.dumps({
                "found": False,
                "message": f"❌ ไม่พบรายการ '{item_name}' ในระบบ กรุณาลองใช้คำค้นอื่น หรือติดต่อเจ้าหน้าที่จัดซื้อ",
                "suggestions": [i['item_name'][:50] for i in self._catalog[:5]]
            }, ensure_ascii=False)

        # Match QTY tier
        tier = self._match_tier(item, quantity)
        unit_price = tier.get('unit_price', item.get('unit_price', 0))

        # Color adjustment (Garment)
        color_adj = 0
        if color_type and item.get('category') == 'Garment':
            adj_map = item.get('color_adjust', {})
            color_adj = adj_map.get(color_type, 0)
            unit_price += color_adj

        # Calculate
        total = unit_price * quantity

        result = {
            "found": True,
            "item_name": item['item_name'],
            "category": item.get('category', ''),
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total,
            "vendor": tier.get('vendor', item.get('vendor', '')),
            "tier_info": f"QTY {tier.get('min_qty','')}-{tier.get('max_qty','')}" if tier.get('min_qty') else "",
            "color_adjustment": f"+{color_adj} บาท (สี{color_type})" if color_adj else "",
            "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
            "lead_time": "10-15 วันทำการหลังยืนยัน AW"
        }

        return json.dumps(result, ensure_ascii=False)

    async def list_categories(self) -> str:
        """แสดงรายการหมวดหมู่สินค้าทั้งหมด"""
        self._init()
        cats = {}
        for item in self._catalog:
            cat = item.get('category', 'Other')
            cats[cat] = cats.get(cat, 0) + 1
        return json.dumps(cats, ensure_ascii=False)

    async def search_items(self, keyword: str) -> str:
        """ค้นหาสินค้าจาก keyword (ใช้เมื่อไม่แน่ใจชื่อ)"""
        self._init()
        keyword = keyword.lower()
        results = []
        for item in self._catalog:
            if keyword in item['item_name'].lower():
                results.append({
                    'item_name': item['item_name'][:80],
                    'category': item.get('category', ''),
                    'price_range': f"{item.get('unit_price', 'N/A')} บาท"
                })
        return json.dumps(results[:10], ensure_ascii=False)
