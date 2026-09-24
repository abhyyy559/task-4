# Demo walkthrough

## 1. Setup (offline, ~2 min)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"      # pytest, pyyaml, numpy
python -m pytest tests/ -q    # expect: 47/47 pass
```

Place the official 704 MB dataset at `data/HHGOA_IEEE_real/HHGOA_IEEE/`
(see `TASK-PLAN-APPENDIX-README.md` for the Drive link).

## 2. Single investigation

```bash
python -m src.agent.runner --case HHG-011
```

Shows the official nested answer: verdict=fraud, pattern=card_testing,
evidence with cited transaction IDs, next-best actions with approval routes
(auto/L1/L2), and the SAR decision. Contrast:

```bash
python -m src.agent.runner --case HHG-001   # legitimate: closed, no actions
python -m src.agent.runner --case HHG-002   # uncertain: escalated to analyst
```

## 3. Full benchmark (20 cases, ~100 s)

```bash
python -m src.agent.runner --all
```

Writes `cases/HHG-001.json … HHG-020.json`. Every answer validates the
official schema; the run prints per-case verdicts. Latest: 6 legitimate /
10 uncertain / 4 fraud, 6 SARs filed.

## 4. Knowledge rebuild

```bash
python -m src.graphrag.ingest_docs   # official patterns + policy + closed cases -> store
```

## 5. UI (needs streamlit)

```bash
pip install streamlit
streamlit run src/ui/app.py
```

Pick a case → "Load saved answer" (or "Run investigation" for a live run) →
verdict, pattern description, evidence table, similar prior cases, SAR,
next-best actions (initial vs final).

## Talking points

- Offline-first: TigerGraph/LangGraph/Streamlit all optional with fallbacks.
- No label leakage by construction (ground truth never read at investigation time).
- Policy R1–R10 verbatim from the official README; uncertain cases escalate, never auto-block.
- Genuine graph algorithm: `q_ring_components` (WCC label propagation) finds device-linked card rings.
