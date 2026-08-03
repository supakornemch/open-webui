#!/usr/bin/env python3
"""Sync the Procurement Y2026 price-book JSONL into Azure AI Search.

Each price tier becomes one searchable document in corpus ``procurement-y2026``.
The script never deletes another corpus and creates ``enterprise-docs-idx`` only
when it does not already exist.

Required environment variables (available in docker/.env.owui):
  AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY, OPENAI_API_BASE_URL,
  OPENAI_API_KEY, OPENAI_API_VERSION
"""

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests

from unified import INDEX_SCHEMA


CORPUS = "procurement-y2026"
INDEX_NAME = "enterprise-docs-idx"
EMBEDDING_DEPLOYMENT = "deploy-embedding-3-large"
API_VERSION = "2024-10-21"
SEARCH_API_VERSION = "2024-07-01"
DEFAULT_INPUT = (
    Path(__file__).resolve().parents[2]
    / "requirements/procurement-ai-chat/data/source/price-book-Y2026.jsonl"
)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name}")
    return value


class AzureSearch:
    def __init__(self) -> None:
        self.endpoint = require_env("AZURE_SEARCH_ENDPOINT").rstrip("/")
        self.key = os.environ.get("AZURE_SEARCH_ADMIN_KEY") or require_env("AZURE_SEARCH_KEY")
        self.headers = {"Content-Type": "application/json", "api-key": self.key}

    def _url(self, suffix: str) -> str:
        return f"{self.endpoint}{suffix}?api-version={SEARCH_API_VERSION}"

    def ensure_index(self) -> None:
        response = requests.get(self._url(f"/indexes/{INDEX_NAME}"), headers=self.headers, timeout=30)
        if response.status_code == 200:
            return
        if response.status_code != 404:
            raise RuntimeError(f"Unable to read index: {response.status_code} {response.text[:300]}")

        response = requests.post(
            self._url("/indexes"), headers=self.headers, json=INDEX_SCHEMA, timeout=60
        )
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(f"Unable to create index: {response.status_code} {response.text[:500]}")
        print(f"Created index: {INDEX_NAME}")

    def existing_ids(self) -> set[str]:
        response = requests.post(
            self._url(f"/indexes/{INDEX_NAME}/docs/search"),
            headers=self.headers,
            json={
                "search": "*",
                "filter": f"corpus eq '{CORPUS}'",
                "select": "id",
                "top": 1000,
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Unable to list Procurement records: {response.status_code} {response.text[:300]}")
        return {document["id"] for document in response.json().get("value", [])}

    def upload(self, documents: list[dict[str, Any]]) -> int:
        response = requests.post(
            self._url(f"/indexes/{INDEX_NAME}/docs/index"),
            headers=self.headers,
            json={"value": documents},
            timeout=90,
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {response.status_code} {response.text[:500]}")
        results = response.json().get("value", [])
        failed = [result for result in results if not result.get("status")]
        if failed:
            raise RuntimeError(f"Upload rejected: {failed[0].get('errorMessage', 'unknown error')}")
        return len(results)

    def delete(self, ids: list[str]) -> int:
        if not ids:
            return 0
        return self.upload([{"@search.action": "delete", "id": document_id} for document_id in ids])

    def count(self) -> int:
        response = requests.get(
            self._url(f"/indexes/{INDEX_NAME}/docs/$count"), headers=self.headers, timeout=30
        )
        if response.status_code != 200:
            raise RuntimeError(f"Unable to count index: {response.status_code} {response.text[:300]}")
        return int(response.text)

    def sample_search(self) -> list[dict[str, Any]]:
        response = requests.post(
            self._url(f"/indexes/{INDEX_NAME}/docs/search"),
            headers=self.headers,
            json={
                "search": "เสื้อโปโล",
                "filter": f"corpus eq '{CORPUS}'",
                "select": "id,doc_id,category,content",
                "top": 3,
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Unable to verify search: {response.status_code} {response.text[:300]}")
        return response.json().get("value", [])


class AzureEmbedder:
    def __init__(self) -> None:
        self.endpoint = require_env("OPENAI_API_BASE_URL").rstrip("/")
        self.key = require_env("OPENAI_API_KEY")
        self.api_version = os.environ.get("OPENAI_API_VERSION", API_VERSION)
        self.headers = {"Content-Type": "application/json", "api-key": self.key}

    def embed(self, texts: list[str]) -> list[list[float]]:
        url = (
            f"{self.endpoint}/openai/deployments/{EMBEDDING_DEPLOYMENT}/embeddings"
            f"?api-version={self.api_version}"
        )
        for attempt in range(3):
            response = requests.post(
                url,
                headers=self.headers,
                json={"input": texts, "dimensions": 3072},
                timeout=90,
            )
            if response.status_code == 200:
                return [entry["embedding"] for entry in response.json()["data"]]
            if attempt == 2:
                raise RuntimeError(f"Embedding failed: {response.status_code} {response.text[:500]}")
            time.sleep(2 ** attempt)
        raise AssertionError("unreachable")


def load_documents(path: Path) -> list[dict[str, Any]]:
    records = []
    tier_sequence: dict[str, int] = defaultdict(int)
    source_path = "requirements/procurement-ai-chat/data/source/price-book-Y2026.jsonl"

    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            item_id = str(record["id"])
            metadata = record.get("metadata", {})
            sequence = tier_sequence[item_id]
            tier_sequence[item_id] += 1
            # Azure Search document keys reject dots in item IDs such as POSM-5.1.
            document_key = hashlib.sha256(f"{item_id}:{sequence}".encode()).hexdigest()[:32]
            document_id = f"{CORPUS}-{document_key}"
            doc_id = f"{CORPUS}-{item_id}"
            text = str(record["text"])
            meta = {
                "source": "price-book-Y2026.jsonl",
                "source_path": source_path,
                "item_id": item_id,
                "tier_sequence": sequence,
                **metadata,
            }
            records.append(
                {
                    "@search.action": "upload",
                    "id": document_id,
                    "doc_id": doc_id,
                    "chunk_seq": sequence,
                    "file_name": "price-book-Y2026.jsonl",
                    "file_path": source_path,
                    "corpus": CORPUS,
                    "category": str(metadata.get("category", "Procurement")),
                    "content": text,
                    "summary": text,
                    "meta": json.dumps(meta, ensure_ascii=False),
                    "related_doc_ids": [],
                }
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Procurement price-book to Azure AI Search")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    if not args.input.is_file():
        parser.error(f"Input file not found: {args.input}")

    documents = load_documents(args.input)
    categories = sorted({document["category"] for document in documents})
    print(f"Loaded {len(documents)} price-tier records from {args.input.name}")
    print(f"Corpus: {CORPUS} | Categories: {', '.join(categories)}")
    if args.dry_run:
        print("Dry run: no Azure resources changed")
        return

    search = AzureSearch()
    search.ensure_index()
    existing_ids = search.existing_ids()
    expected_ids = {document["id"] for document in documents}
    stale_ids = sorted(existing_ids - expected_ids)

    embedder = AzureEmbedder()
    uploaded = 0
    for start in range(0, len(documents), args.batch_size):
        batch = documents[start : start + args.batch_size]
        vectors = embedder.embed([document["content"] for document in batch])
        for document, vector in zip(batch, vectors):
            document["content_vector"] = vector
        uploaded += search.upload(batch)
        print(f"Indexed {min(start + len(batch), len(documents))}/{len(documents)}")

    deleted = 0
    for start in range(0, len(stale_ids), 500):
        deleted += search.delete(stale_ids[start : start + 500])
    samples = search.sample_search()
    print(f"Complete: {uploaded} upserted, {deleted} stale Procurement records deleted")
    print(f"Index document count: {search.count()}")
    print(f"Verification search (เสื้อโปโล): {len(samples)} result(s)")
    for sample in samples:
        print(f"  - {sample['id']}: {sample['content'][:120]}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, requests.RequestException, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)