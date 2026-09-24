"""GraphRAG retriever tests: ingest patterns.md, then per-pattern search.

Asserts each official fraud pattern name ranks its own chunk top-1.
Offline: hashed-trigram vectors, no sklearn, no network.
"""
from __future__ import annotations

from pathlib import Path

from src.graphrag.ingest_docs import STORE_PATH, ingest
from src.graphrag.retriever import Retriever

PATTERNS = [
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
]


def test_ingest_builds_store():
    result = ingest()
    assert result["chunks"] > 0
    assert Path(result["store"]) == STORE_PATH
    assert STORE_PATH.exists()


def test_each_pattern_retrieves_own_chunk_top1():
    retriever = Retriever()
    for pattern in PATTERNS:
        hits = retriever.search(f"PATTERN {pattern}", k=3)
        assert hits, f"no hits for {pattern}"
        assert pattern in hits[0]["text"], (
            f"top hit for {pattern} does not mention it: "
            f"{hits[0]['text'][:80]}"
        )
