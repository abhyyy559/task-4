# How It Works — Technical Deep Dive

> **Snapshot:** 2026-09-21, final rebuild completing. Architecture and data flow are final;
> verify file-level details after the tester/reviewer pass.

## Architecture (one picture)

```
                    ┌─────────────────────────────────────────┐
  TRIGGER           │  risk_score / customer_report /          │
  (case pack) ─────▶  analyst_request                          │
                    └──────────────┬──────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │  ORCHESTRATOR (src/agent/orchestrator.py)│
                    │  sense → investigate → request evidence  │
                    │        → recommend → act → stop          │
                    └──────┬───────────────┬──────────────────┘
                           │               │
              ┌────────────▼──────┐  ┌──────▼──────────────────┐
              │  TIGERGRAPH LAYER │  │  GRAPHRAG MEMORY        │
              │  schema + GSQL    │  │  pattern docs + 5,565   │
              │  k-hop traversals │  │  closed cases, vector   │
              │  graph algorithms │  │  retrieval              │
              └────────────┬──────┘  └──────┬──────────────────┘
                           │               │
                           ▼               ▼
                    ┌─────────────────────────────────────────┐
                    │  POLICY ENGINE (src/agent/policy.py +    │
                    │  config/policies.yaml, rules R1–R10)     │
                    │  every action cites its authorizing rule │
                    └──────────────┬──────────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────┐
                    │  EXECUTOR (src/actions/executor.py)       │
                    │  only `auto`-route actions execute;      │
                    │  L1/L2 are recommendations for humans    │
                    └──────────────┬──────────────────────────┘
                                   ▼
                    20 answer JSONs + case vertices written to graph + UI
```

## Component by component

### 1. Data layer — `src/data/hhgoa.py`

Loads the four official files: `transactions.csv` (590,742 rows, 393 Vesta columns +
`customer_id`, `ts`, `channel`, `risk_score`), `identity.csv` (144,432 rows, device
signals), `closed_cases_history.csv` (5,565 rows, investigation memory), and
`case_pack.csv` (the 20 triggers). One hard rule enforced in code: **the loader never
exposes a fraud label** — there isn't one in the data, and the agent must not go
looking for one (using the original public IEEE-CIS files to recover outcomes is an
explicit disqualification).

### 2. TigerGraph layer — `src/tigergraph/`

- **`schema.gsql`** — the knowledge graph. Vertex types: `Transaction`, `Card`,
  `Customer`, `DeviceProfile`, `Region`, `Case`, `Evidence`. Edges: `MADE_WITH`
  (transaction→card), `OWNED_BY` (card→customer), `ORIGINATED_FROM`
  (transaction→device/region), `SHARES_ORIGIN_WITH` (card↔card via device/region),
  `SUPPORTS` (evidence→case), `SIMILAR_TO` (case↔closed case).
- **`queries.gsql`** — installed GSQL queries: k-hop neighborhood of a transaction,
  shared-device/region card clusters, card velocity windows (card-testing shape:
  many small rapid authorizations), amount/region deviation from customer baseline.
- **Graph algorithms** — connected-components over the shared-origin graph to find
  coordinated rings, and degree/centrality signals to rank which cards in a cluster
  merit `MONITOR_CONNECTED_CARDS` vs `BLOCK_ALL_CARDS` (the latter needs ≥2 confirmed
  fraud cards or confirmed credential compromise — policy R10).
- **Client with honest fallback** — `client.py` tries a live TigerGraph connection
  (Savanna or Community Edition) via pyTigerGraph; when no instance is reachable it
  serves the *same query interface* from the local data with identical semantics.
  The answer files record which path served each case — we never claim a live graph
  write when the fallback ran.

### 3. GraphRAG investigation memory — `src/graphrag/`

Two corpora, one retriever (`retriever.py`):
- **Pattern knowledge**: the official fraud playbook distilled into documents (the 7
  pattern definitions, the R1–R10 policy, SAR conditions).
- **Closed cases**: all 5,565 historical investigations, retrievable by similarity to
  the current case's evidence signature.
- At investigation time the agent retrieves the top-k relevant patterns and similar
  prior cases and injects them as context — this is what "prior cases used as
  investigation memory" means concretely. Embeddings live in TigerGraph's vector
  store when connected, in a local numpy-backed store otherwise.

### 4. The agent loop — `src/agent/`

- `state.py` — the investigation state: trigger, evidence list, fraud probability,
  uncertainty, evidence requests, candidate actions, stop reason.
- `investigate.py` — the core loop. Each step: pick the highest-value unanswered
  question → run graph queries / retrieval → append evidence (each with `claim`,
  `source`, `ref`, `entity_ids`) → update probability and uncertainty.
