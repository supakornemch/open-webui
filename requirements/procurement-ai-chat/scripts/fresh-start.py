#!/usr/bin/env python3
"""
Fresh Procurement AI Agent Setup
สร้าง Agent ใหม่พร้อมใช้งาน (ไม่ต้องกังวล ของเก่า)
"""

import json
from pathlib import Path

def create_fresh_agent_config():
    """สร้าง configuration ใหม่สำหรับ Agent"""
    
    root = Path(__file__).resolve().parents[1]
    
    # 1. Agent Configuration
    agent_config = {
        "name": "Procurement AI Assistant 🤖",
        "description": "ผู้ช่วยตรวจสอบราคาสื่อการตลาด Trade Marketing Materials",
        "model": "gpt-5.4-mini",
        "system_prompt_file": str(root / "AGENT_PROMPT.md"),
        "tools": ["procurement_price_lookup"],
        "capabilities": {
            "price_lookup": True,
            "item_details": True,
            "category_listing": True,
            "bulk_calculation": True
        }
    }
    
    # 2. Tool Configuration
    tool_config = {
        "name": "procurement_price_lookup",
        "functions": [
            {
                "name": "lookup_price",
                "description": "ค้นหาราคาสินค้า",
                "params": [
                    {"name": "item_name", "type": "string", "required": True},
                    {"name": "quantity", "type": "number", "required": False},
                    {"name": "category", "type": "string", "required": False}
                ]
            },
            {
                "name": "get_item_details",
                "description": "ดูรายละเอียดสินค้า",
                "params": [
                    {"name": "item_id", "type": "string", "required": True}
                ]
            },
            {
                "name": "list_categories",
                "description": "แสดงหมวดหมู่สินค้า",
                "params": []
            }
        ]
    }
    
    # 3. Save configurations
    agent_file = root / "AGENT_CONFIG.json"
    tool_file = root / "TOOL_CONFIG.json"
    
    with open(agent_file, 'w', encoding='utf-8') as f:
        json.dump(agent_config, f, indent=2, ensure_ascii=False)
    
    with open(tool_file, 'w', encoding='utf-8') as f:
        json.dump(tool_config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Agent config saved to: {agent_file}")
    print(f"✅ Tool config saved to: {tool_file}")
    
    # 4. Print setup instructions
    print("\n" + "="*70)
    print("🚀 FRESH START — Procurement AI Agent Setup")
    print("="*70)
    
    print("""
## Step 1: Create Tool in Open WebUI

1. Go to http://localhost:3000
2. Open Workspace → Tools (or Admin → Tools)
3. Click "Create Tool" → "Function"
4. Name: procurement_price_lookup
5. Copy-paste code from: tools/procurement-price-lookup.py
6. Add 3 functions with parameters (see TOOL_CONFIG.json)
7. Save

## Step 2: Create Agent

1. Go to Workspace → Agents (or Admin → Agents)  
2. Click "Create Agent"
3. Name: Procurement AI Assistant 🤖
4. Description: ผู้ช่วยตรวจสอบราคาสื่อการตลาด
5. System Prompt: Copy from AGENT_PROMPT.md (entire content)
6. Model: gpt-5.4-mini
7. Attach Tool: procurement_price_lookup ✅
8. Save

## Step 3: Test

Try these questions:
- "ราคาเสื้อยืด 100 ตัว สีเข้มเท่าไหร่?"
- "มีหมวดสินค้าอะไรบ้าง?"
- "ดูรายละเอียดสินค้า PRT-001 หน่อย"

## ✅ Status
Ready to deploy — UI-based setup (no database access needed)

See: QUICK_SETUP.md for visual guide
    """)
    
    print("="*70 + "\n")

if __name__ == "__main__":
    create_fresh_agent_config()
