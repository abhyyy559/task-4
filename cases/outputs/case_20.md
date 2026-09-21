# case_20 — LEGIT

- pattern: None
- risk_score: 4.0 (confidence 0.73)
- transactions_reviewed: [1066]
- evidence_ids: ['1066', 'EMAIL:student.e@univ.edu', 'CARD:855555', 'DEVICE:student-phone-d', 'TXN:1066']

## Graph findings
- q_card_ring: 1 txns share card 855555 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=2 (nodes=1)
- q_mule_fanout: hub card 855555 fans out to 1 recipients (nodes=2)
- q_device_cluster: 1 cards via device student-phone-d (nodes=2)
- q_evidence_subgraph: 4 nodes within 2 hops of 1 txns (nodes=4)

## RAG citations
- patterns.md#synthetic_identity-c0 (score=0.6499)
- patterns.md#synthetic_identity-c1 (score=0.4235)
- patterns.md#device_spoofing_cluster-c1 (score=0.3343)

## Actions taken

## Explanation
Case case_20 (synthetic_identity): verdict=legit with confidence 0.73 and risk score 4.0 over 1 transactions. Key signals: none strong. Pattern knowledge: synthetic_identity-c0, synthetic_identity-c1, device_spoofing_cluster-c1. Evidence: 1066, EMAIL:student.e@univ.edu, CARD:855555, DEVICE:student-phone-d, TXN:1066.

## Recommended next steps
- no action required
- continue monitoring baseline
