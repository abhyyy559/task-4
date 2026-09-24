"""Investigation state schema + official answer contract.

The answer format below is the OFFICIAL HHGOA TigerGraph task format
(transcribed 2026-09-21 from the official dataset README.md, "Answer Format"
section; see TASK-PLAN-APPENDIX-README.md). One JSON file per case, named
<case_id>.json, in a folder called cases/.

Top level: case_id, case{...}, evidence_requests[...], next_best_actions{...},
sar{...}, stop_reason, tool_calls, tokens, latency_s.

Verdicts: fraud | legitimate | uncertain.
Statuses: open | closed_fraud | closed_legitimate | escalated.
Patterns: card_testing | card_not_present_fraud | card_not_present_new_device |
          out_of_region_use | account_takeover | undocumented | none.
"""
from __future__ import annotations

from typing import Any, List, Optional, TypedDict

# Canonical top-level answer fields — exact order from the README field table.
REQUIRED_OUTPUT_FIELDS: List[str] = [
    "case_id",
    "case",
    "evidence_requests",
    "next_best_actions",
    "sar",
    "stop_reason",
    "tool_calls",
    "tokens",
    "latency_s",
]

# Part 1: the case record.
REQUIRED_CASE_FIELDS: List[str] = [
    "status",
    "verdict",
    "fraud_probability",
    "pattern",
    "pattern_description",
    "affected_txn_ids",
    "first_suspicious_txn_id",
    "connected_card_ids",
    "connected_device_profiles",
    "exposure_usd",
    "evidence",
    "similar_prior_cases",
    "summary",
    "written_to_graph",
    "graph_case_id",
]

# Part 2: the suspicious activity report.
REQUIRED_SAR_FIELDS: List[str] = [
    "file",
    "reason",
    "narrative",
    "subjects",
    "total_amount_usd",
    "activity_dates",
]

# Part 3: the next best action.
REQUIRED_NBA_FIELDS: List[str] = [
    "initial",
    "final",
    "what_changed",
]

# Evidence item shape: {claim, source, ref, entity_ids}.
REQUIRED_EVIDENCE_FIELDS: List[str] = ["claim", "source", "ref", "entity_ids"]

# Evidence request item shape: {type, asked_after_step, assumed_response}.
REQUIRED_EVIDENCE_REQUEST_FIELDS: List[str] = [
    "type",
    "asked_after_step",
    "assumed_response",
]

# Next-best-action item shape: {action, route, reason}.
REQUIRED_NBA_ITEM_FIELDS: List[str] = ["action", "route", "reason"]

VERDICTS = ("fraud", "legitimate", "uncertain")
STATUSES = ("open", "closed_fraud", "closed_legitimate", "escalated")
PATTERNS = (
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
    "none",
)
EVIDENCE_SOURCES = ("graph", "document", "customer", "external")
EVIDENCE_REQUEST_TYPES = ("customer_validation", "step_up_auth", "analyst_info")
ACTION_ROUTES = ("auto", "L1", "L2")


class InvestigationState(TypedDict, total=False):
    """LangGraph-compatible investigation state for one HHG case."""

    case_id: str
    case_input: dict  # row from case_pack.csv: flagged txn, card, customer, trigger
    status: str
    verdict: str
    fraud_probability: float
    pattern: str
    pattern_description: str
    affected_txn_ids: List[str]
    first_suspicious_txn_id: str
    connected_card_ids: List[str]
    connected_device_profiles: List[str]
    exposure_usd: float
    evidence: List[dict]
    evidence_requests: List[dict]
    similar_prior_cases: List[str]
    summary: str
    written_to_graph: bool
    graph_case_id: str
    sar: dict
    next_best_actions: dict
    stop_reason: str
    tool_calls: int
    tokens: int
    latency_s: float


