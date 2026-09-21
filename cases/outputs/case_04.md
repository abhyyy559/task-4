# case_04 — LEGIT

- pattern: None
- risk_score: 0.0 (confidence 0.75)
- transactions_reviewed: [1061, 1062]
- evidence_ids: ['1061', '1062', 'EMAIL:family.doe@gmail.com', 'CARD:411112', 'DEVICE:family-iphone-01', 'TXN:1061', 'TXN:1062']

## Graph findings
- q_card_ring: 2 txns share card 411112 in window (nodes=2)
- q_takeover_anomaly: takeover scan over 2 txns: device_change=False (nodes=2)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=0 (nodes=2)
- q_mule_fanout: hub card 411112 fans out to 1 recipients (nodes=3)
- q_device_cluster: 1 cards via device family-iphone-01 (nodes=3)
- q_evidence_subgraph: 5 nodes within 2 hops of 2 txns (nodes=5)

## RAG citations
- patterns.md#card_not_present_ring-c0 (score=0.5276)
- patterns.md#card_not_present_ring-c1 (score=0.4114)
- patterns.md#account_takeover-c0 (score=0.3896)

## Actions taken

## Explanation
Case case_04 (card_not_present_ring): verdict=legit with confidence 0.75 and risk score 0.0 over 2 transactions. Key signals: thin_file. Pattern knowledge: card_not_present_ring-c0, card_not_present_ring-c1, account_takeover-c0. Evidence: 1061, 1062, EMAIL:family.doe@gmail.com, CARD:411112, DEVICE:family-iphone-01, TXN:1061, TXN:1062.

## Recommended next steps
- no action required
- continue monitoring baseline
