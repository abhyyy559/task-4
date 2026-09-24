"""Test isolation: redirect the mock CASE vertex store to a temp dir.

investigate() performs FR-12 graph write-back on every completed case.
Without this fixture, running the test suite pollutes data/graph_cases.json
with synthetic test cases (e.g. case_t01). Autouse so every test is covered.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_case_store(tmp_path, monkeypatch):
    import src.mcp.tools as tools

    client = tools.get_client()
    monkeypatch.setattr(client, "_case_store", tmp_path / "graph_cases.json")
    monkeypatch.setattr(client, "_cases", {})
    yield
