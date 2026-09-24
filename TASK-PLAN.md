# TASK-4 Execution Plan — Hacker House Goa (TigerGraph partner task)

Source of truth: **"TigerGraph Agentic Fraud Investigation HHGOA"**
(Google Doc linked from hhgoa.com; full text captured 2026-09-21 via the doc's
public export. This §1 is the strictly-followable rulebook.)
- Build ONLY what §1 requires.
- Do NOT deviate from §1, do NOT add features §1 does not ask for.
- Every checklist item in §3 maps 1:1 to a requirement in §1.

Repo: https://github.com/abhyyy559/task-4.git
Status: implementation exists & verified (see §2); §1 now LOCKED below.
Next: §3 gap analysis → fixes → re-verify → reviewer/tester → Abhiram approval.

## 1. Task rules (VERBATIM — locked 2026-09-21)

Source: https://docs.google.com/document/d/1AGFr8ltj8hF3CxJ2n2pWjyg7JkCsIbd9-z_kRuHP-dw/edit?usp=sharing

---
TigerGraph Agentic Fraud Investigation HHGOA

Build an AI Agent for Fraud Investigation and Next-Best Action

Fraud teams at financial institutions are under constant pressure. Analysts must manually gather transaction history, trace money movement, identify connected accounts, review policies, assess risk, document findings, and decide what action to take. This process is slow, fragmented, difficult to scale, and often completes only after the money is already gone.

This hackathon challenges participants to build an Agentic Fraud Investigation Agent powered by TigerGraph that investigates fraud and recommends the next best actions when the available signals are uncertain.

Core Challenge / Design Guidelines

Build an AI agent that investigates fraud, creates and progresses cases, and recommends the next best action when available signals are uncertain.

The challenge is to accurately identify fraud patterns, determine what action to take, identify what additional evidence is needed, and decide when there is enough information to act.
The agent:

1. Investigate fraud when triggered by:
 * A fraud signal or risk score
 * A customer report
 * A fraud analyst
2. Gather and analyze evidence from:
 * Knowledge graphs
 * Transaction history
 * Device and identity signals
 * Account behavior
 * Prior fraud cases
 * External data sources
3. Assess the situation by
 * Identifying fraud patterns
 * Determine the likely type of fraud
 * Assessing the level of risk based on available evidence.
4. Create and progress a fraud case:
 * Create a case when investigation is warranted
 * Add new evidence and findings as the investigation progresses
 * Update the case status, risk assessment, and recommended actions
 * Maintain a record of decisions and actions taken
5. Use case memory to improve investigations:
 * Store relevant findings, decisions, actions, and outcomes from prior cases
 * Retrieve similar past cases when investigating new activity
 * Use prior case outcomes and analyst decisions to inform recommendations
 * Identify recurring fraud patterns, entities, and relationships across cases
 * Update memory as new cases are resolved
6. Gather additional evidence when needed through controlled, policy-approved actions, such as:
 * Asking an account owner to validate a transaction
 * Requesting step-up authentication
 * Requesting additional information from an analyst or approved party
7. Recommend or take one or more next actions based on the evidence, such as:
 * Allow or block a transaction
 * Block or monitor an account
 * Warn a customer
 * Create a fraud case
 * File a report
 * Request more evidence
 * Escalate to a fraud analyst
8. Operate within predefined policies and permissions:
 * The agent may recommend an action
 * Only authorized actions may be executed
 * Some actions may require human approval
9. Determine when to stop the investigation once enough evidence is available to take a defensible action.
10. Explain its reasoning, including:
 * What evidence was used
 * Why additional evidence was requested
 * Why the selected actions were recommended

