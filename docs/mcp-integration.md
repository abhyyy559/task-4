# TigerGraph MCP integration

The official task requires TigerGraph MCP
(https://github.com/tigergraph/tigergraph-mcp). This repo satisfies it two ways:

1. **Offline default** — `src/mcp/tools.py`: local tool implementations with
   the same `(name, args) -> dict` contract the agent investigates with.
2. **Live bridge (optional)** — `src/mcp/tigergraph_mcp_bridge.py`: maps every
   local tool to its official `tigergraph-mcp` counterpart. `tigergraph-mcp`
   1.0.3 is installed in `.venv`.

## Tool mapping

| Local tool (`src/mcp/tools.py`) | Official MCP tool | Installed GSQL query (`src/tigergraph/queries.gsql`) |
|---|---|---|
| `get_transactions` | `run_installed_query` | `q_get_transactions` |
| `card_ring` | `run_installed_query` | `q_card_ring` |
| `device_cluster` | `run_installed_query` | `q_device_cluster` |
| `mule_fanout` | `run_installed_query` | `q_mule_fanout` |
| `takeover` | `run_installed_query` | `q_takeover_anomaly` |
| `synthetic` | `run_installed_query` | `q_synthetic_identity` |
| `evidence_subgraph` | `run_installed_query` | `q_evidence_subgraph` |
| `ring_components` | `run_installed_query` | `q_ring_components` |
| `fraud_knowledge` | MCP document/vector tools | n/a — served locally by `src/graphrag`; on live infra ingest the README, Fraud Policy, and closed-case narratives into the MCP server's document collection |

Graph algorithms: `q_ring_components` is a genuine graph algorithm — weakly
connected components over the CARD—TRANSACTION—DEVICE subgraph via iterative
min-label propagation (not a bounded traversal). Its local counterpart
(`ring_components` in `src/mcp/tools.py`) runs union-find over the same edge
set and is unit-tested. The remaining installed queries use bounded multi-hop
traversals (`q_card_ring`, `q_device_cluster`, `q_evidence_subgraph`), which are
the GSQL expression of the connectivity analysis the task's graph algorithms
would perform.

## Enabling the live bridge

```bash
pip install tigergraph-mcp          # already in .venv
export TIGERGRAPH_HOST=https://<workspace>.tgcloud.io
export TIGERGRAPH_USER=tigergraph
export TIGERGRAPH_PASS=<secret>     # via the Secure Vault, never in chat
export TIGERGRAPH_GRAPH=fraud_graph
# configure a tigergraph-mcp connection profile per its README, then:
```

```python
from src.mcp.tigergraph_mcp_bridge import call_via_mcp, is_available
assert is_available()
out = call_via_mcp("t_card_ring", {"card1": "411111", "start_dt": 0, "end_dt": 999999})
```

Without a live host, `call_via_mcp` raises `BridgeUnavailable` and the agent
stays on the offline tools. The investigation logic in
`src/agent/investigate.py` is tool-contract agnostic: swapping the tool
backend does not change evidence, scoring, or policy behavior.

## Honest status

- The bridge is implemented, installed, and mapping-complete; every local
  tool has an official counterpart entry (`describe_mapping()` needs no live
  connection).
- It has **not** been exercised against a live TigerGraph instance in this
  environment (no Savanna credentials available). Live verification is
  recorded as an open item in TASK-PLAN.md.
