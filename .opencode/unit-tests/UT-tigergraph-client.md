# Unit Test Record: src/tigergraph/client.py

## Target File
`src/tigergraph/client.py`

## Test File (DELETED)
`src/tigergraph/__tests__/test_client_isolated.py` (renamed from
`client.isolated.test.py` — dotted name breaks pytest module collection)

## Test Code (Preserved)
```python
"""ISOLATED Unit Test for src/tigergraph/client.py (WILL BE DELETED AFTER PASS)."""
from __future__ import annotations

import os

# Force mock mode: no live TigerGraph endpoint.
for var in ("TIGERGRAPH_HOST", "TIGERGRAPH_USER", "TIGERGRAPH_PASS",
            "TIGERGRAPH_GRAPH", "TG_HOST"):
    os.environ.pop(var, None)

from src.tigergraph.client import TigerGraphClient


def _client() -> TigerGraphClient:
    return TigerGraphClient()


def test_mock_mode_by_default():
    assert _client().mode == "mock"


def test_get_transaction_context_returns_evidence_ids():
    out = _client().get_transaction_context(1001)
    assert isinstance(out["evidence_ids"], list) and len(out["evidence_ids"]) >= 1
    assert "1001" in {str(e) for e in out["evidence_ids"]}
    assert "isFraud" not in out["transaction"]  # no label leakage


def test_card_ring():
    out = _client().card_ring("411111")
    assert out["evidence_ids"], "card_ring must return evidence_ids"
    assert out["node_count"] == len(out["evidence_ids"]) == 12


def test_device_cluster():
    out = _client().device_cluster("emu-spoof-X1")
    assert out["evidence_ids"], "device_cluster must return evidence_ids"


def test_mule_fanout_round_amount_flag():
    out = _client().mule_fanout("522222")
    assert out["evidence_ids"], "mule_fanout must return evidence_ids"
    assert "round_amount" in out  # round-amount dispersal flag


def test_takeover_signals():
    out = _client().takeover_signals([1001, 1002])
    assert out["evidence_ids"], "takeover_signals must return evidence_ids"
    assert "device_change" in out or "signals" in out


def test_synthetic_signals():
    out = _client().synthetic_signals([1001])
    assert out["evidence_ids"], "synthetic_signals must return evidence_ids"


def test_evidence_subgraph_bounded():
    out = _client().evidence_subgraph(
        {"transaction_ids": [1001, 1002], "cards": [], "devices": [],
         "emails": []}, hops=2)
    assert out["evidence_ids"], "evidence_subgraph must return evidence_ids"


def test_unknown_txn_raises_structured_error():
    try:
        _client().get_transaction_context(999999)
    except ValueError as exc:
        assert "999999" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown TransactionID")
```

## Test Result
- Status: pass (9 passed in 0.13s)
- Timestamp: 2026-09-19
- Notes: red phase confirmed first (AttributeError on missing functions);
  green after implementing the 7-function surface. Test file deleted.
