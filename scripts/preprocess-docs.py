#!/usr/bin/env python3
"""
preprocess-docs.py — Extract → Chunk → Classify → Summarize → Embed → JSONL
================================================================================
Preprocessing step: processes all documents and saves results as JSONL files
(one file per document). The upload step is handled separately.

Output: data/ingestion/{corpus}/{relative_path}.jsonl

Features:
  - Document Intelligence prebuilt-layout extraction
  - GPT auto-classify category from content
  - GPT-5.4-nano summary generation (batched per document)
  - text-embedding-3-large (3072d) vectors
  - Incremental: skip files with matching hash in existing JSONL
  - Each JSONL line = 1 chunk with all fields

Usage:
  export AZURE_OPENAI_API_KEY="..."
  export AZURE_SEARCH_KEY="..."  # optional, for delta check

  python3 scripts/preprocess-docs.py --corpus corporate
  python3 scripts/preprocess-docs.py --corpus all --force
"""

import os, re, sys, hashlib, time, argparse, json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from collections import defaultdict

from openai import AzureOpenAI

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import DocumentContentFormat
    HAS_DOC_INTEL = True
except ImportError:
    HAS_DOC_INTEL = False


# ════════════════════════════════════
# CONFIG
# ════════════════════════════════════

class Config:
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT",
                                "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
    openai_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    embedding_deployment = "deploy-embedding-3-large"
    embedding_dimensions = 3072
    summary_deployment = "deploy-gpt-5.4-nano"

    docintel_endpoint = openai_endpoint
    docintel_key = openai_key

    base_dir = Path("documents")
    output_dir = Path("data/ingestion")
    chunk_size = 2000
    chunk_overlap = 200
    max_retries = 3

    corpus_paths = {
        "corporate":   "haadthip-corporate",
        "hr-policies": "haadthip-hr-policies",
    }
    supported_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx',
                            '.jpg', '.jpeg', '.png', '.ppt', '.pptx'}


CATEGORIES_BY_CORPUS = {
    "corporate": ["Security Manual", "Email Manual", "IT Policy",
        "Meeting Room Guide", "Public Disclosure", "Sustainability Report",
        "Corporate Governance"],
    "hr-policies": ["Policy", "Announcement / Order", "Form / Template",
        "Benefits & Welfare", "Training & Development",
        "Recruitment & Appointment", "Privacy / PDPA",
        "Social Security", "Safety & Environment",
        "Company Regulation", "Holiday / Leave", "Manual / Guide", "Newsletter"],
}

TH_PATTERN = re.compile(r'[ก-๙]')

# ════════════════════════════════════
# UTILITIES
# ════════════════════════════════════

def compute_file_hash(filepath: Path) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def detect_language(text: str) -> str:
    ratio = len(TH_PATTERN.findall(text)) / max(len(text.strip()), 1)
    if ratio > 0.5: return "th"
    if ratio > 0.1: return "mixed"
    return "en"

def chunk_text(text: str, max_size: int = 2000, overlap: int = 200) -> List[str]:
    if not text or not text.strip(): return []
    table_pat = re.compile(r'(?:\|[^\n]+\|\n\s*\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*)', re.MULTILINE)
    chunks, current = [], ""
    for para in text.split('\n\n'):
        para = para.strip()
        if not para: continue
        if table_pat.match(para):
            if current: chunks.append(current.strip()); current = ""
            chunks.append(para[:max_size*2]) if len(para) <= max_size*2 else None
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


# ════════════════════════════════════
# DOCUMENT EXTRACTOR
# ════════════════════════════════════

