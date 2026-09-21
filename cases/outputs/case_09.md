# case_09 — FRAUD

- pattern: money_mule_fanout
- risk_score: 100.0 (confidence 0.95)
- transactions_reviewed: [1025, 1026, 1027, 1028]
- evidence_ids: ['1025', '1026', '1027', '1028', '1029', '1030', '1031', '1032', '1033', '1034', '1035', '1036', 'CARD:633333', 'DEVICE:hub-moto-g', 'EMAIL:hub.mule@fast.cc', 'EMAIL:mule00@fast.cc', 'EMAIL:mule01@fast.cc', 'EMAIL:mule02@fast.cc', 'EMAIL:mule03@fast.cc', 'TXN:1025']

## Graph findings
- q_card_ring: 12 txns share card 633333 in window (nodes=12)
- q_takeover_anomaly: takeover scan over 12 txns: device_change=False (nodes=12)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=72 (nodes=12)
- q_mule_fanout: hub card 633333 fans out to 12 recipients (nodes=24)
- q_device_cluster: 1 cards via device hub-moto-g (nodes=13)
- q_evidence_subgraph: 19 nodes within 2 hops of 4 txns (nodes=19)

## RAG citations
- patterns.md#money_mule_fanout-c0 (score=0.5471)
- patterns.md#money_mule_fanout-c1 (score=0.4207)
- patterns.md#synthetic_identity-c1 (score=0.354)

## Actions taken
- freeze_card -> 633333 [ok] via freeze-fraud-confident
- block_device -> hub-moto-g [blocked:escalate] via block-device-review
- flag_email -> hub.mule@fast.cc [ok] via flag-email-fraud
- escalate_case -> case_09 [ok] via escalate-nonlegit
- notify_user -> hub.mule@fast.cc [ok] via notify-always

## Explanation
Case case_09 (money_mule_fanout): verdict=fraud with confidence 0.95 and risk score 100.0 over 4 transactions. Key signals: rapid_velocity_1h. Pattern knowledge: money_mule_fanout-c0, money_mule_fanout-c1, synthetic_identity-c1. Evidence: 1025, 1026, 1027, 1028, 1029, 1030, 1031, 1032.

## Recommended next steps
- confirm card freeze with cardholder
- analyst review of evidence_ids
- consider SAR filing / collect chargeback evidence pack