The core investigation flow is:
1. Trigger - start an investigation based on fraud signal, customer report, analyst request or another event
2. Investigate - create or open a case and examine the relevant entities, transactions, relationships, behavior and prior cases
3. Gather evidence - collect the evidence needed to understand the activity and update the case as new information is found
4. Assess uncertainty - determine the level of risk, confidence in the assessment and whether enough evidence exists to act
5. Gather more evidence if needed - request or obtain additional information when uncertainty remains
6. Take one or more next actions - recommend or execute appropriate actions and progress the case
7. Explain the decision - clearly describe the evidence considered, remaining uncertainty and why the actions were selected
8. Update case memory - record the investigation, actions, decisions and outcomes so they can inform future cases

Actions such as sending customer messages, freezing accounts, blocking cards, refunding customers, updating CRM systems, or closing cases may be simulated, stubbed, or represented through mock APIs.

What Participants Build With

Required components
1. TigerGraph Savanna or Community Edition.
 * Use either for graph and vector storage and retrieval
 * Both are free to use for the hackathon
 * Savanna: https://savanna.tgcloud.io
 * Community Edition: https://dl.tigergraph.com
 * If you use Savanna, ensure auto-stop and auto-start are enabled
2. GSQL and graph algorithms
 * Use GSQL and TigerGraph graph algorithms for graph traversal, pattern detection, relationship analysis, and fraud investigation.
3. TigerGraph MCP
 * Use TigerGraph MCP to expose graph capabilities and data to the agent
 * https://github.com/tigergraph/tigergraph-mcp
4. GraphRAG
 * Use GraphRAG to ground the agent with relevant evidence and context
 * This may include connected evidence retrieved from the knowledge graph and information from documents such as fraud policies, procedures and typologies
 * Pass the relevant context to the LLM rather than simply passing raw data
5. User interface
 * Provide a user interface to demonstrate the investigation, case progression, evidence, uncertainty, recommendations, and next actions
 * This can be an analyst dashboard, conversational interface, case management view or another interface of your choice

Optional components
1. Agent framework — Participants may use the framework of their choice, such as LangChain, LangGraph, OpenAI Agents SDK, CrewAI, or another agent framework. A custom agent implementation is also allowed.
2. LLM — Participants may use the LLM or combination of models of their choice. The LLM should be used for reasoning, tool selection, evidence synthesis, and generating explanations rather than replacing graph analysis.
3. Additional tools and data sources — Participants may integrate external APIs, databases, fraud signals, identity systems, or simulated customer interactions. External sources should complement the TigerGraph-based investigation.

Dataset

