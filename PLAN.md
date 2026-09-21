# PLAN.md — fraud-agent (agentic fraud investigation + Streamlit UI)

Date: 2026-09-19 | Author: Planner | Status: approved for build (user: "Yes. Treat as full build")

## 1. Dataset status: MISSING → synthesis decision

- **Finding:** `data/HHGOA_IEEE/README.md` was **NOT FOUND**. Searched workspace `task-4/` (empty
  except `.opencode/`) and siblings (`hhgoa/`, `hhgoa rag task-2/`, `hhgoa task-3/`) — no IEEE data anywhere.
- **Decision:** synthesize a faithful **IEEE-CIS-Fraud-Detection-compatible stub** (`data/HHGOA_IEEE/`)
  plus 20 benchmark cases. Public IEEE-CIS schema (Kaggle: TransactionID, isFraud, TransactionDT,
  TransactionAmt, ProductCD, card1–6, addr1–2, dist1–2, P/R_emaildomain, M1–9, C1–14, D1–15, V1–339,
  DeviceType/DeviceInfo, identity id_01–id_38) is the modeling base.ber
- **Assumed dataset files (to be created in M1/T1.3):**

| File | Rows | Purpose |
|------|------|---------|
| `data/HHGOA_IEEE/transactions.csv` | ~200 (seeded; ≥60 fraud) | Transaction table, IEEE-CIS columns + `isFraud` |
| `data/HHGOA_IEEE/identity.csv` | 1:1 with subset of transactions | Identity table keyed by `TransactionID` |
| `data/HHGOA_IEEE/patterns.md` | 5 sections | Fraud pattern definitions (GraphRAG corpus seed) |
| `data/HHGOA_IEEE/README.md` | — | Provenance: synthetic, schema source, seed, limits |
| `data/HHGOA_IEEE/cases.json` | index | Optional index over `cases/inputs/*.json` (runner reads dir; index convenience) |

## 2. Assumed schema (every column, dtype, meaning)

### 2.1 transactions.csv
| Column | dtype | Meaning / values |
|--------|-------|------------------|
| TransactionID | int (PK) | Unique transaction key; joins identity.csv |
| isFraud | int {0,1} | Ground-truth label (stub-seeded) |
| TransactionDT | int | Seconds from reference datetime (time ordering) |
| TransactionAmt | float | USD amount |
| ProductCD | str {W,C,H,S,R} | Product code (W=web, C, H, S, R per IEEE-CIS) |
| card1 | int | Primary card identifier (ring linkage key) |
| card2–card6 | float/int (nullable) | Secondary card attributes |
| addr1, addr2 | float (nullable) | Billing/shipping area codes (takeover signal on change) |
| dist1, dist2 | float (nullable) | Distances (billing vs shipping / device) |
| P_emaildomain | str (nullable) | Purchaser email domain |
| R_emaildomain | str (nullable) | Recipient email domain |
| M1–M9 | str {T,F} or float (nullable) | Match flags (name/address/email/phone matches) |
| C1–C14 | int (nullable) | Count features (e.g. cards per device, tx per card-window) |
| D1–D15 | float (nullable) | Timedelta features (days since last event) |
| V1–V339 | float (nullable) | Anonymized engineered features (stub: generate V1–V20 dense, rest null) |
| DeviceType | str {mobile,desktop,missing} | Device class |
| DeviceInfo | str (nullable) | Device fingerprint string (spoof-cluster key) |

### 2.2 identity.csv
| Column | dtype | Meaning |
|--------|-------|---------|
| TransactionID | int (FK) | Join key |
| id_01–id_11 | mixed (nullable) | Identity attributes (device, network, geo) |
| id_12–id_38 | mixed (nullable) | Extended identity/engineered attributes |
| DeviceType, DeviceInfo | str | Mirror of transaction device fields (authoritative for device) |

**Stub simplifications (documented):** only V1–V20 populated; C-features partially populated;
nulls allowed; seeded RNG (`seed=42`) for reproducibility; fraud rows hand-wired to the 5 patterns.

## 3. Case input format (`cases/inputs/case_NN.json`)

```json
{
  "case_id": "case_01",
  "pattern": "card_not_present_ring",
  "label": "fraud",
  "description": "…",
  "subject": { "card1": 12345, "email": "x@y.com", "device": "…", "account_id": "A-…" },
  "transaction_ids": [1001, 1002, 1003],
  "signals": { "velocity_1h": 12, "shared_card_merchants": 4 },
  "expected": { "verdict": "fraud", "min_confidence": 0.7 }
}
```

## 4. Answer/output JSON format (`cases/outputs/case_NN.json`) — exact 16-field schema

