# Fraud Domain Cheatsheet — speak the language

## The 7 patterns (exact enum — use these words, no others)

| Pattern | What it looks like |
|---|---|
| `card_testing` | Many tiny rapid authorizations on a card — thief checking the card works before the big purchase |
| `card_not_present_fraud` | Online/phone fraud on a card the thief physically holds data for |
| `card_not_present_new_device` | Card-not-present **plus** a device profile never seen for this customer — takeover smell |
| `out_of_region_use` | Spend far from the customer's billing/home region with no travel signal |
| `account_takeover` | Behavior break: new device + new region + velocity change on an existing account |
| `undocumented` | Coordinated suspicious shape that matches **no** known pattern — describe it in your own words, escalate (R9) |
| `none` | Legitimate. Half the benchmark is this. Saying `none` confidently is a correct answer. |

## The 14 actions + 3 approval routes

| Action | Route | When |
|---|---|---|
| `ALLOW_TRANSACTION` | auto | Cleared legitimate |
| `DECLINE_TRANSACTION` | auto | Single bad transaction, weak-ish evidence |
| `MONITOR_CARD` | auto | Watch, don't touch yet |
| `MONITOR_CONNECTED_CARDS` | auto | Shared-origin cluster, not yet confirmed |
| `WARN_CUSTOMER` | L1 | Heads-up, needs human sign-off |
| `VERIFY_WITH_CUSTOMER` | L1 | "Was this you?" — the R1 workhorse |
| `STEP_UP_AUTH` | L1 | Force stronger authentication |
| `BLOCK_CARD` | L1 | Confirmed/strong fraud on this card |
| `BLOCK_ALL_CARDS` | L2 | Only with ≥2 confirmed fraud cards or confirmed credential compromise (R10) |
| `GENERATE_REPORT` | auto | Internal write-up |
| `CREATE_CASE` | auto | Fraud probability ≥ 0.30, or evidence requested, or customer disputes |
| `FILE_REPORT` | L2 | SAR filing — senior approval |
| `ESCALATE_TO_ANALYST` | auto | Uncertain, conflicting, or R9 undocumented |
| `CLOSE_NO_FRAUD` | auto | Legitimate — customer confirmed or evidence clears |

Memory hook: **auto = observe and record, L1 = touch the customer's card, L2 = nuke
or report to authorities.**

## The 10 policy rules (R1–R10), one line each

1. **R1** — One weak signal (< 0.70)? Verify with the customer before you block anything.
2. **R2** — Customer says "not mine" → block the card, open a case, think SAR.
3. **R3** — Customer says "that was me" → close it, no fraud, move on.
4. **R4** — Customer ghosts for 24h → monitor or decline; exposure > $500 → escalate.
5. **R5** — Card-testing shape gets its own escalation ladder.
6. **R6** — Fraud shares a device/region with other cards → widen the net to them.
7. **R7** — Disputed charge that recurs legitimately → don't punish the customer.
8. **R8** — Evidence conflicts or exposure is large → a human decides, not the agent.
9. **R9** — Coordinated but unrecognized → describe it yourself, escalate, never
   force-fit a known pattern.
10. **R10** — Never block every card on weak evidence. Ever.

## SAR (Suspicious Activity Report) — when we file

File when fraud is confirmed/strongly suspected **AND** at least one holds:
- exposure > **$1,000**, or
- shared device/region with another customer/card's fraud, or
- coordinated or undocumented pattern (R9).

The SAR object carries `narrative` (who/what/when/where/how), `subjects`,
`total_amount_usd`, `activity_dates`. Filing is an L2 action — recommended, never
self-executed.

## The answer file anatomy (`cases/HHG-XXX.json`)

- `case` — status (`open`/`closed_fraud`/`closed_legitimate`/`escalated`), verdict
  (`fraud`/`legitimate`/`uncertain`), `fraud_probability`, `pattern`,
  `affected_txn_ids`, `first_suspicious_txn_id`, `connected_card_ids`,
  `connected_device_profiles`, `exposure_usd`, `evidence[]` (each: claim, source,
  ref, entity_ids), `similar_prior_cases`, `summary`, `written_to_graph`
- `evidence_requests[]` — type, asked_after_step, **assumed_response**
- `next_best_actions` — `initial[]`, `final[]`, `what_changed`
- `sar` — file?, reason, narrative, subjects, amounts, dates
- `stop_reason`, `tool_calls`, `tokens`, `latency_s`

Legitimate verdict ⇒ empty affected transactions, zero exposure, no SAR.

## The 20 cases at a glance

| Case | Trigger | Signal | Card |
|---|---|---|---|
| HHG-001 | risk_score 0.61 | $77.07, in billing region | C12382-K1 |
| HHG-002 | risk_score 0.79 | $292.36, online | C11891-K1 |
| HHG-003 | customer_report | $49.00 "never made this" | C08623-K2 |
| HHG-004 | customer_report | $128.33 "never made this" | C08106-K1 |
| HHG-005 | risk_score 0.54 | $100.07, online | C02923-K1 |
| HHG-006 | customer_report | $482.12 "never made this" | C07297-K1 |
| HHG-007 | risk_score 0.87 | $111.92, billing region | C09933-K2 |
| HHG-008 | customer_report | $55.68 "never made this" | C13171-K2 |
| HHG-009 | customer_report | $30.02 "never made this" | C08299-K1 |
| HHG-010 | risk_score 0.90 | $1,000.03, online | C10434-K1 |
| HHG-011 | customer_report | $131.30 "never made this" | C11923-K2 |
| HHG-012 | risk_score 0.55 | $30.91, billing region | C05876-K2 |
| HHG-013 | risk_score 0.76 | $35.66, online | C07671-K2 |
| HHG-014 | analyst_request | several cards, same unusual device profile | C13487-K1 |
| HHG-015 | risk_score 0.77 | $599.94, online | C03042-K1 |
| HHG-016 | customer_report | $59.67 "never made this" | C09988-K1 |
| HHG-017 | risk_score 0.57 | $100.09, online | C04570-K1 |
| HHG-018 | customer_report | $39.08 "never made this" | C02354-K2 |
| HHG-019 | risk_score 0.90 | $99.92, online | C07987-K2 |
| HHG-020 | risk_score 0.52 | $125.08, online | C12265-K2 |

Note the traps an evaluator may probe: HHG-014 is the **analyst request** (device
cluster across cards — think R6/R9); HHG-010 pairs a 0.90 score with $1,000.03
(SAR threshold is $1,000 — do the math out loud); the 0.5x-score cases are where
`uncertain` + R1 verification earns its keep.

## Vocabulary upgrades (say this, not that)

- "risk score" → **trigger**, never verdict
- "the model says fraud" → **the evidence supports fraud probability X**
- "we blocked the card" → **we recommended BLOCK_CARD via L1; a human approves**
- "unknown fraud type" → **`undocumented` pattern, described and escalated per R9**
- "the customer didn't answer" → **no reply in 24h → R4: monitor/decline, escalate
  if exposure > $500**
- "false positive" → **cleared legitimate** (say `CLOSE_NO_FRAUD` and mean it)
