# AGENTS.md — fraud-agent operating rules

## Project
Agentic fraud investigation over the official HHGOA_IEEE dataset (TigerGraph
target, mock/offline fallback) + Streamlit UI. Answers follow the official
three-part format: case record, SAR, next-best actions.

## Stack
Python 3.11. LangGraph optional (fallback orchestrator is primary offline path). No sklearn.
Required: pytest, pyyaml, numpy. Optional: streamlit, langgraph.

## Commands
- Tests: `python -m pytest tests/ -q`
- Benchmark: `python -m src.agent.runner --all` (writes `cases/HHG-*.json`)
- Single case: `python -m src.agent.runner --case HHG-001`
- UI: `streamlit run src/ui/app.py`
- Rebuild knowledge: `python -m src.graphrag.ingest_docs`
- Compile check: `python -m py_compile <file>`
- Dataset: `HHGOA_DATA_DIR=data/HHGOA_IEEE_real/HHGOA_IEEE` (default discovery)

## Conventions
- snake_case Python, UPPER GSQL vertices, absolute `src.` imports.
- Never silent failure: exceptions + structured JSON.
- Every fraud finding cites evidence as {claim, source, ref, entity_ids}.
- All side-effect actions go through `policy.py` + `executor.py`; direct mock API calls forbidden. Only `auto`-route actions execute; L1/L2 are recorded as recommendations awaiting human approval.
- Output JSON MUST validate against the official answer format (`src/agent/state.py::validate_output`): top-level case_id, case{}, evidence_requests[], next_best_actions{}, sar{}, stop_reason, tool_calls, tokens, latency_s. Answers live in `cases/HHG-*.json`.
- Verdicts: fraud | legitimate | uncertain. `escalated` is a case *status*, not a verdict.
- Patterns are inferred from evidence only — never read case labels/hints: card_testing | card_not_present_fraud | card_not_present_new_device | out_of_region_use | account_takeover | undocumented | none.
- Policy actions use the 14 exact Fraud Policy v1.0 identifiers (config/policies.yaml); routes auto/L1/L2.
- Offline-first: every module imports cleanly without langgraph/streamlit/TigerGraph.
- Dataset: `data/HHGOA_IEEE_real/` (official download) preferred; `data/HHGOA_IEEE/` is the synthetic stub fallback and must be labeled as such. Never download the original public IEEE-CIS/Kaggle files (disqualification).
