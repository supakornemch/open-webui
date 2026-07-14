#!/usr/bin/env python3
"""
upload-to-search.py — Read JSONL → Upload to Azure AI Search
==============================================================
Second step: reads preprocessed JSONL files and uploads to Azure AI Search.
Supports incremental upload (delta) and orphan document deletion.

Features:
  - Reads all JSONL files from data/ingestion/
  - Compares with existing index to upload only new/changed docs
  - Deletes docs that exist in index but not in JSONL
  - Creates/updates index schema if needed
  - Supports --force for full re-upload

Usage:
  export AZURE_SEARCH_KEY="..."

  # Create index + upload
  python3 scripts/upload-to-search.py --create-index

  # Upload all corpuses
  python3 scripts/upload-to-search.py

  # Upload specific corpus + force
  python3 scripts/upload-to-search.py --corpus corporate --force

  # Verify
  python3 scripts/upload-to-search.py --verify
"""

import os, sys, json, time, argparse, hashlib
from pathlib import Path
from typing import List, Dict, Set
import requests


# ════════════════════════════════════
# CONFIG
# ════════════════════════════════════

class Config:
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT",
                                "https://srch-entchat-poc-sand.search.windows.net")
    search_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
    search_api_version = "2024-07-01"
    index_name = "enterprise-docs-idx"
    jsonl_dir = Path("data/ingestion")
    batch_size = 100
    max_retries = 3

    corpus_paths = {
        "corporate":   "corporate",
        "hr-policies": "hr-policies",
        "openwebui-docs": "openwebui-docs",
    }


INDEX_SCHEMA = {
    "name": "enterprise-docs-idx",
    "fields": [
        {"name": "id",               "type": "Edm.String",  "key": True,
         "searchable": False, "filterable": False, "retrievable": True, "stored": True},
        {"name": "doc_id",           "type": "Edm.String",
         "searchable": False, "filterable": True,  "retrievable": True, "stored": True},
        {"name": "chunk_seq",        "type": "Edm.Int32",
         "filterable": True,  "sortable": True,  "retrievable": True, "stored": True},
        {"name": "file_name",        "type": "Edm.String",
         "searchable": True,  "filterable": True,  "retrievable": True, "stored": True},
        {"name": "file_path",        "type": "Edm.String",
         "searchable": False, "filterable": True,  "retrievable": True, "stored": True},
        {"name": "corpus",           "type": "Edm.String",
         "searchable": False, "filterable": True,  "retrievable": True, "stored": True,
         "facetable": True},
        {"name": "category",         "type": "Edm.String",
         "searchable": True,  "filterable": True,  "retrievable": True, "stored": True,
         "facetable": True},
        {"name": "content",          "type": "Edm.String",
         "searchable": True,  "retrievable": True, "stored": True},
        {"name": "summary",          "type": "Edm.String",
         "searchable": True,  "retrievable": True, "stored": True},
        {"name": "meta",             "type": "Edm.String",
         "retrievable": True, "stored": True},
        {"name": "related_doc_ids",  "type": "Collection(Edm.String)",
         "filterable": True,  "retrievable": True, "stored": True},
        {"name": "content_vector",   "type": "Collection(Edm.Single)",
         "searchable": True,  "retrievable": True, "stored": True,
         "dimensions": 3072, "vectorSearchProfile": "vector-profile"},
    ],
    "vectorSearch": {
        "algorithms": [{
            "name": "hnsw-config", "kind": "hnsw",
            "hnswParameters": {"metric": "cosine", "m": 4, "efConstruction": 400, "efSearch": 500}
        }],
        "profiles": [{"name": "vector-profile", "algorithm": "hnsw-config"}]
    },
    "semantic": {
        "configurations": [{
            "name": "semantic-config",
            "prioritizedFields": {
                "titleField": {"fieldName": "file_name"},
                "prioritizedContentFields": [{"fieldName": "content"}],
                "prioritizedKeywordsFields": [{"fieldName": "summary"}]
            }
        }]
    },
    "corsOptions": {"allowedOrigins": ["*"], "maxAgeInSeconds": 300},
    "similarity": {"@odata.type": "#Microsoft.Azure.Search.BM25Similarity"}
}


# ════════════════════════════════════
# SEARCH MANAGER
# ════════════════════════════════════

class SearchManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def _hdr(self):
        return {"Content-Type": "application/json", "api-key": self.cfg.search_key}

    def create_index(self, delete_existing: bool = False) -> bool:
        url = f"{self.cfg.search_endpoint}/indexes"
        h = self._hdr()
        if delete_existing:
            durl = f"{url}/{self.cfg.index_name}?api-version={self.cfg.search_api_version}"
            r = requests.delete(durl, headers=h)
            print(f"  {'✅ Deleted' if r.status_code in (200,204) else 'ℹ️ Not found' if r.status_code==404 else f'⚠️ {r.status_code}'}")
            time.sleep(2)

        r = requests.get(f"{url}/{self.cfg.index_name}?api-version={self.cfg.search_api_version}", headers=h)
        if r.status_code == 200:
            u = f"{url}/{self.cfg.index_name}?api-version={self.cfg.search_api_version}&allowIndexDowntime=true"
            r2 = requests.put(u, headers=h, json=INDEX_SCHEMA)
        else:
            r2 = requests.post(f"{url}?api-version={self.cfg.search_api_version}", headers=h, json=INDEX_SCHEMA)

        ok = r2.status_code in (200, 201, 204)
        print(f"  {'✅' if ok else '❌'} Index '{self.cfg.index_name}' "
              f"{'ready' if ok else f'failed: {r2.text[:300]}'}")
        return ok

    def upload_batch(self, documents: List[dict]) -> int:
        url = (f"{self.cfg.search_endpoint}/indexes/{self.cfg.index_name}"
               f"/docs/index?api-version={self.cfg.search_api_version}")
        body = {"value": documents}
        for attempt in range(self.cfg.max_retries):
            try:
                r = requests.post(url, headers=self._hdr(), json=body, timeout=60)
                if r.status_code in (200, 201):
                    results = r.json().get('value', [])
                    ok = sum(1 for d in results if d.get('status') == True)
                    errs = sum(1 for d in results if d.get('status') != True)
                    if errs > 0:
                        first = next((d for d in results if d.get('status') != True), None)
                        if first:
                            print(f"      ⚠️ {errs} err: {first.get('errorMessage','?')[:150]}")
                    return ok
                else:
                    err = r.json().get('error', {}).get('message', r.text)[:300]
                    if attempt < self.cfg.max_retries - 1: time.sleep(2 ** attempt)
                    else: print(f"      ❌ {err}")
            except Exception as e:
                if attempt < self.cfg.max_retries - 1: time.sleep(2 ** attempt)
                else: print(f"      ❌ {e}")
        return 0

    def delete_by_ids(self, ids: List[str]) -> int:
        """Delete documents by ID."""
        url = (f"{self.cfg.search_endpoint}/indexes/{self.cfg.index_name}"
               f"/docs/index?api-version={self.cfg.search_api_version}")
        # Batch deletions
        deleted = 0
        for i in range(0, len(ids), 500):
            batch = ids[i:i+500]
            docs = [{"@search.action": "delete", "id": id_val} for id_val in batch]
            try:
                r = requests.post(url, headers=self._hdr(), json={"value": docs}, timeout=30)
                if r.status_code in (200, 201):
                    results = r.json().get('value', [])
                    deleted += sum(1 for d in results if d.get('status') == True)
            except Exception as e:
                print(f"      ⚠️ Delete batch err: {e}")
        return deleted

    def get_existing_index_state(self, corpus: str) -> Dict[str, dict]:
        """Get doc_id → {sample_id, file_path} from index for a corpus."""
        existing = {}
        url = (f"{self.cfg.search_endpoint}/indexes/{self.cfg.index_name}"
               f"/docs/search?api-version={self.cfg.search_api_version}")
        body = {
            "search": "*",
            "filter": f"corpus eq '{corpus}'",
            "select": "id,doc_id,file_path",
            "top": 1000
        }
        try:
            r = requests.post(url, headers=self._hdr(), json=body, timeout=30)
            if r.status_code == 200:
                for doc in r.json().get('value', []):
                    did = doc.get('doc_id')
                    if did not in existing:
                        existing[did] = {'ids': [], 'file_path': doc.get('file_path', '')}
                    existing[did]['ids'].append(doc['id'])
        except Exception as e:
            print(f"    ⚠️ Query existing: {e}")
        return existing

    def get_count(self) -> int:
        url = (f"{self.cfg.search_endpoint}/indexes/{self.cfg.index_name}"
               f"/docs/$count?api-version={self.cfg.search_api_version}")
        try:
            r = requests.get(url, headers=self._hdr(), timeout=10)
            return int(r.text) if r.status_code == 200 else -1
        except Exception:
            return -1


# ════════════════════════════════════
# UPLOADER
# ════════════════════════════════════

