# Demo walkthrough

## 1. Setup (offline, ~1 min)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[test]"      # pytest, pyyaml, numpy
python -m pytest tests/ -q    # expect: all pass
```

## 2. Single investigation

```bash
python -m src.main --case case_01
```

Shows the full 16-field JSON: verdict=fraud, pattern=card_not_present_ring,
evidence_ids (TXNs + CARD:/DEVICE:/EMAIL: nodes), graph_findings per query,
policy-gated actions (freeze_card allowed, block_device escalated to human).

Contrast with a clean case:

```bash
python -m src.main --case case_08   # legit: phone upgrade, no actions taken
python -m src.main --case case_04   # escalate: family card, thin-file ambiguity
```

## 3. Full benchmark (20 cases)

```bash
python -m src.agent.runner --all
```

Writes `cases/outputs/case_01.json … case_20.json`, prints per-case verdicts plus
`benchmark accuracy: 20/20`. Every output validates against the 16-field schema with zero violations.

## 4. Knowledge rebuild

```bash
python -m src.graphrag.ingest_docs   # patterns.md (+docs/*.md) -> data/vector_store.json
```

## 5. UI (needs streamlit)

```bash
pip install streamlit
streamlit run src/ui/app.py
```

Pick a case in the sidebar → Investigate → verdict metrics, explanation, evidence IDs,
graph findings, RAG citations, actions/policy tables, timeline.

## Talking points

- Offline-first: TigerGraph/LangGraph/Streamlit all optional with fallbacks.
- No label leakage by construction (isFraud stripped at the client).
- Policy sandbox: try `freeze_card` on a legit case — recorded as blocked, never executed.
- Solid benchmark: 20/20 benchmark accuracy across 5 distinct fraud patterns and negative controls (see architecture.md).
