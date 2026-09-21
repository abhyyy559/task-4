# Mission: Agentic fraud investigation + Streamlit UI (`fraud-agent`)

> Workspace root = repo root. Do NOT create a subfolder. Source: `src/`, tests: `tests/`, docs: `docs/`,
> config: `config/`, cases: `cases/`, data stub: `data/HHGOA_IEEE/`.
> Stack: Python 3.11, LangGraph (with fallback orchestrator), Streamlit, TigerGraph Savanna w/ local mock fallback.
> Conventions: snake_case (py), UPPER vertices (GSQL), absolute `src.` imports, exceptions + structured JSON, evidence IDs cited.

## File Manifest

| Action | File Path | Description | Dependencies |
|--------|-----------|-------------|--------------|
| CREATE | AGENTS.md | Agent operating rules for repo | - |
| CREATE | README.md | Repo stub (overview, quickstart) | - |
| CREATE | PLAN.md | Data synthesis + design plan (Planner-authored) | - |
| CREATE | pyproject.toml | Packaging, deps, pytest config | - |
| CREATE | src/__init__.py | Package marker | - |
| CREATE | src/agent/__init__.py | Package marker | - |
| CREATE | src/tigergraph/__init__.py | Package marker | - |
| CREATE | src/graphrag/__init__.py | Package marker | - |
| CREATE | src/mcp/__init__.py | Package marker | - |
| CREATE | src/actions/__init__.py | Package marker | - |
| CREATE | src/ui/__init__.py | Package marker | - |
| CREATE | data/HHGOA_IEEE/transactions.csv | Synthetic IEEE-CIS-compatible transactions | PLAN.md |
| CREATE | data/HHGOA_IEEE/identity.csv | Synthetic identity table | PLAN.md |
| CREATE | data/HHGOA_IEEE/patterns.md | 5 fraud pattern definitions | PLAN.md |
| CREATE | data/HHGOA_IEEE/README.md | Provenance + synthesis note | PLAN.md |
| CREATE | src/tigergraph/schema.gsql | Vertex/edge schema DDL | data stub |
| CREATE | src/tigergraph/queries.gsql | 6 named GSQL queries (built in 2 steps) | schema.gsql |
| CREATE | src/tigergraph/client.py | TG client + JSON mock fallback | queries.gsql |
| CREATE | src/graphrag/ingest_docs.py | Docs → chunks → vectors store | patterns.md |
| CREATE | src/graphrag/retriever.py | Lightweight numpy vector search | ingest_docs.py |
| CREATE | src/mcp/tools.py | MCP tool wrappers over client+retriever | client.py, retriever.py |
| CREATE | config/mcp.json | MCP server/tool registry | tools.py |
| CREATE | src/agent/state.py | Agent state schema | - |
| CREATE | src/agent/prompts.py | System/investigator prompts | state.py |
| CREATE | src/agent/memory.py | Conversation/case memory | state.py |
| CREATE | config/policies.yaml | Action policy rules | - |
| CREATE | src/agent/policy.py | Policy engine (allow/deny/escalate) | policies.yaml |
| CREATE | src/agent/orchestrator.py | Fallback orchestrator (no-LangGraph path) | state.py, prompts.py |
| CREATE | src/agent/graph.py | LangGraph nodes + fallback wiring | orchestrator.py, policy.py, tools.py |
| CREATE | src/actions/mock_apis.py | Simulated external APIs | - |
| CREATE | src/actions/executor.py | Policy-gated action executor | policy.py, mock_apis.py |
| CREATE | src/main.py | CLI entry wiring agent | graph.py, executor.py |
| CREATE | config/settings.yaml | App settings | - |
| CREATE | .env.example | Env template (TG creds etc.) | - |
| CREATE | src/agent/runner.py | Benchmark runner (writes cases/outputs/) | graph.py, settings.yaml |
| CREATE | cases/inputs/case_01.json … case_20.json | 20 benchmark cases (5 patterns × 4) | PLAN.md, runner.py contract |
| CREATE | src/ui/app.py | Streamlit investigation UI | runner.py |
| CREATE | docs/architecture.md | System architecture doc | implementation |
| CREATE | docs/demo.md | Demo walkthrough | app.py, runner.py |
| CREATE | docs/blog_draft.md | Blog post draft | architecture.md |
| CREATE | docs/social_draft.md | Social announcement draft | blog_draft.md |
| CREATE | tests/test_policy.py | Policy engine unit tests | policy.py |
| CREATE | tests/test_graph.py | Graph/orchestrator unit tests | graph.py |
| CREATE | tests/test_retriever.py | Retriever unit tests | retriever.py |
| CREATE | tests/test_runner.py | Runner integration tests | runner.py |

