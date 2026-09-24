# AGENTS.md — fraud-agent operating rules

## Project
Agentic fraud investigation over IEEE-CIS-compatible data + TigerGraph (mock fallback) + Streamlit UI.

## Stack
Python 3.11. LangGraph optional (fallback orchestrator is primary offline path). No sklearn.
Required: pytest, pyyaml, numpy. Optional: streamlit, langgraph.

## Commands
- Tests: `python -m pytest tests/ -q`
- Benchmark: `python -m src.agent.runner --all` (writes `cases/outputs/`)
- Single case: `python -m src.main --case case_01`
- UI: `streamlit run src/ui/app.py`
- Rebuild knowledge: `python -m src.graphrag.ingest_docs`
- Compile check: `python -m py_compile <file>`

## Git workflow (standing user instruction)
- The user wants a fully green GitHub contribution graph on github.com/abhyyy559 (repo: task-4).
- After every change the user can see (code, docs, config), commit AND push to `main` — don't wait to be asked. Use the footer:

  ```
  🤖 Generated with Codebuff
  Co-Authored-By: Codebuff <noreply@codebuff.com>
  ```
- Commit message style: short imperative summary line, lowercase, no scope prefix (match existing history).
- Never push broken states: run `python -m pytest tests/ -q` before committing code changes.
- Destructive git commands (force-push, reset --hard) are still forbidden without explicit user approval.

## Conventions
- snake_case Python, UPPER GSQL vertices, absolute `src.` imports.
- Never silent failure: exceptions + structured JSON.
- Every fraud finding cites evidence_ids (TransactionID / node IDs).
- All side-effect actions go through `policy.py` + `executor.py`; direct mock API calls forbidden.
- Output JSON MUST contain all 16 fields in `OUTPUT_SCHEMA` (see `src/agent/runner.py`).
- Offline-first: every module imports cleanly without langgraph/streamlit/TigerGraph.
