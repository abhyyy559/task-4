"""Graph / orchestrator single-case tests on real stub TransactionIDs.

Runs src/agent/graph.py:investigate_case over stub IDs [1001, 1002] and
checks the verdict domain, evidence citation, and the full 16-field
OUTPUT_SCHEMA via src/agent/runner.py:to_output_json + validate_output.
Offline (mock TigerGraph client over data/HHGOA_IEEE/*.csv).
"""
from __future__ import annotations

from typing import Any

from src.agent.graph import investigate_case
from src.agent.runner import OUTPUT_SCHEMA, to_output_json, validate_output

CASE: dict[str, Any] = {
    "case_id": "case_t01",
    "pattern": "card_not_present_ring",
    "label": "fraud",
    "description": "test ring slice",
    "subject": {"card1": 411111, "account_id": "A-ring-test"},
    "transaction_ids": [1001, 1002],
    "signals": {},
    "expected": {"verdict": "fraud", "min_confidence": 0.7},
}


def _output() -> dict[str, Any]:
    state = investigate_case(dict(CASE))
    return to_output_json(dict(CASE), state)


def test_verdict_in_domain():
    state = investigate_case(dict(CASE))
    assert state.get("verdict") in ("fraud", "legit", "escalate")


def test_output_has_all_16_schema_fields():
    output = _output()
    assert validate_output(output) == []
    for field in OUTPUT_SCHEMA:
        assert field in output
    assert len(OUTPUT_SCHEMA) == 16


def test_evidence_ids_cited_when_fraud():
    output = _output()
    if output["verdict"] == "fraud":
        assert len(output["evidence_ids"]) >= 1
        for eid in output["evidence_ids"]:
            assert str(eid).strip() != ""


def test_transactions_reviewed_echo_input_ids():
    output = _output()
    assert sorted(int(t) for t in output["transactions_reviewed"]) == [1001, 1002]


def test_graph_findings_shape():
    output = _output()
    assert isinstance(output["graph_findings"], list)
    assert len(output["graph_findings"]) >= 1
    for finding in output["graph_findings"]:
        assert set(finding) == {"query", "summary", "node_count"}


def test_rag_citations_shape():
    output = _output()
    assert isinstance(output["rag_citations"], list)
    for cite in output["rag_citations"]:
        assert {"doc", "chunk_id", "score"} <= set(cite)


def test_amounts_and_timeline_present():
    output = _output()
    assert set(output["amounts"]) == {"total", "max", "currency"}
    assert output["amounts"]["currency"] == "USD"
    assert isinstance(output["timeline"], list)
    assert len(output["timeline"]) == len(output["transactions_reviewed"])
    assert isinstance(output["explanation"], str) and output["explanation"].strip()
    assert isinstance(output["recommended_next_steps"], list)