class Extractor:
    def __init__(self, cfg: Config, mode: str = "prebuilt-read"):
        self.cfg = cfg
        self.mode = mode  # "pypdf" | "prebuilt-read" | "prebuilt-layout"
        self.client = None
        if mode != "pypdf" and cfg.docintel_key and HAS_DOC_INTEL:
            try:
                self.client = DocumentIntelligenceClient(
                    endpoint=cfg.docintel_endpoint,
                    credential=AzureKeyCredential(cfg.docintel_key))
            except Exception: pass

    def extract(self, fp: Path) -> Optional[Tuple[str, int]]:
        ext = fp.suffix.lower()

        # pypdf mode: native only
        if self.mode == "pypdf":
            return self._native(fp)

        # Doc Intel modes
        if self.client and ext in self.cfg.supported_extensions:
            for attempt in range(self.cfg.max_retries):
                try:
                    with open(fp, "rb") as f:
                        model = "prebuilt-read" if self.mode == "prebuilt-read" else "prebuilt-layout"
                        kwargs = dict(
                            model_id=model,
                            body=f,
                            content_type="application/octet-stream",
                        )
                        if self.mode == "prebuilt-layout":
                            kwargs["output_content_format"] = DocumentContentFormat.MARKDOWN
                        poller = self.client.begin_analyze_document(**kwargs)
                        result = poller.result()
                        pages = len(result.pages) if result.pages else 0
                        content = result.content or ""
                        return (content, pages)
                except Exception as e:
                    if attempt < self.cfg.max_retries - 1:
                        time.sleep(2 ** attempt * 5)
                    else:
                        print(f" ⚠️DocIntel:{e}", end="")
                        return self._native(fp)
        return self._native(fp)

    def _native(self, fp: Path) -> Optional[Tuple[str, int]]:
        try:
            from pypdf import PdfReader
            if fp.suffix == '.pdf':
                r = PdfReader(fp)
                return ('\n\n'.join(p.extract_text() or '' for p in r.pages), len(r.pages))
            from docx import Document as D
            if fp.suffix == '.docx':
                d = D(fp)
                return ('\n\n'.join(p.text for p in d.paragraphs if p.text.strip()), 0)
            from openpyxl import load_workbook
            if fp.suffix == '.xlsx':
                wb = load_workbook(fp, read_only=True, data_only=True)
                parts = []
                for sn in wb.sheetnames:
                    rows = [' | '.join(str(c or '') for c in r) for r in wb[sn].iter_rows(values_only=True)]
                    parts.append(f"## {sn}\n" + '\n'.join(rows))
                return ('\n\n'.join(parts), 0)
            from pptx import Presentation
            if fp.suffix == '.pptx':
                p = Presentation(fp)
                parts = []
                for s in p.slides:
                    texts = [sh.text.strip() for sh in s.shapes if hasattr(sh,'text') and sh.text.strip()]
                    if texts: parts.append('\n'.join(texts))
                return ('\n\n'.join(parts), len(p.slides))
        except Exception: pass
        return (f"[{fp.name}]", 0) if fp.suffix in self.cfg.supported_extensions else None


# ════════════════════════════════════
# LLM (classify + summarize)
# ════════════════════════════════════