def validate_output(record: dict) -> List[str]:
    """Validate an answer record against the official answer format.

    Returns a list of human-readable error strings; empty means valid.
    Checks: top-level fields, case/sar/next_best_actions shapes, enum values,
    evidence item shapes, and SAR internal consistency (file=false implies
    empty narrative/subjects/dates and zero amount; FILE_REPORT in final
    actions must agree with sar.file).
    """
    errors: List[str] = []
    if not isinstance(record, dict):
        return ["record must be an object"]

    for field in REQUIRED_OUTPUT_FIELDS:
        if field not in record:
            errors.append(f"missing top-level field: {field}")

    case = record.get("case")
    if isinstance(case, dict):
        for field in REQUIRED_CASE_FIELDS:
            if field not in case:
                errors.append(f"missing case field: {field}")
        if case.get("status") not in STATUSES:
            errors.append(f"invalid case.status: {case.get('status')!r}")
        if case.get("verdict") not in VERDICTS:
            errors.append(f"invalid case.verdict: {case.get('verdict')!r}")
        prob = case.get("fraud_probability")
        if not isinstance(prob, (int, float)) or not 0 <= prob <= 1:
            errors.append(f"fraud_probability must be 0-1, got {prob!r}")
        if case.get("pattern") not in PATTERNS:
            errors.append(f"invalid case.pattern: {case.get('pattern')!r}")
        if case.get("pattern") == "undocumented" and not case.get(
            "pattern_description"
        ):
            errors.append("pattern_description required when pattern=undocumented")
        if case.get("verdict") == "legitimate":
            if case.get("affected_txn_ids"):
                errors.append("legitimate verdict requires empty affected_txn_ids")
            if float(case.get("exposure_usd", 0) or 0) != 0:
                errors.append("legitimate verdict requires exposure_usd=0")
        evidence = case.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append("case.evidence must be a list")
        else:
            for i, item in enumerate(evidence):
                if not isinstance(item, dict):
                    errors.append(f"evidence[{i}] must be an object")
                    continue
                for field in REQUIRED_EVIDENCE_FIELDS:
                    if field not in item:
                        errors.append(f"evidence[{i}] missing field: {field}")
                if item.get("source") not in EVIDENCE_SOURCES:
                    errors.append(
                        f"evidence[{i}].source invalid: {item.get('source')!r}"
                    )
    elif "case" in record:
        errors.append("case must be an object")

    requests = record.get("evidence_requests", [])
    if isinstance(requests, list):
        for i, item in enumerate(requests):
            if not isinstance(item, dict):
                errors.append(f"evidence_requests[{i}] must be an object")
                continue
            for field in REQUIRED_EVIDENCE_REQUEST_FIELDS:
                if field not in item:
                    errors.append(f"evidence_requests[{i}] missing field: {field}")
            if item.get("type") not in EVIDENCE_REQUEST_TYPES:
                errors.append(
                    f"evidence_requests[{i}].type invalid: {item.get('type')!r}"
                )

    nba = record.get("next_best_actions")
    if isinstance(nba, dict):
        for field in REQUIRED_NBA_FIELDS:
            if field not in nba:
                errors.append(f"missing next_best_actions field: {field}")
        for section in ("initial", "final"):
            items = nba.get(section, [])
            if not isinstance(items, list):
                errors.append(f"next_best_actions.{section} must be a list")
                continue
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(f"next_best_actions.{section}[{i}] must be object")
                    continue
                for field in REQUIRED_NBA_ITEM_FIELDS:
                    if field not in item:
                        errors.append(
                            f"next_best_actions.{section}[{i}] missing: {field}"
                        )
                if item.get("route") not in ACTION_ROUTES:
                    errors.append(
                        f"next_best_actions.{section}[{i}].route invalid: "
                        f"{item.get('route')!r}"
                    )
        if not requests and nba.get("final") != nba.get("initial"):
            errors.append(
                "no evidence requested: next_best_actions.final must equal initial"
            )
    elif "next_best_actions" in record:
        errors.append("next_best_actions must be an object")

    sar = record.get("sar")
    if isinstance(sar, dict):
        for field in REQUIRED_SAR_FIELDS:
            if field not in sar:
                errors.append(f"missing sar field: {field}")
        file_sar = sar.get("file")
        if file_sar is False:
            if sar.get("narrative"):
                errors.append("sar.file=false requires empty narrative")
            if sar.get("subjects"):
                errors.append("sar.file=false requires empty subjects")
            if float(sar.get("total_amount_usd", 0) or 0) != 0:
                errors.append("sar.file=false requires total_amount_usd=0")
            if sar.get("activity_dates"):
                errors.append("sar.file=false requires empty activity_dates")
        # FILE_REPORT in final actions must agree with sar.file
        if isinstance(nba, dict) and isinstance(nba.get("final"), list):
            final_actions = [
                a.get("action") for a in nba["final"] if isinstance(a, dict)
            ]
            if ("FILE_REPORT" in final_actions) != bool(file_sar):
                errors.append(
                    "sar.file must agree with FILE_REPORT in next_best_actions.final"
                )
    elif "sar" in record:
        errors.append("sar must be an object")

    return errors
