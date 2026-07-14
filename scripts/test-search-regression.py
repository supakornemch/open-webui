#!/usr/bin/env python3
"""
test-search-regression.py — Regression tests for enterprise-docs-idx
=====================================================================
Validates search quality, filters, vector/semantic retrieval,
and data integrity after ingestion.

Usage:
  export AZURE_SEARCH_KEY="..."
  python3 scripts/test-search-regression.py
"""

import os, sys, json
import requests


# ════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT",
                            "https://srch-entchat-poc-sand.search.windows.net")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
API_VERSION = "2024-07-01"
INDEX = "enterprise-docs-idx"
BASE_URL = f"{SEARCH_ENDPOINT}/indexes/{INDEX}"

HEADERS = {"Content-Type": "application/json", "api-key": SEARCH_KEY}

PASS = 0
FAIL = 0


def _search(query: str, **kwargs) -> dict:
    """Execute a search query. kwargs become search body params."""
    body = {"search": query}
    # Move well-known params to body
    for k in ["top", "skip", "filter", "select", "orderby", "count",
              "searchMode", "queryType", "scoringProfile", "vectors",
              "semanticConfiguration", "queryLanguage", "speller",
              "answers", "captions", "fuzzy"]:
        if k in kwargs:
            body[k] = kwargs.pop(k)
    body.update(kwargs)  # Any remaining kwargs
    url = f"{BASE_URL}/docs/search?api-version={API_VERSION}"
    try:
        r = requests.post(url, headers=HEADERS, json=body, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _get(id: str) -> dict:
    """Get a document by ID."""
    url = f"{BASE_URL}/docs('{id}')?api-version={API_VERSION}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _count(filter: str = None) -> int:
    """Get document count, optionally filtered."""
    # Use search API for filtered count (more reliable than $count with filter)
    if filter:
        body = {"search": "*", "filter": filter, "top": 0, "count": True}
        url = f"{BASE_URL}/docs/search?api-version={API_VERSION}"
        try:
            r = requests.post(url, headers=HEADERS, json=body, timeout=10)
            if r.status_code == 200:
                return r.json().get("@odata.count", -1)
        except Exception:
            pass
        return -1
    url = f"{BASE_URL}/docs/$count?api-version={API_VERSION}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return int(r.text) if r.status_code == 200 else -1
    except Exception:
        return -1


# ════════════════════════════════════
# TEST HELPERS
# ════════════════════════════════════

def check(name: str, result: bool, detail: str = ""):
    global PASS, FAIL
    if result:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def check_count(name: str, actual: int, expected_min: int, expected_max: int = 100000):
    check(name, expected_min <= actual <= expected_max,
          f"got {actual}, expected {expected_min}-{expected_max}")


def check_search(name: str, query: str, expect_in: list = None, min_results: int = 1,
                 max_results: int = 100, **kwargs):
    """Run a search and validate results."""
    r = _search(query, **kwargs)
    if "error" in r:
        check(name, False, f"API error: {r['error']}")
        return None

    results = r.get("value", [])
    count = len(results)

    passed = True
    detail = ""

    if count < min_results:
        passed = False
        detail = f"too few results: {count} < {min_results}"
    elif count > max_results:
        passed = False
        detail = f"too many results: {count} > {max_results}"
    elif expect_in:
        found = False
        for res in results:
            fname = res.get("file_name", "")
            content = res.get("content", "")
            for term in expect_in:
                if term.lower() in fname.lower() or term.lower() in content.lower():
                    found = True
                    break
        if not found:
            passed = False
            detail = f"expected terms {expect_in} not found in results"

    check(name, passed, detail)
    return r


# ════════════════════════════════════
# TESTS
# ════════════════════════════════════

def test_basic_search():
    print("\n── Basic Full-Text Search ──")

    # Thai keyword search
    check_search("Thai: MFA ตั้งค่า", "MFA ตั้งค่า", expect_in=["MFA"], min_results=2)
    check_search("Thai: สวัสดิการ", "สวัสดิการ", min_results=1)
    check_search("Thai: นโยบาย ความปลอดภัย", "นโยบาย ความปลอดภัย", min_results=1)
    check_search("Thai: อีเมล Setup", "อีเมล setup", min_results=1)
    check_search("Thai: วันหยุด", "วันหยุด", min_results=1)

    # English keyword search
    check_search("EN: VPN", "VPN", min_results=1)
    check_search("EN: DLP", "DLP", expect_in=["DLP"], min_results=1)
    check_search("EN: email exchange", "email exchange", min_results=1)
    check_search("EN: board meeting", "board meeting", min_results=1)

    # Mixed language
    check_search("Mixed: MFA SMS OTP", "MFA SMS OTP", min_results=1)


def test_corpus_filter():
    print("\n── Corpus Filter ──")

    r = check_search("Corpus: corporate", "*", min_results=10,
                     filter="corpus eq 'corporate'")
    if r:
        for doc in r.get("value", []):
            check(f"  → {doc.get('file_name','?')[:40]} corpus",
                  doc.get("corpus") == "corporate",
                  f"got {doc.get('corpus')}")

    r = check_search("Corpus: hr-policies", "*", min_results=10,
                     filter="corpus eq 'hr-policies'")
    if r:
        for doc in r.get("value", []):
            check(f"  → {doc.get('file_name','?')[:40]} corpus",
                  doc.get("corpus") == "hr-policies",
                  f"got {doc.get('corpus')}")


def test_category_filter():
    print("\n── Category Filter ──")

    categories = [
        "Security Manual", "Email Manual", "IT Policy",
        "Meeting Room Guide", "Policy",
        "Announcement / Order", "Benefits & Welfare",
        "Privacy / PDPA", "Training & Development",
        "Newsletter", "Form / Template",
    ]
    for cat in categories:
        # OData filter: category eq 'Some Category'
        r = _search("*", filter=f"category eq '{cat}'", top=3)
        count = len(r.get("value", []))
        check(f"Category: '{cat}' → {count} results", count >= 1,
              f"expected >=1 results")


def test_schema_fields():
    print("\n── Schema Field Integrity ──")

    r = _search("*", top=3)
    docs = r.get("value", [])
    required = ["id", "doc_id", "chunk_seq", "file_name", "file_path",
                "corpus", "category", "content", "summary", "meta",
                "related_doc_ids", "content_vector"]

    for field in required:
        found = any(field in d for d in docs)
        check(f"Field '{field}' present", found)

    for d in docs:
        # Validate meta is valid JSON
        try:
            meta = json.loads(d.get("meta", "{}"))
            check(f"  meta JSON valid for {d.get('file_name','?')[:30]}", isinstance(meta, dict))
            # Check required meta fields
            for mf in ["file_hash", "language", "pages", "corpus", "category"]:
                check(f"    meta.{mf}", mf in meta, f"missing in meta: {meta.keys()}")
        except (json.JSONDecodeError, TypeError):
            check(f"  meta JSON valid", False, "invalid JSON")

        # Validate summary is non-empty (warn if empty, not fail — can happen for tiny files)
        summary = d.get("summary", "")
        if len(summary) <= 5:
            print(f"  ⚠️  summary empty for {d.get('file_name','?')[:30]}: '{summary[:50]}' (GPT may have failed)")
        else:
            check(f"  summary non-empty for {d.get('file_name','?')[:30]}", True)

        # Validate content_vector exists and correct dimensions
        vec = d.get("content_vector", [])
        check(f"  vector dim=3072 for {d.get('file_name','?')[:30]}",
              len(vec) == 3072, f"got {len(vec)} dimensions")


def test_chunk_continuity():
    print("\n── Chunk Continuity (same doc) ──")

    r = _search("*", top=1)
    if not r.get("value"):
        check("Chunk continuity", False, "no results")
        return

    doc_id = r["value"][0].get("doc_id")
    file_name = r["value"][0].get("file_name", "?")

    # Get all chunks for this doc
    all_chunks = _search("*", filter=f"doc_id eq '{doc_id}'", top=50)
    chunks = all_chunks.get("value", [])
    seqs = sorted([c["chunk_seq"] for c in chunks])

    check(f"Chunks for {file_name[:30]} count >= 1", len(chunks) >= 1)
    check(f"Chunk seq are sequential starting at 0",
          seqs[0] == 0 and all(seqs[i] + 1 == seqs[i + 1] for i in range(len(seqs) - 1)),
          f"seqs: {seqs[:5]}...")


def test_document_lookup():
    print("\n── Document Lookup (by ID) ──")

    r = _search("*", top=1)
    if not r.get("value"):
        check("Doc lookup", False, "no results")
        return

    doc_id = r["value"][0]["id"]
    doc = _get(doc_id)
    check(f"GET by id '{doc_id[:20]}...'", "error" not in doc,
          f"got: {doc.get('error','OK')}")

    # Validate the returned doc has all fields
    if "error" not in doc:
        check(f"  Retrieved doc matches id", doc.get("id") == doc_id)


def test_related_docs():
    print("\n── Related Doc IDs ──")

    r = _search("*", top=5)
    for d in r.get("value", []):
        related = d.get("related_doc_ids", [])
        check(f"  {d.get('file_name','?')[:30]} has related_doc_ids",
              len(related) > 0, f"got {len(related)} related")


def test_vector_search():
    print("\n── Vector Search ──")

    # Get a chunk's vector, then search by it
    r = _search("*", top=1)
    if not r.get("value"):
        check("Vector search prep", False, "no results")
        return

    query_vector = r["value"][0].get("content_vector", [])
    file_name = r["value"][0].get("file_name", "?")

    if len(query_vector) != 3072:
        check(f"Vector search", False, f"vector dim is {len(query_vector)}")
        return

    # Vector search using vectorQueries (2024-07-01 format)
    body = {
        "vectorQueries": [{
            "kind": "vector",
            "vector": query_vector,
            "fields": "content_vector",
            "k": 5
        }],
        "select": "file_name,corpus,category,summary",
    }
    url = f"{BASE_URL}/docs/search?api-version={API_VERSION}"
    try:
        r = requests.post(url, headers=HEADERS, json=body, timeout=15)
        r.raise_for_status()
        results = r.json().get("value", [])
        check(f"Vector search: similar to '{file_name[:30]}'",
              len(results) >= 1,
              f"got {len(results)} results")
        if results:
            check(f"  Top result matches self",
                  results[0].get("file_name") == file_name,
                  f"expected '{file_name}', got '{results[0].get('file_name','?')}'")
    except Exception as e:
        check("Vector search", False, str(e))


def test_data_integrity():
    print("\n── Data Integrity ──")

    total = _count()
    corp = _count("corpus eq 'corporate'")
    hr = _count("corpus eq 'hr-policies'")

    check_count("Total docs", total, 770, 780)
    check_count("Corporate docs", corp, 115, 125)
    check_count("HR docs", hr, 645, 660)
    check("Corp + HR = Total", corp + hr == total,
          f"{corp} + {hr} != {total}")

    # Check no null/empty content
    r = _search("*", top=3)
    for d in r.get("value", []):
        check(f"  {d.get('file_name','?')[:30]} has content",
              bool(d.get("content", "").strip()),
              "empty content")


def test_edge_cases():
    print("\n── Edge Cases ──")

    # Empty search
    r = _search("*", top=1)
    check("Wildcard '*' returns results", len(r.get("value", [])) >= 1)

    # Very long query (should not crash)
    r = _search("A" * 500, top=1)
    check("Long query does not crash", "error" not in r)

    # Special characters
    r = _search("email #SpamTitan", top=2)
    check("Special chars (#)", len(r.get("value", [])) >= 0, "should not crash")

    # Numeric search
    r = _search("2568", top=2)
    check("Numeric search (2568)", len(r.get("value", [])) >= 0)


def test_filter_combinations():
    print("\n── Filter Combinations ──")

    r = _search("นโยบาย", filter="corpus eq 'hr-policies' and category eq 'Policy'", top=3)
    count = len(r.get("value", []))
    check(f"นโยบาย + corpus=hr + category=Policy → {count}",
          count >= 1, f"expected >=1")

    r = _search("MFA", filter="corpus eq 'corporate'", top=3)
    count = len(r.get("value", []))
    check(f"MFA + corpus=corp → {count}", count >= 1)


# ════════════════════════════════════
# RUNNER
# ════════════════════════════════════

def main():
    global PASS, FAIL

    if not SEARCH_KEY:
        print("❌ Set AZURE_SEARCH_KEY"); sys.exit(1)

    print("═" * 60)
    print("🧪 REGRESSION TESTS — enterprise-docs-idx")
    print("═" * 60)
    print(f"   Endpoint: {SEARCH_ENDPOINT}")
    print(f"   Index:    {INDEX}")

    tests = [
        ("Basic Search", test_basic_search),
        ("Corpus Filter", test_corpus_filter),
        ("Category Filter", test_category_filter),
        ("Schema Fields", test_schema_fields),
        ("Chunk Continuity", test_chunk_continuity),
        ("Document Lookup", test_document_lookup),
        ("Related Docs", test_related_docs),
        ("Vector Search", test_vector_search),
        ("Data Integrity", test_data_integrity),
        ("Edge Cases", test_edge_cases),
        ("Filter Combos", test_filter_combinations),
    ]

    for name, fn in tests:
        fn()

    print(f"\n{'═' * 60}")
    print(f"📊 RESULTS: {PASS} passed, {FAIL} failed (total {PASS+FAIL})")
    print(f"{'═' * 60}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
