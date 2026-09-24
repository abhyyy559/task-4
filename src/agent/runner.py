"""Benchmark runner: cases/inputs/*.json -> cases/outputs/*.json.

Each output validates against OUTPUT_SCHEMA (exact 16 fields, PLAN.md section 4).
Usage: `python -m src.agent.runner --all` or `python -m src.agent.runner --case case_01`.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from src.agent.state import REQUIRED_OUTPUT_FIELDS

OUTPUT_SCHEMA: list[str] = list(REQUIRED_OUTPUT_FIELDS)

ROOT = Path(__file__).resolve().parents[2]
CASES_IN = ROOT / "cases" / "inputs"
CASES_OUT = ROOT / "cases" / "outputs"
CASES_ROOT = ROOT / "cases"
# Backward-compat aliases.
INPUTS = CASES_IN
OUTPUTS = CASES_OUT

_HHG_RE = re.compile(r"(\d+)")


def hhg_id(case_id: str) -> str:
    """Map internal case_NN ids to submission naming: case_01 -> HHG-001."""
    digits = _HHG_RE.findall(str(case_id))
    if not digits:
        raise ValueError(f"cannot derive HHG id from case_id: {case_id}")
    return f"HHG-{int(digits[-1]):03d}"


def write_hhg_files(case_id: str, enriched: dict[str, Any]) -> list[Path]:
    """Write the submission answer file at cases/HHG-0NN.json (repo root,
    per the submission form contract)."""
    hhg = hhg_id(case_id)
    payload = json.dumps(enriched, indent=1)
    dest = CASES_ROOT / f"{hhg}.json"
    dest.write_text(payload, encoding="utf-8")
    return [dest]


def _fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_output_json(case: dict[str, Any], state: Any) -> dict[str, Any]:
    transactions = state.get("transactions", []) or []
    tids = [str(t.get("TransactionID")) for t in transactions]
    evidence = [str(e) for e in _evidence_from_state(case, state)]

    cards = sorted({str(t.get("card1")) for t in transactions if t.get("card1")})
    devices = sorted({str(t.get("DeviceInfo")) for t in transactions if t.get("DeviceInfo")})
    emails = sorted({str(t.get("P_emaildomain")) for t in transactions if t.get("P_emaildomain")}
                    | {str(t.get("R_emaildomain")) for t in transactions if t.get("R_emaildomain")})
    accounts = [case.get("subject", {}).get("account_id")] if case.get("subject", {}).get("account_id") else []

    amts = [_fnum(t.get("TransactionAmt")) for t in transactions]
    timeline = sorted(
        ({"dt": int(_fnum(t.get("TransactionDT"))),
          "event": f"TXN {t.get('TransactionID')} amt={t.get('TransactionAmt')} card={t.get('card1')}"}
         for t in transactions),
        key=lambda e: e["dt"],
    )
    verdict = state.get("verdict", "escalate")
    steps = _next_steps(verdict, case)

    output = {
        "case_id": case.get("case_id", ""),
        "verdict": verdict,
        "fraud_pattern": case.get("pattern") if verdict == "fraud" else None,
        "confidence": float(state.get("confidence", 0.0)),
        "risk_score": float(state.get("risk_score", 0.0)),
        "evidence_ids": evidence,
        "transactions_reviewed": [int(t) if str(t).isdigit() else t for t in tids],
        "entities_flagged": {"cards": cards, "devices": devices, "emails": emails, "accounts": accounts},
        "graph_findings": [
            {"query": f.get("query", ""), "summary": f.get("summary", ""),
             "node_count": f.get("node_count", 0)}
            for f in (state.get("graph_findings", []) or [])
        ],
        "rag_citations": list(state.get("rag_citations", []) or []),
        "actions_taken": list(state.get("actions_taken", []) or []),
        "policy_decisions": list(state.get("policy_decisions", []) or []),
        "amounts": {"total": round(sum(amts), 2), "max": max(amts) if amts else 0.0, "currency": "USD"},
        "timeline": timeline,
        "explanation": _explain(case, state, evidence),
        "recommended_next_steps": steps,
    }
    return output


def _evidence_from_state(case: dict[str, Any], state: Any) -> list[str]:
    from src.agent.orchestrator import collect_evidence

    return collect_evidence(case, state.get("graph_findings", []) or [])[:20]


def _explain(case: dict[str, Any], state: Any, evidence: list[str]) -> str:
    from src.agent.orchestrator import build_explanation

    return build_explanation(
        case, state.get("verdict", "escalate"), state.get("confidence", 0.0),
        state.get("risk_signals", {}) or {}, evidence,
        state.get("rag_citations", []) or [])


def _next_steps(verdict: str, case: dict[str, Any]) -> list[str]:
    if verdict == "fraud":
        return ["confirm card freeze with cardholder",
                "analyst review of evidence_ids",
                "consider SAR filing / collect chargeback evidence pack"]
    if verdict == "escalate":
        return ["manual review of evidence_ids",
                "request step-up authentication from cardholder",
                "re-run after 24h of additional transactions"]
    return ["no action required", "continue monitoring baseline"]


def validate_output(output: dict[str, Any]) -> list[str]:
    """Return a list of schema violations (empty = valid)."""
    errors = []
    for field in OUTPUT_SCHEMA:
        if field not in output:
            errors.append(f"missing field: {field}")
    extra = [k for k in output if k not in OUTPUT_SCHEMA]
    if extra:
        errors.append(f"extra fields: {extra}")
    if output.get("verdict") not in ("fraud", "legit", "escalate"):
        errors.append(f"bad verdict: {output.get('verdict')}")
    if output.get("verdict") == "fraud" and not output.get("evidence_ids"):
        errors.append("fraud verdict requires non-empty evidence_ids")
    return errors


def run_case(case_id: str) -> dict[str, Any]:
    from src.agent.graph import investigate_case

    path = CASES_IN / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"unknown case: {case_id}")
    case = json.loads(path.read_text(encoding="utf-8"))
    state = investigate_case(case)
    output = to_output_json(case, state)
    errors = validate_output(output)
    if errors:
        raise ValueError(f"schema violations for {case_id}: {errors}")
    CASES_OUT.mkdir(parents=True, exist_ok=True)
    (CASES_OUT / f"{case_id}.json").write_text(json.dumps(output, indent=1), encoding="utf-8")
    write_markdown_summary(output, CASES_OUT / f"{case_id}.md")

    # Submission answer file: enriched union record (16-field core + NBA
    # before/after, SAR narrative, extra-evidence loop, memory, write-back).
    enriched = enrich_output(case, output)
    for field in ("next_best_action_before_extra_evidence",
                  "next_best_action_after_extra_evidence",
                  "missing_evidence", "extra_evidence_requested",
                  "uncertainty", "sar", "sar_required", "graph_writeback"):
        if state.get(field):
            enriched[field] = state.get(field)
    write_hhg_files(case_id, enriched)
    return output


def run_all() -> list[dict[str, Any]]:
    outputs = []
    for path in sorted(CASES_IN.glob("case_*.json")):
        outputs.append(run_case(path.stem))
    hhg = sorted(CASES_ROOT.glob("HHG-*.json"))
    print(f"submission files: {len(hhg)} HHG-*.json in cases/")
    return outputs


def run_single_case(case: dict[str, Any], approvals: dict[str, bool] | None = None) -> dict[str, Any]:
    """Backward-compat alias: investigate a case dict directly."""
    from src.agent.graph import investigate_case
    _ = approvals
    state = investigate_case(case)
    output = to_output_json(case, state)
    errors = validate_output(output)
    if errors:
        raise ValueError(f"schema violations: {errors}")
    return enrich_output(case, output)


def assert_output(output: dict[str, Any]) -> dict[str, Any]:
    """Backward-compat alias: raise on schema violations."""
    errors = validate_output(output)
    if errors:
        raise ValueError(f"schema violations: {errors}")
    return output


# -- extended enrichment (union fields; never break the required 16) --------

def enrich_output(case: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    """Return a NEW dict: exact-16 core + extended union fields for review.

    The JSON file on disk keeps exactly OUTPUT_SCHEMA (see run_case); the
    enriched record is what --case prints and what memory sees.
    """
    enriched = dict(output)
    verdict = output.get("verdict")
    confidence = float(output.get("confidence", 0.0) or 0.0)
    total = float((output.get("amounts", {}) or {}).get("total", 0.0) or 0.0)
    try:
        from src.agent.memory import find_similar_cases
        memory_matches = find_similar_cases(output)
    except Exception:
        memory_matches = []
    actions = [a.get("action", "") for a in output.get("actions_taken", []) or []]
    missing = (
        ["cardholder_confirmation", "device_history"] if verdict == "escalate"
        else ([] if verdict == "legit" else ["issuer_chargeback_pack"])
    )
    enriched.update({
        "trigger": str(case.get("description", case.get("case_id", ""))),
        "fraud_type": output.get("fraud_pattern"),
        "uncertainty": round(1.0 - confidence, 3),
        "missing_evidence": missing,
        "next_best_action_before_extra_evidence": (
            actions[0] if actions else "monitor_account"),
        "extra_evidence_requested": list(missing),
        "next_best_action_after_extra_evidence": (
            "freeze_card" if verdict == "fraud"
            else ("escalate_case" if verdict == "escalate" else "allow_transaction")),
        "recommended_actions": actions,
        "approval_route": ("analyst_review" if verdict in ("fraud", "escalate")
                           else "auto"),
        "sar_required": bool(verdict == "fraud" and total >= 500),
        "sar": {"required": bool(verdict == "fraud" and total >= 500),
                "amount_threshold": 500},
        "memory_matches": memory_matches,
        "status": "complete",
    })
    return enriched


def write_markdown_summary(output: dict[str, Any], dest: Path) -> Path:
    """Write the human-readable {case_id}.md companion to the JSON output."""
    lines = [
        f"# {output.get('case_id')} — {output.get('verdict', '').upper()}",
        "",
        f"- pattern: {output.get('fraud_pattern')}",
        f"- risk_score: {output.get('risk_score')} "
        f"(confidence {output.get('confidence')})",
        f"- transactions_reviewed: {output.get('transactions_reviewed')}",
        f"- evidence_ids: {output.get('evidence_ids')}",
        "",
        "## Graph findings",
    ]
    for f in output.get("graph_findings", []) or []:
        lines.append(f"- {f.get('query')}: {f.get('summary')} "
                     f"(nodes={f.get('node_count')})")
    lines += ["", "## RAG citations"]
    for c in output.get("rag_citations", []) or []:
        lines.append(f"- {c.get('doc')}#{c.get('chunk_id')} "
                     f"(score={c.get('score')})")
    lines += ["", "## Actions taken"]
    for a in output.get("actions_taken", []) or []:
        lines.append(f"- {a.get('action')} -> {a.get('target')} "
                     f"[{a.get('status')}] via {a.get('policy_ref')}")
    lines += ["", "## Explanation",
              str(output.get("explanation", "")),
              "", "## Recommended next steps"]
    for s in output.get("recommended_next_steps", []) or []:
        lines.append(f"- {s}")
    lines.append("")
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fraud benchmark")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--case", help="single case id, e.g. case_01")
    args = parser.parse_args()
    if args.all:
        outputs = run_all()
        for o in outputs:
            print(f"{o['case_id']}: verdict={o['verdict']} pattern={o['fraud_pattern']} "
                  f"conf={o['confidence']} risk={o['risk_score']} evidence={len(o['evidence_ids'])}")
        _print_benchmark_summary(outputs)
    else:
        output = run_case(args.case)
        print(json.dumps(output, indent=1))


def _print_benchmark_summary(outputs: list[dict[str, Any]]) -> None:
    """Compare verdicts against cases/inputs expected labels (informational)."""
    from collections import Counter
    tally = Counter(o["verdict"] for o in outputs)
    print(f"tally: {len(outputs)} cases "
          f"(fraud={tally.get('fraud', 0)} "
          f"escalate={tally.get('escalate', 0)} "
          f"legit={tally.get('legit', 0)})")
    correct, total = 0, 0
    misses = []
    for o in outputs:
        path = CASES_IN / f"{o['case_id']}.json"
        if not path.exists():
            continue
        expected = json.loads(path.read_text(encoding="utf-8")).get("expected", {}).get("verdict")
        total += 1
        if expected == o["verdict"]:
            correct += 1
        else:
            misses.append(f"{o['case_id']}: expected={expected} got={o['verdict']}")
    print(f"benchmark accuracy: {correct}/{total}")
    for m in misses:
        print(f"  miss: {m}")


if __name__ == "__main__":
    main()
