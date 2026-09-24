# Evaluation Playbook — walk in confident

## The 30-second version

"Fraud analysts investigate manually across ten systems and finish after the money's
gone. We built an agentic investigator on TigerGraph: it takes a risk alert, a
customer complaint, or an analyst's hunch, traverses a knowledge graph of 590,000
transactions to gather evidence, checks 5,500 past cases from memory, and recommends
the next best action — each one citing the policy rule that authorized it and the
human approval route it needs. Every claim cites its evidence."

## The 2-minute version

Add: "Three things make it agentic rather than a classifier. First, it investigates —
k-hop graph traversals, shared device and region clustering, velocity analysis — and
the risk score is only the trigger, never the verdict. Second, it knows when it's
uncertain: it requests evidence — customer validation, step-up auth, analyst info —
and gives you next-best actions *before and after* that evidence, so you can see what
changed. Third, it's policy-gated: ten fraud rules decide what's allowed, only
auto-route actions execute without a human, and it files Suspicious Activity Reports
when the law-grade thresholds are met. Half the benchmark cases are legitimate, so
clearing innocent customers is a scored behavior, not an afterthought."

## Demo script (3–5 minutes)

1. **(0:00)** The trigger — open HHG-014, the analyst request: "several cards, same
   unusual device profile." Say why this one: it's the graph-native case.
2. **(0:45)** The investigation — show the graph neighborhood expanding: device
   profile → connected cards → their transactions. Name the GSQL queries as they run.
3. **(1:45)** The evidence panel — each finding with source and entity IDs; the
   GraphRAG memory surfacing similar closed cases.
4. **(2:30)** Uncertainty → evidence request — "we're at 0.68 with conflicting
   signals, so per R1/R8 we verify with the customer and escalate." Show initial
   next-best actions with routes.
5. **(3:30)** The assumed response arrives — show final actions, `what_changed`,
   and the SAR panel if triggered.
6. **(4:15)** The case written to the graph + the stop reason. Close: "Every claim
   cites evidence, every action cites policy, every L1/L2 action waits for a human."

## Likely questions — and strong answers

**"Why TigerGraph and not Postgres or Neo4j?"**
"Fraud is a connections problem — shared devices, shared regions, card clusters.
TigerGraph gives us massively parallel traversals in GSQL, built-in graph algorithms
for the ring detection, and vector search in the same store for our GraphRAG memory.
One system for graph + vectors instead of gluing three together."

**"How does it avoid false positives?"**
"Four layers: the risk score can't convict on its own; R1 forces customer
verification on weak single signals; `uncertain` is a valid verdict that routes to
a human via R8; and half the benchmark is legitimate, so the policy engine is tuned
to clear — CLOSE_NO_FRAUD is a first-class outcome."

**"Walk me through one decision."**
Pick HHG-010: "0.90 score on $1,000.03. Graph shows [evidence]. Probability 0.XX from
N independent signals. Exposure crosses the $1,000 SAR threshold, so: BLOCK_CARD via
L1, CREATE_CASE auto, FILE_REPORT via L2. The agent executes only the auto ones."

**"What happens when the customer doesn't respond?"**
"R4: after 24 hours with no reply, monitor or decline the transaction — and if
exposure exceeds $500, escalate to an analyst. The system never blocks on silence
alone."

**"How do you handle a pattern you've never seen?"**
"That's `undocumented` — R9. The agent describes the shape in its own words,
escalates to an analyst, and refuses to force-fit a known pattern. HHG-014's device
cluster is the demo."

**"Where does the MCP fit?"**
"Every graph query and action is wrapped as a tool and exposed through the TigerGraph
MCP bridge, so any MCP-compatible client can drive the same investigation the
orchestrator runs — the agent's capabilities aren't locked inside our codebase."

**"What did you learn / what would you do with more time?"**
"Learned: restraint is a feature — the legitimate cases forced us to design
clearing paths, not just catching paths. With more time: a live Savanna instance for
the demo instead of the fallback path, streaming ingestion for real-time triggers,
and a human-in-the-loop approval UI so L1/L2 actions can be approved inside the
product."

## Trap questions — answer honestly, don't bluff

**"Is this running on a live TigerGraph instance right now?"**
→ "The code has a live pyTigerGraph path for Savanna or Community Edition. In this
environment it runs the offline fallback with identical query semantics, and each
answer file records which path served it — `written_to_graph` tells the truth per
case." Never claim a live write you didn't make.

**"Did you use the fraud labels from the original dataset?"**
→ "There are no labels in the inputs — they were removed by the task organizers, and
using the public files to recover them is disqualification. Our loader never sees a
label; verdicts come only from graph evidence."

**"Your old demo showed 20/20 — is that this benchmark?"**
→ "No. That was our earlier synthetic prototype. These 20 are the official HHG cases
on the real IEEE-CIS data — different IDs, different schema, different policy. We
rebuilt for the official spec."

**"Can it act on its own?"**
→ "Only `auto`-route actions — monitoring, case creation, escalation. Anything that
touches a customer's card or files a report is recommended to a human via L1/L2. The
executor refuses L1/L2 without recorded approval."

## Things to never claim

- A live TigerGraph cluster write that didn't happen (check `written_to_graph`).
- That customer/analyst replies are real — they're simulated and recorded as
  `assumed_response`, which the task explicitly allows.
- Accuracy numbers from the old synthetic prototype as if they apply here.
- That the agent "detects fraud" — it **investigates** and **recommends**; humans decide.

## One caveat to know (not to volunteer unprompted)

The HH Goa FAQ says all code must be written during the hackathon while libraries and
frameworks are encouraged. If an evaluator asks about build timeline, answer
truthfully about when each part was written — don't invent a timeline.

## Closer (if they ask "why should this win?")

"Most fraud tools are classifiers with a dashboard. Ours is an investigator with a
conscience: it gathers evidence like an analyst, cites policy like a compliance
officer, admits uncertainty like a scientist, and never touches a customer's money
without a human's permission. That's what agentic means here."
