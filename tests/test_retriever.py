"""GraphRAG retriever tests: ingest patterns.md, then per-pattern search.

Asserts each of the 5 fraud pattern names ranks its own chunk top-1.
Offline: hashed-trigram vectors, no sklearn, no network.
"""
from __future__ import annotations

from pathlib import Path

from src.graphrag.ingest_docs import STORE_PATH, ingest
from src.graphrag.retriever import Retriever

PATTERNS = [
    "card_not_present_ring",
    "account_takeover",
    "money_mule_fanout",
    "device_spoofing_cluster",
    "synthetic_identity",
]


def test_ingest_builds_store():
    result = ingest()
    assert result["chunks"] > 0
    assert Path(result["store"]) == STORE_PATH
    assert STORE_PATH.exists()


def test_each_pattern_retrieves_own_chunk_top1():
    retriever = Retriever()
    for pattern in PATTERNS:
        hits = retriever.search(f"{pattern} fraud signals", k=3)
        assert hits, f"no hits for {pattern}"
        assert hits[0]["chunk_id"].startswith(pattern), (
            f"top hit for {pattern} was {hits[0]['chunk_id']}"
        )


def test_search_hit_shape():
    retriever = Retriever()
    hits = retriever.search("card_not_present_ring fraud signals", k=1)
    assert len(hits) == 1
    assert set(hits[0]) == {"doc", "chunk_id", "score", "text"}
    assert hits[0]["doc"] == "patterns.md"
    assert hits[0]["score"] > 0
