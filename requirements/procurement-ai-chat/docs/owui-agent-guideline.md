# Procurement AI Chat — OWUI Agent Guideline

## สร้าง Agent ตอบราคาสื่อการตลาดใน Open WebUI (Genie)

---

## สารบัญ

1. [ภาพรวม Architecture](#1-ภาพรวม-architecture)
2. [วิธีที่ 1: Model Preset + Knowledge (ง่ายสุด)](#2-วิธีที่-1-model-preset--knowledge-ง่ายสุด)
3. [วิธีที่ 2: Model Preset + Tool + Knowledge (แนะนำ)](#3-วิธีที่-2-model-preset--tool--knowledge-แนะนำ)
4. [วิธีที่ 3: Pipe Function (Advanced)](#4-วิธีที่-3-pipe-function-advanced)
5. [การเตรียมข้อมูล Knowledge Base](#5-การเตรียมข้อมูล-knowledge-base)
6. [การเขียน Price Lookup Tool (Python)](#6-การเขียน-price-lookup-tool-python)
7. [System Prompt Template](#7-system-prompt-template)
8. [Testing & Deployment](#8-testing--deployment)
9. [Flow Diagram](#9-flow-diagram)
10. [Reference: OWUI Concepts](#10-reference-owui-concepts)

---

## 1. ภาพรวม Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   genie.haadthip.com                     │
│                   (Open WebUI v0.10.2)                   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Procurement AI Agent (Model Preset)              │   │
│  │                                                   │   │
│  │  ┌─────────────┐   ┌─────────────┐               │   │
│  │  │ System      │   │ Price       │               │   │
│  │  │ Prompt      │──▶│ Lookup Tool  │               │   │
│  │  │ (who you    │   │ (Python,    │               │   │
│  │  │  are)       │   │  function   │               │   │
│  │  └─────────────┘   │  calling)   │               │   │
│  │                    └──────┬──────┘               │   │
│  │                           │                       │   │
│  │  ┌─────────────┐         │                       │   │
│  │  │ Knowledge   │◀────────┘                       │   │
│  │  │ (RAG on     │  return price                   │   │
│  │  │  Excel)     │                                 │   │
│  │  └─────────────┘                                 │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Backend: LiteLLM Proxy                          │   │
│  │  → deploy-gpt-5.4-mini / deploy-gpt-5.4          │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 3 วิธีในการสร้าง Agent (เรียงจากง่ายไปยาก)

| วิธี | ความสามารถ | เหมาะกับ |
|:----:|:----------:|:--------:|
| **1. Model Preset + Knowledge** | RAG อย่างเดียว, ไม่มี calculatio n | ง่าย, ราคาคงที่ |
| **2. Model Preset + Tool + Knowledge** | ✅ **แนะนำ** — RAG + Function Calling | ซับซ้อน, มี QTY tier |
| **3. Pipe Function** | Full control, custom logic | ขั้นสูง, ต้องการ optimization |

---

## 2. วิธีที่ 1: Model Preset + Knowledge (ง่ายสุด)

### ขั้นตอน

#### Step 1: เตรียม Knowledge Base

แปลง Excel → เอกสารที่ OWUI อ่านได้

**Format ที่แนะนำ**: Markdown (.md) หรือ JSON (.json)

```
Admin Settings → Knowledge → + 📁
```

สร้าง Knowledge base ชื่อ `procurement-prices-y2026` และ upload ไฟล์ที่เตรียมไว้

#### Step 2: สร้าง Model Preset

```
Workspace → Models → + Create Model
```

| Field | Value |
|-------|-------|
| **Name** | `Procurement AI Chat (v1)` |
| **Base Model** | `deploy-gpt-5.4-mini` (หรือ `deploy-gpt-5.4` ถ้าต้องการความแม่นยำสูง) |
| **Model ID** | `procurement-ai-v1` |
| **Description** | ผู้ช่วยตอบราคาสื่อการตลาด HaadThip |
| **System Prompt** | [ดูหัวข้อ 7](#7-system-prompt-template) |
| **Knowledge** | ✅ เลือก `procurement-prices-y2026` |
| **Tools** | (ไม่ต้องเลือก ถ้าใช้แค่ RAG) |
| **Access Control** | กำหนด users/groups ที่ต้องการ |

#### Step 3: ทดสอบ

ใน Chat → เลือก model `Procurement AI Chat (v1)` → พิมพ์คำถาม

### ข้อจำกัดของวิธีนี้
- ❌ LLM ต้องคำนวณราคาเอง (อาจผิดพลาด)
- ❌ QTY tier matching ไม่แม่นยำ
- ❌ ไม่สามารถทำ logic เฉพาะ (เช่น ปรับราคาสีเสื้อ)

---

## 3. วิธีที่ 2: Model Preset + Tool + Knowledge (✅ แนะนำ)

### ขั้นตอน

#### Step 1: เตรียม Knowledge Base (เหมือนวิธีที่ 1)

สร้าง `procurement-prices-y2026` สำหรับให้ Tool ใช้ค้นหา

#### Step 2: สร้าง Price Lookup Tool

```
Admin Settings → Functions → + → เลือก "Tools"
```

**ชื่อ**: `procurement_price_lookup`

**Python code**: [ดูหัวข้อ 6](#6-การเขียน-price-lookup-tool-python)

Tool นี้จะเป็น **function calling endpoint** ที่ LLM เรียกใช้เมื่อต้องการหาราคา

**Function signature** (ที่ LLM จะเห็น):
```python
async def lookup_price(
    item_name: str,         # ชื่อรายการ (เช่น "สติ๊กเกอร์ 37x28 cm.")
    quantity: int,          # จำนวนที่ต้องการ
    sheet_name: str = "",   # ระบุ sheet (optional)
    color_type: str = ""    # สีเสื้อ (สำหรับ Garment)
) -> str:
    """ค้นหาราคาสินค้าจาก Master Price"""
```

#### Step 3: สร้าง Model Preset

```
Workspace → Models → + Create Model
```

| Field | Value |
|-------|-------|
| **Name** | `Procurement AI Chat` |
| **Base Model** | `deploy-gpt-5.4-mini` |
| **Model ID** | `procurement-ai` |
| **System Prompt** | [ดูหัวข้อ 7](#7-system-prompt-template) |
| **Knowledge** | ✅ `procurement-prices-y2026` |
| **Tools** | ✅ `procurement_price_lookup` |
| | ✅ `calculator` (สำหรับคำนวณราคารวม) |

#### Step 4: Flow การทำงาน

```
User: "ขอราคาสติกเกอร์ Minute Maid ขนาด 37x28 cm. จำนวน 15,000 แผ่น"

  1. LLM รับคำถาม → เข้าใจว่ารายการคือ "สติ๊กเกอร์ 37x28 cm."
  2. LLM ตรวจสอบ Knowledge (RAG) → เจอ item นี้ใน Printing(MKT)
  3. LLM เรียก Tool: lookup_price("สติ๊กเกอร์ 37x28 cm.", 15000)
  4. Tool คืนค่า: {"unit_price": 10, "total": 150000, "vendor": "vendor 7"}
  5. LLM ประกอบคำตอบ: "ราคาแผ่นละ 10 บาท รวม 150,000 บาท..."
```

---

## 4. วิธีที่ 3: Pipe Function (Advanced)

ใช้เมื่อต้องการควบคุมทุกอย่างเอง (query → AI Search → calculate → respond)

```python
"""
title: Procurement AI Chat (Pipe)
author: Haadthip
version: 1.0
required_open_webui_version: 0.5.0
"""

import json
from typing import Optional
from pydantic import BaseModel, Field
from openai import OpenAI

class Pipe:
    class Valves(BaseModel):
        priority: int = 0

    def __init__(self):
        self.valves = self.Valves()
        self.name = "Procurement AI Chat"

    async def pipe(self, body: dict, user: dict) -> str:
        """Main pipeline"""
        messages = body.get("messages", [])
        query = messages[-1]["content"] if messages else ""
        
        # 1. Intent classification
        intent = self.classify_intent(query)
        
        # 2. Extract entities
        items = self.extract_items(query)
        
        # 3. Lookup prices
        results = []
        for item in items:
            price = self.lookup_price(item)
            results.append(price)
        
        # 4. Build response
        response = self.format_response(results)
        return response

    def classify_intent(self, query: str) -> str:
        # ตรวจสอบว่าเป็นคำขอราคา ใบเสนอราคา หรือสอบถาม
        pass

    def extract_items(self, query: str) -> list:
        # ดึงชื่อรายการ, จำนวน, spec จากข้อความ
        pass

    def lookup_price(self, item: dict) -> dict:
        # ค้นหาราคาจาก database / vector store
        pass

    def format_response(self, results: list) -> str:
        # สร้าง response ในรูปแบบ email
        pass
```

### ข้อดี
- Control เต็มทุก step
- สามารถทำ Post-processing (เพิ่ม VAT, เช็คระยะเวลา ฯลฯ)
- Error handling ที่ดีกว่า

### ข้อเสีย
- เขียนยากกว่า
- ต้องจัดการ context/history เอง
- ไม่ได้ใช้ประโยชน์จาก LLM's function calling

---

## 5. การเตรียมข้อมูล Knowledge Base

### 5.1 รูปแบบไฟล์สำหรับ RAG

#### ตัวเลือก A: JSON (.json)
```json
[
  {
    "id": "PRINTING_12",
    "category": "งานพิมพ์การตลาด",
    "item_name": "สติ๊กเกอร์ 37x28 cm.",
    "description": "สติ๊กเกอร์ 37x28 ซม. วัสดุสติกเกอร์พีวีซี",
    "sheet": "2.Printing(MKT)",
    "unit": "แผ่น",
    "price_tiers": [
      {"min_qty": 300, "max_qty": 300, "unit_price": 19.0, "vendor": "vendor 3"},
      {"min_qty": 501, "max_qty": 500, "unit_price": 18.5, "vendor": "vendor 3"},
      {"min_qty": 1001, "max_qty": 1000, "unit_price": 12.0, "vendor": "vendor 7"},
      {"min_qty": 3001, "max_qty": 99999, "unit_price": 10.0, "vendor": "vendor 7"}
    ],
    "approved_price": 10.0,
    "approved_vendor": "vendor 7",
    "keywords": ["สติกเกอร์", "สติ๊กเกอร์", "sticker", "37x28"],
    "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม"
  }
]
```

#### ตัวเลือก B: Markdown (.md) — LLM-friendly
```markdown
# สติ๊กเกอร์ 37x28 cm.

- **หมวดหมู่**: งานพิมพ์การตลาด (2.Printing(MKT))
- **หน่วย**: แผ่น
- **คำค้น**: สติกเกอร์, สติ๊กเกอร์, sticker, 37x28

### ราคาตามจำนวน
| จำนวน | ราคาต่อหน่วย | ผู้ชนะประมูล |
|:-----:|:----------:|:----------:|
| 300 แผ่น | 19.00 บาท | vendor 3 |
| 500 แผ่น | 18.50 บาท | vendor 3 |
| 1,000 แผ่น | 12.00 บาท | vendor 7 |
| 3,000+ แผ่น | 10.00 บาท | vendor 7 |

### หมายเหตุ
- ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%
- ระยะเวลาผลิต 10-15 วันทำการหลังยืนยัน AW
```

### 5.2 การแปลง Excel → Knowledge Files

ใช้ Python script ใน `scripts/`:

```python
import pandas as pd
import json

xlsx = "Trade Marketing Materials price for Y2026.final.xlsx"

# อ่าน sheet 2.Printing(MKT)
df = pd.read_excel(xlsx, sheet_name="2.Printing(MKT)", header=None)

# แปลงเป็นรายการ items
items = []
for idx in range(2, len(df)):
    row = df.iloc[idx]
    item_name = row[2]
    if pd.isna(item_name):
        continue
    
    item = {
        "item_name": str(item_name).strip(),
        "price_tiers": []
    }
    items.append(item)

# Output เป็น JSON
with open("procurement_prices.json", "w") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
```

### 5.3 Upload เข้า Knowledge Base

```
Admin Settings → Knowledge → + Knowledge
├─ Name: procurement-prices-y2026
├─ Description: ราคาสื่อการตลาดประจำปี 2026
└─ Upload Files:
   ├── procurement_prices.json
   ├── procurement_prices.md
   └── (optional) Trade Marketing Materials price for Y2026.final.xlsx
```

---

## 6. การเขียน Price Lookup Tool (Python)

```python
"""
title: Procurement Price Lookup
author: Haadthip
version: 1.0
required_open_webui_version: 0.5.0
"""

import json
import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from openai import AzureOpenAI


class Tools:
    class Valves(BaseModel):
        """ตั้งค่าใน Admin Settings → Functions"""
        
        # AI Search config
        search_endpoint: str = Field(
            default="https://srch-entchat-poc-sand.search.windows.net",
        )
        search_api_key: str = Field(
            default=os.environ.get("AZURE_SEARCH_ADMIN_KEY", ""),
        )
        index_name: str = Field(
            default="procurement-prices-idx",
            description="ชื่อ index ใน Azure AI Search สำหรับราคาสื่อ",
        )
        api_version: str = Field(default="2024-07-01")
        top_results: int = Field(default=5)

        # Embedding config
        openai_endpoint: str = Field(
            default="https://aif-entchat-poc-sand.cognitiveservices.azure.com",
        )
        openai_api_key: str = Field(
            default=os.environ.get("OPENAI_API_KEY", ""),
        )
        embedding_deployment: str = Field(default="deploy-embedding-3-large")
        embedding_dimensions: int = Field(default=3072)

    def __init__(self):
        self.valves = self.Valves()

    async def lookup_price(
        self,
        item_name: str,
        quantity: int,
        color_type: Optional[str] = None,
        sheet_hint: Optional[str] = None,
    ) -> str:
        """
        ค้นหาราคาสินค้าจาก Master Price.
        
        ใช้เมื่อผู้ใช้ขอราคาสินค้าสื่อการตลาด (POSM, งานพิมพ์, เสื้อ, พรีเมี่ยม)
        
        Parameters:
        - item_name: ชื่อรายการสินค้า (เช่น "สติ๊กเกอร์ 37x28 cm.", "เสื้อยืดคอกลม")
        - quantity: จำนวนที่ต้องการ
        - color_type: (เฉพาะ Garment) สีเสื้อ: "อ่อน", "กลาง", "เข้ม"
        - sheet_hint: (optional) ใบ้ว่ารายการนี้อยู่ใน sheet ไหน
        
        Returns:
        - ข้อมูลราคาในรูปแบบ JSON string
        """
        
        # 1. สร้าง query vector สำหรับค้นหา
        embedding = await self._get_embedding(item_name)
        
        # 2. ค้นหา item ที่ตรงที่สุดจาก AI Search
        search_results = await self._search_item(item_name, embedding, sheet_hint)
        
        if not search_results:
            return json.dumps({
                "found": False,
                "message": f"ไม่พบรายการ '{item_name}' ในฐานข้อมูลราคา"
            }, ensure_ascii=False)
        
        best_match = search_results[0]
        
        # 3. หา QTY tier ที่ตรงกับจำนวน
        price = self._match_qty_tier(best_match.get("price_tiers", []), quantity)
        
        # 4. ปรับราคาสำหรับ Garment (สี)
        if color_type and color_type in ["อ่อน", "กลาง", "เข้ม"]:
            adjustment = {"อ่อน": 5, "กลาง": 10, "เข้ม": 20}
            price["unit_price"] += adjustment.get(color_type, 0)
            price["note"] = f"รวมค่าปรับสี{color_type} +{adjustment.get(color_type, 0)} บาท"
        
        # 5. คำนวณราคารวม
        total = price["unit_price"] * quantity
        
        result = {
            "found": True,
            "item_name": best_match.get("item_name", item_name),
            "category": best_match.get("category", ""),
            "quantity": quantity,
            "unit_price": price["unit_price"],
            "total_price": total,
            "vendor": price.get("vendor", ""),
            "sheet": best_match.get("sheet", ""),
            "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%",
            "lead_time": "10-15 วันทำการหลังยืนยัน AW"
        }
        
        return json.dumps(result, ensure_ascii=False)

    async def _get_embedding(self, text: str) -> list:
        """สร้าง vector embedding"""
        client = AzureOpenAI(
            azure_endpoint=self.valves.openai_endpoint,
            api_key=self.valves.openai_api_key,
            api_version="2024-10-21"
        )
        resp = client.embeddings.create(
            model=self.valves.embedding_deployment,
            input=text,
            dimensions=self.valves.embedding_dimensions
        )
        return resp.data[0].embedding

    async def _search_item(self, query: str, embedding: list, sheet_hint: str = None) -> list:
        """ค้นหา item จาก Azure AI Search"""
        url = f"{self.valves.search_endpoint}/indexes/{self.valves.index_name}/docs/search?api-version={self.valves.api_version}"
        
        headers = {
            "api-key": self.valves.search_api_key,
            "Content-Type": "application/json"
        }
        
        body = {
            "search": query,
            "vector": {
                "value": embedding,
                "fields": "description_vector",
                "k": self.valves.top_results
            },
            "select": "id, item_name, category, sheet, price_tiers, description",
            "top": self.valves.top_results
        }
        
        if sheet_hint:
            body["filter"] = f"sheet eq '{sheet_hint}'"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("value", [])
        return []

    def _match_qty_tier(self, tiers: list, qty: int) -> dict:
        """เลือก QTY tier ที่ตรงกับจำนวน"""
        if not tiers:
            return {"unit_price": 0, "vendor": ""}
        
        # เรียงจาก min_qty น้อยไปมาก
        sorted_tiers = sorted(tiers, key=lambda t: t.get("min_qty", 0))
        
        for tier in sorted_tiers:
            if tier.get("min_qty", 0) <= qty <= tier.get("max_qty", 999999):
                return tier
        
        # ถ้าเกินทุก tier → ใช้ tier สุดท้าย
        return sorted_tiers[-1]


    async def health_check(self) -> str:
        """ตรวจสอบว่า Tool ทำงานปกติ"""
        return json.dumps({
            "status": "ok",
            "tool": "Procurement Price Lookup",
            "index": self.valves.index_name
        })
```

### การติดตั้ง Tool
1. เปิด `Admin Settings → Functions`
2. กด `+` → เลือก **Tools**
3. วาง code ด้านบน
4. กด Save
5. ไปที่ `Workspace → Models` → เลือก Model → เปิด Tool นี้

---

## 7. System Prompt Template

```markdown
คุณคือผู้ช่วยตอบราคาสื่อการตลาด (Procurement AI Assistant) ของ บริษัท HaadThip Public Company Limited

## บุคลิกและน้ำเสียง
- ใช้ภาษาไทยสุภาพ เป็นทางการ
- ใช้คำขึ้นต้น: "เรียน [ชื่อผู้ขอ]"
- ลงท้าย: "จึงเรียนมาเพื่อโปรดพิจารณา" / "ขอบคุณคะ/ครับ"
- อ้างอิงตนเองในฐานะ "เจ้าหน้าที่จัดซื้อ"

## ความสามารถ
1. **ค้นหาราคาสินค้า** — ใช้ Tool lookup_price() เพื่อหาราคา
2. **คำนวณราคารวม** — ใช้ calculator tool
3. **ตอบคำถามทั่วไป** — เกี่ยวกับขั้นตอนการจัดซื้อ, ระยะเวลาผลิต

## ข้อมูลราคา (Master Price Y2026)
มี 6 หมวดหมู่:
1. **POSM(MKT)** — สื่อ ณ จุดขาย (ถังน้ำแข็ง, ร่ม, Rack, RGB)
2. **Printing(MKT)** — งานพิมพ์ (PP Board, สติกเกอร์, แบนเนอร์, โปสเตอร์)
3. **Garment** — เสื้อ (ยืด, โปโล, แจ็คเก็ต) — มีปรับราคาตามสี
4. **Premium-EA&HRC** — ของพรีเมี่ยม (แก้ว, ร่ม, Bean Bag)
5. **Printing-Rate1-43** — อัตรางานพิมพ์ รายการที่ 1-43
6. **Printing-Rate44-109** — อัตรางานพิมพ์ รายการที่ 44-109 (รวมธงปีกนก, ไวนิล)

## วิธีตอบราคา
1. ระบุรายการและจำนวนที่ต้องการ
2. ใช้ lookup_price() หาราคาต่อหน่วย
3. คำนวณราคารวม (ใช้ calculator ถ้าจำเป็น)
4. แจ้ง:
   - ราคาต่อหน่วย
   - ราคารวม
   - ระยะเวลาผลิต (10-15 วันทำการ หลังยืนยัน AW)
   - Vendor ที่ได้รับคัดเลือก
5. หมายเหตุ:
   - ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%
   - ระยะเวลาไม่รวมวันหยุดและวันเสาร์-อาทิตย์

## กฎเฉพาะ
- **Garment**: สีอ่อน +5, สีกลาง +10, สีเข้ม +20 บาท/ตัว
- **Printing-Rate**: หากเร่งด่วน (5-7 วัน) → แจ้งว่าใช้ supplier ท้องถิ่น
- ถ้า vendor ราคาต่ำสุดไม่ตรง spec → แจ้งว่าใช้ vendor ถัดไป
- ถ้าไม่พบรายการในระบบ → แนะนำให้ติดต่อเจ้าหน้าที่จัดซื้อโดยตรง

## ตัวอย่างคำตอบ
```
เรียน คุณเบสท์

ขอแจ้งราคา รายการ สติ๊กเกอร์ 37x28 cm. ดังนี้
- จำนวน 15,000 แผ่น ราคาแผ่นละ 10.00 บาท
- รวมเป็นเงินทั้งสิ้น 150,000.00 บาท
- ผู้ชนะประมูล: vendor 7

กำหนดการส่งมอบ: 15 วันทำการหลังจากยืนยัน AW
หมายเหตุ: ราคานี้ไม่รวมภาษีมูลค่าเพิ่ม 7%

จึงเรียนมาเพื่อโปรดพิจารณา
ขอบคุณคะ
```
```

---

## 8. Testing & Deployment

### 8.1 การทดสอบ

#### ทดสอบ Tool (function calling) ก่อน
```python
# ใน OWUI Admin → Functions → เลือก Tool → Preview
>>> lookup_price("สติ๊กเกอร์ 37x28 cm.", 15000)
{
  "found": true,
  "item_name": "สติ๊กเกอร์ 37x28 cm.",
  "unit_price": 10,
  "total_price": 150000,
  "vendor": "vendor 7",
  "note": "ราคาไม่รวมภาษีมูลค่าเพิ่ม 7%"
}
```

#### ทดสอบ Chat Scenarios
```
Test Case 1: ขอราคามาตรฐาน
→ "สติ๊กเกอร์ 37x28 cm. จำนวน 500 แผ่น ราคาเท่าไหร่"

Test Case 2: ขอราคา Garment (มีปรับสี)
→ "เสื้อยืดคอกลมสีเข้ม จำนวน 200 ตัว"

Test Case 3: ขอราคา POSM
→ "ราคาถังใส่น้ำแข็ง-โค้ก จำนวน 5000 ชิ้น"

Test Case 4: ขอราคาหลายรายการ
→ "ขอราคา Arch 60x70 จำนวน 5 ชิ้น และ Wrap Around 30x70 จำนวน 20 ชิ้น"

Test Case 5: ไม่พบรายการ
→ "ราคาป้ายไฟ LED"
```

### 8.2 การ Deploy ไป Production

#### ขั้นตอน
```
1. ✅ ทดสอบใน Local/Dev OWUI
2. ✅ Export Model Preset → Import ใน Production
3. ✅ Export Tool code → Deploy ผ่าน Admin Settings
4. ✅ Upload Knowledge → Production
5. ✅ ตั้งค่า Access Control
6. ✅ ทดสอบ End-to-End
7. ✅ เปิดให้ users ใช้งาน
```

#### การ Export/Import Model Preset
```
Workspace → Models → [Model] → ⋮ → Export
→ ได้ไฟล์ JSON → นำไป Import ใน Production OWUI
```

### 8.3 การ Monitor
- ดู Usage Analytics ใน Admin Dashboard
- ดู logs จาก OWUI / LiteLLM
- เก็บ feedback จาก users

---

## 9. Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER                                        │
│  "ขอราคาสติกเกอร์ Minute Maid ขนาด 37x28 cm. จำนวน 15,000 แผ่น"     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Open WebUI                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Model: Procurement AI Chat (deploy-gpt-5.4-mini)             │  │
│  │                                                               │  │
│  │  1. 🔍 Knowledge Retrieval (RAG)                              │  │
│  │     → ค้นหา "สติ๊กเกอร์ 37x28" ใน procurement-prices-y2026    │  │
│  │     → พบ item มี price_tiers                                   │  │
│  │                                                               │  │
│  │  2. 🛠️ Function Calling                                       │  │
│  │     → เรียก lookup_price("สติ๊กเกอร์ 37x28 cm.", 15000)        │  │
│  │     → Tool ค้นหา QTY tier 3001+ → price = 10                 │  │
│  │     → คืนค่า {unit_price: 10, total: 150000}                  │  │
│  │                                                               │  │
│  │  3. 🤖 LLM Response Generation                                │  │
│  │     → ประกอบคำตอบจาก system prompt + tool result              │  │
│  │     → "ราคาแผ่นละ 10 บาท รวม 150,000 บาท..."                │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        RESPONSE                                     │
│  เรียน คุณเบสท์                                                    │
│  ขอแจ้งราคา รายการ สติ๊กเกอร์ 37x28 cm. ดังนี้                    │
│  - จำนวน 15,000 แผ่น ราคาแผ่นละ 10.00 บาท                        │
│  - รวมเป็นเงิน 150,000.00 บาท                                     │
│  - กำหนดการส่งมอบ 15 วันทำการ หลังยืนยัน AW                       │
│  หมายเหตุ: ราคาไม่รวม VAT 7%                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 10. Reference: OWUI Concepts

### OWUI Component Types ที่เกี่ยวข้อง

| Component | Description | Use Case |
|-----------|-------------|----------|
| **Model Preset** | กำหนด base model + system prompt + tools + knowledge | ✅ สร้าง Agent |
| **Tool** | Python function calling — LLM เป็นคนเรียก | ✅ Price lookup |
| **Pipe** | Custom pipeline — ควบคุม flow เองทั้งหมด | Advanced |
| **Filter** | Intercept request/response | Token tracking |
| **Knowledge** | RAG document store | ✅ Price data |
| **Prompt** | Slash command template | /procurement-price |
| **Skill** | Markdown instruction for task approach | ใช้กับ Tool ได้ |

### Key OWUI API Endpoints

```bash
# List models
GET /api/v1/models/

# Create model preset
POST /api/v1/models/create
{
  "name": "Procurement AI Chat",
  "model": "deploy-gpt-5.4-mini",
  "params": {
    "system_prompt": "...",
    "tools_ids": ["procurement_price_lookup"],
    "knowledge_ids": ["procurement-prices-y2026"]
  }
}

# List tools
GET /api/v1/tools/

# Create tool
POST /api/v1/tools/create
```

### ไฟล์อ้างอิงใน requirements/

```
requirements/procurement-ai-chat/
├── Trade Marketing Materials price for Y2026.xlsx   ← ข้อมูลราคา
├── email_samples.zip                                 ← ตัวอย่างอีเมล
├── email_samples_extracted.txt                       ← ข้อความจากอีเมล
├── README.md                                         ← ภาพรวมข้อมูล
├── sheet-analysis.md                                 ← วิเคราะห์แต่ละ Sheet
└── owui-agent-guideline.md                           ← ไฟล์นี้ (Guideline)
```

---

> **สรุป**: แนะนำ **วิธีที่ 2 (Model Preset + Tool + Knowledge)** เพราะ:
> - ได้ทั้ง RAG สำหรับค้นหาข้อมูล
> - ได้ Function Calling สำหรับคำนวณ QTY tier
> - ยืดหยุ่น ปรับแต่งง่าย
> - ใช้ OWUI standard features ไม่ต้องเขียน Pipe
> - สามารถ export/import ระหว่าง environment ได้
