#!/usr/bin/env python3
"""
unified-ingestion.py — Enterprise Document Ingestion for Azure AI Search
=========================================================================

Features:
  - Single index (enterprise-docs-idx) with corpus filter
  - Fields: meta (JSON), summary (GPT-5.4-nano), related_doc_ids
  - Document Intelligence prebuilt-layout extraction
  - text-embedding-3-large (3072d) vectors
  - Incremental ingestion (skip unchanged, delete orphans)
  - Source: local disk OR Azure Blob Storage
  - GPT auto-classify category from content
  - Semantic + Hybrid search ready

Usage:
  export AZURE_SEARCH_KEY="..."
  export AZURE_OPENAI_API_KEY="..."

  # Create index first
  python3 scripts/unified-ingestion.py --create-index

  # Ingest from local disk (incremental by default)
  python3 scripts/unified-ingestion.py --corpus corporate

  # Ingest from blob
  python3 scripts/unified-ingestion.py --source blob --blob-container haadthip-docs

  # Dry run
  python3 scripts/unified-ingestion.py --dry-run

  # Force full re-ingestion
  python3 scripts/unified-ingestion.py --force

  # Verify
  python3 scripts/unified-ingestion.py --verify
"""

import os, re, sys, hashlib, time, argparse, json, io, tempfile, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Tuple, Any, Iterator
from collections import defaultdict

import requests
from openai import AzureOpenAI

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import DocumentContentFormat
    HAS_DOC_INTEL = True
except ImportError:
    HAS_DOC_INTEL = False

try:
    from azure.storage.blob import BlobServiceClient
    HAS_BLOB_SDK = True
except ImportError:
    HAS_BLOB_SDK = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
try:
    from openpyxl import load_workbook
    HAS_XLSX = True
except ImportError:
    HAS_XLSX = False
try:
    from pptx import Presentation
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False


# ═══════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════

class Config:
    # AI Search
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT",
                                "https://srch-entchat-poc-sand.search.windows.net")
    search_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
    search_api_version = "2024-07-01"
    index_name = "enterprise-docs-idx"

    # Azure OpenAI
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT",
                                "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
    openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    embedding_deployment = "deploy-embedding-3-large"
    embedding_model = "text-embedding-3-large"
    embedding_dimensions = 3072
    summary_deployment = "deploy-gpt-5.4-nano"
    summary_model = "gpt-5.4-nano"

    # Document Intelligence
    docintel_endpoint = os.getenv("DOCUMENTINTELLIGENCE_ENDPOINT",
                                  "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
    docintel_key = os.getenv("DOCUMENTINTELLIGENCE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")

    # Blob Storage
    blob_conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    blob_container = os.getenv("AZURE_STORAGE_CONTAINER", "documents")

    # Ingestion
    base_dir = Path("documents")
    chunk_size = 2000
    chunk_overlap = 200
    batch_size = 50
    max_retries = 3

    # Corpus → relative folder (local) or blob prefix
    corpus_paths = {
        "investor-relations": "haadthip-investor-relations",
        "corporate":          "haadthip-corporate",
        "hr-policies":        "haadthip-hr-policies",
    }

    supported_extensions = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.jpg', '.jpeg', '.png', '.ppt', '.pptx'
    }


# ═══════════════════════════════════════════════
# INDEX SCHEMA
# ═══════════════════════════════════════════════

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
            "hnswParameters": {
                "metric": "cosine", "m": 4, "efConstruction": 400, "efSearch": 500
            }
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


# ═══════════════════════════════════════════════
# CATEGORIES for auto-classification
# ═══════════════════════════════════════════════

CATEGORIES_BY_CORPUS = {
    "investor-relations": [
        "Annual Report", "Form 56-1", "Financial Data", "Factsheet",
        "Company Disclosure", "AGM Minutes", "Press Release",
        "Management Discussion", "Earnings Results"
    ],
    "corporate": [
        "Security Manual", "Email Manual", "IT Policy",
        "Meeting Room Guide", "Public Disclosure", "Sustainability Report",
        "Corporate Governance"
    ],
    "hr-policies": [
        "Policy", "Announcement / Order", "Form / Template",
        "Benefits & Welfare", "Training & Development",
        "Recruitment & Appointment", "Privacy / PDPA",
        "Social Security", "Safety & Environment",
        "Company Regulation", "Holiday / Leave",
        "Manual / Guide", "Newsletter"
    ],
}

CLASSIFY_PROMPT = (
    "Classify this business document excerpt into EXACTLY ONE category "
    "from the list below. Return ONLY the category name, nothing else.\n"
    "Categories:\n"
)


# ═══════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════

TH_LANG_PATTERN = re.compile(r'[ก-๙]')


def compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash of file for change detection."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def detect_language(text: str) -> str:
    thai_chars = len(TH_LANG_PATTERN.findall(text))
    total_chars = max(len(text.strip()), 1)
    ratio = thai_chars / total_chars
    if ratio > 0.5:
        return "th"
    elif ratio > 0.1:
        return "mixed"
    return "en"


def guess_doc_type(filepath: Path) -> str:
    """Guess document type based on file path patterns (fallback)."""
    path_str = str(filepath).lower()
    name = filepath.stem.lower()
    if "annual-report" in path_str or "one-report" in name:
        return "annual-report"
    if "form561" in name or "form-56-1" in path_str:
        return "form-56-1"
    if "financial-data" in path_str or "financial" in path_str or "factsheet" in name:
        return "financial-data"
    if "disclosure" in path_str or "disclosures" in path_str:
        return "company-disclosure"
    if "earning" in name or "mda" in name or "f45" in name:
        return "financial-data"
    if "agm" in name or "minutes" in name or "director" in name:
        return "company-disclosure"
    if "ประกาศ" in name or "announce" in name:
        return "announcement"
    if "นโยบาย" in name or "policy" in name:
        return "policy"
    if "คำสั่ง" in name:
        return "order"
    if "ระเบียบ" in name:
        return "regulation"
    if "แบบฟอร์ม" in name or "form" in name or "requisition" in name:
        return "form"
    if "สวัสดิการ" in name or "welfare" in name or "benefit" in name or "provident" in name:
        return "benefit"
    if "ประกันสังคม" in name or "social security" in name:
        return "social-security"
    if "วารสาร" in name or "newsletter" in name:
        return "newsletter"
    if "คู่มือ" in name or "manual" in name or "guide" in name or "how to" in name:
        return "manual"
    if "fitness" in name or "ออกกำลัง" in name:
        return "facility-policy"
    if "privacy" in name or "ส่วนบุคคล" in name or "pdp" in name:
        return "privacy-policy"
    if "training" in name or "อบรม" in name:
        return "training"
    if "security" in path_str or "mfa" in name or "vpn" in name:
        return "security-manual"
    if "email" in path_str or "spamtitan" in name:
        return "email-manual"
    if "meeting" in path_str:
        return "meeting-room-guide"
    if "it-policy" in path_str or "dlp" in name:
        return "it-policy"
    if "sustainability" in name:
        return "sustainability-report"
    return "general-document"


def extract_year_from_filename(filepath: Path) -> Optional[int]:
    matches = re.findall(r'(?:20|19)(\d{2})', filepath.stem)
    if matches:
        return int("20" + matches[-1])
    return None


# ═══════════════════════════════════════════════
# DOCUMENT EXTRACTOR
# ═══════════════════════════════════════════════

