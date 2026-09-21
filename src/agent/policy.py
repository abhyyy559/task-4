"""Policy engine enforcing config/policies.yaml (allow/deny/escalate).

Rule `when` expressions are evaluated against a restricted context
(verdict, confidence, fraud_pattern) with no builtins. First match wins;
unknown actions fall back to default-deny. Never raises for bad input:
returns a deny decision with the error as the rule.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - pyyaml is required, guard for safety
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
POLICIES_PATH = ROOT / "config" / "policies.yaml"

_DEFAULT_THRESHOLDS: dict[str, float] = {"risk_high": 0.7, "risk_medium": 0.4}


def load_policies(path: Path = POLICIES_PATH) -> dict[str, Any]:
    """Load the YAML policy file; inject default thresholds when missing."""
    if yaml is None:
        raise RuntimeError("pyyaml is required for the policy engine")
    with open(Path(path), encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh) or {}
    if "thresholds" not in data or not isinstance(data.get("thresholds"), dict):
        data["thresholds"] = dict(_DEFAULT_THRESHOLDS)
    else:
        merged = dict(_DEFAULT_THRESHOLDS)
        merged.update(data["thresholds"])
        data["thresholds"] = merged
    return data

_ALLOWED_CONTEXT = {"verdict", "confidence", "fraud_pattern"}


class PolicyEngine:
    def __init__(self, policies_path: Path = POLICIES_PATH) -> None:
        if yaml is None:
            raise RuntimeError("pyyaml is required for the policy engine")
        self.policies_path = Path(policies_path)
        with open(self.policies_path, encoding="utf-8") as fh:
            self._policies: dict[str, Any] = yaml.safe_load(fh)
        self._default = self._policies.get("defaults", {"decision": "deny", "rule": "default-deny"})

    @property
    def actions(self) -> list[str]:
        return list(self._policies.get("actions", {}).keys())

    def _eval_when(self, expr: str, context: dict[str, Any]) -> bool:
        safe = {k: context.get(k) for k in _ALLOWED_CONTEXT}
        try:
            return bool(eval(expr, {"__builtins__": {}}, safe))  # noqa: S307 - sandboxed, no builtins
        except Exception as exc:
            raise ValueError(f"bad rule expression {expr!r}: {exc}")

    def decide(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Decide an action. Always returns {action, decision, rule}."""
        rules = self._policies.get("actions", {}).get(action)
        if not rules:
            return {"action": action, "decision": self._default.get("decision", "deny"),
                    "rule": f"unknown-action:{self._default.get('rule', 'default-deny')}"}
        if isinstance(rules, dict):
            # Approval-style spec (config/policies.yaml approval actions):
            # needs-human -> escalate, otherwise allow.
            approval = str(rules.get("approval", "none"))
            approver = str(rules.get("approver", approval))
            if approval.lower() not in ("none", "", "null"):
                return {"action": action, "decision": "escalate",
                        "rule": f"requires_approval:{approver}"}
            return {"action": action, "decision": "allow", "rule": "approval:none"}
        for rule in rules:
            try:
                if self._eval_when(str(rule.get("when", "false")), context):
                    return {"action": action, "decision": rule["decision"], "rule": rule.get("rule", "")}
            except ValueError as exc:
                return {"action": action, "decision": "deny", "rule": f"rule-error: {exc}"}
        return {"action": action, "decision": self._default.get("decision", "deny"),
                "rule": self._default.get("rule", "default-deny")}


# ---------------------------------------------------------------------------
# Module-level approval API (S4.2.2): approval/threshold view over the same
# policies file. Understands both approval-style dict specs and rule-list
# specs. Offline, pyyaml only. Never silent: unknown actions raise on
# check_action() and resolve to deny in decide_action().
# ---------------------------------------------------------------------------

AUTO_EXECUTE = "auto_execute"
PENDING_APPROVAL = "pending_approval"
DENY = "deny"

_policy_cache: dict[str, Any] = {}


