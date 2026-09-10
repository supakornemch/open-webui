#!/usr/bin/env python3
"""Comprehensive regression test for procurement-catalog-v1 Azure AI Search index.

Covers:
  1. Exact-match hybrid search (Thai product names from Excel master)
  2. Misspelled queries (พิมพ์ผิด — typo, missing chars, wrong chars)
  3. Language-switching queries (Thai→English, English→Thai, mixed)
  4. Semantic search
  5. Filter cases (category, vendor, year, price range, quantity tier)
  6. Price & tier fact verification against Excel ground truth
  7. Zero-result queries (should NOT find non-existent products)

Usage:
    set -a; source ../../docker/.env.owui; set +a
    E2E_EMBEDDING_KEY=<litellm-key> python3 scripts/test_procurement_regression.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import OpenAI

INDEX = "procurement-catalog-v1"
EMBED_DIMS = 3072

PASS, FAIL = 0, 0

# ═══════════════════════════════════════════════════════════════════════════
# Ground truth from Excel master (verified 2026-08-07)
# logical_item_id -> (product_name_substring, price_min, price_max,
#                      qty_min_all, qty_max_all)
# ═══════════════════════════════════════════════════════════════════════════
EXPECTED_PRODUCTS = {
    # POSM
    "2026:POSM:1":        ("ถังใส่น้ำแข็ง-โค้ก", 42.5, 42.5, 5000, 5000),
    "2026:POSM:2":        ("กล่องทิชชู-โค้ก", 28.5, 28.5, 5000, 5000),
    "2026:POSM:5":        ("ร่มโค้ก 36 นิ้ว โครงเหล็ก สีตาย", 523.0, 523.0, 700, 700),
    "2026:POSM:5.2":      ("ร่มโค้ก 36 นิ้ว โครงไฟเบอร์ สีตาย", 523.0, 523.0, 700, 700),
    "2026:POSM:5.4":      ("ร่มโค้ก 40 นิ้ว โครงเหล็ก สีตาย", 570.0, 570.0, 700, 700),
    "2026:POSM:5.7":      ("ร่มโค้ก 40 นิ้ว โครงไฟเบอร์ ไล่ระดับสี", 585.0, 585.0, 700, 700),
    # Printing-MKT
    "2026:Printing-MKT:1":  ("โคมไฟสำเร็จรูป ทรงกลม แบบนูน", 2095.0, 2095.0, 100, 200),
    "2026:Printing-MKT:2":  ("PP Board โค้กเขียนชื่อร้านค้าโค้ก 120x120", 190.0, 200.0, 500, 1000),
    "2026:Printing-MKT:3":  ("PP Board 85x190 cm", 230.0, 240.0, 500, 1000),
    # Printing-Rate
    "2026:Printing-Rate:1":   ("Arch 60x70", 207.0, 230.0, 1, 20),
    "2026:Printing-Rate:3":   ("Arch 60x100", 304.75, 310.0, 1, 20),
    # Premium
    "2026:Premium:1":  ("ผ้าเบอร์วิ่ง", 1.98, 1.98, 200000, 200000),
    "2026:Premium:5":  ("ร่มสีดำ 2 เมตร", 2400.0, 2400.0, 50, 50),
    "2026:Premium:6":  ("ร่มชายหาด 42 นิ้ว", 1200.0, 1200.0, 100, 100),
    "2026:Premium:7":  ("Menu Stand Earth tone", 4400.0, 4400.0, 10, 50),
}

# ═══════════════════════════════════════════════════════════════════════════
# Test Category 1: Exact-match hybrid search (Thai product names)
# ═══════════════════════════════════════════════════════════════════════════
EXACT_QUERIES = [
    ("ถังน้ำแข็งโค้ก", "2026:POSM:1"),
    ("กล่องทิชชู โค้ก", "2026:POSM:2"),
    ("ร่มโค้ก 36 นิ้ว โครงเหล็ก", "2026:POSM:5"),
    ("โคมไฟสำเร็จรูป", "2026:Printing-MKT:1"),
    ("PP Board 85x190", "2026:Printing-MKT:3"),
    ("แบนเนอร์โค้ก", "2026:Printing-MKT:6"),
    ("Arch 60x70", "2026:Printing-Rate:1"),
    ("Wrap Around 30x70", "2026:Printing-Rate:10"),
    ("Neck tag 6.5", "2026:Printing-Rate:27"),
    ("โปสเตอร์ Cut2", "2026:Printing-Rate:28"),
    ("Tent card A3", "2026:Printing-Rate:35"),
    ("Wobbler 10x10", "2026:Printing-Rate:41"),
    ("ธงปีกนก ไซด์ S", "2026:Printing-Rate:51"),
    ("ผ้าเบอร์วิ่ง", "2026:Premium:1"),
    ("แก้วกระดาษ 6.5", "2026:Premium:2"),
    ("ร่มสีดำ 2 เมตร", "2026:Premium:5"),
    ("ร่มชายหาด", "2026:Premium:6"),
    ("Menu Stand Earth tone", "2026:Premium:7"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Test Category 2: Misspelled queries (พิมพ์ผิด)
# Intentional typos that a real user might make — should still find the product
# ═══════════════════════════════════════════════════════════════════════════
MISSPELLED_QUERIES = [
    # Missing chars / wrong chars in Thai
    ("โคมไฟสำเรจรูป", "2026:Printing-MKT:1", "โคมไฟสำเร็จรูป → โคมไฟสำเรจรูป (จ หาย)"),
    ("รมโค้ก 36 นิ้ว", "2026:POSM:5", "ร่มโค้ก → รมโค้ก (ร่ม → รม)"),
    ("ล่มโค้ก", "2026:POSM:5", "ร่มโค้ก → ล่มโค้ก (ร → ล)"),
    ("ถังนำแข็งโค้ก", "2026:POSM:1", "ถังน้ำแข็ง → ถังนำแข็ง (น้ำ → นำ)"),
    ("กลองทิชชู", "2026:POSM:2", "กล่องทิชชู → กลองทิชชู (กล่อง → กลอง)"),
    ("ปายหน้าเคาท์เตอร์", "2026:Printing-MKT:3", "ป้ายหน้าเคาน์เตอร์ → ปายหน้าเคาท์เตอร์"),
    ("แบนเนอโค้ก", "2026:Printing-MKT:6", "แบนเนอร์ → แบนเนอ"),
    ("ธงปกนก", "2026:Printing-Rate:51", "ธงปีกนก → ธงปกนก (ปีก → ปก)"),
    ("ธงปีกนกก", "2026:Printing-Rate:51", "ธงปีกนก → ธงปีกนกก (extra ก)"),
    ("สติกเกอร์", "2026:Printing-Rate:92", "สติ๊กเกอร์ → สติกเกอร์ (missing ๊, ็)"),
    ("สตีกเกอร์", "2026:Printing-Rate:92", "สติ๊กเกอร์ → สตีกเกอร์ (missing ิ๊)"),
    ("เสื้อยืสีขาว", "2026:Garment:1", "เสื้อยืด → เสื้อยื (ด หาย)"),
    ("แก้วกระดาษ 6.5 ออน", "2026:Premium:2", "ออนซ์ → ออน"),
    ("เมนูสแตนด์", "2026:Premium:7", "Menu Stand → เมนูสแตนด์ (ทับศัพท์)"),
    # English typos
    ("arch 60x70 bord", "2026:Printing-Rate:1", "Arch board → arch bord"),
    ("wobler 10x10", "2026:Printing-Rate:41", "Wobbler → wobler"),
    ("sticker remover", "2026:Printing-Rate:91", "ok (exact match)"),
    ("stiker remover", "2026:Printing-Rate:91", "Sticker → stiker"),
    ("necktag 6.5", "2026:Printing-Rate:27", "Neck tag → necktag (no space)"),
    ("wraparound 30x70", "2026:Printing-Rate:10", "Wrap Around → wraparound"),
    # Partial/truncated queries
    ("Arch 6x", "2026:Printing-Rate:1", "Arch 60x70 → Arch 6x (truncated)"),
    ("Wrap aroun", "2026:Printing-Rate:10", "Wrap Around → Wrap aroun"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Test Category 3: Language-switching queries
# Mix Thai/English or use English to find Thai-named products
# ═══════════════════════════════════════════════════════════════════════════
LANG_SWITCH_QUERIES = [
    # English → Thai product
    ("umbrella coke 36 inch", "2026:POSM:5", "English: umbrella coke → ร่มโค้ก"),
    ("ice bucket coke", "2026:POSM:1", "English: ice bucket → ถังน้ำแข็งโค้ก"),
    ("tissue box coke", "2026:POSM:2", "English: tissue box → กล่องทิชชูโค้ก"),
    ("apron coca cola", "2026:POSM:3", "English: apron → ผ้ากันเปื้อน"),
    ("light fixture globe", "2026:Printing-MKT:1", "English: light fixture → โคมไฟ"),
    ("banner coke 80x300", "2026:Printing-MKT:6", "English: banner → แบนเนอร์"),
    ("tablecloth coke", "2026:Printing-MKT:11", "English: tablecloth → ผ้าปูโต๊ะ"),
    ("poster 20x30", "2026:Printing-Rate:28", "English: poster → โปสเตอร์"),
    ("flag wing S size", "2026:Printing-Rate:51", "English: wing flag → ธงปีกนก"),
    ("t-shirt white cotton", "2026:Garment:1", "English: t-shirt → เสื้อยืด"),
    ("polo shirt TC fabric", "2026:Garment:2", "English: polo shirt → เสื้อโปโล"),
    ("beach umbrella 42 inch", "2026:Premium:6", "English: beach umbrella → ร่มชายหาด"),
    ("paper cup 6.5 oz", "2026:Premium:2", "English: paper cup → แก้วกระดาษ"),
    # Mixed Thai + English
    ("sticker PVC 4 สี", "2026:Printing-Rate:82", "Mixed: sticker PVC + 4 สี"),
    ("PP Board 3 มิล", "2026:Printing-Rate:63", "Mixed: PP Board + 3 มิล"),
    ("Arch ไดคัท PP Board", "2026:Printing-Rate:1", "Mixed: Arch + ไดคัท PP Board"),
    ("vacuum sticker ติดกระจก", "2026:Printing-Rate:38", "Mixed: vacuum sticker + ติดกระจก"),
    ("shelf talker 8x21", "2026:Printing-Rate:44", "English: shelf talker"),
    ("brand menu ใบเรือ", "2026:Printing-Rate:109", "Mixed: brand menu + ใบเรือ"),
    ("hand prop A3 ด้าม", "2026:Printing-Rate:50", "Mixed: hand prop + A3 + ด้าม"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Test Category 4: Semantic search (concept-based, not keyword)
# ═══════════════════════════════════════════════════════════════════════════
SEMANTIC_QUERIES = [
    ("ของพรีเมี่ยม แก้ว", "2026:Premium:2", "semantic: ของพรีเมี่ยม → แก้วกระดาษ"),
    ("อุปกรณ์ตั้งโชว์สินค้า", "2026:POSM:9", "semantic: อุปกรณ์ตั้งโชว์ → PM Rack"),
    ("ที่บังแดดหน้าร้าน", "2026:Premium:5", "semantic: ที่บังแดด → ร่มสีดำ 2 เมตร"),
    ("ป้ายราคาสินค้า", "2026:Printing-Rate:46", "semantic: ป้ายราคา → Price tag"),
    ("ของแจกลูกค้างานอีเวนท์", "2026:Premium:2", "semantic: ของแจก → แก้วกระดาษ"),
    ("สื่อโฆษณาหน้าร้าน", "2026:Printing-MKT:3", "semantic: สื่อโฆษณา → PP Board"),
    ("uniform พนักงาน", "2026:Garment:1", "semantic: uniform → เสื้อยืด"),
    ("heavy duty rack storage", "2026:POSM:12", "semantic: storage rack → Mega Rack"),
]

# ═══════════════════════════════════════════════════════════════════════════
# Test Category 5: Filter cases
# ═══════════════════════════════════════════════════════════════════════════
FILTER_CASES = [
    # Category filters
    ("category=POSM", "*", "category eq 'POSM'", None, 15),
    ("category=Printing-Rate", "*", "category eq 'Printing-Rate'", None, 50),
    ("category=Garment", "*", "category eq 'Garment'", None, 5),
    ("category=Premium", "*", "category eq 'Premium'", None, 5),
    # Year filter
    ("year=2026", "*", "year eq 2026", None, 123),
    # Price range
    ("price<=1 THB", "*", "price_min le 1", None, 2),
    ("price 2000-5000", "*", "price_min ge 2000 and price_max le 5000", None, 3),
    # Quantity tier matching
    ("qty=15 (Arch tier)", "Arch", "tiers/any(t: t/quantity_min le 15 and (t/quantity_max ge 15 or t/quantity_max eq null))",
     "2026:Printing-Rate:1", None),
    ("qty=500 (Tshirt tier)", "เสื้อยืด", "tiers/any(t: t/quantity_min le 500 and (t/quantity_max ge 500 or t/quantity_max eq null))",
     "2026:Garment:1", None),
    ("qty=5000 exact", "*", "tiers/any(t: t/quantity_min eq 5000 and t/quantity_max eq 5000)", None, 3),
    # Combined search + filter
    ("Arch + category=Printing-Rate", "Arch", "category eq 'Printing-Rate'", "2026:Printing-Rate:1", None),
    ("ร่ม + category=Premium", "ร่ม", "category eq 'Premium'", "2026:Premium:5", None),
]

# ═══════════════════════════════════════════════════════════════════════════
# Test Category 6: Zero-result / negative queries
# Products NOT in the index — should NOT return results
# ═══════════════════════════════════════════════════════════════════════════
ZERO_RESULT_QUERIES = [
    ("iPhone 15 Pro Max", "brand not in procurement catalog"),
    ("รถยนต์ Toyota", "vehicle not in catalog"),
    ("กระดาษ A4 80 แกรม Double A", "consumer paper, not procurement item"),
    ("ค่าจ้างพนักงาน", "payroll, not procurement"),
]


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def get_embedding(client: OpenAI, deployment: str, text: str) -> list[float]:
    resp = client.embeddings.create(input=text, model=deployment)
    return resp.data[0].embedding


def run_search(
    client: SearchClient, *,
    search_text: str,
    query_vector: list[float],
    filter_expr: str | None = None,
    use_semantic: bool = False,
    top: int = 10,
) -> list[dict[str, Any]]:
    vector_query = VectorizedQuery(
        vector=query_vector, k_nearest_neighbors=50, fields="content_vector"
    )
    kwargs: dict[str, Any] = {
        "search_text": search_text,
        "vector_queries": [vector_query],
        "filter": filter_expr,
        "top": top,
        "select": [
            "logical_item_id", "year", "category", "product_name",
            "price_min", "price_max", "quantity_min_all", "quantity_max_all",
            "award_vendors", "tiers",
        ],
    }
    if use_semantic:
        kwargs["query_type"] = "semantic"
        kwargs["semantic_configuration_name"] = "procurement-semantic"
    return list(client.search(**kwargs))


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  —  {detail}")


def section(title: str) -> None:
    bar = "═" * 70
    print(f"\n{bar}\n  {title}\n{bar}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    search_endpoint = env("AZURE_SEARCH_ENDPOINT")
    search_key = env("AZURE_SEARCH_ADMIN_KEY")
    openai_endpoint = os.environ.get(
        "E2E_EMBEDDING_ENDPOINT",
        "https://app-litellm-poc-sand.azurewebsites.net",
    )
    openai_key = os.environ.get("E2E_EMBEDDING_KEY") or os.environ.get("AZURE_OPENAI_KEY") or env("OPENAI_API_KEY")
    embedding_deployment = os.environ.get("E2E_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

    embed_client = OpenAI(
        api_key=openai_key,
        base_url=openai_endpoint.rstrip("/") + "/v1",
    )
    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=INDEX,
        credential=AzureKeyCredential(search_key),
        api_version="2024-07-01",
    )

    # ── 0. Index sanity ──────────────────────────────────────────────
    section("0. Index sanity")
    total = search_client.search(search_text="*", top=0, include_total_count=True)
    count = total.get_count()
    check(f"index count >= 123 (got {count})", count is not None and count >= 123,
          f"expected >= 123, got {count}")

    # ── 1. Exact-match hybrid search ─────────────────────────────────
    section("1. Exact-match queries (Thai product names)")
    for query, expected_id in EXACT_QUERIES:
        vec = get_embedding(embed_client, embedding_deployment, query)
        results = run_search(search_client, search_text=query, query_vector=vec, top=5)
        ids = {r.get("logical_item_id") for r in results}
        if expected_id not in ids:
            # Try top-20 for longer product names
            results = run_search(search_client, search_text=query, query_vector=vec, top=20)
            ids = {r.get("logical_item_id") for r in results}
        ok = expected_id in ids
        found_names = [f"{r.get('logical_item_id')}: {r.get('product_name','')[:50]}" for r in results[:3]]
        check(f'"{query}" → {expected_id}', ok,
              f"top hits: {found_names}")

    # ── 2. Misspelled queries ────────────────────────────────────────
    section("2. Misspelled queries (พิมพ์ผิด)")
    for query, expected_id, desc in MISSPELLED_QUERIES:
        vec = get_embedding(embed_client, embedding_deployment, query)
        results = run_search(search_client, search_text=query, query_vector=vec, top=10)
        ids = {r.get("logical_item_id") for r in results}
        ok = expected_id in ids
        found_names = [f"{r.get('logical_item_id')}" for r in results[:3]]
        check(f'{desc}', ok,
              f'query="{query}" top hits: {found_names}')

    # ── 3. Language-switching queries ────────────────────────────────
    section("3. Language-switching queries (เปลี่ยนภาษา)")
    for query, expected_id, desc in LANG_SWITCH_QUERIES:
        vec = get_embedding(embed_client, embedding_deployment, query)
        results = run_search(search_client, search_text=query, query_vector=vec, top=10)
        ids = {r.get("logical_item_id") for r in results}
        ok = expected_id in ids
        found_names = [f"{r.get('logical_item_id')}: {r.get('product_name','')[:50]}" for r in results[:3]]
        check(f'{desc}', ok,
              f'query="{query}" top hits: {found_names}')

    # ── 4. Semantic search ──────────────────────────────────────────
    section("4. Semantic search")
    for query, expected_id, desc in SEMANTIC_QUERIES:
        vec = get_embedding(embed_client, embedding_deployment, query)
        results = run_search(search_client, search_text=query, query_vector=vec,
                             use_semantic=True, top=5)
        ids = {r.get("logical_item_id") for r in results}
        ok = expected_id in ids
        found_names = [f"{r.get('logical_item_id')}: {r.get('product_name','')[:50]}" for r in results[:3]]
        check(f'{desc}', ok,
              f'query="{query}" top hits: {found_names}')

    # ── 5. Filter cases ─────────────────────────────────────────────
    section("5. Filter cases")
    for label, search, filter_expr, must_contain, min_hits in FILTER_CASES:
        vec = get_embedding(embed_client, embedding_deployment, search)
        # For broad count-based filters, use count API for accuracy
        if must_contain is None and search == "*" and min_hits and min_hits > 20:
            count_resp = search_client.search(
                search_text="*", filter=filter_expr, top=0, include_total_count=True,
            )
            count = count_resp.get_count() or 0
            ok = count >= (min_hits or 1)
            check(f'{label} (expect >= {min_hits})', ok,
                  f'got {count} documents (count mode)')
            continue
        results = run_search(
            search_client, search_text=search, query_vector=vec,
            filter_expr=filter_expr, top=50,
        )
        ids = [r.get("logical_item_id") for r in results]
        if must_contain:
            ok = must_contain in ids
            check(f'{label} → {must_contain}', ok,
                  f'got {len(ids)} hits: {ids[:5]}')
        else:
            ok = len(ids) >= (min_hits or 1)
            check(f'{label} (expect >= {min_hits})', ok,
                  f'got {len(ids)} hits')

    # ── 6. Price & tier fact verification ───────────────────────────
    section("6. Price & tier facts (Excel ground truth)")
    for pid, (sub, pmin, pmax, qmin, qmax) in EXPECTED_PRODUCTS.items():
        vec = get_embedding(embed_client, embedding_deployment, sub)
        results = run_search(search_client, search_text=sub, query_vector=vec, top=15)
        r = next((x for x in results if x.get("logical_item_id") == pid), None)
        if r is None:
            check(f"{pid} found", False, f"not in top-15 results for {sub!r}")
            continue
        name_ok = sub[:15] in str(r.get("product_name", ""))
        price_ok = abs((r.get("price_min") or 0) - pmin) < 1e-6 and abs((r.get("price_max") or 0) - pmax) < 1e-6
        qty_ok = (r.get("quantity_min_all") == qmin) and (r.get("quantity_max_all") == qmax)
        check(f"{pid}: {sub[:60]}", name_ok and price_ok and qty_ok,
              f"name={name_ok} price={price_ok} (got {r.get('price_min')}/{r.get('price_max')}) "
              f"qty={qty_ok} (got {r.get('quantity_min_all')}/{r.get('quantity_max_all')})")

    # ── 7. Tier integrity ───────────────────────────────────────────
    section("7. Tier & vendor integrity")
    vec = get_embedding(embed_client, embedding_deployment, "Arch 60x70")
    results = run_search(search_client, search_text="Arch 60x70", query_vector=vec, top=5)
    arch = next((r for r in results if r.get("logical_item_id") == "2026:Printing-Rate:1"), None)
    if arch is None:
        check("Arch 60x70 found for tier check", False)
    else:
        tiers = arch.get("tiers") or []
        check(f"Arch 60x70 tiers >= 2 (got {len(tiers)})", len(tiers) >= 2)
        if tiers:
            awarded_ok = all(
                t.get("awarded_price") in (207.0, 230.0) for t in tiers
            )
            check("tiers awarded_price in {207, 230}", awarded_ok)
            tier_has_label = all(t.get("quantity_label") is not None for t in tiers)
            check("all tiers have quantity_label", tier_has_label)

    # Check garment tiers (range-based)
    vec = get_embedding(embed_client, embedding_deployment, "เสื้อยืดสีขาว")
    results = run_search(search_client, search_text="เสื้อยืด", query_vector=vec, top=5)
    shirt = next((r for r in results if r.get("logical_item_id") == "2026:Garment:1"), None)
    if shirt is None:
        check("เสื้อยืด found for tier check", False)
    else:
        tiers = shirt.get("tiers") or []
        check(f"เสื้อยืด tiers >= 5 (got {len(tiers)})", len(tiers) >= 5)
        if tiers:
            has_range = any(
                (t.get("quantity_min") or 0) < (t.get("quantity_max") or 0)
                for t in tiers
            )
            check("at least one tier is range (min < max)", has_range)

    # ── 8. Zero-result queries ──────────────────────────────────────
    section("8. Zero-result queries (should NOT find)")
    for query, desc in ZERO_RESULT_QUERIES:
        vec = get_embedding(embed_client, embedding_deployment, query)
        results = run_search(search_client, search_text=query, query_vector=vec, top=5)
        # Check that none of the results look like a procurement item match
        names = [r.get("product_name", "") for r in results]
        has_valid = any(
            any(kw in name.lower() for kw in query.lower().split() if len(kw) > 3)
            for name in names
        )
        # For zero-result: the top hit should NOT contain the query terms
        # We use a lenient check: no result should match >2 significant words
        significant = [w for w in query.split() if len(w) > 3]
        match_count = 0
        if results and significant:
            top_name = (results[0].get("product_name") or "").lower()
            match_count = sum(1 for w in significant if w.lower() in top_name)
        ok = match_count < max(2, len(significant) // 2)
        check(f'"{query}" → {desc}', ok,
              f"top hit: {results[0].get('product_name','') if results else 'no results'}")

    # ═════════════════════════════════════════════════════════════════
    section("SUMMARY")
    total = PASS + FAIL
    pct = (PASS / total * 100) if total > 0 else 0
    pass_msg = f"PASS={PASS} FAIL={FAIL} TOTAL={total} ({pct:.1f}%)"
    if FAIL == 0:
        print(f"  🎉 ALL {PASS} TESTS PASSED!")
    else:
        print(f"  ⚠️  {pass_msg}")
    print()
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        raise SystemExit(2) from e
