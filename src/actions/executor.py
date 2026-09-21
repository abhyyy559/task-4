"""Policy-gated action executor: the ONLY path to side-effect APIs.

Flow: PolicyEngine.decide() -> allow: call mock API; deny/escalate: record
without side effects. Returns (action_record, policy_decision) where the
action record matches the OUTPUT_SCHEMA actions_taken item
({action, target, status, policy_ref}) and the decision matches
policy_decisions ({action, decision, rule}).
"""
from __future__ import annotations

from typing import Any

from src.actions import mock_apis
from src.agent.policy import PolicyEngine

_engine: PolicyEngine | None = None


def get_engine() -> PolicyEngine:
    global _engine
    if _engine is None:
        _engine = PolicyEngine()
    return _engine


def execute(action: str, target: Any, context: dict[str, Any],
            engine: PolicyEngine | None = None, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    eng = engine or get_engine()
    decision = eng.decide(action, context)
    if decision["decision"] == "allow":
        fn = mock_apis.MOCK_APIS.get(action)
        if fn is None:
            record = {"action": action, "target": str(target), "status": "error:unknown-api",
                      "policy_ref": decision["rule"]}
            return record, decision
        try:
            result = fn(target, **kwargs) if kwargs else fn(target)
            record = {"action": action, "target": str(target), "status": result.get("status", "ok"),
                      "policy_ref": decision["rule"], "ref": result.get("ref", "")}
        except Exception as exc:
            record = {"action": action, "target": str(target),
                      "status": f"error:{type(exc).__name__}: {exc}", "policy_ref": decision["rule"]}
        return record, decision
    record = {"action": action, "target": str(target),
              "status": f"blocked:{decision['decision']}", "policy_ref": decision["rule"]}
    return record, decision
