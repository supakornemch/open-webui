#!/usr/bin/env python3
"""
ingest-eexpense-faq.py — Embed + Upload E-Expense FAQ to Azure AI Search
=========================================================================

Pipeline:
  1. Read data/eexpense-faq.jsonl
  2. Generate embeddings via Azure OpenAI (text-embedding-3-large, 3072d)
  3. Upload documents to eexpense-faq-idx

Usage:
  export AZURE_SEARCH_KEY="..."
  export AZURE_OPENAI_API_KEY="..."
  python3 scripts/ingest-eexpense-faq.py [--input data/eexpense-faq.jsonl]
"""

import os, sys, json, time, argparse
from pathlib import Path
from typing import List

import requests
from openai import AzureOpenAI

# ── Config ──────────────────────────────────────────────
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT",
                             "https://srch-entchat-poc-sand.search.windows.net")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
INDEX_NAME = os.getenv("EEXPENSE_INDEX", "eexpense-faq-idx")
API_VERSION = "2024-07-01"

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT",
                             "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBEDDING_DEPLOYMENT = "deploy-embedding-3-large"
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072

DEFAULT_INPUT = str(Path(__file__).parent.parent / "data" / "eexpense-faq.jsonl")
BATCH_SIZE = 20  # OpenAI embedding batch size
UPLOAD_BATCH = 100  # Search upload batch size


def load_documents(filepath: str) -> list[dict]:
    """Load FAQ documents from JSONL."""
    docs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def build_embedding_text(doc: dict) -> str:
    """Build a rich text string for embedding generation."""
    parts = [doc.get("question", "")]
    parts.append(doc.get("answer", ""))
    # Add keywords for better semantic matching
    kws = doc.get("keywords", [])
    if kws:
        parts.append(" | ".join(kws))
    # Add category context
    cat = doc.get("category", "")
    if cat:
        parts.append(f"[{cat}]")
    return " ".join(parts)


def generate_embeddings(client: AzureOpenAI, texts: list[str]) -> list[list[float]]:
    """Generate embeddings in batches."""
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        try:
            resp = client.embeddings.create(
                model=EMBEDDING_DEPLOYMENT,
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            all_embeddings.extend([e.embedding for e in resp.data])
            print(f"   📐 Embedded {i + len(batch)}/{len(texts)}")
        except Exception as e:
            print(f"   ❌ Embedding failed at batch {i}: {e}")
            # Fill with zeros for failed batch
            all_embeddings.extend([[0.0] * EMBEDDING_DIMENSIONS for _ in batch])
    return all_embeddings


def upload_documents(docs: list[dict], index_name: str, reset: bool = False):
    """Upload documents to Azure AI Search index."""
    headers = {"Content-Type": "application/json", "api-key": SEARCH_KEY}
    upload_url = f"{SEARCH_ENDPOINT}/indexes/{index_name}/docs/index?api-version={API_VERSION}"

    # Optional: count existing docs for reporting
    if reset:
        count_url = f"{SEARCH_ENDPOINT}/indexes/{index_name}/docs?api-version={API_VERSION}&search=*&$select=id&$top=1000"
        resp = requests.get(count_url, headers=headers)
        if resp.status_code == 200:
            existing = resp.json().get("value", [])
            if existing:
                deletes = [{"@search.action": "delete", "id": d["id"]} for d in existing]
                requests.post(upload_url, json={"value": deletes}, headers=headers)
                print(f"   🗑️  Deleted {len(existing)} existing documents")

    # Upload in batches
    total = 0
    for i in range(0, len(docs), UPLOAD_BATCH):
        batch = docs[i:i + UPLOAD_BATCH]
        payload = {"value": batch}
        try:
            resp = requests.post(upload_url, json=payload, headers=headers)
            if resp.status_code == 200:
                results = resp.json().get("value", [])
                ok = sum(1 for r in results if r.get("status") in (True, "success", 200, 201))
                print(f"   📤 Batch {i // UPLOAD_BATCH + 1}: {ok}/{len(batch)} indexed")
                total += ok
            else:
                print(f"   ❌ Batch failed: {resp.status_code} {resp.text[:300]}")
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
    return total


def main():
    parser = argparse.ArgumentParser(description="Embed & upload E-Expense FAQ to AI Search")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to FAQ JSONL")
    parser.add_argument("--index", default=INDEX_NAME, help="Target index name")
    parser.add_argument("--skip-embed", action="store_true",
                        help="Skip embedding (docs already have contentVector)")
    parser.add_argument("--reset", action="store_true",
                        help="Delete existing docs before upload")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate only, no upload")
    args = parser.parse_args()

    # Validate env
    if not SEARCH_KEY:
        print("❌ Set AZURE_SEARCH_KEY or AZURE_SEARCH_ADMIN_KEY")
        sys.exit(1)

    index_name = args.index

    # Load
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Input not found: {input_path}")
        sys.exit(1)

    docs = load_documents(str(input_path))
    print(f"📖 Loaded {len(docs)} documents from {input_path}")

    # Embed
    if not args.skip_embed:
        if not OPENAI_KEY:
            print("❌ Set AZURE_OPENAI_API_KEY for embedding generation")
            sys.exit(1)

        print(f"\n🧠 Generating embeddings ({EMBEDDING_MODEL}, {EMBEDDING_DIMENSIONS}d)...")
        print(f"   Azure OpenAI: {OPENAI_ENDPOINT}")
        print(f"   Deployment: {EMBEDDING_DEPLOYMENT}")

        client = AzureOpenAI(
            api_key=OPENAI_KEY,
            api_version="2024-12-01-preview",
            azure_endpoint=OPENAI_ENDPOINT,
        )

        texts = [build_embedding_text(d) for d in docs]
        print(f"   Building embeddings for {len(texts)} texts...")
        embeddings = generate_embeddings(client, texts)

        # Attach embeddings to docs
        for doc, emb in zip(docs, embeddings):
            doc["contentVector"] = emb
            doc["@search.action"] = "mergeOrUpload"
        print(f"   ✅ Embeddings generated")
    else:
        for doc in docs:
            doc["@search.action"] = "mergeOrUpload"

    if args.dry_run:
        print(f"\n🔍 Dry run — would upload {len(docs)} docs to {INDEX_NAME}")
        print(f"   Sample ID: {docs[0].get('id', 'N/A')}")
        return

    # Upload
    print(f"\n📤 Uploading {len(docs)} documents to index: {INDEX_NAME}")
    print(f"   Endpoint: {SEARCH_ENDPOINT}")
    count = upload_documents(docs, index_name, reset=args.reset)
    print(f"\n✅ Complete! {count} documents indexed")

    print(f"\n💡 Try querying:")
    print(f"   curl -X POST '{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/search?api-version={API_VERSION}' \\")
    print(f"     -H 'api-key: ...' -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"search\":\"ขอล่วงหน้ากี่วัน\",\"top\":3}}'")


if __name__ == "__main__":
    main()
