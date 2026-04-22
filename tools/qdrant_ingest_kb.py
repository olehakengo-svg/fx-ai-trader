#!/usr/bin/env python3
"""Ingest knowledge-base wiki markdown into qdrant-fx collection.

IMPORTANT: The MCP qdrant-fx server holds an exclusive lock on the embedded
Qdrant storage at knowledge-base/.qdrant/. Stop the MCP server before running
this script, then /mcp reconnect after ingest completes.

Run:
    python3 tools/qdrant_ingest_kb.py                  # default dirs
    python3 tools/qdrant_ingest_kb.py --rebuild        # drop + recreate collection
    python3 tools/qdrant_ingest_kb.py --dirs wiki/research wiki/lessons

First invocation bootstraps a dedicated venv at tools/.venv-qdrant-ingest/
(qdrant-client + fastembed). Subsequent runs reuse it.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / "tools" / ".venv-qdrant-ingest"
VENV_PY = VENV_DIR / "bin" / "python"

QDRANT_PATH = PROJECT_ROOT / "knowledge-base" / ".qdrant"
COLLECTION = "fx-research"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384

DEFAULT_DIRS = [
    "knowledge-base/wiki/research",
    "knowledge-base/wiki/lessons",
    "knowledge-base/wiki/analyses",
    "knowledge-base/wiki/strategies",
    "knowledge-base/wiki/syntheses",
    "knowledge-base/wiki/decisions",
]

CHUNK_CHARS = 2000
CHUNK_OVERLAP = 200


def _bootstrap_venv() -> Path:
    if VENV_PY.exists():
        return VENV_PY
    print(f"[bootstrap] Creating venv at {VENV_DIR}", flush=True)
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    pip = VENV_DIR / "bin" / "pip"
    subprocess.check_call([
        str(pip), "install", "-q", "--upgrade", "pip",
    ])
    subprocess.check_call([
        str(pip), "install", "-q",
        "qdrant-client>=1.10,<2",
        "fastembed>=0.3",
    ])
    return VENV_PY


def _in_target_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV_DIR.resolve()
    except OSError:
        return False


def _ensure_deps() -> None:
    if _in_target_venv():
        return
    try:
        import qdrant_client  # noqa: F401
        import fastembed  # noqa: F401
        return
    except ImportError:
        pass
    py = _bootstrap_venv()
    os.execv(str(py), [str(py), __file__, *sys.argv[1:]])


def _read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _chunk(text: str) -> list[str]:
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks: list[str] = []
    step = CHUNK_CHARS - CHUNK_OVERLAP
    for start in range(0, len(text), step):
        chunk = text[start : start + CHUNK_CHARS]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _point_id(path_rel: str, chunk_idx: int) -> str:
    h = hashlib.sha256(f"{path_rel}#{chunk_idx}".encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def ingest(dirs: list[str], rebuild: bool) -> None:
    from fastembed import TextEmbedding
    from qdrant_client import QdrantClient, models

    client = QdrantClient(path=str(QDRANT_PATH))
    existing = {c.name for c in client.get_collections().collections}

    if rebuild and COLLECTION in existing:
        print(f"[rebuild] Dropping {COLLECTION}")
        client.delete_collection(COLLECTION)
        existing.discard(COLLECTION)

    if COLLECTION not in existing:
        print(f"[create] {COLLECTION} dim={EMBED_DIM}")
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBED_DIM, distance=models.Distance.COSINE
            ),
        )

    embedder = TextEmbedding(model_name=EMBED_MODEL)

    files: list[Path] = []
    for d in dirs:
        base = (PROJECT_ROOT / d).resolve()
        if not base.exists():
            print(f"[skip] missing {d}")
            continue
        files.extend(sorted(base.rglob("*.md")))

    print(f"[scan] {len(files)} markdown files across {len(dirs)} dirs")

    points: list = []
    total_chunks = 0
    for path in files:
        text = _read_markdown(path)
        if not text.strip():
            continue
        rel = str(path.relative_to(PROJECT_ROOT))
        category = rel.split("/")[2] if rel.startswith("knowledge-base/wiki/") else "other"
        title = _extract_title(text, path.stem)
        mtime = path.stat().st_mtime
        chunks = _chunk(text)
        for idx, chunk in enumerate(chunks):
            vec = next(iter(embedder.embed([chunk]))).tolist()
            points.append(
                models.PointStruct(
                    id=_point_id(rel, idx),
                    vector=vec,
                    payload={
                        "document": chunk,
                        "path": rel,
                        "category": category,
                        "title": title,
                        "chunk_idx": idx,
                        "chunk_total": len(chunks),
                        "mtime": mtime,
                    },
                )
            )
            total_chunks += 1

        if len(points) >= 64:
            client.upsert(collection_name=COLLECTION, points=points)
            points = []

    if points:
        client.upsert(collection_name=COLLECTION, points=points)

    info = client.get_collection(COLLECTION)
    print(
        f"[done] ingested {total_chunks} chunks from {len(files)} files; "
        f"collection points={info.points_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=DEFAULT_DIRS,
        help="KB subdirs to ingest (relative to project root)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop + recreate the collection (default: upsert only)",
    )
    args = parser.parse_args()

    _ensure_deps()
    ingest(args.dirs, args.rebuild)


if __name__ == "__main__":
    main()
