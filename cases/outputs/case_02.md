# case_02 — FRAUD

- pattern: card_not_present_ring
- risk_score: 100.0 (confidence 0.95)
- transactions_reviewed: [1005, 1006, 1007, 1008]
- evidence_ids: ['1005', '1006', '1007', '1008', '1001', '1002', '1003', '1004', '1009', '1010', '1011', '1012', 'CARD:411111', 'DEVICE:ring-dev-0', 'DEVICE:ring-dev-1', 'DEVICE:ring-dev-2', 'EMAIL:drop06@ringmail.cc', 'EMAIL:ring.buyer@ringmail.cc', 'TXN:1001', 'TXN:1002']

## Graph findings
- q_card_ring: 12 txns share card 411111 in window (nodes=12)
- q_takeover_anomaly: takeover scan over 12 txns: device_change=True (nodes=12)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=72 (nodes=12)
- q_mule_fanout: hub card 411111 fans out to 5 recipients (nodes=17)
- q_device_cluster: 1 cards via device ring-dev-0 (nodes=5)
- q_device_cluster: 1 cards via device ring-dev-1 (nodes=5)
- q_device_cluster: 1 cards via device ring-dev-2 (nodes=5)
- q_evidence_subgraph: 18 nodes within 2 hops of 4 txns (nodes=18)

## RAG citations
- patterns.md#card_not_present_ring-c0 (score=0.5276)
- patterns.md#card_not_present_ring-c1 (score=0.4114)
- patterns.md#account_takeover-c0 (score=0.3896)

## Actions taken
- freeze_card -> 411111 [ok] via freeze-fraud-confident
- block_device -> ring-dev-0 [blocked:escalate] via block-device-review
- flag_email -> ring.buyer@ringmail.cc [ok] via flag-email-fraud
- escalate_case -> case_02 [ok] via escalate-nonlegit
- notify_user -> ring.buyer@ringmail.cc [ok] via notify-always

## Explanation
Case case_02 (card_not_present_ring): verdict=fraud with confidence 0.95 and risk score 100.0 over 4 transactions. Key signals: rapid_velocity_1h, device_change, new_device_age. Pattern knowledge: card_not_present_ring-c0, card_not_present_ring-c1, account_takeover-c0. Evidence: 1005, 1006, 1007, 1008, 1001, 1002, 1003, 1004.

## Recommended next steps
- confirm card freeze with cardholder
- analyst review of evidence_ids
- consider SAR filing / collect chargeback evidence pack
