"""Orchestrator: plan -> investigate -> answer (offline primary path).

Thin orchestration layer over :mod:`src.agent.investigate`. It resolves the
dataset store and the graph client, runs the evidence-driven investigation,
and returns the official answer record. No ground-truth labels or patterns
are read from the case input at any point: pattern and verdict are inferred
from graph evidence only.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from src.agent.investigate import investigate
from src.data.hhgoa import HHGOAStore
from src.tigergraph.client import TigerGraphClient


def _default_client() -> TigerGraphClient:
    """Build a graph client, falling back to offline mock on partial config."""
    try:
        return TigerGraphClient()
    except RuntimeError:
        os.environ.pop("TIGERGRAPH_HOST", None)
        return TigerGraphClient()


def investigate_case(
    case_input: Dict[str, Any],
    store: Optional[HHGOAStore] = None,
    client: Optional[TigerGraphClient] = None,
) -> Dict[str, Any]:
    """Run a full investigation for one case-pack input.

    Returns the official answer record (validates against
    src.agent.state.validate_output). Raises on data errors; never fails
    silently.
    """
    own_store = store if store is not None else HHGOAStore.discover().load()
    own_client = client if client is not None else _default_client()
    return investigate(dict(case_input), own_store, own_client)


def run_single_case(case_id: str) -> Dict[str, Any]:
    """Load cases/inputs/<case_id>.json and investigate it."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "cases" / "inputs" / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"case input missing: {path}")
    case_input = json.loads(path.read_text(encoding="utf-8"))
    return investigate_case(case_input)


# Back-compat alias.
run_case = run_single_case
