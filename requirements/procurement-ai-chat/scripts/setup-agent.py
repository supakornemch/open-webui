#!/usr/bin/env python3
"""
Agent Creation Script for Open WebUI

สร้าง Agent ที่ชื่อ "Procurement AI Assistant" ใน Open WebUI พร้อม tools
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Configuration
OWUI_BASE_URL = "http://localhost:3000"
OWUI_API_KEY = ""  # Will be prompted if needed

def create_agent(
    name: str,
    description: str,
    system_prompt: str,
    model: str = "gpt-5.4-mini",
    tools: Optional[list] = None
) -> dict:
    """
    Create an Agent in Open WebUI via API

    Args:
        name: Agent name
        description: Agent description
        system_prompt: System prompt/instructions
        model: Model name to use
        tools: List of tool names to attach

    Returns:
        Response JSON from Open WebUI API
    """
    endpoint = f"{OWUI_BASE_URL}/api/v1/agents"

    payload = {
        "name": name,
        "description": description,
        "instructions": system_prompt,
        "model": model,
        "tools": tools or []
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OWUI_API_KEY}" if OWUI_API_KEY else ""
    }

    print(f"📤 Creating agent '{name}' at {endpoint}...")
    print(f"   Model: {model}")
    print(f"   Tools: {', '.join(tools) if tools else 'none'}")

    response = requests.post(endpoint, json=payload, headers=headers)

    if response.status_code in [200, 201]:
        print(f"✅ Agent created successfully!")
        return response.json()
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return {"error": response.text}


def register_tool_function(
    tool_name: str,
    function_name: str,
    function_code: str,
    tool_definition: dict
) -> dict:
    """
    Register a tool function in Open WebUI

    Args:
        tool_name: Unique tool identifier
        function_name: Display name of function
        function_code: Python function code
        tool_definition: JSON definition of function (params, etc)

    Returns:
        Response from Open WebUI
    """
    endpoint = f"{OWUI_BASE_URL}/api/v1/tools"

    payload = {
        "name": tool_name,
        "display_name": function_name,
        "type": "function",
        "code": function_code,
        "definition": tool_definition
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OWUI_API_KEY}" if OWUI_API_KEY else ""
    }

    print(f"📤 Registering tool '{tool_name}'...")

    response = requests.post(endpoint, json=payload, headers=headers)

    if response.status_code in [200, 201]:
        print(f"✅ Tool registered!")
        return response.json()
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return {"error": response.text}


def main():
    """Main setup script"""
    root_dir = Path(__file__).resolve().parents[1]  # Go up 1 level to procurement-ai-chat

    print("\n" + "="*60)
    print("🚀 Procurement AI Agent Setup")
    print("="*60)

    # Step 1: Read system prompt
    prompt_file = root_dir / "AGENT_PROMPT.md"
    if not prompt_file.exists():
        print(f"❌ Prompt file not found: {prompt_file}")
        return

    with open(prompt_file) as f:
        system_prompt = f.read()
    print(f"✅ Loaded system prompt ({len(system_prompt)} chars)")

    # Step 2: Read tool code
    tool_file = root_dir / "tools" / "procurement-price-lookup.py"
    if not tool_file.exists():
        print(f"❌ Tool file not found: {tool_file}")
        return

    with open(tool_file) as f:
        tool_code = f.read()
    print(f"✅ Loaded tool code ({len(tool_code)} chars)")

    # Step 3: Read tool definition
    tool_def_file = root_dir / "tools" / "openwebui-tool-definition.json"
    if not tool_def_file.exists():
        print(f"❌ Tool definition not found: {tool_def_file}")
        return

    with open(tool_def_file) as f:
        tool_definition = json.load(f)
    print(f"✅ Loaded tool definition")

    # Step 4: Register tool (optional - manual for now)
    print("\n" + "-"*60)
    print("📝 Next Steps:")
    print("-"*60)
    print("""
1. ⚙️  ใน Open WebUI UI, ไปที่ Tools section
   - เลือก "Create Tool" → "Function"
   - Copy code จาก: tools/procurement-price-lookup.py
   - Set parameters ตามไฟล์: tools/openwebui-tool-definition.json

2. 🤖 สร้าง Agent:
   - ชื่อ: "Procurement AI Assistant"
   - Description: "ผู้ช่วยตรวจสอบราคาสื่อการตลาด (Trade Marketing Materials)"
   - System Prompt: Copy ทั้งหมดจาก: AGENT_PROMPT.md
   - Model: gpt-5.4-mini (หรือ gpt-5.4 เพื่อ better reasoning)
   - Attach Tool: procurement_price_lookup

3. ✅ Test Agent:
   - คำถามทดสอบ: "ราคาเสื้อยืดเท่าไหร่ถ้าอยากได้ 100 ตัว?"
   - ต่อ: "ดูรายละเอียดทั้งหมด"
   - ต่อ: "มีสินค้า Garment อื่น ๆ อีกไหม?"

ℹ️  API automation support can be added later if needed.
""")

    # Step 5: Show summary
    print("\n" + "="*60)
    print("📦 Configuration Summary")
    print("="*60)
    print(f"Agent Name:       Procurement AI Assistant")
    print(f"Tool Name:        procurement_price_lookup")
    print(f"Language:         Thai (ไทย)")
    print(f"Model:            gpt-5.4-mini")
    print(f"System Prompt:    {len(system_prompt)} chars")
    print(f"Tool Code:        {len(tool_code)} chars")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