## M1: Foundation | status: completed
### T1.1: Repo docs & plan | agent:Worker | parallel-group:1
- [x] S1.1.1: CREATE `AGENTS.md` (agent operating rules) | agent:Worker | file:AGENTS.md | size:S
- [x] S1.1.2: CREATE `README.md` (overview + quickstart stub) | agent:Worker | file:README.md | size:S
- [x] S1.1.3: CREATE `PLAN.md` (Planner drafts; Worker verifies/extends if missing) | agent:Worker | file:PLAN.md | size:S
### T1.2: Packaging & scaffold | agent:Worker | parallel-group:1
- [x] S1.2.1: CREATE `pyproject.toml` (deps: langgraph, streamlit, pyyaml, numpy, pytest) | agent:Worker | file:pyproject.toml | size:S
- [x] S1.2.2: CREATE `src/__init__.py` | agent:Worker | file:src/__init__.py | size:XS
- [x] S1.2.3: CREATE `src/agent/__init__.py` | agent:Worker | file:src/agent/__init__.py | size:XS
- [x] S1.2.4: CREATE `src/tigergraph/__init__.py` | agent:Worker | file:src/tigergraph/__init__.py | size:XS
- [x] S1.2.5: CREATE `src/graphrag/__init__.py` | agent:Worker | file:src/graphrag/__init__.py | size:XS
- [x] S1.2.6: CREATE `src/mcp/__init__.py` | agent:Worker | file:src/mcp/__init__.py | size:XS
- [x] S1.2.7: CREATE `src/actions/__init__.py` | agent:Worker | file:src/actions/__init__.py | size:XS
- [x] S1.2.8: CREATE `src/ui/__init__.py` | agent:Worker | file:src/ui/__init__.py | size:XS
### T1.3: Synthetic IEEE data stub | agent:Worker | parallel-group:1
- [x] S1.3.1: CREATE `data/HHGOA_IEEE/transactions.csv` (IEEE-CIS cols + isFraud, per PLAN.md) | agent:Worker | file:data/HHGOA_IEEE/transactions.csv | size:M
- [x] S1.3.2: CREATE `data/HHGOA_IEEE/identity.csv` (TransactionID + id_01–id_38 + device) | agent:Worker | file:data/HHGOA_IEEE/identity.csv | size:M
- [x] S1.3.3: CREATE `data/HHGOA_IEEE/patterns.md` (5 fraud pattern definitions) | agent:Worker | file:data/HHGOA_IEEE/patterns.md | size:S
- [x] S1.3.4: CREATE `data/HHGOA_IEEE/README.md` (provenance + synthesis note) | agent:Worker | file:data/HHGOA_IEEE/README.md | size:S
### T1.4: M1 review | agent:Reviewer | depends:T1.1,T1.2,T1.3
- [x] S1.4.1: Verify scaffold imports + `py_compile` sweep of M1 files | agent:Reviewer | size:S

