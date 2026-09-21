# case_13 — FRAUD

- pattern: device_spoofing_cluster
- risk_score: 100.0 (confidence 0.95)
- transactions_reviewed: [1037, 1038, 1039, 1040]
- evidence_ids: ['1037', '1038', '1039', '1040', 'EMAIL:ghost00@tempmail.cc', 'EMAIL:ghost01@tempmail.cc', 'EMAIL:ghost02@tempmail.cc', 'EMAIL:ghost03@tempmail.cc', '1041', '1042', '1043', '1044', '1045', '1046', '1047', '1048', 'CARD:744400', 'CARD:744401', 'CARD:744402', 'CARD:744403']

## Graph findings
- q_card_ring: 1 txns share card 744400 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=9 (nodes=1)
- q_mule_fanout: hub card 744400 fans out to 1 recipients (nodes=2)
- q_card_ring: 1 txns share card 744401 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=9 (nodes=1)
- q_mule_fanout: hub card 744401 fans out to 1 recipients (nodes=2)
- q_card_ring: 1 txns share card 744402 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=9 (nodes=1)
- q_mule_fanout: hub card 744402 fans out to 1 recipients (nodes=2)
- q_card_ring: 1 txns share card 744403 in window (nodes=1)
- q_takeover_anomaly: takeover scan over 1 txns: device_change=False (nodes=1)
- q_synthetic_identity: synthetic scan: thin_file=False, mismatch_flags=9 (nodes=1)
- q_mule_fanout: hub card 744403 fans out to 1 recipients (nodes=2)
- q_device_cluster: 12 cards via device emu-spoof-X1 (nodes=24)
- q_evidence_subgraph: 21 nodes within 2 hops of 4 txns (nodes=21)

## RAG citations
- patterns.md#device_spoofing_cluster-c0 (score=0.6126)
- patterns.md#account_takeover-c0 (score=0.4491)
- patterns.md#account_takeover-c1 (score=0.3851)

## Actions taken
- freeze_card -> 744400 [ok] via freeze-fraud-confident
- freeze_card -> 744401 [ok] via freeze-fraud-confident
- block_device -> emu-spoof-X1 [ok] via block-device-pattern
- flag_email -> ghost00@tempmail.cc [ok] via flag-email-fraud
- escalate_case -> case_13 [ok] via escalate-nonlegit
- notify_user -> ghost00@tempmail.cc [ok] via notify-always

## Explanation
Case case_13 (device_spoofing_cluster): verdict=fraud with confidence 0.95 and risk score 100.0 over 4 transactions. Key signals: rapid_velocity_1h, device_change, new_device_age. Pattern knowledge: device_spoofing_cluster-c0, account_takeover-c0, account_takeover-c1. Evidence: 1037, 1038, 1039, 1040, EMAIL:ghost00@tempmail.cc, EMAIL:ghost01@tempmail.cc, EMAIL:ghost02@tempmail.cc, EMAIL:ghost03@tempmail.cc.

## Recommended next steps
- confirm card freeze with cardholder
- analyst review of evidence_ids
- consider SAR filing / collect chargeback evidence pack
