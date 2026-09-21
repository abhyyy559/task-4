# fraud-agent

Agentic fraud investigation over IEEE-CIS-compatible transaction data.
Graph layer (TigerGraph w/ local mock fallback) + GraphRAG pattern knowledge +
policy-gated actions + Streamlit UI + 20-case benchmark.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows; `source .venv/bin/activate` on POSIX
pip install -e ".[test]"      # or: pip install pytest pyyaml numpy
python -m pytest tests/ -q    # unit + integration tests
python -m src.agent.runner --all   # benchmark 20 cases -> cases/outputs/
python -m src.main --case case_01  # single case
python -m src.graphrag.ingest_docs # rebuild pattern knowledge store
streamlit run src/ui/app.py   # investigation UI (needs streamlit)
```

## Repo tree
- `src/agent/` — state, prompts, memory, policy, orchestrator, LangGraph, runner
- `src/tigergraph/` — `schema.gsql`, `queries.gsql`, mock-backed `client.py`
- `src/graphrag/` — ingest + numpy-light retriever
- `src/mcp/` — tool wrappers; `config/mcp.json` registry
- `src/actions/` — mock APIs + policy-gated executor
- `cases/inputs/` — 20 benchmark cases (5 patterns x 4)
- `data/HHGOA_IEEE/` — synthetic IEEE-CIS-compatible stub (see PLAN.md, data README)
- `docs/` — architecture, demo, blog + social drafts

## Notes
- Works fully offline: TigerGraph/LangGraph/Streamlit are all optional with fallbacks.
- `data/HHGOA_IEEE/` is synthetic (real dataset was missing); see `PLAN.md` section 1.
- IEEE-CIS stub: `transactions.csv` (PK TransactionID + `isFraud` ground truth for
  scoring only — never read at investigation time), `identity.csv` (FK TransactionID),
  `patterns.md` (5 fraud pattern definitions, GraphRAG corpus seed). Only V1–V2, C1–C2,
  D1 populated; V3–V339 omitted by design. See `data/HHGOA_IEEE/README.md`.

## Config
- `config/settings.yaml` — model name, thresholds (no API key needed for mock path).
- `config/policies.yaml` — action allow/deny rules enforced by `policy.py`.
- `config/mcp.json` — MCP tool registry mirroring `src/mcp/tools.py`.
- `.env.example` — TigerGraph Savanna vars (`TG_HOST`, …); unset = mock fallback.

## Outputs
- `cases/inputs/case_NN.json` — 20 benchmark cases (5 patterns × 4).
- `cases/outputs/case_NN.json` — investigation results, exact 16-field schema
  (see `PLAN.md` §4; `OUTPUT_SCHEMA` in `src/agent/runner.py`).
