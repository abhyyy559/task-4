# case_03 — ESCALATE

- pattern: None
- risk_score: 66.0 (confidence 0.664)
- transactions_reviewed: [1009, 1010]
- evidence_ids: ['1009', '1010', '1001', '1002', '1003', '1004', '1005', '1006', '1007', '1008', '1011', '1012', 'CARD:411111', 'DEVICE:ring-dev-0', 'DEVICE:ring-dev-2', 'EMAIL:drop09@ringmail.cc', 'EMAIL:ring.buyer@ringmail.cc', 'TXN:1001', 'TXN:1002', 'TXN:1003']

## Graph findings
- q_card_ring: 12 txns share card 411111 in window (nodes=12)
- q_takeover_anomaly: takeover scan over 12 txns: device_change=True (nodes=12)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=72 (nodes=12)
- q_mule_fanout: hub card 411111 fans out to 5 recipients (nodes=17)
- q_device_cluster: 1 cards via device ring-dev-0 (nodes=5)
- q_device_cluster: 1 cards via device ring-dev-2 (nodes=5)
- q_evidence_subgraph: 17 nodes within 2 hops of 2 txns (nodes=17)

## RAG citations
- patterns.md#card_not_present_ring-c0 (score=0.5276)
- patterns.md#card_not_present_ring-c1 (score=0.4114)
- patterns.md#account_takeover-c0 (score=0.3896)

## Actions taken
- escalate_case -> case_03 [ok] via escalate-nonlegit
- notify_user -> ring.buyer@ringmail.cc [ok] via notify-always

## Explanation
Case case_03 (card_not_present_ring): verdict=escalate with confidence 0.664 and risk score 66.0 over 2 transactions. Key signals: device_change, new_device_age. Pattern knowledge: card_not_present_ring-c0, card_not_present_ring-c1, account_takeover-c0. Evidence: 1009, 1010, 1001, 1002, 1003, 1004, 1005, 1006.

## Recommended next steps
- manual review of evidence_ids
- request step-up authentication from cardholder
- re-run after 24h of additional transactions
