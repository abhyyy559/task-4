"""Evidence-driven fraud investigation producing the official answer format.

Pipeline per case:
  1. load case input (case_pack row) and resolve card keys
  2. gather evidence from the graph store (flagged txn, card history, device,
     device sharing, region, closed cases, policy documents)
  3. detect fraud-pattern signatures from evidence (never from input labels)
  4. score fraud_probability from evidence-derived signals
  5. recommend initial next-best actions under Fraud Policy R1-R10
  6. request extra evidence where the policy calls for it (simulated replies,
     assumptions recorded in evidence_requests)
  7. recommend final actions, decide SAR, write the case to the graph

No ground-truth labels are read anywhere in this module: pattern and verdict
come only from transaction/device/region evidence. The bank's risk_score is
treated as one weak input signal, never a verdict.
"""
from __future__ import annotations

import time
from collections import Counter
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.agent import policy as policy_mod
from src.data.hhgoa import ClosedCase, HHGOAStore, Identity, Txn

# Pattern priority when several signatures fire (strongest documented first).
PATTERN_PRIORITY = [
    "card_testing",
    "account_takeover",
    "out_of_region_use",
    "card_not_present_new_device",
    "card_not_present_fraud",
    "undocumented",
    "none",
]

_EPS = 1e-9


# ---------------------------------------------------------------------------
# small statistics helpers
# ---------------------------------------------------------------------------
def _median(values: List[float]) -> float:
    vals = sorted(values)
    n = len(vals)
    if n == 0:
        return 0.0
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def _mode(values: List[str]) -> str:
    vals = [v for v in values if v]
    return Counter(vals).most_common(1)[0][0] if vals else ""


# ---------------------------------------------------------------------------
# pattern-signature detectors (evidence-derived)
# ---------------------------------------------------------------------------
def _detect_structuring(
    txns: List[Txn], ref: Txn
) -> Tuple[bool, List[Txn], str]:
    """>=3 online txns within 60 minutes with amounts just under a round
    authorization threshold ($100/$500/$1000), occurring within 72h before
    the flagged transaction: the classic structuring signature seen in the
    closed-case history. Stale windows from months ago are not evidence."""
    online = sorted(
        (t for t in txns if t.channel == "online"), key=lambda t: t.ts
    )
    lo = ref.ts - timedelta(hours=72)
    for threshold in (100.0, 500.0, 1000.0):
        for i, start in enumerate(online):
            if not (lo <= start.ts <= ref.ts):
                continue
            window = [
                t
                for t in online[i:]
                if timedelta(0) <= t.ts - start.ts <= timedelta(minutes=60)
            ]
            near = [
                t
                for t in window
                if 0.85 * threshold <= abs(t.amt) < threshold
            ]
            if len(near) >= 3:
                return True, near, (
                    f"{len(near)} online purchases within an hour, each just "
                    f"under ${threshold:,.0f} — structuring signature"
                )
    return False, [], ""


def _detect_card_testing(txns: List[Txn]) -> Tuple[bool, List[Txn]]:
    """>=3 tiny online authorizations (<$5) within an hour, then a larger purchase."""
    online = [t for t in txns if t.channel == "online"]
    for i, start in enumerate(online):
        window = [
            t
            for t in online[i:]
            if timedelta(0) <= t.ts - start.ts <= timedelta(hours=1)
        ]
        small = [t for t in window if abs(t.amt) < 5.0]
        if len(small) >= 3:
            after = [
                t
                for t in online
                if timedelta(0) < t.ts - small[-1].ts <= timedelta(hours=24)
                and abs(t.amt) >= 10.0
            ]
            if after:
                return True, small + after[:2]
    return False, []


def _burst_48h(txns: List[Txn], ref: Txn) -> List[Txn]:
    lo = ref.ts - timedelta(hours=48)
    return [t for t in txns if t.channel == "online" and lo <= t.ts <= ref.ts]


def _card_baseline(
    store: "HHGOAStore", cust: str, c1: str, ref: Txn
) -> Tuple[float, float]:
    """Median and max amount of a card's own 60-day history before ref."""
    amts = [
        abs(t.amt)
        for t in store.card_txns(cust, c1)
        if t.ts < ref.ts and t.ts >= ref.ts - timedelta(days=60)
    ]
    return (_median(amts), max(amts) if amts else 0.0)


def _detect_cnp_burst(
    txns: List[Txn], ref: Txn, prior_median: float, prior_max: float
) -> Tuple[bool, List[Txn]]:
    """2-4 online txns within 48h with amounts not fitting card history."""
    burst = _burst_48h(txns, ref)
    if not 2 <= len(burst) <= 4:
        return False, []
    inconsistent = [
        t
        for t in burst
        if abs(t.amt) > 3 * max(prior_median, _EPS) or abs(t.amt) > prior_max
    ]
    if inconsistent:
        return True, burst
    return False, []


def _detect_new_device(
    store: HHGOAStore, txns: List[Txn], ref: Txn
) -> Tuple[bool, str]:
    """Flagged txn's device marked New while the card's history shows another device."""
    ident = store.identity_for(ref.txn_id)
    if ident is None or ident.id_15.lower() != "new":
        return False, ""
    cutoff = ref.ts - timedelta(days=60)
    older_profiles = [
        store.device_profile_for(t.txn_id)
        for t in txns
        if t.ts < ref.ts - timedelta(hours=1) and t.ts >= cutoff
    ]
    modal = _mode(older_profiles)
    current = ident.profile()
    if modal and current and current != modal:
        return True, current
    # New device with no usable history is still a weak new-device signal.
    return True, current


def _detect_out_of_region(
    txns: List[Txn], ref: Txn
) -> Tuple[bool, List[Txn], str]:
    """Card-present txns in a billing region with no card history, while home
    activity continues. Several days of new-region purchases = trip, not clone."""
    if ref.channel != "in_person":
        return False, [], ""
    cutoff = ref.ts - timedelta(days=90)
    prior_regions = {t.addr1 for t in txns if t.ts < ref.ts and t.ts >= cutoff}
    if not ref.addr1 or ref.addr1 in prior_regions:
        return False, [], ""
    home = _mode([t.addr1 for t in txns if t.ts < ref.ts])
    week = [t for t in txns if abs((t.ts - ref.ts).days) <= 7]
    home_continues = any(t.addr1 == home and t.addr1 for t in week)
    new_region_txns = [
        t
        for t in txns
        if t.channel == "in_person"
        and t.addr1 == ref.addr1
        and abs((t.ts - ref.ts).days) <= 7
    ]
    distinct_days = {t.ts.date() for t in new_region_txns}
    if len(distinct_days) >= 3:
        return False, [], ""  # trip, not a clone
    if home_continues and new_region_txns:
        return True, new_region_txns, ref.addr1
    return False, [], ""


