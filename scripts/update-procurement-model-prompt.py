#!/usr/bin/env python3
"""
Update procurement-price-assistant model system prompt on QAS OWUI.

Usage:
  python3 scripts/update-procurement-model-prompt.py

Requires:
  - Azure QAS PostgreSQL credentials in qas.env (DATABASE_URL)
  - New system prompt in features/procurement/docs/procurement-assistant-system-prompt.md
"""
import os, sys
from pathlib import Path
from urllib.parse import urlparse

# ── Config ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
SYS_PROMPT_FILE = REPO_ROOT / "features/procurement/docs/procurement-assistant-system-prompt.md"
MODEL_ID = "procurement-price-assistant"
ENV_FILE = REPO_ROOT / "qas.env"

# ── Load system prompt ──────────────────────────────────────────────
def load_system_prompt() -> str:
    content = SYS_PROMPT_FILE.read_text(encoding="utf-8")
    # Strip the "Knowledge Reference" section that lives in skill, not the model
    # Keep everything up to (but not including) the "## Knowledge Reference" line
    marker = "\n## Knowledge Reference"
    if marker in content:
        content = content.split(marker)[0].rstrip()
    print(f"Loaded system prompt ({len(content)} chars) from {SYS_PROMPT_FILE.name}")
    return content

# ── Parse DATABASE_URL ───────────────────────────────────────────────
def parse_db_url(url: str):
    p = urlparse(url)
    return {
        "host": p.hostname,
        "port": p.port or 5432,
        "dbname": p.path.lstrip("/"),
        "user": p.username,
        "password": p.password,
    }

# ── Main ─────────────────────────────────────────────────────────────
def main():
    # Load env
    db_url = None
    import subprocess
    from urllib.parse import urlparse

    # Fetch real DB URL from Key Vault (qas.env has wrong password)
    result = subprocess.run(
        [
            "az", "keyvault", "secret", "show",
            "--vault-name", "kv-entchat-qas",
            "--name", "entchat-owui-database-url",
            "--subscription", "SUB-HTC-QAS-DC",
            "--query", "value", "--output", "tsv"
        ],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0 or not result.stdout.strip():
        print("⚠️  KeyVault fetch failed.")
        sys.exit(1)
    db_url = result.stdout.strip()
    print("Fetched DB URL from KeyVault.")

    # Decode URL-encoded password (Azure CLI hides ! as %21 in output)
    parsed = urlparse(db_url)
    db_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 5432}{parsed.path}?sslmode=require"

    creds = parse_db_url(db_url)
    print(f"Connecting to {creds['dbname']}@{creds['host']}:{creds['port']} ...")

    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed — run: pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(**creds, connect_timeout=15, sslmode="require")
    conn.autocommit = True
    cur = conn.cursor()

    # Find the model
    cur.execute(
        "SELECT id, name, prompt FROM models WHERE id = %s OR id LIKE %s LIMIT 5",
        (MODEL_ID, f"%{MODEL_ID}%")
    )
    rows = cur.fetchall()
    print(f"Models found: {len(rows)}")
    for row in rows:
        print(f"  id={row[0]}  name={row[1]}")

    if not rows:
        print(f"❌ Model '{MODEL_ID}' not found in OWUI database")
        sys.exit(1)

    model_id = rows[0][0]
    old_prompt = rows[0][2] or ""

    new_prompt = load_system_prompt()
    print(f"\nCurrent prompt length: {len(old_prompt)} chars")
    print(f"New prompt length:    {len(new_prompt)} chars")

    if old_prompt == new_prompt:
        print("\n✅ Prompt unchanged — no update needed.")
        sys.exit(0)

    # Show diff preview
    print("\n--- Old prompt (first 300 chars) ---")
    print(old_prompt[:300])
    print("\n--- New prompt (first 300 chars) ---")
    print(new_prompt[:300])

    # Update
    cur.execute(
        "UPDATE models SET prompt = %s WHERE id = %s",
        (new_prompt, model_id)
    )
    print(f"\n✅ Updated model '{model_id}' — {cur.rowcount} row(s) affected.")
    print(f"   Prompt is now {len(new_prompt)} chars.")


if __name__ == "__main__":
    main()
