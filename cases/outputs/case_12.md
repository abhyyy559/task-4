# case_12 — LEGIT

- pattern: None
- risk_score: 26.0 (confidence 0.62)
- transactions_reviewed: [1067, 1068]
- evidence_ids: ['1067', '1068', 'EMAIL:user1067@example.com', 'EMAIL:user1068@example.com', '1086', '1105', '1106', '1122', '1132', '1137', '1164', 'CARD:900508', 'CARD:902143', 'CARD:903429', 'CARD:904225', '1126', 'CARD:904592', 'CARD:907245', 'DEVICE:office-pc-02', 'DEVICE:office-pc-07']

## Graph findings
- q_card_ring: 1 txns share card 904225 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=2 (nodes=1)
- q_mule_fanout: hub card 904225 fans out to 1 recipients (nodes=2)
- q_card_ring: 1 txns share card 904592 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=3 (nodes=1)
- q_mule_fanout: hub card 904592 fans out to 1 recipients (nodes=2)
- q_device_cluster: 8 cards via device office-pc-02 (nodes=16)
- q_device_cluster: 2 cards via device office-pc-07 (nodes=4)
- q_evidence_subgraph: 16 nodes within 2 hops of 2 txns (nodes=16)

## RAG citations
- patterns.md#money_mule_fanout-c0 (score=0.5471)
- patterns.md#money_mule_fanout-c1 (score=0.4207)
- patterns.md#synthetic_identity-c1 (score=0.354)

## Actions taken

## Explanation
Case case_12 (money_mule_fanout): verdict=legit with confidence 0.62 and risk score 26.0 over 2 transactions. Key signals: device_change, thin_file. Pattern knowledge: money_mule_fanout-c0, money_mule_fanout-c1, synthetic_identity-c1. Evidence: 1067, 1068, EMAIL:user1067@example.com, EMAIL:user1068@example.com, 1086, 1105, 1106, 1122.

## Recommended next steps
- no action required
- continue monitoring baseline
