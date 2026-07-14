#!/usr/bin/env python3
"""
ingest-blob-to-search-v2.py — Fast ingestion with batch embedding
Chunks: 4000 chars, Batch: up to 20 texts per embedding API call
"""

import os, re, hashlib, time
from io import BytesIO

import requests
from pypdf import PdfReader
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# ============================================================
CONTAINER = "documents"
PREFIX = "haadthip"

EMBEDDING_URL = "https://aif-entchat-poc-sand.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2025-03-01-preview"
EMBEDDING_KEY = "<REPLACE_WITH_EMBEDDING_KEY>"

SEARCH_ENDPOINT = "https://srch-entchat-poc-sand.search.windows.net"
SEARCH_KEY = "<REPLACE_WITH_SEARCH_KEY>"
INDEX_NAME = "haadthip-docs"

CATEGORY_MAP = {
    "01-security": "security", "02-email": "email", "03-meeting-room": "meeting_room",
    "04-it-policy": "it_policy", "05-public-disclosure": "public_disclosure",
}

STORAGE_CONN_STR = "DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=staentchatdoc;BlobEndpoint=https://staentchatdoc.blob.core.windows.net/"
# NOTE: Add AccountKey from Azure Portal before running!

# ============================================================
def chunk_text(text, max_chars=4000, overlap=400):
    """Chunk by paragraph boundaries"""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks, current = [], ""
    for para in paragraphs:
        para = para.strip()
        if not para: continue
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current: chunks.append(current)
            if len(para) > max_chars:
                # Split long para by sentences
                for sent in re.split(r'(?<=[.!?。！？])\s+', para):
                    if len(sent) > max_chars:
                        for i in range(0, len(sent), max_chars - overlap):
                            chunks.append(sent[i:i + max_chars])
                    else:
                        chunks.append(sent)
            else:
                current = para
    if current: chunks.append(current)
    return chunks

def batch_embed(texts, retries=5):
    """Get embeddings for multiple texts in one API call"""
    # Truncate each text to ~8000 chars (embedding limit ≈ 8192 tokens)
    truncated = [t[:8000] for t in texts]
    for attempt in range(retries):
        try:
            resp = requests.post(EMBEDDING_URL,
                headers={"Content-Type": "application/json", "api-key": EMBEDDING_KEY},
                json={"input": truncated}, timeout=120)
            if resp.status_code == 200:
                data = resp.json()["data"]
                return [d["embedding"] for d in sorted(data, key=lambda x: x["index"])]
            elif resp.status_code == 429:
                wait = min(10 * (attempt + 1), 120)
                print(f"      ⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"      ⚠️  API {resp.status_code}: {resp.text[:150]}")
                time.sleep(5)
        except Exception as e:
            print(f"      ⚠️  Error: {e}")
            time.sleep(5)
    return [None] * len(texts)

# ============================================================
def main():
    print("=" * 60)
    print(" Haadthip Ingestion v2 (Batch Embed)")
    print("=" * 60)

    blob_svc = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
    container = blob_svc.get_container_client(CONTAINER)
    search = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=AzureKeyCredential(SEARCH_KEY))

    pdfs = [b for b in container.list_blobs(name_starts_with=PREFIX) if b.name.lower().endswith(".pdf")]
    print(f"\n{len(pdfs)} PDFs to process\n")

    total = 0
    for bi, blob in enumerate(pdfs):
        name = blob.name.split("/")[-1]
        cat = next((v for k, v in CATEGORY_MAP.items() if k in blob.name), "general")
        print(f"📄 [{bi+1}/{len(pdfs)}] {name[:60]} ({cat})")

        try:
            # Extract text
            stream = container.download_blob(blob).readall()
            pages = [p.extract_text().strip() for p in PdfReader(BytesIO(stream)).pages if p.extract_text() and p.extract_text().strip()]
            full_text = "\n\n".join(pages)
            print(f"   {len(pages)} pages, {len(full_text):,} chars")

            # Chunk
            chunks = [c for c in chunk_text(full_text) if len(c.strip()) >= 50]
            print(f"   {len(chunks)} chunks")

            # Batch embed (20 chunks at a time)
            parent_id = hashlib.md5(name.encode()).hexdigest()
            all_docs = []
            for i in range(0, len(chunks), 10):
                batch_texts = chunks[i:i+10]
                embeddings = batch_embed(batch_texts)
                for j, emb in enumerate(embeddings):
                    if emb:
                        ci = i + j
                        all_docs.append({
                            "chunk_id": hashlib.md5(f"{name}_{ci}".encode()).hexdigest(),
                            "parent_id": parent_id,
                            "content": batch_texts[j],
                            "content_vector": emb,
                            "title": name,
                            "category": cat,
                            "chunk_index": ci,
                        })
                if i % 20 == 0:
                    print(f"   📤 Embedding batch {i//10+1}/{ (len(chunks)+9)//10 }...")

            # Upload all docs for this PDF
            if all_docs:
                for k in range(0, len(all_docs), 50):
                    batch = all_docs[k:k+50]
                    results = search.upload_documents(batch)
                    ok = sum(1 for r in results if r.succeeded)
                    total += ok
                print(f"   ✅ {len(all_docs)} chunks indexed (total: {total})")
            else:
                print(f"   ⚠️  No chunks indexed (embedding failed)")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Rate limit: 1 req/10s for embedding
        if bi < len(pdfs) - 1:
            time.sleep(3)

    print(f"\n{'=' * 60}")
    print(f" ✅ DONE! {total} chunks in '{INDEX_NAME}'")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
