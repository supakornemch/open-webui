#!/usr/bin/env python3
"""
Create procurement pricing model in Open WebUI and link the tool.

Usage:
    export OWUI_URL="http://localhost:3000"
    export OWUI_TOKEN="sk-..."
    python3 scripts/create-procurement-model.py
"""

import os
import sys
import requests
import json

# Configuration
OWUI_URL = os.environ.get("OWUI_URL", "http://localhost:3000")
OWUI_TOKEN = os.environ.get("OWUI_TOKEN")

if not OWUI_TOKEN:
    print("Error: OWUI_TOKEN environment variable is required")
    sys.exit(1)

# System prompt
SYSTEM_PROMPT = """คุณคือผู้ช่วยตรวจสอบราคาสื่อการตลาด (Trade Marketing Materials) จากระบบจัดซื้อ HaadThip

เครื่องมือที่คุณมี:
- search_procurement_prices: ค้นหาราคาสินค้าจาก Azure AI Search (hybrid search: keyword + vector)
- get_cheapest_option: หาราคาถูกสุดสำหรับสินค้า
- compare_vendors: เปรียบเทียบราคาระหว่าง vendors

วิธีการทำงาน:
1. เมื่อผู้ใช้ถามราคาสินค้า ให้ใช้ search_procurement_prices(query=...)
2. วิเคราะห์ผลลัพธ์:
   - ถ้าพบ 1 รายการ → ตอบราคาทันที
   - ถ้าพบหลาย variants → ดู specs (ขนาด, โครง, สี, ผ้า) แล้วถามกลับเป็นภาษาไทยธรรมชาติ
   - ถ้าไม่พบ → ขอให้ระบุชื่อสินค้าชัดเจนขึ้น
3. เมื่อระบุสินค้าได้แล้ว → แสดง: ชื่อ + ราคา × จำนวน = ยอดรวม + vendor

กฎการตอบคำถาม:
- ตอบเป็นภาษาไทยเสมอ แบบสบายๆ เป็นกันเอง
- แสดง vendor ที่ราคาถูกสุด (winner_vendor)
- ถ้ามีหลาย vendor ให้แสดงตัวเลือก พร้อมช่วงราคา (qty_range)
- ไม่เดาราคา ต้องมาจาก search result เท่านั้น
- สำหรับ compound Thai words (เช่น "ร่มโค้ก") ถ้า search ไม่เจอ ให้ลอง use_wildcard=True

ตัวอย่าง:
Q: "ร่มโค้กราคาเท่าไหร่"
A: "ร่มโค้ก มีให้เลือก 3 vendors ค่ะ:
- Vendor A: ฿528 (1-99 ชิ้น)
- Vendor B: ฿565 (100-499 ชิ้น) 
- Vendor C: ฿480 (500+ ชิ้น)
ถ้าสั่งจำนวนมากแนะนำ Vendor C ค่ะ"
"""

# Model configuration
payload = {
    "id": "procurement-price-assistant",
    "name": "ผู้ช่วยตรวจสอบราคาสื่อการตลาด (Trade Marketing Materials) จากระบบจัดซื้อ HaadThip",
    "base_model_id": "gpt-5.4-mini",
    "params": {
        "system": SYSTEM_PROMPT
    },
    "meta": {
        "description": "ผู้ช่วยค้นหาราคาสินค้าจากระบบจัดซื้อ พร้อมเปรียบเทียบ vendors และแนะนำราคาที่ดีที่สุด",
        "capabilities": {
            "vision": False,
            "usage": True
        },
        "toolIds": ["procurement_price_search"]
    }
}

print(f"Creating or updating model at {OWUI_URL}...")

existing = requests.get(
    f"{OWUI_URL}/api/v1/models/model?id={payload['id']}",
    headers={
        "Authorization": f"Bearer {OWUI_TOKEN}",
    }
)
if existing.status_code == 200:
    existing_model = existing.json()
    payload = {
        **existing_model,
        "base_model_id": payload["base_model_id"],
        "name": payload["name"],
        "params": payload["params"],
        "meta": {**existing_model.get("meta", {}), **payload["meta"]},
    }
endpoint = (
    f"{OWUI_URL}/api/v1/models/model/update"
    if existing.status_code == 200
    else f"{OWUI_URL}/api/v1/models/create"
)
response = requests.post(
    endpoint,
    headers={"Authorization": f"Bearer {OWUI_TOKEN}", "Content-Type": "application/json"},
    json=payload,
)

if response.status_code == 200:
    result = response.json()
    model_id = result.get("id")
    print(f"✅ Model {'updated' if existing.status_code == 200 else 'created'} successfully!")
    print(f"   Model ID: {model_id}")
    print(f"   Name: {result.get('name')}")
    print(f"   Tools: {result.get('meta', {}).get('toolIds', [])}")
    print(f"""
=== Next Steps ===

1. Test the model:
   URL: {OWUI_URL}/c/new?models={model_id}
   
2. Ask: "ร่มโค้กราคาเท่าไหร่"

3. Verify tool is called (check function call logs in UI)

4. If needed, adjust base_model_id in this script to match your deployment
""")
else:
    print(f"❌ Failed to create model: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    sys.exit(1)
