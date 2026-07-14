#!/usr/bin/env python3
"""
ingest-openwebui-docs.py — Fetch Open WebUI docs → chunk → summarize → embed → JSONL
=====================================================================================
Scrapes Open WebUI documentation pages and ingests into enterprise-docs-idx
as corpus="openwebui-docs". Uses the same pipeline as preprocess-docs.py.

Sources:
  - https://docs.openwebui.com/reference/api-endpoints
  - https://docs.openwebui.com/features/
  - Plus any additional --url arguments

Usage:
  export AZURE_OPENAI_API_KEY="..."
  export AZURE_SEARCH_KEY="..."  # optional, for direct upload

  # Fetch + preprocess (saves JSONL)
  python3 scripts/ingest-openwebui-docs.py

  # Fetch + preprocess + upload directly
  python3 scripts/ingest-openwebui-docs.py --upload

  # Add extra URL
  python3 scripts/ingest-openwebui-docs.py --url https://docs.openwebui.com/pipelines/
"""

import os, re, sys, hashlib, time, argparse, json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from urllib.parse import urlparse

import requests
from openai import AzureOpenAI


# ════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT",
                     "https://aif-entchat-poc-sand.cognitiveservices.azure.com")
KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBED_DEPLOY = "deploy-embedding-3-large"
SUMMARY_DEPLOY = "deploy-gpt-5.4-nano"
DIMENSIONS = 3072
OUTPUT_DIR = Path("data/ingestion/openwebui-docs")
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 150

DEFAULT_URLS = [
    "https://docs.openwebui.com/reference/api-endpoints",
    "https://docs.openwebui.com/features/",
]

CATEGORIES = [
    "API Reference", "Chat & Conversations", "Knowledge & RAG",
    "Models & Agents", "Notes", "Channels", "Open Terminal",
    "Extensibility", "Authentication & Access", "Administration",
    "Deployment", "Getting Started",
]

CATEGORY_PROMPT = (
    "Classify this Open WebUI documentation excerpt into ONE category. "
    "Return ONLY the category name.\n" +
    "\n".join(f"  - {c}" for c in CATEGORIES) +
    f"\n\nExcerpt:\n{{text}}"
)

SUMMARY_PROMPT = (
    "For each numbered excerpt of Open WebUI documentation below, "
    "write a 1-sentence summary in English. Return ONLY a JSON array of strings.\n\n"
)


# ════════════════════════════════════════
# WEB SCRAPER
# ════════════════════════════════════════

