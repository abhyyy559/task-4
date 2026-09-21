# case_08 — LEGIT

- pattern: None
- risk_score: 0.0 (confidence 0.75)
- transactions_reviewed: [1063]
- evidence_ids: ['1063', 'EMAIL:upgrade.d@gmail.com', 'CARD:522223', 'DEVICE:pixel-8-new', 'TXN:1063']

## Graph findings
- q_card_ring: 1 txns share card 522223 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=0 (nodes=1)
- q_mule_fanout: hub card 522223 fans out to 1 recipients (nodes=2)
- q_device_cluster: 1 cards via device pixel-8-new (nodes=2)
- q_evidence_subgraph: 4 nodes within 2 hops of 1 txns (nodes=4)

## RAG citations
- patterns.md#account_takeover-c0 (score=0.6784)
- patterns.md#money_mule_fanout-c0 (score=0.4218)
- patterns.md#account_takeover-c1 (score=0.3989)

## Actions taken

## Explanation
Case case_08 (account_takeover): verdict=legit with confidence 0.75 and risk score 0.0 over 1 transactions. Key signals: none strong. Pattern knowledge: account_takeover-c0, money_mule_fanout-c0, account_takeover-c1. Evidence: 1063, EMAIL:upgrade.d@gmail.com, CARD:522223, DEVICE:pixel-8-new, TXN:1063.

## Recommended next steps
- no action required
- continue monitoring baseline
