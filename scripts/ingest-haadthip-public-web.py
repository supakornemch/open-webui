#!/usr/bin/env python3
"""
ingest-haadthip-public-web.py — Haadthip public website → chunk → summarize → embed → JSONL
==============================================================================================
Fetches key pages from www.haadthip.com (company info, products, IR, sustainability, etc.)
and ingests into enterprise-docs-idx as corpus="haadthip-public-web".

Uses the same pipeline pattern as ingest-openwebui-docs.py — fetch, chunk, GPT classify,
GPT summarize, embed, write JSONL.

Usage:
  export AZURE_OPENAI_API_KEY="..."
  export AZURE_SEARCH_KEY="..."   # optional, for direct upload

  # Fetch + preprocess (saves JSONL)
  python3 scripts/ingest-haadthip-public-web.py

  # Fetch + preprocess + upload directly to AI Search
  python3 scripts/ingest-haadthip-public-web.py --upload

  # Dry run (show chunks without LLM calls)
  python3 scripts/ingest-haadthip-public-web.py --dry-run
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
OUTPUT_DIR = Path("data/ingestion/haadthip-public-web")
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200

# ── Key pages to ingest ──────────────────
PAGES = [
    # (title_for_display, url)
    ("หน้าแรก",               "https://www.haadthip.com/th/home"),
    ("ข้อมูลบริษัท",          "https://www.haadthip.com/th/about/about-the-company"),
    ("วิสัยทัศน์และพันธกิจ",  "https://www.haadthip.com/th/about/vision-and-mission"),
    ("ประวัติบริษัท",         "https://www.haadthip.com/th/about/company-milestones"),
    ("โครงสร้างกลุ่มธุรกิจ",   "https://www.haadthip.com/th/about/business-structure"),
    ("ศูนย์กระจายสินค้า",     "https://www.haadthip.com/th/about/distribution-centers-and-branches"),
    ("ระบบคุณภาพ",           "https://www.haadthip.com/th/about/quality-system"),
    ("การกำกับดูแลกิจการ",    "https://www.haadthip.com/th/about/good-corporate-governance"),
    ("นักลงทุนสัมพันธ์",      "https://www.haadthip.com/th/investor-relations/home"),
]

# ── Categories for Haadthip content ──────
CATEGORIES = [
    "Company Overview",
    "Vision & Mission",
    "History & Milestones",
    "Products & Brands",
    "Distribution & Logistics",
    "Quality & Certifications",
    "Corporate Governance",
    "Sustainability",
    "Investor Relations",
    "Business Structure",
    "HR & Culture",
    "News & Events",
]

CATEGORY_PROMPT = (
    "Classify this excerpt of Haadthip Public Company Limited content into ONE category. "
    "Return ONLY the category name.\n"
    + "\n".join(f"  - {c}" for c in CATEGORIES)
    + "\n\nExcerpt:\n{text}"
)

SUMMARY_PROMPT = (
    "For each numbered excerpt of Haadthip company content below, "
    "write a 1-sentence summary in Thai. Return ONLY a JSON array of strings.\n\n"
)


# ════════════════════════════════════════
# WEB FETCHER
# ════════════════════════════════════════

def fetch_page(url: str) -> Tuple[str, str]:
    """
    Fetch a Haadthip public web page and extract readable text content.
    Returns (title, text_content).
    """
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }, timeout=30)
        r.raise_for_status()
    except Exception as e:
        return ("", f"[Error fetching {url}: {e}]")

    html = r.text
    title = ""

    # Extract title from og:title (Haadthip site has empty <title>)
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r'<meta\s+name="twitter:title"\s+content="([^"]*)"', html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
    if not title:
        m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            title = re.sub(r'\s*[|–-].*$', '', title).strip()

    # Remove non-content elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove specific Haadthip site noise elements (sidebar menus, headers, cookie banners)
    html = re.sub(
        r'<div\s+class="[^"]*\b(?:menu-wrapper|header__navigation|header__search|'
        r'cookie-consent|breadcrumb__dropdown|breadcrumb__mobile)[^"]*"[^>]*>.*?</div>',
        '', html, flags=re.DOTALL | re.IGNORECASE
    )

    # Try to extract meaningful content area — Haadthip uses <section class="section ...">
    for selector in [r'<main[^>]*>(.*?)</main>',
                     r'<article[^>]*>(.*?)</article>',
                     r'<section[^>]*\bclass\s*=\s*"[^"]*\bsection\b[^"]*"[^>]*>(.*?)</section>',
                     r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                     r'<div[^>]*class="[^"]*page-content[^"]*"[^>]*>(.*?)</div>',
                     r'<div[^>]*class="[^"]*wrapper[^"]*"[^>]*>(.*?)</div>']:
        m = re.search(selector, html, re.DOTALL | re.IGNORECASE)
        if m:
            html = m.group(1)
            break

    # Replace block-level closing tags with newlines
    for tag in ['</div>', '</p>', '</h1>', '</h2>', '</h3>', '</h4>', '</h5>',
                '</h6>', '</li>', '</tr>', '</td>', '</section>', '</article>',
                '</dd>', '</dt>', '</figcaption>', '</blockquote>']:
        html = html.replace(tag, tag + '\n')
    html = html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    html = html.replace('</th>', '</th>\n')

    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Decode HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&apos;', "'")
    text = re.sub(r'&#x?[0-9a-fA-F]+;', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)

    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()

    # Remove common noise lines
    noise_prefixes = [
        'Skip to', 'Menu', 'Search', 'Copyright', 'All Rights Reserved',
        'Cookie', 'Accept All', 'ยอมรับ', 'Accept', 'Close',
        'Facebook', 'Instagram', 'YouTube', 'ติดต่อเรา', 'แผนผังเว็บไซต์',
        'นโยบายความเป็นส่วนตัว', 'นโยบายคุกกี้', 'ข้อกำหนดและเงื่อนไข',
    ]
    lines = [l.strip() for l in text.split('\n')]
    filtered = []
    for l in lines:
        if not l:
            continue
        if any(l.strip().startswith(p) for p in noise_prefixes):
            continue
        # Skip very short lines that are likely UI artifacts
        if len(l.strip()) < 3:
            continue
        filtered.append(l)
    text = '\n\n'.join(filtered)

    return (title, text)


# ════════════════════════════════════════
# CHUNKING
# ════════════════════════════════════════

def chunk_text(text: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into chunks, preserving natural paragraph boundaries."""
    if len(text) <= max_size:
        return [text] if len(text.strip()) > 30 else []

    # Try splitting by double newlines first (paragraph boundaries)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks = []
    current = ""

    for para in paragraphs:
        if len(para) > max_size:
            # Paragraph too large — split by sentences
            if current:
                chunks.append(current.strip())
                current = ""
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                if not sent.strip():
                    continue
                if len(current) + len(sent) + 1 <= max_size:
                    current = current + ' ' + sent if current else sent
                else:
                    if current:
                        chunks.append(current.strip())
                    current = sent
        elif len(current) + len(para) + 2 <= max_size:
            current = current + '\n\n' + para if current else para
        else:
            if current:
                chunks.append(current.strip())
            current = para

    if current and current.strip():
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
                messages=[
                    {"role": "system", "content": "Classify into 1 category. Return ONLY the name."},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=30, temperature=0.0)
            result = r.choices[0].message.content.strip()
            for c in CATEGORIES:
                if c.lower() in result.lower():
                    return c
            return result[:50]
        except Exception as e:
            print(f"    ⚠️ Classify err: {e}")
            return "Company Overview"

    def summarize(self, chunks: List[str]) -> List[str]:
        summaries = []
        for i in range(0, len(chunks), 10):
            batch = chunks[i:i+10]
            blocks = "\n\n---\n\n".join(f"[{j}] {t[:2000]}" for j, t in enumerate(batch))
            prompt = SUMMARY_PROMPT + blocks

            try:
                r = self.cl.chat.completions.create(
                    model=SUMMARY_DEPLOY,
                    messages=[
                        {"role": "system", "content": "Summarize in Thai. Return JSON array of strings."},
                        {"role": "user", "content": prompt},
                    ],
                    max_completion_tokens=500, temperature=0.2)
                result = r.choices[0].message.content.strip()

                try:
                    m = re.search(r'\[.*\]', result, re.DOTALL)
                    parsed = json.loads(m.group(0) if m else result)
                    if isinstance(parsed, list):
                        while len(parsed) < len(batch):
                            parsed.append("")
                        summaries.extend(str(s) for s in parsed[:len(batch)])
                        continue
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass

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
                if attempt < 3:
                    time.sleep(2 ** attempt)
                else:
                    print(f"    ❌ Embed err: {e}")
                    raise