| # | Field | Type | Notes |
|---|-------|------|-------|
| 1 | case_id | str | echoes input |
| 2 | verdict | str {fraud, legit, escalate} | final decision |
| 3 | fraud_pattern | str \| null | one of 5 patterns or null |
| 4 | confidence | float 0–1 | calibrated-ish score |
| 5 | risk_score | float 0–100 | operational score |
| 6 | evidence_ids | str[] | TransactionID / node IDs cited (≥1 when fraud) |
| 7 | transactions_reviewed | int[] | TransactionIDs examined |
| 8 | entities_flagged | object | {cards[], devices[], emails[], accounts[]} |
| 9 | graph_findings | object[] | {query, summary, node_count} per GSQL hit |
| 10 | rag_citations | object[] | {doc, chunk_id, score} |
| 11 | actions_taken | object[] | {action, target, status, policy_ref} |
| 12 | policy_decisions | object[] | {action, decision, rule} per attempted action |
| 13 | amounts | object | {total, max, currency} |
| 14 | timeline | object[] | {dt, event} ordered |
| 15 | explanation | str | human-readable rationale |
| 16 | recommended_next_steps | str[] | follow-ups |

Runner MUST validate all 16 fields (Reviewer S5.8.1 / tests/test_runner.py).

## 5. Benchmark: 20 cases (5 patterns × 4)

| Pattern | Cases | Mix |
|---------|-------|-----|
| A. card-not-present ring | 01–04 | 2 strong fraud (velocity + shared card/email), 1 borderline, 1 negative control (family shared card, legit) |
| B. account takeover | 05–08 | 2 strong (new device + addr/email change + amount spike), 1 borderline (travel), 1 negative (phone upgrade) |
| C. money-mule fan-out | 09–12 | 2 strong (1→N rapid/round-amount dispersal), 1 borderline (payroll), 1 negative (marketplace payouts) |
| D. device-spoofing cluster | 13–16 | 2 strong (many cards/one DeviceInfo, emulator reuse), 1 borderline (kiosk), 1 negative (corporate NAT) |
| E. synthetic identity | 17–20 | 2 strong (thin file + velocity, mismatched id_ signals), 1 borderline (new immigrant), 1 negative (student first card) |

Each pattern: ≥1 case exercising each of the 6 GSQL queries; labels cover fraud/legit/escalate.

## 6. Mapping: dataset entity → TigerGraph vertex/edge

| Dataset entity | Vertex | Key attribute |
|----------------|--------|---------------|
| Transaction row | TRANSACTION | TransactionID, amt, dt, ProductCD, isFraud |
| card1 (+card4/6) | CARD | card1 |
| P/R_emaildomain | EMAIL | domain + role flag |
| DeviceInfo/Type | DEVICE | DeviceInfo |
| addr1/addr2 | ADDRESS | code |
| identity row | IDENTITY | TransactionID (+id_01–38) |
| ProductCD/merchant | MERCHANT | ProductCD |

| Edge | From → To | Meaning |
|------|-----------|---------|
| MADE_WITH | TRANSACTION → CARD | payment instrument |
| USED_EMAIL | TRANSACTION → EMAIL | purchaser/recipient email |
| USED_DEVICE | TRANSACTION → DEVICE | device used |
| SHIPPED_TO / BILLED_TO | TRANSACTION → ADDRESS | geo linkage |
| HAS_IDENTITY | TRANSACTION → IDENTITY | identity profile |
| SOLD_BY | TRANSACTION → MERCHANT | product/merchant |
| SAME_CARD / SAME_DEVICE / SAME_EMAIL (derived) | TRANSACTION ↔ TRANSACTION | ring/cluster hops for queries |

6 GSQL queries: (1) card-ring expansion, (2) device-cluster expansion, (3) mule fan-out,
(4) takeover anomaly (addr/device/email change + velocity), (5) synthetic-identity signals,
(6) evidence-subgraph export (bounded k-hop around case entities).

## 7. Open questions / ambiguities

1. Real `data/HHGOA_IEEE/` may appear later — runner/client must tolerate row-count/schema drift
   (nullable columns already assumed). If real data arrives, re-run ingest + benchmark.
2. Output 16-field schema is a **Planner assumption from the Commander spec text**; if the grader
   expects different field names, `runner.py` should keep a single `OUTPUT_SCHEMA` constant so rename is 1-file.
3. TigerGraph Savanna credentials unknown → `client.py` MUST run fully offline via mock fallback;
   `.env.example` documents expected vars.
4. LLM for agent unspecified → prompts must be model-agnostic; `settings.yaml` holds model name;
   no API key required for mock/benchmark path.
5. Only V1–V20 populated in stub — document clearly so nobody claims full IEEE-CIS fidelity.

## 8. Milestone dependency map

M1 (scaffold+data) → M2 (TG schema/queries/client) → M3 (MCP tools depend T2.2; ingest/retriever
parallel with M2) → M4 (agent core; needs tools+retriever+policy) → M5 (runner+cases+UI) → M6
(docs+tests+full verify). Max-parallel groups noted per task in `.opencode/todo.md`.
Total: **72 leaf subtasks** (M1:16, M2:5, M3:5, M4:11, M5:25, M6:10).
