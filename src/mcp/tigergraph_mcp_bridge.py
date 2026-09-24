"""Optional bridge: local investigation tools -> official tigergraph-mcp tools.

``tigergraph-mcp`` (https://github.com/tigergraph/tigergraph-mcp) is the
official TigerGraph MCP server. This module maps every local tool in
:mod:`src.mcp.tools` to its official MCP counterpart so an MCP-capable agent
can run the *same* investigation against a live TigerGraph instance.

Requirements (all three, otherwise use :mod:`src.mcp.tools` offline):
  1. ``pip install tigergraph-mcp`` (installed in .venv)
  2. A reachable TigerGraph instance: TIGERGRAPH_HOST/USER/PASS/GRAPH,
     plus a tigergraph-mcp connection profile (see docs/mcp-integration.md)
  3. The GSQL queries in src/tigergraph/queries.gsql installed on the graph

When any requirement is missing, :func:`call_via_mcp` raises
:class:`BridgeUnavailable` with a precise reason. The offline default path
never imports this module.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

# Local tool name (as in src/mcp/tools.py TOOLS) ->
# (official MCP tool, installed GSQL query, local->MCP arg mapping).
# Document tools: our GraphRAG is local; the MCP server exposes document /
# vector tools (see docs/mcp-integration.md) when a document collection is
# configured on the live instance.
LOCAL_TO_MCP: Dict[str, Dict[str, Any]] = {
    "get_transactions": {
        "mcp_tool": "run_installed_query",
        "query": "q_get_transactions",
        "args": {"transaction_ids": "transaction_ids"},
    },
    "card_ring": {
        "mcp_tool": "run_installed_query",
        "query": "q_card_ring",
        "args": {"card_id": "card1", "start_dt": "start_dt", "end_dt": "end_dt"},
        "note": "start_dt/end_dt are live-only GSQL params (q_card_ring "
                "accepts them); the local tool takes card1 only — extras are "
                "passed through only when the caller supplies them",
    },
    "device_cluster": {
        "mcp_tool": "run_installed_query",
        "query": "q_device_cluster",
        "args": {"device": "device", "min_cards": "min_cards"},
    },
    "mule_fanout": {
        "mcp_tool": "run_installed_query",
        "query": "q_mule_fanout",
        "args": {"hub_card": "hub_card", "start_dt": "start_dt",
                 "end_dt": "end_dt"},
        "note": "start_dt/end_dt are live-only GSQL params; the local tool "
                "takes hub_card only",
    },
    "takeover": {
        "mcp_tool": "run_installed_query",
        "query": "q_takeover_anomaly",
        "args": {"card_id": "card1", "window_secs": "window_secs"},
    },
    "synthetic": {
        "mcp_tool": "run_installed_query",
        "query": "q_synthetic_identity",
        "args": {"card_id": "card1"},
    },
    "evidence_subgraph": {
        "mcp_tool": "run_installed_query",
        "query": "q_evidence_subgraph",
        "args": {"txn_ids": "transaction_ids", "hops": "hops"},
    },
    "ring_components": {
        "mcp_tool": "run_installed_query",
        "query": "q_ring_components",
        "args": {"max_iter": "max_iter"},
        "note": "genuine graph algorithm (WCC label propagation); live only",
    },
    "fraud_knowledge": {
        "mcp_tool": "document_search",
        "query": None,
        "args": {"query": "query"},
        "note": "served locally by src.graphrag; on live infra use the MCP "
                "server's document/vector tools against the ingested README, "
                "policy, and closed-case narratives",
    },
}

LOCAL_TOOL_NAMES = tuple(LOCAL_TO_MCP)


class BridgeUnavailable(RuntimeError):
    """Raised when the live MCP bridge cannot be used."""


def is_available() -> bool:
    """True only when tigergraph-mcp is importable AND a live host is set."""
    if not os.environ.get("TIGERGRAPH_HOST"):
        return False
    try:
        import tigergraph_mcp  # noqa: F401
    except ImportError:
        return False
    return True


def _require_available() -> None:
    if not is_available():
        missing = []
        if not os.environ.get("TIGERGRAPH_HOST"):
            missing.append("TIGERGRAPH_HOST")
        try:
            import tigergraph_mcp  # noqa: F401
        except ImportError:
            missing.append("tigergraph-mcp package")
        raise BridgeUnavailable(
            "live MCP bridge unavailable (missing: "
            + ", ".join(missing)
            + "); use src.mcp.tools (offline local implementations)"
        )


def describe_mapping() -> Dict[str, Dict[str, Any]]:
    """Return the local->official tool mapping (no live connection needed)."""
    return {k: dict(v) for k, v in LOCAL_TO_MCP.items()}


def call_via_mcp(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Call the official MCP counterpart of a local tool.

    Same ``(name, args) -> dict`` contract as ``src.mcp.tools.call_tool``.
    Raises BridgeUnavailable when live requirements are missing, KeyError
    for unknown tool names.
    """
    _require_available()
    if name not in LOCAL_TO_MCP:
        raise KeyError(f"unknown local tool: {name!r}")
    mapping = LOCAL_TO_MCP[name]
    if mapping["mcp_tool"] == "document_search":
        raise BridgeUnavailable(
            "t_fraud_knowledge is served locally by src.graphrag; configure "
            "the MCP server's document collection for a live equivalent"
        )

    from tigergraph_mcp import tools as mcp_tools

    params = {
        mcp_param: args.get(local_param)
        for mcp_param, local_param in mapping["args"].items()
        if local_param in args
    }
    query_name = mapping["query"]
    graph_name = os.environ.get("TIGERGRAPH_GRAPH", "fraud_graph")

    async def _run() -> Any:
        return await mcp_tools.run_installed_query(
            query_name, params=params, graph_name=graph_name
        )

    try:
        raw = asyncio.run(_run())
    except Exception as exc:
        raise BridgeUnavailable(
            f"MCP call {mapping['mcp_tool']}({query_name}) failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    # tigergraph-mcp reports transport failures as a payload, not an
    # exception: {"success": false, "error": "..."}. Treat that as
    # unavailable rather than a normal result.
    if isinstance(raw, dict) and raw.get("success") is False:
        raise BridgeUnavailable(
            f"MCP call {mapping['mcp_tool']}({query_name}) failed: "
            f"{raw.get('error', 'unknown error')}"
        )
    return {
        "tool": name,
        "via": f"tigergraph-mcp:{mapping['mcp_tool']}",
        "query": query_name,
        "result": [
            {"type": getattr(block, "type", ""), "text": getattr(block, "text", "")}
            for block in (raw or [])
        ],
    }
