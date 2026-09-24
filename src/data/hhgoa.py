"""Official HHGOA_IEEE dataset access layer.

Data directory resolution (first hit wins):
  1. $HHGOA_DATA_DIR
  2. data/HHGOA_IEEE_real/HHGOA_IEEE  (downloaded official dataset)
  3. data/HHGOA_IEEE                   (synthetic stub — OFFLINE FALLBACK ONLY)

The fallback is clearly labeled via ``is_fallback`` and ``describe()``: its
IDs are NOT the official dataset IDs, so answers produced from it are
pipeline-validation artifacts, not submittable cases. Never download the
original public IEEE-CIS/Kaggle files to recover outcomes (disqualification).

transactions.csv (590,742 rows x ~397 cols) is streamed ONCE into compact
in-memory indexes:
  - txn_by_id:      TransactionID -> Txn (compact tuple-backed dataclass)
  - txns_by_card:   (customer_id, card1) -> [TransactionID ...] sorted by ts
  - device_to_cards: device profile -> {(customer_id, card1)}
identity.csv (144,432 rows) and closed_cases_history.csv (5,565 rows) load
fully; both are small.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_CANDIDATES = (
    Path(os.environ["HHGOA_DATA_DIR"])
    if os.environ.get("HHGOA_DATA_DIR")
    else None,
    REPO_ROOT / "data" / "HHGOA_IEEE_real" / "HHGOA_IEEE",
    REPO_ROOT / "data" / "HHGOA_IEEE",
)

# Dataset epoch: TransactionDT is seconds from the dataset start; the added
# `ts` column runs 2016-07-02 .. 2016-12-31. Fallback derives ts from this.
_FALLBACK_EPOCH = datetime(2016, 7, 2, tzinfo=timezone.utc)

_M_COLUMNS = [f"M{i}" for i in range(1, 10)]


@dataclass
class Txn:
    txn_id: str
    customer_id: str
    card1: str
    ts: datetime
    dt: int
    amt: float
    product: str
    channel: str  # in_person | online
    addr1: str
    addr2: str
    p_email: str
    r_email: str
    risk: Optional[float]
    m_flags: Tuple[str, ...] = ()


@dataclass
class Identity:
    txn_id: str
    id_15: str = ""  # device New / Found
    id_23: str = ""  # proxy: transparent / anonymous / hidden
    id_30: str = ""  # OS
    id_31: str = ""  # browser
    id_33: str = ""  # screen
    id_34: str = ""  # match status
    device_type: str = ""
    device_info: str = ""

    def profile(self) -> str:
        """Device profile = DeviceInfo + OS + browser + screen (README)."""
        return " | ".join(
            p for p in (self.device_info, self.id_30, self.id_31, self.id_33) if p
        )


@dataclass
class ClosedCase:
    case_id: str
    customer_id: str
    card_id: str
    opened_at: str
    closed_at: str
    outcome: str  # confirmed_fraud | cleared
    pattern: str
    first_fraud_txn_id: str
    txn_ids: List[str] = field(default_factory=list)
    n_txns: int = 0
    exposure_usd: float = 0.0
    connected_card_ids: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    report_filed: str = ""
    analyst_notes: str = ""


class DataError(RuntimeError):
    """Raised when the dataset cannot be loaded (never silent)."""


class HHGOAStore:
    """Indexed access to the HHGOA_IEEE dataset (real or fallback)."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.is_fallback = self.data_dir.name != "HHGOA_IEEE" or (
            self.data_dir.parent.name != "HHGOA_IEEE_real"
        )
        self.txn_by_id: Dict[str, Txn] = {}
        self.txns_by_card: Dict[Tuple[str, str], List[str]] = {}
        self.device_to_cards: Dict[str, Set[Tuple[str, str]]] = {}
        self.identities: Dict[str, Identity] = {}
        self.closed_cases: List[ClosedCase] = []
        self.card_suffix: Dict[Tuple[str, str], str] = {}  # (customer_id, card1) -> K<n>
        self.card_home_region: Dict[Tuple[str, str], str] = {}  # (customer_id, card1) -> modal addr1
        self._txn_header: List[str] = []
        self._full_row_cache: Dict[str, Dict[str, str]] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # discovery / loading
    # ------------------------------------------------------------------
    @classmethod
    def discover(cls) -> "HHGOAStore":
        for cand in DATA_CANDIDATES:
            if cand is None:
                continue
            if (cand / "transactions.csv").exists():
                return cls(cand)
        raise DataError(
            "no dataset found; checked: "
            + ", ".join(str(c) for c in DATA_CANDIDATES if c)
        )

    def describe(self) -> Dict[str, object]:
        return {
            "data_dir": str(self.data_dir),
            "is_fallback": self.is_fallback,
            "n_transactions": len(self.txn_by_id),
            "n_identities": len(self.identities),
            "n_closed_cases": len(self.closed_cases),
        }

    def load(self) -> "HHGOAStore":
        if self._loaded:
            return self
        tx_path = self.data_dir / "transactions.csv"
        id_path = self.data_dir / "identity.csv"
        cc_path = self.data_dir / "closed_cases_history.csv"
        for p in (tx_path,):
            if not p.exists():
                raise DataError(f"missing required file: {p}")
        self._load_transactions(tx_path)
        if id_path.exists():
            self._load_identities(id_path)
        if cc_path.exists():
            self._load_closed_cases(cc_path)
        self._build_card_suffix_map()
        self._build_card_home_regions()
        self._loaded = True
        return self

    def _build_card_home_regions(self) -> None:
        """Most-common billing region (addr1) per (customer_id, card1).

        Used by the investigator's region-cluster signal: only cards whose
        home region differs from a flagged region count as convergence.
        Single pass over the card index; done once at load.
        """
        from collections import Counter

        for key, tids in self.txns_by_card.items():
            regs = Counter(
                t.addr1
                for tid in tids
                if (t := self.txn_by_id.get(tid)) and t.addr1
            )
            self.card_home_region[key] = regs.most_common(1)[0][0] if regs else ""

    # ------------------------------------------------------------------
    # transactions
    # ------------------------------------------------------------------
    def _row_get(self, row: Dict[str, str], *names: str, default: str = "") -> str:
        for n in names:
            v = row.get(n)
            if v not in (None, ""):
                return v
        return default

    def _load_transactions(self, path: Path) -> None:
        real = not self.is_fallback
        with open(path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            self._txn_header = reader.fieldnames or []
            for row in reader:
                txn_id = (row.get("TransactionID") or "").strip()
                if not txn_id:
                    continue
                try:
                    dt = int(float(row.get("TransactionDT") or 0))
                except ValueError:
                    dt = 0
                try:
                    amt = float(row.get("TransactionAmt") or 0.0)
                except ValueError:
                    amt = 0.0
                product = (row.get("ProductCD") or "").strip()
                card1 = (row.get("card1") or "").strip()
                if real:
                    customer_id = (row.get("customer_id") or "").strip()
                    ts_raw = (row.get("ts") or "").strip()
                    try:
                        ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S").replace(
                            tzinfo=timezone.utc
                        )
                    except ValueError:
                        ts = _FALLBACK_EPOCH + timedelta(seconds=dt)
                    channel = (row.get("channel") or "").strip() or (
                        "in_person" if product == "W" else "online"
                    )
                    risk_raw = (row.get("risk_score") or "").strip()
                    risk = float(risk_raw) if risk_raw else None
                else:  # synthetic stub fallback: derive the added columns
                    customer_id = f"C{card1.zfill(5)}" if card1 else ""
                    ts = _FALLBACK_EPOCH + timedelta(seconds=dt)
                    channel = "in_person" if product == "W" else "online"
                    risk = None
                txn = Txn(
                    txn_id=txn_id,
                    customer_id=customer_id,
                    card1=card1,
                    ts=ts,
                    dt=dt,
                    amt=amt,
                    product=product,
                    channel=channel,
                    addr1=(row.get("addr1") or "").strip(),
                    addr2=(row.get("addr2") or "").strip(),
                    p_email=(row.get("P_emaildomain") or "").strip(),
                    r_email=(row.get("R_emaildomain") or "").strip(),
                    risk=risk,
                    m_flags=tuple((row.get(m) or "").strip() for m in _M_COLUMNS),
                )
                self.txn_by_id[txn_id] = txn
                if customer_id and card1:
                    self.txns_by_card.setdefault((customer_id, card1), []).append(
                        txn_id
                    )
        for key in self.txns_by_card:
            self.txns_by_card[key].sort(key=lambda tid: self.txn_by_id[tid].ts)

    def full_row(self, txn_id: str) -> Optional[Dict[str, str]]:
        """Full CSV row (all V/C/D/id columns) for one transaction.

        Implemented as a cached streaming re-scan: correct on any CSV,
        including ones with quoted multiline fields. Only used for rare
        deep-evidence reads; the hot path uses the compact Txn index.
        """
        txn_id = str(txn_id).strip()
        if txn_id in self._full_row_cache:
            return self._full_row_cache[txn_id]
        if txn_id not in self.txn_by_id:
            return None
        path = self.data_dir / "transactions.csv"
        with open(path, "r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if (row.get("TransactionID") or "").strip() == txn_id:
                    self._full_row_cache[txn_id] = row
                    return row
        return None

    # ------------------------------------------------------------------
    # identity
    # ------------------------------------------------------------------
    def _load_identities(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                txn_id = (row.get("TransactionID") or "").strip()
                if not txn_id:
                    continue
                ident = Identity(
                    txn_id=txn_id,
                    id_15=(row.get("id_15") or "").strip(),
                    id_23=(row.get("id_23") or "").strip(),
                    id_30=(row.get("id_30") or "").strip(),
                    id_31=(row.get("id_31") or "").strip(),
                    id_33=(row.get("id_33") or "").strip(),
                    id_34=(row.get("id_34") or "").strip(),
                    device_type=(row.get("DeviceType") or "").strip(),
                    device_info=(row.get("DeviceInfo") or "").strip(),
                )
                self.identities[txn_id] = ident
                txn = self.txn_by_id.get(txn_id)
                if txn and txn.customer_id and txn.card1:
                    profile = ident.profile()
                    if profile:
                        self.device_to_cards.setdefault(profile, set()).add(
                            (txn.customer_id, txn.card1)
                        )

    # ------------------------------------------------------------------
    # closed cases
    # ------------------------------------------------------------------
    def _load_closed_cases(self, path: Path) -> None:
        def _split(value: str) -> List[str]:
            return [p.strip() for p in (value or "").split("|") if p.strip()]

        with open(path, "r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                case_id = (row.get("case_id") or "").strip()
                if not case_id:
                    continue
                try:
                    exposure = float(row.get("exposure_usd") or 0.0)
                except ValueError:
                    exposure = 0.0
                try:
                    n_txns = int(float(row.get("n_txns") or 0))
                except ValueError:
                    n_txns = 0
                self.closed_cases.append(
                    ClosedCase(
                        case_id=case_id,
                        customer_id=(row.get("customer_id") or "").strip(),
                        card_id=(row.get("card_id") or "").strip(),
                        opened_at=(row.get("opened_at") or "").strip(),
                        closed_at=(row.get("closed_at") or "").strip(),
                        outcome=(row.get("outcome") or "").strip(),
                        pattern=(row.get("pattern") or "").strip(),
                        first_fraud_txn_id=(
                            row.get("first_fraud_txn_id") or ""
                        ).strip(),
                        txn_ids=_split(row.get("txn_ids", "")),
                        n_txns=n_txns,
                        exposure_usd=exposure,
                        connected_card_ids=_split(
                            row.get("connected_card_ids", "")
                        ),
                        actions_taken=_split(row.get("actions_taken", "")),
                        report_filed=(row.get("report_filed") or "").strip(),
                        analyst_notes=(row.get("analyst_notes") or "").strip(),
                    )
                )

    def _build_card_suffix_map(self) -> None:
        """Derive (customer_id, card1) -> 'K<n>' from closed cases whose
        txn_ids join back to transactions (empirical, no guessing)."""
        for cc in self.closed_cases:
            if not cc.card_id or "-K" not in cc.card_id:
                continue
            suffix = cc.card_id.rsplit("-K", 1)[-1]
            if not suffix.isdigit():
                continue
            for tid in cc.txn_ids:
                txn = self.txn_by_id.get(tid)
                if txn and txn.customer_id and txn.card1:
                    key = (txn.customer_id, txn.card1)
                    self.card_suffix.setdefault(key, f"K{suffix}")

    # ------------------------------------------------------------------
    # query API (used by the investigator)
    # ------------------------------------------------------------------
    def get_txn(self, txn_id: str) -> Optional[Txn]:
        return self.txn_by_id.get(str(txn_id).strip())

    def card_id_for(self, customer_id: str, card1: str) -> str:
        suffix = self.card_suffix.get((customer_id, card1))
        if suffix:
            return f"{customer_id}-{suffix}"
        # deterministic fallback: enumerate distinct card1 values per customer
        card1s = sorted(
            {c1 for (cust, c1) in self.txns_by_card if cust == customer_id}
        )
        if card1 in card1s:
            return f"{customer_id}-K{card1s.index(card1) + 1}"
        return f"{customer_id}-K?"

    def card1s_for_card_id(self, card_id: str) -> List[Tuple[str, str]]:
        """Resolve a case-pack card_id like C12382-K1 to (customer_id, card1) keys."""
        card_id = card_id.strip()
        if "-K" not in card_id:
            return []
        customer_id, _, suffix = card_id.rpartition("-K")
        want = f"K{suffix}"
        out = [
            (cust, c1)
            for (cust, c1), sfx in self.card_suffix.items()
            if cust == customer_id and sfx == want
        ]
        if out:
            return out
        # fallback: K<n> -> nth distinct card1 for the customer
        card1s = sorted({c1 for (cust, c1) in self.txns_by_card if cust == customer_id})
        try:
            idx = int(suffix) - 1
            if 0 <= idx < len(card1s):
                return [(customer_id, card1s[idx])]
        except ValueError:
            pass
        return []

    def customer_cards(self, customer_id: str) -> List[str]:
        keys = sorted({c1 for (cust, c1) in self.txns_by_card if cust == customer_id})
        return [self.card_id_for(customer_id, c1) for c1 in keys]

    def card_txns(
        self, customer_id: str, card1: str, limit: Optional[int] = None
    ) -> List[Txn]:
        tids = self.txns_by_card.get((customer_id, card1), [])
        if limit is not None:
            tids = tids[-limit:]
        return [self.txn_by_id[t] for t in tids if t in self.txn_by_id]

    def txns_around(
        self, txn: Txn, before_days: int = 60, after_days: int = 2
    ) -> List[Txn]:
        lo = txn.ts - timedelta(days=before_days)
        hi = txn.ts + timedelta(days=after_days)
        return [
            t
            for t in self.card_txns(txn.customer_id, txn.card1)
            if lo <= t.ts <= hi
        ]

    def identity_for(self, txn_id: str) -> Optional[Identity]:
        return self.identities.get(str(txn_id).strip())

    def device_profile_for(self, txn_id: str) -> str:
        ident = self.identity_for(txn_id)
        return ident.profile() if ident else ""

    def cards_sharing_device(self, profile: str) -> List[str]:
        keys = self.device_to_cards.get(profile, set())
        return sorted(
            {self.card_id_for(cust, c1) for (cust, c1) in keys}
        )

    def iter_identity_rows(self) -> Iterator[Identity]:
        return iter(self.identities.values())

    def find_similar_cases(
        self,
        pattern: Optional[str] = None,
        customer_id: Optional[str] = None,
        card_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[ClosedCase]:
        scored: List[Tuple[int, ClosedCase]] = []
        for cc in self.closed_cases:
            score = 0
            if pattern and cc.pattern == pattern:
                score += 3
            if customer_id and cc.customer_id == customer_id:
                score += 4
            if card_id and cc.card_id == card_id:
                score += 4
            if score:
                scored.append((score, cc))
        scored.sort(key=lambda s: (-s[0], s[1].case_id))
        return [cc for _, cc in scored[:limit]]
