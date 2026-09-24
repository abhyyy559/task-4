"""Policy tests: official 14 actions, auto/L1/L2 routes, R1-R10 wiring.

Covers src/agent/policy.py (module-level API + PolicyEngine) and
src/actions/executor.py (only `auto` actions execute; L1/L2 are recorded
as recommendations; unknown actions raise, never fail silently).
Offline, stdlib + pyyaml only.
"""
from __future__ import annotations

import pytest

from src.actions import executor as executor_mod
from src.agent import policy as policy_mod
from src.agent.policy import PolicyEngine, PolicyError


def test_exactly_14_official_actions():
    assert list(policy_mod.KNOWN_ACTIONS) == [
        "ALLOW_TRANSACTION", "DECLINE_TRANSACTION", "MONITOR_CARD",
        "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER",
        "STEP_UP_AUTH", "BLOCK_CARD", "BLOCK_ALL_CARDS", "GENERATE_REPORT",
        "CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD",
    ]


def test_auto_routes():
    for action in ("ALLOW_TRANSACTION", "MONITOR_CARD", "MONITOR_CONNECTED_CARDS",
                   "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH",
                   "GENERATE_REPORT", "CREATE_CASE", "ESCALATE_TO_ANALYST",
                   "CLOSE_NO_FRAUD"):
        assert policy_mod.get_route(action) == "auto", action
        assert not policy_mod.requires_approval(action)


def test_l1_l2_routes():
    assert policy_mod.get_route("DECLINE_TRANSACTION") == "L1"
    assert policy_mod.get_route("BLOCK_ALL_CARDS") == "L2"
    assert policy_mod.get_route("FILE_REPORT") == "L2"
    assert policy_mod.requires_approval("FILE_REPORT")


def test_block_card_route_is_exposure_conditional():
    assert policy_mod.get_route("BLOCK_CARD", 2500) == "L1"
    assert policy_mod.get_route("BLOCK_CARD", 2500.01) == "L2"
    assert policy_mod.get_route("BLOCK_CARD", 0) == "L1"


def test_unknown_action_raises():
    with pytest.raises(PolicyError):
        policy_mod.get_route("freeze_card")
    with pytest.raises(PolicyError):
        policy_mod.check_action("nope")


def test_decide_execute_vs_recommend():
    d = policy_mod.decide("VERIFY_WITH_CUSTOMER", {"rule": "R1"})
    assert d["decision"] == "execute" and d["route"] == "auto"
    d = policy_mod.decide("BLOCK_CARD", {"exposure_usd": 100, "rule": "R2"})
    assert d["decision"] == "recommend" and d["route"] == "L1"
    d = policy_mod.decide("FILE_REPORT", {"rule": "R6"})
    assert d["decision"] == "recommend" and d["route"] == "L2"


def test_sar_required_rule():
    # confirmed fraud + exposure > 1000 -> file
    assert policy_mod.sar_required(0.9, 1500) is True
    # confirmed fraud but low exposure and no shared origin -> no file
    assert policy_mod.sar_required(0.9, 200) is False
    # shared origin qualifies even at moderate exposure
    assert policy_mod.sar_required(0.9, 200, shared_origin=True) is True
    # undocumented pattern qualifies (R9)
    assert policy_mod.sar_required(0.9, 200, pattern="undocumented") is True
    # not confirmed/strongly suspected -> never file
    assert policy_mod.sar_required(0.4, 5000) is False


def test_should_open_case():
    assert policy_mod.should_open_case(0.30) is True
    assert policy_mod.should_open_case(0.29) is False
    assert policy_mod.should_open_case(0.10, evidence_requested=True) is True
    assert policy_mod.should_open_case(0.10, customer_dispute=True) is True


def test_engine_facade():
    eng = PolicyEngine()
    assert eng.route("CLOSE_NO_FRAUD") == "auto"
    assert eng.requires_approval("BLOCK_ALL_CARDS") is True
    assert eng.decide("WARN_CUSTOMER", {})["decision"] == "execute"
    assert eng.sar_required(0.95, 2000) is True
    assert eng.should_open_case(0.5) is True
    assert "verify" in eng.rule_text("R1").lower()
    with pytest.raises(PolicyError):
        eng.rule_text("R99")


def test_executor_runs_auto_actions_only():
    record, decision = executor_mod.execute(
        "VERIFY_WITH_CUSTOMER", "C12382", {"rule": "R1"}
    )
    assert decision["decision"] == "execute"
    assert record["status"] == "simulated"


def test_executor_records_l1_l2_without_side_effects():
    record, decision = executor_mod.execute(
        "BLOCK_CARD", "C12382-K1", {"rule": "R2", "exposure_usd": 100}
    )
    assert decision["decision"] == "recommend"
    assert decision["route"] == "L1"
    assert record["status"].startswith("recommended:L1")
    record, decision = executor_mod.execute("FILE_REPORT", "HHG-001", {"rule": "R6"})
    assert decision["route"] == "L2"
    assert "awaiting-human-approval" in record["status"]


def test_executor_rejects_unknown_action():
    with pytest.raises(PolicyError):
        executor_mod.execute("freeze_card", "x", {})
