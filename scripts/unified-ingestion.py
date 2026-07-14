#!/usr/bin/env python3
"""
unified-ingestion.py — Ingest ALL Haadthip documents into AI Search
====================================================================
One script to rule them all. Handles every file type and every corpus.

Corpuses:
  - haadthip-ir/        (PDF annual reports, financial data)
  - haadthip-public/    (PDF corporate docs: security, email, meeting, IT policy)
  - sap-hip/            (PDF/DOCX/PPTX SAP manuals)
  - mihcm-hr/           (DOC/XLS/JPG/PNG/XLSX HR documents)

File types:
  - .pdf   → pypdf (native text)  OR Document Intelligence layout model
  - .doc   → Document Intelligence (layout model, markdown output)
  - .docx  → python-docx  OR Document Intelligence
  - .xls   → Document Intelligence
  - .xlsx  → openpyxl  OR Document Intelligence
  - .jpg/png → Document Intelligence (OCR + layout)
  - .pptx  → python-pptx  OR Document Intelligence

Pipeline per file:
  1. Extract text (appropriate extractor per type)
  2. Chunk (RecursiveCharacterTextSplitter, 2000 chars, 200 overlap)
  3. Classify subject area (keyword heuristic, optional)
  4. Generate embedding (Azure OpenAI, text-embedding-3-large)
  5. Index to AI Search

Usage:
  export AZURE_SEARCH_KEY="..."
  export AZURE_OPENAI_KEY="..."          # Required for embeddings
  export DOCUMENTINTELLIGENCE_KEY="..."  # Required for complex files
  
  # Full run
  python3 scripts/unified-ingestion.py
  
  # Specific corpus only
  python3 scripts/unified-ingestion.py --corpus mihcm-hr
  
  # Dry run
  python3 scripts/unified-ingestion.py --dry-run
"""

import os, re, sys, hashlib, time, argparse, io
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Tuple, Callable

# ── Core libraries ──
import requests
from openai import AzureOpenAI

# ── Optional: Document Intelligence for complex files ──
try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import ContentFormat
    HAS_DOC_INTEL = True
except ImportError:
    HAS_DOC_INTEL = False

# ── Optional: Native file parsers ──
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
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "https://srch-entchat-poc-sand.search.windows.net")
    search_key = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
    search_api_version = "2024-07-01"
    
    # Azure OpenAI (Embeddings)
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
    openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    embedding_deployment = "deploy-embedding-3-large"
    embedding_model = "text-embedding-3-large"
    embedding_dimensions = 3072
    
    # Document Intelligence
    docintel_endpoint = os.getenv("DOCUMENTINTELLIGENCE_ENDPOINT", "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
    docintel_key = os.getenv("DOCUMENTINTELLIGENCE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")
    
    # Ingestion
    base_dir = Path("documents")
    chunk_size = 2000
    chunk_overlap = 200
    batch_size = 50
    max_retries = 3
    use_doc_intel = True  # Use Document Intelligence for complex files (PDF/DOC/XLS/Images)
    
    # Target indexes
    indexes = {
        "haadthip-ir":  "haadthip-ir-idx",
        "haadthip-public": "haadthip-public-idx-v2",
        "sap-hip":      "sap-docs-idx",
        "mihcm-hr":     "mihcm-hr-idx",
    }


# ═══════════════════════════════════════════════
# TEXT EXTRACTORS (per file type)
# ═══════════════════════════════════════════════

class TextExtractor:
    """Extract text from various file formats."""
    
    def __init__(self, config: Config):
        self.config = config
        self.docintel = None
        
        if config.use_doc_intel and config.docintel_key and HAS_DOC_INTEL:
            try:
                self.docintel = DocumentIntelligenceClient(
                    endpoint=config.docintel_endpoint,
                    credential=AzureKeyCredential(config.docintel_key)
                )
            except Exception as e:
                print(f"  ⚠️ Doc Intel init failed, using native parsers: {e}")
    
    def extract(self, filepath: Path) -> Optional[str]:
        """Route to appropriate extractor based on file extension."""
        ext = filepath.suffix.lower()
        size_mb = filepath.stat().st_size / (1024 * 1024)
        
        # Very small files - use native parsers
        if size_mb < 0.05:
            return self._extract_native(filepath, ext)
        
        # Use Doc Intel for complex/large files if available
        if self.docintel and ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.ppt', '.pptx'}:
            return self._extract_docintel(filepath)
        
        return self._extract_native(filepath, ext)
    
    def _extract_docintel(self, filepath: Path) -> Optional[str]:
        """Extract using Document Intelligence layout model (markdown output)."""
        for attempt in range(self.config.max_retries):
            try:
                with open(filepath, "rb") as f:
                    poller = self.docintel.begin_analyze_document(
                        model_id="prebuilt-layout",
                        analyze_request=f,
                        output_content_format=ContentFormat.MARKDOWN,
                        content_type="application/octet-stream"
                    )
                    result = poller.result()
                    return result.content
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt * 5)
                else:
                    print(f"    ⚠️ Doc Intel failed for {filepath.name}: {e}")
                    return self._extract_native(filepath, filepath.suffix.lower())
        return None
    
    def _extract_native(self, filepath: Path, ext: str) -> Optional[str]:
        """Extract using native Python libraries."""
        try:
            if ext == '.pdf' and HAS_PYPDF:
                reader = PdfReader(filepath)
                return '\n\n'.join(page.extract_text() or '' for page in reader.pages)
            
            elif ext == '.docx' and HAS_DOCX:
                doc = DocxDocument(filepath)
                return '\n\n'.join(p.text for p in doc.paragraphs if p.text.strip())
            
            elif ext == '.doc':
                # .doc format is hard natively — read as raw text, might get garbage
                return f"[DOC: {filepath.name} — use Document Intelligence for full extraction]"
            
            elif ext == '.xlsx' and HAS_XLSX:
                wb = load_workbook(filepath, read_only=True, data_only=True)
                parts = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    rows = []
                    for row in ws.iter_rows(values_only=True):
                        rows.append(' | '.join(str(c or '') for c in row))
                    parts.append(f"## {sheet_name}\n" + '\n'.join(rows))
                return '\n\n'.join(parts)
            
            elif ext == '.xls':
                return f"[XLS: {filepath.name} — use Document Intelligence for full extraction]"
            
            elif ext in {'.jpg', '.jpeg', '.png'}:
                return f"[IMAGE: {filepath.name} — use Document Intelligence for OCR]"
            
            elif ext == '.pptx' and HAS_PPTX:
                prs = Presentation(filepath)
                parts = []
                for slide in prs.slides:
                    texts = []
                    for shape in slide.shapes:
                        if hasattr(shape, 'text') and shape.text.strip():
                            texts.append(shape.text.strip())
                    if texts:
                        parts.append('\n'.join(texts))
                return '\n\n'.join(parts)
            
            elif ext == '.ppt':
                return f"[PPT: {filepath.name} — use Document Intelligence]"
            
            else:
                return f"[UNSUPPORTED: {filepath.name} ({ext})]"
                
        except Exception as e:
            print(f"    ⚠️ Native extract failed for {filepath.name}: {e}")
            return None


