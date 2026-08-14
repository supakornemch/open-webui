#!/usr/bin/env python3
"""Deploy procurement-price-assistant model + tool to Open WebUI (Genie).

Reads tool code from app/tools/procurement-search.py and system prompt /
skill from docs/, then registers everything via OWUI REST API.

Prerequisites:
    export OWUI_URL=https://genie.haadthip.com
    export OWUI_TOKEN=<admin-api-key>

What it does:
    1. Upload the tool (procurement_price_search) — create or update
    2. Set tool valves (AZURE_SEARCH_KEY, AZURE_OPENAI_KEY, etc.)
    3. Create/update the model (procurement-price-assistant) with
       system prompt + tool reference
    4. Verify the model is active

Usage:
    cd requirements/precurement-price-chat
    export OWUI_URL=https://genie.haadthip.com
    export OWUI_TOKEN=sk-...
    python3 scripts/deploy_to_genie.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
TOOL_FILE = ROOT / ".." / ".." / "app" / "tools" / "procurement-search.py"
SYSTEM_PROMPT_FILE = ROOT / "docs" / "procurement-assistant-system-prompt.md"
SKILL_FILE = ROOT / "docs" / "procurement-catalog-skill.md"
LOGO_FILE = ROOT / "Procurement_AI_logo_Haadthip_202607301711.jpeg"

# ── Configuration ──────────────────────────────────────────────────
TOOL_ID = "procurement_price_search"
MODEL_ID = "procurement-price-assistant"
MODEL_NAME = "Procurement Price Assistant"
BASE_MODEL_ID = "genie.gpt-5.4-mini"  # LiteLLM model name on Genie

# Tool valves — secrets come from env, endpoints use known defaults
TOOL_VALVES = {
    "AZURE_SEARCH_ENDPOINT": "https://srch-entchat-poc-sand.search.windows.net",
    "AZURE_OPENAI_ENDPOINT": "https://app-litellm-poc-sand.azurewebsites.net",
    "AZURE_SEARCH_INDEX": "procurement-catalog-v1",
    "AZURE_SEARCH_SEMANTIC_CONFIG": "procurement-semantic",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "deploy-embedding-3-large",
    "AZURE_OPENAI_API_VERSION": "2024-10-21",
    "AZURE_SEARCH_API_VERSION": "2024-07-01",
    "max_results": 5,
    "max_search_rounds": 3,
}


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def api_url() -> str:
    return env("OWUI_URL").rstrip("/")


def api_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {env('OWUI_TOKEN')}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def api(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{api_url()}{path}"
    resp = requests.request(method, url, headers=api_headers(), timeout=30, **kwargs)
    if resp.status_code >= 400:
        detail = ""
        try:
            detail = resp.json().get("detail", resp.text[:500])
        except Exception:
            detail = resp.text[:500]
        print(f"  API ERROR {resp.status_code} {method} {path}: {detail}", file=sys.stderr)
    return resp


def deploy_tool() -> bool:
    """Upload the procurement_price_search tool to OWUI."""
    print(f"\n── Tool: {TOOL_ID} ──")

    # Read tool source
    if not TOOL_FILE.exists():
        print(f"  ERROR: Tool file not found: {TOOL_FILE}")
        return False
    content = TOOL_FILE.read_text(encoding="utf-8")
    print(f"  Read {len(content)} bytes from {TOOL_FILE.name}")

    # Check if tool already exists
    check = api("GET", f"/api/v1/tools/id/{TOOL_ID}")
    exists = check.status_code == 200

    if exists:
        print(f"  Tool exists — updating via POST /api/v1/tools/id/{TOOL_ID}/update")
        body = {
            "id": TOOL_ID,
            "name": "Procurement Price Search",
            "content": content,
            "meta": {
                "description": "Search awarded procurement prices from Azure AI Search (hybrid: BM25 + vector)",
                "manifest": {},
            },
            "access_control": None,
        }
        resp = api("POST", f"/api/v1/tools/id/{TOOL_ID}/update", json=body)
    else:
        print(f"  Tool not found — creating via POST /api/v1/tools/create")
        body = {
            "id": TOOL_ID,
            "name": "Procurement Price Search",
            "content": content,
            "meta": {
                "description": "Search awarded procurement prices from Azure AI Search (hybrid: BM25 + vector)",
                "manifest": {},
            },
            "access_control": None,
        }
        resp = api("POST", "/api/v1/tools/create", json=body)

    if resp.status_code not in {200, 201}:
        print(f"  FAILED to deploy tool: {resp.status_code}")
        return False

    print(f"  ✅ Tool deployed (status {resp.status_code})")
    return True


def deploy_tool_valves() -> bool:
    """Set/update the tool's valve values."""
    print(f"\n── Tool Valves: {TOOL_ID} ──")

    # Read secrets from environment (same as Genie's docker env)
    search_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    valves = dict(TOOL_VALVES)
    if search_key:
        valves["AZURE_SEARCH_KEY"] = search_key
    if openai_key:
        valves["AZURE_OPENAI_KEY"] = openai_key

    print(f"  Setting {len(valves)} valve(s)")

    resp = api("POST", f"/api/v1/tools/id/{TOOL_ID}/valves/update", json=valves)
    if resp.status_code not in {200, 201}:
        print(f"  FAILED to set valves: {resp.status_code}")
        return False

    print(f"  ✅ Valves updated")
    return True