class LLM:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.cl = AzureOpenAI(api_key=cfg.openai_key,
                               azure_endpoint=cfg.openai_endpoint,
                               api_version="2024-10-21")

    def classify(self, text: str, corpus: str) -> str:
        cats = CATEGORIES_BY_CORPUS.get(corpus, ["General"])
        prompt = ("Classify this document into ONE category from the list. "
                  "Return ONLY the category name.\n" +
                  "\n".join(f"  - {c}" for c in cats) +
                  f"\n\nExcerpt:\n{text[:3000]}")
        try:
            r = self.cl.chat.completions.create(
                model=self.cfg.summary_deployment,
                messages=[{"role":"system","content":"Classify documents into categories. Return ONLY the category name."},
                          {"role":"user","content":prompt}],
                max_completion_tokens=30, temperature=0.0)
            result = r.choices[0].message.content.strip()
            for c in cats:
                if c.lower() in result.lower(): return c
            return result[:50]
        except Exception:
            return "General Document"

    def summarize(self, chunks: List[str]) -> List[str]:
        summaries = []
        bs = 15
        for i in range(0, len(chunks), bs):
            batch = chunks[i:i+bs]
            if len(chunks) > 20:
                print(f"  s{i}", end=" ", flush=True)
            try:
                summaries.extend(self._sum_batch(batch))
            except Exception:
                for t in batch:
                    try: summaries.append(self._sum_one(t))
                    except Exception: summaries.append("")
        if len(chunks) > 20:
            print("", flush=True)
        return summaries

    def _sum_batch(self, texts: List[str]) -> List[str]:
        blocks = "\n\n---\n\n".join(f"[{j}] {t[:1500]}" for j, t in enumerate(texts))
        prompt = ("For each numbered excerpt below, write a 1-sentence summary "
                  "in the same language. Return ONLY a JSON array of strings.\n\n" + blocks)
        r = self.cl.chat.completions.create(
            model=self.cfg.summary_deployment,
            messages=[{"role":"system","content":"Summarizer. Return ONLY a JSON array of strings."},
                      {"role":"user","content":prompt}],
            max_completion_tokens=400, temperature=0.2)
        result = r.choices[0].message.content.strip()
        try:
            m = re.search(r'\[.*\]', result, re.DOTALL)
            parsed = json.loads(m.group(0) if m else result)
            if isinstance(parsed, list):
                while len(parsed) < len(texts): parsed.append("")
                return [str(s) for s in parsed[:len(texts)]]
        except (json.JSONDecodeError, TypeError, AttributeError): pass
        lines = [l.strip() for l in result.split('\n') if l.strip() and l.strip() not in '[]']
        return lines[:len(texts)] if len(lines) >= len(texts) else [""]*len(texts)

    def _sum_one(self, text: str) -> str:
        r = self.cl.chat.completions.create(
            model=self.cfg.summary_deployment,
            messages=[{"role":"system","content":"Summarize in 1-2 sentences."},
                      {"role":"user","content":f"{text[:4000]}"}],
            max_completion_tokens=150, temperature=0.3)
        return r.choices[0].message.content.strip()

    def embed(self, texts: List[str]) -> List[List[float]]:
        for attempt in range(5):
            try:
                r = self.cl.embeddings.create(
                    input=texts, model=self.cfg.embedding_deployment,
                    dimensions=self.cfg.embedding_dimensions)
                return [e.embedding for e in r.data]
            except Exception as e:
                err_str = str(e)
                if '429' in err_str or 'RateLimit' in err_str or 'rate' in err_str.lower():
                    wait = min(2 ** attempt * 10, 120)
                    print(f"  ⏳ Rate limit, waiting {wait}s...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                if attempt < 3: time.sleep(2**attempt)
                else: raise


# ════════════════════════════════════
# PREPROCESSOR
# ════════════════════════════════════

class Preprocessor:
    def __init__(self, cfg: Config, extract_mode: str = "prebuilt-read"):
        self.cfg = cfg
        self.extractor = Extractor(cfg, mode=extract_mode)
        self.llm = LLM(cfg)
        self.stats = {"files": 0, "chunks": 0, "skipped": 0, "errors": 0}

    def process_corpus(self, corpus: str, force: bool = False):
        folder = self.cfg.corpus_paths.get(corpus)
        if not folder:
            print(f"  ❌ Unknown corpus: {corpus}")
            return
        corpus_dir = self.cfg.base_dir / folder
        if not corpus_dir.exists():
            print(f"  ❌ Not found: {corpus_dir}")
            return

        files = sorted([f for f in corpus_dir.rglob("*")
                        if f.is_file() and f.suffix.lower() in self.cfg.supported_extensions])
        if not files:
            print(f"  ℹ️ No supported files")
            return

        print(f"\n{'═'*60}\n📦 {corpus} ({len(files)} files)\n{'═'*60}")

        for idx, fp in enumerate(files):
            fhash = compute_file_hash(fp)
            rel = fp.relative_to(self.cfg.base_dir)
            out_path = self.cfg.output_dir / corpus / (str(rel).replace('/', '_') + '.jsonl')

            # Delta check
            if not force and out_path.exists():
                existing = self._read_existing_hash(out_path)
                if existing and existing == fhash:
                    self.stats["skipped"] += 1
                    print(f"  ⏭️  [{idx+1}/{len(files)}] {fp.name} (unchanged)")
                    continue

            print(f"  📄 [{idx+1}/{len(files)}] {fp.name} ({fp.suffix} "
                  f"{fp.stat().st_size/1024/1024:.1f}MB)", end="", flush=True)

            try:
                # 1. Extract
                r = self.extractor.extract(fp)
                if not r or not r[0].strip():
                    print(" ⚠️ no content")
                    continue
                text, pages = r
                print(f" {pages}p", end="", flush=True)

                # 2. Chunk
                chunks = chunk_text(text, self.cfg.chunk_size, self.cfg.chunk_overlap)
                if not chunks:
                    print(" ⚠️ no chunks")
                    continue
                print(f" →{len(chunks)}c", end="", flush=True)

                # 3. Classify
                cat = self.llm.classify(text[:3000], corpus)
                print(f" [{cat}]", end="", flush=True)

                # 4. Summarize
                summaries = self.llm.summarize(chunks)

                # 5. Embed
                embs = self.llm.embed([c for c in chunks])

                # 6. Build meta
                meta = json.dumps({
                    "file_hash": fhash,
                    "language": detect_language(text),
                    "pages": pages,
                    "file_size_bytes": fp.stat().st_size,
                    "file_modified": datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc).isoformat(),
                    "corpus": corpus,
                    "category": cat,
                    "source": "local",
                    "file_path": str(fp),
                }, ensure_ascii=False)

                # 7. Write JSONL
                doc_id = hashlib.md5((str(fp) + fhash).encode()).hexdigest()[:16]
                os.makedirs(out_path.parent, exist_ok=True)
                with open(out_path, 'w', encoding='utf-8') as f:
                    for i, (chunk_text_val, summary, emb) in enumerate(zip(chunks, summaries, embs)):
                        line = json.dumps({
                            "id": f"{doc_id}_{i:05d}",
                            "doc_id": doc_id,
                            "chunk_seq": i,
                            "file_name": fp.name,
                            "file_path": str(rel),
                            "corpus": corpus,
                            "category": cat,
                            "content": chunk_text_val,
                            "summary": summary,
                            "meta": meta,
                            "content_vector": emb,
                        }, ensure_ascii=False)
                        f.write(line + '\n')

                self.stats["files"] += 1
                self.stats["chunks"] += len(chunks)
                print(f" ✅")

            except Exception as e:
                print(f" ❌ {e}")
                self.stats["errors"] += 1

    def _read_existing_hash(self, jsonl_path: Path) -> Optional[str]:
        """Read file_hash from first line's meta."""
        try:
            with open(jsonl_path) as f:
                line = f.readline()
                doc = json.loads(line)
                meta = json.loads(doc.get('meta', '{}'))
                return meta.get('file_hash')
        except Exception:
            return None

    def print_summary(self):
        s = self.stats
        print(f"\n{'═'*60}\n📊 PREPROCESS SUMMARY\n{'═'*60}")
        print(f"  Files: {s['files']} | Chunks: {s['chunks']} | "
              f"Skipped: {s['skipped']} | Errors: {s['errors']}")
        print(f"{'═'*60}")


