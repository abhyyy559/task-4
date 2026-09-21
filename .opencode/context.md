# Project Context

## Environment
- Language: Python 3.11.9 (verified via `python --version`)
- Runtime: CPython 3.11, pip 24.0
- Build: none yet (will use `pyproject.toml` + venv)
- Test: pytest (to be added)
- Package Manager: pip (no lockfile yet)

## Project Type
- [x] Application (agentic fraud investigation + Streamlit UI)
- [ ] Library/Package
- Monorepo: no, single Python package `fraud-agent`

## Infrastructure
- Container: None
- Orchestration: None
- CI/CD: None yet
- Cloud: TigerGraph Savanna (target) / local mock fallback

## Structure (to be scaffolded in workspace root = fraud-agent/)
- Source: `src/` (agent, tigergraph, graphrag, actions, ui)
- Tests: `tests/`
- Docs: `docs/`
- Entry: `src/main.py`, `src/ui/app.py`, `src/agent/runner.py`
- Config: `config/settings.yaml`, `config/policies.yaml`, `config/mcp.json`
- Cases: `cases/inputs/`, `cases/outputs/`
- Data: `data/HHGOA_IEEE/` (MISSING — will synthesize IEEE-CIS-compatible stub)

## Conventions (to enforce)
- Naming: snake_case (py), UPPER for GSQL vertices
- Imports: absolute from `src.`
- Error handling: exceptions + structured JSON returns, never silent
- Testing: pytest unit + benchmark runner integration
- Every finding must cite evidence IDs; all actions via policy engine

## Discovery Notes (2026-09-19)
- Workspace `task-4/` empty except `.opencode/todo.md` placeholder.
- `data/HHGOA_IEEE/README.md` NOT FOUND anywhere under `hhgoaa/`. Siblings (hhgoa, task-2, task-3) contain no IEEE data.
- Decision: synthesize faithful HHGOA_IEEE-compatible stub from public IEEE-CIS Fraud Detection schema (TransactionID, card/product/M/C/D/V features, isFraud) + spec's 5 fraud patterns + 20 benchmark cases. Document assumptions in PLAN.md.
- Classification (brainstorming skill): ARCHITECTURAL — new multi-subsystem project. User pre-approved full build ("Yes. Treat as full build"), so proceeding without additional approval gate per autonomous mandate.
- Stack: LangGraph (with graceful fallback to custom orchestrator if not installed), Streamlit UI, TigerGraph MCP (with local JSON mock fallback so demo runs without live TG), scikit-learn-free lightweight vector search (numpy) to avoid heavy deps.

## Verification Frontier
- `python -m pytest tests/ -q`
- `python -m src.agent.runner --all` (benchmark, writes cases/outputs/)
- `streamlit run src/ui/app.py` (manual)
- `python -m py_compile` per module