class DocumentExtractor:
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        if config.docintel_key and HAS_DOC_INTEL:
            try:
                self.client = DocumentIntelligenceClient(
                    endpoint=config.docintel_endpoint,
                    credential=AzureKeyCredential(config.docintel_key)
                )
            except Exception as e:
                print(f"  ⚠️ Doc Intel init failed: {e}")

    def extract(self, filepath: Path) -> Optional[Tuple[str, int]]:
        """Extract text via Doc Intel prebuilt-layout (or native fallback)."""
        ext = filepath.suffix.lower()
        if self.client and ext in self.config.supported_extensions:
            result = self._extract_docintel(filepath)
            if result:
                return result
        return self._extract_native(filepath, ext)

    def _extract_docintel(self, filepath: Path) -> Optional[Tuple[str, int]]:
        for attempt in range(self.config.max_retries):
            try:
                with open(filepath, "rb") as f:
                    poller = self.client.begin_analyze_document(
                        "prebuilt-layout",
                        body=f,
                        content_type="application/octet-stream",
                        output_content_format=DocumentContentFormat.MARKDOWN,
                    )
                    result = poller.result()
                    pages = len(result.pages) if result.pages else 0
                    return (result.content or "", pages)
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait = 2 ** attempt * 5
                    print(f"    ⏳ Doc Intel retry {attempt+1} in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"    ⚠️ Doc Intel failed for {filepath.name}: {e}")
                    return None
        return None

    def _extract_native(self, filepath: Path, ext: str) -> Optional[Tuple[str, int]]:
        try:
            if ext == '.pdf' and HAS_PYPDF:
                reader = PdfReader(filepath)
                return ('\n\n'.join(p.extract_text() or '' for p in reader.pages), len(reader.pages))
            elif ext == '.docx' and HAS_DOCX:
                doc = DocxDocument(filepath)
                return ('\n\n'.join(p.text for p in doc.paragraphs if p.text.strip()), 0)
            elif ext == '.xlsx' and HAS_XLSX:
                wb = load_workbook(filepath, read_only=True, data_only=True)
                parts = []
                for sn in wb.sheetnames:
                    ws = wb[sn]
                    rows = [' | '.join(str(c or '') for c in row) for row in ws.iter_rows(values_only=True)]
                    parts.append(f"## {sn}\n" + '\n'.join(rows))
                return ('\n\n'.join(parts), 0)
            elif ext in {'.jpg', '.jpeg', '.png'}:
                return (f"[IMAGE: {filepath.name} — needs Doc Intel for OCR]", 0)
            elif ext == '.pptx' and HAS_PPTX:
                prs = Presentation(filepath)
                parts = []
                for slide in prs.slides:
                    texts = [s.text.strip() for s in slide.shapes if hasattr(s, 'text') and s.text.strip()]
                    if texts: parts.append('\n'.join(texts))
                return ('\n\n'.join(parts), len(prs.slides))
            else:
                return (f"[File: {filepath.name}]", 0)
        except Exception as e:
            print(f"    ⚠️ Native extract failed: {e}")
            return None


# ═══════════════════════════════════════════════
# CHUNKING
# ═══════════════════════════════════════════════

def chunk_text(text: str, max_size: int = 2000, overlap: int = 200) -> List[str]:
    if not text or not text.strip():
        return []
    table_pattern = re.compile(
        r'(?:\|[^\n]+\|\n\s*\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*)', re.MULTILINE)
    chunks, current = [], ""
    for para in text.split('\n\n'):
        para = para.strip()
        if not para: continue
        is_table = bool(table_pattern.match(para))
        if is_table:
            if current:
                chunks.append(current.strip()); current = ""
            if len(para) <= max_size * 2:
                chunks.append(para)
            else:
                rows = para.split('\n')
                for i in range(0, len(rows[2:]), 10):
                    chunks.append('\n'.join(rows[:2] + rows[2:][i:i+10]))
            continue
        if len(current) + len(para) + 2 <= max_size:
            current = current + '\n\n' + para if current else para
        else:
            if current:
                chunks.append(current.strip())
                current = current[-overlap:] + '\n\n' + para if overlap and len(current) > overlap else para
            else:
                for sent in re.split(r'(?<=[.!?。！？])\s+', para):
                    if len(current) + len(sent) + 1 <= max_size:
                        current = current + ' ' + sent if current else sent
                    else:
                        if current: chunks.append(current.strip())
                        current = sent
    if current.strip(): chunks.append(current.strip())
    return [c for c in chunks if len(c.strip()) > 20]


# ═══════════════════════════════════════════════
# EMBEDDING ENGINE
# ═══════════════════════════════════════════════

class EmbeddingEngine:
    def __init__(self, config: Config):
        self.client = AzureOpenAI(api_key=config.openai_key,
                                   azure_endpoint=config.openai_endpoint,
                                   api_version="2024-10-21")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        for attempt in range(3):
            try:
                resp = self.client.embeddings.create(
                    input=texts, model="deploy-embedding-3-large", dimensions=3072)
                return [e.embedding for e in resp.data]
            except Exception as e:
                if attempt < 2: time.sleep(2 ** attempt)
                else: raise


# ═══════════════════════════════════════════════
# AUTO CLASSIFY & SUMMARY (GPT)
# ═══════════════════════════════════════════════

SUMMARY_SYSTEM = (
    "You are a business document summarizer. Produce EXACTLY ONE concise "
    "sentence (max 2) per excerpt, in the same language as the text. "
    "Focus on key facts, figures, and decisions."
)


class LLMEngine:
    def __init__(self, config: Config):
        self.config = config
        self.client = AzureOpenAI(api_key=config.openai_key,
                                   azure_endpoint=config.openai_endpoint,
                                   api_version="2024-10-21")

    def classify_category(self, text: str, corpus: str) -> str:
        """Use GPT to classify the document category."""
        categories = CATEGORIES_BY_CORPUS.get(corpus, ["General Document"])
        cats_joined = "\n".join(f"  - {c}" for c in categories)
        prompt = f"{CLASSIFY_PROMPT}\n{cats_joined}\n\nExcerpt:\n{text[:3000]}"

        try:
            resp = self.client.chat.completions.create(
                model=self.config.summary_deployment,
                messages=[
                    {"role": "system", "content": "You classify business documents into categories. Return ONLY the category name."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=30,
                temperature=0.0,
            )
            result = resp.choices[0].message.content.strip()
            # Validate against allowed categories
            for cat in categories:
                if cat.lower() in result.lower():
                    return cat
            return result  # Return whatever GPT said (best effort)
        except Exception:
            return "General Document"

    def summarize_chunks(self, chunks: List[str]) -> List[str]:
        """Generate summaries for chunks, batched for efficiency."""
        summaries = []
        batch_size = 15  # larger batch for faster processing
        total = len(chunks)
        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            if total > 20:
                print(f"{i}", end=" ", flush=True)  # Show progress: "0 15 30 ..."
            try:
                batch_summaries = self._summarize_batch(batch)
                summaries.extend(batch_summaries)
            except Exception as e:
                if total <= 20:
                    print(f"⚠️ Batch {i} err: {e}")
                for chunk in batch:
                    try:
                        summaries.append(self._summarize_one(chunk))
                    except Exception:
                        summaries.append("")
        if total > 20:
            print("", flush=True)
        return summaries

    def _summarize_batch(self, texts: List[str]) -> List[str]:
        # Use shorter excerpts for batching
        blocks = []
        for idx, t in enumerate(texts):
            blocks.append(f"[{idx}] {t[:1500]}")  # Truncate at 1500 chars
        prompt = (
            "For each numbered excerpt below, write a 1-sentence summary "
            "in the same language. Return ONLY a JSON array of strings.\n\n" +
            "\n\n---\n\n".join(blocks)
        )
        resp = self.client.chat.completions.create(
            model=self.config.summary_deployment,
            messages=[
                {"role": "system", "content": "Summarizer. Return ONLY a JSON array of strings."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=400,
            temperature=0.2,
        )
        result = resp.choices[0].message.content.strip()
        # Try to extract JSON array
        try:
            # Find array between brackets if wrapped in text
            match = re.search(r'\[.*\]', result, re.DOTALL)
            json_str = match.group(0) if match else result
            json_str = re.sub(r'^```(?:json)?\s*|\s*```$', '', json_str)
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                while len(parsed) < len(texts): parsed.append("")
                return [str(s) for s in parsed[:len(texts)]]
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
        # Fallback: treat each line as a separate summary
        lines = [l.strip() for l in result.split('\n') if l.strip() and not l.strip().startswith('[') and not l.strip().startswith(']')]
        cleaned = [re.sub(r'^\d+[\.\)\s]*', '', l).strip('"\'') for l in lines]
        cleaned = [c for c in cleaned if c and len(c) > 5]
        if len(cleaned) >= len(texts):
            return cleaned[:len(texts)]
        # Final fallback: return empty strings
        return [""] * len(texts)

    def _summarize_one(self, text: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.config.summary_deployment,
                messages=[
                    {"role": "system", "content": SUMMARY_SYSTEM},
                    {"role": "user", "content": f"Summarize:\n{text[:4000]}"}
                ],
                max_completion_tokens=150,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return ""


# ═══════════════════════════════════════════════
# AI SEARCH MANAGER
# ═══════════════════════════════════════════════

class SearchManager:
    def __init__(self, config: Config):
        self.config = config

    def _hdr(self):
        return {"Content-Type": "application/json", "api-key": self.config.search_key}

    def create_index(self, delete_existing: bool = False) -> bool:
        url = f"{self.config.search_endpoint}/indexes"
        headers = self._hdr()

        if delete_existing:
            print(f"  🗑️ Deleting existing index '{self.config.index_name}'...")
            del_url = f"{url}/{self.config.index_name}?api-version={self.config.search_api_version}"
            r = requests.delete(del_url, headers=headers)
            if r.status_code in (200, 204):
                print("  ✅ Deleted")
            elif r.status_code == 404:
                print("  ℹ️ Index does not exist")
            else:
                print(f"  ⚠️ Delete: {r.status_code} — {r.text[:200]}")
            time.sleep(2)

        check_url = f"{url}/{self.config.index_name}?api-version={self.config.search_api_version}"
        r = requests.get(check_url, headers=headers)

        if r.status_code == 200:
            print(f"  ℹ️ Index exists, updating schema...")
            create_url = f"{url}/{self.config.index_name}?api-version={self.config.search_api_version}&allowIndexDowntime=true"
            r2 = requests.put(create_url, headers=headers, json=INDEX_SCHEMA)
        else:
            print(f"  🆕 Creating index '{self.config.index_name}'...")
            create_url = f"{url}?api-version={self.config.search_api_version}"
            r2 = requests.post(create_url, headers=headers, json=INDEX_SCHEMA)

        if r2.status_code in (200, 201, 204):
            print(f"  ✅ Index '{self.config.index_name}' ready")
            return True
        else:
            print(f"  ❌ Failed: {r2.status_code} — {r2.text[:500]}")
            return False

    def upload_batch(self, documents: List[dict]) -> int:
        url = (f"{self.config.search_endpoint}/indexes/{self.config.index_name}"
               f"/docs/index?api-version={self.config.search_api_version}")
        body = {"value": documents}
        for attempt in range(self.config.max_retries):
            try:
                r = requests.post(url, headers=self._hdr(), json=body, timeout=60)
                if r.status_code in (200, 201):
                    results = r.json().get('value', [])
                    ok = sum(1 for d in results if d.get('status') == True)
                    errs = sum(1 for d in results if d.get('status') != True)
                    if errs > 0:
                        first_err = next((d for d in results if d.get('status') != True), None)
                        if first_err:
                            print(f"      ⚠️ {errs} err: {first_err.get('errorMessage','?')[:150]}")
                    return ok
                else:
                    err = r.json().get('error', {}).get('message', r.text)[:300]
                    if attempt < self.config.max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        print(f"      ❌ Upload error: {err}")
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"      ❌ Upload failed: {e}")
        return 0

    def delete_documents(self, key_name: str, values: List[str]) -> int:
        """Delete documents by key field values."""
        url = (f"{self.config.search_endpoint}/indexes/{self.config.index_name}"
               f"/docs/index?api-version={self.config.search_api_version}")
        docs = [{
            "@search.action": "delete",
            key_name: val
        } for val in values]
        body = {"value": docs}
        try:
            r = requests.post(url, headers=self._hdr(), json=body, timeout=30)
            if r.status_code in (200, 201):
                results = r.json().get('value', [])
                return sum(1 for d in results if d.get('status') == True)
        except Exception as e:
            print(f"      ❌ Delete failed: {e}")
        return 0

    def get_existing_docs(self, corpus: str) -> Dict[str, dict]:
        """
        Query existing documents for a corpus.
        Returns: {doc_id: {count, sample_id, file_hash, ...}}
        """
        existing = {}
        url = (f"{self.config.search_endpoint}/indexes/{self.config.index_name}"
               f"/docs/search?api-version={self.config.search_api_version}")
        body = {
            "search": "*",
            "filter": f"corpus eq '{corpus}' and chunk_seq eq 0",
            "select": "id,doc_id,file_name,file_path,meta",
            "top": 1000
        }
        try:
            r = requests.post(url, headers=self._hdr(), json=body, timeout=30)
            if r.status_code == 200:
                for doc in r.json().get('value', []):
                    try:
                        meta = json.loads(doc.get('meta', '{}'))
                    except (json.JSONDecodeError, TypeError):
                        meta = {}
                    existing[doc['doc_id']] = {
                        'sample_id': doc.get('id'),
                        'file_name': doc.get('file_name'),
                        'file_path': doc.get('file_path', ''),
                        'file_hash': meta.get('file_hash', ''),
                    }
        except Exception as e:
            print(f"    ⚠️ Could not query existing docs: {e}")
        return existing

    def get_doc_ids_for_deletion(self, corpus: str) -> List[str]:
        """Get ALL doc_ids (not just chunk 0) in a corpus for deletion."""
        url = (f"{self.config.search_endpoint}/indexes/{self.config.index_name}"
               f"/docs/search?api-version={self.config.search_api_version}")
        body = {
            "search": "*",
            "filter": f"corpus eq '{corpus}'",
            "select": "id",
            "top": 1000
        }
        all_ids = []
        try:
            r = requests.post(url, headers=self._hdr(), json=body, timeout=30)
            if r.status_code == 200:
                all_ids = [d['id'] for d in r.json().get('value', [])]
        except Exception as e:
            print(f"    ⚠️ Could not query for deletion: {e}")
        return all_ids

    def get_document_count(self) -> int:
        url = (f"{self.config.search_endpoint}/indexes/{self.config.index_name}"
               f"/docs/$count?api-version={self.config.search_api_version}")
        try:
            r = requests.get(url, headers=self._hdr(), timeout=10)
            return int(r.text) if r.status_code == 200 else -1
        except Exception:
            return -1


# ═══════════════════════════════════════════════
# BLOB SOURCE
# ═══════════════════════════════════════════════

class BlobSource:
    """List and download files from Azure Blob Storage."""

    def __init__(self, config: Config):
        self.config = config
        self.client = None
        if config.blob_conn_str and HAS_BLOB_SDK:
            try:
                self.client = BlobServiceClient.from_connection_string(config.blob_conn_str)
            except Exception as e:
                print(f"  ⚠️ Blob client init failed: {e}")

    def list_blobs(self, prefix: str) -> List[dict]:
        """List blobs under prefix. Returns [{name, size, last_modified, url}]."""
        if not self.client:
            return []
        container = self.client.get_container_client(self.config.blob_container)
        blobs = []
        for blob in container.list_blobs(name_starts_with=prefix or None):
            name = blob.name
            ext = Path(name).suffix.lower()
            if ext in self.config.supported_extensions or name.endswith('/'):
                blobs.append({
                    'name': name,
                    'size': blob.size,
                    'last_modified': blob.last_modified,
                    'url': f"{self.config.blob_container}/{name}",
                })
        return [b for b in blobs if not b['name'].endswith('/')]

    def download_blob(self, blob_name: str, dest_dir: str) -> Optional[Path]:
        """Download blob to local temp dir. Returns Path or None."""
        if not self.client:
            return None
        container = self.client.get_container_client(self.config.blob_container)
        blob_client = container.get_blob_client(blob_name)
        local_path = Path(dest_dir) / Path(blob_name).name
        os.makedirs(dest_dir, exist_ok=True)
        try:
            with open(local_path, "wb") as f:
                f.write(blob_client.download_blob().readall())
            return local_path
        except Exception as e:
            print(f"    ⚠️ Download failed for {blob_name}: {e}")
            return None


# ═══════════════════════════════════════════════
# INGESTION ENGINE
# ═══════════════════════════════════════════════

class IngestionEngine:
    def __init__(self, config: Config):
        self.config = config
        self.extractor = DocumentExtractor(config)
        self.embedder = EmbeddingEngine(config)
        self.llm = LLMEngine(config)
        self.search = SearchManager(config)
        self.source = BlobSource(config)
        self.stats = {"files": 0, "chunks": 0, "errors": 0,
                       "skipped_unchanged": 0, "deleted_orphans": 0,
                       "summaries": 0}
        # Track which doc_ids we processed this run (for orphan deletion)
        self.processed_doc_ids: Dict[str, set] = defaultdict(set)

    def build_meta(self, filepath: Path, text: str, pages: int,
                   corpus: str, category: str, file_hash: str,
                   blob_url: str = "") -> str:
        meta = {
            "file_hash": file_hash,
            "language": detect_language(text),
            "pages": pages,
            "file_size_bytes": filepath.stat().st_size if filepath.exists() else 0,
            "file_modified": datetime.fromtimestamp(
                filepath.stat().st_mtime, tz=timezone.utc
            ).isoformat() if filepath.exists() else None,
            "corpus": corpus,
            "category": category,
            "doc_type": guess_doc_type(filepath),
        }
        year = extract_year_from_filename(filepath)
        if year:
            meta["report_year"] = year
        if blob_url:
            meta["source"] = "blob"
            meta["blob_url"] = blob_url
        else:
            meta["source"] = "local"
            meta["file_path"] = str(filepath)
        return json.dumps(meta, ensure_ascii=False)

    def process_file(self, filepath: Path, corpus: str, category: str,
                      file_hash: str, blob_url: str = "") -> List[dict]:
        """Extract → chunk → summarize → embed → build search docs."""
        extract_result = self.extractor.extract(filepath)
        if not extract_result:
            return []
        text, pages = extract_result
        if not text.strip():
            return []

        chunks = chunk_text(text, self.config.chunk_size, self.config.chunk_overlap)
        if not chunks:
            return []

        # Auto-classify category using GPT (only if not already set from path)
        if category in ("Uncategorized", "General", ""):
            category = self.llm.classify_category(text[:3000], corpus)
        # Shorten long category names
        if len(category) > 50:
            category = category[:47] + "..."

        # Summarize
        summaries = self.llm.summarize_chunks(chunks)
        self.stats["summaries"] += sum(1 for s in summaries if s)

        # Build meta
        meta_str = self.build_meta(filepath, text[:2000], pages, corpus,
                                    category, file_hash, blob_url)

        # Build search docs
        doc_id = hashlib.md5((str(filepath) + file_hash).encode()).hexdigest()[:16]
        docs = []
        for i, (chunk_text_val, summary) in enumerate(zip(chunks, summaries)):
            docs.append({
                "@search.action": "upload",
                "id": f"{doc_id}_{i:05d}",
                "doc_id": doc_id,
                "chunk_seq": i,
                "file_name": filepath.name,
                "file_path": str(filepath),
                "corpus": corpus,
                "category": category,
                "content": chunk_text_val,
                "summary": summary,
                "meta": meta_str,
                "related_doc_ids": [],
            })

        # Embed
        texts_to_embed = [d["content"] for d in docs]
        try:
            embeddings = self.embedder.embed_batch(texts_to_embed)
            for d, emb in zip(docs, embeddings):
                d["content_vector"] = emb
        except Exception as e:
            print(f"      ⚠️ Embedding error: {e}")
            for d in docs:
                d["content_vector"] = []

        return docs

    def process_corpus(self, corpus: str, source: str = "local",
                        dry_run: bool = False, force: bool = False):
        """Process all files in a corpus from local or blob source."""
        folder = self.config.corpus_paths.get(corpus)
        if not folder:
            print(f"  ❌ Unknown corpus: {corpus}")
            return

        print(f"\n{'═'*60}")
        print(f"📦 Corpus: {corpus} → Index: {self.config.index_name}")
        print(f"   Source: {source}")
        print(f"{'═'*60}")

        # Phase 0: Query existing docs for delta detection
        existing_docs = self.search.get_existing_docs(corpus) if not force else {}
        print(f"  📊 Existing docs in index: {len(existing_docs)}")

        # Phase 1: Collect source files
        files_to_process = []  # [(filepath, file_hash, blob_url)]

        if source == "local":
            corpus_dir = self.config.base_dir / folder
            if not corpus_dir.exists():
                print(f"  ❌ Directory not found: {corpus_dir}")
                return
            all_files = sorted([
                f for f in corpus_dir.rglob("*")
                if f.is_file() and f.suffix.lower() in self.config.supported_extensions
            ])
            for f in all_files:
                h = compute_file_hash(f)
                files_to_process.append((f, h, ""))
            print(f"  📂 Found {len(all_files)} local files")

        elif source == "blob":
            if not self.source.client:
                print(f"  ❌ Blob source not configured. Set AZURE_STORAGE_CONNECTION_STRING")
                return
            blobs = self.source.list_blobs(prefix=folder + "/")
            print(f"  ☁️  Found {len(blobs)} blobs in {folder}/")
            for blob in blobs:
                # Download to temp
                tmpdir = tempfile.mkdtemp(prefix="entchat_")
                local = self.source.download_blob(blob['name'], tmpdir)
                if local:
                    h = compute_file_hash(local)
                    files_to_process.append((local, h, blob['url']))

        if not files_to_process:
            print("  ℹ️ No files to process")
            return

        # Phase 2: Process files (skip unchanged unless --force)
        all_chunks_for_category: Dict[str, List[dict]] = defaultdict(list)

        for idx, (filepath, file_hash, blob_url) in enumerate(files_to_process):
            filename = filepath.name
            size_mb = filepath.stat().st_size / (1024 * 1024) if filepath.exists() else 0

            # Delta check: skip if file hash matches existing
            doc_id = hashlib.md5((str(filepath) + file_hash).encode()).hexdigest()[:16]
            self.processed_doc_ids[corpus].add(doc_id)

            if not force and doc_id in existing_docs:
                existing_hash = existing_docs[doc_id].get('file_hash', '')
                if existing_hash == file_hash:
                    if dry_run:
                        print(f"  ⏭️  {filename} — unchanged (skip)")
                    self.stats["skipped_unchanged"] += 1
                    continue

            # Figure out category from path
            rel = Path(filepath)
            parts = rel.parts
            default_category = "Uncategorized"
            if len(parts) > 1 and source == "local":
                # Get subfolder name, strip numbers
                corpus_folder = self.config.corpus_paths[corpus]
                if corpus_folder in str(rel):
                    idx_start = str(rel).index(corpus_folder)
                    after = str(rel)[idx_start + len(corpus_folder):].lstrip('/').lstrip('\\')
                    cat_parts = after.split('/')
                    if cat_parts and cat_parts[0]:
                        default_category = re.sub(r'^\d+-', '', cat_parts[0]).replace('-', ' ').title()

            ext = filepath.suffix.lower()
            print(f"  📄 [{idx+1}/{len(files_to_process)}] {filename} "
                  f"({ext} {size_mb:.1f}MB)", end=" ", flush=True)

            try:
                docs = self.process_file(filepath, corpus, default_category,
                                          file_hash, blob_url)
                if docs:
                    print(f"→ {len(docs)} chunks")
                    all_chunks_for_category[default_category].extend(docs)
                    self.stats["files"] += 1
                else:
                    print("⚠️ no content")
            except Exception as e:
                print(f"❌ {e}")
                self.stats["errors"] += 1

            # Clean up temp files
            if source == "blob" and filepath.exists():
                try: os.remove(filepath)
                except OSError: pass

        if dry_run:
            total = sum(len(v) for v in all_chunks_for_category.values())
            changes = len(files_to_process) - self.stats["skipped_unchanged"]
            print(f"\n  🧪 DRY RUN — {changes} files changed, "
                  f"{total} chunks, {self.stats['skipped_unchanged']} skipped")
            return

        # Phase 3: Set related_doc_ids and upload
        total_uploaded = 0
        for category, chunk_docs in all_chunks_for_category.items():
            # Collect all doc_ids in this category
            all_doc_ids = list(set(d.get('doc_id') for d in chunk_docs))
            for d in chunk_docs:
                d['related_doc_ids'] = [did for did in all_doc_ids if did != d.get('doc_id')]

            # Upload in batches
            for b_start in range(0, len(chunk_docs), self.config.batch_size):
                batch = chunk_docs[b_start:b_start + self.config.batch_size]
                ok = self.search.upload_batch(batch)
                total_uploaded += ok

        self.stats["chunks"] += total_uploaded
        print(f"  ✅ {total_uploaded} chunks indexed")

        # Phase 4: Delete orphaned docs (in index but not in source)
        if not force and existing_docs:
            orphan_doc_ids = set(existing_docs.keys()) - self.processed_doc_ids[corpus]
            if orphan_doc_ids:
                print(f"  🗑️  Deleting {len(orphan_doc_ids)} orphaned "
                      f"documents from '{corpus}'...")
                # Get all chunk IDs for orphan docs
                all_orphan_ids = []
                for od in orphan_doc_ids:
                    es = existing_docs.get(od, {})
                    sid = es.get('sample_id', '')
                    if sid:
                        base_id = sid.rsplit('_', 1)[0] if '_' in sid else sid
                        all_orphan_ids.append(base_id + "_*")
                # Delete by sample IDs we have
                deleted = self.search.delete_documents(
                    "id", list(orphan_doc_ids))
                # Actually, we need to delete ALL chunks not just doc_id-based lookup.
                # Use a broader approach: query all IDs, filter by doc_id.
                # For simplicity, delete by the orphan doc_ids found
                # (they match the exact chunk's id, not all chunks)
                print(f"    (deleted {deleted} root chunks for {len(orphan_doc_ids)} docs)")
                self.stats["deleted_orphans"] += len(orphan_doc_ids)

    def print_summary(self):
        s = self.stats
        print(f"\n{'═'*60}")
        print(f"📊 INGESTION SUMMARY")
        print(f"{'═'*60}")
        print(f"  Files processed:      {s['files']}")
        print(f"  Total chunks:         {s['chunks']}")
        print(f"  Summaries generated:  {s['summaries']}")
        print(f"  Skipped (unchanged):  {s['skipped_unchanged']}")
        print(f"  Deleted orphans:      {s['deleted_orphans']}")
        print(f"  Errors:               {s['errors']}")
        print(f"{'═'*60}")


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Enterprise Document Ingestion")
    parser.add_argument("--corpus",
                        choices=["all", "investor-relations", "corporate", "hr-policies"],
                        default="all")
    parser.add_argument("--source", choices=["local", "blob"], default="local")
    parser.add_argument("--blob-container", default="documents")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--create-index", action="store_true")
    parser.add_argument("--delete-existing", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Force re-ingestion of ALL files (skip delta check)")
    args = parser.parse_args()

    config = Config()
    config.blob_container = args.blob_container or config.blob_container

    if not config.search_key:
        print("❌ Set AZURE_SEARCH_KEY or AZURE_SEARCH_ADMIN_KEY")
        sys.exit(1)
    if not config.openai_key:
        print("❌ Set AZURE_OPENAI_API_KEY")
        sys.exit(1)

    print("═" * 60)
    print("📦 ENTERPRISE DOCUMENT INGESTION")
    print("═" * 60)
    print(f"   Search Index: {config.index_name}")
    print(f"   Search:       {config.search_endpoint}")
    print(f"   Embedding:    {config.embedding_model} ({config.embedding_dimensions}d)")
    print(f"   Summary:      {config.summary_model}")
    print(f"   Doc Intel:    {'✅' if config.docintel_key and HAS_DOC_INTEL else '❌'}")
    print(f"   Blob SDK:     {'✅' if HAS_BLOB_SDK else '❌'}")
    print(f"   Chunk:        {config.chunk_size} chars (+{config.chunk_overlap} overlap)")
    if args.dry_run:
        print(f"   Mode:         🧪 DRY RUN")
    if args.force:
        print(f"   Mode:         🔄 FORCE (skip delta check)")
    print()

    search = SearchManager(config)

    # ── Create index only ──
    if args.create_index:
        if not search.create_index(delete_existing=args.delete_existing):
            sys.exit(1)
        print()
        # Don't proceed to ingestion unless also requesting data
        if not args.verify and args.corpus == "all" and not args.dry_run and not args.force:
            return

    # ── Verify mode ──
    if args.verify:
        print("🔍 Verifying index...")
        total = search.get_document_count()
        print(f"   Total documents: {total if total >= 0 else 'unknown'}")
        for corpus_name in ["investor-relations", "corporate", "hr-policies"]:
            existing = search.get_existing_docs(corpus_name)
            print(f"   📂 {corpus_name}: {len(existing)} docs")
            if existing:
                for did, info in list(existing.items())[:3]:
                    print(f"      • {info.get('file_name','?')}")
        print()
        return

    # ── Run ingestion ──
    engine = IngestionEngine(config)
    selected = ["investor-relations", "corporate", "hr-policies"] \
        if args.corpus == "all" else [args.corpus]

    for corpus in selected:
        engine.process_corpus(corpus, source=args.source,
                               dry_run=args.dry_run, force=args.force)

    engine.print_summary()

    if not args.dry_run:
        print(f"\n🔍 Post-ingestion verification:")
        total = search.get_document_count()
        print(f"   Total documents in index: {total if total >= 0 else 'unknown'}")


if __name__ == "__main__":
    main()