def _detect_takeover(
    store: HHGOAStore, txns: List[Txn], ref: Txn
) -> Tuple[bool, List[Txn], str]:
    """Mixed-channel activity inconsistent with the cardholder: channel mix in
    48h plus a device change and match-flag anomalies vs the card's mode."""
    lo = ref.ts - timedelta(hours=48)
    window = [t for t in txns if lo <= t.ts <= ref.ts]
    channels = {t.channel for t in window}
    if len(channels) < 2:
        return False, [], ""
    cutoff = ref.ts - timedelta(days=60)
    prior = [t for t in txns if t.ts < lo and t.ts >= cutoff]
    modal_profile = _mode([store.device_profile_for(t.txn_id) for t in prior])
    current_profile = store.device_profile_for(ref.txn_id)
    device_changed = bool(modal_profile and current_profile and modal_profile != current_profile)
    # match-flag anomalies: M1..M9 differing from the card's modal flags
    modal_flags = [
        _mode([t.m_flags[i] for t in prior if len(t.m_flags) > i]) for i in range(9)
    ]
    anomalies = sum(
        1
        for i in range(9)
        if len(ref.m_flags) > i and ref.m_flags[i] and modal_flags[i]
        and ref.m_flags[i] != modal_flags[i]
    )
    if device_changed and anomalies >= 2:
        detail = (
            f"channel mix {sorted(channels)} in 48h; device changed "
            f"({modal_profile[:40]} -> {current_profile[:40]}); "
            f"{anomalies} match-flag anomalies"
        )
        return True, window, detail
    if device_changed or anomalies >= 3:
        detail = (
            f"channel mix {sorted(channels)} in 48h"
            + ("; device changed" if device_changed else "")
            + (f"; {anomalies} match-flag anomalies" if anomalies else "")
        )
        return True, window, detail
    return False, [], ""


def _detect_recurring(txns: List[Txn], ref: Txn) -> Tuple[bool, str]:
    """R7: disputed charge matching the card's own recurring pattern
    (same amount within 3%, ~monthly cadence, >=2 prior occurrences)."""
    if abs(ref.amt) < _EPS:
        return False, ""
    matches = [
        t
        for t in txns
        if t.ts < ref.ts
        and abs(abs(t.amt) - abs(ref.amt)) / abs(ref.amt) <= 0.03
    ]
    if len(matches) < 2:
        return False, ""
    gaps = sorted(
        (matches[i + 1].ts - matches[i].ts).days for i in range(len(matches) - 1)
    )
    monthly = [g for g in gaps if 25 <= g <= 35]
    if monthly:
        return True, (
            f"{len(matches)} prior charges within 3% of ${abs(ref.amt):.2f}, "
            f"~monthly cadence"
        )
    return False, ""


