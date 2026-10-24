---
name: team-report
description: Reports the agent team's activity and cost by role and by model (agents, resumes, requests, tool calls and errors, hook blocks, tokens, cache share, peak context, cost) from this project's local session files. Use when the owner asks what the agents did or cost, for a session, a day or a wave, or to compare models for a role.
argument-hint: "[--session <id>] [--since <date>] [--until <date>]"
---

# Report the agent team

For the owner only. The numbers are never put in a brief or shown to an agent: an agent shown its own numbers
optimizes for them (`docs/measuring.md`, *Principles*).

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agent_report.py" $ARGUMENTS` from the project's folder. With no
   arguments it reads every session of this project; a wave is `--since` its plan PR's merge and `--until` the next
   one's.
2. Show the owner its tables as they are, then at most three lines on what stands out, each tied to its metric in
   `docs/measuring.md` (AG1–AG8): a role whose cost or peak context grows, a low cache share, tool errors or blocks
   that cluster on one role.
3. A model missing from the price table is listed as unpriced; say so, and that `scripts/prices.json` names its
   source and the date it was checked.

The report covers activity and cost. The quality of each role's output (AG9–AG15) needs GitHub's data and comes with
the scorecard.
