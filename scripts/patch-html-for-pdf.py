#!/usr/bin/env python3
"""
Patch HTML to add Table of Contents and fix titles for PDF generation.
"""

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "docs", "genie-setup-manual.html")
OUT = os.path.join(BASE, "docs", "_tmp_print.html")

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# ── 1. Fix titles ──
html = html.replace(
    '<title>Genie Enterprise Agent — Setup Guide</title>',
    '<title>Genie Enterprise Agent — User Guide</title>'
)
html = html.replace(
    '<h1>🪄 Genie — Enterprise Knowledge Setup Guide</h1>',
    '<h1>🪄 Genie — Enterprise Chat User Guide</h1>'
)
html = html.replace(
    '<p>คู่มือติดตั้ง Enterprise AI Agent สำหรับ Haadthip DIO Team</p>',
    '<p>คู่มือการใช้งาน Enterprise AI Assistant สำหรับทีม DIO</p>'
)

# ── 2. Inject TOC page + print CSS before </style> ──
toc_css = """
/* ── TOC styles ── */
.toc-page { page-break-after: always; padding: 40px 30px; max-width: 960px; margin: 0 auto; }
.toc-page h2 { font-size: 24px; font-weight: 600; margin-bottom: 30px; color: #1d1d1f; text-align: center; border-bottom: 2px solid #0071e3; padding-bottom: 12px; }
.toc-item { display: flex; align-items: center; padding: 12px 16px; margin-bottom: 8px; border-radius: 10px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.08); transition: none; }
.toc-num { font-size: 14px; font-weight: 700; color: #0071e3; min-width: 32px; }
.toc-icon { font-size: 20px; margin-right: 12px; }
.toc-title { font-size: 15px; font-weight: 600; color: #1d1d1f; }
.toc-desc { font-size: 12px; color: #6e6e73; margin-left: auto; }

/* ── Print / PDF overrides ── */
.tabs { display: none !important; }
.panel { display: block !important; max-width: 100% !important; padding: 24px 30px !important; margin: 0 auto !important; }
.panel h2 { font-size: 20pt; margin-top: 0; }
.panel .desc { font-size: 12pt; color: #555; }
.step { page-break-inside: avoid; break-inside: avoid; margin-bottom: 18pt; }
.step h3 { font-size: 13pt; }
.step p, .step li { font-size: 11pt; line-height: 1.8; }
.step code { font-size: 10pt; }
.step pre { font-size: 8pt; max-height: none; }
.info-table { font-size: 10pt; }
.info-table th, .info-table td { padding: 6pt 8pt; }
.grid-2, .grid-3 { grid-template-columns: 1fr 1fr; }
img { max-width: 90% !important; height: auto; page-break-inside: avoid; }
.header-bar { padding: 30px 20px; }
.header-bar h1 { font-size: 18pt; }
.header-bar p { font-size: 11pt; }
.code-toggle { display: none !important; }
.code-wrap { display: block !important; margin-top: 8pt; }
.lightbox { display: none !important; }
.step img, .showcase-body img { cursor: default; }
.terminal { font-size: 8pt; padding: 10pt; }
thead { display: table-row-group; }
body { background: white; }
@page { margin: 20pt 25pt; }
"""

# Insert CSS before </style>
html = html.replace("</style>", toc_css + "\n</style>")

# ── 3. Build TOC block ──
toc_block = """
<div class="toc-page">
  <h2>📋 สารบัญ</h2>

  <div class="toc-item">
    <span class="toc-num">1</span>
    <span class="toc-icon">📖</span>
    <span class="toc-title">วิธีใช้ Genie — Open WebUI Wiki</span>
    <span class="toc-desc">แชท, แนบไฟล์, ฟีเจอร์พื้นฐาน, Tips &amp; Tricks, Use Cases</span>
  </div>

  <div class="toc-item">
    <span class="toc-num">2</span>
    <span class="toc-icon">📚</span>
    <span class="toc-title">Knowledge Base</span>
    <span class="toc-desc">สร้างและจัดการฐานความรู้สำหรับ Agent</span>
  </div>

  <div class="toc-item">
    <span class="toc-num">3</span>
    <span class="toc-icon">💬</span>
    <span class="toc-title">Prompts</span>
    <span class="toc-desc">เทมเพลตคำสั่งสำหรับเรียกใช้ซ้ำ</span>
  </div>

  <div class="toc-item">
    <span class="toc-num">4</span>
    <span class="toc-icon">🤖</span>
    <span class="toc-title">ขั้นตอนสร้าง Agent</span>
    <span class="toc-desc">สร้าง Model ที่มี Tool ติดตัว</span>
  </div>

  <div class="toc-item">
    <span class="toc-num">5</span>
    <span class="toc-icon">🧠</span>
    <span class="toc-title">Skills</span>
    <span class="toc-desc">ความสามารถเฉพาะทางของ Agent</span>
  </div>

  <div class="toc-item">
    <span class="toc-num">6</span>
    <span class="toc-icon">🔧</span>
    <span class="toc-title">ขั้นตอนเพิ่ม Tool (Advance)</span>
    <span class="toc-desc">เพิ่ม Enterprise Search Tool</span>
  </div>
</div>
"""

# Insert TOC after header bar (before tabs)
html = html.replace('<div class="tabs" id="tabs">', toc_block + '\n<div class="tabs" id="tabs">')

# ── 4. Remove tab-switching and lightbox JS ──
import re
html = re.sub(r'// Tab switching.*?}\);', '', html, flags=re.DOTALL)
html = re.sub(r'// Lightbox.*?}\);', '', html, flags=re.DOTALL)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Patched HTML with TOC: {OUT}")
print(f"   Size: {os.path.getsize(OUT) / 1024:.0f} KB")