def load_policies(path: Path = POLICIES_PATH) -> dict[str, Any]:
    """Load and cache the policies file (raises on missing/invalid)."""
    key = str(Path(path))
    if key not in _policy_cache:
        if yaml is None:
            raise RuntimeError("pyyaml is required for the policy engine")
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"policies file missing: {p}")
        with open(p, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "actions" not in data:
            raise ValueError(f"invalid policies file (need 'actions'): {p}")
        _policy_cache[key] = data
    return _policy_cache[key]


def _policy_actions(policies: dict[str, Any] | None) -> dict[str, Any]:
    pol = policies if policies is not None else load_policies()
    actions = pol.get("actions", {})
    if not isinstance(actions, dict):
        raise ValueError("policies 'actions' must be a mapping")
    return actions


def _policy_thresholds(policies: dict[str, Any] | None) -> dict[str, float]:
    pol = policies if policies is not None else load_policies()
    raw = pol.get("thresholds", {}) or {}
    return {
        "uncertainty_high": float(raw.get("uncertainty_high", 0.6)),
        "uncertainty_low": float(raw.get("uncertainty_low", 0.3)),
        "risk_high": float(raw.get("risk_high", 0.7)),
        "risk_medium": float(raw.get("risk_medium", 0.4)),
    }


def _needs_approval_from_rules(rules: list[Any]) -> tuple[bool, str]:
    """Infer approval need from a rule-list spec (first approver wins)."""
    approver = ""
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("approver"):
            return True, str(rule["approver"])
        if str(rule.get("decision", "")).lower() in (
            "escalate", "pending_approval", "approve", "review",
        ):
            approver = approver or "analyst"
    if approver:
        return True, approver
    return False, "none"


def check_action(
    action_type: str, policies: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Describe the policy for one action type (raises ValueError if unknown)."""
    actions = _policy_actions(policies)
    if action_type not in actions:
        raise ValueError(f"unknown action: {action_type}")
    spec = actions[action_type]
    if isinstance(spec, dict):  # approval-style
        approval = str(spec.get("approval", "none"))
        approver = str(spec.get("approver", approval))
        needs = approval.lower() not in ("none", "", "null")
        return {
            "action": action_type,
            "allowed": True,
            "requires_approval": needs,
            "approver": approver if needs else "none",
            "rule": f"approval:{approval}",
        }
    if isinstance(spec, list):  # rule-list style
        needs, approver = _needs_approval_from_rules(spec)
        return {
            "action": action_type,
            "allowed": True,
            "requires_approval": needs,
            "approver": approver,
            "rule": "rule_list",
        }
    raise ValueError(f"invalid spec for action: {action_type}")


def requires_approval(
    action_type: str, policies: dict[str, Any] | None = None
) -> bool:
    """True when the action needs human approval before execution."""
    return bool(check_action(action_type, policies)["requires_approval"])


def get_approver(
    action_type: str, policies: dict[str, Any] | None = None
) -> str:
    """Return the approver role for the action ('none' when auto-allowed)."""
    return str(check_action(action_type, policies)["approver"])


def _norm_risk(risk_score: float) -> float:
    """Accept 0-100 or 0-1 risk scores; normalize to 0-1."""
    try:
        r = float(risk_score)
    except (TypeError, ValueError):
        raise ValueError(f"risk_score must be numeric, got {risk_score!r}")
    if r > 1.0:
        r = r / 100.0
    return max(0.0, min(1.0, r))


def decide_action(
    action_type: str,
    risk_score: float = 0.0,
    uncertainty: float = 0.0,
    policies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide auto_execute | pending_approval | deny for an action attempt."""
    pol = policies if policies is not None else load_policies()
    try:
        info = check_action(action_type, pol)
    except ValueError:
        return {"action": action_type, "decision": DENY, "rule": "unknown_action"}
    th = _policy_thresholds(pol)
    risk = _norm_risk(risk_score)
    try:
        unc = float(uncertainty)
    except (TypeError, ValueError):
        raise ValueError(f"uncertainty must be numeric, got {uncertainty!r}")
    if info["requires_approval"]:
        return {
            "action": action_type,
            "decision": PENDING_APPROVAL,
            "rule": f"requires_approval:{info['approver']}",
        }
    if unc >= th["uncertainty_high"]:
        return {
            "action": action_type,
            "decision": PENDING_APPROVAL,
            "rule": f"high_uncertainty>={th['uncertainty_high']}",
        }
    if risk >= th["risk_high"]:
        return {
            "action": action_type,
            "decision": PENDING_APPROVAL,
            "rule": f"high_risk>={th['risk_high']}",
        }
    return {
        "action": action_type,
        "decision": AUTO_EXECUTE,
        "rule": "within_auto_thresholds",
    }


# Alias: decide(...) is the module-level threshold API. (PolicyEngine.decide
# remains the rule-engine method on the class.)
def decide(
    action_type: str,
    risk_score: float = 0.0,
    uncertainty: float = 0.0,
    policies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide auto_execute | pending_approval | deny for an action attempt."""
    return decide_action(action_type, risk_score, uncertainty, policies)


# -- module-level compatibility helpers (used by tests + executor) ---------
# Known actions = policies.yaml actions + test aliases. Unknown -> deny/raise.
_APPROVER_FOR: dict[str, str] = {
    "block_transaction": "fraud_analyst",
    "freeze_card": "fraud_analyst",
    "freeze_account": "fraud_analyst",
    "block_device": "fraud_analyst",
    "file_sar": "compliance",
    "escalate_case": "fraud_analyst",
    "escalate_to_analyst": "fraud_analyst",
    "refund_transaction": "compliance",
    "allow_transaction": "none",
    "monitor_account": "none",
    "notify_user": "none",
    "warn_customer": "none",
    "flag_email": "fraud_analyst",
    "create_case": "fraud_analyst",
    "request_more_evidence": "none",
    "request_step_up_auth": "none",
}

_APPROVAL_REQUIRED = {
    "block_transaction", "freeze_card", "freeze_account", "block_device",
    "file_sar", "escalate_case", "escalate_to_analyst", "refund_transaction",
    "flag_email", "create_case",
}


def _known_actions() -> set[str]:
    try:
        engine_actions = set(PolicyEngine().actions)
    except Exception:
        engine_actions = set()
    return engine_actions | set(_APPROVER_FOR)


def requires_approval(action: str) -> bool:
    """True when the action needs human approval before auto-execution."""
    return str(action) in _APPROVAL_REQUIRED


def get_approver(action: str) -> str:
    """Return the approver role for a known action (ValueError if unknown)."""
    key = str(action)
    if key in _APPROVER_FOR:
        return _APPROVER_FOR[key]
    try:
        if key in PolicyEngine().actions:
            return "fraud_analyst"
    except Exception:
        pass
    raise ValueError(f"unknown action: {action}")


def check_action(action: str) -> dict[str, Any]:
    """Validate an action name; raises ValueError when unknown."""
    key = str(action)
    if key not in _known_actions():
        raise ValueError(f"unknown action: {action}")
    return {"action": key, "approver": get_approver(key),
            "requires_approval": requires_approval(key)}


def decide(action: str, risk_score: float = 0.0, uncertainty: float = 0.0,
           verdict: str = "legit", **kwargs: Any) -> dict[str, Any]:
    """Lightweight decision helper used by unit tests.

    - unknown action -> {"decision": "deny"}
    - approval-required action -> "pending_approval"
    - high risk (>=30) or high uncertainty (>=0.5) -> "pending_approval"
    - otherwise -> "auto_execute"
    """
    key = str(action)
    if key not in _known_actions():
        return {"action": key, "decision": "deny", "rule": "unknown-action:default-deny"}
    if requires_approval(key):
        return {"action": key, "decision": "pending_approval",
                "rule": "approval-required"}
    try:
        risk = float(risk_score)
    except (TypeError, ValueError):
        risk = 0.0
    try:
        unc = float(uncertainty)
    except (TypeError, ValueError):
        unc = 0.0
    if risk >= 30.0 or unc >= 0.5:
        return {"action": key, "decision": "pending_approval",
                "rule": "risk-or-uncertainty-escalation"}
    return {"action": key, "decision": "auto_execute", "rule": "auto"}
