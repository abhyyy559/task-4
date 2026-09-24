"""Fraud Policy v1.0 enforcement (HHGOA TigerGraph task).

Single, coherent module-level API over config/policies.yaml:

- load_policies()            cached, validated policy document
- get_route(action, ...)     'auto' | 'L1' | 'L2' (BLOCK_CARD is exposure-conditional)
- requires_approval(action, ...)  True when the route is L1 or L2
- check_action(action, ...)  {action, route, requires_approval, approver}
- decide(action, context)     {action, decision, route, rule, reason}
- sar_required(...)          SAR filing requirement per policy section 3a
- should_open_case(...)      case-open rule per policy section 3a

Only `auto` actions may be executed by the agent; L1/L2 actions are
*recommended* with the route stated and wait for a human. Unknown actions
raise PolicyError. Nothing here fails silently: a missing/invalid config
raises at load time.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES_PATH = REPO_ROOT / "config" / "policies.yaml"

KNOWN_ACTIONS = (
    "ALLOW_TRANSACTION",
    "DECLINE_TRANSACTION",
    "MONITOR_CARD",
    "MONITOR_CONNECTED_CARDS",
    "WARN_CUSTOMER",
    "VERIFY_WITH_CUSTOMER",
    "STEP_UP_AUTH",
    "BLOCK_CARD",
    "BLOCK_ALL_CARDS",
    "GENERATE_REPORT",
    "CREATE_CASE",
    "FILE_REPORT",
    "ESCALATE_TO_ANALYST",
    "CLOSE_NO_FRAUD",
)

AUTO_ACTIONS = (
    "ALLOW_TRANSACTION",
    "MONITOR_CARD",
    "MONITOR_CONNECTED_CARDS",
    "WARN_CUSTOMER",
    "VERIFY_WITH_CUSTOMER",
    "STEP_UP_AUTH",
    "GENERATE_REPORT",
    "CREATE_CASE",
    "ESCALATE_TO_ANALYST",
    "CLOSE_NO_FRAUD",
)

_APPROVER = {"auto": "agent", "L1": "team_lead", "L2": "fraud_manager"}


class PolicyError(ValueError):
    """Raised for unknown actions or an invalid policy document."""


@lru_cache(maxsize=1)
def load_policies(path: Optional[str] = None) -> Dict[str, Any]:
    """Load and validate the fraud policy document (cached).

    Raises PolicyError when the file is missing, invalid YAML, or does not
    define exactly the 14 official actions.
    """
    target = Path(path) if path else POLICIES_PATH
    if not target.exists():
        raise PolicyError(f"policy file not found: {target}")
    try:
        doc = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # never fail silently on a bad policy
        raise PolicyError(f"invalid policy YAML in {target}: {exc}") from exc
    if not isinstance(doc, dict):
        raise PolicyError(f"policy document must be a mapping: {target}")
    actions = doc.get("actions", {})
    missing = [a for a in KNOWN_ACTIONS if a not in actions]
    extra = [a for a in actions if a not in KNOWN_ACTIONS]
    if missing or extra:
        raise PolicyError(
            "policy must define exactly the 14 official actions "
            f"(missing={missing}, extra={extra})"
        )
    return doc


def get_route(action: str, exposure_usd: float = 0.0) -> str:
    """Return the approval route for an action: 'auto', 'L1', or 'L2'.

    BLOCK_CARD is exposure-conditional per the policy: L1 when
    exposure_usd <= 2500, otherwise L2.
    """
    if action not in KNOWN_ACTIONS:
        raise PolicyError(f"unknown action: {action!r}")
    if action == "BLOCK_CARD":
        policies = load_policies()
        limit = float(
            policies.get("sar", {}).get("block_card_l1_exposure_limit_usd", 2500)
        )
        return "L1" if float(exposure_usd) <= limit else "L2"
    if action in AUTO_ACTIONS:
        return "auto"
    if action == "DECLINE_TRANSACTION":
        return "L1"
    return "L2"  # BLOCK_ALL_CARDS, FILE_REPORT


def requires_approval(action: str, exposure_usd: float = 0.0) -> bool:
    """True when the action's route is L1 or L2 (human approval required)."""
    return get_route(action, exposure_usd) != "auto"


