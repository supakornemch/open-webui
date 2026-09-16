#!/usr/bin/env python3
"""E2E regression harness for procurement-price-assistant on QAS.

Drives the OWUI tool-calling loop exactly like the web UI does:
  1. POST /api/chat/completions -> model emits tool_calls
  2. Execute the tool faithfully (same Azure AI Search + LiteLLM embedding
     path the server-side tool uses, with env from QAS app settings)
  3. POST the tool result back -> final answer
Then asserts expected price strings, exclusions, etc.

Usage: python3 qas_procurement_regression.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import OpenAI

# ── Config (QAS) ────────────────────────────────────────────────────────
OWUI_URL = "https://app-entchat-owui-qas.azurewebsites.net"
OWUI_KEY = open("/tmp/qas_owui_key.txt").read().strip()
MODEL = "procurement-price-assistant"

SEARCH_ENDPOINT = "https://srch-entchat-qas.search.windows.net"
SEARCH_KEY = "tLfXnXbmMSuchgSckUs2apeqOMevZWpwI4vGUISRVIAzSeAQhlVK"
SEARCH_INDEX = "procurement-catalog-v1"
LITELLM_BASE = "https://app-litellm-qas.azurewebsites.net"
LITELLM_KEY = open("/tmp/qas_litellm_key.txt").read().strip()
EMBED_MODEL = "deploy-embedding-3-large"

SELECT_FIELDS = [
    "logical_item_id", "year", "category", "product_name", "product_aliases",
    "product_type", "product_spec_text", "product_condition_text",
    "pricing_basis", "notes_text", "award_vendors", "price_min", "price_max",
    "quantity_min_all", "quantity_max_all", "tiers",
]

TOOL_SCHEMA = [{
    "type": "function",
    "function": {
        "name": "search_procurement_prices",
        "description": "Search procurement products. Hybrid retrieval: keyword + vector.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "category": {"type": "string", "enum": ["POSM", "Printing-MKT", "Printing-Rate", "Garment", "Premium"]},
                "year": {"type": "integer"},
                "min_price": {"type": "number"},
                "max_price": {"type": "number"},
                "quantity": {"type": "integer"},
                "use_semantic": {"type": "boolean", "default": False},
                "sort_by_price": {"type": "boolean", "default": False},
                "use_wildcard": {"type": "boolean", "default": False},
            },
            "required": ["query"],
        },
    },
}]

# ═══ Tool runtime (faithful copy of procurement-search.py logic) ════════
def get_embedding(text: str) -> list[float]:
    client = OpenAI(api_key=LITELLM_KEY, base_url=LITELLM_BASE.rstrip("/") + "/v1")
    resp = client.embeddings.create(input=text, model=EMBED_MODEL)
    return resp.data[0].embedding


def build_filter(category=None, year=None, min_price=None, max_price=None, quantity=None):
    f = []
    if category:
        f.append(f"category eq '{category}'")
    if year:
        f.append(f"year eq {year}")
    if min_price is not None:
        f.append(f"price_min ge {min_price}")
    if max_price is not None:
        f.append(f"price_max le {max_price}")
    if quantity is not None:
        f.append(
            f"tiers/any(t: t/quantity_min le {quantity} and "
            f"(t/quantity_max ge {quantity} or t/quantity_max eq null))"
        )
    return " and ".join(f) if f else None


def search_tool(query: str, category=None, year=None, min_price=None, max_price=None,
                quantity=None, use_semantic=False, sort_by_price=False,
                use_wildcard=False) -> str:
    client = SearchClient(
        endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY), api_version="2024-07-01",
    )
    vec = VectorizedQuery(vector=get_embedding(query), k_nearest_neighbors=50,
                          fields="content_vector")
    kwargs = {
        "search_text": query,
        "search_mode": "any",
        "vector_queries": [vec],
        "filter": build_filter(category, year, min_price, max_price, quantity),
        "top": 5,
        "select": SELECT_FIELDS,
    }
    if use_semantic:
        kwargs["query_type"] = "semantic"
        kwargs["semantic_configuration_name"] = "procurement-semantic"

    results_list = list(client.search(**kwargs))

    # category fallback
    category_dropped = False
    if not results_list and kwargs["filter"] and category:
        kwargs["filter"] = build_filter(None, year, min_price, max_price, quantity)
        results_list = list(client.search(**kwargs))
        category_dropped = results_list is not None and len(results_list) > 0

    # quantity fallback
    quantity_dropped = False
    if not results_list and kwargs["filter"] and quantity is not None:
        kwargs["filter"] = build_filter(category, year, min_price, max_price, None)
        results_list = list(client.search(**kwargs))
        quantity_dropped = len(results_list) > 0

    if sort_by_price and results_list:
        results_list.sort(key=lambda r: r.get("price_min") if r.get("price_min") is not None else float("inf"))

    items = []
    for r in results_list:
        tiers = [{
            "lead_time": t.get("lead_time"), "quantity_label": t.get("quantity_label"),
            "quantity_min": t.get("quantity_min"), "quantity_max": t.get("quantity_max"),
            "awarded_price": t.get("awarded_price"),
        } for t in (r.get("tiers") or [])]
        items.append({
            "logical_item_id": r.get("logical_item_id"), "year": r.get("year"),
            "category": r.get("category"), "product_name": r.get("product_name"),
            "product_aliases": r.get("product_aliases") or [],
            "product_type": r.get("product_type"), "pricing_basis": r.get("pricing_basis"),
            "product_spec_text": r.get("product_spec_text"),
            "product_condition_text": r.get("product_condition_text"),
            "notes_text": r.get("notes_text"), "award_vendors": r.get("award_vendors") or [],
            "price_min": r.get("price_min"), "price_max": r.get("price_max"),
            "quantity_min_all": r.get("quantity_min_all"),
            "quantity_max_all": r.get("quantity_max_all"), "tiers": tiers,
        })

    if items:
        response = {"success": True, "query": query, "total_results": len(items), "results": items}
        if category_dropped:
            response["warning"] = f"ไม่พบผลเมื่อ filter category='{category}' → ค้นใหม่โดยไม่ระบุ category"
        if quantity_dropped:
            response["warning"] = f"ไม่พบผลเมื่อ filter quantity={quantity} → ค้นใหม่โดยไม่ระบุจำนวน (MOQ อาจสูงกว่าที่ขอ)"
        return json.dumps(response, ensure_ascii=False, indent=2)
    return json.dumps({"success": True, "query": query, "total_results": 0,
                       "message": "ไม่พบสินค้าที่ตรงกับเงื่อนไข"}, ensure_ascii=False, indent=2)


# ═══ Chat loop driver ═══════════════════════════════════════════════════
def chat_with_tools(message: str, max_rounds: int = 3, timeout: int = 240):
    messages = [{"role": "user", "content": message}]
    tool_trace = []
    for _ in range(max_rounds):
        r = requests.post(
            f"{OWUI_URL}/api/chat/completions",
            headers={"Authorization": f"Bearer {OWUI_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "tools": TOOL_SCHEMA,
                  "tool_choice": "auto", "stream": False},
            timeout=timeout,
        )
        if r.status_code != 200:
            return f"[HTTP {r.status_code}] {r.text[:200]}", tool_trace
        d = r.json()
        ch = d["choices"][0]
        msg = ch["message"]
        if ch.get("finish_reason") == "tool_calls" and msg.get("tool_calls"):
            messages.append(msg)
            for tc in msg["tool_calls"]:
                fn = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"] or "{}")
                if fn == "search_procurement_prices":
                    result = search_tool(**args)
                else:
                    result = json.dumps({"error": f"unknown tool {fn}"})
                tool_trace.append({"name": fn, "args": args,
                                   "n_results": json.loads(result).get("total_results")})
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": result})
            continue
        return msg.get("content") or "", tool_trace
    return "[max rounds reached without final answer]", tool_trace


# ═══ Test cases ═════════════════════════════════════════════════════════
TEST_CASES = [
    # Exact match
    ("EX-01", "ร่มโค้ก 36 นิ้ว โครงเหล็ก ราคาเท่าไหร่", ["523"], None),
    ("EX-02", "โคมไฟสำเร็จรูป ราคาเท่าไหร่", ["2095"], None),
    ("EX-04", "Arch 60x70 cm ราคาเท่าไหร่", ["207"], None),
    # Misspelling
    ("TY-01", "โคมไฟสำเรจรูป ราคาเท่าไหร่", ["2095"], None),
    ("TY-02", "รมโค้ก 36 นิ้ว ราคา", ["523"], None),
    # Language switching
    ("LS-01", "how much is coke umbrella 36 inch", ["523"], None),
    ("LS-03", "how much is beach umbrella 42 inch", ["1200"], None),
    # Quantity tier
    ("QT-01", "Arch 60x70 15 อัน ราคาเท่าไหร่", ["207"], None),
    ("QT-02", "Arch 60x70 5 อัน ราคา", ["230"], None),
    # Variant clarification (tool must run, answer may ask for spec)
    ("VC-01", "ร่มโค้ก 10 อัน ราคาเท่าไหร่", [], None),
    # Zero result
    ("ZR-01", "iPhone 15 Pro Max ราคาเท่าไหร่", [], "บาท"),
    # Natural Thai
    ("TH-02", "เช็คราคาถังน้ำแข็งโค้กให้หน่อย", ["42.5"], None),
    # Unit pricing
    ("UP-01", "ถังน้ำแข็งโค้ก ราคาต่ออันเท่าไหร่", ["42.5"], None),
]

# Sanity: ground-truth from the index for tier prices
def ground_truths():
    """Fetch expected values directly from the index to avoid stale assertions."""
    client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=SEARCH_INDEX,
                          credential=AzureKeyCredential(SEARCH_KEY), api_version="2024-07-01")
    out = {}
    for name in ["ร่มโค้ก 36 นิ้ว - โครงเหล็ก", "โคมไฟสำเร็จรูป", "ถังน้ำแข็ง"]:
        res = list(client.search(search_text=name, top=3, select=["product_name", "price_min", "tiers", "category"]))
        out[name] = [(r["product_name"], r.get("price_min"), r.get("tiers")) for r in res]
    return out


def main():
    print("=" * 72)
    print("  Procurement Assistant E2E Regression — QAS")
    print(f"  Model: {MODEL} | Target: {OWUI_URL}")
    print("=" * 72, "\n")

    gt = ground_truths()
    for k, v in gt.items():
        print(f"  [ground truth] {k}:")
        for pn, pmin, tiers in v[:2]:
            tier_str = ", ".join(f"{t.get('quantity_label')}→{t.get('awarded_price')}" for t in (tiers or []))
            print(f"     - {pn} | price_min={pmin} | tiers: {tier_str}")
    print()

    passed = failed = 0
    results = []
    for tid, q, expects, excludes in TEST_CASES:
        t0 = time.time()
        try:
            answer, trace = chat_with_tools(q)
        except Exception as e:
            answer, trace = f"[EXC] {e}", []
        dt = time.time() - t0

        checks = []
        if trace:
            checks.append(("tool called", True))
        elif excludes != "บาท":
            checks.append(("tool called", False))

        for want in expects:
            found = want.lower() in (answer or "").lower()
            if not found and want.replace('.', '').isdigit():
                # models may format 2095 as 2,095
                if "." in str(want):
                    found = f"{float(want):,.2f}" in (answer or "") or str(want) in (answer or "")
                else:
                    found = f"{int(want):,}" in (answer or "")
                if want in (answer or ""):
                    found = True
            checks.append((f'contains "{want}"', found))
        if excludes:
            checks.append((f'excludes "{excludes}"', excludes.lower() not in (answer or "").lower()))

        ok = all(c[1] for c in checks)
        passed += ok
        failed += (not ok)
        flag = "✅ PASS" if ok else "❌ FAIL"
        tool_note = f"tool×{len(trace)}" if trace else "no-tool"
        print(f"{flag} {tid} ({dt:.0f}s, {tool_note}) Q: {q[:48]}")
        for label, c in checks:
            if not c:
                print(f"      ↳ ❌ {label}")
        if not ok:
            print(f"      ↳ answer: {(answer or '')[:220].replace(chr(10), ' ')}")
            if trace:
                print(f"      ↳ trace: {json.dumps(trace, ensure_ascii=False)[:200]}")
        results.append({"id": tid, "q": q, "passed": ok, "answer": answer,
                        "tool_trace": trace})

        time.sleep(1)

    total = passed + failed
    print("\n" + "=" * 72)
    print(f"  RESULT: {passed}/{total} passed ({passed / total * 100:.0f}%)")
    print("=" * 72)

    out = Path(__file__).parent / "qas-regression-results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  saved: {out}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
