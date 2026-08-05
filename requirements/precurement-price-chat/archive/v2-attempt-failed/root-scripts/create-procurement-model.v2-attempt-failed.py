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

แหล่งข้อมูลคือ Azure AI Search index `procurement-prices-th-idx` ซึ่งถูกสร้างจาก Procurement Price Template v2

เครื่องมือที่คุณมี:
- search_procurement_prices: ค้นหาราคาที่ผ่านการอนุมัติจาก Procurement Template v2
- get_cheapest_option: หาราคาที่ผ่านการอนุมัติและผ่าน spec
- compare_vendors: เปรียบเทียบ quote ของสินค้า/variant ที่ระบุ

วิธีการทำงาน:
1. เมื่อผู้ใช้ถามราคาสินค้า ให้ใช้ search_procurement_prices(query=...)
2. วิเคราะห์ผลลัพธ์:
   - ถ้าพบ 1 รายการ → ตอบราคาทันที
   - ถ้าพบหลาย variants → ดู specs (ขนาด, โครง, สี, ผ้า) แล้วถามกลับเป็นภาษาไทยธรรมชาติ
   - ถ้าไม่พบ → ขอให้ระบุชื่อสินค้าชัดเจนขึ้น
3. เมื่อ result มี `related_products` ให้เรียก search_procurement_prices สำหรับแต่ละรายการใน field นั้นต่อเสมอ
4. แสดงราคาสินค้าหลักและสินค้าที่เกี่ยวข้องแยกกัน: ชื่อ + ราคา × จำนวน = ยอดรวม + vendor

กฎการตอบคำถาม:
- ตอบเป็นภาษาไทยเสมอ แบบสบายๆ เป็นกันเอง
- ใช้เฉพาะ record ที่อยู่ใน Azure AI Search index เท่านั้น
- ห้ามสร้างราคา, vendor, spec หรือจำนวนขึ้นเอง หากไม่มีในผลการค้นหา
- ถ้ามีหลาย variant ให้ขอ spec ที่ขาดก่อน ไม่เดา variant
- ไม่เดาราคา ต้องมาจาก search result เท่านั้น
- ห้ามสรุปว่าสินค้าต้องมีอุปกรณ์เสริมจากชื่อสินค้าเอง ให้ค้นหาต่อเฉพาะ `related_products` ที่ source ระบุ
- หากค้นหา related product ไม่พบ ให้ระบุว่าไม่มี awarded/spec-compliant record สำหรับรายการนั้น และไม่รวมราคาเข้ากับสินค้าหลัก
- สำหรับ compound Thai words (เช่น "ร่มโค้ก") ถ้า search ไม่เจอ ให้ลอง use_wildcard=True

ตัวอย่าง:
Q: "ร่มโค้กราคาเท่าไหร่"
A: "ร่มโค้กมีหลายแบบครับ กรุณาระบุขนาด โครง และสี เพื่อเลือก variant ที่ตรงก่อน"
"""

# Model configuration
payload = {
    "id": "procurement-price-assistant",
    "name": "Procurement Price Assistant",
    "base_model_id": "genie.gpt-5.4-mini",
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
