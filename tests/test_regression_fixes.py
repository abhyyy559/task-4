"""Regression tests for the four must-fix behaviors (2026-09-21 rounds).

Covers, end-to-end on a synthetic fallback CSV dataset, the behaviors that
caused repeated review/tester findings:

A. analyst_request + shared origin (HHG-014 shape): the analyst-info final
   branch must never fabricate a customer denial; shared-origin analyst
   confirmation uses R6 (CREATE_CASE, FILE_REPORT, MONITOR_CONNECTED_CARDS).
B. weak-signal R1 path (HHG-001 shape): any evidence request adds CREATE_CASE
   per 3a; GENERATE_REPORT is permitted only when no evidence is requested.
C. deny path with exposure > $1,000 and an uncertain verdict (HHG-013 shape):
   R8 is re-applied to the rebuilt final actions; FILE_REPORT reconciliation
   strips it from the final list when no SAR is filed; what_changed does not
   claim FILE_REPORT; the SAR not-filed reason is dynamic and factual.

All assertions were verified behaviorally against the real investigator
before being pinned here.
"""
from __future__ import annotations

import csv

from src.agent.investigate import investigate
from src.agent.state import validate_output
from src.data.hhgoa import HHGOAStore

EPOCH = 1467417600  # 2016-07-02 00:00:00 UTC, seconds

PROF_NEW = ("dev-X", "MacOS", "Safari", "1024x768")
PROF_OLD = ("dev-old", "Windows", "Chrome", "1920x1080")
PROF_Z = ("dev-Z", "Linux", "Firefox", "1600x900")
PROF_W = ("dev-W", "Windows", "Edge", "1366x768")


def _dt(day=0, hour=0, minute=0):
    return EPOCH + day * 86400 + hour * 3600 + minute * 60


def _row(tid, card1, dt, amt, id15="Found", prof=PROF_OLD):
    return {
        "TransactionID": str(tid), "TransactionDT": str(dt),
        "TransactionAmt": f"{amt:.2f}", "ProductCD": "C",
        "card1": card1, "addr1": "101", "addr2": "87",
        "id15": id15, "prof": prof,
    }


def _build_dataset(tmp_path):
    txns, ids = [], []

    # Scenario A: flagged card 55555 (analyst_request, shared origin).
    t = 1000
    for d in (5, 10, 15, 20, 25):
        txns.append(_row(t, "55555", _dt(day=-d), 25.0, prof=PROF_OLD))
        ids.append((t, "Found", PROF_OLD)); t += 1
    txns.append(_row(t, "55555", _dt(hour=-30), 290.0, prof=PROF_NEW)); t += 1
    txns.append(_row(t, "55555", _dt(hour=-20), 310.0, prof=PROF_NEW)); t += 1
    txns.append(_row(9001, "55555", _dt(), 450.0, id15="New", prof=PROF_NEW))
    ids.append((9001, "New", PROF_NEW))
    # Other card 66666 on the same device profile with coordinated burst.
    t = 2000
    for d in (5, 10, 15, 20, 25):
        txns.append(_row(t, "66666", _dt(day=-d), 20.0, prof=PROF_NEW))
        ids.append((t, "Found", PROF_NEW)); t += 1
    for h in (30, 20, 10):
        txns.append(_row(t, "66666", _dt(hour=-h), 295.0, prof=PROF_NEW))
        ids.append((t, "Found", PROF_NEW)); t += 1

    # Scenario B: flagged card 77777 (risk_score, weak signal -> no_reply).
    t = 3000
    for d in (5, 10, 15):
        txns.append(_row(t, "77777", _dt(day=-d), 20.0, prof=PROF_Z))
        ids.append((t, "Found", PROF_Z)); t += 1
    txns.append(_row(t, "77777", _dt(hour=-30), 120.0, prof=PROF_Z)); t += 1
    txns.append(_row(t, "77777", _dt(hour=-15), 125.0, prof=PROF_Z)); t += 1
    txns.append(_row(9002, "77777", _dt(), 90.0, prof=PROF_Z))
    ids.append((9002, "Found", PROF_Z))

    # Scenario C: flagged card 88888 (burst CNP, customer denies,
    # exposure > $1,000, uncertain verdict).
    t = 4000
    for d in (5, 10, 15, 20, 25):
        txns.append(_row(t, "88888", _dt(day=-d), 100.0, prof=PROF_W))
        ids.append((t, "Found", PROF_W)); t += 1
    txns.append(_row(t, "88888", _dt(hour=-30), 350.0, prof=PROF_W)); t += 1
    txns.append(_row(t, "88888", _dt(hour=-15), 360.0, prof=PROF_W)); t += 1
    txns.append(_row(9003, "88888", _dt(), 380.0, prof=PROF_W))
    ids.append((9003, "Found", PROF_W))

    with open(tmp_path / "closed_cases_history.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case_id", "customer_id", "card_id", "opened_at", "closed_at",
                    "outcome", "pattern", "first_fraud_txn_id", "txn_ids", "n_txns",
                    "exposure_usd", "connected_card_ids", "actions_taken",
                    "report_filed", "analyst_notes"])
        for i in range(3):
            w.writerow([f"OLD-00{i+1}", "C00001", "C00001-K1", "2016-01-01",
                        "2016-01-02", "confirmed_fraud", "card_not_present_fraud",
                        "100", "100", "1", "500", "", "BLOCK_CARD", "yes",
                        "online burst inconsistent with history"])
    with open(tmp_path / "transactions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["TransactionID", "TransactionDT",
                                          "TransactionAmt", "ProductCD", "card1",
                                          "addr1", "addr2"])
        w.writeheader()
        for r in txns:
            w.writerow({k: r[k] for k in w.fieldnames})
    with open(tmp_path / "identity.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["TransactionID", "id_15", "id_23", "id_30", "id_31",
                    "id_33", "id_34", "DeviceType", "DeviceInfo"])
        for tid, id15, (di, os_, br, scr) in ids:
            w.writerow([tid, id15, "", os_, br, scr, "", "desktop", di])


