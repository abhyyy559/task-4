"""Investigator tests: pattern detectors + fallback answer path.

Detector unit tests use synthetic Txn objects (no dataset needed). The
fallback path is exercised with an empty store: a flagged txn absent from
the data must yield an honest uncertain/escalated answer, never a
fabricated verdict.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.agent.investigate import (
    _detect_card_testing,
    _detect_cnp_burst,
    _detect_out_of_region,
    _detect_recurring,
    _detect_structuring,
    investigate,
)
from src.agent.state import validate_output
from src.data.hhgoa import HHGOAStore, Txn

BASE = datetime(2016, 12, 5, 12, 0, 0, tzinfo=timezone.utc)


def _txn(tid, minutes=0, amt=50.0, channel="online", addr1="101", card1="111",
         customer="C99999"):
    return Txn(
        txn_id=str(tid), customer_id=customer, card1=card1,
        ts=BASE + timedelta(minutes=minutes), dt=0, amt=amt, product="C",
        channel=channel, addr1=addr1, addr2="87", p_email="a@x.com",
        r_email="b@y.com", risk=0.5,
    )


def test_detect_card_testing():
    txns = [
        _txn("t1", minutes=0, amt=1.5), _txn("t2", minutes=10, amt=2.0),
        _txn("t3", minutes=20, amt=1.0), _txn("t4", minutes=90, amt=250.0),
    ]
    found, seq = _detect_card_testing(txns)
    assert found and len(seq) >= 4


def test_detect_card_testing_negative():
    txns = [_txn("t1", minutes=0, amt=50.0), _txn("t2", minutes=10, amt=60.0)]
    found, _ = _detect_card_testing(txns)
    assert not found


def test_detect_cnp_burst():
    # Official pattern: 2-4 online txns within 48h. Keep older history outside
    # the 48h window so the burst is exactly 3 (b1, b2, ref).
    prior = [_txn(f"p{i}", minutes=-60 * 24 * i, amt=20.0) for i in range(3, 20)]
    ref = _txn("flag", minutes=0, amt=300.0)
    burst_txns = [_txn("b1", minutes=-60, amt=280.0), _txn("b2", minutes=-30, amt=310.0)]
    all_txns = prior + burst_txns + [ref]
    found, burst = _detect_cnp_burst(all_txns, ref, 20.0, 25.0)
    assert found and len(burst) == 3


def test_detect_out_of_region():
    home = [_txn(f"h{i}", minutes=-60 * 24 * i, amt=40.0, channel="in_person", addr1="101")
            for i in range(1, 10)]
    ref = _txn("flag", minutes=0, amt=80.0, channel="in_person", addr1="444")
    home_now = _txn("hh", minutes=-60, amt=30.0, channel="in_person", addr1="101")
    found, txns, region = _detect_out_of_region(home + [home_now, ref], ref)
    assert found and region == "444"


def test_detect_recurring():
    txns = [
        _txn("r1", minutes=-60 * 24 * 60, amt=49.0),
        _txn("r2", minutes=-60 * 24 * 30, amt=49.0),
        _txn("flag", minutes=0, amt=49.0),
    ]
    found, detail = _detect_recurring(txns, txns[-1])
    assert found and "monthly" in detail


class _EmptyStore:
    """Minimal store stub: flagged txn always absent."""

    def get_txn(self, txn_id):
        return None


def test_fallback_answer_when_flagged_txn_absent():
    store = _EmptyStore()
    case_input = {
        "case_id": "HHG-001", "trigger_type": "risk_score",
        "flagged_txn_id": "3514030", "card_id": "C12382-K1",
        "customer_id": "C12382", "trigger_text": "scored 0.61",
    }
    answer = investigate(case_input, store, client=None)
    assert validate_output(answer) == []
    case = answer["case"]
    assert case["verdict"] == "uncertain"
    assert case["status"] == "escalated"
    assert case["pattern"] == "none"
    assert case["exposure_usd"] == 0.0
    assert answer["sar"]["file"] is False
    assert "FALLBACK" in case["summary"]
    finals = [a["action"] for a in answer["next_best_actions"]["final"]]
    assert "ESCALATE_TO_ANALYST" in finals


def test_fallback_never_invents_evidence_ids():
    store = _EmptyStore()
    answer = investigate(
        {"case_id": "HHG-002", "trigger_type": "risk_score",
         "flagged_txn_id": "3478782", "card_id": "C11891-K1",
         "customer_id": "C11891", "trigger_text": "x"},
        store, client=None,
    )
    assert answer["case"]["affected_txn_ids"] == []


def test_detect_structuring_positive():
    ref = _txn("flag", minutes=0, amt=499.0)
    txns = [
        _txn("s1", minutes=-50, amt=95.0), _txn("s2", minutes=-40, amt=97.5),
        _txn("s3", minutes=-30, amt=99.0), _txn("s4", minutes=-20, amt=92.0),
        ref,
    ]
    found, seq, detail = _detect_structuring(txns, ref)
    assert found and len(seq) == 4 and "100" in detail


def test_detect_structuring_stale_window_ignored():
    # structuring 100 days before the flag must not drive the verdict
    ref = _txn("flag", minutes=0, amt=499.0)
    txns = [
        _txn("s1", minutes=-100 * 24 * 60, amt=95.0),
        _txn("s2", minutes=-100 * 24 * 60 + 10, amt=97.5),
        _txn("s3", minutes=-100 * 24 * 60 + 20, amt=99.0),
        ref,
    ]
    found, _, _ = _detect_structuring(txns, ref)
    assert not found


def test_detect_structuring_negative():
    ref = _txn("flag", minutes=0, amt=499.0)
    txns = [_txn("s1", minutes=-50, amt=45.0), _txn("s2", minutes=-40, amt=60.0), ref]
    found, _, _ = _detect_structuring(txns, ref)
    assert not found