def fetch_page(url: str) -> Tuple[str, str]:
    """
    Fetch a URL and extract readable text content.
    Returns (title, text_content).
    """
    try:
        r = requests.get(url, headers={
            "User-Agent": "EnterpriseChat-DocIngest/1.0"
        }, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return ("", f"[Error fetching {url}: {e}]")

    html = r.text
    title = ""

    # Extract title
    m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if m:
        title = m.group(1).strip()

    # Remove scripts, styles, nav, footer
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Extract main content area
    main = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
    if main:
        html = main.group(1)
    else:
        article = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        if article:
            html = article.group(1)

    # Convert to text
    # Replace block elements with newlines
    for tag in ['</div>', '</p>', '</h1>', '</h2>', '</h3>', '</h4>', '</h5>',
                '</h6>', '</li>', '</tr>', '</section>', '</article>']:
        html = html.replace(tag, tag + '\n')
    html = html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')

    # Strip all remaining tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Decode HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&apos;', "'")
    text = re.sub(r'&#x?[0-9a-fA-F]+;', ' ', text)

    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()

    # Remove common noise lines
    lines = [l.strip() for l in text.split('\n')]
    lines = [l for l in lines if l and not l.startswith('Skip to') and l != 'Menu'
             and l != 'Search' and not l.startswith('Copyright')]
    text = '\n\n'.join(lines)

    return (title, text)


# ════════════════════════════════════════
# CHUNKING
# ════════════════════════════════════════

def chunk_text(text: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into paragraphs, then sentences, preserving code blocks."""
    # Preserve code blocks
    code_pattern = re.compile(r'```[\s\S]*?```')
    code_blocks = code_pattern.findall(text)
    placeholder = "CODEBLOCK_PLACEHOLDER_{}"
    for i, cb in enumerate(code_blocks):
        text = text.replace(cb, placeholder.format(i), 1)

    chunks = []
    for para in text.split('\n\n'):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_size:
            # Reinsert code blocks
            for i, cb in enumerate(code_blocks):
                para = para.replace(placeholder.format(i), cb)
            chunks.append(para)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 <= max_size:
                    current = current + ' ' + sent if current else sent
                else:
                    if current:
                        for i, cb in enumerate(code_blocks):
                            current = current.replace(placeholder.format(i), cb)
                        chunks.append(current.strip())
                    current = sent
            if current:
                for i, cb in enumerate(code_blocks):
                    current = current.replace(placeholder.format(i), cb)
                chunks.append(current.strip())

    return [c for c in chunks if len(c.strip()) > 30]


# ════════════════════════════════════════
# LLM
# ════════════════════════════════════════

class LLM:
    def __init__(self):
        self.cl = AzureOpenAI(api_key=KEY, azure_endpoint=ENDPOINT,
                               api_version="2024-10-21")

    def classify(self, text: str) -> str:
        prompt = CATEGORY_PROMPT.replace("{text}", text[:3000])
        try:
            r = self.cl.chat.completions.create(
                model=SUMMARY_DEPLOY,
                messages=[{"role":"system","content":"Classify into 1 category. Return ONLY the name."},
                          {"role":"user","content":prompt}],
                max_completion_tokens=30, temperature=0.0)
            result = r.choices[0].message.content.strip()
            for c in CATEGORIES:
                if c.lower() in result.lower():
                    return c
            return result[:50]
        except Exception:
            return "API Reference"

    def summarize(self, chunks: List[str]) -> List[str]:
        summaries = []
        for i in range(0, len(chunks), 10):
            batch = chunks[i:i+10]
            blocks = "\n\n---\n\n".join(f"[{j}] {t[:2000]}" for j, t in enumerate(batch))
            prompt = SUMMARY_PROMPT + blocks

            try:
                r = self.cl.chat.completions.create(
                    model=SUMMARY_DEPLOY,
                    messages=[{"role":"system","content":"Summarize docs. Return JSON array of strings."},
                              {"role":"user","content":prompt}],
                    max_completion_tokens=500, temperature=0.2)
                result = r.choices[0].message.content.strip()

                try:
                    m = re.search(r'\[.*\]', result, re.DOTALL)
                    parsed = json.loads(m.group(0) if m else result)
                    if isinstance(parsed, list):
                        while len(parsed) < len(batch): parsed.append("")
                        summaries.extend(str(s) for s in parsed[:len(batch)])
                        continue
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass

                # Fallback: one summary for all
                summaries.append(result)
                while len(summaries) < i + len(batch):
                    summaries.append("")
            except Exception as e:
                print(f"    ⚠️ Summary err: {e}")
                for _ in batch:
                    summaries.append("")
        return summaries

    def embed(self, texts: List[str]) -> List[List[float]]:
        for attempt in range(5):
            try:
                # Truncate long chunks
                truncated = [t[:4000] for t in texts]
                r = self.cl.embeddings.create(
                    input=truncated, model=EMBED_DEPLOY, dimensions=DIMENSIONS)
                return [e.embedding for e in r.data]
            except Exception as e:
                err = str(e)
                if '429' in err or 'RateLimit' in err:
                    wait = min(2 ** attempt * 10, 120)
                    print(f"    ⏳ Rate limit, wait {wait}s...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                if attempt < 3: time.sleep(2 ** attempt)
                else: raise


# ════════════════════════════════════════
# MAIN
# ════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Ingest Open WebUI docs")
    parser.add_argument("--url", action="append", default=[],
                        help="Additional URLs to fetch")
    parser.add_argument("--upload", action="store_true",
                        help="Upload to AI Search after preprocessing")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not KEY:
        print("❌ Set AZURE_OPENAI_API_KEY"); sys.exit(1)

    urls = DEFAULT_URLS + args.url
    print("═" * 60)
    print("📦 OPEN WEBUI DOCS INGESTION")
    print("═" * 60)
    print(f"   URLs: {len(urls)}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Model: {SUMMARY_DEPLOY} / {EMBED_DEPLOY}")
    if args.dry_run: print(f"   Mode: 🧪 DRY RUN")

    llm = LLM()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_chunks = 0

    for url in urls:
        print(f"\n🌐 Fetching: {url}")
        title, text = fetch_page(url)

        if not text or text.startswith("[Error"):
            print(f"  ❌ {text}")
            continue

        print(f"  📄 {title[:60]} — {len(text):,} chars")

        # Chunk
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            print("  ⚠️ No chunks")
            continue
        print(f"  → {len(chunks)} chunks")

        if args.dry_run:
            for i, c in enumerate(chunks[:3]):
                print(f"    Chunk {i}: {len(c)} chars — {c[:100]}...")
            continue

        # Classify (first chunk)
        category = llm.classify(chunks[0][:3000])
        print(f"  🏷️  {category}")

        # Summarize
        print(f"  ✍️  Summarizing...", end=" ", flush=True)
        summaries = llm.summarize(chunks)
        print(f"{len([s for s in summaries if s])}/{len(chunks)} done")

        # Embed
        print(f"  🧠 Embedding...", end=" ", flush=True)
        try:
            embeddings = llm.embed(chunks)
            print(f"done")
        except Exception as e:
            print(f"❌ {e}")
            continue

        # Build meta
        doc_id = hashlib.md5(url.encode()).hexdigest()[:12]
        meta = json.dumps({
            "file_hash": hashlib.md5(text.encode()).hexdigest(),
            "source": "web",
            "url": url,
            "title": title,
            "corpus": "openwebui-docs",
            "category": category,
            "language": "en",
            "pages": 1,
            "file_size_bytes": len(text),
        }, ensure_ascii=False)

        # Write JSONL
        fname = re.sub(r'[^a-zA-Z0-9_-]', '_', urlparse(url).path.strip('/'))
        if not fname:
            fname = "index"
        out_path = OUTPUT_DIR / f"{fname}.jsonl"

        with open(out_path, 'w', encoding='utf-8') as f:
            for i, (chunk_text_val, summary, emb) in enumerate(zip(chunks, summaries, embeddings)):
                line = json.dumps({
                    "id": f"{doc_id}_{i:05d}",
                    "doc_id": doc_id,
                    "chunk_seq": i,
                    "file_name": f"{title} ({url})",
                    "file_path": url,
                    "corpus": "openwebui-docs",
                    "category": category,
                    "content": chunk_text_val,
                    "summary": summary,
                    "meta": meta,
                    "content_vector": emb,
                }, ensure_ascii=False)
                f.write(line + '\n')

        total_chunks += len(chunks)
        print(f"  ✅ {len(chunks)} chunks written to {out_path.name}")

    print(f"\n{'═'*60}")
    print(f"📊 Done: {total_chunks} total chunks → {OUTPUT_DIR}")
    print(f"{'═'*60}")

    # Optionally upload
    if args.upload and not args.dry_run:
        print("\n📤 Uploading to AI Search...")
        import subprocess
        subprocess.run([
            sys.executable, "scripts/upload-to-search.py",
            "--corpus", "openwebui-docs",
        ], check=False)


if __name__ == "__main__":
    main()
