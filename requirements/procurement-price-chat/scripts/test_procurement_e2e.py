#!/usr/bin/env python3
"""E2E regression test for the procurement price search tool.

Replicates what the Open WebUI tool (procurement_price_search v3.0) does, so we
can verify end-to-end against the live Azure AI Search index without the chat
layer:

  1. Generate a query embedding via the same LiteLLM proxy endpoint/keys the
     tool valves use (text-embedding-3-large, 3072 dims).
  2. Hybrid search (keyword + vector) against procurement-catalog-v1.
  3. Exercise filters: category / vendor / year / price range / quantity tier.
  4. Assert the results match the products we KNOW are in the index.

Run later (needs VPN + env):
    set -a; source ../../docker/.env.owui; set +a
    python3 scripts/test_procurement_e2e.py
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

# --------------------------------------------------------------------------
# Product facts we expect in the index (sourced from the Excel master data).
# logical_item_id -> (product_name_substring, min_award, max_award,
#                      quantity_min_all, quantity_max_all)
# --------------------------------------------------------------------------
EXPECTED_PRODUCTS = {
    "2026:Printing-Rate:1": ("Arch 60x70", 207.0, 230.0, 1, 20),
    "2026:Printing-MKT:1": ("โคมไฟสำเร็จรูป", 2095.0, 2095.0, 100, 200),
    "2026:Printing-Rate:3": ("Arch 60x100", 304.75, 310.0, 1, 20),
}

# Queries that MUST return at least one of the expected products.
QUERY_CASES = [
    ("Arch 60x70", {"logical_item_id": "2026:Printing-Rate:1"}),
    ("โคมไฟสำเร็จรูป ทรงกลม", {"logical_item_id": "2026:Printing-MKT:1"}),
    ("PP Board Arch", {"logical_item_id": "2026:Printing-Rate:3"}),
]

FILTER_CASES = [
    ("category=Printing-Rate", {"search": "*", "filter": "category eq 'Printing-Rate'", "min_hits": 1}),
    ("year=2026", {"search": "*", "filter": "year eq 2026", "min_hits": 1}),
    (
        "vendor=บจก.กราฟฟิกเน็กซ์",
        {"search": "*", "filter": "vendor_keys/any(v: v eq 'บจก.กราฟฟิกเน็กซ์')", "min_hits": 1},
    ),
    (
        "price_min<=250",
        {"search": "Arch", "filter": "price_min le 250", "min_hits": 1},
    ),
    (
        "quantity=15 (tier 1-20 of Arch 60x70)",
        {
            "search": "Arch",
            "filter": "tiers/any(t: t/quantity_min le 15 and (t/quantity_max ge 15 or t/quantity_max eq null))",
            "must_contain": "2026:Printing-Rate:1",
        },
    ),
    (
        "quantity=5000 (exact tier)",
        {
            "search": "*",
            "filter": "tiers/any(t: t/quantity_min le 5000 and (t/quantity_max ge 5000 or t/quantity_max eq null))",
            "min_hits": 1,
        },
    ),
]

PASS, FAIL = 0, 0


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def get_embedding(client: OpenAI, deployment: str, text: str) -> list[float]:
    resp = client.embeddings.create(input=text, model=deployment)
    return resp.data[0].embedding


def run_search(client: SearchClient, *, search_text: str, query_vector: list[float],
               filter_expr: str | None = None, use_semantic: bool = False,
               top: int = 10) -> list[dict[str, Any]]:
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
            "award_vendors", "vendor_names", "tiers",
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
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}  {detail}")


def main() -> int:
    search_endpoint = env("AZURE_SEARCH_ENDPOINT")
    search_key = env("AZURE_SEARCH_ADMIN_KEY")
    # Embedding endpoint = the LiteLLM proxy the tool valves use (NOT the
    # Azure OpenAI direct endpoint from .env.owui). Overridable via env.
    openai_endpoint = os.environ.get(
        "E2E_EMBEDDING_ENDPOINT",
        "https://app-litellm-poc-sand.azurewebsites.net",
    )
    openai_key = os.environ.get("E2E_EMBEDDING_KEY") or env("AZURE_OPENAI_KEY")
    embedding_deployment = os.environ.get("E2E_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

    # ---- embedding client (same as tool valves, OpenAI-compatible) ----
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

    # ---- 0. index count ----
    print("== index sanity ==")
    total = search_client.search(search_text="*", top=0, include_total_count=True)
    count = total.get_count()
    check(f"index count >= 123 (got {count})", count is not None and count >= 123)
    print()

    # ---- 1. query cases (hybrid, expect specific product) ----
    print("== query cases (hybrid) ==")
    for query, expect in QUERY_CASES:
        vec = get_embedding(embed_client, embedding_deployment, query)
        check(f"embedding dims == {EMBED_DIMS}", len(vec) == EMBED_DIMS, f"got {len(vec)}")
        results = run_search(search_client, search_text=query, query_vector=vec)
        ids = {r.get("logical_item_id") for r in results}
        ok = expect["logical_item_id"] in ids
        check(f'query "{query}" -> {expect["logical_item_id"]}', ok, f"got {ids}")
    print()

    # ---- 2. semantic query ----
    print("== semantic query ==")
    vec = get_embedding(embed_client, embedding_deployment, "โคมไฟสำเร็จรูป ทรงกลม แบบนูน")
    results = run_search(search_client, search_text="โคมไฟสำเร็จรูป ทรงกลม แบบนูน",
                         query_vector=vec, use_semantic=True)
    ids = [r.get("logical_item_id") for r in results]
    check('semantic "โคมไฟ" top1 == 2026:Printing-MKT:1',
          ids and ids[0] == "2026:Printing-MKT:1", f"got {ids[:3]}")
    print()

    # ---- 3. filter cases ----
    print("== filter cases ==")
    for label, cfg in FILTER_CASES:
        vec = get_embedding(embed_client, embedding_deployment, cfg.get("search", "*"))
        results = run_search(search_client, search_text=cfg["search"], query_vector=vec,
                             filter_expr=cfg.get("filter"))
        ids = [r.get("logical_item_id") for r in results]
        if "must_contain" in cfg:
            check(f'filter "{label}" contains {cfg["must_contain"]}',
                  cfg["must_contain"] in ids, f"got {ids[:5]}")
        else:
            check(f'filter "{label}" hits >= {cfg.get("min_hits", 1)}',
                  len(ids) >= cfg.get("min_hits", 1), f"got {len(ids)}")
    print()

    # ---- 4. exact product facts (search each with its own query) ----
    print("== product facts ==")
    for pid, (sub, pmin, pmax, qmin, qmax) in EXPECTED_PRODUCTS.items():
        vec = get_embedding(embed_client, embedding_deployment, sub)
        results = run_search(search_client, search_text=sub, query_vector=vec, top=10)
        r = next((x for x in results if x.get("logical_item_id") == pid), None)
        if r is None:
            check(f"{pid} found", False, f"not in top-10 results for {sub!r}")
            continue
        name_ok = sub in str(r.get("product_name", ""))
        price_ok = abs((r.get("price_min") or 0) - pmin) < 1e-6 and abs((r.get("price_max") or 0) - pmax) < 1e-6
        qty_ok = (r.get("quantity_min_all") == qmin) and (r.get("quantity_max_all") == qmax)
        check(f"{pid} name/price/qty", name_ok and price_ok and qty_ok,
              f"name={name_ok} price={price_ok} qty={qty_ok} got={r.get('price_min')}/{r.get('price_max')}")
    print()

    # ---- 5. tier & vendor_quotes integrity ----
    print("== tier integrity ==")
    vec = get_embedding(embed_client, embedding_deployment, "Arch 60x70")
    results = run_search(search_client, search_text="Arch 60x70", query_vector=vec, top=5)
    arch = next((r for r in results if r.get("logical_item_id") == "2026:Printing-Rate:1"), None)
    if arch is None:
        check("Arch 60x70 found for tier check", False)
    else:
        tiers = arch.get("tiers") or []
        # With duration expansion: 2 qty tiers × 4 durations = 8 tiers
        check(f"Arch 60x70 has 8 tiers (2 qty × 4 durations, got {len(tiers)})", len(tiers) == 8)
        awarded_ok = all(
            t.get("awarded_price") in (207.0, 230.0) for t in tiers
        )
        check("tiers awarded_price in {207, 230}", awarded_ok)
        quote_ok = all(
            any(q.get("is_awarded") is True for q in (t.get("vendor_quotes") or []))
            for t in tiers
        )
        check("each tier has an is_awarded quote", quote_ok)
    print()

    print(f"==== RESULT: {PASS} passed, {FAIL} failed ====")
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1) from e
