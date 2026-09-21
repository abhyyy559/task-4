# case_15 — ESCALATE

- pattern: None
- risk_score: 44.0 (confidence 0.576)
- transactions_reviewed: [1045, 1046]
- evidence_ids: ['1045', '1046', 'EMAIL:ghost08@tempmail.cc', 'EMAIL:ghost09@tempmail.cc', '1037', '1038', '1039', '1040', '1041', '1042', '1043', '1044', '1047', '1048', 'CARD:744408', 'CARD:744409', 'DEVICE:emu-spoof-X1', 'TXN:1037', 'TXN:1038', 'TXN:1039']

## Graph findings
- q_card_ring: 1 txns share card 744408 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=9 (nodes=1)
- q_mule_fanout: hub card 744408 fans out to 1 recipients (nodes=2)
- q_card_ring: 1 txns share card 744409 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=9 (nodes=1)
- q_mule_fanout: hub card 744409 fans out to 1 recipients (nodes=2)
- q_device_cluster: 12 cards via device emu-spoof-X1 (nodes=24)
- q_evidence_subgraph: 17 nodes within 2 hops of 2 txns (nodes=17)

## RAG citations
- patterns.md#device_spoofing_cluster-c0 (score=0.6126)
- patterns.md#account_takeover-c0 (score=0.4491)
- patterns.md#account_takeover-c1 (score=0.3851)

## Actions taken
- escalate_case -> case_15 [ok] via escalate-nonlegit
- notify_user -> ghost08@tempmail.cc [ok] via notify-always

## Explanation
Case case_15 (device_spoofing_cluster): verdict=escalate with confidence 0.576 and risk score 44.0 over 2 transactions. Key signals: device_change, new_device_age. Pattern knowledge: device_spoofing_cluster-c0, account_takeover-c0, account_takeover-c1. Evidence: 1045, 1046, EMAIL:ghost08@tempmail.cc, EMAIL:ghost09@tempmail.cc, 1037, 1038, 1039, 1040.

## Recommended next steps
- manual review of evidence_ids
- request step-up authentication from cardholder
- re-run after 24h of additional transactions
