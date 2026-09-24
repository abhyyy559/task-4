"""Benchmark runner: cases/inputs/HHG-*.json -> cases/HHG-*.json.

Each answer validates against the official answer format
(src.agent.state.validate_output). The 20 answer files go in cases/
named <case_id>.json, per the official README.

Usage:
    python -m src.agent.runner --all
    python -m src.agent.runner --case HHG-001
    HHGOA_DATA_DIR=/path/to/data python -m src.agent.runner --all
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from src.agent.investigate import investigate
from src.agent.state import REQUIRED_OUTPUT_FIELDS, validate_output
from src.data.hhgoa import DataError, HHGOAStore
from src.tigergraph.client import TigerGraphClient

OUTPUT_SCHEMA: List[str] = list(REQUIRED_OUTPUT_FIELDS)

ROOT = Path(__file__).resolve().parents[2]
CASES_IN = ROOT / "cases" / "inputs"
CASES_OUT = ROOT / "cases"  # official: twenty files in a folder called cases/
# Backward-compat aliases.
INPUTS = CASES_IN
OUTPUTS = CASES_OUT


def list_cases() -> List[Path]:
    return sorted(CASES_IN.glob("HHG-*.json"))


def load_case_input(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "case_id" not in data:
        raise ValueError(f"invalid case input: {path}")
    return data


def run_case(
    case_input: Dict[str, Any], store: HHGOAStore, client: Any
) -> Dict[str, Any]:
    answer = investigate(case_input, store, client)
    errors = validate_output(answer)
    if errors:
        raise ValueError(
            f"answer for {answer.get('case_id')} failed validation: {errors}"
        )
    return answer


def write_answer(answer: Dict[str, Any]) -> Path:
    CASES_OUT.mkdir(parents=True, exist_ok=True)
    path = CASES_OUT / f"{answer['case_id']}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(answer, fh, indent=1)
    return path


def run_all(store: HHGOAStore, client: Any) -> Dict[str, Any]:
    results: Dict[str, Any] = {"ok": [], "failed": []}
    for path in list_cases():
        case_id = path.stem
        try:
            answer = run_case(load_case_input(path), store, client)
            write_answer(answer)
            results["ok"].append(case_id)
        except Exception as exc:  # never fail silently: record and continue
            results["failed"].append({"case_id": case_id, "error": str(exc)})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HHG fraud investigations")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--case", help="single case id, e.g. HHG-001")
    args = parser.parse_args()

    try:
        store = HHGOAStore.discover().load()
    except DataError as exc:
        print(f"data error: {exc}")
        return 2
    print(f"dataset: {store.describe()}")
    try:
        client = TigerGraphClient()
    except RuntimeError as exc:
        # Partial live config (e.g. TIGERGRAPH_HOST without credentials)
        # must not kill the run: fall back to offline mock mode.
        print(f"live client unavailable ({exc}); using offline mock mode")
        os.environ.pop("TIGERGRAPH_HOST", None)
        client = TigerGraphClient()

    if args.all:
        results = run_all(store, client)
        print(f"ok: {len(results['ok'])}, failed: {len(results['failed'])}")
        for item in results["failed"]:
            print(f"  FAILED {item['case_id']}: {item['error']}")
        return 1 if results["failed"] else 0

    path = CASES_IN / f"{args.case}.json"
    if not path.exists():
        print(f"unknown case: {args.case}")
        return 2
    answer = run_case(load_case_input(path), store, client)
    out = write_answer(answer)
    case = answer["case"]
    print(f"wrote {out}")
    print(
        f"verdict={case['verdict']} status={case['status']} "
        f"pattern={case['pattern']} prob={case['fraud_probability']} "
        f"exposure=${case['exposure_usd']:.2f} sar={answer['sar']['file']} "
        f"tool_calls={answer['tool_calls']} latency={answer['latency_s']}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
