#!/usr/bin/env python3
"""
Upload procurement-search.py tool to Open WebUI via API.

Usage:
    export OWUI_URL="https://genie.haadthip.com"
    export OWUI_TOKEN="sk-..."
    export AZURE_SEARCH_ADMIN_KEY="..."
    export AZURE_OPENAI_API_KEY="..."
    python3 scripts/upload-procurement-tool.py
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

# Read the tool file
tool_path = "app/tools/procurement-search.py"
with open(tool_path, "r", encoding="utf-8") as f:
    tool_code = f.read()

# Create tool via API
print(f"Uploading tool to {OWUI_URL}...")

payload = {
    "id": "procurement_price_search",
    "name": "Procurement Price Search",
    "content": tool_code,
    "meta": {
        "description": "Search procurement prices from Azure AI Search with hybrid search (keyword + vector)",
        "manifest": {}
    }
}

response = requests.post(
    f"{OWUI_URL}/api/v1/tools/create",
    headers={
        "Authorization": f"Bearer {OWUI_TOKEN}",
        "Content-Type": "application/json"
    },
    json=payload
)

if response.status_code == 200:
    result = response.json()
    tool_id = result.get("id")
    print(f"✅ Tool created successfully!")
    print(f"   Tool ID: {tool_id}")
    print(f"   Name: {result.get('name')}")
    
    # Update valves if env vars are set
    azure_search_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
    azure_openai_key = os.environ.get("AZURE_OPENAI_API_KEY")
    
    if azure_search_key and azure_openai_key:
        print(f"\n🔧 Updating tool valves...")
        valves_payload = {
            "AZURE_SEARCH_KEY": azure_search_key,
            "AZURE_OPENAI_KEY": azure_openai_key
        }
        
        valves_response = requests.post(
            f"{OWUI_URL}/api/v1/tools/id/{tool_id}/valves/update",
            headers={
                "Authorization": f"Bearer {OWUI_TOKEN}",
                "Content-Type": "application/json"
            },
            json=valves_payload
        )
        
        if valves_response.status_code == 200:
            print(f"✅ Valves updated successfully!")
        else:
            print(f"⚠️  Failed to update valves: {valves_response.status_code}")
            print(f"   Response: {valves_response.text[:200]}")
    else:
        print(f"\n⚠️  AZURE_SEARCH_ADMIN_KEY or AZURE_OPENAI_API_KEY not set")
        print(f"   Set valves manually at: {OWUI_URL}/workspace/tools")
    
    print(f"""
=== Next Steps ===

1. Update Model to use this tool:
   URL: {OWUI_URL}/workspace/models/edit?id=ผู้ช่วยตรวจสอบราคาสื่อการตลาด%20(Trade%20Marketing%20Materials)%20จากระบบจัดซื้อ%20HaadThip
   
2. Add Tool ID to model: {tool_id}

3. Update System Prompt:

---
คุณคือผู้ช่วยตรวจสอบราคาสื่อการตลาด (Trade Marketing Materials) จากระบบจัดซื้อ HaadThip

เครื่องมือที่คุณมี:
- search_procurement_prices: ค้นหาราคาสินค้าจาก Azure AI Search (hybrid search)
- get_cheapest_option: หาราคาถูกสุด
- compare_vendors: เปรียบเทียบราคาระหว่าง vendors

วิธีการทำงาน:
1. เมื่อผู้ใช้ถามราคา → ใช้ search_procurement_prices(query=...)
2. วิเคราะห์ผลลัพธ์:
   - 1 รายการ → ตอบราคาทันที
   - หลาย variants → ดู specs แล้วถามกลับเป็นภาษาไทย
   - ไม่พบ → ขอให้ระบุชื่อชัดเจนขึ้น
3. แสดง: ชื่อ + ราคา × จำนวน = ยอดรวม + vendor

กฎ:
- ตอบภาษาไทยแบบสบายๆ
- แสดง winner vendor (ราคาถูกสุด)
- หลาย vendors → แสดงตัวเลือก + qty_range
- ไม่เดาราคา ต้องมาจาก search
- ถ้า compound Thai words ไม่เจอ → ลอง use_wildcard=True

ตัวอย่าง:
Q: "ร่มโค้กราคาเท่าไหร่"
A: "ร่มโค้ก มี 3 vendors:
- Vendor A: ฿528 (1-99 ชิ้น)
- Vendor B: ฿565 (100-499 ชิ้น) 
- Vendor C: ฿480 (500+ ชิ้น)
ถ้าสั่งจำนวนมากแนะนำ Vendor C"
---

4. Test in chat: "ร่มโค้กราคาเท่าไหร่"
""")

else:
    print(f"❌ Failed to create tool: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    sys.exit(1)
