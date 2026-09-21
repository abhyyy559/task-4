"""MCP tool wrappers: uniform function surface over client + retriever.

Each tool returns structured JSON (never raises for bad input: returns an
error object). `config/mcp.json` mirrors TOOL_SCHEMAS. Direct mock API calls
are forbidden here — side effects live in src/actions/executor.py only.
"""
from __future__ import annotations

from typing import Any, Callable

from src.tigergraph.client import TigerGraphClient
from src.graphrag.retriever import Retriever

_client: TigerGraphClient | None = None
_retriever: Retriever | None = None


def get_client() -> TigerGraphClient:
    global _client
    if _client is None:
        _client = TigerGraphClient()
    return _client


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def _ok(name: str, data: Any) -> dict[str, Any]:
    return {"tool": name, "status": "ok", "data": data}


def _err(name: str, message: str) -> dict[str, Any]:
    return {"tool": name, "status": "error", "error": message}


def t_get_transactions(args: dict[str, Any]) -> dict[str, Any]:
    try:
        ids = args["transaction_ids"]
        return _ok("get_transactions", get_client().get_transactions(ids))
    except (KeyError, ValueError, FileNotFoundError) as exc:
        return _err("get_transactions", str(exc))


def t_card_ring(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok("card_ring", get_client().q_card_ring(args["card1"]))
    except KeyError as exc:
        return _err("card_ring", f"missing arg: {exc}")


def t_device_cluster(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok("device_cluster", get_client().q_device_cluster(args["device"]))
    except KeyError as exc:
        return _err("device_cluster", f"missing arg: {exc}")


def t_mule_fanout(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok("mule_fanout", get_client().q_mule_fanout(args["hub_card"]))
    except KeyError as exc:
        return _err("mule_fanout", f"missing arg: {exc}")


def t_takeover(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok("takeover", get_client().q_takeover(args["card1"]))
    except KeyError as exc:
        return _err("takeover", f"missing arg: {exc}")


def t_synthetic(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok("synthetic", get_client().q_synthetic(args["card1"]))
    except KeyError as exc:
        return _err("synthetic", f"missing arg: {exc}")


def t_evidence_subgraph(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok("evidence_subgraph",
                   get_client().q_evidence_subgraph(args["transaction_ids"]))
    except KeyError as exc:
        return _err("evidence_subgraph", f"missing arg: {exc}")


def t_fraud_knowledge(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return _ok("fraud_knowledge",
                   get_retriever().search(args["query"], int(args.get("k", 3))))
    except KeyError as exc:
        return _err("fraud_knowledge", f"missing arg: {exc}")


TOOLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "get_transactions": t_get_transactions,
    "card_ring": t_card_ring,
    "device_cluster": t_device_cluster,
    "mule_fanout": t_mule_fanout,
    "takeover": t_takeover,
    "synthetic": t_synthetic,
    "evidence_subgraph": t_evidence_subgraph,
    "fraud_knowledge": t_fraud_knowledge,
}

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_transactions": {"args": {"transaction_ids": "int[]"}},
    "card_ring": {"args": {"card1": "uint"}},
    "device_cluster": {"args": {"device": "string"}},
    "mule_fanout": {"args": {"hub_card": "uint"}},
    "takeover": {"args": {"card1": "uint"}},
    "synthetic": {"args": {"card1": "uint"}},
    "evidence_subgraph": {"args": {"transaction_ids": "int[]"}},
    "fraud_knowledge": {"args": {"query": "string", "k": "int?"}},
}


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    fn = TOOLS.get(name)
    if fn is None:
        return _err(name, f"unknown tool: {name}")
    try:
        return fn(args or {})
    except Exception as exc:  # never silent: structured error
        return _err(name, f"{type(exc).__name__}: {exc}")