def get_approver(action: str, exposure_usd: float = 0.0) -> str:
    """Return the approver role for an action's route."""
    return _APPROVER[get_route(action, exposure_usd)]


def check_action(action: str, exposure_usd: float = 0.0) -> Dict[str, Any]:
    """Pre-flight check for a proposed action.

    Returns {"action", "route", "requires_approval", "approver"}.
    Raises PolicyError for unknown actions.
    """
    route = get_route(action, exposure_usd)
    return {
        "action": action,
        "route": route,
        "requires_approval": route != "auto",
        "approver": _APPROVER[route],
    }


def decide(action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Decide what the agent may do with a proposed action.

    decision is one of:
      - "execute":   route is auto; the agent may act alone
      - "recommend": route is L1/L2; record the recommendation, wait for a human

    Unknown actions raise PolicyError (never silently denied).
    `context` may carry rule ("R1".."R10"), exposure_usd, and reason.
    """
    ctx = dict(context or {})
    route = get_route(action, float(ctx.get("exposure_usd", 0.0)))
    return {
        "action": action,
        "decision": "execute" if route == "auto" else "recommend",
        "route": route,
        "approver": _APPROVER[route],
        "rule": ctx.get("rule", ""),
        "reason": ctx.get("reason", ""),
    }


def sar_required(
    fraud_probability: float,
    exposure_usd: float,
    shared_origin: bool = False,
    pattern: str = "none",
    strongly_suspected: bool = False,
) -> bool:
    """SAR requirement per policy section 3a.

    File when fraud is confirmed or strongly suspected AND at least one of:
      - exposure exceeds $1,000
      - activity connects to a shared device profile / shared region cluster /
        another customer's fraud
      - the pattern is coordinated or undocumented (R9)
    """
    policies = load_policies()
    threshold = float(policies.get("sar", {}).get("exposure_threshold_usd", 1000))
    confirmed_or_suspected = fraud_probability >= 0.85 or bool(strongly_suspected)
    if not confirmed_or_suspected:
        return False
    return (
        float(exposure_usd) > threshold
        or bool(shared_origin)
        or pattern == "undocumented"
    )


def should_open_case(
    fraud_probability: float,
    evidence_requested: bool = False,
    customer_dispute: bool = False,
) -> bool:
    """Case-open rule per policy section 3a: open whenever fraud probability
    reaches 0.30, whenever evidence is requested, or whenever a customer
    disputes a charge."""
    policies = load_policies()
    threshold = float(policies.get("case_open_threshold", 0.30))
    return (
        float(fraud_probability) >= threshold
        or bool(evidence_requested)
        or bool(customer_dispute)
    )


class PolicyEngine:
    """Object-oriented facade over the module-level policy API."""

    def __init__(self, policies_path: Optional[str] = None):
        self.policies = load_policies(policies_path)

    def route(self, action: str, exposure_usd: float = 0.0) -> str:
        return get_route(action, exposure_usd)

    def requires_approval(self, action: str, exposure_usd: float = 0.0) -> bool:
        return requires_approval(action, exposure_usd)

    def check(self, action: str, exposure_usd: float = 0.0) -> Dict[str, Any]:
        return check_action(action, exposure_usd)

    def decide(
        self, action: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return decide(action, context)

    def sar_required(self, *args: Any, **kwargs: Any) -> bool:
        return sar_required(*args, **kwargs)

    def should_open_case(self, *args: Any, **kwargs: Any) -> bool:
        return should_open_case(*args, **kwargs)

    def rule_text(self, rule: str) -> str:
        rules = self.policies.get("rules", {})
        entry = rules.get(rule)
        if entry is None:
            raise PolicyError(f"unknown rule: {rule!r}")
        return entry.get("text", "")

    def allowed_actions(self) -> List[str]:
        return list(KNOWN_ACTIONS)
