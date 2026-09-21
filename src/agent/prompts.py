"""Model-agnostic prompts for planner / investigator / reporter roles."""
from __future__ import annotations

SYSTEM = (
    "You are a fraud investigation agent. Use graph tools and pattern knowledge. "
    "Every fraud finding MUST cite evidence_ids. Never invent TransactionIDs. "
    "Prefer 'escalate' over 'fraud' when evidence is thin."
)

PLANNER = (
    "Given case {case_id} (hint: {pattern_hint}) with transactions {transaction_ids}, "
    "decide which graph queries to run: card_ring, device_cluster, mule_fanout, "
    "takeover, synthetic, evidence_subgraph. Reply as a JSON list of tool calls."
)

INVESTIGATOR = (
    "You have graph findings: {graph_findings} and pattern citations: {rag_citations}. "
    "List risk signals with the evidence IDs supporting each one. "
    "Output JSON: {{\"signals\": {{...}}, \"evidence_ids\": [...]}}."
)

REPORTER = (
    "Write a 3-6 sentence rationale for verdict={verdict} (confidence {confidence}) "
    "over transactions {transaction_ids}, citing evidence {evidence_ids} and "
    "patterns {patterns}. Then list recommended_next_steps as JSON."
)

ASSESS_PROMPT = (
    "You are a fraud assessor. Given case {case_id} with transactions {transactions}, "
    "graph findings {graph_findings} and pattern context {rag_context}, assess fraud risk. "
    "Output JSON ONLY: {{\"verdict\": \"fraud|legit|escalate\", \"fraud_pattern\": str|null, "
    "\"risk_score\": 0-100, \"confidence\": 0-1, \"uncertainty\": 0-1, "
    "\"evidence_ids\": [...], \"explanation\": str}}. "
    "Every claim MUST cite evidence_ids (TransactionID / node IDs). Never invent IDs."
)

DECIDE_MORE_EVIDENCE_PROMPT = (
    "You decide if more evidence is needed. Given verdict={verdict}, confidence={confidence}, "
    "uncertainty={uncertainty}, missing_evidence={missing_evidence}, decide. "
    "Output JSON ONLY: {{\"extra_evidence_requested\": bool, "
    "\"next_best_action_before_extra_evidence\": str, \"missing_evidence\": [...]}}. "
    "Cite evidence_ids supporting the decision."
)

RECOMMEND_ACTIONS_PROMPT = (
    "Recommend policy-gated actions for case {case_id} (verdict={verdict}, risk_score={risk_score}). "
    "Allowed actions: allow_transaction, block_transaction, monitor_account, freeze_account, "
    "warn_customer, create_case, file_sar, request_more_evidence, escalate_to_analyst, request_step_up_auth. "
    "Output JSON ONLY: {{\"recommended_actions\": [{{\"action\": str, \"target\": str, \"reason\": str}}], "
    "\"approval_route\": str}}. Every recommendation MUST cite evidence_ids."
)

EXPLAIN_PROMPT = (
    "Explain verdict={verdict} (confidence {confidence}) over transactions {transaction_ids} "
    "citing evidence {evidence_ids} and patterns {patterns}. "
    "Output JSON ONLY: {{\"explanation\": str (3-6 sentences), "
    "\"recommended_next_steps\": [str], \"evidence_ids\": [...]}}."
)


def render(template: str, **kwargs: object) -> str:
    # Aliases so callers can pass either naming convention (offline robustness).
    aliased = dict(kwargs)
    if "transactions" not in aliased and "transaction_ids" in aliased:
        aliased["transactions"] = aliased["transaction_ids"]
    if "transaction_ids" not in aliased and "transactions" in aliased:
        aliased["transaction_ids"] = aliased["transactions"]
    if "rag_context" not in aliased:
        if "rag_citations" in aliased:
            aliased["rag_context"] = aliased["rag_citations"]
        elif "rag_hits" in aliased:
            aliased["rag_context"] = aliased["rag_hits"]
    if "patterns" not in aliased and "pattern_hint" in aliased:
        aliased["patterns"] = aliased["pattern_hint"]
    try:
        return template.format(**aliased)
    except KeyError as exc:
        raise ValueError(f"missing prompt variable: {exc}")
