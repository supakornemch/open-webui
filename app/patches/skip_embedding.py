"""Per-file embedding skip, driven by SKIP_EMBEDDING_EXTENSIONS.

Upstream only has the global BYPASS_EMBEDDING_AND_RETRIEVAL flag, which kills RAG
for every file in the system. We still want RAG for docs, but not for data files
(xlsx/csv) that a Tool reads with pandas — embedding a 500-row price table is cost
with no benefit, and its numbers must not leak into unrelated RAG answers.

Dockerfile.owui seds routers/retrieval.py to OR should_skip_embedding() into the
existing bypass branch: text is still extracted into file.data.content, only the
vector write is skipped.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def _extensions() -> set[str]:
    raw = os.environ.get('SKIP_EMBEDDING_EXTENSIONS', '')
    return {e.strip().lower().lstrip('.') for e in raw.split(',') if e.strip()}


def should_skip_embedding(filename: str | None) -> bool:
    if not filename:
        return False

    extensions = _extensions()
    if not extensions:
        return False

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in extensions:
        log.info('skip_embedding: %s matches SKIP_EMBEDDING_EXTENSIONS (.%s)', filename, ext)
        return True
    return False
