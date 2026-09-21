# case_16 — LEGIT

- pattern: None
- risk_score: 0.0 (confidence 0.75)
- transactions_reviewed: [1065]
- evidence_ids: ['1065', 'EMAIL:employee@bigcorp.com', 'CARD:744444', 'DEVICE:corp-nat-7', 'TXN:1065']

## Graph findings
- q_card_ring: 1 txns share card 744444 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=0 (nodes=1)
- q_mule_fanout: hub card 744444 fans out to 1 recipients (nodes=2)
- q_device_cluster: 1 cards via device corp-nat-7 (nodes=2)
- q_evidence_subgraph: 4 nodes within 2 hops of 1 txns (nodes=4)

## RAG citations
- patterns.md#device_spoofing_cluster-c0 (score=0.6126)
- patterns.md#account_takeover-c0 (score=0.4491)
- patterns.md#account_takeover-c1 (score=0.3851)

## Actions taken

## Explanation
Case case_16 (device_spoofing_cluster): verdict=legit with confidence 0.75 and risk score 0.0 over 1 transactions. Key signals: none strong. Pattern knowledge: device_spoofing_cluster-c0, account_takeover-c0, account_takeover-c1. Evidence: 1065, EMAIL:employee@bigcorp.com, CARD:744444, DEVICE:corp-nat-7, TXN:1065.

## Recommended next steps
- no action required
- continue monitoring baseline