Here is the dataset: HHGOA_IEEE (Google Drive folder: https://drive.google.com/drive/folders/1YDJUW1fiE7Jx8R9KqknC4IcsED9zll2A?usp=sharing)

The dataset is built on the IEEE-CIS Fraud Detection data from Vesta Corporation, with every original row and column kept: about 590,000 card transactions over six months from about 13,500 customers, plus device and connection records for online transactions.
* Every transaction includes a risk score from the bank's fraud detection model. There is no "Is Fraud" flag.
* Closed investigations from the first four months are included, with cases that were confirmed as fraud and cases that were cleared.
* The dataset also includes the bank's fraud policy, five known fraud patterns, and relevant regulatory references.
* Twenty cases from the final two months are used as the benchmark. Every team will be evaluated on the same cases.
* You may extend the dataset with additional data or sources.
* Not every fraud pattern present in the data is documented.
Read the README inside the dataset first. It explains every file, every column, the answer format, and how the cases work.

Submissions

Submissions should include:
* Working agent
* GitHub repository
* Agent output on the 20 provided cases. For each case, one answer file contains
 * The case, including the internal investigation record, evidence, findings, decisions and actions taken.
 * The case should also be written to the graph
 * A suspicious activity report when required by policy
 * The next best action and required approval route recorded:
 * Before any additional evidence is requested
 * After any additional evidence is received
* 3–5 minute demo video showing the agent working end to end
* Technical blog post covering:
 * What you built
 * The architecture
 * How TigerGraph is used
 * The agentic capabilities you implemented
 * What you learned
 * What you would improve with more time
* Social media post on X or LinkedIn about what you built, your approach, or your experience building on TigerGraph, with a link to your blog post or demo. Tag @TigerGraphDB.

Judging Criteria
Investigation accuracy — 25%: Accuracy of identifying fraud patterns and quality of the fraud investigation and evidence gathered.
Next best action — 25%: Quality of the recommended actions, including how the agent handles uncertain or ambiguous fraud signals, determine when more evidence is needed and updates its recommendation as new evidence becomes available
Case summary and explainability — 10%: Quality of the case creation and progression, and clarity of the case summary, supporting evidence, reasoning, decisions and recommended actions
Agentic design and engineering — 15%: Quality of the agent architecture, tool use, workflow orchestration, memory, controls, permissions and overall implementation.
Innovation — 15%: Originality of the approach and use of graph, AI, GraphRAG, and agentic capabilities.
Demo quality and completeness — 10%: Clarity and effectiveness of the end-to-end demonstration.

What Success Looks Like
A successful solution should demonstrate that the agent can:
1. Investigate a fraud case from an initial trigger.
2. Gather relevant evidence from the graph and other available sources.
3. Identify fraud patterns and assess risk.
4. Create and progress a fraud case as new evidence and decisions are added
5. Recognize when the available evidence is not sufficient or uncertain
6. Gather additional evidence through controlled actions when needed.
7. Recommend one or more appropriate next actions and update those recommendations as new evidence becomes available
8. Explain the evidence, reasoning, uncertainty and decisions behind its recommendations.
9. Operate within defined policies, permissions and approval requirements
10. Use prior cases and outcomes as memory to inform new investigations
11. Present the investigation, case progression and recommended actions clearly through a usable interface.
The strongest solutions will show that the agent can move from uncertain fraud signals to a clear, defensible course of action, while maintaining a complete case record and using past investigations to improve future decisions

Support
TigerGraph Mentors and Judges answer questions on the TigerGraph Discord: https://discord.gg/7JMkCAy9D3
Or reach out directly to Devanshu, DevRel at TigerGraph: +91 7404313376
Join the TigerGraph WhatsApp group - quick doubts, announcements, and updates.
---

## 2. Verified baseline (2026-09-21, official-spec rebuild, this session)

Official dataset obtained and verified: `data/HHGOA_IEEE_real/HHGOA_IEEE/`
(590,742 txns / 144,432 identities / 5,565 closed cases; 704 MB, gitignored).
Old 16-field/`case_NN` structure replaced by the official nested answer schema
(`case_id`, `case`, `evidence_requests`, `next_best_actions`, `sar`,
`stop_reason`, `tool_calls`, `tokens`, `latency_s`); inputs `cases/inputs/HHG-*.json`,
answers `cases/HHG-*.json`.

- `pytest tests/ -q` → **42/42 pass** (incl. structuring-detector + WCC union-find tests)
- `python -m src.agent.runner --all` → **20/20 ok, 0 failed** (~100 s)
- Latest distribution: 6 legitimate / 10 uncertain / 4 fraud; patterns: none×14,
  undocumented×1, card_testing×1, card_not_present_new_device×1,
  account_takeover×3; SARs filed: 6
- Invariant verification (this session): 0 errors across official top-level keys,
  verdict/status/pattern/action/route vocabularies, FILE_REPORT⇔sar.file agreement,
  final==initial when no evidence requested, exposure == |Σ affected txns|,
  legitimate ⇒ no affected/exposure/SAR, all IDs resolvable
- No label leakage: no `isFraud`/`is_fraud` reads in `src/agent|actions|ui`;
  no `attacker`/`emu-spoof`/`office-pc`/`corp-nat` heuristics remain
- R1–R10 in `config/policies.yaml` verified **verbatim** against the official
  dataset README §3 (programmatic diff, this session)
- GSQL: `schema.gsql` + 8 queries in `queries.gsql` (added `q_get_transactions`,
  `q_ring_components` = genuine WCC label-propagation algorithm); CASE-vertex
  upsert fixed to schema type `CASE`; `.env.example` vars aligned to code
- MCP: `tigergraph-mcp==1.0.3` installed; bridge mapping-complete incl.
  `ring_components`; offline tests green; **not** exercised against live
  TigerGraph (no credentials) — recorded as an honest limitation

Key calibration fixes this session (evidence-grounded, from the dataset's own
closed cases): region-cluster now requires foreign-home cards + burst activity;
device coordination requires per-card-baseline bursts (was: any 3 txns);
structuring detector added (≥3 near-threshold online txns/hour within 72 h of
the flag; stale windows ignored). SAR count fell 16 → 6; undocumented 12 → 2.

Independent gates: **pending** — fresh reviewer + tester must pass over the
final diff before any commit (standing rule). No commits yet (Abhiram's rule).

## 2b. Superseded pre-rebuild baseline (kept for history)

- `pytest tests/ -q` → 28/28 pass; `runner --all` → 20/20 on the old 16-field schema.
- Tester PASS (2026-09-21); Reviewer REQUEST CHANGES (B1/B2/M1/M2/M3 + m1) —
  addressed in the rebuild above.
- Reviewer: **REQUEST CHANGES** — must-fix: (B1) dedupe 5 doubly-defined funcs in
  `src/agent/policy.py`; (B2) remove ground-truth `pattern`/`label` consumption from
  the investigation path (RAG seeding, `fraud_pattern` output, explanation,
  `block_device` policy context); (M1) wire `takeover` findings into `score_signals`,
  replace `attacker`/`emu-spoof`/`office-pc`/`corp-nat` magic substrings with
  query-derived evidence; (M2) fix `ORDER BY` in `q_mule_fanout` (invalid GSQL in
  SELECT); (M3) merge duplicate `thresholds:` blocks in `config/policies.yaml`;
  minors: remove "Expected label" from UI (m1), use FRAUD/ESCALATE_THRESHOLD consts.

## 3. Requirement → evidence checklist (from §1)

### Agent capabilities (Core Challenge 1–10)
| # | Requirement (§1 rule) | Repo evidence | Status |
|---|----------------------|---------------|--------|
| 1 | Investigate on trigger: fraud signal / risk score, customer report, analyst | `src/main.py --case`, UI `run_live_investigation`, runner `--all` | ✅ have |
| 2 | Evidence from: knowledge graphs, txn history, device/identity signals, account behavior, prior cases, external sources | MCP tools (graph), GraphRAG (prior cases + policy docs); "external sources" thin | ⚠️ partial |
| 3 | Assess: identify fraud patterns, likely type, risk level from evidence | `score_signals` + `decide_verdict`; `fraud_pattern` output | ⚠️ pattern currently = case-input label (B2) — must be evidence-derived |
| 4 | Create & progress case: add evidence/findings, update status/risk/actions, record decisions | case outputs + memory store | ⚠️ "written to the graph" missing (see Submissions) |
| 5 | Case memory: store findings/decisions/outcomes, retrieve similar cases, inform recommendations, update on resolve | `src/agent/memory.py` | ✅ have |
| 6 | Controlled evidence gathering: ask owner, step-up auth, ask analyst | `request_step_up_auth`, `request_more_evidence` mock actions | ✅ have (simulated) |
| 7 | Next actions: allow/block txn, block/monitor account, warn customer, create case, file report, request evidence, escalate | `propose_actions` + policy engine | ⚠️ file_sar never proposed; no before/after-evidence recording |
| 8 | Policies/permissions: recommend vs execute, human approval | policy engine default-deny, approvers | ✅ have |
| 9 | Stop when enough evidence for defensible action | risk/confidence thresholds | ✅ have |
| 10 | Explain: evidence used, why more evidence requested, why actions selected | `explanation`, `recommended_next_steps` | ✅ have |

### Required components
| # | Requirement (§1 rule) | Repo evidence | Status |
|---|----------------------|---------------|--------|
| R1 | TigerGraph Savanna or CE for graph + vector storage/retrieval | schema.gsql + mock; `_init_live()` claims live but queries require mock | ❌ live path not genuinely implemented |
| R2 | GSQL + graph algorithms for traversal/pattern detection | 6 GSQL queries; no algorithm calls (e.g. WCC/PageRank); ORDER BY bug (M2) | ⚠️ partial |
| R3 | TigerGraph MCP to expose graph capabilities to the agent | `src/mcp/` is a custom shim, not tigergraph-mcp | ⚠️ partial |
| R4 | GraphRAG grounding with relevant evidence + context | `src/graphrag/` retriever + 18-chunk store | ✅ have |
| R5 | UI demonstrating investigation, case progression, evidence, uncertainty, recommendations, next actions | Streamlit `src/ui/app.py` | ✅ have (minus label-leak fix m1) |

### Dataset
| # | Requirement (§1 rule) | Repo evidence | Status |
|---|----------------------|---------------|--------|
| D1 | Use HHGOA_IEEE (IEEE-CIS, ~590k txns, risk scores, no isFraud flag, 20 official benchmark cases, README answer format) | synthetic 200-row CSV with isFraud labels; 20 synthetic cases | ❌ dataset not obtained; answer format from dataset README unknown |

### Submissions
| # | Requirement (§1 rule) | Repo evidence | Status |
|---|----------------------|---------------|--------|
| S1 | Working agent | ✅ verified | ✅ have |
| S2 | GitHub repository | https://github.com/abhyyy559/task-4.git | ✅ have |
| S3 | Per-case answer file: investigation record + evidence + findings + decisions + actions | 16-field JSON outputs | ⚠️ missing: next-best-action + approval route BEFORE/AFTER extra evidence; SAR; case-written-to-graph record |
| S4 | 3–5 min demo video, agent working end to end | — | ❌ missing |
| S5 | Technical blog post (6 bullets) | `docs/blog.md` exists — coverage vs 6 bullets unverified | ⚠️ verify |
| S6 | Social post on X/LinkedIn tagging @TigerGraphDB (with blog/demo link) | — | ❌ draft needed (Abhiram posts himself) |

## 4. Build loop

1. §1 LOCKED ✅ (2026-09-21). §3 checklist filled ✅.
2. Fix gaps in priority order, re-running `pytest` + `runner --all` after each fix.
   Priority: (a) reviewer must-fixes B1/B2/M1/M2/M3 + m1 (correctness/integrity —
   B2/M1 change scoring, must re-verify 20/20); (b) S3 answer-file fields
   (before/after next-best-action + approval route, SAR, graph-write record);
   (c) R1 genuine live-TigerGraph path (pyTigerGraph, fallback to mock);
   (d) R2 fix ORDER BY + add/verify algorithm usage; (e) R3 tigergraph-mcp
   integration note/config; (f) S4 demo video; (g) S5 blog gap-fill;
   (h) S6 social draft; (i) D1 dataset — attempt Drive listing via live browser;
   if unobtainable, document as the key open item for Abhiram.
3. Independent reviewer agent + tester agent pass over the final diff
   (standing rule before any commit).
4. Present diff + proof to Abhiram for merge approval (no commits without his OK).

## 5. What we will NOT do (out of scope per the strict-rules mandate)

- No new fraud patterns, features, or UI beyond §1.
- No real TigerGraph Savanna provisioning (needs Abhiram's account) — implement the
  genuine client path + docs; live proof needs his credentials.
- No submission/posting on Abhiram's behalf (X post, Devfolio submit) — drafts only.
- No inventing the dataset README's answer format — flag as open item if unobtainable.