class Uploader:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.search = SearchManager(cfg)
        self.stats = {"uploaded": 0, "skipped": 0, "deleted": 0, "errors": 0}

    def load_jsonl_docs(self, corpus: str) -> Dict[str, List[dict]]:
        """Load all JSONL files for a corpus. Returns {doc_id: [chunks]}."""
        corpus_dir = self.cfg.jsonl_dir / self.cfg.corpus_paths.get(corpus, corpus)
        if not corpus_dir.exists():
            print(f"  ⚠️ No preprocessed data at {corpus_dir}")
            return {}

        docs_by_id: Dict[str, List[dict]] = {}
        for jsonl_file in sorted(corpus_dir.glob("*.jsonl")):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        doc = json.loads(line)
                        did = doc.get('doc_id')
                        if did:
                            if did not in docs_by_id: docs_by_id[did] = []
                            docs_by_id[did].append(doc)
            except Exception as e:
                print(f"    ⚠️ Read error {jsonl_file.name}: {e}")
        return docs_by_id

    def upload_corpus(self, corpus: str, force: bool = False):
        print(f"\n{'═'*60}\n📤 Uploading: {corpus}\n{'═'*60}")

        # Load JSONL data
        jsonl_docs = self.load_jsonl_docs(corpus)
        if not jsonl_docs:
            print("  ℹ️ No preprocessed data to upload")
            return

        # Get existing index state
        existing = self.search.get_existing_index_state(corpus)
        print(f"  📊 JSONL: {len(jsonl_docs)} docs | Index: {len(existing)} docs")

        # Build related_doc_ids per category
        all_doc_ids_by_cat: Dict[str, List[str]] = {}
        for did, chunks in jsonl_docs.items():
            cat = chunks[0].get('category', 'uncategorized') if chunks else 'uncategorized'
            if cat not in all_doc_ids_by_cat: all_doc_ids_by_cat[cat] = []
            all_doc_ids_by_cat[cat].append(did)

        # Upload changed docs
        to_delete_ids: Set[str] = set()
        for did, chunks in jsonl_docs.items():
            cat = chunks[0].get('category', 'uncategorized') if chunks else 'uncategorized'
            related = [d for d in all_doc_ids_by_cat.get(cat, []) if d != did]

            # Set related_doc_ids on all chunks
            for c in chunks:
                c["@search.action"] = "upload"
                c["related_doc_ids"] = related

            # Delta check
            if not force and did in existing:
                # Simple check: same doc_id exists, skip
                if len(chunks) <= len(existing[did].get('ids', [])) + 3:
                    self.stats["skipped"] += len(chunks)
                    continue

            # Upload chunks
            for b_start in range(0, len(chunks), self.cfg.batch_size):
                batch = chunks[b_start:b_start + self.cfg.batch_size]
                ok = self.search.upload_batch(batch)
                self.stats["uploaded"] += ok

            to_delete_ids.add(did)

        # Find orphaned (in index but not in JSONL)
        if not force:
            orphan_ids = []
            for did in existing:
                if did not in jsonl_docs:
                    orphan_ids.extend(existing[did].get('ids', []))
            if orphan_ids:
                print(f"  🗑️  Deleting {len(orphan_ids)} orphan chunks...")
                d = self.search.delete_by_ids(orphan_ids)
                self.stats["deleted"] += d
                print(f"    Deleted {d}")

        print(f"  ✅ Chunks: {self.stats['uploaded']} uploaded, "
              f"{self.stats['skipped']} skipped, "
              f"{self.stats['deleted']} deleted")

    def print_summary(self):
        s = self.stats
        print(f"\n{'═'*60}\n📊 UPLOAD SUMMARY\n{'═'*60}")
        print(f"  Uploaded: {s['uploaded']} | Skipped: {s['skipped']} | "
              f"Deleted: {s['deleted']} | Errors: {s['errors']}")
        print(f"  Total in index: {self.search.get_count()}")
        print(f"{'═'*60}")


# ════════════════════════════════════
# MAIN
# ════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="Upload preprocessed JSONL to AI Search")
    p.add_argument("--corpus", choices=["all","corporate","hr-policies","openwebui-docs"], default="all")
    p.add_argument("--create-index", action="store_true")
    p.add_argument("--delete-existing", action="store_true")
    p.add_argument("--force", action="store_true", help="Force re-upload all docs")
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()

    cfg = Config()
    if not cfg.search_key:
        print("❌ Set AZURE_SEARCH_KEY"); sys.exit(1)

    print("═"*60)
    print("📤 JSONL → AI SEARCH UPLOAD")
    print("═"*60)
    print(f"   Index:    {cfg.index_name}")
    print(f"   JSONL:    {cfg.jsonl_dir}")
    print(f"   Search:   {cfg.search_endpoint}")
    if args.force: print(f"   Mode:     🔄 FORCE")
    print()

    search = SearchManager(cfg)

    if args.create_index:
        if not search.create_index(delete_existing=args.delete_existing):
            sys.exit(1)
        print()

    if args.verify:
        total = search.get_count()
        print(f"🔍 Index: {cfg.index_name} — {total if total >= 0 else 'N/A'} docs")
        for c in ["corporate","hr-policies","openwebui-docs"]:
            e = search.get_existing_index_state(c)
            print(f"   📂 {c}: {len(e)} docs")
            if e:
                for did, info in list(e.items())[:2]:
                    print(f"      • {info.get('file_path','?')} ({len(info.get('ids',[]))} chunks)")
        print()
        return

    uploader = Uploader(cfg)
    selected = ["corporate","hr-policies","openwebui-docs"] if args.corpus == "all" else [args.corpus]
    for c in selected:
        uploader.upload_corpus(c, args.force)
    uploader.print_summary()


if __name__ == "__main__":
    main()