# ════════════════════════════════════
# MAIN
# ════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="Preprocess documents to JSONL")
    p.add_argument("--corpus", choices=["all","corporate","hr-policies"], default="all")
    p.add_argument("--extractor", choices=["pypdf","prebuilt-read","prebuilt-layout"],
                   default="prebuilt-read",
                   help="Extraction method (default: prebuilt-read)")
    p.add_argument("--force", action="store_true", help="Reprocess all files")
    args = p.parse_args()

    cfg = Config()
    if not cfg.openai_key:
        print("❌ Set AZURE_OPENAI_API_KEY"); sys.exit(1)

    print("═"*60)
    print("📦 DOCUMENT PREPROCESSING")
    print("═"*60)
    print(f"   Output:       {cfg.output_dir}")
    print(f"   Summary:      {cfg.summary_deployment}")
    print(f"   Embedding:    {cfg.embedding_deployment} ({cfg.embedding_dimensions}d)")
    print(f"   Doc Intel:    {'✅' if HAS_DOC_INTEL else '❌ native only'}")
    print(f"   Extractor:    {args.extractor}")
    if args.force: print(f"   Mode:         🔄 FORCE")

    pre = Preprocessor(cfg, extract_mode=args.extractor)
    selected = ["corporate","hr-policies"] if args.corpus == "all" else [args.corpus]
    for c in selected:
        pre.process_corpus(c, args.force)
    pre.print_summary()


if __name__ == "__main__":
    main()
