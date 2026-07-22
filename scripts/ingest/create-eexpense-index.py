#!/usr/bin/env python3
"""
create-eexpense-index.py — Create/Recreate Azure AI Search Index for E-Expense FAQ
====================================================================================

Schema designed for hybrid search (BM25 + Vector + Semantic):
  - thai.microsoft analyzer for Thai text
  - text-embedding-3-large (3072d) for vector search
  - HNSW + cosine similarity
  - Semantic ranker configuration

Usage:
  export AZURE_SEARCH_KEY="..."
  python3 scripts/create-eexpense-index.py [--endpoint URL] [--index-name NAME]

Defaults use the project's POC sandbox endpoint.
"""

import os, sys, json, argparse
import requests

# ── Defaults (from project sandbox) ───────────────────
DEFAULT_ENDPOINT = "https://srch-entchat-poc-sand.search.windows.net"
DEFAULT_INDEX = "eexpense-faq-idx"
API_VERSION = "2024-07-01"

# ── Index Schema ───────────────────────────────────────
INDEX_SCHEMA = {
    "name": DEFAULT_INDEX,
    "fields": [
        {
            "name": "id",
            "type": "Edm.String",
            "key": True,
            "searchable": False,
            "filterable": True,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
        },
        {
            "name": "question",
            "type": "Edm.String",
            "searchable": True,
            "filterable": False,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
            "analyzer": "th.lucene",
        },
        {
            "name": "answer",
            "type": "Edm.String",
            "searchable": True,
            "filterable": False,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
            "analyzer": "th.lucene",
        },
        {
            "name": "shortAnswer",
            "type": "Edm.String",
            "searchable": True,
            "filterable": False,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
            "analyzer": "th.lucene",
        },
        {
            "name": "category",
            "type": "Edm.String",
            "searchable": False,
            "filterable": True,
            "retrievable": True,
            "sortable": False,
            "facetable": True,
        },
        {
            "name": "keywords",
            "type": "Collection(Edm.String)",
            "searchable": True,
            "filterable": False,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
            "analyzer": "th.lucene",
        },
        {
            "name": "conditions",
            "type": "Collection(Edm.String)",
            "searchable": True,
            "filterable": True,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
            "analyzer": "th.lucene",
        },
        {
            "name": "contextQuestions",
            "type": "Collection(Edm.String)",
            "searchable": True,
            "filterable": False,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
            "analyzer": "th.lucene",
        },
        {
            "name": "sourceId",
            "type": "Edm.String",
            "searchable": False,
            "filterable": True,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
        },
        {
            "name": "choiceType",
            "type": "Edm.String",
            "searchable": False,
            "filterable": True,
            "retrievable": True,
            "sortable": False,
            "facetable": True,
        },
        {
            "name": "contentVector",
            "type": "Collection(Edm.Single)",
            "searchable": True,
            "filterable": False,
            "retrievable": True,
            "sortable": False,
            "facetable": False,
            "dimensions": 3072,
            "vectorSearchProfile": "eexpense-vector-profile",
        },
    ],
    "semantic": {
        "configurations": [
            {
                "name": "eexpense-semantic-config",
                "prioritizedFields": {
                    "titleField": {"fieldName": "question"},
                    "prioritizedContentFields": [
                        {"fieldName": "answer"},
                        {"fieldName": "keywords"},
                    ],
                    "prioritizedKeywordsFields": [
                        {"fieldName": "keywords"},
                        {"fieldName": "category"},
                    ],
                },
            }
        ]
    },
    "vectorSearch": {
        "algorithms": [
            {
                "name": "eexpense-hnsw",
                "kind": "hnsw",
                "hnswParameters": {
                    "metric": "cosine",
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                },
            }
        ],
        "profiles": [
            {
                "name": "eexpense-vector-profile",
                "algorithm": "eexpense-hnsw",
            }
        ],
    },
}


def get_index(endpoint: str, key: str, index_name: str) -> dict | None:
    url = f"{endpoint}/indexes/{index_name}?api-version={API_VERSION}"
    resp = requests.get(url, headers={"api-key": key, "Content-Type": "application/json"})
    if resp.status_code == 200:
        return resp.json()
    return None


def delete_index(endpoint: str, key: str, index_name: str) -> bool:
    url = f"{endpoint}/indexes/{index_name}?api-version={API_VERSION}"
    resp = requests.delete(url, headers={"api-key": key})
    return resp.status_code in (200, 204)


def create_index(endpoint: str, key: str, schema: dict) -> dict:
    index_name = schema["name"]
    url = f"{endpoint}/indexes/{index_name}?api-version={API_VERSION}"
    resp = requests.put(url, json=schema, headers={
        "api-key": key, "Content-Type": "application/json"
    })
    if resp.status_code in (200, 201):
        return resp.json()
    else:
        print(f"❌ Failed to create index: {resp.status_code}")
        print(f"   {resp.text[:500]}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create E-Expense FAQ Search Index")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--index-name", default=DEFAULT_INDEX)
    parser.add_argument("--drop", action="store_true",
                        help="Delete existing index first")
    parser.add_argument("--force", action="store_true",
                        help="Skip confirmation prompt")
    args = parser.parse_args()

    search_key = os.environ.get("AZURE_SEARCH_KEY") or os.environ.get("AZURE_SEARCH_ADMIN_KEY")
    if not search_key:
        print("❌ Set AZURE_SEARCH_KEY or AZURE_SEARCH_ADMIN_KEY environment variable")
        sys.exit(1)

    # Update schema with custom index name
    schema = json.loads(json.dumps(INDEX_SCHEMA))  # deep copy
    schema["name"] = args.index_name

    # Check existing
    existing = get_index(args.endpoint, search_key, args.index_name)
    if existing:
        print(f"⚠️  Index '{args.index_name}' already exists")
        print(f"   Fields: {[f['name'] for f in existing.get('fields', [])]}")
        print(f"   Vector profiles: {[p['name'] for p in existing.get('vectorSearch', {}).get('profiles', [])]}")
        if args.drop:
            print(f"🗑️  Dropping existing index...")
            delete_index(args.endpoint, search_key, args.index_name)
            print("   ✅ Deleted")
        elif not args.force:
            resp = input("   Drop and recreate? [y/N] ").strip().lower()
            if resp != "y":
                print("   ⏭️  Skipping")
                return
            delete_index(args.endpoint, search_key, args.index_name)
            print("   ✅ Deleted")
        else:
            delete_index(args.endpoint, search_key, args.index_name)
            print("   ✅ Deleted (--force)")

    # Create
    print(f"\n🔨 Creating index: {args.index_name}")
    print(f"   Endpoint: {args.endpoint}")
    print(f"   Fields: {len(schema['fields'])}")
    print(f"   Vector: 3072d, HNSW, cosine")
    print(f"   Analyzer: thai.microsoft")
    print(f"   Semantic config: yes")

    result = create_index(args.endpoint, search_key, schema)
    print(f"\n✅ Index created: {result.get('name')}")
    print(f"   Status: {result.get('status', 'N/A')}")


if __name__ == "__main__":
    main()
