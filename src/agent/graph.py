"""Agent graph entry point.

The evidence-driven investigation in :mod:`src.agent.investigate` (via
:mod:`src.agent.orchestrator`) is the primary path. When ``langgraph`` is
installed, callers may wrap :func:`investigate_case` in their own StateGraph;
this module keeps the historic ``investigate_case`` entry point stable for
the UI and other callers. No ground-truth labels leak through this module.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.agent import orchestrator
from src.data.hhgoa import HHGOAStore
from src.tigergraph.client import TigerGraphClient

try:  # optional dependency; absence only disables LangGraph wrapping
    from langgraph.graph import StateGraph  # type: ignore

    _HAS_LANGGRAPH = True
except Exception:
    StateGraph = None  # type: ignore
    _HAS_LANGGRAPH = False


def investigate_case(
    case_input: Dict[str, Any],
    store: Optional[HHGOAStore] = None,
    client: Optional[TigerGraphClient] = None,
) -> Dict[str, Any]:
    """Run a full investigation; delegates to the orchestrator."""
    return orchestrator.investigate_case(case_input, store=store, client=client)