def _run(tmp_path, case_id, **kw):
    _build_dataset(tmp_path)
    store = HHGOAStore(tmp_path).load()
    ans = investigate({"case_id": case_id, **kw}, store, client=None)
    assert validate_output(ans) == [], f"{case_id} failed output validation"
    return ans


def _actions(ans, section):
    return [a["action"] for a in ans["next_best_actions"][section]]


def _reasons(ans, section):
    return {a["action"]: a.get("reason", "") for a in ans["next_best_actions"][section]}


def test_analyst_request_shared_origin_never_fabricates_denial(tmp_path):
    """HHG-014 shape: analyst info path must not claim customer denial; R6."""
    a = _run(tmp_path, "HHG-A", trigger_type="analyst_request",
             flagged_txn_id="9001", card_id="C55555-K1", customer_id="C55555",
             trigger_text="Analyst flagged unusual activity on device profile dev-X",
             risk_score=0.6)
    final_reasons = _reasons(a, "final")
    # No fabricated denial anywhere in the final branch.
    for action, reason in final_reasons.items():
        assert "denies" not in reason and "denial" not in reason, \
            f"fabricated denial language in analyst path: {action}"
    # Shared-origin analyst confirmation uses R6 in the initial branch.
    init_reasons = _reasons(a, "initial")
    assert any(act == "FILE_REPORT" and "R6" in r
               for act, r in init_reasons.items()), \
        "initial should carry R6 FILE_REPORT for shared origin"
    assert "MONITOR_CONNECTED_CARDS" in _actions(a, "final")
    # Uncertain verdict => no SAR => reconciliation removes FILE_REPORT.
    assert a["sar"]["file"] is False
    assert "FILE_REPORT" not in _actions(a, "final")
    assert "FILE_REPORT" not in (a["next_best_actions"]["what_changed"] or "")
    # R8 re-applied onto the analyst final branch.
    assert any(act == "ESCALATE_TO_ANALYST" and "R8" in r
               for act, r in final_reasons.items())


def test_evidence_request_always_opens_case_no_generate_report(tmp_path):
    """HHG-001 shape: evidence requested => CREATE_CASE; no GENERATE_REPORT."""
    b = _run(tmp_path, "HHG-B", trigger_type="risk_score",
             flagged_txn_id="9002", card_id="C77777-K1", customer_id="C77777",
             trigger_text="scored 0.6", risk_score=0.6)
    init_reasons = _reasons(b, "initial")
    assert any(act == "VERIFY_WITH_CUSTOMER" and "R1" in r
               for act, r in init_reasons.items())
    assert any(act == "CREATE_CASE" and "3a" in r
               for act, r in init_reasons.items()), \
        "evidence requested must open a case (3a)"
    assert "GENERATE_REPORT" not in _actions(b, "initial") + _actions(b, "final"), \
        "GENERATE_REPORT must not appear alongside evidence requests"
    final = _actions(b, "final")
    assert "MONITOR_CARD" in final
    assert "DECLINE_TRANSACTION" in final
    assert "CREATE_CASE" in final


def test_deny_branch_reapplies_r8_and_reconciles_file_report(tmp_path):
    """HHG-013 shape: deny + uncertain + exposure>$500 => R8; no stale claims."""
    c = _run(tmp_path, "HHG-C", trigger_type="risk_score",
             flagged_txn_id="9003", card_id="C88888-K1", customer_id="C88888",
             trigger_text="scored 1.0", risk_score=1.0)
    assert c["case"]["verdict"] == "uncertain"
    final_reasons = _reasons(c, "final")
    assert "BLOCK_CARD" in final_reasons
    assert "CREATE_CASE" in final_reasons
    # R8: uncertain + exposure > $500 must escalate on the rebuilt final list.
    assert any(act == "ESCALATE_TO_ANALYST" and "R8" in r
               for act, r in final_reasons.items()), \
        "R8 escalation missing from deny final branch"
    # FILE_REPORT reconciliation: uncertain => no SAR => removed from final.
    assert c["sar"]["file"] is False
    assert "FILE_REPORT" not in final_reasons
    what_changed = c["next_best_actions"]["what_changed"] or ""
    assert "FILE_REPORT" not in what_changed, \
        "what_changed must not claim FILE_REPORT after reconciliation removed it"


def test_sar_not_filed_reason_is_dynamic_and_factual(tmp_path):
    """HHG-013 shape: the SAR reason must state the real exposure, not boilerplate."""
    c = _run(tmp_path, "HHG-C2", trigger_type="risk_score",
             flagged_txn_id="9003", card_id="C88888-K1", customer_id="C88888",
             trigger_text="scored 1.0", risk_score=1.0)
    assert c["sar"]["file"] is False
    reason = c["sar"]["reason"]
    assert "$1,090.00 exceeds $1,000" in reason, \
        f"SAR reason not dynamic/factual: {reason!r}"
    assert "card_not_present_fraud" in reason
    assert "no shared origin" in reason
