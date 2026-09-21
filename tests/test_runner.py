"""Runner tests: OUTPUT_SCHEMA contract + validate_output + run_case.

Validates the exact 16-field schema (PLAN.md section 4) and exercises
run_case on a small real case when cases/inputs/ exists (skips otherwise).
Offline; run_case writes cases/outputs/<case_id>.json as a side effect.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent import runner
from src.agent.runner import OUTPUT_SCHEMA, run_case, validate_output

EXPECTED_SCHEMA = [
    "case_id", "verdict", "fraud_pattern", "confidence", "risk_score",
    "evidence_ids", "transactions_reviewed", "entities_flagged",
    "graph_findings", "rag_citations", "actions_taken", "policy_decisions",
    "amounts", "timeline", "explanation", "recommended_next_steps",
]

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "cases" / "inputs"
OUTPUTS = ROOT / "cases" / "outputs"


def _good_record() -> dict:
    return {
        "case_id": "case_t99", "verdict": "fraud", "fraud_pattern": "account_takeover",
        "confidence": 0.9, "risk_score": 90.0, "evidence_ids": ["1013"],
        "transactions_reviewed": [1013], "entities_flagged": {"cards": []},
        "graph_findings": [], "rag_citations": [], "actions_taken": [],
        "policy_decisions": [], "amounts": {"total": 1.0, "max": 1.0, "currency": "USD"},
        "timeline": [], "explanation": "x", "recommended_next_steps": [],
    }


def test_output_schema_is_exact_16_fields():
    assert runner.OUTPUT_SCHEMA == EXPECTED_SCHEMA
    assert len(OUTPUT_SCHEMA) == 16


def test_validate_output_accepts_good_record():
    assert validate_output(_good_record()) == []


def test_validate_output_rejects_missing_fields():
    errors = validate_output({"case_id": "x"})
    assert any("missing field" in e for e in errors)
    assert len(errors) >= len(EXPECTED_SCHEMA) - 1


def test_validate_output_rejects_bad_verdict():
    rec = _good_record()
    rec["verdict"] = "maybe"
    assert any("bad verdict" in e for e in validate_output(rec))


def test_validate_output_rejects_fraud_without_evidence():
    rec = _good_record()
    rec["evidence_ids"] = []
    assert any("evidence_ids" in e for e in validate_output(rec))


def test_run_case_small_real_case():
    case_path = INPUTS / "case_01.json"
    if not case_path.exists():
        pytest.skip("cases/inputs/case_01.json not present yet")
    output = run_case("case_01")
    assert validate_output(output) == []
    assert output["verdict"] in ("fraud", "legit", "escalate")
    if output["verdict"] == "fraud":
        assert len(output["evidence_ids"]) >= 1
    written = OUTPUTS / "case_01.json"
    assert written.exists()
    assert json.loads(written.read_text(encoding="utf-8"))["case_id"] == "case_01"


def test_run_case_unknown_id_raises():
    with pytest.raises(FileNotFoundError):
        run_case("case_zz_does_not_exist")
