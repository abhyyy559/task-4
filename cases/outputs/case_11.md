# case_11 — ESCALATE

- pattern: None
- risk_score: 35.0 (confidence 0.54)
- transactions_reviewed: [1064]
- evidence_ids: ['1064', 'EMAIL:emp.101@acmecorp.com', 'CARD:633334', 'DEVICE:acme-managed-01', 'EMAIL:payroll@acmecorp.com', 'TXN:1064']

## Graph findings
- q_card_ring: 1 txns share card 633334 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=0 (nodes=1)
- q_mule_fanout: hub card 633334 fans out to 1 recipients (nodes=2)
- q_device_cluster: 1 cards via device acme-managed-01 (nodes=2)
- q_evidence_subgraph: 5 nodes within 2 hops of 1 txns (nodes=5)

## RAG citations
- patterns.md#money_mule_fanout-c0 (score=0.5471)
- patterns.md#money_mule_fanout-c1 (score=0.4207)
- patterns.md#synthetic_identity-c1 (score=0.354)

## Actions taken
- escalate_case -> case_11 [ok] via escalate-nonlegit
- notify_user -> payroll@acmecorp.com [ok] via notify-always

## Explanation
Case case_11 (money_mule_fanout): verdict=escalate with confidence 0.54 and risk score 35.0 over 1 transactions. Key signals: amount_spike. Pattern knowledge: money_mule_fanout-c0, money_mule_fanout-c1, synthetic_identity-c1. Evidence: 1064, EMAIL:emp.101@acmecorp.com, CARD:633334, DEVICE:acme-managed-01, EMAIL:payroll@acmecorp.com, TXN:1064.

## Recommended next steps
- manual review of evidence_ids
- request step-up authentication from cardholder
- re-run after 24h of additional transactions
