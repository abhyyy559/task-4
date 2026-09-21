"""TigerGraph client with local CSV mock fallback (offline-first).

Live path: used only when TIGERGRAPH_HOST is set (plus TIGERGRAPH_USER /
TIGERGRAPH_PASS / TIGERGRAPH_GRAPH). The ``requests`` import is lazy so this
module always imports cleanly offline. Default path is the local mock, which
loads ``data/HHGOA_IEEE/*.csv`` with the stdlib ``csv`` module only.

Every public method returns a dict containing an ``evidence_ids`` list
(TransactionID strings and/or CARD:/DEVICE:/EMAIL: node IDs). Never raises
silently: unknown IDs raise ValueError; a missing stub raises FileNotFoundError.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "HHGOA_IEEE"
TXN_CSV = DATA_DIR / "transactions.csv"
ID_CSV = DATA_DIR / "identity.csv"

_M_COLS = [f"M{i}" for i in range(1, 10)]


def _fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class TigerGraphClient:
    """Unified client: live Savanna endpoint when configured, mock otherwise."""

    def __init__(self, host: Optional[str] = None, graph: str = "fraud_graph",
                 data_dir: Optional[Path] = None) -> None:
        self.graph = os.environ.get("TIGERGRAPH_GRAPH", graph)
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.mode = "mock"
        self.host = host or os.environ.get("TIGERGRAPH_HOST", "")
        if self.host:
            self._init_live()
        else:
            self._txns: list[dict[str, Any]] = []
            self._identity: dict[str, dict[str, Any]] = {}
            self._load_stub()

    # -- live path --------------------------------------------------------
    def _init_live(self) -> None:
        try:
            import requests  # noqa: F401  (lazy: offline imports stay clean)
        except ImportError as exc:
            raise RuntimeError(
                "TIGERGRAPH_HOST is set but 'requests' is not installed; "
                "unset TIGERGRAPH_HOST for offline mock mode"
            ) from exc
        user = os.environ.get("TIGERGRAPH_USER", "")
        password = os.environ.get("TIGERGRAPH_PASS", "")
        if not user or not password:
            raise RuntimeError(
                "TIGERGRAPH_HOST is set but TIGERGRAPH_USER/TIGERGRAPH_PASS "
                "are missing"
            )
        self.mode = "live"
        self._txns = []
        self._identity = {}

    # -- stub loading -----------------------------------------------------
    def _load_stub(self) -> None:
        txn_csv = self.data_dir / "transactions.csv"
        id_csv = self.data_dir / "identity.csv"
        if not txn_csv.exists():
            raise FileNotFoundError(f"transaction stub missing: {txn_csv}")
        with open(txn_csv, newline="", encoding="utf-8") as fh:
            self._txns = list(csv.DictReader(fh))
        if id_csv.exists():
            with open(id_csv, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    self._identity[str(row.get("TransactionID"))] = row

    # -- helpers ----------------------------------------------------------
    def _require_mock(self) -> None:
        if self.mode != "mock":
            raise RuntimeError("mock query semantics require mock mode")

    def _rows_for(self, ids: list[Any]) -> list[dict[str, Any]]:
        wanted = [str(i) for i in ids]
        by_id = {str(r.get("TransactionID")): r for r in self._txns}
        missing = [i for i in wanted if i not in by_id]
        if missing:
            raise ValueError(f"unknown TransactionIDs: {sorted(missing)}")
        return [by_id[i] for i in wanted]

    def _cards_for(self, txn_ids: list[Any]) -> list[str]:
        return sorted({str(r.get("card1")) for r in self._rows_for(txn_ids)})

    @staticmethod
    def _result(query: str, summary: str,
                evidence_ids: list[str], **extra: Any) -> dict[str, Any]:
        result: dict[str, Any] = {
            "query": query,
            "summary": summary,
            "node_count": len(evidence_ids),
            "evidence_ids": evidence_ids,
        }
        result.update(extra)
        return result

    # -- required surface -------------------------------------------------
    def get_transaction_context(self, txn_id: Any) -> dict[str, Any]:
        """Full row for one TransactionID (WITHOUT isFraud: no label leakage)."""
        self._require_mock()
        row = self._rows_for([txn_id])[0]
        txn = {k: v for k, v in row.items() if k != "isFraud"}
        txn["identity"] = self._identity.get(str(txn_id), {})
        return self._result(
            "get_transaction_context",
            f"context for TransactionID {txn_id}",
            [str(txn_id)],
            transaction=txn,
        )

    def card_ring(self, card1: Any, start_dt: float = 0,
                  end_dt: float = float("inf")) -> dict[str, Any]:
        """Transactions sharing one card (mock of q_card_ring)."""
        self._require_mock()
        hits = [r["TransactionID"] for r in self._txns
                if str(r.get("card1")) == str(card1)
                and start_dt <= _fnum(r.get("TransactionDT")) <= end_dt]
        return self._result(
            "q_card_ring",
            f"{len(hits)} txns share card {card1} in window",
            [str(t) for t in hits],
        )

    def device_cluster(self, device_info: str) -> dict[str, Any]:
        """Cards + transactions funnelled through one device (q_device_cluster)."""
        self._require_mock()
        txns = [r for r in self._txns if (r.get("DeviceInfo") or "") == device_info]
        cards = sorted({str(r.get("card1")) for r in txns})
        evidence = [str(r["TransactionID"]) for r in txns] + [f"CARD:{c}" for c in cards]
        return self._result(
            "q_device_cluster",
            f"{len(cards)} cards via device {device_info}",
            evidence,
            cards=cards,
            transaction_ids=[str(r["TransactionID"]) for r in txns],
        )

    def mule_fanout(self, card1: Any) -> dict[str, Any]:
        """Recipients downstream of one hub card, ordered by dt (q_mule_fanout)."""
        self._require_mock()
        txns = sorted(
            (r for r in self._txns if str(r.get("card1")) == str(card1)),
            key=lambda r: _fnum(r.get("TransactionDT")),
        )
        amounts = [_fnum(r.get("TransactionAmt")) for r in txns]
        round_amount = bool(amounts) and all(a == round(a) for a in amounts)
        emails = sorted({str(r.get("R_emaildomain")) for r in txns if r.get("R_emaildomain")})
        evidence = [str(r["TransactionID"]) for r in txns] + [f"EMAIL:{e}" for e in emails]
        return self._result(
            "q_mule_fanout",
            f"hub card {card1} fans out to {len(emails)} recipients",
            evidence,
            transaction_ids=[str(r["TransactionID"]) for r in txns],
            recipients=emails,
            round_amount=round_amount,
        )

    def takeover_signals(self, txn_ids: list[Any]) -> dict[str, Any]:
        """Device/email/address change + amount spike over the cards in txn_ids."""
        self._require_mock()
        rows = self._rows_for(txn_ids)
        signals: dict[str, Any] = {}
        evidence = [str(r.get("TransactionID")) for r in rows]
        for card in sorted({str(r.get("card1")) for r in rows}):
            card_rows = sorted(
                (r for r in self._txns if str(r.get("card1")) == str(card)),
                key=lambda r: _fnum(r.get("TransactionDT")),
            )
            devices = [r.get("DeviceInfo") for r in card_rows]
            addrs = [(r.get("addr1"), r.get("addr2")) for r in card_rows]
            emails = [r.get("R_emaildomain") for r in card_rows]
            amounts = [_fnum(r.get("TransactionAmt")) for r in card_rows]
            dts = [_fnum(r.get("TransactionDT")) for r in card_rows]
            spike = (max(amounts) / min(amounts)) if amounts and min(amounts) > 0 else 0.0
            signals[str(card)] = {
                "device_change": len(set(devices)) > 1,
                "address_change": len(set(addrs)) > 1,
                "email_change": len(set(emails)) > 1,
                "amount_spike_ratio": round(spike, 3),
                "txn_count": len(card_rows),
                "dt_span_secs": (max(dts) - min(dts)) if len(dts) > 1 else 0.0,
            }
        device_change = any(s["device_change"] for s in signals.values())
        return self._result(
            "q_takeover_anomaly",
            f"takeover scan over {len(rows)} txns: device_change={device_change}",
            evidence,
            signals=signals,
            device_change=device_change,
        )

    def synthetic_signals(self, txn_ids: list[Any]) -> dict[str, Any]:
        """Thin-file M-flag + identity mismatch signals (q_synthetic_identity)."""
        self._require_mock()
        rows = self._rows_for(txn_ids)
        mismatch = sum(1 for r in rows for m in [r.get(c) for c in _M_COLS] if m == "F")
        thin = any(_fnum(r.get("C1"), 99) <= 2 for r in rows)
        missing_id = sum(1 for r in rows
                         if not self._identity.get(str(r.get("TransactionID"))))
        new_device = sum(1 for r in rows if _fnum(r.get("D1"), 99) <= 2)
        signals = {
            "thin_file": thin,
            "mismatch_flags": mismatch,
            "missing_identity_rows": missing_id,
            "new_device_count": new_device,
        }
        return self._result(
            "q_synthetic_identity",
            f"synthetic scan: thin_file={thin}, mismatch_flags={mismatch}",
            [str(r.get("TransactionID")) for r in rows],
            signals=signals,
        )

    def evidence_subgraph(self, case_entities: dict[str, Any],
                          hops: int = 2) -> dict[str, Any]:
        """Bounded k-hop neighbourhood around case entities (q_evidence_subgraph)."""
        self._require_mock()
        if hops < 1:
            raise ValueError(f"hops must be >= 1, got {hops}")
        txn_ids = [str(i) for i in (case_entities.get("transaction_ids") or [])]
        seen: set[str] = set()
        for tid in txn_ids:
            rows = [r for r in self._txns if str(r.get("TransactionID")) == str(tid)]
            for r in rows:
                seen.add(f"TXN:{tid}")
                seen.add(f"CARD:{r.get('card1')}")
                if r.get("DeviceInfo"):
                    seen.add(f"DEVICE:{r.get('DeviceInfo')}")
                if r.get("P_emaildomain"):
                    seen.add(f"EMAIL:{r.get('P_emaildomain')}")
                if r.get("R_emaildomain"):
                    seen.add(f"EMAIL:{r.get('R_emaildomain')}")
        if hops >= 2:  # second hop: same-card / same-device sibling transactions
            cards = {s.split(":", 1)[1] for s in seen if s.startswith("CARD:")}
            devices = {s.split(":", 1)[1] for s in seen if s.startswith("DEVICE:")}
            for r in self._txns:
                if str(r.get("card1")) in cards or (r.get("DeviceInfo") or "") in devices:
                    seen.add(f"TXN:{r.get('TransactionID')}")
        for key, prefix in (("cards", "CARD"), ("devices", "DEVICE"), ("emails", "EMAIL")):
            for value in case_entities.get(key) or []:
                seen.add(f"{prefix}:{value}")
        return self._result(
            "q_evidence_subgraph",
            f"{len(seen)} nodes within {hops} hops of {len(txn_ids)} txns",
            sorted(seen),
        )

    # -- back-compat aliases mirroring queries.gsql names ------------------
    def get_transactions(self, ids: list[Any]) -> list[dict[str, Any]]:
        self._require_mock()
        return [self.get_transaction_context(i)["transaction"] for i in ids]

    def q_card_ring(self, card1: Any, **kw: Any) -> dict[str, Any]:
        return self.card_ring(card1, **kw)

    def q_device_cluster(self, device: str) -> dict[str, Any]:
        return self.device_cluster(device)

    def q_mule_fanout(self, hub_card: Any) -> dict[str, Any]:
        return self.mule_fanout(hub_card)

    def q_takeover(self, card1: Any) -> dict[str, Any]:
        rows = [r for r in self._txns if str(r.get("card1")) == str(card1)]
        return self.takeover_signals([r["TransactionID"] for r in rows])

    def q_synthetic(self, card1: Any) -> dict[str, Any]:
        rows = [r for r in self._txns if str(r.get("card1")) == str(card1)]
        return self.synthetic_signals([r["TransactionID"] for r in rows])

    def q_evidence_subgraph(self, transaction_ids: list[Any],
                            hops: int = 2) -> dict[str, Any]:
        return self.evidence_subgraph({"transaction_ids": list(transaction_ids)},
                                      hops=hops)
