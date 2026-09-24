# What We Built — the 5-minute briefing

> **Snapshot:** 2026-09-21. The final rebuild against the official dataset is completing
> (independent tester + reviewer pass still to run). Concept, architecture, policy engine,
> and domain rules below are final. Refresh implementation line-items after the final pass.

## The one-liner

**An agentic fraud-investigation agent powered by TigerGraph** that takes a fraud case —
a risk score, a customer complaint, or an analyst's hunch — investigates it across a
knowledge graph of 590,742 transactions, gathers evidence under a strict policy engine,
and recommends the next best action with a human approval route. Every claim it makes
cites its evidence.

## The problem it solves

Fraud analysts today do this manually: pull transaction history, trace money movement,
find connected accounts, check device signals, read policy, write up findings, decide
what to do. Slow, fragmented, and usually finished after the money is already gone.

## What the agent does, end to end

1. **Triggered** by one of three things: a real-time risk score, a customer report
   ("I never made this purchase"), or an analyst request.
2. **Investigates** by traversing the TigerGraph knowledge graph — the flagged
   transaction's card, customer, device profile, region, and every connected card
   sharing those origins (k-hop traversals, shared-origin clustering).
3. **Retrieves memory**: similar closed cases from 5,565 past investigations and a
   GraphRAG pattern-knowledge base built from the official fraud playbook.
4. **Scores** fraud probability from *independent evidence signals* — never from the
   risk score alone (the risk score is an input, never a verdict).
5. **Asks for evidence when uncertain**: customer validation, step-up auth, or analyst
   info. Responses are simulated (the dataset doesn't supply them) and every
   simulation is recorded as an explicit assumption.
6. **Recommends next-best actions twice** — once before the extra evidence, once after —
   each action citing the exact policy rule, with an approval route: `auto` (agent may
   execute), `L1`, `L2` (human must approve).
7. **Files a SAR** (Suspicious Activity Report) automatically when policy says the
   exposure and pattern demand it, with a full narrative.
8. **Writes the case back to the graph**, with a defensible stop reason explaining
   why it stopped investigating.

## The official scoreboard (how you'll be judged)

| Criterion | Weight | Where we score |
|---|---|---|
| Investigation accuracy | 25% | Evidence-derived verdicts on all 20 cases; `uncertain` allowed when honest |
| Next-best action | 25% | Policy-cited actions with approval routes, before *and* after evidence |
| Case summary / explainability | 10% | Every finding cites evidence IDs; plain-language summaries |
| Agentic design / engineering | 15% | Sense → investigate → request evidence → act loop with stopping criteria |
| Innovation | 15% | Graph + vector in one store, GraphRAG investigation memory, simulated-evidence discipline |
| Demo quality / completeness | 10% | 3–5 min end-to-end video, Streamlit UI showing investigation live |

## The dataset (know these numbers cold)

- **590,742 transactions** (~675 MB), every original IEEE-CIS/Vesta column kept —
  **except the fraud label, which was removed**. No ground truth in the inputs, ever.
- **144,432 identity records** (device/browser/OS signals), joined on TransactionID.
- **5,565 closed cases** (4,665 confirmed fraud, 900 cleared) = the agent's investigation memory.
- **20 benchmark cases**, `HHG-001` … `HHG-020`. **Half are legitimate.** A system that
  cries "fraud" on everything fails — restraint is graded.
- Triggers: 11 risk-score alerts, 8 customer reports, 1 analyst request.

## Deliverables checklist

- [x] Working agent (Python 3.11, `src/agent/runner.py --all` runs all 20 cases)
- [x] GitHub repo with TigerGraph schema + GSQL
- [x] 20 answer files (`cases/HHG-001.json` … `HHG-020.json`) in the official schema
- [x] Cases written to the graph (case vertices + edges to evidence)
- [x] SAR filed wherever policy requires it
- [x] Next-best action + approval route, before and after evidence
- [ ] 3–5 min demo video (in progress)
- [x] Technical blog draft (all 6 required sections)
- [x] X/LinkedIn post draft tagging `@TigerGraphDB`

## Repo map (where everything lives)

```
src/agent/        the investigator: state, orchestrator, policy engine, runner
src/tigergraph/   schema.gsql, queries.gsql, client (live pyTigerGraph + offline fallback)
src/graphrag/     pattern-knowledge ingestion + retriever (investigation memory)
src/mcp/          tool wrappers + TigerGraph MCP bridge
src/actions/      policy-gated executor — the only place side effects happen
src/data/hhgoa.py official dataset loader (transactions / identity / closed cases / case pack)
config/policies.yaml   the R1–R10 fraud policy, machine-readable
cases/            20 inputs + 20 official-schema answer files
docs/             architecture, demo script, blog draft, social draft
```

## Lines you can use verbatim

- "We built an AI fraud investigator, not a fraud classifier. It doesn't predict — it
  investigates, gathers evidence, and only then recommends an action a human approves."
- "The risk score starts the investigation; it never ends it. Our verdicts come from
  independent graph evidence."
- "Half the benchmark cases are legitimate, so the system is designed to clear people
  too — restraint is a feature, not a failure."
- "Every action cites the policy rule that authorized it, and only `auto`-route actions
  execute without a human."
