"""
Re-upload knowledge documents to OWUI → Azure AI Search backend.

Run INSIDE the OWUI container:
  docker exec -w /app/backend open-webui-local python3 /tmp/upload_knowledge.py
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from typing import List, Optional

# Add OWUI backend to path
sys.path.insert(0, "/app/backend")

from open_webui.internal.db import SessionLocal
from open_webui.models.knowledge import Knowledges, KnowledgeForm
from open_webui.models.files import Files, FileForm
from open_webui.config import DATA_DIR
from sqlalchemy import text

# Knowledge sources (copied into container)
KNOWLEDGE_ROOT = Path("/app/backend/data/knowledge_docs")
UPLOADS_DIR = Path(DATA_DIR) / "uploads"

KB_CONFIGS = [
    {
        "name": "Corporate Knowledge",
        "description": "Haadthip corporate documents — IT, Security, Email, Meeting Rooms, Policies",
        "folder": "corporate",
    },
    {
        "name": "HR Policies",
        "description": "Haadthip HR policies and procedures",
        "folder": "hr-policies",
    },
]

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".xlsx", ".csv"}


def find_files(root: Path) -> List[Path]:
    """Find all supported document files recursively."""
    files = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return sorted(files)


def main():
    print("=" * 60)
    print("Knowledge Base Re-upload → Azure AI Search")
    print("=" * 60)
    print(f"Document root: {KNOWLEDGE_ROOT}")
    print()

    if not KNOWLEDGE_ROOT.exists():
        print(f"❌ KNOWLEDGE_ROOT not found: {KNOWLEDGE_ROOT}")
        sys.exit(1)

    db = SessionLocal()

    try:
        for kb_config in KB_CONFIGS:
            print(f"\n📁 {kb_config['name']}")
            print(f"   {kb_config['description']}")
            print("-" * 40)

            # Get or create knowledge base
            result = db.execute(
                text("SELECT id FROM knowledge WHERE name = :name"),
                {"name": kb_config["name"]}
            ).fetchone()

            if result:
                kb_id = result[0]
                print(f"   [KB] Found: {kb_id[:16]}...")
            else:
                form = KnowledgeForm(
                    name=kb_config["name"],
                    description=kb_config["description"],
                    access_control=None,
                )
                kb = Knowledges.insert_new_knowledge(
                    "172bdc06-2feb-4680-ad10-28dcc7cae92e",  # default user
                    form,
                    db
                )
                db.commit()
                kb_id = kb.id if kb else None
                print(f"   [KB] Created: {kb_id}")

            # Find files
            folder = KNOWLEDGE_ROOT / kb_config["folder"]
            if not folder.exists():
                print(f"   ⚠️  Folder not found: {folder}")
                continue

            files = find_files(folder)
            print(f"   Found {len(files)} files")

            for i, filepath in enumerate(files, 1):
                rel = filepath.relative_to(KNOWLEDGE_ROOT)
                filename = filepath.name

                try:
                    # Read file
                    with open(filepath, "rb") as f:
                        content = f.read()

                    # Save to uploads
                    upload_path = UPLOADS_DIR / filename
                    upload_path.parent.mkdir(parents=True, exist_ok=True)
                    upload_path.write_bytes(content)

                    # Create file record
                    file_form = FileForm(
                        filename=filename,
                        meta=json.dumps({
                            "collection_name": kb_id,
                            "name": filename,
                            "path": str(upload_path),
                            "size": len(content),
                        }),
                    )
                    file_record = Files.insert_new_file(
                        "172bdc06-2feb-4680-ad10-28dcc7cae92e",  # default user
                        file_form,
                        db
                    )
                    db.commit()

                    print(f"   [{i}/{len(files)}] ✅ {rel}")

                except Exception as e:
                    print(f"   [{i}/{len(files)}] ❌ {rel}: {e}")

            print(f"   ✅ Done — {kb_config['name']}")

    finally:
        db.close()

    print(f"\n{'=' * 60}")
    print("Upload complete! OWUI will embed files in background.")
    print("Check Azure AI Search for new indexes.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
