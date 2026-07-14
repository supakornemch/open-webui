#!/usr/bin/env python3
"""
ingest-haadthip-investor-relations-v2.py — IR Documents Ingestion with Document Intelligence
===========================================================================
Pipeline:
  1. Azure AI Document Intelligence (prebuilt-layout) → Markdown
     - Extracts text, tables (as markdown | tables |), headings, lists
     - Preserves document structure (H1-H6, bold, italic)
  2. Markdown-aware Chunking
     - Split on ##/### headings
     - Tables as atomic units (never split mid-table)
     - Max ~2000 chars, 100 char overlap
  3. Subject Classification (keyword heuristic)
     - Multi-label: one chunk can be [financial, business]
  4. Vector Embedding (Azure OpenAI text-embedding-3-large)
  5. Azure AI Search Index (haadthip-investor-relations-idx)

Subject Areas (6):
  financial | governance | business | esg | risk | company-profile

Usage:
  export AZURE_SEARCH_KEY=$(az search admin-key show ...)
  export DOCUMENTINTELLIGENCE_ENDPOINT="https://aif-entchat-poc-sand.cognitiveservices.azure.com"
  export DOCUMENTINTELLIGENCE_API_KEY="..."
  export AZURE_OPENAI_API_KEY="..."
  python3 scripts/ingest-haadthip-investor-relations-v2.py

Requirements:
  pip install azure-ai-documentintelligence azure-search-documents
             azure-identity openai tiktoken
"""

import os, re, json, hashlib, time, io
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Tuple

# === Azure AI Document Intelligence ===
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeContentFormat, ContentFormat

# === Azure AI Search ===
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticPrioritizedFields, SemanticField,
    AzureOpenAIVectorizer, AzureOpenAIVectorizerParameters,
)

# === Azure OpenAI ===
from openai import AzureOpenAI


# ═══════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════

