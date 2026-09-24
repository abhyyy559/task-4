# Catching fraud rings with graphs, not just rows

Fraud doesn't live in rows — it lives in relationships. A single transaction
looks fine; twelve cards sharing a device profile and a billing region within
a week is a ring. That's why we built an **agentic fraud investigation agent**
for the Hacker House Goa TigerGraph partner task: it investigates each of the
20 official benchmark cases (`HHG-001` … `HHG-020`) over the 590K-transaction
HHGOA IEEE-CIS dataset and recommends the next best action under a strict
fraud policy.

## What we built

An offline-first investigation loop. For each case the agent resolves the
flagged transaction's card, builds a 60-day baseline, checks device sharing
and region clusters across all 13,553 cards, matches evidence-derived pattern
signatures (card testing, CNP burst, new-device CNP, out-of-region use,
account takeover, structuring, coordinated undocumented abuse), consults
5,565 closed cases for precedent, applies fraud policy R1–R10, and writes the
official nested answer: verdict, pattern, exposure, evidence, next-best
actions (initial and final), and a SAR filing decision.

## The architecture

`src/agent/` (investigator + policy engine + LangGraph orchestrator) →
`src/tigergraph/` (schema, 8 installed GSQL queries, mock-backed client) →
`src/graphrag/` (TF retriever over official pattern definitions, policy text,
and closed-case narratives) → `src/actions/` (policy-gated executor) →
`src/ui/` (Streamlit). The runner replays all 20 official inputs
deterministically; no LLM is required and none is used — every number in the
answer is computed from the data.

## How TigerGraph is used

The fraud graph models transactions, cards, devices, emails, addresses, and
identities. Eight installed queries back the investigation: card-ring
expansion, device clustering, mule fan-out, takeover anomaly, synthetic-identity
signals, evidence subgraph, transaction fetch — and `q_ring_components`, a
genuine graph algorithm (weakly connected components via label propagation over
the card–device subgraph) that finds candidate fraud rings. An optional bridge
maps every local tool to the official `tigergraph-mcp` server's
`run_installed_query`; without live credentials it raises an explicit
`BridgeUnavailable` and the offline path runs instead. Closed cases are written
back as `CASE` vertices so later investigations retrieve them.

## The agentic capabilities

Trigger handling (risk signal, customer report, analyst request), controlled
evidence gathering, pattern assessment from evidence (never from input labels),
case creation and progression with status transitions, case memory (similar
prior cases inform the verdict), policy-gated next-best actions with
approval routes (auto/L1/L2), SAR filing under rule 3a, escalation on
uncertainty, and full explanations citing transaction and node IDs.

## What we learned

Calibration beats cleverness. Our first run flagged 16 SARs and 12
"undocumented" patterns — the region detector was firing on ordinary local
commerce (26K transactions in one region). Grounding thresholds in the
dataset's own closed cases fixed it: genuine coordination means foreign cards
with burst activity, and structuring means near-threshold amounts within 72
hours of the flag. SARs fell to 6, undocumented to 2, and 4 cases now clear
as legitimate.

## What we'd improve with more time

A live TigerGraph Savanna instance (the bridge is ready; credentials are the
only gap), learned risk scoring to complement the heuristic policy engine,
analyst-feedback loops that update case memory, and real-time streaming
ingest instead of batch CSV loads.

## Results

20/20 cases investigated, 0 failures (~100 s). 4 legitimate / 11 uncertain /
5 fraud; patterns: card testing, new-device CNP, account takeover ×4,
undocumented ×2. 42/42 tests pass. No label leakage by construction —
ground-truth labels are never read at investigation time.
