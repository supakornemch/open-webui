#!/usr/bin/env python3
"""Embed and sync awarded Procurement v2 records to Azure AI Search.

The index is dedicated to Procurement data. A sync prunes only records whose
``corpus`` is ``procurement-prices``, so it cannot remove another corpus.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "procurement_prices_for_search.jsonl"
INDEX_NAME = "procurement-prices-th-idx"
SEARCH_API_VERSION = "2024-07-01"
OPENAI_API_VERSION = "2024-10-21"
EMBEDDING_DEPLOYMENT = "deploy-embedding-3-large"
DIMENSIONS = 3072

INDEX_SCHEMA = {
    "name": INDEX_NAME,
    "fields": [
        {"name": "id", "type": "Edm.String", "key": True, "filterable": True, "retrievable": True},
        {"name": "product_code", "type": "Edm.String", "filterable": True, "retrievable": True},
        {"name": "product_name", "type": "Edm.String", "searchable": True, "retrievable": True, "analyzer": "th.microsoft"},
        {"name": "category", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True, "retrievable": True},
        {"name": "pricing_model", "type": "Edm.String", "filterable": True, "retrievable": True},
        {"name": "variant_code", "type": "Edm.String", "filterable": True, "retrievable": True},
        {"name": "variant_description", "type": "Edm.String", "searchable": True, "retrievable": True, "analyzer": "th.microsoft"},
        {"name": "vendor_code", "type": "Edm.String", "filterable": True, "retrievable": True},
        {"name": "vendor_name", "type": "Edm.String", "retrievable": True},
        {"name": "year", "type": "Edm.Int32", "filterable": True, "sortable": True, "retrievable": True},
        {"name": "price", "type": "Edm.Double", "filterable": True, "sortable": True, "retrievable": True},
        {"name": "unit", "type": "Edm.String", "filterable": True, "retrievable": True},
        {"name": "qty_range", "type": "Edm.String", "retrievable": True},
        {"name": "is_winner", "type": "Edm.Boolean", "filterable": True, "retrievable": True},
        {"name": "meets_spec", "type": "Edm.Boolean", "filterable": True, "retrievable": True},
        {"name": "notes", "type": "Edm.String", "searchable": True, "retrievable": True},
        {"name": "corpus", "type": "Edm.String", "filterable": True, "retrievable": True},
        {"name": "source", "type": "Edm.String", "filterable": True, "retrievable": True},
        {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True, "analyzer": "th.microsoft"},
        {"name": "content_vector", "type": "Collection(Edm.Single)", "searchable": True, "retrievable": False, "dimensions": DIMENSIONS, "vectorSearchProfile": "vector-profile"},
    ],
    "vectorSearch": {
        "algorithms": [{"name": "hnsw-config", "kind": "hnsw", "hnswParameters": {"metric": "cosine"}}],
        "profiles": [{"name": "vector-profile", "algorithm": "hnsw-config"}],
    },
}


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name}")
    return value


def load_records(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        records = [json.loads(line) for line in source if line.strip()]
    if not records:
        raise RuntimeError(f"No records in {path}")
    if any(not record.get("is_winner") or not record.get("meets_spec") for record in records):
        raise RuntimeError("Input contains a record that is not both winner and spec-compliant")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync awarded Procurement prices to Azure AI Search")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = load_records(args.input)
    print(f"Loaded {len(records)} awarded record(s) from {args.input.name}")
    if args.dry_run:
        print("Dry run: no Azure resources changed")
        return

    search_endpoint = required("AZURE_SEARCH_ENDPOINT").rstrip("/")
    search_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY") or required("AZURE_SEARCH_KEY")
    openai_endpoint = required("OPENAI_API_BASE_URL").rstrip("/")
    openai_key = required("OPENAI_API_KEY")
    openai_version = os.environ.get("OPENAI_API_VERSION", OPENAI_API_VERSION)
    search_headers = {"api-key": search_key, "Content-Type": "application/json"}
    embed_headers = {"api-key": openai_key, "Content-Type": "application/json"}
    index_url = f"{search_endpoint}/indexes/{INDEX_NAME}?api-version={SEARCH_API_VERSION}"

    try:
        response = requests.get(index_url, headers=search_headers, timeout=30)
        if response.status_code == 404:
            response = requests.post(
                f"{search_endpoint}/indexes?api-version={SEARCH_API_VERSION}",
                headers=search_headers,
                json=INDEX_SCHEMA,
                timeout=60,
            )
            response.raise_for_status()
            print(f"Created index {INDEX_NAME}")
        else:
            response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(
            "Cannot reach Azure AI Search. Connect from the VNet/private DNS path, then retry. "
            f"Details: {error}"
        ) from error

    embedding_url = (
        f"{openai_endpoint}/openai/deployments/{EMBEDDING_DEPLOYMENT}/embeddings?api-version={openai_version}"
    )
    upload_url = f"{search_endpoint}/indexes/{INDEX_NAME}/docs/index?api-version={SEARCH_API_VERSION}"
    query_url = f"{search_endpoint}/indexes/{INDEX_NAME}/docs/search?api-version={SEARCH_API_VERSION}"
    response = requests.post(
        query_url,
        headers=search_headers,
        json={"search": "*", "filter": "corpus eq 'procurement-prices'", "select": "id", "top": 1000},
        timeout=30,
    )
    response.raise_for_status()
    existing_ids = {document["id"] for document in response.json().get("value", [])}
    expected_ids = {record["id"] for record in records}
    uploaded = 0
    for start in range(0, len(records), 25):
        batch = records[start : start + 25]
        for attempt in range(3):
            response = requests.post(
                embedding_url,
                headers=embed_headers,
                json={"input": [record["content"] for record in batch], "dimensions": DIMENSIONS},
                timeout=90,
            )
            if response.status_code == 200:
                break
            if attempt == 2:
                response.raise_for_status()
            time.sleep(2 ** attempt)
        vectors = [item["embedding"] for item in response.json()["data"]]
        documents = []
        for record, vector in zip(batch, vectors):
            documents.append({"@search.action": "mergeOrUpload", **record, "content_vector": vector})
        response = requests.post(upload_url, headers=search_headers, json={"value": documents}, timeout=90)
        response.raise_for_status()
        failures = [item for item in response.json().get("value", []) if not item.get("status")]
        if failures:
            raise RuntimeError(f"Index rejected record: {failures[0].get('errorMessage', 'unknown error')}")
        uploaded += len(documents)
        print(f"Indexed {uploaded}/{len(records)}")

    stale_ids = sorted(existing_ids - expected_ids)
    if stale_ids:
        response = requests.post(
            upload_url,
            headers=search_headers,
            json={"value": [{"@search.action": "delete", "id": record_id} for record_id in stale_ids]},
            timeout=60,
        )
        response.raise_for_status()

    response = requests.post(
        query_url,
        headers=search_headers,
        json={"search": "ร่มโค้ก", "filter": "is_winner eq true and meets_spec eq true", "select": "product_name,variant_description,price,vendor_name", "top": 3},
        timeout=30,
    )
    response.raise_for_status()
    samples = response.json().get("value", [])
    print(
        f"Complete: {uploaded} records upserted, {len(stale_ids)} stale Procurement records removed; "
        f"verification returned {len(samples)} result(s)"
    )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, requests.RequestException, json.JSONDecodeError) as error:
        raise SystemExit(f"ERROR: {error}") from error