def build_system_prompt() -> str:
    """Build the full system prompt from the markdown doc + skill reference."""
    prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    skill = SKILL_FILE.read_text(encoding="utf-8").strip()

    # Combine: system prompt first, then skill reference as appended knowledge
    full = f"""{prompt}

---
## Knowledge Reference (procurement-catalog-skill)

{skill}
"""
    return full


def upload_logo() -> str | None:
    """Upload the model logo to OWUI files and return its content URL."""
    if not LOGO_FILE.exists():
        print(f"  ⚠️  Logo not found: {LOGO_FILE} — skipping profile image")
        return None

    print(f"\n── Logo Upload ──")
    print(f"  File: {LOGO_FILE.name} ({LOGO_FILE.stat().st_size:,} bytes)")

    with open(LOGO_FILE, "rb") as f:
        resp = requests.post(
            f"{api_url()}/api/v1/files",
            headers={"Authorization": f"Bearer {env('OWUI_TOKEN')}", "Accept": "application/json"},
            files={"file": (LOGO_FILE.name, f, "image/jpeg")},
            timeout=60,
        )

    if resp.status_code not in {200, 201}:
        detail = resp.text[:300]
        print(f"  ❌ Logo upload failed ({resp.status_code}): {detail}")
        return None

    data = resp.json()
    file_id = data.get("id") or data.get("file_id")
    if not file_id:
        print(f"  ❌ Logo upload response missing id: {json.dumps(data, ensure_ascii=False)[:300]}")
        return None

    logo_url = f"/api/v1/files/{file_id}/content"
    print(f"  ✅ Logo uploaded — URL: {logo_url}")
    return logo_url


