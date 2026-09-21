"""GraphRAG ingest: chunk docs -> hashed char-trigram vectors -> JSON store.

Offline by design: no sklearn, no numpy required (numpy optional, unused
here), no API keys, no network. Embeddings are deterministic hashed
character-trigram vectors (hashlib.md5 -> DIM buckets, L2-normalised), so
ingest and retrieval agree without a shared vocabulary file.

Corpus: ``data/HHGOA_IEEE/patterns.md`` plus ``config/policies.yaml`` when
present (skipped otherwise). Store: ``data/graphrag_store.json`` with shape
``{"chunks": [{"doc", "chunk_id", "text", "vector"}]}``.

CLI: ``python -m src.graphrag.ingest_docs``.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERNS_MD = ROOT / "data" / "HHGOA_IEEE" / "patterns.md"
POLICIES_YAML = ROOT / "config" / "policies.yaml"
DOCS_DIR = ROOT / "docs"
STORE_PATH = ROOT / "data" / "graphrag_store.json"
# Previous iteration of this module wrote a TF/vocab store here; the
# retriever still reads it as a legacy fallback.
LEGACY_STORE_PATH = ROOT / "data" / "vector_store.json"

DIM = 256
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

TOKEN_RE = re.compile(r"[a-z0-9_]+")
HEADING_RE = re.compile(r"^##\s+PATTERN\s+(\S+)", re.MULTILINE)


def tokenize(text: str) -> list[str]:
    """Word tokens (kept for backward compatibility with TF-based callers)."""
    return TOKEN_RE.findall(text.lower())


def char_trigrams(text: str) -> list[str]:
    """Normalised character trigrams used as embedding features."""
    norm = re.sub(r"\s+", " ", text.lower()).strip()
    if len(norm) < 3:
        return [norm] if norm else []
    return [norm[i:i + 3] for i in range(len(norm) - 2)]


def embed(text: str, dim: int = DIM) -> list[float]:
    """Deterministic hashed-trigram embedding, L2-normalised.

    No numpy/sklearn: bucket = md5(trigram) % dim, then L2 normalise.
    """
    counts: dict[int, float] = {}
    for tri in char_trigrams(text):
        bucket = int.from_bytes(hashlib.md5(tri.encode("utf-8")).digest()[:4], "big") % dim
        counts[bucket] = counts.get(bucket, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    vec = [0.0] * dim
    for bucket, cnt in counts.items():
        vec[bucket] = round(cnt / norm, 6)
    return vec


def chunk_text(text: str, doc: str, chunk_prefix: str,
               size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict[str, str]]:
    """Sliding-window char chunks (~size chars, overlap chars) with word-boundary snap."""
    text = text.strip()
    if not text:
        return []
    chunks: list[dict[str, str]] = []
    start, idx = 0, 0
    step = max(size - overlap, 1)
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):  # snap to word boundary
            snap = text.rfind(" ", start, end)
            if snap > start + size // 2:
                end = snap
        piece = text[start:end].strip()
        if piece:
            chunks.append({"doc": doc, "chunk_id": f"{chunk_prefix}-c{idx}", "text": piece})
            idx += 1
        if end >= len(text):
            break
        start += step
    return chunks


def chunk_patterns(path: Path = PATTERNS_MD) -> list[dict[str, str]]:
    """One chunk-group per PATTERN section, sub-chunked to ~500 chars."""
    text = path.read_text(encoding="utf-8")
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        raise ValueError(f"no PATTERN sections found in {path}")
    chunks: list[dict[str, str]] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        name = match.group(1).lower()
        sub = chunk_text(section, path.name, name)
        chunks.extend(sub or [{"doc": path.name, "chunk_id": name, "text": section}])
    return chunks


def chunk_policies(path: Path = POLICIES_YAML) -> list[dict[str, str]]:
    """Chunk policies.yaml when present, else return [] (explicit skip)."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return chunk_text(text, path.name, path.stem)


def chunk_docs(docs_dir: Path = DOCS_DIR) -> list[dict[str, str]]:
    """Chunk extra .md docs (kept for backward compatibility; optional corpus)."""
    chunks: list[dict[str, str]] = []
    if not docs_dir.exists():
        return chunks
    for md in sorted(docs_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i, para in enumerate(paras):
            chunks.extend(chunk_text(para, md.name, f"{md.stem}-p{i}"))
    return chunks


def build_store(chunks: list[dict[str, str]], dim: int = DIM) -> dict:
    """Attach hashed-trigram vectors to chunks."""
    out = []
    for ch in chunks:
        out.append({"doc": ch["doc"], "chunk_id": ch["chunk_id"],
                    "text": ch["text"], "vector": embed(ch["text"], dim)})
    return {"dim": dim, "chunks": out}


def ingest(patterns_md: Path = PATTERNS_MD, docs_dir: Path | None = None,
           store_path: Path = STORE_PATH,
           policies_yaml: Path = POLICIES_YAML) -> dict:
    """Chunk patterns.md (+ policies.yaml if present) and persist the store."""
    if not Path(patterns_md).exists():
        raise FileNotFoundError(f"patterns corpus missing: {patterns_md}")
    chunks = chunk_patterns(Path(patterns_md))
    policy_chunks = chunk_policies(Path(policies_yaml))
    chunks.extend(policy_chunks)
    if docs_dir is not None and Path(docs_dir).exists():
        chunks.extend(chunk_docs(Path(docs_dir)))
    if not chunks:
        raise ValueError("no chunks to ingest")
    store = build_store(chunks)
    store_path = Path(store_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(store, indent=1), encoding="utf-8")
    return {"chunks": len(chunks), "policy_chunks": len(policy_chunks),
            "dim": DIM, "store": str(store_path)}


def main() -> None:
    result = ingest()
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
