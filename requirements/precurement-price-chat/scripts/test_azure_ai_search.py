#!/usr/bin/env python3
"""
Test Azure AI Search for procurement items.

Goal: Validate that vector search quality > keyword match for Thai product names.

Steps:
1. Create index `procurement-items-idx` (vector + BM25)
2. Extract 88 items from Excel
3. Generate embeddings + upload
4. Run test queries (typo / numeric / word-order variants)
5. Compare results with naive keyword match
"""

import os, sys, json, time
from pathlib import Path
import openpyxl
import requests

# === Config ===
SEARCH_ENDPOINT = "https://srch-entchat-poc-sand.search.windows.net"
SEARCH_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]
EMBED_ENDPOINT = "https://aif-entchat-poc-sand.cognitiveservices.azure.com"
EMBED_KEY = os.environ["OPENAI_API_KEY"]   # AI Foundry key (not search admin key)
EMBED_DEPLOYMENT = "deploy-embedding-3-large"
EMBED_DIM = 3072
INDEX_NAME = "procurement-items-idx"
API_VERSION = "2024-07-01"
API_VERSION_OPENAI = "2024-12-01-preview"

HERE = Path(__file__).parent
PRICE_FILE = HERE.parent / "Trade Marketing Materials price for Y2026.final.xlsx"

CAT_MAP = {
    "1.POSM(MKT)": "POSM",
    "2.Printing(MKT)": "Printing",
    "3.Garment": "Garment",
    "4.สรุปPremium": "Premium",
    "5.Printing-Rate1-43": "PrintRate",
    "5.Printing-Rate44-109": "PrintRate",
}


def h():
    return {"api-key": SEARCH_KEY, "Content-Type": "application/json"}


def ho():
    return {"api-key": EMBED_KEY, "Content-Type": "application/json"}


def embed(text: str) -> list[float]:
    url = f"{EMBED_ENDPOINT}/openai/deployments/{EMBED_DEPLOYMENT}/embeddings?api-version={API_VERSION_OPENAI}"
    r = requests.post(url, headers=ho(), json={"input": [text], "dimensions": EMBED_DIM})
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def extract_items():
    """Extract items from Excel sheets. Item number is in column 1 (not 0)."""
    wb = openpyxl.load_workbook(PRICE_FILE, data_only=True)
    items = []
    seen_ids = set()
    for sheet_name, category in CAT_MAP.items():
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        for row in ws.iter_rows(min_row=3, values_only=True):
            # Skip if no item number (col 1) or no name (col 2)
            if row[1] is None or not row[2]:
                continue
            item_no = row[1]
            name = str(row[2]).strip()
            if len(name) < 5:
                continue
            # Build unique id: category + sheet ordinal (sheet may have dup sequential nums)
            item_id = f"{category}-{item_no}"
            # De-dup: if collision (same item_no in same category across 2 PrintRate sheets), suffix
            if item_id in seen_ids:
                item_id = f"{item_id}-{sheet_name.split('-')[-1]}"
            seen_ids.add(item_id)
            prices = [
                float(row[i])
                for i in range(10, min(24, len(row)))
                if isinstance(row[i], (int, float)) and row[i] > 0
            ]
            if not prices:
                continue
            winner = min(prices)
            items.append({
                "item_id": item_id,
                "category": category,
                "name": name,
                "winner_price": winner,
                "price_count": len(prices),
                "price_min": min(prices),
                "price_max": max(prices),
            })
    wb.close()
    return items


def delete_index():
    r = requests.delete(f"{SEARCH_ENDPOINT}/indexes('{INDEX_NAME}')?api-version={API_VERSION}", headers=h())
    print(f"  delete old index: {r.status_code}")


def create_index():
    schema = {
        "name": INDEX_NAME,
        "fields": [
            {"name": "item_id", "type": "Edm.String", "key": True, "searchable": False, "filterable": True},
            {"name": "category", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True},
            {"name": "name", "type": "Edm.String", "searchable": True, "filterable": False, "analyzer": "th.microsoft"},
            {"name": "winner_price", "type": "Edm.Double", "filterable": True, "sortable": True},
            {"name": "price_count", "type": "Edm.Int32"},
            {"name": "price_min", "type": "Edm.Double"},
            {"name": "price_max", "type": "Edm.Double"},
            {"name": "name_vector", "type": "Collection(Edm.Single)", "searchable": True,
             "dimensions": EMBED_DIM, "vectorSearchProfile": "hnsw-profile"},
        ],
        "vectorSearch": {
            "profiles": [{"name": "hnsw-profile", "algorithm": "hnsw-config"}],
            "algorithms": [{"name": "hnsw-config", "kind": "hnsw"}],
        }
    }
    r = requests.put(f"{SEARCH_ENDPOINT}/indexes('{INDEX_NAME}')?api-version={API_VERSION}", headers=h(), json=schema)
    print(f"  create index: {r.status_code}")
    if r.status_code >= 400:
        print(f"  ⚠️ response: {r.text[:500]}")