# ═══════════════════════════════════════════════
# CHUNKING
# ═══════════════════════════════════════════════

def chunk_text(text: str, max_size: int = 2000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap.
    - Split on paragraph boundaries (double newlines)
    - If paragraph exceeds max_size, split on sentences
    - Keep tables (markdown pipe tables) as atomic units
    """
    if not text or not text.strip():
        return []
    
    # Detect and preserve markdown tables
    table_pattern = re.compile(
        r'(?:\|[^\n]+\|\n\s*\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*)',
        re.MULTILINE
    )
    
    chunks = []
    paragraphs = text.split('\n\n')
    current = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Check if this paragraph is a table
        is_table = bool(table_pattern.match(para))
        
        # Tables should be atomic if they fit
        if is_table:
            if current:
                chunks.append(current.strip())
                current = ""
            if len(para) <= max_size * 2:  # Allow tables up to double
                chunks.append(para)
            else:
                # Split large table by rows
                rows = para.split('\n')
                header = rows[:2]  # Keep header with each chunk
                body = rows[2:]
                for i in range(0, len(body), 10):
                    chunk_rows = header + body[i:i+10]
                    chunks.append('\n'.join(chunk_rows))
            continue
        
        # Regular paragraph
        if len(current) + len(para) + 2 <= max_size:
            current = current + '\n\n' + para if current else para
        else:
            if current:
                chunks.append(current.strip())
                # Overlap: keep last bit of previous chunk
                if overlap > 0 and len(current) > overlap:
                    current = current[-overlap:] + '\n\n' + para
                else:
                    current = para
            else:
                # Single paragraph too large — split by sentences
                sentences = re.split(r'(?<=[.!?。！？])\s+', para)
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_size:
                        current = current + ' ' + sent if current else sent
                    else:
                        if current:
                            chunks.append(current.strip())
                        current = sent
    
    if current.strip():
        chunks.append(current.strip())
    
    return [c for c in chunks if c.strip() and len(c.strip()) > 20]


# ═══════════════════════════════════════════════
# SUBJECT CLASSIFICATION (for IR docs)
# ═══════════════════════════════════════════════

SUBJECT_KEYWORDS = {
    "financial": ["revenue", "profit", "EBITDA", "income", "balance sheet", "cash flow",
                  "dividend", "รายได้", "กำไร", "งบการเงิน", "สินทรัพย์"],
    "governance": ["board of directors", "AGM", "shareholder", "corporate governance",
                   "กรรมการ", "ผู้ถือหุ้น", "คณะกรรมการ"],
    "business": ["carbonate", "market share", "product", "distribution",
                 "ยอดขาย", "ส่วนแบ่งการตลาด", "สินค้า"],
    "esg": ["ESG", "environment", "carbon", "sustainability",
            "สิ่งแวดล้อม", "ความยั่งยืน"],
    "risk": ["risk", "mitigation", "ความเสี่ยง", "internal control"],
    "company-profile": ["company overview", "vision", "mission", "วิสัยทัศน์", "ประวัติ"],
}

def classify_subject(text: str) -> List[str]:
    """Simple keyword-based subject classification."""
    text_lower = text.lower()
    matched = []
    for subject, keywords in SUBJECT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score >= 2:
            matched.append(subject)
    return matched or ["company-profile"]


# ═══════════════════════════════════════════════
# EMBEDDING ENGINE
# ═══════════════════════════════════════════════

class EmbeddingEngine:
    def __init__(self, config: Config):
        self.config = config
        self.client = AzureOpenAI(
            api_key=config.openai_key,
            azure_endpoint=config.openai_endpoint,
            api_version="2024-10-21"
        )
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        for attempt in range(self.config.max_retries):
            try:
                resp = self.client.embeddings.create(
                    input=texts,
                    model=self.config.embedding_deployment,
                    dimensions=self.config.embedding_dimensions
                )
                return [e.embedding for e in resp.data]
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise


# ═══════════════════════════════════════════════
# AI SEARCH INDEXER
# ═══════════════════════════════════════════════

class SearchIndexer:
    def __init__(self, config: Config, index_name: str):
        self.config = config
        self.index_name = index_name
        self.endpoint = config.search_endpoint
    
    def _hdr(self):
        return {
            "Content-Type": "application/json",
            "api-key": self.config.search_key
        }
    
    def upload_batch(self, documents: List[dict]) -> int:
        """Upload documents to search index."""
        url = f"{self.endpoint}/indexes/{self.index_name}/docs/index?api-version={self.config.search_api_version}"
        body = {"value": documents}
        
        for attempt in range(self.config.max_retries):
            try:
                r = requests.post(url, headers=self._hdr(), json=body, timeout=30)
                if r.status_code in (200, 201):
                    results = r.json().get('value', [])
                    ok = sum(1 for d in results if d.get('status') == True)
                    errs = sum(1 for d in results if d.get('status') != True)
                    if errs > 0:
                        first_err = next((d for d in results if d.get('status') != True), None)
                        if first_err:
                            print(f"      ⚠️ {errs} failed: {first_err.get('errorMessage', '?')[:100]}")
                    return ok
                else:
                    err = r.json().get('error', {}).get('message', r.text)[:200]
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


# ═══════════════════════════════════════════════
# INGESTION ENGINE
# ═══════════════════════════════════════════════

class IngestionEngine:
    def __init__(self, config: Config):
        self.config = config
        self.extractor = TextExtractor(config)
        self.embedder = EmbeddingEngine(config)
        self.stats = {"files": 0, "chunks": 0, "errors": 0, "skipped": 0}
    
    def process_file(self, filepath: Path, indexer: SearchIndexer, corpus: str) -> int:
        """Process one file: extract → chunk → embed → index."""
        filename = filepath.name
        ext = filepath.suffix.lower()
        size_mb = filepath.stat().st_size / (1024 * 1024)
        
        print(f"  📄 {filename} ({ext} {size_mb:.1f}MB)")
        
        # Extract
        text = self.extractor.extract(filepath)
        if not text:
            print(f"    ⚠️ No text extracted")
            self.stats["skipped"] += 1
            return 0
        
        # Chunk
        chunks = chunk_text(text, self.config.chunk_size, self.config.chunk_overlap)
        if not chunks:
            print(f"    ⚠️ No chunks produced")
            self.stats["skipped"] += 1
            return 0
        
        print(f"    → {len(chunks)} chunks")
        
        # Build search documents
        docs = []
        doc_id_base = hashlib.md5(str(filepath).encode()).hexdigest()[:12]
        
        for i, chunk_text_val in enumerate(chunks):
            doc = {
                "@search.action": "upload",
                "id": f"{doc_id_base}_{i:05d}",
                "parent_id": str(filepath.relative_to(self.config.base_dir)),
                "content": chunk_text_val,
                "title": filename,
                "source_path": str(filepath),
                "chunk_index": i,
            }
            
            # Add corpus-specific fields
            if corpus == "haadthip-ir":
                doc["subject_area"] = classify_subject(chunk_text_val)
                # Try to extract year from filename
                year_match = re.search(r'(?:20|19)(\d{2})', filename)
                if year_match:
                    doc["report_year"] = int(year_match.group(0))
            
            docs.append(doc)
        
        # Generate embeddings in batches
        for batch_start in range(0, len(docs), self.config.batch_size):
            batch = docs[batch_start:batch_start + self.config.batch_size]
            try:
                texts = [d["content"] for d in batch]
                embeddings = self.embedder.embed_batch(texts)
                for d, emb in zip(batch, embeddings):
                    d["content_vector"] = emb
            except Exception as e:
                print(f"    ⚠️ Embedding error: {e}")
                self.stats["errors"] += 1
                return 0
        
        # Upload to search
        total_uploaded = 0
        for batch_start in range(0, len(docs), self.config.batch_size):
            batch = docs[batch_start:batch_start + self.config.batch_size]
            ok = indexer.upload_batch(batch)
            total_uploaded += ok
        
        self.stats["files"] += 1
        self.stats["chunks"] += total_uploaded
        print(f"    ✅ {total_uploaded} indexed")
        return total_uploaded
    
    def run_corpus(self, corpus: str, dry_run: bool = False):
        """Process all files in a corpus directory."""
        corpus_dir = self.config.base_dir / corpus
        if not corpus_dir.exists():
            print(f"  ❌ Directory not found: {corpus_dir}")
            return
        
        index_name = self.config.indexes.get(corpus)
        if not index_name:
            print(f"  ❌ No index mapping for corpus: {corpus}")
            return
        
        print(f"\n{'═'*60}")
        print(f"📦 Corpus: {corpus} → Index: {index_name}")
        print(f"{'═'*60}")
        
        indexer = SearchIndexer(self.config, index_name)
        pdfs = sorted(corpus_dir.rglob("*"))
        pdfs = [f for f in pdfs if f.is_file() and f.suffix.lower() in {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.ppt', '.pptx'
        }]
        
        print(f"  Files: {len(pdfs)}")
        
        if dry_run:
            print("  🧪 DRY RUN — no indexing\n")
            for f in pdfs:
                text = self.extractor.extract(f)
                chunks = chunk_text(text or "", self.config.chunk_size)
                print(f"  📄 {f.name}: {len(chunks)} chunks → would upload")
            return
        
        for f in pdfs:
            try:
                self.process_file(f, indexer, corpus)
            except Exception as e:
                print(f"    ❌ Error: {e}")
                self.stats["errors"] += 1
    
    def print_summary(self):
        print(f"\n{'═'*60}")
        print(f"📊 INGESTION SUMMARY")
        print(f"{'═'*60}")
        print(f"  Files processed: {self.stats['files']}")
        print(f"  Total chunks:    {self.stats['chunks']}")
        print(f"  Errors:          {self.stats['errors']}")
        print(f"  Skipped:         {self.stats['skipped']}")
        print(f"{'═'*60}")


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Unified Haadthip Document Ingestion")
    parser.add_argument("--corpus", choices=["all", "haadthip-ir", "haadthip-public", "sap-hip", "mihcm-hr"],
                        default="all", help="Which corpus to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview without indexing")
    parser.add_argument("--no-doc-intel", action="store_true", help="Skip Document Intelligence, use native parsers")
    args = parser.parse_args()
    
    config = Config()
    if args.no_doc_intel:
        config.use_doc_intel = False
    
    # Validate keys
    if not config.search_key:
        print("❌ Set AZURE_SEARCH_KEY or AZURE_SEARCH_ADMIN_KEY")
        sys.exit(1)
    if not config.openai_key:
        print("❌ Set AZURE_OPENAI_API_KEY")
        sys.exit(1)
    
    print("═" * 60)
    print("📦 UNIFIED HAADTHIP DOCUMENT INGESTION")
    print("═" * 60)
    print(f"   Search:    {config.search_endpoint}")
    print(f"   Embedding: {config.embedding_model} ({config.embedding_dimensions}d)")
    print(f"   Doc Intel: {'✅' if config.use_doc_intel else '❌'}")
    print(f"   Chunk:    {config.chunk_size} chars (+{config.chunk_overlap} overlap)")
    if args.dry_run:
        print(f"   Mode:     🧪 DRY RUN")
    
    engine = IngestionEngine(config)
    
    if args.corpus == "all":
        for corpus in ["haadthip-ir", "haadthip-public", "sap-hip", "mihcm-hr"]:
            engine.run_corpus(corpus, args.dry_run)
    else:
        engine.run_corpus(args.corpus, args.dry_run)
    
    engine.print_summary()


if __name__ == "__main__":
    main()
