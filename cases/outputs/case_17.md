# case_17 — FRAUD

- pattern: synthetic_identity
- risk_score: 100.0 (confidence 0.95)
- transactions_reviewed: [1049, 1050, 1051]
- evidence_ids: ['1049', '1050', '1051', 'EMAIL:synth00@freshmail.net', 'EMAIL:synth01@freshmail.net', 'EMAIL:synth02@freshmail.net', '1053', '1057', 'CARD:855500', 'CARD:855501', 'CARD:855502', '1054', '1058', 'CARD:855503', '1055', '1059', 'DEVICE:low-end-0', 'DEVICE:low-end-1', 'DEVICE:low-end-2', 'TXN:1049']

## Graph findings
- q_card_ring: 3 txns share card 855500 in window (nodes=3)
- q_takeover_anomaly: takeover scan over 3 txns: device_change=True (nodes=3)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=27 (nodes=3)
- q_mule_fanout: hub card 855500 fans out to 3 recipients (nodes=6)
- q_device_cluster: 3 cards via device low-end-0 (nodes=6)
- q_device_cluster: 3 cards via device low-end-1 (nodes=6)
- q_device_cluster: 3 cards via device low-end-2 (nodes=6)
- q_evidence_subgraph: 16 nodes within 2 hops of 3 txns (nodes=16)

## RAG citations
- patterns.md#synthetic_identity-c0 (score=0.6499)
- patterns.md#synthetic_identity-c1 (score=0.4235)
- patterns.md#device_spoofing_cluster-c1 (score=0.3343)

## Actions taken
- freeze_card -> 855500 [ok] via freeze-fraud-confident
- block_device -> low-end-0 [blocked:escalate] via block-device-review
- flag_email -> synth00@freshmail.net [ok] via flag-email-fraud
- escalate_case -> case_17 [ok] via escalate-nonlegit
- notify_user -> synth00@freshmail.net [ok] via notify-always

## Explanation
Case case_17 (synthetic_identity): verdict=fraud with confidence 0.95 and risk score 100.0 over 3 transactions. Key signals: rapid_velocity_1h, device_change, thin_file, amount_spike. Pattern knowledge: synthetic_identity-c0, synthetic_identity-c1, device_spoofing_cluster-c1. Evidence: 1049, 1050, 1051, EMAIL:synth00@freshmail.net, EMAIL:synth01@freshmail.net, EMAIL:synth02@freshmail.net, 1053, 1057.

## Recommended next steps
- confirm card freeze with cardholder
- analyst review of evidence_ids
- consider SAR filing / collect chargeback evidence pack