def upload_items(items):
    """Upload with embeddings.  Batched with error detail."""
    total = 0
    batch = []
    for i, it in enumerate(items):
        print(f"  [{i+1}/{len(items)}] embed: {it['name'][:40]}")
        try:
            vec = embed(it["name"])
        except Exception as e:
            print(f"    ⚠️ embed failed: {e}")
            continue
        batch.append({
            "@search.action": "mergeOrUpload",
            "item_id": it["item_id"],
            "category": it["category"],
            "name": it["name"],
            "winner_price": it["winner_price"],
            "price_count": it["price_count"],
            "price_min": it["price_min"],
            "price_max": it["price_max"],
            "name_vector": vec,
        })
        if len(batch) == 20 or i == len(items) - 1:
            r = requests.post(
                f"{SEARCH_ENDPOINT}/indexes('{INDEX_NAME}')/docs/index?api-version={API_VERSION}",
                headers=h(), json={"value": batch}
            )
            if r.status_code >= 400:
                print(f"  ❌ upload batch failed: {r.status_code}")
                print(f"     {r.text[:600]}")
                # try one-by-one to find the bad doc
                for doc in batch:
                    r2 = requests.post(
                        f"{SEARCH_ENDPOINT}/indexes('{INDEX_NAME}')/docs/index?api-version={API_VERSION}",
                        headers=h(), json={"value": [doc]}
                    )
                    if r2.status_code >= 400:
                        print(f"     bad doc: id={doc['item_id']} {doc['name'][:40]}")
            else:
                total += len(batch)
                print(f"  uploaded {total} docs (status {r.status_code})")
            batch = []
    return total


def search(query, kind="hybrid", top=5):
    """Run a search against AI Search."""
    vec = embed(query)
    body = {
        "search": query,
        "top": top,
        "select": "item_id,category,name,winner_price,price_count",
        "vectorQueries": [{
            "kind": "vector",
            "vector": vec,
            "fields": "name_vector",
            "k": top,
        }],
    }
    if kind == "vector":
        body.pop("search")
    if kind == "text":
        body.pop("vectorQueries")
    r = requests.post(
        f"{SEARCH_ENDPOINT}/indexes('{INDEX_NAME}')/docs/search?api-version={API_VERSION}",
        headers=h(), json=body
    )
    r.raise_for_status()
    return r.json().get("value", [])


TEST_QUERIES = [
    "ร่มโค้ก 36 นิ้ว โครงไฟเบอร์ สีตาย 2 อัน",
    "ร่มโค้ก 10 อัน",                          # ไม่ระบุ spec -> ควรเจอ 8 variants
    "ร่มโค้ก 36",                              # numeric abbreviation
    "กันเปื้อณ แบบเอี้ยม",                     # typo กันเปื้อนโคคา -> กันเปื้อณ
    "ผ้ากันเปื้อน",                            # nom-accusative case
    "ป้ายราคา RGB พลาสวูด",                    # from email PDF
    "สติกเกอร์ Minute Maid ขนาด 37x28",        # real email PDF wording
    "ร่มโค้กเหล็กสีตาย",                       # word run-together (no spaces)
]


def run_tests():
    print("\n" + "=" * 80)
    print("TESTING SEARCH QUALITY")
    print("=" * 80)
    for q in TEST_QUERIES:
        print(f"\n🔍 Query: {q}")
        results = search(q, kind="hybrid", top=5)
        for j, r in enumerate(results):
            score = r.get("@search.score", 0)
            rscore = r.get("@search.rerankerScore", 0)
            print(f"  {j+1}. [{score:.3f}] {r['item_id']}  {r['name'][:60]}  ({r['winner_price']}฿)")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="Delete and recreate index")
    ap.add_argument("--upload-only", action="store_true", help="Skip index creation, only upload items")
    args = ap.parse_args()

    print("=== Azure AI Search Test for Procurement Items ===\n")
    if not SEARCH_KEY:
        print("❌ AZURE_SEARCH_ADMIN_KEY not set"); sys.exit(1)

    print("1. Extracting items from Excel...")
    items = extract_items()
    print(f"   {len(items)} items\n")

    if args.rebuild:
        print("2. Recreating index...")
        delete_index()
        create_index()
        time.sleep(3)
    elif not args.upload_only:
        print("2. Creating index if missing...")
        # only create if not exists
        r = requests.get(f"{SEARCH_ENDPOINT}/indexes('{INDEX_NAME}')?api-version={API_VERSION}", headers=h())
        if r.status_code == 404:
            create_index()
            time.sleep(3)
        else:
            print(f"   index exists (status {r.status_code}), reusing")

    print("\n3. Uploading items with embeddings...")
    upload_items(items)
    print(f"   Done.\n")
    time.sleep(5)

    print("4. Running test queries...\n")
    run_tests()
    print("\n=== Done. Manual cleanup: delete_index() when finished ===")


if __name__ == "__main__":
    main()