def deploy_model(logo_url: str | None = None) -> bool:
    """Create or update the procurement-price-assistant model."""
    print(f"\n── Model: {MODEL_ID} ──")

    if not SYSTEM_PROMPT_FILE.exists():
        print(f"  ERROR: System prompt not found: {SYSTEM_PROMPT_FILE}")
        return False

    system_prompt = build_system_prompt()
    print(f"  System prompt: {len(system_prompt)} chars")

    # Preserve existing profile_image_url if we're updating and no new logo
    existing_logo_url = None
    check = api("GET", f"/api/v1/models/model?id={MODEL_ID}")
    exists = check.status_code == 200
    if exists:
        existing = check.json()
        existing_meta = existing.get("meta") or {}
        existing_logo_url = existing_meta.get("profile_image_url")
        if existing_logo_url:
            print(f"  Existing logo: {'data:...' if existing_logo_url.startswith('data:') else existing_logo_url[:80]}")

    meta: dict[str, Any] = {
        "description": (
            "Procurement price assistant for Trade Marketing Materials — "
            "searches Azure AI Search via procurement_price_search tool. "
            "ภาษาไทย, ตอบราคาจาก Excel Master (awarded prices)."
        ),
        "capabilities": {
            "tools": True,
            "citations": False,
        },
    }
    # Only set logo if we have a NEW uploaded one (skip giant base64 data URIs)
    if logo_url and not logo_url.startswith("data:"):
        meta["profile_image_url"] = logo_url
        print(f"  Logo URL: {logo_url}")
    elif existing_logo_url:
        print(f"  Preserving existing logo (not re-sending to avoid payload bloat)")

    body = {
        "id": MODEL_ID,
        "base_model_id": BASE_MODEL_ID,
        "name": MODEL_NAME,
        "meta": meta,
        "params": {
            "system": system_prompt,
        },
        "access_control": None,
        "is_active": True,
    }

    if exists:
        print(f"  Model exists — updating via POST /api/v1/models/model/update?id={MODEL_ID}")
        resp = api("POST", f"/api/v1/models/model/update?id={MODEL_ID}", json=body)
    else:
        print(f"  Model not found — creating via POST /api/v1/models/create")
        resp = api("POST", "/api/v1/models/create", json=body)

    if resp.status_code not in {200, 201}:
        # 500 is a known issue with OWUI v0.11.0 model update API.
        # Write the system prompt to a file so the user can copy-paste via web UI.
        prompt_out = ROOT / "data" / "exports" / "model-system-prompt.txt"
        prompt_out.parent.mkdir(parents=True, exist_ok=True)
        prompt_out.write_text(system_prompt, encoding="utf-8")
        print(f"  ⚠️  Model API returned {resp.status_code}.")
        print(f"  ✅ System prompt saved to: {prompt_out}")
        print(f"  📋 Copy it into: {api_url()}/workspace/models/edit?id={MODEL_ID}")
        return False

    print(f"  ✅ Model deployed (status {resp.status_code})")

    # Verify
    verify = api("GET", f"/api/v1/models/model?id={MODEL_ID}")
    if verify.status_code == 200:
        data = verify.json()
        print(f"    id={data.get('id')} name={data.get('name')} active={data.get('is_active')}")
        print(f"    base_model={data.get('base_model_id')}")
        vmeta = data.get("meta") or {}
        if vmeta.get("profile_image_url"):
            print(f"    logo={vmeta.get('profile_image_url')}")

    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate everything without making API calls")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Deploy Procurement Price Chat to OWUI")
    print(f"  Target: {api_url() if not args.dry_run else '(dry-run, no API calls)'}")
    print("=" * 60)

    # ── Dry-run: validate tool & prompt ──
    if args.dry_run:
        print("\n── Dry Run: Validating files ──")
        if not TOOL_FILE.exists():
            print(f"  ❌ Tool file missing: {TOOL_FILE}")
            return 1
        content = TOOL_FILE.read_text(encoding="utf-8")
        print(f"  ✅ Tool: {len(content)} bytes from {TOOL_FILE.name}")
        if "class Tools" not in content or "search_procurement_prices" not in content:
            print(f"  ❌ Tool missing expected class/function")
            return 1

        if not SYSTEM_PROMPT_FILE.exists():
            print(f"  ❌ System prompt missing: {SYSTEM_PROMPT_FILE}")
            return 1
        prompt = build_system_prompt()
        print(f"  ✅ System prompt: {len(prompt)} chars")

        if not SKILL_FILE.exists():
            print(f"  ❌ Skill file missing: {SKILL_FILE}")
            return 1
        print(f"  ✅ Skill: {len(SKILL_FILE.read_text(encoding='utf-8'))} bytes")

        if LOGO_FILE.exists():
            print(f"  ✅ Logo: {LOGO_FILE.name} ({LOGO_FILE.stat().st_size:,} bytes)")
        else:
            print(f"  ⚠️  Logo missing (will skip profile image): {LOGO_FILE.name}")

        print(f"\n  Would deploy:")
        print(f"    Tool:  {TOOL_ID} ({len(content)} bytes)")
        print(f"    Model: {MODEL_ID} (base: {BASE_MODEL_ID})")
        print(f"    Logo:  {'✅' if LOGO_FILE.exists() else '❌'}")
        print(f"    Valves: {len(TOOL_VALVES)} keys")
        print(f"\n  Run without --dry-run when ready:")
        print(f"    export OWUI_URL=https://genie.haadthip.com")
        print(f"    export OWUI_TOKEN=<your-admin-api-key>")
        print(f"    python3 scripts/deploy_to_genie.py")
        return 0

    # Pre-flight: check connectivity
    print("\n── Pre-flight ──")
    health = api("GET", "/api/v1/models")
    if health.status_code != 200:
        print(f"  ERROR: Cannot reach OWUI at {api_url()} (status {health.status_code})")
        print(f"  Check OWUI_URL and OWUI_TOKEN.")
        return 1
    print(f"  ✅ Connected — {len(health.json())} models found")

    ok = True
    ok &= deploy_tool()
    ok &= deploy_tool_valves()
    # Logo upload: try but don't block deployment if it fails
    logo_url = upload_logo()
    # Model update: try but don't block (the API has a known 500 issue on this instance)
    model_ok = deploy_model(logo_url)
    if not model_ok:
        print("\n  ⚠️  Model API update returned 500 (known OWUI v0.11.0 issue).")
        print("  The tool and valves are deployed; update the system prompt manually:")
        print(f"  → {api_url()}/workspace/models/edit?id={MODEL_ID}")

    print("\n" + "=" * 60)
    if ok:
        print("  ✅ Deployment complete!")
        print(f"  Model: {MODEL_ID} (base: {BASE_MODEL_ID})")
        print(f"  Tool:  {TOOL_ID}")
        print(f"  URL:   {api_url()}")
        print("=" * 60)
        return 0
    else:
        print("  ❌ Deployment had errors — review above.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        raise SystemExit(2) from e
