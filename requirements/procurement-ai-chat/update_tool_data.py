"""
อัปเดต procurement_price_lookup tool + system prompt บน OWUI
- Token-based fuzzy matching (ค้นหาด้วย keyword สั้นๆ ก็เจอ)
- search_items() สำหรับค้นแบบกว้าง
- อัปเดตทั้ง tool code และ model system prompt

Usage:
    python update_tool_data.py [--dry-run]
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "https://genie.haadthip.com"
API_KEY = "sk-5ef8fdfafc824bf1bf582a6049bbd56c"
TOOL_ID = "procurement_price_lookup"
MODEL_ID = "procurement-ai-v1"
JSON_DIR = Path(__file__).parent / "json"


def api(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body[:500]}")
        sys.exit(1)


def load_json(filename):
    p = JSON_DIR / filename
    if not p.exists():
        print(f"  WARNING: Missing {p}")
        return []
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Data converters (same as before) ───────────────────────────────

def convert_posm(items):
    out = []
    for it in items:
        out.append({
            "n": it["item_name"], "t": [],
            "p": it["approved_price_per_unit"], "v": it["approved_vendor"],
        })
    return out


def convert_printing_mkt(items):
    out = []
    for it in items:
        tiers = []
        for t in it.get("price_tiers", []):
            qty_val = t.get("qty", "")
            if qty_val:
                # Parse quantity: "500", "1000", "1-10", "1,001-1,500"
                qty_str = str(qty_val).replace(",", "").strip()
                if "-" in qty_str:
                    # Range: use start value for tier comparison
                    parts = qty_str.split("-")
                    try:
                        qty_start = int(parts[0].strip())
                    except ValueError:
                        qty_start = 0
                else:
                    try:
                        qty_start = int(qty_str)
                    except ValueError:
                        qty_start = 0
                tiers.append({"q": qty_start, "p": t["unit_price"]})
        out.append({
            "n": it["item_name"], "t": tiers,
            "p": it.get("approved_price_per_unit", 0),
            "v": it.get("approved_vendor", ""),
        })
    return out


def convert_garment(items):
    out = []
    for it in items:
        tiers = []
        for t in it.get("price_tiers", []):
            qty_range = t.get("qty_range", "")
            lo, hi = parse_range(qty_range)
            if lo is not None:
                tiers.append({"lo": lo, "hi": hi, "p": t["unit_price"]})
        out.append({
            "n": it["item_name"], "t": tiers,
            "p": it.get("approved_price_per_unit", 0),
            "v": it.get("approved_vendor", ""),
        })
    return out


def convert_premium(items):
    out = []
    for it in items:
        tiers = []
        for t in it.get("price_tiers", []):
            qty_str = str(t.get("qty", ""))
            tiers.append({"q": qty_str, "p": t["unit_price"]})
        out.append({
            "n": it["item_name"], "t": tiers,
            "p": it.get("approved_price_per_unit", 0),
            "v": it.get("approved_vendor", ""),
        })
    return out


def parse_range(s):
    s = str(s).strip().replace(",", "").replace(" ", "")
    if "-" in s:
        parts = s.split("-")
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None, None
    return None, None


# ─── Improved Tool Code ─────────────────────────────────────────────

TOOL_CODE = (
    'import json\n'
    'from typing import Optional\n'
    'from pydantic import BaseModel, Field\n'
    '\n'
    'class Tools:\n'
    '    class Valves(BaseModel):\n'
    '        price_data: str = Field(\n'
    '            default=__PRICE_DATA_PLACEHOLDER__,\n'
    '            description="Price data JSON Y2026 (UTF-8)"\n'
    '        )\n'
    '\n'
    '    def __init__(self):\n'
    '        self.valves = self.Valves()\n'
    '        self._data = None\n'
    '        # Synonym map: common user terms -> database terms\n'
    '        self._synonyms = {\n'
    '            "\u0e42\u0e1f\u0e21\u0e1a\u0e2d\u0e23\u0e4c\u0e14": "pp board",\n'
    '            "\u0e44\u0e14\u0e04\u0e31\u0e14": "\u0e44\u0e14\u0e04\u0e31\u0e17",\n'
    '            "\u0e21\u0e34\u0e25": "mm",\n'
    '            "\u0e42\u0e04\u0e49\u0e01": "\u0e42\u0e04\u0e49\u0e01 \u0e42\u0e04\u0e04\u0e32-\u0e42\u0e04\u0e25\u0e48\u0e32",\n'
    '            "\u0e1b\u0e23\u0e34\u0e49\u0e19\u0e17\u0e4c": "\u0e1e\u0e34\u0e21\u0e1e\u0e4c",\n'
    '            "foam board": "pp board",\n'
    '            "foamboard": "pp board",\n'
    '            "\u0e25\u0e49\u0e2d\u0e21\u0e01\u0e2d\u0e07": "wrap around",\n'
    '            "\u0e1b\u0e49\u0e32\u0e22\u0e25\u0e49\u0e2d\u0e21\u0e01\u0e2d\u0e07": "wrap around",\n'
    '        }\n'
    '\n'
    '    def _expand_synonyms(self, text: str) -> str:\n'
    '        """Expand common Thai synonyms to database terms for better matching."""\n'
    '        t = text.lower()\n'
    '        for user_term, db_term in self._synonyms.items():\n'
    '            if user_term in t and db_term not in t:\n'
    '                t += " " + db_term\n'
    '        return t\n'
    '\n'
    '    def _load(self):\n'
    '        if self._data: return self._data\n'
    '        self._data = json.loads(self.valves.price_data)\n'
    '        return self._data\n'
    '\n'
    '    def _tokenize(self, text: str):\n'
    '        """Split text into tokens. Expands dimension tokens (NxM) into component parts for fuzzy matching."""\n'
    '        import re\n'
    '        raw = re.split(r"[\\s,/.()\\-]+", text.lower())\n'
    '        noise = {"for","and","the","with","pdf","file","2026","y2026","\u0e01\u0e32\u0e23","\u0e08\u0e30","\u0e43\u0e2b\u0e49","\u0e14\u0e49\u0e27\u0e22","\u0e40\u0e1e\u0e37\u0e48\u0e2d","\u0e2d\u0e22\u0e48\u0e32\u0e07","\u0e40\u0e1b\u0e47\u0e19","\u0e17\u0e35\u0e48","\u0e21\u0e35"}\n'
    '        tokens = []\n'
    '        for t in raw:\n'
    '            if len(t) < 2 or t in noise:\n'
    '                continue\n'
    '            tokens.append(t)\n'
    '            # Dimension expansion: "80x100" -> also add "80", "100", and sorted "80x100"\n'
    '            m = re.match(r"^(\\d+)\\s*[x\\u00d7]\\s*(\\d+)$", t)\n'
    '            if m:\n'
    '                a, b = m.group(1), m.group(2)\n'
    '                if a not in tokens: tokens.append(a)\n'
    '                if b not in tokens: tokens.append(b)\n'
    '                # Sorted version for swapped-dimension matching (90x60 -> 60x90)\n'
    '                nums = sorted([a, b], key=int)\n'
    '                sd = f"{nums[0]}x{nums[1]}"\n'
    '                if sd != t and sd not in tokens:\n'
    '                    tokens.append(sd)\n'
    '        return tokens\n'
    '\n'
    '    def _is_dim_token(self, t: str) -> bool:\n'
    '        """Check if token is dimension-like (NxM pattern or standalone number)."""\n'
    '        import re\n'
    '        if re.match(r"^\\d+\\s*[x\\u00d7]\\s*\\d+$", t):\n'
    '            return True\n'
    '        # Standalone numbers (2-5 digits) that could be dimensions\n'
    '        if t.isdigit() and 2 <= len(t) <= 5:\n'
    '            return True\n'
    '        return False\n'
    '\n'
    '    def _match_score(self, query: str, item_name: str):\n'
    '        """\n'
    '        Dimension-aware fuzzy match score 0.0-1.0.\n'
    '        Automatically expands synonyms before matching.\n'
    '        """\n'
    '        query = self._expand_synonyms(query)\n'
    '        q_tokens = self._tokenize(query)\n'
    '        n_tokens = self._tokenize(item_name)\n'
    '        if not q_tokens:\n'
    '            return 0.0\n'
    '\n'
    '        # Separate dimension tokens from text tokens\n'
    '        q_dims = [t for t in q_tokens if self._is_dim_token(t)]\n'
    '        n_dims = [t for t in n_tokens if self._is_dim_token(t)]\n'
    '        q_text = [t for t in q_tokens if t not in q_dims]\n'
    '        n_text = [t for t in n_tokens if t not in n_dims]\n'
    '\n'
    '        # Text token scoring (proportional matching)\n'
    '        matched_text = 0.0\n'
    '        for qt in q_text:\n'
    '            best = 0.0\n'
    '            for nt in n_text:\n'
    '                if qt == nt:\n'
    '                    best = 1.0\n'
    '                    break\n'
    '                elif qt in nt:\n'
    '                    best = max(best, len(qt) / len(nt))\n'
    '                elif nt in qt and len(nt) >= 3:\n'
    '                    best = max(best, len(nt) / len(qt))\n'
    '            matched_text += best\n'
    '\n'
    '        # Dimension scoring: exact number overlap\n'
    '        dim_score = 1.0  # No dimensions in query = no penalty\n'
    '        if q_dims:\n'
    '            q_set = set(q_dims)\n'
    '            n_set = set(n_dims)\n'
    '            if n_set:\n'
    '                overlap = q_set & n_set\n'
    '                dim_score = len(overlap) / max(len(q_set), 1)\n'
    '            else:\n'
    '                dim_score = 0.0  # Query has dims but item has none\n'
    '\n'
    '        text_score = matched_text / max(len(q_text), 1) if q_text else 0.0\n'
    '\n'
    '        # Full query substring bonus\n'
    '        if query.lower() in item_name.lower():\n'
    '            text_score = max(text_score, 1.0)\n'
    '\n'
    '        # Combined: 70% text + 30% dimension\n'
    '        return 0.7 * text_score + 0.3 * dim_score\n'
    '\n'
    '    def _find_best(self, query: str, sheet_filter: Optional[str] = None):\n'
    '        """Find best matching item across all sheets. Returns (sheet, item, score)."""\n'
    '        data = self._load()\n'
    '        best_score = 0.0\n'
    '        best_result = None\n'
    '        all_matches = []\n'
    '        for sn, items in data.items():\n'
    '            if sheet_filter and sheet_filter not in sn:\n'
    '                continue\n'
    '            for item in items:\n'
    '                nm = item.get("n", "")\n'
    '                score = self._match_score(query, nm)\n'
    '                if score > 0:\n'
    '                    all_matches.append((sn, item, score))\n'
    '                if score > best_score:\n'
    '                    best_score = score\n'
    '                    best_result = (sn, item, score)\n'
    '        # Sort all_matches by score desc\n'
    '        all_matches.sort(key=lambda x: x[2], reverse=True)\n'
    '        return best_result, all_matches[:10]\n'
    '\n'
    '    async def search_items(self, query: str, limit: int = 10) -> str:\n'
    '        """\n'
    '        Fuzzy search for items by keyword(s).\n'
    '        Use short Thai or English keywords like "\u0e23\u0e48\u0e21\u0e42\u0e04\u0e49\u0e01", "A4", "\u0e40\u0e2a\u0e37\u0e49\u0e2d\u0e42\u0e1b\u0e42\u0e25".\n'
    '        Returns top matching items with scores, categories, and prices.\n'
    '        For composite jobs (e.g. print+bind+laminate), call multiple times with different keywords.\n'
    '        """\n'
    '        _, matches = self._find_best(query)\n'
    '        if not matches:\n'
    '            return json.dumps({"found": False, "query": query, "hint": "\u0e25\u0e2d\u0e07\u0e43\u0e0a\u0e49 keyword \u0e2a\u0e31\u0e49\u0e19\u0e46 \u0e40\u0e0a\u0e48\u0e19 \u0e23\u0e48\u0e21\u0e42\u0e04\u0e49\u0e01, A4, \u0e40\u0e2a\u0e37\u0e49\u0e2d\u0e22\u0e37\u0e14"}, ensure_ascii=False)\n'
    '        results = []\n'
    '        for sn, item, score in matches[:limit]:\n'
    '            results.append({\n'
    '                "sheet": sn,\n'
    '                "item": item["n"],\n'
    '                "score": round(score, 2),\n'
    '                "unit_price": item.get("p", 0),\n'
    '                "vendor": item.get("v", ""),\n'
    '                "tiers": item.get("t", [])[:5],\n'
    '            })\n'
    '        return json.dumps({"found": True, "count": len(results), "results": results}, ensure_ascii=False)\n'
    '\n'
    '    async def lookup_price(self, item_name: str, quantity: int, color_type: Optional[str] = None) -> str:\n'
    '        """\n'
    '        Search price from embedded JSON.\n'
    '        Use SHORT keywords like "\u0e23\u0e48\u0e21\u0e42\u0e04\u0e49\u0e01 36 \u0e19\u0e34\u0e49\u0e27", "Sale kit A4", "A4 230g".\n'
    '        Do NOT pass long descriptions. Break compound requests into separate calls.\n'
    '        """\n'
    '        # Fuzzy match\n'
    '        best, _ = self._find_best(item_name)\n'
    '        if not best:\n'
    '            return json.dumps({"found": False, "query": item_name, "hint": "\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23 \u0e25\u0e2d\u0e07\u0e43\u0e0a\u0e49 keyword \u0e2a\u0e31\u0e49\u0e19\u0e46 \u0e2b\u0e23\u0e37\u0e2d\u0e43\u0e0a\u0e49 search_items \u0e04\u0e49\u0e19\u0e2b\u0e32\u0e01\u0e48\u0e2d\u0e19"}, ensure_ascii=False)\n'
    '        sn, item, score = best\n'
    '        nm = item["n"]\n'
    '        p = item.get("p", 0)\n'
    '        v = item.get("v", "")\n'
    '        tiers = item.get("t", [])\n'
    '\n'
    '        # Determine pricing based on sheet type\n'
    '        if "POSM" in sn:\n'
    '            return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": p, "total": p * quantity, "vendor": v, "source": "Excel>JSON"}, ensure_ascii=False)\n'
    '\n'
    '        elif "Printing(MKT)" in sn or "Printing-Rate" in sn:\n'
    '            if tiers:\n'
    '                sorted_tiers = sorted(tiers, key=lambda x: x["q"])\n'
    '                best_tier = sorted_tiers[0]\n'
    '                for t in sorted_tiers:\n'
    '                    if t["q"] <= quantity:\n'
    '                        best_tier = t\n'
    '                return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": best_tier["p"], "total": best_tier["p"] * quantity, "vendor": v, "tier_used": best_tier["q"], "source": "Excel>JSON"}, ensure_ascii=False)\n'
    '            else:\n'
    '                return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": p, "total": p * quantity, "vendor": v, "source": "Excel>JSON"}, ensure_ascii=False)\n'
    '\n'
    '        elif "Garment" in sn:\n'
    '            adj = {"\u0e2d\u0e48\u0e2d\u0e19": 5, "\u0e01\u0e25\u0e32\u0e07": 10, "\u0e40\u0e02\u0e49\u0e21": 20}.get(color_type, 0)\n'
    '            for t in tiers:\n'
    '                lo = t.get("lo", 0)\n'
    '                hi = t.get("hi", 999999)\n'
    '                if lo <= quantity <= hi:\n'
    '                    up = t["p"] + adj\n'
    '                    return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": up, "total": up * quantity, "vendor": v, "color_adj": f"+{adj}" if adj else "", "source": "Excel>JSON"}, ensure_ascii=False)\n'
    '            if tiers:\n'
    '                t = tiers[-1]\n'
    '                up = t["p"] + adj\n'
    '                return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": up, "total": up * quantity, "source": "Excel>JSON"}, ensure_ascii=False)\n'
    '            return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": p, "total": p * quantity, "vendor": v, "source": "Excel>JSON (no tier match)"}, ensure_ascii=False)\n'
    '\n'
    '        elif "Premium" in sn:\n'
    '            if tiers:\n'
    '                best_tier = tiers[0]\n'
    '                for t in tiers:\n'
    '                    try:\n'
    '                        tq = int(str(t["q"]).replace(",", ""))\n'
    '                    except:\n'
    '                        tq = 0\n'
    '                    if tq <= quantity:\n'
    '                        best_tier = t\n'
    '                return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": best_tier["p"], "total": best_tier["p"] * quantity, "vendor": v, "tier_used": best_tier["q"], "source": "Excel>JSON"}, ensure_ascii=False)\n'
    '            return json.dumps({"found": True, "match_score": round(score,2), "item": nm, "unit": p, "total": p * quantity, "vendor": v, "source": "Excel>JSON"}, ensure_ascii=False)\n'
    '\n'
    '        return json.dumps({"found": False, "hint": f"Unknown sheet type: {sn}"}, ensure_ascii=False)\n'
    '\n'
    '    async def health_check(self) -> str:\n'
    '        try:\n'
    '            data = self._load()\n'
    '            total = sum(len(v) for v in data.values())\n'
    '            sheets = list(data.keys())\n'
    '            return json.dumps({"status": "ok", "items": total, "sheets": sheets, "source": "Excel>JSON embedded"}, ensure_ascii=False)\n'
    '        except Exception as e:\n'
    '            return json.dumps({"status": "error", "detail": str(e)})\n'
)