## M2: TigerGraph layer | status: completed | depends:M1
### T2.1: Schema & queries | agent:Worker | parallel-group:2
- [x] S2.1.1: CREATE `src/tigergraph/schema.gsql` (vertices/edges per PLAN.md mapping) | agent:Worker | file:src/tigergraph/schema.gsql | size:M
- [x] S2.1.2: CREATE `src/tigergraph/queries.gsql` (queries 1–3: card ring, device cluster, mule fan-out) | agent:Worker | file:src/tigergraph/queries.gsql | size:M
- [x] S2.1.3: MODIFY `src/tigergraph/queries.gsql` (append queries 4–6: takeover, synthetic id, evidence subgraph) | agent:Worker | file:src/tigergraph/queries.gsql | depends:S2.1.2 | size:M
### T2.2: Client | agent:Worker | parallel-group:2
- [x] S2.2.1: CREATE `src/tigergraph/client.py` (Savanna client + local JSON mock fallback) | agent:Worker | file:src/tigergraph/client.py | size:M
### T2.3: M2 review | agent:Reviewer | depends:T2.1,T2.2
- [x] S2.3.1: Review GSQL coverage (6 queries vs 5 patterns) + `py_compile` client | agent:Reviewer | size:S

## M3: MCP tools + GraphRAG | status: completed | depends:M1
### T3.1: GraphRAG ingest | agent:Worker | parallel-group:2
- [x] S3.1.1: CREATE `src/graphrag/ingest_docs.py` (chunk + embed + persist vector store) | agent:Worker | file:src/graphrag/ingest_docs.py | size:M
### T3.2: GraphRAG retriever | agent:Worker | parallel-group:2
- [x] S3.2.1: CREATE `src/graphrag/retriever.py` (numpy cosine search, no sklearn) | agent:Worker | file:src/graphrag/retriever.py | size:M
### T3.3: MCP tools | agent:Worker | depends:T2.2 | parallel-group:3
- [x] S3.3.1: CREATE `src/mcp/tools.py` (tool wrappers over client + retriever) | agent:Worker | file:src/mcp/tools.py | size:M
- [x] S3.3.2: CREATE `config/mcp.json` (server/tool registry matching tools.py) | agent:Worker | file:config/mcp.json | depends:S3.3.1 | size:S
### T3.4: M3 review | agent:Reviewer | depends:T3.1,T3.2,T3.3
- [x] S3.4.1: Verify ingest→retrieve round-trip on patterns.md + `py_compile` | agent:Reviewer | size:S

## M4: Agent core | status: completed | depends:M3
### T4.1: State, prompts, memory | agent:Worker | parallel-group:4
- [x] S4.1.1: CREATE `src/agent/state.py` (investigation state schema) | agent:Worker | file:src/agent/state.py | size:S
- [x] S4.1.2: CREATE `src/agent/prompts.py` (planner/investigator/reporter prompts) | agent:Worker | file:src/agent/prompts.py | size:S
- [x] S4.1.3: CREATE `src/agent/memory.py` (case + conversation memory) | agent:Worker | file:src/agent/memory.py | size:S
### T4.2: Policy engine | agent:Worker | parallel-group:4
- [x] S4.2.1: CREATE `config/policies.yaml` (allow/deny/escalate rules per action) | agent:Worker | file:config/policies.yaml | size:S
- [x] S4.2.2: CREATE `src/agent/policy.py` (engine enforcing policies.yaml) | agent:Worker | file:src/agent/policy.py | depends:S4.2.1 | size:M
### T4.3: Agent graph | agent:Worker | depends:T4.1 | parallel-group:5
- [x] S4.3.1: CREATE `src/agent/orchestrator.py` (fallback orchestrator: plan→tools→synthesize) | agent:Worker | file:src/agent/orchestrator.py | size:M
- [x] S4.3.2: CREATE `src/agent/graph.py` (LangGraph nodes; fallback to orchestrator if langgraph missing) | agent:Worker | file:src/agent/graph.py | depends:S4.3.1 | size:M
### T4.4: Actions | agent:Worker | parallel-group:5
- [x] S4.4.1: CREATE `src/actions/mock_apis.py` (simulated freeze/notify/escalate APIs) | agent:Worker | file:src/actions/mock_apis.py | size:S
- [x] S4.4.2: CREATE `src/actions/executor.py` (policy-gated action execution) | agent:Worker | file:src/actions/executor.py | depends:T4.2 | size:M
### T4.5: Entry | agent:Worker | depends:T4.3,T4.4 | parallel-group:6
- [x] S4.5.1: CREATE `src/main.py` (CLI wiring graph + executor) | agent:Worker | file:src/main.py | size:S
### T4.6: M4 review | agent:Reviewer | depends:T4.1,T4.2,T4.3,T4.4,T4.5
- [x] S4.6.1: Verify single-case end-to-end (mock) + every action passes policy + evidence IDs cited | agent:Reviewer | size:M

