"""MCP bridge tests: mapping completeness + offline unavailability.

Covers src/mcp/tigergraph_mcp_bridge.py without any live TigerGraph
connection: every local tool in src/mcp/tools.py must have a bridge entry,
and call_via_mcp must raise BridgeUnavailable (not fail silently) when the
live requirements are missing.
"""
from __future__ import annotations

import pytest

from src.mcp import tools as local_tools
from src.mcp import tigergraph_mcp_bridge as bridge


def test_every_local_tool_has_bridge_entry():
    mapping = bridge.describe_mapping()
    for name in local_tools.TOOLS:
        assert name in mapping, f"no bridge entry for {name}"


def test_bridge_unavailable_offline(monkeypatch):
    monkeypatch.delenv("TIGERGRAPH_HOST", raising=False)
    assert not bridge.is_available()
    with pytest.raises(bridge.BridgeUnavailable):
        bridge.call_via_mcp("t_card_ring", {"card1": "1"})


def test_bridge_rejects_unknown_tool():
    with pytest.raises((KeyError, bridge.BridgeUnavailable)):
        bridge.call_via_mcp("t_nope", {})


def test_bridge_raises_on_failure_payload(monkeypatch):
    """tigergraph-mcp returns {"success": false, "error": ...} as a payload
    (not an exception) on transport failure; the bridge must surface that as
    BridgeUnavailable rather than a normal result."""
    monkeypatch.setenv("TIGERGRAPH_HOST", "bogus-host")
    import tigergraph_mcp.tools as mcp_tools

    async def _fail(query_name, params=None, graph_name=None):
        return {"success": False, "error": "Cannot connect to host bogus-host"}

    monkeypatch.setattr(mcp_tools, "run_installed_query", _fail)
    assert bridge.is_available()
    with pytest.raises(bridge.BridgeUnavailable, match="Cannot connect"):
        bridge.call_via_mcp("card_ring", {"card1": "111"})


def test_ring_components_union_find(tmp_path):
    """ring_components links cards through shared devices (union-find WCC)."""
    import csv
    from src.tigergraph.client import TigerGraphClient

    txn_csv = tmp_path / "transactions.csv"
    id_csv = tmp_path / "identity.csv"
    with open(txn_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["TransactionID", "card1", "TransactionAmt"])
        w.writerow(["1", "111", "10"]); w.writerow(["2", "222", "20"])
        w.writerow(["3", "333", "30"]); w.writerow(["4", "444", "40"])
    with open(id_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["TransactionID", "DeviceInfo"])
        w.writerow(["1", "dev-A"]); w.writerow(["2", "dev-A"])
        w.writerow(["3", "dev-B"]); w.writerow(["4", "dev-C"])
    client = TigerGraphClient(data_dir=tmp_path)
    res = client.ring_components(min_size=2)
    assert res["query"] == "q_ring_components"
    comps = res["components"]
    assert len(comps) == 1
    assert comps[0]["card_count"] == 2
    assert set(comps[0]["cards"]) == {"111", "222"}