# ─── System Prompt ─────────────────────────────────────────────────

SYSTEM_PROMPT = """คุณคือ Procurement AI ผู้ช่วยจัดซื้อสื่อการตลาดของ Haadthip ประจำปี 2026
คุณมี tool สำหรับค้นหาราคาจากฐานข้อมูลราคากลางที่ผ่านการประมูลแล้ว

## คำแนะนำในการใช้ tool
1. **ใช้คำค้นสั้นๆ** — ห้ามส่งคำอธิบายยาวๆ เข้าไปใน tool ให้แยก keyword สำคัญออกมา เช่น:
   - "ร่มโค้ก 36 นิ้ว" ไม่ใช่ "ต้องการสอบถามราคาร่มโค้ก 36 นิ้วจำนวน 100 อัน"
   - "Sale kit A4" ไม่ใช่ "Sales Kit 2026 PDF for Print A4 พิมพ์สี รวมปก กระดาษ 230 แกรม"
   - "เสื้อยืด" ไม่ใช่ "ขอราคาเสื้อยืดสีขาวคอกลมแขนสั้น"

2. **ถ้าผู้ใช้ถามของหลายอย่าง** — แยกค้นหาทีละรายการ แล้วรวมราคาให้ เช่น:
   - "Sale Kit A4 10 หน้า 10 ชุด" → ค้น "Sale kit A4" + "เคลือบลามิเนต" + "เข้าเล่ม" แล้วรวมราคา

3. **ถ้าครั้งแรกหาไม่เจอ** — ใช้ `search_items` ด้วย keyword ที่สั้นลง หรือลองใช้คำพ้อง เช่น:
   - "เย็บหัวจักร" → ลอง "เข้าเล่ม", "มุงหลังคา", "เย็บเล่ม"
   - "เคลือบเงา" → ลอง "เคลือบลามิเนต", "เคลือบมัน", "เคลือบ UV"
   - "ปริ้นท์" → ลอง "พิมพ์"
   - "โค้ก" → ลอง "โคคา-โคล่า", "โคคา"

4. **เวลาแจ้งราคา** — บอกราคาต่อหน่วย จำนวนที่สั่ง รวมเป็นเงินทั้งหมด และแจ้งว่า "ราคาไม่รวม VAT 7%" เสมอ

## หมวดหมู่สินค้า
- **1.POSM(MKT)** — อุปกรณ์สื่อการตลาด ณ จุดขาย (ถังน้ำแข็ง, กล่องทิชชู, ร่ม, Rack, หมวก ฯลฯ)
- **2.Printing(MKT)** — งานพิมพ์การตลาด (PP Board, ป้าย, สติ๊กเกอร์, แผ่นริจิ ฯลฯ)
- **3.Garment** — เสื้อผ้าเครื่องแต่งกาย (เสื้อยืด, เสื้อโปโล, เสื้อแจ็คเก็ต, หมวก ฯลฯ)
- **4.สรุปPremium** — สินค้าพรีเมียม (ผ้าเบอร์วิ่ง, แก้วกระดาษ, ร่มสนาม, Bean Bag ฯลฯ)
- **5.Printing-Rate** — อัตราค่าบริการพิมพ์ (ป้ายไดคัท, สติ๊กเกอร์, โปสเตอร์, Sale Kit, Coupon, หนังสือคู่มือ, เคลือบลามิเนต, เข้าเล่ม ฯลฯ)

## ข้อควรระวัง
- **lead time** — แจ้งลูกค้าเสมอ: POSM 10-15 วันทำการ, Garment 15 วัน, Premium 15-20 วัน
- **ราคา** — เป็นราคาประมูล Y2026 ผ่านการอนุมัติแล้ว, ไม่รวม VAT 7%
- **Garment** — แจ้งเรื่องค่าสีเพิ่ม: สีอ่อน +5, สีกลาง +10, สีเข้ม +20 บาท
"""