# ════════════════════════════════════════
# MAIN
# ════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Ingest Haadthip public web content")
    parser.add_argument("--url", action="append", default=[],
                        help="Additional page URLs to fetch (appended to default list)")
    parser.add_argument("--upload", action="store_true",
                        help="Upload to AI Search after preprocessing")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show chunks without LLM calls")
    parser.add_argument("--corpus", default="haadthip-public-web",
                        help="Corpus name (default: haadthip-public-web)")
    args = parser.parse_args()

    if not KEY:
        print("❌ Set AZURE_OPENAI_API_KEY environment variable")
        sys.exit(1)

    pages = list(PAGES)
    for extra_url in args.url:
        pages.append((extra_url, extra_url))

    print("═" * 70)
    print("🏢 HAADTHIP PUBLIC WEBSITE INGESTION")
    print("═" * 70)
    print(f"   Pages: {len(pages)}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Corpus: {args.corpus}")
    print(f"   Model: {SUMMARY_DEPLOY} / {EMBED_DEPLOY}")
    print(f"   Chunk: {CHUNK_SIZE} chars / {CHUNK_OVERLAP} overlap")
    if args.dry_run:
        print(f"   Mode: 🧪 DRY RUN (no LLM calls)")
    print()

    llm = LLM()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_chunks = 0

    for page_name, url in pages:
        print(f"\n{'─' * 60}")
        print(f"🌐 [{page_name}]")
        print(f"   URL: {url}")

        title, text = fetch_page(url)

        if not text or text.startswith("[Error"):
            print(f"   ❌ {text}")
            continue

        print(f"   📄 Title: {title[:80]}")
        print(f"   📏 {len(text):,} chars extracted")

        # Chunk
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            print("   ⚠️ No chunks generated")
            continue
        print(f"   🔪 {len(chunks)} chunks")

        if args.dry_run:
            for i, c in enumerate(chunks[:4]):
                print(f"      Chunk {i}: {len(c)} chars — {c[:120]}...")
            if len(chunks) > 4:
                print(f"      ... and {len(chunks)-4} more chunks")
            continue

        # Classify (using first chunk's content)
        category = llm.classify(chunks[0][:3000])
        print(f"   🏷️  Category: {category}")

        # Summarize
        print(f"   ✍️  Summarizing...", end=" ", flush=True)
        summaries = llm.summarize(chunks)
        summary_count = len([s for s in summaries if s])
        print(f"{summary_count}/{len(chunks)} done")

        # Embed
        print(f"   🧠 Embedding...", end=" ", flush=True)
        try:
            embeddings = llm.embed(chunks)
            print(f"✅ {len(embeddings)} vectors ({DIMENSIONS}d)")
        except Exception as e:
            print(f"❌ {e}")
            continue

        # Build metadata
        doc_id = hashlib.md5(url.encode()).hexdigest()[:12]
        file_hash = hashlib.md5(text.encode()).hexdigest()
        meta = json.dumps({
            "file_hash": file_hash,
            "source": "haadthip-public-web",
            "url": url,
            "title": title or page_name,
            "page_name": page_name,
            "corpus": args.corpus,
            "category": category,
            "language": "th",
            "file_size_bytes": len(text),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

        # Write JSONL
        # Use URL path segments as safe filename (e.g. "about-about-the-company")
        path = urlparse(url).path.strip('/')
        safe_name = path.replace('/', '-') if path else "home"
        out_path = OUTPUT_DIR / f"{safe_name}.jsonl"

        with open(out_path, 'w', encoding='utf-8') as f:
            for i, (chunk_val, summary, emb) in enumerate(zip(chunks, summaries, embeddings)):
                line = json.dumps({
                    "id": f"{doc_id}_{i:05d}",
                    "doc_id": doc_id,
                    "chunk_seq": i,
                    "file_name": f"{title or page_name}",
                    "file_path": url,
                    "corpus": args.corpus,
                    "category": category,
                    "content": chunk_val,
                    "summary": summary,
                    "meta": meta,
                    "content_vector": emb,
                }, ensure_ascii=False)
                f.write(line + '\n')

        total_chunks += len(chunks)
        print(f"   ✅ Saved: {out_path.name} ({len(chunks)} chunks)")

    print(f"\n{'═' * 70}")
    print(f"📊 Done: {total_chunks} total chunks → {OUTPUT_DIR}/")
    print(f"{'═' * 70}")

    # ── Optional upload ──
    if args.upload and not args.dry_run:
        print(f"\n📤 Uploading corpus '{args.corpus}' to Azure AI Search...")
        import subprocess
        result = subprocess.run([
            sys.executable, "scripts/upload-to-search.py",
            "--corpus", args.corpus,
        ], check=False)
        if result.returncode == 0:
            print("✅ Upload complete!")
        else:
            print(f"⚠️ Upload returned exit code {result.returncode}")
            print("   You can re-run manually:")
            print(f"   python3 scripts/upload-to-search.py --corpus {args.corpus}")


if __name__ == "__main__":
    main()
