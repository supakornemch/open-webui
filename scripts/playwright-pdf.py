#!/usr/bin/env python3
"""
Generate PDF User Guide using Playwright (Chrome) for proper Thai font shaping.

ReportLab doesn't support OpenType Thai mark positioning (e.g., สระอี+ไม้โท stacking),
so we use Playwright which uses Chrome's HarfBuzz text engine for correct Thai rendering.
"""

import os
import re
import time
import subprocess
import threading
import http.server
import socketserver

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_SRC = os.path.join(BASE_DIR, "docs", "genie-setup-manual.html")
HTML_TMP = os.path.join(BASE_DIR, "docs", "_tmp_print.html")
OUTPUT_PDF = os.path.join(BASE_DIR, "docs", "genie-user-guide.pdf")
PORT = 8899


def patch_html():
    """Read original HTML, create a print-friendly version with all panels visible."""
    with open(HTML_SRC, "r", encoding="utf-8") as f:
        html = f.read()

    # --- Fix titles ---
    html = html.replace(
        '<h1>🪄 Genie — Enterprise Knowledge Setup Guide</h1>',
        '<h1>🪄 Genie — Enterprise Chat User Guide</h1>'
    )
    html = html.replace(
        '<p>คู่มือติดตั้ง Enterprise AI Agent สำหรับ Haadthip DIO Team</p>',
        '<p>คู่มือการใช้งาน Enterprise AI Assistant สำหรับทีม DIO</p>'
    )

    # --- Inject print CSS before </style> ---
    print_css = """
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
    html = html.replace("</style>", print_css + "\n</style>")

    # --- Remove tab-switching JS but keep toggleCode ---
    old_js = """// Tab switching
	const tabs = document.querySelectorAll('.tab-btn');
	tabs.forEach(btn => {
	  btn.addEventListener('click', () => {
	    tabs.forEach(b => b.classList.remove('active'));
	    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
	    btn.classList.add('active');
	    document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
	    window.scrollTo(0, 0);
	  });
	});"""
    html = html.replace(old_js, "")

    # Remove lightbox JS
    lightbox_js = """// Lightbox — click any img to view full size
	document.querySelectorAll('.step img, .showcase-body img').forEach(img => {
	  img.addEventListener('click', () => {
	    document.getElementById('lightbox-img').src = img.src;
	    document.getElementById('lightbox').classList.add('open');
	  });
	});"""
    html = html.replace(lightbox_js, "")

    with open(HTML_TMP, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Patched HTML: {HTML_TMP}")
    return HTML_TMP


def start_server():
    """Start a simple HTTP server in the BASE_DIR."""
    os.chdir(BASE_DIR)
    handler = http.server.SimpleHTTPRequestHandler

    class QuietHandler(handler):
        def log_message(self, format, *args):
            pass  # Suppress logs

    httpd = socketserver.TCPServer(("", PORT), QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"🌐 Server started on http://localhost:{PORT}")
    return httpd


def generate_pdf_playwright(html_path):
    """Use browser_run_code_unsafe via MCP-like approach..."""
    pass
    # We'll use the MCP Playwright tools directly


if __name__ == "__main__":
    patch_html()
    # Server + Playwright will be handled interactively via MCP tools
    print(f"\nRun these steps manually:")
    print(f"1. python3 -m http.server {PORT} -d {BASE_DIR}")
    print(f"2. Use Playwright: navigate to http://localhost:{PORT}/docs/_tmp_print.html")
    print(f"3. Inject CSS via evaluate to ensure all content visible")
    print(f"4. Call browser_run_code_unsafe: page.pdf()")
