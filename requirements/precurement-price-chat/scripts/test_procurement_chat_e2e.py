#!/usr/bin/env python3
"""E2E chat regression test for procurement-price-assistant on Genie.

Tests the deployed model + tool through OWUI chat completions REST API.
Validates: tool calling, price accuracy, misspelling, language switching,
variant clarification, and zero-result handling.

Usage:
    export OWUI_URL=https://genie.haadthip.com   # or via .zshrc
    # OWUI_TOKEN already set via .zshrc
    python3 scripts/test_procurement_chat_e2e.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

MODEL_ID = "procurement-price-assistant"
ROOT = Path(__file__).resolve().parents[1]
CACHE_FILE = ROOT / "data" / "exports" / "chat-test-results.json"

PASS, FAIL, SKIP = 0, 0, 0

# ══════════════════════════════════════════════════════════════════════
# Test Cases
# ══════════════════════════════════════════════════════════════════════

@dataclass
class TestCase:
    id: str
    message: str
    expect_text: str | None = None     # substring that MUST appear
    expect_excludes: str | None = None  # substring that must NOT appear
    expect_price: float | None = None  # expected price range
    expect_tool_call: bool = False     # should call search_procurement_prices
    tags: tuple[str, ...] = ()

TEST_CASES = [
    # ── Category 1: Exact Match ──
    TestCase("EX-01", "ร่มโค้ก 36 นิ้ว โครงเหล็ก 2 อัน ราคาเท่าไหร่",
             expect_text="523", expect_tool_call=True, tags=("exact", "price")),
    TestCase("EX-02", "โคมไฟสำเร็จรูป ราคาเท่าไหร่",
             expect_text="2095", expect_tool_call=True, tags=("exact", "price")),
    TestCase("EX-03", "แก้วกระดาษ 6.5 ออนซ์ ราคา",
             expect_text="0.98", expect_tool_call=True, tags=("exact", "price")),
    TestCase("EX-04", "Arch 60x70 cm ราคาเท่าไหร่",
             expect_text="207", expect_tool_call=True, tags=("exact", "price")),
    TestCase("EX-05", "ผ้าเบอร์วิ่ง ราคาเท่าไหร่",
             expect_text="1.98", expect_tool_call=True, tags=("exact", "price")),

    # ── Category 2: Misspelling ──
    TestCase("TY-01", "โคมไฟสำเรจรูป ราคาเท่าไหร่",
             expect_text="2095", expect_tool_call=True, tags=("typo",)),
    TestCase("TY-02", "รมโค้ก 36 นิ้ว ราคา",
             expect_text="523", expect_tool_call=True, tags=("typo",)),
    TestCase("TY-03", "ถังนำแข็งโค้ก",
             expect_tool_call=True, tags=("typo",)),
    TestCase("TY-04", "ธงปกนก ราคา",
             expect_tool_call=True, tags=("typo",)),
    TestCase("TY-05", "แบนเนอโค้ก ราคาเท่าไหร่",
             expect_tool_call=True, tags=("typo",)),

    # ── Category 3: Language Switching ──
    TestCase("LS-01", "how much is coke umbrella 36 inch",
             expect_text="523", expect_tool_call=True, tags=("lang",)),
    TestCase("LS-02", "ice bucket coke price",
             expect_tool_call=True, tags=("lang",)),
    TestCase("LS-03", "how much is beach umbrella 42 inch",
             expect_text="1200", expect_tool_call=True, tags=("lang",)),
    TestCase("LS-04", "sticker PVC 4 สี ราคา",
             expect_tool_call=True, tags=("lang", "mixed")),
    TestCase("LS-05", "PP Board 3 มิล ราคา",
             expect_tool_call=True, tags=("lang", "mixed")),

    # ── Category 4: Quantity Tier Matching ──
    TestCase("QT-01", "Arch 60x70 15 อัน ราคาเท่าไหร่",
             expect_text="207", expect_tool_call=True, tags=("qty", "tier")),
    TestCase("QT-02", "Arch 60x70 5 อัน ราคา",
             expect_text="230", expect_tool_call=True, tags=("qty", "tier")),
    TestCase("QT-03", "ถังน้ำแข็งโค้ก 5000 อัน ราคาเท่าไหร่",
             expect_text="42.5", expect_tool_call=True, tags=("qty", "tier")),

    # ── Category 5: Variant Clarification ──
    TestCase("VC-01", "ร่มโค้ก 10 อัน ราคาเท่าไหร่",
             expect_tool_call=True, tags=("variant",)),
    TestCase("VC-02", "PP Board ราคา",
             expect_tool_call=True, tags=("variant",)),

    # ── Category 6: Zero Result ──
    TestCase("ZR-01", "iPhone 15 Pro Max ราคาเท่าไหร่",
             expect_excludes="บาท", tags=("zero",)),
    TestCase("ZR-02", "รถยนต์ Toyota ราคา",
             expect_excludes="บาท", tags=("zero",)),

    # ── Category 7: Thai Natural Conversation ──
    TestCase("TH-01", "ขอสอบถามราคาหน่อยครับ พอดีจะสั่งร่มโค้ก 36 นิ้ว โครงไฟเบอร์ สีตาย 3 อัน",
             expect_tool_call=True, tags=("thai", "natural")),
    TestCase("TH-02", "เช็คราคาถังน้ำแข็งโค้กให้หน่อย",
             expect_text="42.5", expect_tool_call=True, tags=("thai",)),

    # ── Category 8: Unit Pricing ──
    TestCase("UP-01", "ถังน้ำแข็งโค้ก ราคาต่ออันเท่าไหร่",
             expect_text="42.5", expect_tool_call=True, tags=("unit",)),
    TestCase("UP-02", "แก้วกระดาษ 6.5 ออนซ์ ราคาต่อใบ",
             expect_text="0.98", expect_tool_call=True, tags=("unit",)),
]


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def chat(message: str, model: str = MODEL_ID) -> dict[str, Any]:
    """Send a single message to OWUI chat completions and return parsed response."""
    url = f"{env('OWUI_URL').rstrip('/')}/api/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {env('OWUI_TOKEN')}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )
    if resp.status_code != 200:
        return {"_error": f"HTTP {resp.status_code}", "_body": resp.text[:500]}
    return resp.json()


def evaluate(case: TestCase) -> tuple[bool, str, dict[str, Any]]:
    """Run one test case and return (pass, detail, raw_response)."""
    t0 = time.time()
    response = chat(case.message)
    elapsed = time.time() - t0

    if "_error" in response:
        return False, f"API Error: {response['_error']}", response

    choices = response.get("choices", [])
    if not choices:
        return False, "No choices in response", response

    content = choices[0].get("message", {}).get("content", "") or ""
    usage = response.get("usage", {})

    # ── Checks ──
    checks: list[tuple[bool, str]] = []

    # 1. Tool call expected?
    if case.expect_tool_call:
        has_tool = "search_procurement_prices" in str(response).lower()
        # Also check if the response looks like a tool call was executed
        has_numbers_in_answer = any(c.isdigit() for c in content) and "บาท" in content
        has_fallback = "ยังดึง" in content or "ขออภัย" in content
        checks.append(("tool called", has_tool and (has_numbers_in_answer or not has_fallback)))

    # 2. Expected text substring?
    if case.expect_text:
        found = case.expect_text.lower() in content.lower()
        checks.append((f'contains "{case.expect_text}"', found))

    # 3. Excluded text?
    if case.expect_excludes:
        excluded = case.expect_excludes.lower() not in content.lower()
        checks.append((f'excludes "{case.expect_excludes}"', excluded))

    # 4. Price accuracy?
    if case.expect_price is not None:
        # Look for price pattern near expected value
        found = str(int(case.expect_price)) in content or str(case.expect_price) in content
        checks.append((f"price ~{case.expect_price}", found))

    # Build detail
    passed = all(ok for ok, _ in checks)
    detail_parts = [f"{'✅' if ok else '❌'} {label}" for ok, label in checks]
    detail_parts.append(f"⏱ {elapsed:.1f}s {usage.get('total_tokens',0)} tok")
    if not passed:
        # Show response snippet on failure
        detail_parts.append(f"📝 {content[:120].replace(chr(10), ' ')}...")

    return passed, " | ".join(detail_parts), response


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL, SKIP
    if ok is None:
        SKIP += 1
        print(f"  ⏭️  {label}")
    elif ok:
        PASS += 1
        print(f"  ✅ {label}  —  {detail}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  —  {detail}")


def main() -> int:
    print(f"{'='*70}")
    print(f"  Procurement Chat E2E Test")
    print(f"  Model: {MODEL_ID}  |  Target: {env('OWUI_URL')}")
    print(f"{'='*70}\n")

    results = []
    for case in TEST_CASES:
        tag_str = " ".join(f"[{t}]" for t in case.tags)
        print(f"\n── {case.id} {tag_str} ──")
        print(f"  Q: {case.message[:100]}")
        try:
            ok, detail, raw = evaluate(case)
        except Exception as e:
            ok, detail, raw = False, f"Exception: {e}", {}
        check(case.id, ok, detail)
        results.append({
            "id": case.id,
            "message": case.message,
            "passed": ok,
            "detail": detail,
            "tags": list(case.tags),
        })
        time.sleep(1)  # Rate limit

    # Save results
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    total = PASS + FAIL + SKIP
    print(f"\n{'='*70}")
    if FAIL == 0:
        print(f"  🎉 ALL {PASS}/{total} PASSED!")
    else:
        print(f"  PASS={PASS}  FAIL={FAIL}  SKIP={SKIP}  TOTAL={total}  ({PASS/total*100:.1f}%)")
    print(f"  Results saved: {CACHE_FILE}")
    print(f"{'='*70}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        raise SystemExit(2) from e