## M5: UI + benchmark | status: completed | depends:M4
### T5.1: Config & runner | agent:Worker | parallel-group:6
- [x] S5.1.1: CREATE `config/settings.yaml` (model, TG, paths, thresholds) | agent:Worker | file:config/settings.yaml | size:S
- [x] S5.1.2: CREATE `.env.example` (TG creds + model keys template) | agent:Worker | file:.env.example | size:XS
- [x] S5.1.3: CREATE `src/agent/runner.py` (benchmark: all cases → cases/outputs/ JSON) | agent:Worker | file:src/agent/runner.py | size:M
### T5.2: Pattern A — card-not-present ring (4 cases) | agent:Worker | parallel-group:6
- [x] S5.2.1: CREATE `cases/inputs/case_01.json` (ring, high-velocity shared card) | agent:Worker | file:cases/inputs/case_01.json | size:S
- [x] S5.2.2: CREATE `cases/inputs/case_02.json` (ring, cross-merchant shared email) | agent:Worker | file:cases/inputs/case_02.json | size:S
- [x] S5.2.3: CREATE `cases/inputs/case_03.json` (ring, borderline — shared card, legit-looking amounts) | agent:Worker | file:cases/inputs/case_03.json | size:S
- [x] S5.2.4: CREATE `cases/inputs/case_04.json` (ring, negative control — family shared card, legit) | agent:Worker | file:cases/inputs/case_04.json | size:S
### T5.3: Pattern B — account takeover (4 cases) | agent:Worker | parallel-group:6
- [x] S5.3.1: CREATE `cases/inputs/case_05.json` (takeover, new device + addr change) | agent:Worker | file:cases/inputs/case_05.json | size:S
- [x] S5.3.2: CREATE `cases/inputs/case_06.json` (takeover, email change + high amount) | agent:Worker | file:cases/inputs/case_06.json | size:S
- [x] S5.3.3: CREATE `cases/inputs/case_07.json` (takeover, borderline — travel device change) | agent:Worker | file:cases/inputs/case_07.json | size:S
- [x] S5.3.4: CREATE `cases/inputs/case_08.json` (takeover, negative control — user upgraded phone) | agent:Worker | file:cases/inputs/case_08.json | size:S
### T5.4: Pattern C — money-mule fan-out (4 cases) | agent:Worker | parallel-group:6
- [x] S5.4.1: CREATE `cases/inputs/case_09.json` (mule, 1→N rapid dispersal) | agent:Worker | file:cases/inputs/case_09.json | size:S
- [x] S5.4.2: CREATE `cases/inputs/case_10.json` (mule, round-amount fan-out) | agent:Worker | file:cases/inputs/case_10.json | size:S
- [x] S5.4.3: CREATE `cases/inputs/case_11.json` (mule, borderline — payroll disbursement) | agent:Worker | file:cases/inputs/case_11.json | size:S
- [x] S5.4.4: CREATE `cases/inputs/case_12.json` (mule, negative control — marketplace payouts) | agent:Worker | file:cases/inputs/case_12.json | size:S
### T5.5: Pattern D — device-spoofing cluster (4 cases) | agent:Worker | parallel-group:6
- [x] S5.5.1: CREATE `cases/inputs/case_13.json` (spoof, many cards one DeviceInfo) | agent:Worker | file:cases/inputs/case_13.json | size:S
- [x] S5.5.2: CREATE `cases/inputs/case_14.json` (spoof, emulator fingerprint reuse) | agent:Worker | file:cases/inputs/case_14.json | size:S
- [x] S5.5.3: CREATE `cases/inputs/case_15.json` (spoof, borderline — shared kiosk device) | agent:Worker | file:cases/inputs/case_15.json | size:S
- [x] S5.5.4: CREATE `cases/inputs/case_16.json` (spoof, negative control — corporate NAT device) | agent:Worker | file:cases/inputs/case_16.json | size:S
### T5.6: Pattern E — synthetic identity (4 cases) | agent:Worker | parallel-group:6
- [x] S5.6.1: CREATE `cases/inputs/case_17.json` (synthetic, thin file + high velocity) | agent:Worker | file:cases/inputs/case_17.json | size:S
- [x] S5.6.2: CREATE `cases/inputs/case_18.json` (synthetic, mismatched identity signals) | agent:Worker | file:cases/inputs/case_18.json | size:S
- [x] S5.6.3: CREATE `cases/inputs/case_19.json` (synthetic, borderline — new immigrant thin file) | agent:Worker | file:cases/inputs/case_19.json | size:S
- [x] S5.6.4: CREATE `cases/inputs/case_20.json` (synthetic, negative control — student first card) | agent:Worker | file:cases/inputs/case_20.json | size:S
### T5.7: UI | agent:Worker | depends:T5.1 | parallel-group:7
- [x] S5.7.1: CREATE `src/ui/app.py` (Streamlit: case select, evidence view, actions, outputs) | agent:Worker | file:src/ui/app.py | size:M
### T5.8: M5 review | agent:Reviewer | depends:T5.1,T5.2,T5.3,T5.4,T5.5,T5.6,T5.7
- [x] S5.8.1: Run `python -m src.agent.runner --all`, verify 20 outputs match 16-field schema | agent:Reviewer | size:M