class Config:
    # === AI Search ===
    search_endpoint: str = os.getenv("AZURE_SEARCH_ENDPOINT",
        "https://srch-entchat-poc-sand.search.windows.net")
    search_key: str = os.getenv("AZURE_SEARCH_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
    index_name: str = "haadthip-investor-relations-idx"
    
    # === Document Intelligence ===
    docintel_endpoint: str = os.getenv("DOCUMENTINTELLIGENCE_ENDPOINT",
        "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
    docintel_key: str = os.getenv("DOCUMENTINTELLIGENCE_API_KEY", "")
    docintel_model: str = "prebuilt-layout"  # Layout model for markdown output
    
    # === Azure OpenAI (Embeddings) ===
    openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT",
        "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
    openai_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    embedding_deployment: str = "text-embedding-3-large"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072
    
    # === Ingestion ===
    docs_dir: Path = Path("documents/haadthip-investor-relations")
    max_chunk_size: int = 2000
    chunk_overlap: int = 100
    batch_size: int = 50
    max_retries: int = 3
    
    # File size limits for Doc Intelligence
    max_file_size_mb: int = 200  # Doc Intelligence limit
    
    # === Dry Run ===
    dry_run: bool = False  # Set True to skip actual indexing


# ═══════════════════════════════════════════════
# SUBJECT CLASSIFICATION
# ═══════════════════════════════════════════════

SUBJECT_PATTERNS: Dict[str, List[str]] = {
    "financial": [
        "revenue", "profit", "EBITDA", "income", "financial statement",
        "balance sheet", "cash flow", "net profit", "gross profit",
        "operating profit", "earnings", "dividend", "cost of sales",
        "SG&A", "financial ratio", "liquidity", "profitability",
        "return on", "income tax", "asset", "liabilit", "equity",
        "รายได้", "กำไร", "งบการเงิน", "สินทรัพย์", "หนี้สิน",
        "ส่วนของผู้ถือหุ้น", "กระแสเงินสด", "กำไรขั้นต้น", "กำไรสุทธิ",
        "เงินปันผล", "ต้นทุนขาย", "ค่าใช้จ่าย", "อัตราส่วนทางการเงิน",
    ],
    "governance": [
        "board of directors", "AGM", "annual general meeting",
        "shareholder", "corporate governance", "audit committee",
        "remuneration", "nomination committee", "independent director",
        "company secretary", "investor relations", "dividend policy",
        "related party transaction", "conflict of interest",
        "corporate secretary", "executive committee",
        "กรรมการ", "ผู้ถือหุ้น", "คณะกรรมการ", "การกำกับดูแลกิจการ",
        "ประชุมผู้ถือหุ้น", "กรรมการอิสระ", "กรรมการตรวจสอบ",
        "ค่าตอบแทน", "การควบคุมภายใน", "รายการระหว่างกัน",
        "เลขานุการบริษัท", "นักลงทุนสัมพันธ์", "นโยบายเงินปันผล",
    ],
    "business": [
        "carbonate", "non-carbonate", "market share", "product",
        "distribution", "sale volume", "cooler", "NARTD", "brand",
        "customer", "manufacturing", "supply chain", "beverage",
        "sparkling", "ready-to-drink", "packaging", "promotion",
        "trade marketing", "portfolio", "product mix",
        "ยอดขาย", "ส่วนแบ่งการตลาด", "สินค้า", "จำหน่าย",
        "คูลเลอร์", "ตู้เย็น", "ตราสินค้า", "ลูกค้า", "การผลิต",
        "ห่วงโซ่อุปทาน", "เครื่องดื่ม", "บรรจุภัณฑ์", "ส่งเสริมการขาย",
        "ปริมาณขาย", "ตลาด", "ช่องทางจำหน่าย", "ภาคใต้",
    ],
    "esg": [
        "ESG", "environment", "social", "sustainability",
        "carbon", "greenhouse gas", "climate change", "emission",
        "water", "waste", "recycle", "community", "society",
        "occupational health", "safety", "human rights", "labor",
        "stakeholder", "CSR", "energy", "renewable", "biodiversity",
        "สิ่งแวดล้อม", "ความยั่งยืน", "ชุมชน", "สังคม",
        "ก๊าซเรือนกระจก", "การเปลี่ยนแปลงสภาพภูมิอากาศ",
        "ของเสีย", "รีไซเคิล", "ความปลอดภัย", "อาชีวอนามัย",
        "สิทธิมนุษยชน", "แรงงาน", "ผู้มีส่วนได้เสีย",
    ],
    "risk": [
        "risk", "risk management", "mitigation", "uncertainty",
        "risk factor", "business risk", "financial risk",
        "market risk", "operational risk", "compliance risk",
        "strategic risk", "risk oversight", "risk appetite",
        "risk assessment", "internal control", "crisis",
        "ความเสี่ยง", "การบริหารความเสี่ยง", "ปัจจัยความเสี่ยง",
        "ความไม่แน่นอน", "การควบคุม", "ภัยคุกคาม",
    ],
    "company-profile": [
        "company overview", "vision", "mission", "history",
        "core value", "business overview", "company structure",
        "organization", "nature of business", "principal business",
        "corporate structure", "shareholding structure",
        "major shareholder", "group structure",
        "วิสัยทัศน์", "พันธกิจ", "ประวัติบริษัท", "ภาพรวมบริษัท",
        "โครงสร้างองค์กร", "ลักษณะธุรกิจ", "โครงสร้างผู้ถือหุ้น",
        "ผู้ถือหุ้นรายใหญ่",
    ],
}


def classify_subject_area(text: str) -> List[str]:
    """
    Classify text chunk into subject areas using keyword matching.
    
    Returns list of matched subjects. Multi-label: a chunk can belong
    to multiple subjects (e.g., financial + business).
    
    If no match, returns ["company-profile"] as fallback.
    """
    text_lower = text.lower()
    matched = []
    
    for subject, patterns in SUBJECT_PATTERNS.items():
        score = sum(1 for p in patterns if p.lower() in text_lower)
        if score >= 2:
            matched.append(subject)
        elif score == 1 and subject in ("company-profile",):
            # company-profile keywords are specific enough for single match
            matched.append(subject)
    
    # Fallback: if nothing matched, tag as company-profile
    if not matched:
        matched.append("company-profile")
    
    return matched


# ═══════════════════════════════════════════════
# DOCUMENT TYPE DETECTION
# ═══════════════════════════════════════════════

def detect_doc_type(filepath: Path) -> str:
    """Detect document type from file path."""
    path_str = filepath.as_posix()
    if "01-annual-reports" in path_str:
        if "form561" in filepath.stem.lower():
            return "form-56-1"
        return "annual-report"
    elif "02-financial-data" in path_str:
        return "financial-data"
    elif "03-company-disclosures" in path_str:
        return "company-disclosure"
    return "other"


def extract_report_year(filename: str) -> Optional[int]:
    """Extract report year from filename."""
    patterns = [
        r'(?:one[-_]?)?report(\d{4})',
        r'ar(\d{4})',
        r'form[_-]?561[_-](\d{4})',
        r'(\d{4})[_-]?(?:results|factsheet|f45|mda)',
        r'q[12][_-]?(\d{4})',
        r'factsheet[_-]?(\d{1,2})m(\d{4})',
    ]
    for pat in patterns:
        m = re.search(pat, filename, re.IGNORECASE)
        if m:
            if m.lastindex == 2 and m.group(2):  # factsheet pattern
                return int(m.group(2))
            return int(m.group(1))
    return None


def extract_language(text: str) -> str:
    """Detect if text is Thai or English."""
    thai_chars = sum(1 for c in text[:1000] if '\u0e00' <= c <= '\u0e7f')
    return "th" if thai_chars > 20 else "en"


def sanitize_id(raw: str) -> str:
    """Create a valid document ID for AI Search."""
    safe = re.sub(r'[^a-zA-Z0-9_=-]', '_', raw)
    return safe[:120]


# ═══════════════════════════════════════════════
# MARKDOWN-AWARE CHUNKING
# ═══════════════════════════════════════════════

def chunk_markdown(md_content: str, max_size: int = 2000, overlap: int = 100) -> List[str]:
    """
    Chunk markdown content preserving structure:
    - Split primarily on ##/###/#### headings
    - Tables (markdown pipe tables) are kept as atomic units
    - If a section exceeds max_size, split by double newlines
    - Overlap: attach last `overlap` chars of previous chunk
    
    Returns list of chunk strings (markdown text).
    """
    if not md_content or not md_content.strip():
        return []
    
    # Step 1: Split into sections by markdown headings (##, ###, ####)
    # but NOT # (H1) as that's usually the document title
    section_pattern = re.compile(r'(?=\n(?=##(?!#)))', re.MULTILINE)
    sections = section_pattern.split(md_content)
    
    # Step 2: Detect tables within each section and keep them atomic
    # Markdown tables look like: | col1 | col2 |\n| --- | --- |\n| val1 | val2 |
    table_pattern = re.compile(
        r'(?:\|[^\n]+\|\n\s*\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*)',
        re.MULTILINE
    )
    
    chunks = []
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Check if section contains tables → extract and keep whole
        tables = table_pattern.findall(section)
        
        if tables:
            # Remove tables from text, then chunk text parts
            text_part = table_pattern.sub('', section).strip()
            
            # Split text around tables
            for table in tables:
                stripped_text = text_part.strip()
                if len(stripped_text) > 0:
                    if len(stripped_text) <= max_size:
                        chunks.append(stripped_text)
                    else:
                        # Split long text sections by paragraphs
                        for para in split_long_text(stripped_text, max_size, overlap):
                            chunks.append(para)
                    text_part = ""
                
                # Add table as its own chunk (preserving structure)
                table_md = table.strip()
                if len(table_md) > 0:
                    chunks.append(table_md)
            
            # Remaining text after last table
            if text_part.strip():
                if len(text_part) <= max_size:
                    chunks.append(text_part.strip())
                else:
                    for para in split_long_text(text_part.strip(), max_size, overlap):
                        chunks.append(para)
        else:
            # No tables, just text
            if len(section) <= max_size:
                chunks.append(section)
            else:
                for para in split_long_text(section, max_size, overlap):
                    chunks.append(para)
    
    # Clean up and remove empty chunks
    return [c for c in chunks if c.strip() and len(c.strip()) > 10]


def split_long_text(text: str, max_size: int, overlap: int) -> List[str]:
    """Split long text by paragraphs, respecting max_size."""
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current) + len(para) + 2 <= max_size:
            if current:
                current += '\n\n' + para
            else:
                current = para
        else:
            if current:
                chunks.append(current)
                # Add overlap from end of previous chunk
                if overlap > 0 and len(current) > overlap:
                    current = current[-overlap:] + '\n\n' + para
                else:
                    current = para
            else:
                # Single paragraph exceeds max → split by sentences
                current = para
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks


# ═══════════════════════════════════════════════
# DOCUMENT INTELLIGENCE CLIENT
# ═══════════════════════════════════════════════

class DocIntelligenceProcessor:
    """Process PDFs using Azure AI Document Intelligence Layout model."""
    
    def __init__(self, config: Config):
        self.config = config
        
        if not config.docintel_key:
            config.docintel_key = os.environ.get("AZURE_AI_SERVICES_KEY", "")
        
        if not config.docintel_key:
            raise ValueError("Missing DOCUMENTINTELLIGENCE_API_KEY")
        
        self.client = DocumentIntelligenceClient(
            endpoint=config.docintel_endpoint,
            credential=AzureKeyCredential(config.docintel_key),
        )
    
    def analyze_pdf(self, filepath: Path) -> Optional[str]:
        """
        Analyze PDF with Document Intelligence Layout model.
        Returns markdown content.
        """
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.max_file_size_mb:
            raise ValueError(f"File too large: {file_size_mb:.1f} MB > {self.config.max_file_size_mb} MB")
        
        # If file is very small (<50KB), it might be a simple disclosure
        # that can be read directly without DI
        if file_size_mb < 0.05:
            return self._read_simple_pdf(filepath)
        
        print(f"  🔍 Doc Intelligence analyzing...")
        
        for attempt in range(self.config.max_retries):
            try:
                with open(filepath, "rb") as f:
                    poller = self.client.begin_analyze_document(
                        model_id="prebuilt-layout",
                        analyze_request=f,
                        output_content_format=ContentFormat.MARKDOWN,
                        content_type="application/octet-stream",
                    )
                    result = poller.result()
                    return result.content
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait = 2 ** attempt * 5
                    print(f"    ⚠️ Doc Intel retry {attempt+1}/{self.config.max_retries} in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise
    
    def _read_simple_pdf(self, filepath: Path) -> Optional[str]:
        """Read simple PDFs with pypdf (faster than DI for small files)."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(filepath)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return '\n\n'.join(text_parts)
        except Exception as e:
            print(f"    ⚠️ pypdf fallback failed: {e}, using DI instead")
            # Fall back to DI
            with open(filepath, "rb") as f:
                poller = self.client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    analyze_request=f,
                    output_content_format=ContentFormat.MARKDOWN,
                    content_type="application/octet-stream",
                )
                result = poller.result()
                return result.content


# ═══════════════════════════════════════════════
# INGESTION ENGINE
# ═══════════════════════════════════════════════

class IngestionEngine:
    def __init__(self, config: Config):
        self.config = config
        
        # === Validate credentials ===
        if not config.search_key:
            raise ValueError("Missing AZURE_SEARCH_KEY")
        if not config.docintel_key:
            raise ValueError("Missing DOCUMENTINTELLIGENCE_API_KEY")
        if not config.openai_key:
            raise ValueError("Missing AZURE_OPENAI_API_KEY")
        
        # === Clients ===
        self.doc_processor = DocIntelligenceProcessor(config)
        
        self.search_client = SearchClient(
            endpoint=config.search_endpoint,
            index_name=config.index_name,
            credential=AzureKeyCredential(config.search_key),
        )
        
        self.openai_client = AzureOpenAI(
            api_key=config.openai_key,
            azure_endpoint=config.openai_endpoint,
            api_version="2024-10-21",
        )
        
        # === Stats ===
        self.stats = {
            "total_files": 0, "processed": 0, "skipped": 0, "errors": 0,
            "total_chunks": 0, "total_tables": 0,
            "subject_counts": {}, "doc_type_counts": {},
        }
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch for multiple texts."""
        for attempt in range(self.config.max_retries):
            try:
                resp = self.openai_client.embeddings.create(
                    input=texts,
                    model=self.config.embedding_deployment,
                    dimensions=self.config.embedding_dimensions,
                )
                return [e.embedding for e in resp.data]
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait = 2 ** attempt
                    print(f"    ⚠️ Embedding retry in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate single embedding."""
        return self.get_embeddings([text])[0]
    
    def index_batch(self, documents: List[dict]) -> Tuple[int, int]:
        """Upload batch to AI Search."""
        for attempt in range(self.config.max_retries):
            try:
                result = self.search_client.upload_documents(documents)
                success = sum(1 for r in result if r.succeeded)
                errors = sum(1 for r in result if not r.succeeded)
                if errors > 0:
                    error_detail = next((r.error_message for r in result if not r.succeeded), "unknown")
                    print(f"      ⚠️ {errors}/{len(result)} failed: {error_detail[:100]}")
                return success, errors
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
    
    def process_file(self, filepath: Path) -> int:
        """
        Process one file through the full pipeline:
        DI → Markdown → Chunk → Classify → Embed → Index
        """
        filename = filepath.name
        size_mb = filepath.stat().st_size / (1024 * 1024)
        
        doc_type = detect_doc_type(filepath)
        report_year = extract_report_year(filepath.stem)
        
        self.stats["doc_type_counts"][doc_type] = \
            self.stats["doc_type_counts"].get(doc_type, 0) + 1
        
        print(f"\n📄 {filename} ({size_mb:.1f} MB)")
        print(f"   Type: {doc_type}" + (f" | Year: {report_year}" if report_year else ""))
        
        # Step 1: Document Intelligence → Markdown
        try:
            md_content = self.doc_processor.analyze_pdf(filepath)
        except Exception as e:
            print(f"  ❌ Doc Intelligence error: {e}")
            self.stats["errors"] += 1
            return 0
        
        if not md_content:
            print(f"  ⚠️ No content extracted")
            self.stats["skipped"] += 1
            return 0
        
        print(f"  → Extracted {len(md_content):,} chars markdown")
        
        # Step 2: Markdown-aware Chunking
        chunks = chunk_markdown(
            md_content,
            max_size=self.config.max_chunk_size,
            overlap=self.config.chunk_overlap,
        )
        
        # Count tables in chunks
        table_chunks = sum(1 for c in chunks if c.strip().startswith('|'))
        self.stats["total_tables"] += table_chunks
        
        print(f"  → {len(chunks)} chunks ({table_chunks} table chunks)")
        
        if not chunks:
            self.stats["skipped"] += 1
            return 0
        
        # Step 3-4: Classify each chunk + Build search documents
        search_docs = []
        for i, chunk_text in enumerate(chunks):
            subject_areas = classify_subject_area(chunk_text)
            language = extract_language(chunk_text)
            
            # Determine if this is a table chunk
            is_table = chunk_text.strip().startswith('|')
            
            chunk_id = sanitize_id(f"{filepath.stem}_c{i}")
            
            doc = {
                "chunk_id": chunk_id,
                "parent_id": sanitize_id(filepath.stem),
                "content": chunk_text,
                "title": filename,
                "doc_type": doc_type,
                "subject_area": subject_areas,
                "report_year": report_year,
                "source_path": filepath.as_posix(),
                "chunk_index": i,
                "is_table": is_table,
                "language": language,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            
            for sa in subject_areas:
                self.stats["subject_counts"][sa] = \
                    self.stats["subject_counts"].get(sa, 0) + 1
            
            search_docs.append(doc)
        
        # Step 5: Generate embeddings (batch)
        try:
            texts = [d["content"] for d in search_docs]
            all_embeddings = self.get_embeddings(texts)
            for doc, emb in zip(search_docs, all_embeddings):
                doc["content_vector"] = emb
        except Exception as e:
            if len(search_docs) <= 3:
                # Fallback: embed individually
                print(f"  ⚠️ Batch embedding failed, trying one-by-one: {e}")
                for doc in search_docs:
                    doc["content_vector"] = self.get_embedding(doc["content"])
            else:
                raise
        
        # Step 6: Upload to AI Search
        if self.config.dry_run:
            print(f"  🧪 DRY RUN — would index {len(search_docs)} docs")
            return len(search_docs)
        
        total_uploaded = 0
        for batch_start in range(0, len(search_docs), self.config.batch_size):
            batch = search_docs[batch_start:batch_start + self.config.batch_size]
            success, errors = self.index_batch(batch)
            total_uploaded += success
        
        self.stats["processed"] += 1
        self.stats["total_chunks"] += total_uploaded
        
        print(f"  ✅ {total_uploaded} chunks indexed")
        return total_uploaded
    
    def run(self):
        """Main ingestion loop."""
        docs_dir = self.config.docs_dir
        
        if not docs_dir.exists():
            print(f"❌ Directory not found: {docs_dir}")
            return
        
        pdfs = sorted(docs_dir.rglob("*.pdf"))
        self.stats["total_files"] = len(pdfs)
        
        print("═" * 60)
        print("📦 HAADTHIP IR DOCUMENTS INGESTION")
        print("═" * 60)
        print(f"   Pipeline:  Doc Intelligence → Markdown → Chunk → Classify → Embed → Index")
        print(f"   Index:     {self.config.index_name}")
        print(f"   Total:     {len(pdfs)} PDFs")
        print(f"   Chunk:     max {self.config.max_chunk_size} chars")
        print(f"   Vector:    {self.config.embedding_dimensions} dims")
        if self.config.dry_run:
            print(f"   Mode:      🧪 DRY RUN")
        print("═" * 60)
        
        for i, pdf_path in enumerate(pdfs, 1):
            try:
                self.process_file(pdf_path)
            except Exception as e:
                print(f"  ❌ Fatal error: {e}")
                self.stats["errors"] += 1
        
        self.print_summary()
    
    def print_summary(self):
        print()
        print("═" * 60)
        print("📊 INGESTION SUMMARY")
        print("═" * 60)
        print(f"   Files:          {self.stats['total_files']}")
        print(f"   Processed:     {self.stats['processed']}")
        print(f"   Skipped:       {self.stats['skipped']}")
        print(f"   Errors:        {self.stats['errors']}")
        print(f"   Total chunks:   {self.stats['total_chunks']}")
        print(f"   Table chunks:  {self.stats['total_tables']}")
        print()
        print("   Subject breakdown:")
        for subject, count in sorted(self.stats["subject_counts"].items(), key=lambda x: -x[1]):
            bar = '█' * min(count // 10, 50)
            print(f"     • {subject:20s}: {count:5d} {bar}")
        print()
        print("   Doc type breakdown:")
        for dt, count in sorted(self.stats["doc_type_counts"].items()):
            print(f"     • {dt:20s}: {count:3d} files")
        print()
        print(f"   ✅ Done! Index: {self.config.index_name}")


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    config = Config()
    engine = IngestionEngine(config)
    engine.run()
