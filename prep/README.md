# Evaluation Preparation — read in order

Everything you need to understand and defend this project in the evaluation round.

1. **[01-what-we-built.md](01-what-we-built.md)** — the story: what the agent is,
   how a case flows end to end, the judging criteria, dataset numbers, repo map.
2. **[02-how-it-works-technical.md](02-how-it-works-technical.md)** — the engineering:
   architecture diagram and every component (TigerGraph schema/GSQL, GraphRAG memory,
   policy engine, MCP bridge, executor, UI) plus the design decisions to say out loud.
3. **[03-fraud-domain-cheatsheet.md](03-fraud-domain-cheatsheet.md)** — the language:
   the 7 fraud patterns, 14 actions with approval routes, the R1–R10 policy rules in
   one line each, SAR conditions, and all 20 cases at a glance.
4. **[04-evaluation-playbook.md](04-evaluation-playbook.md)** — the performance:
   30-second and 2-minute pitches, the demo script, likely questions with strong
   answers, trap questions with honest answers, and things to never claim.

> Snapshot 2026-09-21: written while the final official-spec rebuild was completing.
> Concept, architecture, policy engine, and domain rules are final; implementation
> line-items refresh after the final tester/reviewer pass.
