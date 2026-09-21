"""LangGraph wiring with graceful fallback to the orchestrator.

When `langgraph` imports cleanly, investigations run as a StateGraph with
nodes plan -> investigate -> act -> report. Otherwise (offline default)
`investigate_case` delegates to src/agent/orchestrator.investigate.
"""
from __future__ import annotations

from typing import Any

from src.agent import orchestrator
from src.agent.state import InvestigationState

_HAS_LANGGRAPH = False
try:  # pragma: no cover - optional dependency
    from langgraph.graph import StateGraph  # type: ignore

    _HAS_LANGGRAPH = True
except Exception:
    StateGraph = None  # type: ignore


def _node_plan(state: InvestigationState) -> InvestigationState:
    return state


def _node_investigate(state: InvestigationState) -> InvestigationState:
    case = {"case_id": state.get("case_id"), "pattern": state.get("pattern_hint"),
            "transaction_ids": state.get("transaction_ids", []),
            "subject": state.get("subject", {})}
    result = orchestrator.investigate(case)
    state.update(result)
    return state


def _node_act(state: InvestigationState) -> InvestigationState:
    return state  # actions already executed inside orchestrator.investigate


def _node_report(state: InvestigationState) -> InvestigationState:
    return state


def build_graph() -> Any:
    """Build the LangGraph StateGraph. Raises if langgraph is missing."""
    if not _HAS_LANGGRAPH:
        raise RuntimeError("langgraph is not installed; use orchestrator.investigate instead")
    graph = StateGraph(InvestigationState)
    graph.add_node("plan", _node_plan)
    graph.add_node("investigate", _node_investigate)
    graph.add_node("act", _node_act)
    graph.add_node("report", _node_report)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "investigate")
    graph.add_edge("investigate", "act")
    graph.add_edge("act", "report")
    graph.set_finish_point("report")
    return graph.compile()


def investigate_case(case: dict[str, Any]) -> InvestigationState:
    """Uniform entry: LangGraph path when available, orchestrator otherwise."""
    if _HAS_LANGGRAPH:
        app = build_graph()
        initial: InvestigationState = InvestigationState(
            case_id=str(case.get("case_id", "unknown")),
            pattern_hint=str(case.get("pattern", "")),
            transaction_ids=list(case.get("transaction_ids", [])),
            subject=case.get("subject", {}),
        )
        return app.invoke(initial)
    return orchestrator.investigate(case)


def run_case(case: dict[str, Any]) -> InvestigationState:
    """Backward-compat alias for investigate_case."""
    return investigate_case(case)
