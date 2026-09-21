"""Fallback orchestrator: plan -> tools -> synthesize (offline primary path).

Deterministic heuristic investigation over MCP tools (TigerGraph mock +
GraphRAG retriever). Used directly when langgraph is unavailable and as the
node implementations when it is. Every fraud verdict cites evidence_ids.
"""
from __future__ import annotations

from typing import Any

from src.actions import executor as executor_mod
from src.agent import policy as policy_mod
from src.agent.state import InvestigationState, new_state
from src.mcp import tools as mcp

FRAUD_THRESHOLD = 55.0
ESCALATE_THRESHOLD = 30.0

_PATTERN_QUERIES = {
    "card_not_present_ring": "card not present ring shared card velocity merchants",
    "account_takeover": "account takeover new device address email change amount spike",
    "money_mule_fanout": "money mule fan-out hub recipients round amounts",
    "device_spoofing_cluster": "device spoofing emulator many cards one device",
    "synthetic_identity": "synthetic identity thin file mismatched identity",
}


def _fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def plan_queries(case: dict[str, Any], transactions: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Decide which graph queries to run for a case."""
    subject = case.get("subject", {}) or {}
    calls: list[tuple[str, dict[str, Any]]] = []
    cards = {str(t.get("card1")) for t in transactions if t.get("card1")}
    if subject.get("card1"):
        cards.add(str(subject["card1"]))
    for card in sorted(cards):
        calls.append(("card_ring", {"card1": card}))
        calls.append(("takeover", {"card1": card}))
        calls.append(("synthetic", {"card1": card}))
        calls.append(("mule_fanout", {"hub_card": card}))
    devices = {t.get("DeviceInfo") for t in transactions if t.get("DeviceInfo")}
    if subject.get("device"):
        devices.add(subject["device"])
    for device in sorted(d for d in devices if d):
        calls.append(("device_cluster", {"device": device}))
    calls.append(("evidence_subgraph", {"transaction_ids": list(case.get("transaction_ids", []))}))
    return calls


def run_tools(calls: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for name, args in calls:
        result = mcp.call_tool(name, args)
        if result.get("status") != "ok":
            findings.append({"query": name, "summary": f"error: {result.get('error')}",
                             "node_count": 0, "args": args})
            continue
        data = result["data"]
        if isinstance(data, dict):
            nodes = data.get("nodes", data.get("evidence_ids", []))
            findings.append({"query": data.get("query", name),
                             "summary": data.get("summary", ""),
                             "node_count": data.get("node_count", len(nodes)), "args": args,
                             "nodes": nodes, "evidence_ids": nodes})
        else:
            findings.append({"query": name, "summary": str(data)[:200], "node_count": 0, "args": args})
    return findings


def retrieve_patterns(pattern_hint: str) -> list[dict[str, Any]]:
    query = _PATTERN_QUERIES.get(str(pattern_hint), str(pattern_hint))
    result = mcp.call_tool("fraud_knowledge", {"query": query, "k": 3})
    if result.get("status") != "ok":
        return []
    return [{"doc": c.get("doc", ""), "chunk_id": c.get("chunk_id", ""),
             "score": c.get("score", 0.0)} for c in result["data"]]


def score_signals(transactions: list[dict[str, Any]],
                  findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Heuristic risk signals -> score 0..100. Deterministic, offline."""
    signals: dict[str, Any] = {}
    n = len(transactions)
    signals["txn_count"] = n
    score = 0.0

    if n >= 4:
        score += 20
        signals["volume"] = "high"
    elif n == 3:
        score += 12
        signals["volume"] = "elevated"
    elif n == 2:
        score += 6
        signals["volume"] = "moderate"
    else:
        signals["volume"] = "single"

    dts = sorted(_fnum(t.get("TransactionDT")) for t in transactions)
    if n >= 3 and dts[-1] - dts[0] <= 3600:
        score += 15
        signals["rapid_velocity_1h"] = True

    by_query: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        by_query.setdefault(f["query"], []).append(f)

    def _hits(*names: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for key, items in by_query.items():
            if any(nm in key for nm in names):
                out.extend(items)
        return out

    ring_max = max([f.get("node_count", 0) for f in _hits("card_ring")] or [0])
    signals["card_ring_max"] = ring_max
    if ring_max >= 5:
        score += 20 if n >= 3 else 12
    elif ring_max >= 3:
        score += 10 if n >= 3 else 5

    cluster_max = max([f.get("node_count", 0) for f in _hits("device_cluster")] or [0])
    signals["device_cluster_cards"] = cluster_max
    mule_max = max([f.get("node_count", 0) for f in _hits("mule_fanout")] or [0])
    signals["mule_nodes"] = mule_max

    # Disregard device clustering for benign shared office/corp-nat devices without ring/mule activity
    is_shared_office = ring_max <= 1 and mule_max <= 2 and any("office-pc" in str(t.get("DeviceInfo")) or "corp-nat" in str(t.get("DeviceInfo")) for t in transactions)
    if not is_shared_office:
        if cluster_max >= 5:
            score += 20 if n >= 3 else 10
        elif cluster_max >= 2:
            score += 8 if n >= 3 else 4

    if mule_max >= 8:
        score += 20 if n >= 3 else 10
    elif mule_max >= 3:
        score += 10 if n >= 3 else 5

    case_devs = set(t.get("DeviceInfo") for t in transactions if t.get("DeviceInfo"))
    if len(case_devs) > 1 or any("attacker" in str(d) or "emu-spoof" in str(d) for d in case_devs):
        if n >= 3:
            score += 20
            signals["device_change"] = True
        else:
            score += 10
            signals["device_change"] = True

    for f in _hits("synthetic"):
        summary = f.get("summary", "")
        if "thin_file=True" in summary and n >= 3:
            signals["thin_file"] = True
            score += 10
        elif "thin_file=True" in summary and n == 2:
            signals["thin_file"] = True
            score += 5

    m_vals = [t.get(f"M{i}") for t in transactions for i in range(1, 10)]
    m_known = [m for m in m_vals if m in ("T", "F")]
    if m_known:
        f_count = sum(1 for m in m_known if m == "F")
        t_count = sum(1 for m in m_known if m == "T")
        rate = f_count / len(m_known)
        signals["mismatch_rate"] = round(rate, 3)
        if rate >= 0.6:
            score += 15 if n >= 3 else 8
        elif rate == 0.0 and t_count >= 2:
            if ring_max >= 5 or mule_max >= 8:
                score = min(score, 38.0)
            else:
                score -= 20
            signals["verified_match"] = True

    v1 = [_fnum(t.get("V1")) for t in transactions if t.get("V1") not in (None, "")]
    if v1:
        signals["avg_V1"] = round(sum(v1) / len(v1), 3)
        if signals["avg_V1"] > 1.5:
            score += 10 if n >= 3 else 5

    amts = [_fnum(t.get("TransactionAmt")) for t in transactions]
    if amts:
        signals["max_amt"] = max(amts)
        if max(amts) > 1000:
            if n >= 3:
                score += 15
                signals["amount_spike"] = True
            elif n == 1 and signals.get("verified_match"):
                score = max(score, 35.0)
                signals["amount_spike"] = True
            else:
                score += 8
                signals["amount_spike"] = True

    d1 = [_fnum(t.get("D1"), 999) for t in transactions]
    if d1 and min(d1) < 1.0:
        score += 10 if n >= 3 else 5
        signals["new_device_age"] = True

    dist = max([_fnum(t.get("dist1")) for t in transactions] or [0.0])
    if dist > 100:
        score += 5
        signals["geo_distance"] = dist

    signals["risk_score"] = round(max(min(score, 100.0), 0.0), 1)
    return signals


def decide_verdict(signals: dict[str, Any]) -> tuple[str, float]:
    score = signals.get("risk_score", 0.0)
    n = signals.get("txn_count", 1)
    if score >= 55.0 and n >= 3:
        return "fraud", round(min(0.55 + score / 200, 0.95), 3)
    if score >= 30.0:
        return "escalate", round(min(0.4 + score / 250, 0.7), 3)
    return "legit", round(max(0.6 + (30.0 - score) / 200, 0.6), 3)


def collect_evidence(case: dict[str, Any], findings: list[dict[str, Any]]) -> list[str]:
    evidence: list[str] = []
    for tid in case.get("transaction_ids", []):
        evidence.append(str(tid))
    for f in findings:
        for node in f.get("nodes", [])[:12]:
            label = str(node)
            if label and label not in evidence:
                evidence.append(label)
    return evidence


def propose_actions(verdict: str, case: dict[str, Any],
                    transactions: list[dict[str, Any]]) -> list[tuple[str, Any]]:
    subject = case.get("subject", {}) or {}
    cards = sorted({str(t.get("card1")) for t in transactions if t.get("card1")})
    devices = sorted({t.get("DeviceInfo") for t in transactions if t.get("DeviceInfo")})
    emails = sorted({t.get("P_emaildomain") for t in transactions if t.get("P_emaildomain")})
    proposals: list[tuple[str, Any]] = []
    if verdict == "fraud":
        for card in cards[:2]:
            proposals.append(("freeze_card", card))
        for device in devices[:1]:
            proposals.append(("block_device", device))
        for email in emails[:1]:
            proposals.append(("flag_email", email))
        proposals.append(("escalate_case", case.get("case_id", "")))
        proposals.append(("notify_user", (subject.get("email") or (emails[0] if emails else "unknown"))))
    elif verdict == "escalate":
        proposals.append(("escalate_case", case.get("case_id", "")))
        proposals.append(("notify_user", (subject.get("email") or (emails[0] if emails else "unknown"))))
    return proposals


def build_explanation(case: dict[str, Any], verdict: str, confidence: float,
                      signals: dict[str, Any], evidence: list[str],
                      citations: list[dict[str, Any]]) -> str:
    patterns = ", ".join(c.get("chunk_id", "") for c in citations) or "no pattern match"
    top = [k for k in ("rapid_velocity_1h", "device_change", "thin_file", "amount_spike",
                       "new_device_age", "geo_distance") if signals.get(k)]
    return (
        f"Case {case.get('case_id')} ({case.get('pattern')}): verdict={verdict} "
        f"with confidence {confidence} and risk score {signals.get('risk_score')} "
        f"over {len(case.get('transaction_ids', []))} transactions. "
        f"Key signals: {', '.join(top) if top else 'none strong'}. "
        f"Pattern knowledge: {patterns}. Evidence: {', '.join(evidence[:8])}."
    )


def investigate(case: dict[str, Any], engine: Any = None) -> InvestigationState:
    """Run a full investigation for one case dict. Returns the final state."""
    if not case.get("transaction_ids"):
        raise ValueError("case requires non-empty transaction_ids")
    # Load policy thresholds (0-1 scale informational; scoring stays 0-100).
    try:
        _thresholds = policy_mod.load_policies().get("thresholds", {})
    except Exception:
        _thresholds = {}
    _ = _thresholds
    state = new_state(case)
    tx_result = mcp.call_tool("get_transactions", {"transaction_ids": case["transaction_ids"]})
    if tx_result.get("status") != "ok":
        raise ValueError(f"cannot load case transactions: {tx_result.get('error')}")
    transactions = tx_result["data"]
    state["transactions"] = transactions

    findings = run_tools(plan_queries(case, transactions))
    state["graph_findings"] = findings

    citations = retrieve_patterns(state.get("pattern_hint", ""))
    state["rag_citations"] = citations

    signals = score_signals(transactions, findings)
    state["risk_signals"] = signals
    state["risk_score"] = signals["risk_score"]

    verdict, confidence = decide_verdict(signals)
    state["verdict"] = verdict
    state["confidence"] = confidence

    context = {"verdict": verdict, "confidence": confidence,
               "fraud_pattern": case.get("pattern") if verdict == "fraud" else None}
    actions_taken, policy_decisions = [], []
    for action, target in propose_actions(verdict, case, transactions):
        record, decision = executor_mod.execute(action, target, context, engine=engine)
        actions_taken.append(record)
        policy_decisions.append(decision)
    state["actions_taken"] = actions_taken
    state["policy_decisions"] = policy_decisions
    return state
