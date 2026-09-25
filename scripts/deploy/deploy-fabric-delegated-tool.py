#!/usr/bin/env python3
"""Deploy the QAS-only delegated Fabric tool under a distinct Open WebUI ID.

Required for live deployment:
    OWUI_URL
    OWUI_TOKEN

The script does not change the existing Service Principal Fabric tool.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
TOOL_ID = "fabric_query_delegated_user_qas"
TOOL_FILE = ROOT / "app" / "openwebui" / "tools" / "fabric-query-delegated.py"


def build_body() -> dict[str, Any]:
    content = TOOL_FILE.read_text(encoding="utf-8")
    ast.parse(content, filename=str(TOOL_FILE))
    header = re.search(r'^"""\n(?P<header>.*?)\n"""', content, re.DOTALL)
    if not header:
        raise RuntimeError("Tool source is missing its opening metadata docstring")

    manifest: dict[str, str] = {}
    for line in header.group("header").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() in {"title", "author", "version", "required_open_webui_version"}:
            manifest[key.strip()] = value.strip()

    required = {"title", "author", "version", "required_open_webui_version"}
    if required - manifest.keys():
        raise RuntimeError(f"Tool metadata missing: {sorted(required - manifest.keys())}")

    return {
        "id": TOOL_ID,
        "name": manifest["title"],
        "content": content,
        "meta": {
            "description": "QAS experiment: query Fabric SQL with the signed-in user's delegated token",
            "manifest": manifest,
        },
        "access_control": None,
    }


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--payload", type=Path)
    args = parser.parse_args()

    body = build_body()
    encoded = json.dumps(body, ensure_ascii=False, indent=2)
    json.loads(encoded)
    if args.payload:
        args.payload.parent.mkdir(parents=True, exist_ok=True)
        args.payload.write_text(encoded + "\n", encoding="utf-8")
        print(f"Wrote validated payload: {args.payload}")

    print(f"Validated {TOOL_FILE} ({len(body['content'])} chars)")
    print(f"Distinct QAS tool ID: {TOOL_ID}")
    print("JSON encoding: OK")
    print("Python syntax: OK")
    if args.dry_run:
        return 0

    base_url = required_env("OWUI_URL").rstrip("/")
    token = required_env("OWUI_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    check = requests.get(f"{base_url}/api/v1/tools/id/{TOOL_ID}", headers=headers, timeout=30)
    if check.status_code == 200:
        path = f"/api/v1/tools/id/{TOOL_ID}/update"
    elif check.status_code == 404:
        path = "/api/v1/tools/create"
    else:
        raise RuntimeError(f"Tool lookup failed: HTTP {check.status_code}: {check.text[:500]}")

    response = requests.post(f"{base_url}{path}", headers=headers, json=body, timeout=60)
    if response.status_code not in {200, 201}:
        raise RuntimeError(f"Tool deploy failed: HTTP {response.status_code}: {response.text[:1000]}")
    print(f"Deployed {TOOL_ID}: HTTP {response.status_code} via {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
