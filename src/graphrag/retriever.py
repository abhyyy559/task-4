"""Lightweight retriever over the hashed-trigram JSON store.

Cosine similarity on L2-normalised vectors; numpy when importable, pure
Python otherwise. If the store is missing, vectors are rebuilt in-memory
from ``patterns.md`` so retrieval still works offline. Never raises on a
missing store: falls back to the in-memory rebuild (which raises only when
the corpus itself is absent).

Public API: :func:`retrieve_context` plus the backward-compatible
:class:`Retriever` (with ``search`` and ``retrieve`` methods).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

try:
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _np = None

from src.graphrag.ingest_docs import (
    LEGACY_STORE_PATH,
    PATTERNS_MD,
    POLICIES_YAML,
    STORE_PATH,
    chunk_patterns,
    chunk_policies,
    embed,
    tokenize,
)

_DEFAULT_STORE = STORE_PATH

# ~2000 tokens ~= ~7000 chars for this corpus; cap the context block there.
MAX_CONTEXT_CHARS = 7000


def _cosine_numpy(qvec: list[float], mats: Any) -> list[float]:
    import numpy as np  # local import: _np may be the same module

    q = np.asarray(qvec, dtype=float)
    denom = float(np.linalg.norm(q)) or 1.0
    q = q / denom
    scores = mats @ q
    return [float(s) for s in scores]


def _cosine_pure(qvec: list[float], chunk_vecs: list[list[float]]) -> list[float]:
    qnorm = math.sqrt(sum(v * v for v in qvec)) or 1.0
    q = [v / qnorm for v in qvec]
    scores = []
    for cvec in chunk_vecs:
        cnorm = math.sqrt(sum(v * v for v in cvec)) or 1.0
        scores.append(sum(a * b for a, b in zip(q, cvec)) / cnorm)
    return scores


class Retriever:
    def __init__(self, store_path: Path = _DEFAULT_STORE) -> None:
        self.store_path = Path(store_path)
        self._is_default = Path(store_path) == Path(_DEFAULT_STORE)
        self._store: dict[str, Any] | None = None
        self._mem_chunks: list[dict[str, Any]] | None = None

    # -- loading ---------------------------------------------------------
    def _load(self) -> dict[str, Any] | None:
        if self._store is None:
            # Explicit custom path that does not exist: strict miss -> None
            # (test_missing_store_returns_empty). Default path falls back to
            # legacy store, then in-memory rebuild for offline use.
            if not self._is_default and not Path(self.store_path).exists():
                return None
            candidates = (self.store_path, LEGACY_STORE_PATH) if self._is_default else (self.store_path,)
            for candidate in candidates:
                if Path(candidate).exists():
                    try:
                        self._store = json.loads(Path(candidate).read_text(encoding="utf-8"))
                        break
                    except (OSError, ValueError):
                        continue
        return self._store

    def _memory_chunks(self) -> list[dict[str, Any]]:
        """Rebuild chunk vectors in-memory when no store file exists."""
        if self._mem_chunks is None:
            chunks: list[dict[str, Any]] = [
                dict(ch) for ch in chunk_patterns(PATTERNS_MD)
            ]
            chunks.extend(dict(ch) for ch in chunk_policies(POLICIES_YAML))
            for ch in chunks:
                ch["vector"] = embed(ch["text"])
            self._mem_chunks = chunks
        return self._mem_chunks

    def _chunk_vectors(self) -> tuple[list[dict[str, Any]], list[list[float]]]:
        store = self._load()
        if store is None and not self._is_default:
            return [], []
        if store and store.get("chunks") and isinstance(store["chunks"][0].get("vector"), list):
            chunks = store["chunks"]
            return chunks, [list(map(float, c["vector"])) for c in chunks]
        if store and store.get("vocab"):  # legacy TF/vocab store fallback
            return self._legacy_chunks(store)
        chunks = self._memory_chunks()
        return chunks, [list(map(float, c["vector"])) for c in chunks]

    def _legacy_chunks(
        self, store: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[list[float]]]:
        """Score path for the previous TF/vocab store format (compat only)."""
        from src.graphrag.ingest_docs import DIM

        vocab = store["vocab"]
        index = {tok: i for i, tok in enumerate(vocab)}
        chunks = store["chunks"]
        vecs = []
        for vec in store["vectors"]:
            dense = [0.0] * len(vocab)
            for dim, val in vec.items():
                dense[int(dim)] = float(val)
            vecs.append(dense)
        # Pad/truncate note: legacy dim differs from hashed DIM; search()
        # handles it by re-embedding the query as TF over the legacy vocab.
        self._legacy_index = index  # stash for search()
        _ = DIM
        return chunks, vecs

    # -- scoring ----------------------------------------------------------
    def _score(self, query: str, chunks: list[dict[str, Any]],
               vecs: list[list[float]]) -> list[tuple[float, dict[str, Any]]]:
        legacy_index = getattr(self, "_legacy_index", None)
        if legacy_index is not None:  # legacy TF query vector
            from collections import Counter

            qtokens = [t for t in tokenize(query) if t in legacy_index]
            if not qtokens:
                return []
            counts = Counter(qtokens)
            norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
            qvec = [0.0] * len(legacy_index)
            for tok, cnt in counts.items():
                qvec[legacy_index[tok]] = cnt / norm
        else:
            qvec = embed(query)
        if _np is not None:
            try:
                import numpy as np

                mats = np.asarray(vecs, dtype=float)
                scores = _cosine_numpy(qvec, mats)
            except Exception:
                scores = _cosine_pure(qvec, vecs)
        else:
            scores = _cosine_pure(qvec, vecs)
        scored = sorted(zip(scores, chunks), key=lambda s: s[0], reverse=True)
        if hasattr(self, "_legacy_index"):
            delattr(self, "_legacy_index")
        return scored

    # -- public API --------------------------------------------------------
    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Backward-compatible search: top-k hits with text + score."""
        chunks, vecs = self._chunk_vectors()
        scored = self._score(query, chunks, vecs)
        return [{"doc": ch["doc"], "chunk_id": ch["chunk_id"],
                 "score": round(score, 4), "text": ch["text"][:500]}
                for score, ch in scored[:k] if score > 0]

    def retrieve(self, query: str, top_k: int = 3,
                 graph_evidence: list[str] | None = None) -> dict[str, Any]:
        """Compact context block + citations for the agent investigator."""
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        hits = self.search(query, k=top_k)
        lines = [f"# Fraud pattern context (query: {query.strip()})"]
        for hit in hits:
            lines.append(f"\n## {hit['doc']}::{hit['chunk_id']} (score {hit['score']})")
            lines.append(hit["text"])
        if graph_evidence:
            lines.append("\n## Graph evidence")
            lines.append(", ".join(str(e) for e in graph_evidence))
        context = "\n".join(lines)
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS].rsplit(" ", 1)[0] + "\n[truncated]"
        citations = [{"doc": h["doc"], "chunk_id": h["chunk_id"], "score": h["score"]}
                     for h in hits]
        return {"context": context, "rag_citations": citations}


def retrieve_context(query: str, graph_evidence: list[str] | None = None,
                     top_k: int = 3) -> dict[str, Any]:
    """Load the store (or rebuild in-memory) and return context + citations.

    Returns ``{"context": str, "rag_citations": [{doc, chunk_id, score}]}``
    where ``context`` is capped at ~2000 tokens.
    """
    return Retriever().retrieve(query, top_k=top_k, graph_evidence=graph_evidence)
