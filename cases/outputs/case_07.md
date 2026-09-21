# case_07 — ESCALATE

- pattern: None
- risk_score: 38.0 (confidence 0.552)
- transactions_reviewed: [1015, 1016]
- evidence_ids: ['1015', '1016', '1013', '1014', '1017', '1018', '1019', '1020', '1021', '1022', '1023', '1024', 'CARD:522222', 'DEVICE:victim-iphone-01', 'EMAIL:victim.a@post.com', 'TXN:1013', 'TXN:1014', 'TXN:1015', 'TXN:1016', 'TXN:1017']

## Graph findings
- q_card_ring: 12 txns share card 522222 in window (nodes=12)
- q_takeover_anomaly: takeover scan over 12 txns: device_change=True (nodes=12)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=56 (nodes=12)
- q_mule_fanout: hub card 522222 fans out to 2 recipients (nodes=14)
- q_device_cluster: 1 cards via device victim-iphone-01 (nodes=5)
- q_evidence_subgraph: 15 nodes within 2 hops of 2 txns (nodes=15)

## RAG citations
- patterns.md#account_takeover-c0 (score=0.6784)
- patterns.md#money_mule_fanout-c0 (score=0.4218)
- patterns.md#account_takeover-c1 (score=0.3989)

## Actions taken
- escalate_case -> case_07 [ok] via escalate-nonlegit
- notify_user -> victim.a@post.com [ok] via notify-always

## Explanation
Case case_07 (account_takeover): verdict=escalate with confidence 0.552 and risk score 38.0 over 2 transactions. Key signals: thin_file. Pattern knowledge: account_takeover-c0, money_mule_fanout-c0, account_takeover-c1. Evidence: 1015, 1016, 1013, 1014, 1017, 1018, 1019, 1020.

## Recommended next steps
- manual review of evidence_ids
- request step-up authentication from cardholder
- re-run after 24h of additional transactions
