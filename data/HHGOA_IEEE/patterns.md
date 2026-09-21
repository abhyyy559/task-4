# Fraud patterns (GraphRAG corpus seed)

> Synthetic stub — each pattern below is hand-wired into `transactions.csv`
> (12 fraud rows per pattern, seed=42). Field names follow IEEE-CIS.

## PATTERN card_not_present_ring

- **Name:** card_not_present_ring
- **Description:** One stolen card (card1) or purchaser email reused across many
  rapid card-not-present transactions, often across merchants, to cash out before
  the card is blocked.
- **Graph signals:** CARD node with high out-degree to TRANSACTION nodes inside a
  1-hour window; shared P_emaildomain fan-in; `q_card_ring` expansion returns
  10+ transactions for one card.
- **Column signals:** TransactionDT span < 3600s for 10+ rows sharing card1;
  C1 (tx per card window) >= 8; V1 > 1.5; M1/M2 = F with M3 = T.
- **Severity:** high
- **Stub rows:** TransactionID 1001–1012 (card1 411111). Negative control: family
  shared card, low velocity, all M = T.

## PATTERN account_takeover

- **Name:** account_takeover
- **Description:** Legitimate account hijacked: a never-before-seen DeviceInfo
  appears for an established card, paired with address/email change and an
  amount spike as the attacker drains the account.
- **Graph signals:** CARD node gains a new USED_DEVICE edge; `q_takeover`
  shows device/email/address change plus velocity break for the card.
- **Column signals:** D1 near 0 (first event on new device); dist1/dist2 large
  (>= 100); addr2 != addr1; M1/M2 flip T -> F; TransactionAmt 10x baseline.
- **Severity:** critical
- **Stub rows:** TransactionID 1013–1024 (card1 522222; first 4 rows baseline,
  last 8 post-takeover). Negative control: phone upgrade, stable profile.

## PATTERN money_mule_fanout

- **Name:** money_mule_fanout
- **Description:** One hub card disperses funds to many recipient emails in rapid
  succession, often in identical round amounts — classic mule-network payout.
- **Graph signals:** 1-to-N CARD -> TRANSACTION -> EMAIL topology within minutes;
  `q_mule_fanout` returns 10+ distinct recipient emails for one hub card.
- **Column signals:** identical round TransactionAmt (900.00); C2 (recipients per
  hub) >= 9; distinct R_emaildomain per row; DT spacing ~5 minutes.
- **Severity:** high
- **Stub rows:** TransactionID 1025–1036 (hub card1 633333). Negative control:
  payroll — monthly cadence, stable employee recipients.

## PATTERN device_spoofing_cluster

- **Name:** device_spoofing_cluster
- **Description:** Many distinct cards funnelled through a single DeviceInfo
  fingerprint (emulator/spoofed device) running automated fraud at scale.
- **Graph signals:** DEVICE node with high in-degree from distinct CARD nodes;
  `q_device_cluster` returns 10+ cards for one DeviceInfo.
- **Column signals:** cards-per-device >= 10; all M1–M9 = F; identity fields
  missing/thin; V1 > 2.5; D1 near 0.
- **Severity:** critical
- **Stub rows:** TransactionID 1037–1048 (DeviceInfo emu-spoof-X1, 12 distinct
  cards). Negative control: corporate NAT, long histories, normal amounts.

## PATTERN synthetic_identity

- **Name:** synthetic_identity
- **Description:** Fabricated identity fragments stitched into a "thin file":
  brand-new accounts with no history, mismatched identity signals, and fast
  early velocity at high amounts.
- **Graph signals:** fresh CARD/IDENTITY nodes with shallow history;
  `q_synthetic` flags thin-file plus mismatch for the card.
- **Column signals:** C1 = 1 (thin file); D1 low (1–3 days); all M flags = F;
  id_ mismatch/empty in identity.csv; high TransactionAmt for account age.
- **Severity:** medium
- **Stub rows:** TransactionID 1049–1060 (4 cards x 3 txns). Negative control:
  student first card — thin file but small amounts, verified university email.
