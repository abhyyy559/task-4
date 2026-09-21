"""Case + conversation memory (JSON-backed, offline)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MEMORY_PATH = ROOT / "cases" / "outputs" / "_memory.json"


class CaseMemory:
    def __init__(self, path: Path = MEMORY_PATH) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except ValueError:
                self._data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=1), encoding="utf-8")

    def remember(self, case_id: str, record: dict[str, Any]) -> None:
        self._data[str(case_id)] = record
        self.save()

    def recall(self, case_id: str) -> dict[str, Any]:
        return self._data.get(str(case_id), {})

    def history(self) -> dict[str, Any]:
        return dict(self._data)


def _entities_of(record: dict[str, Any]) -> set[str]:
    ents = record.get("entities_flagged") or {}
    out: set[str] = set()
    for key in ("cards", "devices", "emails", "accounts"):
        for v in ents.get(key, []) or []:
            out.add(f"{key}:{v}")
    for eid in record.get("evidence_ids", []) or []:
        out.add(f"ev:{eid}")
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def save_case(case_data: dict[str, Any]) -> dict[str, Any]:
    """Persist a case result; returns stored record."""
    case_id = str(case_data.get("case_id", "unknown"))
    mem = CaseMemory()
    mem.remember(case_id, dict(case_data))
    return {"case_id": case_id, "status": "saved", "path": str(mem.path)}


def find_similar_cases(features: dict[str, Any], top_k: int = 5) -> list[dict[str, Any]]:
    """Jaccard on entities_flagged sets + fraud_pattern bonus."""
    mem = CaseMemory()
    history = mem.history()
    if not history:
        return []
    target_ents = _entities_of(features)
    target_pat = str(features.get("fraud_pattern") or features.get("pattern") or "")
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for cid, rec in history.items():
        score = _jaccard(target_ents, _entities_of(rec))
        pat = str(rec.get("fraud_pattern") or rec.get("pattern") or "")
        if target_pat and pat and target_pat == pat:
            score += 0.3
        scored.append((round(score, 4), cid, rec))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [
        {"case_id": cid, "score": score,
         "fraud_pattern": rec.get("fraud_pattern") or rec.get("pattern"),
         "verdict": rec.get("verdict")}
        for score, cid, rec in scored[:top_k] if score > 0
    ]
