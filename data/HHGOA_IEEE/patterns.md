# Fraud patterns (GraphRAG corpus seed)

> Official pattern definitions from the HHGOA_IEEE dataset README
> ("The five known fraud patterns"), transcribed 2026-09-21. These are the
> patterns the bank's analysts recognize; they are not the only patterns in
> the data. `undocumented` covers confirmed abuse matching none of the five;
> `none` marks cleared alerts.

## PATTERN card_testing

- **Name:** card_testing
- **Description:** A stolen card number is checked before use: three or more
  tiny online authorizations, often under $5, then a larger purchase.
  Confirmed by the sequence itself. Policy R5.
- **Graph signals:** CARD node with >=3 small-amount online TRANSACTION nodes
  inside a 1-hour window, followed by a larger purchase within 24h.
- **Column signals:** TransactionAmt < 5 for the probe authorizations;
  ProductCD != W (online); a later TransactionAmt an order of magnitude larger.
- **Policy:** R5 — three or more small online authorizations within an hour
  plus a larger purchase: DECLINE_TRANSACTION and STEP_UP_AUTH; if a purchase
  over $100 already cleared, BLOCK_CARD.

## PATTERN card_not_present_fraud

- **Name:** card_not_present_fraud
- **Description:** The card number is used online without the card. Amounts
  and products that don't fit the cardholder's history, often in a burst of
  two to four within 48 hours. On its own, one unusual online purchase is
  ambiguous: verify. Policy R1 to R4.
- **Graph signals:** burst of 2-4 online TRANSACTION nodes in 48h on one CARD,
  amounts above the card's history envelope.
- **Column signals:** ProductCD != W; TransactionAmt inconsistent with the
  card's 60-day median/max; new P_emaildomain vs history.
- **Policy:** R1 (verify before blocking on a weak signal), R2/R3/R4
  (customer response handling).

## PATTERN card_not_present_new_device

- **Name:** card_not_present_new_device
- **Description:** Same as card-not-present fraud, with the identity record
  marking the device as New for this account, sometimes behind a proxy.
  Stronger than pattern 2, still not proof: people buy new phones.
- **Graph signals:** online burst as above, plus the TRANSACTION's
  FROM_DEVICE edge leads to a DeviceProfile never seen for the card.
- **Column signals:** id_15 = New for the flagged transaction while earlier
  transactions show Found or another device; id_23 proxy flags
  (transparent/anonymous/hidden); new DeviceInfo.
- **Policy:** R1-R4; the new-device signal strengthens suspicion but a
  single signal still means verify first.

## PATTERN out_of_region_use

- **Name:** out_of_region_use
- **Description:** Card-present purchases in a billing region the cardholder
  has no history in, while their normal activity continues at home. Several
  days of purchases in one new region is a trip, not a clone. Policy R2, R3.
- **Graph signals:** in-person TRANSACTION nodes BILLED_IN a BillingRegion
  with no prior edge from the CARD, while HOME-region transactions continue
  in the same week.
- **Column signals:** ProductCD = W (in person); addr1 unseen in 90 days of
  history; addr2 = 87 continuing on other transactions.
- **Policy:** R2 (customer denies -> BLOCK_CARD + CREATE_CASE), R3
  (customer confirms -> CLOSE_NO_FRAUD).

## PATTERN account_takeover

- **Name:** account_takeover
- **Description:** Mixed-channel activity inconsistent with the cardholder,
  often with device and match-flag anomalies, pointing to stolen credentials
  rather than a stolen number.
- **Graph signals:** CARD with both in-person and online TRANSACTION nodes
  in 48h; a new FROM_DEVICE edge; prior device profile abandoned.
- **Column signals:** channel mix; DeviceInfo/OS/browser change; M1-M9
  match flags flipping vs the card's mode; id_34 match-status anomalies.
- **Policy:** R2/R3/R4 by customer response; R10 guards BLOCK_ALL_CARDS.

## PATTERN undocumented

- **Name:** undocumented
- **Description:** Analysts confirmed fraud but could not match it to a
  known pattern. Noticing activity that fits none of the five, describing
  it in your own words, and recommending a defensible action is scored.
- **Graph signals:** coordinated or repeated abuse across customers via
  shared device profiles, region clusters, or recipient emails.
- **Policy:** R9 — CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST; describe
  the pattern in your own words; do not force it into a known category.

## PATTERN none

- **Name:** none
- **Description:** Cleared alerts: the activity was legitimate. Half the
  cases are legitimate; an agent that blocks everything scores badly.
- **Policy:** R3 (customer confirms -> CLOSE_NO_FRAUD), R7 (disputed but
  legitimate recurring charge -> CREATE_CASE + VERIFY_WITH_CUSTOMER +
  WARN_CUSTOMER, do not block).
