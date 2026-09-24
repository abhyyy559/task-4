# Teaching an Agent to Investigate Fraud: Graphs, Policy, and the Courage to Say "I Don't Know Yet"

*How we built an agentic fraud investigator for the TigerGraph HHGOA hackathon — and why its most important feature is knowing when it isn't sure.*

## What we built

Fraud investigation is broken in a specific way: automation either scores a transaction without explaining why, or recommends an action without evidence or policy grounding. Analysts then do the slow part by hand — tracing money movement, finding connected accounts, checking policy, writing it all up.

**fraud-agent** is our answer: an agentic system that behaves like a junior fraud analyst. A trigger opens a case, the agent gathers evidence from a fraud graph, grounds its reasoning in pattern knowledge via GraphRAG, quantifies its own uncertainty, requests *controlled* extra evidence when unsure, recommends policy-gated next-best actions, explains every finding with cited evidence IDs, and writes the closed case back to the graph as institutional memory.

The result we're proudest of: on our 20-case benchmark (5 fraud typologies × 4, including borderline and negative controls), the agent scores **20/20** — 10 frauds caught with cited multi-hop evidence, 5 ambiguous cases safely escalated, 5 legitimate cases cleared with zero false-positive actions.

## The architecture

The system is a pipeline of five layers, each independently testable and fully runnable offline:

```
trigger → open case → gather graph evidence → GraphRAG context → assess
       → decide_more_evidence ─┬─ request_evidence → reassess (bounded loop)
                               └─ recommend_actions → policy approval → execute
       → explain → memory → write back to graph
```

- **Agent orchestrator** (`src/agent/orchestrator.py`): plans which graph queries to run per case, scores risk signals deterministically (0–100), and drives the evidence loop. A LangGraph StateGraph wrapper exists, but the fallback orchestrator is the primary offline path — every node's logic is plain, auditable Python.
- **Graph layer** (`src/tigergraph/`): a GSQL schema (TRANSACTION, CARD, DEVICE, EMAIL, ADDRESS, IDENTITY, plus CASE/EVIDENCE/FINDING/ACTION/POLICY/PATTERN vertices) with six traversal queries — card-ring expansion, device clustering, mule fan-out, takeover anomalies, synthetic-identity signals, and a bounded k-hop evidence subgraph.
- **GraphRAG** (`src/graphrag/`): pattern definitions and policies are chunked and embedded with deterministic hashed-trigram vectors — no model downloads, no API keys — and retrieval caps context at ~2,000 tokens so the agent reasons over compact context, not raw data.
- **Policy engine** (`src/agent/policy.py` + `config/policies.yaml`): every action passes a sandboxed rule evaluation (evaluated with `{"__builtins__": {}}` against three context keys, first-match-wins, default-deny). Approval-required actions are recorded as blocked, never executed.
- **Runner + UI** (`src/agent/runner.py`, `src/ui/app.py`): a 20-case benchmark runner that validates every output against a strict 16-field schema, plus a Streamlit console showing the verdict, evidence, uncertainty, and approval routes live.

## How TigerGraph is used

The graph is the *only* place detection happens — the LLM-shaped part of this system reasons over structured query output, never over raw rows. This is our anti-hallucination stance: **every fraud verdict must cite evidence IDs** (TransactionIDs, CARD:/DEVICE:/EMAIL: node IDs), and the output validator rejects a fraud verdict with empty evidence.

We were honest with ourselves about infrastructure: for this submission the schema and queries were authored as GSQL (`schema.gsql`, `queries.gsql`) and executed through a local graph engine that implements the same six query semantics over the dataset, so the entire pipeline runs offline with no credentials. The MCP tool bridge (`src/mcp/tools.py`) exposes the identical tool surface — including `write_case` / `get_case` for persistence — and activates against a live TigerGraph Savanna endpoint the moment `TIGERGRAPH_HOST` is set. The investigation logic doesn't change between modes.

Two details matter more than they look:

1. **No label leakage.** The ground-truth `isFraud` column is stripped at the client; the agent never sees the answer it's being graded on.
2. **Graph write-back.** Every completed investigation persists as a CASE vertex — verdict, pattern, risk, evidence, actions — building institutional memory the memory module retrieves for future cases.

## The agentic capabilities (the part judges should poke)

**The uncertainty loop.** After initial assessment the agent computes calibrated confidence. Below 0.60, it diagnoses *what specifically it's missing* (cardholder confirmation? device history? issuer chargeback pack?), requests that evidence through the same policy gate as any other action, folds received evidence back into its findings, and re-scores — for at most 3 rounds. Crucially, it records its **next best action before** requesting evidence and **after** receiving it, so a reviewer can watch the recommendation evolve. A score is a reason to look; it is never a verdict.

**Temporal safety.** When retrieving similar prior cases, the agent only sees cases that chronologically predate the current one — no accidental time travel, no future leakage.

**Policy-gated everything.** Actions like `freeze_card` or `file_sar` carry approval routes (`fraud_analyst`, `compliance`). The executor is the *only* path to side-effect APIs, and it blocks before it acts. In the UI you can try freezing a card on a legitimate case — the engine denies it and the attempt is recorded. Deterministic rules decide; nothing is left to model discretion.

**SAR when the law says so.** Confirmed fraud over the reporting threshold triggers a Suspicious Activity Report with a FinCEN-style narrative — who, what, how much, which evidence, which typology — routed to compliance approval.

## What we learned

- **Determinism is a feature, not a limitation.** The risk-scoring heuristics are plain arithmetic over graph findings. That made the benchmark *debuggable*: when a negative control (shared office PC) initially scored too high, we traced it to one rule and fixed it in minutes. A neural scorer would have hidden that.
- **Negative controls are half the benchmark.** Designing legitimate-but-suspicious-looking cases (family shared card, corporate NAT, student's first card) taught us more than designing frauds. The agent's escalation path — not its fraud path — is what keeps false positives at zero.
- **Evidence citations discipline the whole design.** Once every verdict must cite IDs, the graph queries, the schema, the output validator, and the UI all align around that contract.
- **Offline-first saved the demo.** No live credentials? The identical tool surface runs on the local engine. The demo can't break because a service is down.

## What we'd improve with more time

1. **A self-evolving layer.** Compressing every closed case into memory is step one; step two is an adversarial loop where a red-team simulator generates fraud variants, tests whether the agent catches them, and feeds failures back as new pattern candidates — an agent that learns as fraud tactics evolve.
2. **Live Savanna end-to-end.** The MCP bridge is built; deploying the schema to Savanna and re-running the benchmark against the real graph is the next milestone.
3. **Smarter memory compression.** Jaccard similarity over flagged entities is transparent but shallow; embedding-based case similarity would catch typological resemblance that entity overlap misses.
4. **Streaming evidence.** The evidence loop currently runs to completion per case; a long-running variant would watch live transaction feeds and re-open dormant cases when new connections appear.

## Try it

```bash
pip install -e ".[test]"
python -m pytest tests/ -q          # 28 tests
python -m src.agent.runner --all    # 20-case benchmark -> cases/HHG-001..020.json
streamlit run src/ui/app.py         # analyst console
```

Fully offline. No API keys. Every fraud finding cites its evidence.
