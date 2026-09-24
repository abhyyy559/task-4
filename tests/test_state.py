"""Answer-format tests: official schema validation + edge cases.

Covers src/agent/state.py validate_output: top-level fields, case/sar/
next_best_actions shapes, enum values, SAR internal consistency, and the
FILE_REPORT <-> sar.file agreement rule.
"""
from __future__ import annotations

from src.agent.state import (
    PATTERNS,
    REQUIRED_OUTPUT_FIELDS,
    STATUSES,
    VERDICTS,
    validate_output,
)


def _good_answer() -> dict:
    return {
        "case_id": "HHG-001",
        "case": {
            "status": "closed_fraud",
            "verdict": "fraud",
            "fraud_probability": 0.9,
            "pattern": "card_not_present_fraud",
            "pattern_description": "",
            "affected_txn_ids": ["3514030"],
            "first_suspicious_txn_id": "3514030",
            "connected_card_ids": [],
            "connected_device_profiles": [],
            "exposure_usd": 77.07,
            "evidence": [
                {
                    "claim": "flagged txn is online and inconsistent with history",
                    "source": "graph",
                    "ref": "q_card_history",
                    "entity_ids": ["3514030"],
                }
            ],
            "similar_prior_cases": ["CC-0001"],
            "summary": "Fraud episode identified.",
            "written_to_graph": True,
            "graph_case_id": "CASE-HHG-001",
        },
        "evidence_requests": [
            {
                "type": "customer_validation",
                "asked_after_step": 9,
                "assumed_response": "Customer denies the transaction",
            }
        ],
        "next_best_actions": {
            "initial": [
                {"action": "VERIFY_WITH_CUSTOMER", "route": "auto",
                 "reason": "R1: verify before block"}
            ],
            "final": [
                {"action": "BLOCK_CARD", "route": "L1", "reason": "R2: denied"},
                {"action": "CREATE_CASE", "route": "auto", "reason": "R2"},
            ],
            "what_changed": "customer denied",
        },
        "sar": {
            "file": False,
            "reason": "3a: exposure <= $1,000 and no shared origin",
            "narrative": "",
            "subjects": [],
            "total_amount_usd": 0,
            "activity_dates": [],
        },
        "stop_reason": "Fraud probability 0.90 >= 0.85 with 2+ evidence items",
        "tool_calls": 8,
        "tokens": 0,
        "latency_s": 1.23,
    }


def test_top_level_fields_exact():
    assert REQUIRED_OUTPUT_FIELDS == [
        "case_id", "case", "evidence_requests", "next_best_actions",
        "sar", "stop_reason", "tool_calls", "tokens", "latency_s",
    ]


def test_good_answer_validates():
    assert validate_output(_good_answer()) == []


def test_missing_top_level_field():
    ans = _good_answer()
    del ans["sar"]
    errors = validate_output(ans)
    assert any("sar" in e for e in errors)


def test_bad_enums_rejected():
    ans = _good_answer()
    ans["case"]["verdict"] = "fraudulent"
    ans["case"]["status"] = "pending"
    ans["case"]["pattern"] = "card_not_present_ring"
    errors = validate_output(ans)
    assert len(errors) == 3
    assert set(VERDICTS) == {"fraud", "legitimate", "uncertain"}
    assert set(STATUSES) == {
        "open", "closed_fraud", "closed_legitimate", "escalated",
    }
    assert set(PATTERNS) == {
        "card_testing", "card_not_present_fraud",
        "card_not_present_new_device", "out_of_region_use",
        "account_takeover", "undocumented", "none",
    }


def test_legitimate_requires_empty_exposure():
    ans = _good_answer()
    ans["case"]["verdict"] = "legitimate"
    ans["case"]["status"] = "closed_legitimate"
    errors = validate_output(ans)
    assert any("affected_txn_ids" in e for e in errors)
    assert any("exposure_usd" in e for e in errors)


def test_undocumented_requires_description():
    ans = _good_answer()
    ans["case"]["pattern"] = "undocumented"
    errors = validate_output(ans)
    assert any("pattern_description" in e for e in errors)
    ans["case"]["pattern_description"] = "Coordinated abuse across cards."
    assert validate_output(ans) == []


def test_sar_file_false_requires_empty_fields():
    ans = _good_answer()
    ans["sar"]["narrative"] = "oops"
    errors = validate_output(ans)
    assert any("narrative" in e for e in errors)


def test_file_report_must_agree_with_sar_file():
    ans = _good_answer()
    ans["next_best_actions"]["final"].append(
        {"action": "FILE_REPORT", "route": "L2", "reason": "3a"}
    )
    errors = validate_output(ans)
    assert any("sar.file must agree" in e for e in errors)
    ans["sar"]["file"] = True
    ans["sar"]["reason"] = "3a: exposure exceeds $1,000"
    ans["sar"]["narrative"] = "Who what when where how why. " * 3
    ans["sar"]["subjects"] = ["C12382"]
    ans["sar"]["total_amount_usd"] = 1500.0
    ans["sar"]["activity_dates"] = ["2016-12-05", "2016-12-05"]
    assert validate_output(ans) == []


def test_final_must_equal_initial_when_nothing_requested():
    ans = _good_answer()
    ans["evidence_requests"] = []
    errors = validate_output(ans)
    assert any("final" in e and "initial" in e for e in errors)


def test_bad_evidence_source_rejected():
    ans = _good_answer()
    ans["case"]["evidence"][0]["source"] = "vibes"
    errors = validate_output(ans)
    assert any("source" in e for e in errors)