# ---------------------------------------------------------------------------
# investigation
# ---------------------------------------------------------------------------
class Investigation:
    def __init__(
        self, case_input: Dict[str, Any], store: HHGOAStore, client: Any = None
    ):
        self.case_input = case_input
        self.store = store
        self.client = client
        self.case_id = str(case_input.get("case_id", ""))
        self.tool_calls = 0
        self.evidence: List[Dict[str, Any]] = []
        self._steps = 0

    # -- evidence helpers -------------------------------------------------
    def _step(self) -> int:
        self._steps += 1
        return self._steps

    def _call(self, ref: str) -> None:
        self.tool_calls += 1

    def _add(
        self, claim: str, source: str, ref: str, entity_ids: List[str]
    ) -> None:
        self.evidence.append(
            {
                "claim": claim,
                "source": source,
                "ref": ref,
                "entity_ids": [str(e) for e in entity_ids],
            }
        )

    # -- main -------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        started = time.time()
        store = self.store
        ci = self.case_input

        self._step()  # 1: load case input
        flagged_txn_id = str(ci.get("flagged_txn_id", ""))
        card_id = str(ci.get("card_id", ""))
        customer_id = str(ci.get("customer_id", ""))
        trigger_type = str(ci.get("trigger_type", ""))
        trigger_text = str(ci.get("trigger_text", ""))
        risk_score = ci.get("risk_score")

        flagged = store.get_txn(flagged_txn_id)
        self._call("q_flagged_transaction")
        if flagged is None:
            return self._fallback_answer(
                flagged_txn_id, card_id, customer_id, trigger_text, started
            )

        keys = store.card1s_for_card_id(card_id)
        if not keys:
            # fall back to the flagged txn's own card key
            keys = [(flagged.customer_id, flagged.card1)]
        self._step()  # 2: resolve card
        card_txns: List[Txn] = []
        for cust, c1 in keys:
            card_txns.extend(store.card_txns(cust, c1))
        card_txns.sort(key=lambda t: t.ts)
        self._call("q_card_history")

        before = [t for t in card_txns if t.ts < flagged.ts]
        prior60 = [t for t in before if t.ts >= flagged.ts - timedelta(days=60)]
        prior_amts = [abs(t.amt) for t in prior60]
        prior_median = _median(prior_amts)
        prior_max = max(prior_amts) if prior_amts else 0.0
        self._step()  # 3: baseline

        ident = store.identity_for(flagged_txn_id)
        profile = ident.profile() if ident else ""
        self._call("q_device_profile")
        if ident:
            self._add(
                f"Flagged transaction {flagged_txn_id}: channel={flagged.channel}, "
                f"amount=${flagged.amt:.2f}, billing region {flagged.addr1 or 'n/a'}, "
                f"device marked '{ident.id_15 or 'unknown'}'"
                + (f", proxy={ident.id_23}" if ident.id_23 else ""),
                "graph",
                "q_device_profile",
                [flagged_txn_id, card_id],
            )
        else:
            self._add(
                f"Flagged transaction {flagged_txn_id}: channel={flagged.channel}, "
                f"amount=${flagged.amt:.2f}, billing region {flagged.addr1 or 'n/a'}; "
                "no identity record (in-person style transaction)",
                "graph",
                "q_flagged_transaction",
                [flagged_txn_id, card_id],
            )
        self._add(
            f"Card {card_id} baseline (60d before flag): {len(prior60)} transactions, "
            f"median amount ${prior_median:.2f}, max ${prior_max:.2f}, "
            f"usual channels {dict(Counter(t.channel for t in prior60).most_common(3)) or 'none'}",
            "graph",
            "q_card_history",
            [card_id],
        )
        if risk_score is not None:
            self._add(
                f"Bank model scored transaction {flagged_txn_id} at {risk_score}: "
                "an input signal, not a verdict (the model is often wrong in "
                "both directions)",
                "external",
                "model:risk_score",
                [flagged_txn_id],
            )
        if trigger_type == "customer_report":
            self._add(
                f"Customer {customer_id} denies transaction {flagged_txn_id}: "
                f"{trigger_text[:160]}",
                "customer",
                f"customer:trigger:{self.case_id}",
                [flagged_txn_id, card_id, customer_id],
            )
        elif trigger_type == "analyst_request":
            self._add(
                f"Analyst request on transaction {flagged_txn_id}: {trigger_text[:160]}",
                "external",
                f"analyst:trigger:{self.case_id}",
                [flagged_txn_id, card_id],
            )
        self._step()  # 4: device evidence

        # device sharing / shared origin
        self._step()  # 5
        self._call("q_device_sharing")
        shared_cards = (
            [c for c in store.cards_sharing_device(profile) if c != card_id]
            if profile
            else []
        )
        shared_origin = False
        coordinated_cards: List[str] = []
        if profile and shared_cards:
            self._add(
                f"Device profile '{profile[:80]}' is shared by {len(shared_cards)+1} "
                f"cards: {card_id} plus {', '.join(shared_cards[:5])}"
                f"{'...' if len(shared_cards) > 5 else ''}",
                "graph",
                "q_device_sharing",
                [card_id] + shared_cards[:5],
            )
            # check coordinated burst activity on the other cards, judged
            # against each card's own baseline (not the flagged card's)
            for other in shared_cards[:10]:
                okeys = store.card1s_for_card_id(other)
                for ocust, oc1 in okeys:
                    otxns = [
                        t
                        for t in store.card_txns(ocust, oc1)
                        if abs((t.ts - flagged.ts).days) <= 30
                    ]
                    o_med, o_max = _card_baseline(store, ocust, oc1, flagged)
                    burst, _ = _detect_cnp_burst(otxns, flagged, o_med, o_max)
                    if burst:
                        coordinated_cards.append(other)
                        break
            if coordinated_cards:
                shared_origin = True
                self._add(
                    f"Coordinated activity: {len(coordinated_cards)} other card(s) "
                    f"on the same device profile show burst activity within 30 days "
                    f"of the flag ({', '.join(coordinated_cards[:5])})",
                    "graph",
                    "q_device_sharing",
                    coordinated_cards[:5],
                )
        # region cluster: OTHER cards whose usual billing region is DIFFERENT
        # from the flagged region, making card-present purchases there within
        # a week of the flag AND showing burst activity near the flag (same
        # bar as the device path). Same-region cards shopping locally is noise
        # (a populous region has thousands of cards); foreign-card convergence
        # with bursts is the genuine shared-origin signal (R6).
        self._call("q_region_cluster")
        region_cards: List[str] = []
        if flagged.addr1:
            for (cust, c1), tids in store.txns_by_card.items():
                if (cust, c1) in keys:
                    continue
                if store.card_home_region.get((cust, c1), "") == flagged.addr1:
                    continue  # local card: not a convergence signal
                otxns = [store.txn_by_id.get(tid) for tid in tids]
                otxns = [t for t in otxns if t]
                if not any(
                    t.addr1 == flagged.addr1
                    and t.channel == "in_person"
                    and abs((t.ts - flagged.ts).days) <= 7
                    for t in otxns
                ):
                    continue
                burst, _ = _detect_cnp_burst(
                    otxns, flagged, *_card_baseline(store, cust, c1, flagged)
                )
                if burst:
                    region_cards.append(store.card_id_for(cust, c1))
        if region_cards:
            shared_origin = True
            self._add(
                "Region cluster: "
                f"{len(region_cards)} foreign card(s) made card-present purchases "
                f"in billing region {flagged.addr1} within a week of the flag "
                "with burst activity near the flag",
                "graph",
                "q_region_cluster",
                region_cards[:5],
            )

        # pattern-signature detection (evidence-derived)
        self._step()  # 6
        candidates: List[Tuple[str, float, List[Txn], str]] = []
        testing, testing_txns = _detect_card_testing(card_txns)
        if testing:
            candidates.append(
                ("card_testing", 0.42, testing_txns, "card-testing sequence detected")
            )
            self._add(
                f"Card-testing signature: {len([t for t in testing_txns if abs(t.amt) < 5])} "
                f"tiny online authorizations (<$5) within an hour followed by a larger "
                f"purchase on card {card_id}",
                "graph",
                "q_card_history",
                [t.txn_id for t in testing_txns],
            )
        structuring, struct_txns, struct_detail = _detect_structuring(
            card_txns, flagged
        )
        if structuring:
            candidates.append(
                ("undocumented", 0.40, struct_txns, struct_detail)
            )
            self._add(
                f"Structuring signature: {struct_detail}",
                "graph",
                "q_card_history",
                [t.txn_id for t in struct_txns],
            )
        takeover, takeover_txns, takeover_detail = _detect_takeover(
            store, card_txns, flagged
        )
        if takeover:
            candidates.append(
                ("account_takeover", 0.34, takeover_txns, takeover_detail)
            )
            self._add(
                f"Account-takeover signature on card {card_id}: {takeover_detail}",
                "graph",
                "q_card_history",
                [t.txn_id for t in takeover_txns[:8]],
            )
        oor, oor_txns, oor_region = _detect_out_of_region(card_txns, flagged)
        if oor:
            candidates.append(
                (
                    "out_of_region_use",
                    0.32,
                    oor_txns,
                    f"card-present use in region {oor_region}",
                )
            )
            self._add(
                f"Out-of-region signature: card-present purchases in billing region "
                f"{oor_region} (no 90-day history) while home-region activity continues",
                "graph",
                "q_region_cluster",
                [t.txn_id for t in oor_txns],
            )
        newdev, newdev_profile = _detect_new_device(store, card_txns, flagged)
        burst, burst_txns = _detect_cnp_burst(
            card_txns, flagged, prior_median, prior_max
        )
        if newdev and burst:
            candidates.append(
                (
                    "card_not_present_new_device",
                    0.30,
                    burst_txns,
                    "online burst from a new device",
                )
            )
            self._add(
                f"New-device CNP signature: {len(burst_txns)} online transactions in "
                f"48h inconsistent with history, from a device marked New for this account",
                "graph",
                "q_device_profile",
                [t.txn_id for t in burst_txns],
            )
        elif burst:
            candidates.append(
                (
                    "card_not_present_fraud",
                    0.24,
                    burst_txns,
                    "online burst inconsistent with history",
                )
            )
            self._add(
                f"Card-not-present signature: {len(burst_txns)} online transactions in "
                f"48h with amounts not fitting the card's history",
                "graph",
                "q_card_history",
                [t.txn_id for t in burst_txns],
            )
        # undocumented: coordinated abuse across customers fitting none above
        if not candidates and (
            len(coordinated_cards) >= 2 or len(region_cards) >= 3
        ):
            shared_origin = True
            candidates.append(
                (
                    "undocumented",
                    0.30,
                    [flagged],
                    "coordinated cross-card abuse with no known-pattern match",
                )
            )
            self._add(
                "Coordinated cross-card activity fits none of the five documented "
                "patterns; treating as undocumented abuse pending analyst review",
                "graph",
                "q_device_sharing",
                [flagged_txn_id, card_id],
            )
        recurring, recurring_detail = _detect_recurring(card_txns, flagged)
        if recurring:
            self._add(
                f"Recurring-pattern match (R7): {recurring_detail}",
                "graph",
                "q_card_history",
                [flagged_txn_id, card_id],
            )

        # similar prior cases (case memory)
        self._step()  # 7
        self._call("q_closed_cases")
        pattern_guess = (
            max(candidates, key=lambda c: c[1])[0] if candidates else None
        )
        similar: List[ClosedCase] = store.find_similar_cases(
            pattern=pattern_guess, customer_id=customer_id, card_id=card_id, limit=5
        )
        similar_ids = [c.case_id for c in similar]
        for cc in similar:
            self._add(
                f"Prior case {cc.case_id} ({cc.outcome}, pattern={cc.pattern}): "
                f"{cc.analyst_notes[:160]}",
                "graph",
                "q_closed_cases",
                [cc.case_id],
            )
        # policy document evidence
        self._call("doc:fraud-policy")
        self._add(
            "Fraud Policy v1.0 R1-R10 governs actions, approval routes "
            "(auto/L1/L2), SAR conditions, case-open threshold (0.30), and stopping criteria",
            "document",
            "doc:fraud-policy",
            [],
        )

        # ---- scoring ----------------------------------------------------
        self._step()  # 8
        prob = 0.08
        n_signals = 0
        if trigger_type == "customer_report":
            prob += 0.35
            n_signals += 1
        for _name, weight, _txns, _detail in candidates:
            prob += weight
            n_signals += 1
        if shared_origin:
            prob += 0.16
            n_signals += 1
        n_confirmed_similar = sum(
            1 for c in similar if c.outcome == "confirmed_fraud"
        )
        prob += 0.05 * min(n_confirmed_similar, 3)
        if risk_score is not None:
            prob += max(-0.10, min(0.12, (risk_score - 0.5) * 0.25))
        if prior_amts and abs(flagged.amt) > 5 * max(prior_median, _EPS):
            prob += 0.12
            n_signals += 1
            self._add(
                f"Amount spike: flagged ${abs(flagged.amt):.2f} exceeds 5x the "
                f"card's 60-day median (${prior_median:.2f})",
                "graph",
                "q_card_history",
                [flagged_txn_id],
            )
        if recurring:
            prob -= 0.38
        prob = max(0.01, min(0.99, prob))

        if candidates:
            pattern = max(candidates, key=lambda c: (c[1], -PATTERN_PRIORITY.index(c[0])))[0]
            episode_txns = max(candidates, key=lambda c: c[1])[2]
        else:
            pattern = "none"
            episode_txns = []
        pattern_description = ""
        if pattern == "undocumented":
            # describe the actual winning signature: structuring if that
            # candidate won, else the cross-card coordination
            struct_won = structuring and all(
                t in struct_txns for t in episode_txns
            )
            if struct_won:
                pattern_description = (
                    f"{struct_detail}. Amounts appear chosen to stay under an "
                    f"authorization threshold; the signature matches none of the "
                    f"five documented patterns. Found in the card's own "
                    f"transaction history in the graph."
                )
            else:
                who = (
                    f"{len(coordinated_cards)} cards on one device profile"
                    if coordinated_cards
                    else f"{len(region_cards)} cards in billing region {flagged.addr1}"
                )
                pattern_description = (
                    f"Coordinated abuse across {who} within a short window that matches "
                    f"none of the five documented patterns. Found by joining device-profile "
                    f"and billing-region edges across cards in the graph; the shared origin "
                    f"is the evidence, not any single transaction."
                )
        if pattern == "none" and prob >= 0.30:
            # suspicious but no documented signature: keep undocumented out unless
            # there is coordination; otherwise leave pattern none with low prob.
            pass

        affected = sorted({t.txn_id for t in episode_txns} | ({flagged_txn_id} if pattern != "none" else set()))
        if pattern == "none":
            affected = []
        first_suspicious = (
            min(
                (store.get_txn(tid) for tid in affected),
                key=lambda t: t.ts if t else flagged.ts,
            ).txn_id
            if affected
            else ""
        )
        exposure = round(
            sum(abs(store.get_txn(tid).amt) for tid in affected if store.get_txn(tid)),
            2,
        )
        connected_cards = sorted(set(shared_cards) | set(coordinated_cards))
        connected_profiles = [profile] if profile and shared_cards else []

        # ---- initial next-best actions (policy) --------------------------
        self._step()  # 9
        customer_dispute = trigger_type == "customer_report"
        evidence_requested = False
        initial: List[Dict[str, str]] = []

        def add_action(action: str, rule: str, reason: str) -> None:
            route = policy_mod.get_route(
                action, exposure if action == "BLOCK_CARD" else 0.0
            )
            initial.append({"action": action, "route": route, "reason": reason})

        open_case = policy_mod.should_open_case(
            prob, evidence_requested=False, customer_dispute=customer_dispute
        )
        if customer_dispute and recurring:
            # R7: disputed but legitimate recurring charge — no block.
            add_action(
                "CREATE_CASE",
                "R7",
                "R7: disputed charge matches the card's own recurring pattern; "
                "open a case without blocking",
            )
            add_action(
                "VERIFY_WITH_CUSTOMER",
                "R7",
                "R7: verify the recurring charge with the cardholder",
            )
            add_action(
                "WARN_CUSTOMER",
                "R7",
                "R7: send a recurring-charge reminder",
            )
        elif customer_dispute:
            # R2: the denial is already in hand via the trigger.
            add_action(
                "BLOCK_CARD",
                "R2",
                f"R2: customer {customer_id} denies transaction {flagged_txn_id}; "
                "recommend BLOCK_CARD and CREATE_CASE",
            )
            add_action(
                "CREATE_CASE",
                "R2",
                "R2: open a case with the evidence attached and write it to the graph",
            )
            if exposure > 1000 or shared_origin:
                add_action(
                    "FILE_REPORT",
                    "R2",
                    "R2/3a: exposure exceeds $1,000 or the case connects to a shared "
                    "device profile or another card's fraud",
                )
            if shared_origin and connected_cards:
                add_action(
                    "MONITOR_CONNECTED_CARDS",
                    "R6",
                    f"R6: shared origin links {len(connected_cards)} other card(s)",
                )
        elif trigger_type == "analyst_request":
            evidence_requested = True
            add_action(
                "CREATE_CASE",
                "3a",
                "3a: evidence is being requested; open a case and write it to the graph",
            )
            if shared_origin:
                add_action(
                    "FILE_REPORT",
                    "R6",
                    "R6: several cards show fraud from the same device profile; "
                    "name the shared element and file",
                )
                add_action(
                    "MONITOR_CONNECTED_CARDS",
                    "R6",
                    "R6: monitor every card sharing the device profile",
                )
            else:
                add_action(
                    "VERIFY_WITH_CUSTOMER",
                    "R1",
                    "R1: single weak signal; verify before any block",
                )
        else:  # risk_score trigger
            if pattern == "card_testing":
                big_cleared = any(abs(t.amt) > 100 for t in episode_txns)
                if big_cleared:
                    add_action(
                        "BLOCK_CARD",
                        "R5",
                        "R5: card-testing sequence with a purchase over $100 cleared",
                    )
                else:
                    add_action(
                        "DECLINE_TRANSACTION",
                        "R5",
                        "R5: card-testing authorizations; decline the flagged authorization",
                    )
                    add_action(
                        "STEP_UP_AUTH",
                        "R5",
                        "R5: require step-up authentication before further activity",
                    )
                add_action("CREATE_CASE", "3a", "3a: fraud probability >= 0.30")
            elif prob < 0.70 and n_signals < 2:
                # R1: weak single signal -> verify before any block
                evidence_requested = True
                add_action(
                    "VERIFY_WITH_CUSTOMER",
                    "R1",
                    "R1: case rests on a single signal and fraud probability is "
                    f"below 0.70 ({prob:.2f}); verify before any block",
                )
                # 3a: evidence is being requested, so a case must be opened.
                # (open_case was computed before evidence_requested was set.)
                open_case = policy_mod.should_open_case(
                    prob, evidence_requested=True, customer_dispute=customer_dispute
                )
                if open_case:
                    add_action("CREATE_CASE", "3a", "3a: evidence requested")
            else:
                add_action(
                    "BLOCK_CARD",
                    "R1/R2",
                    f"Fraud probability {prob:.2f} supported by {n_signals} independent "
                    "signals; recommend block with human approval",
                )
                add_action("CREATE_CASE", "3a", "3a: fraud probability >= 0.30")
                if exposure > 1000 or shared_origin or pattern == "undocumented":
                    add_action(
                        "FILE_REPORT",
                        "3a",
                        "3a: SAR conditions met (exposure > $1,000, shared origin, "
                        "or undocumented pattern)",
                    )
                if shared_origin and connected_cards:
                    add_action(
                        "MONITOR_CONNECTED_CARDS",
                        "R6",
                        "R6: monitor every card sharing the origin",
                    )
        if pattern == "undocumented" and not any(
            a["action"] == "ESCALATE_TO_ANALYST" for a in initial
        ):
            add_action(
                "ESCALATE_TO_ANALYST",
                "R9",
                "R9: undocumented pattern; describe in own words and escalate",
            )
        # R8: escalate when uncertain and exposed. This is an initial
        # recommendation: final must equal initial when no evidence was
        # requested, so the escalation cannot be appended later.
        uncertain_now = not (prob >= 0.85 or prob <= 0.15)
        if uncertain_now and (exposure > 500 or n_signals == 0) and not any(
            a["action"] == "ESCALATE_TO_ANALYST" for a in initial
        ):
            add_action(
                "ESCALATE_TO_ANALYST",
                "R8",
                "R8: verdict is uncertain and exposure exceeds $500 (or "
                "evidence conflicts); hand to a human analyst",
            )
        if (
            not open_case
            and not evidence_requested
            and not any(a["action"] == "CREATE_CASE" for a in initial)
        ):
            add_action(
                "GENERATE_REPORT",
                "3a",
                "3a: fraud probability below 0.30 with no evidence requested and "
                "no dispute; write up without opening a case",
            )

        # ---- evidence requests (simulated replies) -----------------------
        self._step()  # 10
        evidence_requests: List[Dict[str, Any]] = []
        assumed_customer = ""
        if evidence_requested:
            if any(a["action"] == "VERIFY_WITH_CUSTOMER" for a in initial):
                if prob >= 0.55:
                    assumed_customer = "deny"
                    assumed_text = (
                        "Customer denies the transaction when contacted "
                        "(simulated reply consistent with the fraud evidence)"
                    )
                elif prob <= 0.30:
                    assumed_customer = "confirm"
                    assumed_text = (
                        "Customer confirms the transaction as their own "
                        "(simulated reply consistent with the weak evidence)"
                    )
                else:
                    assumed_customer = "no_reply"
                    assumed_text = (
                        "No reply within 24 hours "
                        "(simulated; policy R4 applies)"
                    )
                evidence_requests.append(
                    {
                        "type": "customer_validation",
                        "asked_after_step": 9,
                        "assumed_response": assumed_text,
                    }
                )
            if any(a["action"] == "STEP_UP_AUTH" for a in initial):
                evidence_requests.append(
                    {
                        "type": "step_up_auth",
                        "asked_after_step": 9,
                        "assumed_response": (
                            "Step-up challenge unanswered within the window "
                            "(simulated)"
                        ),
                    }
                )
            if trigger_type == "analyst_request":
                evidence_requests.append(
                    {
                        "type": "analyst_info",
                        "asked_after_step": 9,
                        "assumed_response": (
                            "Analyst confirms the device profile is under review "
                            "across multiple cards this month (simulated)"
                        ),
                    }
                )

        # ---- final actions ------------------------------------------------
        final: List[Dict[str, str]] = []

        def add_final(action: str, rule: str, reason: str) -> None:
            route = policy_mod.get_route(
                action, exposure if action == "BLOCK_CARD" else 0.0
            )
            final.append({"action": action, "route": route, "reason": reason})

        if customer_dispute:
            final = [dict(a) for a in initial]
            what_changed = "nothing"
        elif not evidence_requests:
            final = [dict(a) for a in initial]
            what_changed = "nothing"
        elif assumed_customer == "confirm":
            # R3
            add_final(
                "CLOSE_NO_FRAUD",
                "R3",
                "R3: customer confirms the transaction; close as legitimate and "
                "note the confirmation",
            )
            what_changed = (
                "the customer confirmed the transaction, so the R1 verification "
                "recommendation resolved to CLOSE_NO_FRAUD under R3"
            )
        elif assumed_customer == "no_reply":
            # R4
            add_final(
                "MONITOR_CARD",
                "R4",
                "R4: no reply within 24 hours; raise monitoring sensitivity",
            )
            add_final(
                "DECLINE_TRANSACTION",
                "R4",
                "R4: decline pending authorizations until the customer responds",
            )
            if exposure > 500:
                add_final(
                    "ESCALATE_TO_ANALYST",
                    "R4",
                    "R4: exposure exceeds $500 with no reply; escalate",
                )
            if open_case:
                add_final("CREATE_CASE", "3a", "3a: evidence was requested")
            what_changed = (
                "no customer reply within 24 hours, so verification became "
                "MONITOR_CARD plus DECLINE_TRANSACTION under R4"
            )
        elif trigger_type == "analyst_request" and not assumed_customer:
            # Analyst-requested review with no customer contact: the customer
            # was never reached, so no denial exists and R2 language is
            # forbidden here. The analyst's reply drives R6 (shared origin)
            # or the R1 verification track.
            add_final(
                "CREATE_CASE",
                "3a",
                "3a: evidence was requested; keep the case open with the findings",
            )
            if shared_origin and connected_cards:
                add_final(
                    "FILE_REPORT",
                    "R6",
                    "R6: analyst confirms the device profile is under review "
                    "across multiple cards; file naming the shared element",
                )
                add_final(
                    "MONITOR_CONNECTED_CARDS",
                    "R6",
                    "R6: monitor every card sharing the device profile",
                )
            else:
                add_final(
                    "VERIFY_WITH_CUSTOMER",
                    "R1",
                    "R1: analyst review found no shared origin; verify the "
                    "flagged transaction with the cardholder before any block",
                )
            if pattern == "undocumented":
                add_final(
                    "ESCALATE_TO_ANALYST",
                    "R9",
                    "R9: undocumented pattern; escalate with the description",
                )
            what_changed = (
                "the analyst confirmed the device profile is under review "
                "across multiple cards, so the case proceeds on the R6 "
                "shared-origin track"
                if shared_origin
                else "the analyst's review found no shared device origin, so "
                "the case stays on the R1 verification track; no customer "
                "denial exists"
            )
        else:  # deny -> R2 / R6
            add_final(
                "BLOCK_CARD",
                "R2",
                f"R2: customer denies transaction {flagged_txn_id}; recommend "
                "BLOCK_CARD and CREATE_CASE",
            )
            add_final(
                "CREATE_CASE",
                "R2",
                "R2: open a case with the evidence attached and write it to the graph",
            )
            if exposure > 1000 or shared_origin:
                add_final(
                    "FILE_REPORT",
                    "R2",
                    "R2/3a: exposure exceeds $1,000 or shared device/another "
                    "card's fraud",
                )
            if shared_origin and connected_cards:
                add_final(
                    "MONITOR_CONNECTED_CARDS",
                    "R6",
                    "R6: monitor every card sharing the origin",
                )
            if pattern == "undocumented":
                add_final(
                    "ESCALATE_TO_ANALYST",
                    "R9",
                    "R9: undocumented pattern; escalate with the description",
                )
            what_changed = (
                "the customer denied the transaction, so the R1 verification "
                "recommendation escalated to BLOCK_CARD and CREATE_CASE under R2"
                + (
                    ", with FILE_REPORT under R2/3a"
                    if any(a["action"] == "FILE_REPORT" for a in final)
                    else ""
                )
            )

        # (R7 is handled in the initial recommendations above: a disputed
        # recurring charge never takes the block path, so final==initial
        # holds here.)

        # verdict / status
        if assumed_customer == "confirm" or (recurring and trigger_type == "customer_report"):
            verdict = "legitimate"
            prob = min(prob, 0.10)
            pattern = "none"
            pattern_description = ""
            affected = []
            exposure = 0.0
            first_suspicious = ""
        elif prob >= 0.85 and n_signals >= 2:
            verdict = "fraud"
        elif prob <= 0.15 and n_signals <= 1:
            verdict = "legitimate"
            pattern = "none"
            affected = []
            exposure = 0.0
            first_suspicious = ""
        else:
            verdict = "uncertain"
        status = (
            "closed_fraud"
            if verdict == "fraud"
            else "closed_legitimate"
            if verdict == "legitimate"
            else "escalated"
        )

        # R8 re-application: the deny / no-reply / analyst final branches
        # rebuild the action list from scratch and must not drop a required
        # escalation. (The customer_dispute / no-evidence / confirm branches
        # either copy initial — which already applied R8 — or resolve to a
        # non-uncertain verdict, so the guard below is a no-op for them.)
        if (
            verdict == "uncertain"
            and (exposure > 500 or n_signals == 0)
            and not any(a["action"] == "ESCALATE_TO_ANALYST" for a in final)
        ):
            add_final(
                "ESCALATE_TO_ANALYST",
                "R8",
                "R8: verdict is uncertain and exposure exceeds $500 (or "
                "evidence conflicts); hand to a human analyst",
            )

        # ---- SAR ----------------------------------------------------------
        strongly_suspected = verdict == "fraud" or (prob >= 0.70 and n_signals >= 2)
        file_sar = policy_mod.sar_required(
            prob,
            exposure,
            shared_origin=shared_origin,
            pattern=pattern,
            strongly_suspected=strongly_suspected,
        )
        # FILE_REPORT in final actions must agree with sar.file.
        # When no evidence was requested, final must equal initial, so the
        # reconciliation applies to both lists (they are the same content).
        has_file_report = any(a["action"] == "FILE_REPORT" for a in final)
        reconcile_targets = (
            (initial, final) if not evidence_requests else (final,)
        )
        if file_sar and not has_file_report:
            for target in reconcile_targets:
                target.append(
                    {
                        "action": "FILE_REPORT",
                        "route": "L2",
                        "reason": "3a: SAR conditions met; file with fraud-manager approval",
                    }
                )
        elif has_file_report and not file_sar:
            for target in reconcile_targets:
                target[:] = [
                    a for a in target if a["action"] != "FILE_REPORT"
                ]
        # what_changed was drafted before FILE_REPORT reconciliation; fix its
        # FILE_REPORT mention to match the reconciled final list.
        if what_changed != "nothing":
            fr_suffix = ", with FILE_REPORT under R2/3a"
            base = (
                what_changed[: -len(fr_suffix)]
                if what_changed.endswith(fr_suffix)
                else what_changed
            )
            if any(a["action"] == "FILE_REPORT" for a in final):
                what_changed = base + fr_suffix
            else:
                what_changed = base
        sar = self._build_sar(
            file_sar,
            prob,
            verdict,
            pattern,
            affected,
            exposure,
            shared_origin,
            connected_cards,
            profile,
            customer_id,
            card_id,
            store,
            flagged,
        )

        # ---- stop reason ---------------------------------------------------
        n_evidence = len(self.evidence)
        if prob >= 0.85 and n_evidence >= 2:
            stop_reason = (
                f"Fraud probability {prob:.2f} at or above 0.85, supported by "
                f"{n_evidence} independent pieces of evidence"
            )
        elif prob <= 0.15 and n_evidence >= 2:
            stop_reason = (
                f"Fraud probability {prob:.2f} at or below 0.15, supported by "
                f"{n_evidence} independent pieces of evidence"
            )
        elif assumed_customer in ("deny", "confirm"):
            stop_reason = "A verification response settles the question"
        else:
            stop_reason = (
                "Further steps (additional graph traversals) are unlikely to "
                "change the decision; stopping per policy section 6"
            )

        # ---- write case to graph ------------------------------------------
        self._call("graph:write_case")
        written_to_graph = False
        graph_case_id = ""
        if any(a["action"] == "CREATE_CASE" for a in final):
            case_record = {
                "case_id": self.case_id,
                "status": status,
                "verdict": verdict,
                "pattern": pattern,
                "fraud_probability": round(prob, 4),
                "exposure_usd": exposure,
                "affected_txn_ids": affected,
                "connected_card_ids": connected_cards,
                "connected_device_profiles": connected_profiles,
                "summary": "",
            }
            if self.client is not None:
                try:
                    graph_case_id = self.client.write_case_vertex(case_record)
                    written_to_graph = True
                except Exception:
                    written_to_graph = False
                    graph_case_id = ""
            self._add(
                f"Case {self.case_id} written to the graph as {graph_case_id or 'pending'} "
                "so later investigations can retrieve it",
                "graph",
                "graph:write_case",
                [graph_case_id or self.case_id],
            )

        summary = self._summarize(
            verdict, prob, pattern, affected, exposure, customer_id, card_id,
            flagged, trigger_type, similar_ids,
        )
        if written_to_graph and self.client is not None:
            # refresh the stored summary for case memory
            vid = f"CASE-{self.case_id}"
            if vid in self.client._case_ledger:
                self.client._case_ledger[vid]["summary"] = summary

        latency = round(time.time() - started, 3)
        answer = {
            "case_id": self.case_id,
            "case": {
                "status": status,
                "verdict": verdict,
                "fraud_probability": round(prob, 4),
                "pattern": pattern,
                "pattern_description": pattern_description,
                "affected_txn_ids": affected,
                "first_suspicious_txn_id": first_suspicious,
                "connected_card_ids": connected_cards,
                "connected_device_profiles": connected_profiles,
                "exposure_usd": exposure,
                "evidence": self.evidence,
                "similar_prior_cases": similar_ids,
                "summary": summary,
                "written_to_graph": written_to_graph,
                "graph_case_id": graph_case_id,
            },
            "evidence_requests": evidence_requests,
            "next_best_actions": {
                "initial": initial,
                "final": final,
                "what_changed": what_changed,
            },
            "sar": sar,
            "stop_reason": stop_reason,
            "tool_calls": self.tool_calls,
            "tokens": 0,
            "latency_s": latency,
        }
        return answer

    # -- fallback when the flagged txn is absent ---------------------------
    def _fallback_answer(
        self,
        flagged_txn_id: str,
        card_id: str,
        customer_id: str,
        trigger_text: str,
        started: float,
    ) -> Dict[str, Any]:
        self._add(
            f"Flagged transaction {flagged_txn_id} is not present in the local "
            "dataset (offline synthetic fallback); no evidence can be gathered",
            "graph",
            "q_flagged_transaction",
            [flagged_txn_id],
        )
        latency = round(time.time() - started, 3)
        return {
            "case_id": self.case_id,
            "case": {
                "status": "escalated",
                "verdict": "uncertain",
                "fraud_probability": 0.5,
                "pattern": "none",
                "pattern_description": "",
                "affected_txn_ids": [],
                "first_suspicious_txn_id": "",
                "connected_card_ids": [],
                "connected_device_profiles": [],
                "exposure_usd": 0.0,
                "evidence": self.evidence,
                "similar_prior_cases": [],
                "summary": (
                    f"OFFLINE SYNTHETIC FALLBACK: flagged transaction {flagged_txn_id} "
                    f"for card {card_id} is absent from the local fallback data, so no "
                    "defensible decision is possible. Escalated for human review; "
                    "re-run against the official HHGOA_IEEE dataset."
                ),
                "written_to_graph": False,
                "graph_case_id": "",
            },
            "evidence_requests": [],
            "next_best_actions": {
                "initial": [
                    {
                        "action": "ESCALATE_TO_ANALYST",
                        "route": "auto",
                        "reason": "R8: no evidence available; hand to a human analyst",
                    },
                    {
                        "action": "GENERATE_REPORT",
                        "route": "auto",
                        "reason": "3a: record the data gap without opening a case",
                    },
                ],
                "final": [
                    {
                        "action": "ESCALATE_TO_ANALYST",
                        "route": "auto",
                        "reason": "R8: no evidence available; hand to a human analyst",
                    },
                    {
                        "action": "GENERATE_REPORT",
                        "route": "auto",
                        "reason": "3a: record the data gap without opening a case",
                    },
                ],
                "what_changed": "nothing",
            },
            "sar": {
                "file": False,
                "reason": "3a: fraud is neither confirmed nor strongly suspected",
                "narrative": "",
                "subjects": [],
                "total_amount_usd": 0,
                "activity_dates": [],
            },
            "stop_reason": (
                "Further steps are unlikely to change the decision: the flagged "
                "transaction is absent from the local data"
            ),
            "tool_calls": self.tool_calls,
            "tokens": 0,
            "latency_s": latency,
        }

    # -- SAR -----------------------------------------------------------------
    def _build_sar(
        self,
        file_sar: bool,
        prob: float,
        verdict: str,
        pattern: str,
        affected: List[str],
        exposure: float,
        shared_origin: bool,
        connected_cards: List[str],
        profile: str,
        customer_id: str,
        card_id: str,
        store: HHGOAStore,
        flagged: Txn,
    ) -> Dict[str, Any]:
        if not file_sar:
            conditions = []
            if exposure > 1000:
                conditions.append(f"exposure ${exposure:,.2f} exceeds $1,000")
            else:
                conditions.append(f"exposure ${exposure:,.2f} is within $1,000")
            conditions.append(
                "shared origin present" if shared_origin else "no shared origin"
            )
            conditions.append(
                "undocumented pattern" if pattern == "undocumented"
                else f"pattern is {pattern}"
            )
            return {
                "file": False,
                "reason": (
                    "3a: fraud is neither confirmed nor strongly suspected "
                    f"({', '.join(conditions)}); no SAR filed"
                ),
                "narrative": "",
                "subjects": [],
                "total_amount_usd": 0,
                "activity_dates": [],
            }
        txns = [store.get_txn(t) for t in affected]
        txns = [t for t in txns if t]
        dates = sorted(t.ts.strftime("%Y-%m-%d") for t in txns) if txns else [
            flagged.ts.strftime("%Y-%m-%d")
        ]
        channels = sorted({t.channel for t in txns}) if txns else [flagged.channel]
        regions = sorted({t.addr1 for t in txns if t.addr1})
        who = (
            f"customer {customer_id}, card {card_id}"
            + (
                f", with connected cards {', '.join(connected_cards[:4])}"
                if connected_cards
                else ""
            )
        )
        what = (
            f"{len(affected)} transaction(s) totaling ${exposure:,.2f} identified as "
            f"a {pattern.replace('_', ' ')} episode"
        )
        when = f"between {dates[0]} and {dates[-1]}"
        where = (
            f"via {', '.join(channels)} channels"
            + (f" in billing region(s) {', '.join(regions[:4])}" if regions else "")
        )
        how = (
            f"The flagged transaction {flagged.txn_id} (${flagged.amt:.2f}) triggered "
            f"review; graph analysis of the card's history, device records, and "
            f"cross-card device/region edges identified the episode."
            + (
                f" A shared device profile links this case to {len(connected_cards)} "
                "other card(s)."
                if shared_origin and connected_cards
                else ""
            )
        )
        why = (
            f"The activity is inconsistent with the cardholder's history and matches "
            f"the {pattern.replace('_', ' ')} pattern (assessed fraud probability "
            f"{prob:.2f} from {len(self.evidence)} evidence items); innocent "
            "explanations were considered and rejected on the evidence."
        )
        narrative = (
            f"WHO: {who}. WHAT: {what}. WHEN: {when}. WHERE: {where}. "
            f"HOW: {how} WHY SUSPICIOUS: {why}"
        )
        subjects = [customer_id, card_id] + connected_cards[:4]
        if profile:
            subjects.append(profile[:80])
        return {
            "file": True,
            "reason": (
                "3a: fraud is confirmed or strongly suspected and at least one SAR "
                "condition holds: "
                + ", ".join(
                    c
                    for c, hold in (
                        (f"exposure ${exposure:,.2f} exceeds $1,000", exposure > 1000),
                        ("shared device profile / region cluster / another card's fraud", shared_origin),
                        ("coordinated or undocumented pattern (R9)", pattern == "undocumented"),
                    )
                    if hold
                )
            ),
            "narrative": narrative,
            "subjects": subjects,
            "total_amount_usd": exposure,
            "activity_dates": [dates[0], dates[-1]],
        }

    # -- summary ---------------------------------------------------------------
    def _summarize(
        self,
        verdict: str,
        prob: float,
        pattern: str,
        affected: List[str],
        exposure: float,
        customer_id: str,
        card_id: str,
        flagged: Txn,
        trigger_type: str,
        similar_ids: List[str],
    ) -> str:
        trig = {
            "risk_score": "a risk-score alert",
            "customer_report": "a customer denial",
            "analyst_request": "an analyst request",
        }.get(trigger_type, "an alert")
        base = (
            f"Case {self.case_id}: {trig} on transaction {flagged.txn_id} "
            f"(${flagged.amt:.2f}, {flagged.channel}) for card {card_id}."
        )
        if verdict == "fraud":
            mid = (
                f" Investigation found a {pattern.replace('_', ' ')} episode of "
                f"{len(affected)} transaction(s) with exposure ${exposure:,.2f} "
                f"(fraud probability {prob:.2f})."
            )
        elif verdict == "legitimate":
            mid = (
                f" The activity is consistent with legitimate use (fraud probability "
                f"{prob:.2f}); no fraud episode identified."
            )
        else:
            mid = (
                f" Evidence is inconclusive (fraud probability {prob:.2f}); "
                "escalated for human review."
            )
        mem = (
            f" Similar prior cases consulted: {', '.join(similar_ids)}."
            if similar_ids
            else " No sufficiently similar prior cases found."
        )
        return (base + mid + mem).strip()


def investigate(
    case_input: Dict[str, Any], store: HHGOAStore, client: Any = None
) -> Dict[str, Any]:
    """Run one investigation and return the official answer record."""
    return Investigation(case_input, store, client).run()
