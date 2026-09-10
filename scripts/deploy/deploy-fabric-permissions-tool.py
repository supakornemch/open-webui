#!/usr/bin/env python3
"""Deploy Fabric permission discovery tool to QAS.

Requires:
    OWUI_URL (e.g. https://app-entchat-owui-qas.azurewebsites.net)
    OWUI_TOKEN (admin API token)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "app" / "tools" / "fabric-permissions.py"


def main():
    owui_url = os.getenv("OWUI_URL")
    owui_token = os.getenv("OWUI_TOKEN")
    
    if not owui_url or not owui_token:
        print("ERROR: OWUI_URL and OWUI_TOKEN env vars are required")
        sys.exit(1)
    
    if not TOOL_PATH.exists():
        print(f"ERROR: Tool not found at {TOOL_PATH}")
        sys.exit(1)
    
    content = TOOL_PATH.read_text("utf-8")
    tool_id = "fabric_permissions_discovery_qas"
    payload = {
        "id": tool_id,
        "name": "Fabric Permissions Discovery (QAS)",
        "content": content,
        "meta": {
            "description": "Discover accessible Fabric schemas/tables/columns for delegated user",
            "manifest": {},
        },
    }
    
    url = f"{owui_url.rstrip('/')}/api/v1/tools/create"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {owui_token}",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.load(resp)
            print(f"✓ Deployed {tool_id}")
            print(json.dumps(result, indent=2))
    except urllib.error.HTTPError as exc:
        print(f"✗ Deploy failed: {exc.code} {exc.reason}")
        print(exc.read().decode("utf-8"))
        sys.exit(1)


if __name__ == "__main__":
    main()
