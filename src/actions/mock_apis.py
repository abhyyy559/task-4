"""Simulated enforcement / notification APIs (offline, stdlib only).

Functions are named with the EXACT official action identifiers from Fraud
Policy v1.0 (config/policies.yaml). Only `auto`-route actions are ever
dispatched here by src/actions/executor.py; L1/L2 actions are recorded as
recommendations awaiting human approval and never reach these functions.

Every function is side-effect free, deterministic apart from its unique
ticket/ref id, and raises on empty targets (never silent failure).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import uuid as _uuid
from typing import Any


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _ref(action: str, target: Any) -> str:
    digest = hashlib.sha1(f"{action}:{target}".encode()).hexdigest()[:8].upper()
    return f"{action[:3].upper()}-{digest}"


def _ticket(action: str) -> str:
    return f"{action.upper()}-{_uuid.uuid4().hex[:8]}"


def _require(target: Any, action: str) -> str:
    if target is None or str(target).strip() == "":
        raise ValueError(f"{action} requires a non-empty target")
    return str(target)


def _result(action: str, target: Any, **extra: Any) -> dict[str, Any]:
    target = _require(target, action)
    return {
        "status": "simulated",
        "action": action,
        "target": target,
        "timestamp": _now_iso(),
        "ticket_id": _ticket(action),
        **extra,
    }


# -- official actions: auto route (agent may execute) ------------------------


def ALLOW_TRANSACTION(transaction_id: Any) -> dict[str, Any]:
    """Let the flagged transaction stand."""
    return _result("ALLOW_TRANSACTION", transaction_id)


def MONITOR_CARD(card_id: Any, hours: int = 72) -> dict[str, Any]:
    """Raise monitoring sensitivity on a card for 72 hours."""
    return _result("MONITOR_CARD", card_id, hours=hours)


def MONITOR_CONNECTED_CARDS(card_ids: Any) -> dict[str, Any]:
    """Put linked cards under monitoring."""
    ids = card_ids if isinstance(card_ids, list) else [card_ids]
    return _result("MONITOR_CONNECTED_CARDS", ",".join(str(i) for i in ids))


def WARN_CUSTOMER(customer_ref: Any, message: str = "") -> dict[str, Any]:
    """Send an informational message to the customer."""
    return _result("WARN_CUSTOMER", customer_ref, message=message)


def VERIFY_WITH_CUSTOMER(customer_ref: Any, transaction_id: Any = "") -> dict[str, Any]:
    """Ask the cardholder whether they made the transaction."""
    return _result(
        "VERIFY_WITH_CUSTOMER", customer_ref, transaction_id=str(transaction_id)
    )


def STEP_UP_AUTH(customer_ref: Any, method: str = "otp") -> dict[str, Any]:
    """Require a one-time passcode or app confirmation."""
    if method not in ("otp", "webauthn", "call"):
        raise ValueError(f"STEP_UP_AUTH: unknown method {method!r}")
    return _result("STEP_UP_AUTH", customer_ref, method=method)


def GENERATE_REPORT(case_ref: Any, summary: str = "") -> dict[str, Any]:
    """Write up the investigation for the internal record (no case opened)."""
    return _result("GENERATE_REPORT", case_ref, summary=summary)


def CREATE_CASE(case_id: Any, summary: str = "") -> dict[str, Any]:
    """Open an internal fraud case with the evidence attached."""
    return _result("CREATE_CASE", case_id, summary=summary)


def ESCALATE_TO_ANALYST(case_id: Any, summary: str = "") -> dict[str, Any]:
    """Hand the case to a human analyst with the evidence."""
    return _result("ESCALATE_TO_ANALYST", case_id, summary=summary)


def CLOSE_NO_FRAUD(alert_ref: Any, note: str = "") -> dict[str, Any]:
    """Close the alert as legitimate."""
    return _result("CLOSE_NO_FRAUD", alert_ref, note=note)


# -- official actions: L1/L2 route (recommendation only; never dispatched) ---


def DECLINE_TRANSACTION(transaction_id: Any) -> dict[str, Any]:
    """Decline the flagged authorization only. Card stays active."""
    return _result("DECLINE_TRANSACTION", transaction_id)


def BLOCK_CARD(card_id: Any, reason: str = "") -> dict[str, Any]:
    """Block a card and reissue."""
    return _result("BLOCK_CARD", card_id, reason=reason)


def BLOCK_ALL_CARDS(customer_id: Any, reason: str = "") -> dict[str, Any]:
    """Block every card the customer holds."""
    return _result("BLOCK_ALL_CARDS", customer_id, reason=reason)


def FILE_REPORT(case_id: Any, amount: float = 0.0, narrative: str = "") -> dict[str, Any]:
    """File a suspicious activity report with the regulator."""
    if amount < 0:
        raise ValueError("FILE_REPORT: amount must be >= 0")
    return _result("FILE_REPORT", case_id, amount=float(amount), narrative=narrative)


MOCK_APIS = {
    "ALLOW_TRANSACTION": ALLOW_TRANSACTION,
    "DECLINE_TRANSACTION": DECLINE_TRANSACTION,
    "MONITOR_CARD": MONITOR_CARD,
    "MONITOR_CONNECTED_CARDS": MONITOR_CONNECTED_CARDS,
    "WARN_CUSTOMER": WARN_CUSTOMER,
    "VERIFY_WITH_CUSTOMER": VERIFY_WITH_CUSTOMER,
    "STEP_UP_AUTH": STEP_UP_AUTH,
    "BLOCK_CARD": BLOCK_CARD,
    "BLOCK_ALL_CARDS": BLOCK_ALL_CARDS,
    "GENERATE_REPORT": GENERATE_REPORT,
    "CREATE_CASE": CREATE_CASE,
    "FILE_REPORT": FILE_REPORT,
    "ESCALATE_TO_ANALYST": ESCALATE_TO_ANALYST,
    "CLOSE_NO_FRAUD": CLOSE_NO_FRAUD,
}

# Alias for compatibility.
ACTIONS = MOCK_APIS