## M6: Docs + verification | status: completed | depends:M5
### T6.1: Docs | agent:Worker | parallel-group:8
- [x] S6.1.1: CREATE `docs/architecture.md` (components, data flow, TG + GraphRAG + agent) | agent:Worker | file:docs/architecture.md | size:M
- [x] S6.1.2: CREATE `docs/demo.md` (demo script: runner + UI walkthrough) | agent:Worker | file:docs/demo.md | size:S
- [x] S6.1.3: CREATE `docs/blog_draft.md` (project blog post draft) | agent:Worker | file:docs/blog_draft.md | size:S
- [x] S6.1.4: CREATE `docs/social_draft.md` (announcement post draft) | agent:Worker | file:docs/social_draft.md | size:XS
### T6.2: Tests | agent:Worker | parallel-group:8
- [x] S6.2.1: CREATE `tests/test_policy.py` (allow/deny/escalate unit tests) | agent:Worker | file:tests/test_policy.py | size:S
- [x] S6.2.2: CREATE `tests/test_graph.py` (nodes + fallback orchestrator tests) | agent:Worker | file:tests/test_graph.py | size:S
- [x] S6.2.3: CREATE `tests/test_retriever.py` (retrieval recall on patterns.md) | agent:Worker | file:tests/test_retriever.py | size:S
- [x] S6.2.4: CREATE `tests/test_runner.py` (schema + outputs integration tests) | agent:Worker | file:tests/test_runner.py | size:S
### T6.3: Final verification | agent:Reviewer | depends:T6.1,T6.2
- [x] S6.3.1: Full pass — `pytest tests/ -q` + `runner --all` + `py_compile` sweep | agent:Reviewer | size:M
- [x] S6.3.2: UI smoke — `streamlit run src/ui/app.py` import/compile check | agent:Reviewer | size:S
