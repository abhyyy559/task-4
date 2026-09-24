"""Policy-gated action executor: the ONLY path to side-effect APIs.

Flow: policy.decide() -> "execute" (route auto): call the mock API;
"recommend" (route L1/L2): record the recommendation WITHOUT side effects --
a human must approve first. Unknown actions raise PolicyError (never silent).

Returns (action_record, policy_decision).
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from src.actions import mock_apis
from src.agent import policy as policy_mod

_engine: policy_mod.PolicyEngine | None = None


def get_engine() -> policy_mod.PolicyEngine:
    global _engine
    if _engine is None:
        _engine = policy_mod.PolicyEngine()
    return _engine


def execute(
    action: str,
    target: Any,
    context: dict[str, Any] | None = None,
    engine: policy_mod.PolicyEngine | None = None,
    **kwargs: Any,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    eng = engine or get_engine()
    decision = eng.decide(action, context or {})
    if decision["decision"] == "execute":
        fn = mock_apis.MOCK_APIS.get(action)
        if fn is None:
            record = {
                "action": action,
                "target": str(target),
                "status": "error:unknown-api",
                "policy_ref": decision["rule"],
            }
            return record, decision
        try:
            result = fn(target, **kwargs) if kwargs else fn(target)
            record = {
                "action": action,
                "target": str(target),
                "status": result.get("status", "ok"),
                "policy_ref": decision["rule"],
                "ref": result.get("ref", ""),
            }
        except Exception as exc:
            record = {
                "action": action,
                "target": str(target),
                "status": f"error:{type(exc).__name__}: {exc}",
                "policy_ref": decision["rule"],
            }
        return record, decision
    # L1/L2: recommendation only -- no side effects without human approval.
    record = {
        "action": action,
        "target": str(target),
        "status": f"recommended:{decision['route']}:awaiting-human-approval",
        "policy_ref": decision["rule"],
    }
    return record, decision
