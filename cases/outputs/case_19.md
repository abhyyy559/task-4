# case_19 — ESCALATE

- pattern: None
- risk_score: 62.0 (confidence 0.648)
- transactions_reviewed: [1056, 1057]
- evidence_ids: ['1056', '1057', '1055', 'EMAIL:synth06@freshmail.net', 'EMAIL:synth07@freshmail.net', 'EMAIL:synth08@freshmail.net', '1049', '1053', 'CARD:855500', 'CARD:855501', 'CARD:855502', '1052', '1060', 'CARD:855503', 'DEVICE:low-end-0', 'DEVICE:low-end-3', 'TXN:1049', 'TXN:1052', 'TXN:1053', 'TXN:1055']

## Graph findings
- q_card_ring: 3 txns share card 855502 in window (nodes=3)
- q_takeover_anomaly: takeover scan over 3 txns: device_change=True (nodes=3)
- q_synthetic_identity: synthetic scan: thin_file=True, mismatch_flags=27 (nodes=3)
- q_mule_fanout: hub card 855502 fans out to 3 recipients (nodes=6)
- q_device_cluster: 3 cards via device low-end-0 (nodes=6)
- q_device_cluster: 3 cards via device low-end-3 (nodes=6)
- q_evidence_subgraph: 12 nodes within 2 hops of 2 txns (nodes=12)

## RAG citations
- patterns.md#synthetic_identity-c0 (score=0.6499)
- patterns.md#synthetic_identity-c1 (score=0.4235)
- patterns.md#device_spoofing_cluster-c1 (score=0.3343)

## Actions taken
- escalate_case -> case_19 [ok] via escalate-nonlegit
- notify_user -> synth07@freshmail.net [ok] via notify-always

## Explanation
Case case_19 (synthetic_identity): verdict=escalate with confidence 0.648 and risk score 62.0 over 2 transactions. Key signals: device_change, thin_file, amount_spike. Pattern knowledge: synthetic_identity-c0, synthetic_identity-c1, device_spoofing_cluster-c1. Evidence: 1056, 1057, 1055, EMAIL:synth06@freshmail.net, EMAIL:synth07@freshmail.net, EMAIL:synth08@freshmail.net, 1049, 1053.

## Recommended next steps
- manual review of evidence_ids
- request step-up authentication from cardholder
- re-run after 24h of additional transactions
