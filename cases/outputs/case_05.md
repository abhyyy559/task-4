# case_05 — FRAUD

- pattern: account_takeover
- risk_score: 100.0 (confidence 0.95)
- transactions_reviewed: [1013, 1017, 1018, 1021]
- evidence_ids: ['1013', '1017', '1018', '1021', '1014', '1015', '1016', '1019', '1020', '1022', '1023', '1024', 'CARD:522222', 'DEVICE:attacker-fresh-01', 'DEVICE:victim-iphone-01', 'EMAIL:brand.new@fresh.cc', 'EMAIL:victim.a@post.com', 'TXN:1013', 'TXN:1014', 'TXN:1015']

## Graph findings
- q_card_ring: 12 txns share card 522222 in window (nodes=12)
- q_takeover_anomaly: takeover scan over 12 txns: device_change=True (nodes=12)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=56 (nodes=12)
- q_mule_fanout: hub card 522222 fans out to 2 recipients (nodes=14)
- q_device_cluster: 1 cards via device attacker-fresh-01 (nodes=9)
- q_device_cluster: 1 cards via device victim-iphone-01 (nodes=5)
- q_evidence_subgraph: 17 nodes within 2 hops of 4 txns (nodes=17)

## RAG citations
- patterns.md#account_takeover-c0 (score=0.6784)
- patterns.md#money_mule_fanout-c0 (score=0.4218)
- patterns.md#account_takeover-c1 (score=0.3989)

## Actions taken
- freeze_card -> 522222 [ok] via freeze-fraud-confident
- block_device -> attacker-fresh-01 [ok] via block-device-pattern
- flag_email -> victim.a@post.com [ok] via flag-email-fraud
- escalate_case -> case_05 [ok] via escalate-nonlegit
- notify_user -> victim.a@post.com [ok] via notify-always

## Explanation
Case case_05 (account_takeover): verdict=fraud with confidence 0.95 and risk score 100.0 over 4 transactions. Key signals: device_change, thin_file, amount_spike, new_device_age, geo_distance. Pattern knowledge: account_takeover-c0, money_mule_fanout-c0, account_takeover-c1. Evidence: 1013, 1017, 1018, 1021, 1014, 1015, 1016, 1019.

## Recommended next steps
- confirm card freeze with cardholder
- analyst review of evidence_ids
- consider SAR filing / collect chargeback evidence pack
