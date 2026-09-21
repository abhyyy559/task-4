"""Simulated enforcement / notification APIs (offline, stdlib only).

Two name families are exposed (merged for cross-worker compatibility):

- Spec family (S4.4.1): ``freeze_account``, ``block_card``,
  ``notify_customer``, ``escalate_to_analyst``, ``file_sar``,
  ``step_up_auth`` — return
  ``{status: simulated, action, target, timestamp, ticket_id}``.
- Executor family: ``freeze_card``, ``block_device``, ``flag_email``,
  ``notify_user``, ``escalate_case``, ``refund_transaction`` — return
  ``{action, target, status: ok, ref, timestamp, ticket_id}`` and are
  dispatched via ``MOCK_APIS`` by ``src/actions/executor.py``.

Every function is deterministic apart from its unique ticket/ref id, is
side-effect free, and raises on empty targets (never silent failure).
Actual side-effect gating lives in ``src/actions/policy.py`` +
``src/actions/executor.py``; agent code must call those, not this module.
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


# -- executor family (dispatched via MOCK_APIS) ----------------------------

def freeze_card(card: Any) -> dict[str, Any]:
    card = _require(card, "freeze_card")
    return {"action": "freeze_card", "target": card, "status": "ok",
            "ref": _ref("freeze_card", card), "timestamp": _now_iso(),
            "ticket_id": _ticket("freeze_card")}


def block_device(device: Any) -> dict[str, Any]:
    device = _require(device, "block_device")
    return {"action": "block_device", "target": device, "status": "ok",
            "ref": _ref("block_device", device), "timestamp": _now_iso(),
            "ticket_id": _ticket("block_device")}


def flag_email(email: Any) -> dict[str, Any]:
    email = _require(email, "flag_email")
    return {"action": "flag_email", "target": email, "status": "ok",
            "ref": _ref("flag_email", email), "timestamp": _now_iso(),
            "ticket_id": _ticket("flag_email")}


def notify_user(user: Any, message: str = "") -> dict[str, Any]:
    user = _require(user, "notify_user")
    return {"action": "notify_user", "target": user, "status": "ok",
            "ref": _ref("notify_user", user), "message": message,
            "timestamp": _now_iso(), "ticket_id": _ticket("notify_user")}


def escalate_case(case_id: Any, reason: str = "") -> dict[str, Any]:
    case_id = _require(case_id, "escalate_case")
    return {"action": "escalate_case", "target": str(case_id), "status": "ok",
            "ref": _ref("escalate_case", case_id), "reason": reason,
            "timestamp": _now_iso(), "ticket_id": _ticket("escalate_case")}


def refund_transaction(transaction_id: Any) -> dict[str, Any]:
    transaction_id = _require(transaction_id, "refund_transaction")
    return {"action": "refund_transaction", "target": str(transaction_id),
            "status": "ok", "ref": _ref("refund_transaction", transaction_id),
            "timestamp": _now_iso(), "ticket_id": _ticket("refund_transaction")}


# -- spec family (S4.4.1) ----------------------------------------------------

def _result(action: str, target: Any, **extra: Any) -> dict[str, Any]:
    target = _require(target, action)
    return {"status": "simulated", "action": action, "target": target,
            "timestamp": _now_iso(), "ticket_id": _ticket(action), **extra}


def freeze_account(account_id: Any, reason: str = "") -> dict[str, Any]:
    """Simulate freezing an account."""
    return _result("freeze_account", account_id, reason=reason)


def block_card(card1: Any, reason: str = "") -> dict[str, Any]:
    """Simulate blocking a card."""
    return _result("block_card", card1, reason=reason)


def notify_customer(customer_ref: Any, channel: str = "email",
                    message: str = "") -> dict[str, Any]:
    """Simulate notifying a customer (email/sms/push)."""
    if channel not in ("email", "sms", "push"):
        raise ValueError(f"notify_customer: unknown channel {channel!r}")
    return _result("notify_customer", customer_ref, channel=channel, message=message)


def escalate_to_analyst(case_id: Any, summary: str = "") -> dict[str, Any]:
    """Simulate escalating a case to a human analyst."""
    return _result("escalate_to_analyst", case_id, summary=summary)


def file_sar(subject_ref: Any, amount: float = 0.0,
             narrative: str = "") -> dict[str, Any]:
    """Simulate filing a Suspicious Activity Report."""
    if amount < 0:
        raise ValueError("file_sar: amount must be >= 0")
    return _result("file_sar", subject_ref, amount=float(amount), narrative=narrative)


def step_up_auth(customer_ref: Any, method: str = "otp") -> dict[str, Any]:
    """Simulate triggering step-up authentication (otp/webauthn/call)."""
    if method not in ("otp", "webauthn", "call"):
        raise ValueError(f"step_up_auth: unknown method {method!r}")
    return _result("step_up_auth", customer_ref, method=method)


MOCK_APIS = {
    "freeze_card": freeze_card,
    "block_device": block_device,
    "flag_email": flag_email,
    "notify_user": notify_user,
    "escalate_case": escalate_case,
    "refund_transaction": refund_transaction,
    "freeze_account": freeze_account,
    "block_card": block_card,
    "notify_customer": notify_customer,
    "escalate_to_analyst": escalate_to_analyst,
    "file_sar": file_sar,
    "step_up_auth": step_up_auth,
}

# Alias used by the S4.4.1 spec surface.
ACTIONS = MOCK_APIS
