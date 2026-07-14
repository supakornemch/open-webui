#!/usr/bin/env python3
"""
ingest-to-search-sandbox.py — Push documents to AI Search index
Reads PDFs/DOCXs from local documents/ folder and pushes to the index.
Usage: python3 scripts/ingest-to-search-sandbox.py
"""

import os, re, hashlib, json, sys
from pathlib import Path
from io import BytesIO
import requests

# === CONFIG ===
SEARCH_ENDPOINT = "https://srch-entchat-poc-sand.search.windows.net"
SEARCH_KEY = "VeJOFJHJtmGvRp15ZQrk9mXCmI1JHpfyXTBNyuAiEUAzSeCmkPxY"
INDEX_NAME = "haadthip-public-idx-v2"
API_VERSION = "2024-07-01"

DOCS_DIR = Path(__file__).parent.parent / "documents" / "haadthip-public"

CATEGORY_MAP = {
    "01-security": "security",
    "02-email": "email",
    "03-meeting-room": "meeting_room",
    "04-it-policy": "it_policy",
    "05-public-disclosure": "public_disclosure",
}

def extract_text_from_pdf(filepath: Path) -> str:
    """Extract text from a PDF using PyMuPDF (fitz) or pypdf"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(filepath))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
        return "\n\n".join(pages)
    except ImportError:
        print("  ⚠️  pypdf not installed, trying fallback...")
        # Try pdftotext command-line tool
        import subprocess
        result = subprocess.run(["pdftotext", str(filepath), "-"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        return f"[PDF - text extraction failed: {filepath.name}]"

def extract_text_from_docx(filepath: Path) -> str:
    """Extract text from a DOCX file"""
    try:
        from docx import Document
        doc = Document(str(filepath))
        return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except ImportError:
        print("  ⚠️  python-docx not installed")
        return f"[DOCX - text extraction failed: {filepath.name}]"

def sanitize_id(raw: str) -> str:
    """Create a valid document ID"""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', raw)[:100]

def chunk_text(text, max_chars=4000, overlap=400):
    """Simple chunking by paragraph boundaries"""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks, current = [], ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                # Split long paragraph by sentences
                for i in range(0, len(para), max_chars - overlap):
                    chunks.append(para[i:i + max_chars])
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks

def upload_documents(docs: list):
    """Upload documents to search index"""
    url = f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/index?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "api-key": SEARCH_KEY
    }
    
    # Split into batches of 100
    for i in range(0, len(docs), 100):
        batch = docs[i:i+100]
        payload = {"value": batch}
        
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            results = resp.json().get("value", [])
            ok = sum(1 for r in results if r.get("status") in (True, "success"))
            print(f"   📤 Batch {i//100+1}: {ok}/{len(batch)} indexed")
        else:
            print(f"   ❌ Batch failed: {resp.status_code} {resp.text[:200]}")

def main():
    print("=" * 60)
    print(f" Ingest to AI Search: {INDEX_NAME}")
    print("=" * 60)
    
    # Delete all existing docs first (reset)
    print("\n=== Resetting index (deleting all docs) ===")
    # Get existing doc IDs
    search_url = f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs?api-version={API_VERSION}&search=*&$select=id&$top=1000"
    headers = {"api-key": SEARCH_KEY}
    resp = requests.get(search_url, headers=headers)
    if resp.status_code == 200:
        existing = resp.json().get("value", [])
        if existing:
            deletes = [{"@search.action": "delete", "id": doc["id"]} for doc in existing]
            del_resp = requests.post(
                f"{SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/index?api-version={API_VERSION}",
                json={"value": deletes}, headers=headers
            )
            if del_resp.status_code == 200:
                print(f"   🗑️  Deleted {len(existing)} existing docs")
    
    # Process each category
    total_chunks = 0
    all_docs = []
    
    for category_dir, category_name in CATEGORY_MAP.items():
        pdf_dir = DOCS_DIR / category_dir
        if not pdf_dir.exists():
            print(f"\n⚠️  Directory not found: {pdf_dir}")
            continue
        
        for filepath in sorted(pdf_dir.iterdir()):
            if filepath.suffix.lower() not in (".pdf", ".docx", ".pptx"):
                continue
            
            print(f"\n📄 {filepath.name}")
            print(f"   Category: {category_name}")
            
            try:
                # Extract text
                if filepath.suffix.lower() == ".pdf":
                    text = extract_text_from_pdf(filepath)
                elif filepath.suffix.lower() == ".docx":
                    text = extract_text_from_docx(filepath)
                else:
                    text = f"[{filepath.suffix} - unsupported format]"
                
                if not text or len(text.strip()) < 50:
                    print(f"   ⚠️  Too little text extracted ({len(text or '')} chars)")
                    # still index with metadata only
                
                # Get file size and last modified
                stat = filepath.stat()
                file_size = stat.st_size
                
                # Use file path within container as a pseudo-path
                relative_path = f"haadthip-public/{category_dir}/{filepath.name}"
                
                # Create parent document
                parent_id = sanitize_id(f"parent_{filepath.stem}")
                
                # Push the whole document as a single doc
                doc = {
                    "id": parent_id,
                    "content": text[:300000] if text else "",  # 300K chars max per doc
                    "metadata_storage_name": filepath.name,
                    "metadata_storage_path": relative_path,
                    "metadata_storage_content_type": f"application/{filepath.suffix[1:]}",
                    "metadata_storage_size": file_size,
                    "metadata_storage_last_modified": "2026-07-05T00:00:00Z",
                    "category": category_name,
                    "@search.action": "mergeOrUpload"
                }
                all_docs.append(doc)
                total_chunks += 1
                
                if len(all_docs) >= 100:
                    upload_documents(all_docs)
                    all_docs = []
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    # Upload remaining
    if all_docs:
        upload_documents(all_docs)
    
    print(f"\n{'=' * 60}")
    print(f" ✅ Complete! {total_chunks} documents indexed")
    print(f" Index: {INDEX_NAME}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
