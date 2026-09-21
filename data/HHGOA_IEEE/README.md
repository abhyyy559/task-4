# HHGOA_IEEE data README (synthetic stub)

## Provenance

The expected source `data/HHGOA_IEEE/` (real HHGOA IEEE transaction data) was
**NOT FOUND** in this workspace or its siblings (verified 2026-09-19).
This directory is a **synthetic, IEEE-CIS-Fraud-Detection-compatible stub**
created so the full agentic pipeline, benchmark and UI run offline.

Schema basis: public IEEE-CIS Fraud Detection (Kaggle) — TransactionID,
isFraud, TransactionDT, TransactionAmt, ProductCD, card1–6, addr1–2, dist1–2,
P/R_emaildomain, M1–9, C1–14, D1–15, V1–339, DeviceType, DeviceInfo, plus
identity id_01–id_38.

## Generation

- Generator: seeded RNG `seed=42` (see build notes in work-log ses_4).
- `transactions.csv`: 200 rows, TransactionID 1001–1200, 60 fraud rows
  (12 per pattern x 5 patterns, hand-wired per `patterns.md`) + 134 legit
  background rows including 6 negative controls.
- `identity.csv`: 120 rows (all 60 fraud + 60 legit sample), TransactionID-keyed,
  id_01–id_12 + DeviceType/DeviceInfo mirroring transactions.csv.
- Nulls are empty fields. `isFraud` is ground truth for benchmark scoring
  ONLY — the agent never reads it at investigation time.

## Scope limits (documented, not hidden)

- Only V1–V20 populated (V21–V339 omitted); only C1–C5 (of C1–C14) and D1–D5
  (of D1–D15) populated; identity only id_01–id_12 (of id_01–id_38).
- Fraud rows are stylized (round amounts, clean spacings) — good for pipeline
  testing, not for model training.

## Files

- `transactions.csv` — transaction table (PK TransactionID).
- `identity.csv` — identity table (FK TransactionID).
- `patterns.md` — 5 fraud pattern definitions; GraphRAG corpus seed.

## Replacing with real data

1. Drop real `transactions.csv` / `identity.csv` here with the same PK/FK and
   column names (extra V/C/D/id_ columns are tolerated — nullable by design).
2. Update this README with source + row counts.
3. Re-run `python -m src.graphrag.ingest_docs` and
   `python -m src.agent.runner --all` to refresh knowledge + benchmark.