def build_tool_content(price_data):
    price_data_str = json.dumps(price_data, ensure_ascii=False, separators=(",", ":"))
    price_data_literal = json.dumps(price_data_str, ensure_ascii=False)
    return TOOL_CODE.replace("__PRICE_DATA_PLACEHOLDER__", price_data_literal)


def update_model_system_prompt():
    """Update the model's system prompt via API.
    Must send ALL info fields (including access_grants, updated_at, etc.)
    or the endpoint returns 500.
    """
    print("\nUpdating system prompt for procurement-ai-v1...")

    # Fetch current model
    models = api("GET", "/api/models")
    model = next((m for m in models.get("data", []) if m["id"] == MODEL_ID), None)
    if not model:
        print(f"ERROR: Model '{MODEL_ID}' not found!")
        return False

    # Copy ALL info fields, then override params
    info = dict(model.get("info", {}))
    info["params"] = {"system": SYSTEM_PROMPT}

    result = api("POST", "/api/v1/models/model/update", info)
    saved_len = len(result.get("params", {}).get("system", ""))
    print(f"   System prompt updated! ({saved_len} chars saved)")
    return True


def main():
    dry_run = "--dry-run" in sys.argv

    # 1. Load JSON data
    print("Loading JSON files...")
    posm = load_json("1.POSM(MKT).json")
    printing_mkt = load_json("2.Printing(MKT).json")
    garment = load_json("3.Garment.json")
    premium = load_json("4.\u0e2a\u0e23\u0e38\u0e1bPremium.json")
    printing_rate = load_json("5.Printing-Rate.json")

    # 2. Convert to compact format
    print("Converting to compact format...")
    price_data = {
        "1.POSM(MKT)": convert_posm(posm),
        "2.Printing(MKT)": convert_printing_mkt(printing_mkt),
        "3.Garment": convert_garment(garment),
        "4.\u0e2a\u0e23\u0e38\u0e1bPremium": convert_premium(premium),
        "5.Printing-Rate": convert_printing_mkt(printing_rate),
    }
    total = sum(len(v) for v in price_data.values())
    print(f"   Total: {total} items across {len(price_data)} sheets")

    # 3. Build tool content
    print("\nBuilding tool content (UTF-8, fuzzy search)...")
    content = build_tool_content(price_data)
    has_thai = any(ord(c) > 0x0E00 for c in content)
    print(f"   Thai chars: {has_thai}, Size: {len(content):,} chars")

    if dry_run:
        print("\nDRY RUN - skipping API update")
        out_path = JSON_DIR / "tool_content_preview.py"
        out_path.write_text(content, encoding="utf-8")
        (JSON_DIR / "system_prompt_preview.md").write_text(SYSTEM_PROMPT, encoding="utf-8")
        print(f"   Preview: {out_path}")
        print(f"   System prompt preview: {JSON_DIR}/system_prompt_preview.md")
        return

    # 4. Update tool
    print("\nUpdating tool via API...")
    current = api("GET", "/api/v1/tools/")
    current_tool = next((t for t in current if t["id"] == TOOL_ID), None)
    if not current_tool:
        print(f"ERROR: Tool '{TOOL_ID}' not found!")
        sys.exit(1)

    meta = current_tool.get("meta", {})
    meta["description"] = (
        f"Excel>JSON Y2026 ({total} items, {len(price_data)} sheets) "
        f"- fuzzy token search + search_items()"
    )

    update_payload = {
        "id": TOOL_ID,
        "name": current_tool.get("name", "Procurement Price Lookup"),
        "content": content,
        "meta": meta,
    }
    result = api("POST", f"/api/v1/tools/id/{TOOL_ID}/update", update_payload)
    print(f"   Tool updated! ID: {result.get('id')}")

    # 5. Update system prompt
    update_model_system_prompt()

    # 6. Verify
    print("\nVerifying tool...")
    updated = api("GET", "/api/v1/tools/")
    verified = next((t for t in updated if t["id"] == TOOL_ID), None)
    if verified:
        print(f"   Content: {len(verified['content']):,} chars")
        print(f"   Has search_items: {'search_items' in verified['content']}")
        print(f"   Has _tokenize: {'_tokenize' in verified['content']}")
    else:
        print("   Verification failed!")

    # Quick test: simulate a local search
    print("\nSimulated test searches:")
    print("---")
    # Test with Python
    import subprocess
    test_script = """
import json, sys
sys.path.insert(0, '.')
price_data = json.loads(open('json/5.Printing-Rate.json').read())

# Simulate token-based match for "Sale kit A4"
def tokenize(text):
    import re
    tokens = re.split(r'[\\s,/.()\\-]+', text.lower())
    noise = {"for","and","the","with","pdf","file","2026","y2026"}
    return [t for t in tokens if len(t) >= 2 and t not in noise]

def match_score(query, item_name):
    q_tokens = tokenize(query)
    n_tokens = tokenize(item_name)
    if not q_tokens: return 0.0
    matched = 0
    for qt in q_tokens:
        for nt in n_tokens:
            if qt in nt or nt in qt:
                matched += 1
                break
    if query.lower() in item_name.lower():
        matched = max(matched, len(q_tokens))
    return matched / len(q_tokens)

queries = ["Sale kit A4", "Sales Kit 2026 PDF for Print A4", "A4 230g", "เคลือบลามิเนต", "เย็บหัวจักร"]
for q in queries:
    best_score = 0
    best_item = ""
    for item in price_data:
        score = match_score(q, item.get('item_name',''))
        if score > best_score:
            best_score = score
            best_item = item.get('item_name','')[:80]
    print(f"  '{q}' -> score={best_score:.0%} -> {best_item}")
"""
    subprocess.run([sys.executable, "-c", test_script], cwd=str(Path(__file__).parent))

    print("\nDone!")


if __name__ == "__main__":
    main()