- `memory.py` — working memory of the current case plus retrieved prior cases.
- `orchestrator.py` / `graph.py` — LangGraph-compatible orchestration of the loop
  (nodes: triage → investigate → request-evidence → recommend → finalize).
- `runner.py` — batch entry point: `--all` runs HHG-001…HHG-020 and writes the 20
  answer files; single-case mode for the UI/demo.

**Stopping criteria** (defensible, per the task): stop when additional traversals
can't move the decision — probability confidently above/below thresholds, or
uncertainty irreducible without human-supplied evidence. The `stop_reason` field
says exactly which condition fired.

### 5. Policy engine — `src/agent/policy.py` + `config/policies.yaml`

The brain's conscience, deliberately **separate** from the investigator. It maps
(evidence strength, pattern, exposure, customer response) → allowed actions, and
every recommended action carries the rule that authorized it. The ten rules, R1–R10:

| Rule | Plain meaning |
|---|---|
| R1 | Weak single signal (< 0.70 strength) → verify with customer before blocking |
| R2 | Customer denies the charge → block card + create case, consider SAR |
| R3 | Customer confirms it was them → close, no fraud |
| R4 | No reply in 24h → monitor/decline; escalate if exposure > $500 |
| R5 | Card-testing shape (rapid small auths) → its own action ladder |
| R6 | Shared device/region across cards → widen to connected cards |
| R7 | Disputed but recurring legitimate charge → don't nuke the customer's life |
| R8 | Conflicting evidence or big exposure → escalate to analyst |
| R9 | Coordinated/undocumented pattern → describe it in own words, escalate |
| R10 | Never block ALL cards without ≥2 confirmed fraud cards or confirmed credential compromise |

Approval routes: `auto` (agent executes: monitor, create case, escalate), `L1`
(analyst approval: block card, warn/verify customer, step-up auth), `L2` (senior
approval: block all cards, file SAR/report). **The agent never executes L1/L2 —
it recommends them.**

### 6. Evidence requests — the honest-simulation discipline

The dataset provides no customer/analyst replies, and the README explicitly permits
simulating them **if the assumption is recorded**. So each `evidence_requests` entry
carries `type` (`customer_validation` / `step_up_auth` / `analyst_info`),
`asked_after_step`, and `assumed_response`. The agent then produces next-best actions
**twice** — `initial` (before evidence) and `final` (after) — plus `what_changed`.
This is the task's "uncertain signals" requirement made concrete.

### 7. Executor — `src/actions/`

`executor.py` is the **only** module allowed side effects, and `mock_apis.py`
simulates the bank's core systems (card block, case management, SAR filing). The
executor refuses any L1/L2 action without a recorded human approval — that refusal
is itself logged as evidence of the control working.

### 8. MCP — `src/mcp/`

`tools.py` wraps every graph query and action as a callable tool; `tigergraph_mcp_bridge.py`
exposes them through the TigerGraph MCP surface so an MCP-compatible client can drive
the same investigation the orchestrator runs. Config in `config/mcp.json`.

### 9. UI — Streamlit

One screen per investigation: trigger → graph neighborhood visualization →
evidence list with sources → probability + uncertainty meter → evidence-request
timeline → initial vs final next-best actions with routes → SAR panel → stop reason.
Built for the 3–5 minute demo: an evaluator can watch a case go from alert to
recommended action without touching code.

## Tech stack

Python 3.11 · TigerGraph (GSQL, graph algorithms, vector search) · pyTigerGraph ·
GraphRAG (pattern docs + closed-case memory) · MCP tool bridge · LangGraph-compatible
orchestration · Streamlit UI · pytest suite · offline-first design (every external
dependency has a local fallback with identical interfaces).

## Key design decisions (say these out loud)

1. **Policy separated from inference.** The investigator finds facts; the policy
   engine decides what's allowed. An evaluator can audit every action back to a rule.
2. **Risk score is a trigger, never a verdict.** Probability comes only from
   independent graph evidence. This is why the system can clear legitimate cases.
3. **`uncertain` is a first-class verdict.** Forcing fraud/legitimate on thin evidence
   is how innocent customers get blocked. R8 exists for exactly this.
4. **Assumptions are data.** Simulated customer replies are recorded, not hidden —
   the answer schema has a field for them because the task demands that honesty.
5. **Fallback without lying.** No TigerGraph instance in the demo room? The same
   queries run locally and the output says so. Claiming a live graph write we didn't
  make would be disqualifying-level dishonesty; the schema has `written_to_graph`
   precisely so we tell the truth per case.
