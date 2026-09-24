# HHGOA TigerGraph Task-4 — Agentic Fraud Investigation

Agentic fraud investigation over the official HHGOA IEEE-CIS dataset
(590,742 transactions, 144,432 identities, 5,565 closed cases).
Graph layer (TigerGraph w/ local mock fallback) + GraphRAG pattern knowledge +
policy-gated actions (R1–R10, verbatim from the official README) +
Streamlit UI + 20-case benchmark (`HHG-001` … `HHG-020`).

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate            # POSIX; `.venv\Scripts\activate` on Windows
pip install -e ".[test]"             # or: pip install pytest pyyaml numpy
python -m pytest tests/ -q           # unit + integration tests
python -m src.agent.runner --all     # investigate 20 cases -> cases/HHG-*.json
python -m src.agent.runner --case HHG-001   # single case
streamlit run src/ui/app.py          # investigation UI (needs streamlit)
```

The official 704 MB dataset (`data/HHGOA_IEEE_real/`, from the Google Drive
link in `TASK-PLAN-APPENDIX-README.md`) is **not** committed; place it there
before running. Without it the runner uses the small synthetic stub in
`data/HHGOA_IEEE/` and marks output `is_fallback: true`.

## Repo tree
- `src/agent/` — state, policy (R1–R10), investigator, orchestrator, LangGraph, runner
- `src/tigergraph/` — `schema.gsql`, `queries.gsql` (incl. WCC `q_ring_components`), mock-backed `client.py`
- `src/graphrag/` — ingest + numpy-light retriever over official pattern definitions
- `src/mcp/` — local tool wrappers + optional live bridge to official `tigergraph-mcp`
- `src/actions/` — mock APIs + policy-gated executor
- `cases/inputs/` — 20 official inputs (`HHG-001.json` … `HHG-020.json`)
- `cases/` — 20 generated answers (`HHG-001.json` … `HHG-020.json`), official nested schema
- `data/HHGOA_IEEE/` — small synthetic stub for offline testing only
- `docs/` — architecture, MCP integration, demo, blog + social drafts

## Notes
- Works fully offline: TigerGraph/LangGraph/Streamlit are all optional with fallbacks.
- Official answer schema: `case_id`, `case`, `evidence_requests`, `next_best_actions`,
  `sar`, `stop_reason`, `tool_calls`, `tokens`, `latency_s`. Verdicts are
  `fraud | legitimate | uncertain`; `escalated` is a status, never a verdict.
- Fraud Policy R1–R10 in `config/policies.yaml` is transcribed verbatim from the
  official dataset README (§3).
- Never download the original IEEE-CIS/Kaggle data to recover outcomes
  (disqualification rule); this repo only uses the official HHGOA release.

## Config
- `config/settings.yaml` — model name, thresholds (no API key needed for mock path).
- `config/policies.yaml` — R1–R10 policy rules enforced by `policy.py`.
- `config/mcp.json` — MCP tool registry mirroring `src/mcp/tools.py`.
- `.env.example` — optional live TigerGraph (`TIGERGRAPH_HOST/USER/PASS/GRAPH`); unset = mock fallback.

## Outputs
- `cases/inputs/HHG-001.json … HHG-020.json` — 20 official benchmark inputs.
- `cases/HHG-001.json … HHG-020.json` — **submission answer files** (repo-root contract). Each carries the full investigation record: evidence, pattern signatures, fraud probability, `next_best_actions` (before/after extra evidence), `evidence_requests`, SAR block when policy requires, and the graph write-back receipt.
