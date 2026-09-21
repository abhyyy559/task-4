"""Policy engine tests: allow / deny / escalate + default-deny + executor gating.

Covers src/agent/policy.py (PolicyEngine.decide) and src/actions/executor.py
(execute blocks non-allowed actions without touching mock APIs).
Offline, stdlib + pyyaml only.
"""
from __future__ import annotations

from src.actions import executor as executor_mod
from src.agent.policy import PolicyEngine

FRAUD_CTX = {"verdict": "fraud", "confidence": 0.9,
             "fraud_pattern": "card_not_present_ring"}
LEGIT_CTX = {"verdict": "legit", "confidence": 0.9, "fraud_pattern": None}


def _engine() -> PolicyEngine:
    return PolicyEngine()


def test_allow_high_confidence_fraud_freeze():
    eng = _engine()
    out = eng.decide("freeze_card", dict(FRAUD_CTX))
    assert out["action"] == "freeze_card"
    assert out["decision"] == "allow"
    assert out["rule"] == "freeze-fraud-confident"


def test_deny_freeze_on_legit():
    eng = _engine()
    out = eng.decide("freeze_card", dict(LEGIT_CTX))
    assert out["decision"] == "deny"


def test_escalate_low_confidence_fraud_freeze():
    eng = _engine()
    ctx = dict(FRAUD_CTX, confidence=0.5)
    out = eng.decide("freeze_card", ctx)
    assert out["decision"] == "escalate"
    assert out["rule"] == "freeze-fraud-unconfident"


def test_escalate_refund_needs_human_review():
    eng = _engine()
    out = eng.decide("refund_transaction", dict(FRAUD_CTX))
    assert out["decision"] == "escalate"
    assert out["rule"] == "refund-human-review"


def test_escalate_flag_email_on_escalate_verdict():
    eng = _engine()
    ctx = {"verdict": "escalate", "confidence": 0.5, "fraud_pattern": None}
    out = eng.decide("flag_email", ctx)
    assert out["decision"] == "escalate"


def test_deny_escalate_case_on_legit():
    eng = _engine()
    out = eng.decide("escalate_case", dict(LEGIT_CTX))
    assert out["decision"] == "deny"


def test_unknown_action_default_deny():
    eng = _engine()
    out = eng.decide("launch_missiles", dict(FRAUD_CTX))
    assert out["decision"] == "deny"
    assert out["rule"].startswith("unknown-action:")


def test_decide_never_raises_on_bad_input():
    eng = _engine()
    for ctx in ({}, {"verdict": None}, {"confidence": "high"}):
        out = eng.decide("freeze_card", dict(ctx))
        assert set(out) == {"action", "decision", "rule"}
        assert out["decision"] in ("allow", "deny", "escalate")


def test_executor_refuses_denied_action_without_side_effect():
    # Empty target would raise ValueError in the mock API; a blocked record
    # proves the mock was never called (direct mock calls forbidden).
    record, decision = executor_mod.execute("freeze_card", "", dict(LEGIT_CTX))
    assert decision["decision"] == "deny"
    assert record["status"] == "blocked:deny"
    assert record["policy_ref"] == decision["rule"]


def test_executor_refuses_escalated_action_without_side_effect():
    record, decision = executor_mod.execute(
        "refund_transaction", "1001", dict(FRAUD_CTX))
    assert decision["decision"] == "escalate"
    assert record["status"] == "blocked:escalate"


def test_executor_runs_allowed_action_through_mock_api():
    record, decision = executor_mod.execute(
        "notify_user", "cust-1", dict(LEGIT_CTX))
    assert decision["decision"] == "allow"
    assert record["status"] == "ok"
    assert record["target"] == "cust-1"
