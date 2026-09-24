"""Runner tests: official answer contract + run_case on HHG inputs.

Exercises src.agent.runner.run_case against the synthetic fallback dataset
(HHGOA_DATA_DIR unset and real data absent): the flagged HHG txns are not in
the stub, so each case must yield the honest fallback answer, which must
validate against the official format. Answers are written to a temp dir, not
cases/, to keep the working tree clean.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent import runner
from src.agent.runner import OUTPUT_SCHEMA, list_cases, run_case
from src.agent.state import REQUIRED_OUTPUT_FIELDS, validate_output
from src.data.hhgoa import HHGOAStore
from src.tigergraph.client import TigerGraphClient

ROOT = Path(__file__).resolve().parents[1]


def test_output_schema_matches_official_top_level():
    assert OUTPUT_SCHEMA == REQUIRED_OUTPUT_FIELDS
    assert OUTPUT_SCHEMA == [
        "case_id", "case", "evidence_requests", "next_best_actions",
        "sar", "stop_reason", "tool_calls", "tokens", "latency_s",
    ]


def test_list_cases_finds_20_hhg_inputs():
    cases = list_cases()
    assert len(cases) == 20
    assert cases[0].stem == "HHG-001" and cases[-1].stem == "HHG-020"


def _fallback_store() -> HHGOAStore:
    store = HHGOAStore(ROOT / "data" / "HHGOA_IEEE")
    assert store.is_fallback
    return store.load()


def test_run_case_fallback_answer_validates(tmp_path):
    store = _fallback_store()
    case_input = json.loads(
        (ROOT / "cases" / "inputs" / "HHG-001.json").read_text(encoding="utf-8")
    )
    answer = run_case(case_input, store, client=None)
    assert answer["case_id"] == "HHG-001"
    assert validate_output(answer) == []
    # fallback honesty: no invented verdict
    assert answer["case"]["verdict"] == "uncertain"
    out = tmp_path / "HHG-001.json"
    out.write_text(json.dumps(answer, indent=1), encoding="utf-8")
    assert json.loads(out.read_text())["case_id"] == "HHG-001"


def test_case_inputs_have_official_ids():
    data = json.loads(
        (ROOT / "cases" / "inputs" / "HHG-014.json").read_text(encoding="utf-8")
    )
    assert data["flagged_txn_id"] == "3478561"
    assert data["card_id"] == "C13487-K1"
    assert data["customer_id"] == "C13487"
    assert data["trigger_type"] == "analyst_request"
    assert "device profile" in data["trigger_text"]
