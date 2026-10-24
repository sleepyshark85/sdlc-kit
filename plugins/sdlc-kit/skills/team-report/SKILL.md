---
name: team-report
description: Reports the agent team's activity and cost by role and by model (agents, resumes, requests, tool calls and errors, hook blocks, tokens, cache share, peak context, cost, and the spread per dispatch) from this project's local session files. For the owner, who runs it as /team-report.
argument-hint: "[--session <id>] [--since <date>] [--until <date>]"
disable-model-invocation: true
---

# Report the agent team

For the owner only, so only the owner's `/team-report` runs it: no agent invokes it on its own, and the numbers are
never put in a brief or shown to an agent, as an agent shown its own numbers optimizes for them (`docs/measuring.md`,
*Principles*).

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agent_report.py" $ARGUMENTS` from the project's folder. With no
   arguments it reads every session of this project; a wave is `--since` its plan PR's merge and `--until` the next
   one's.
2. Show the owner its tables as they are, then at most three lines on what stands out, each tied to its metric in
   `docs/measuring.md`: a role whose cost or peak context grows (AG5, AG8), a low cache share (AG7), tool errors or
   blocks that cluster on one role (AG4), a wide spread per dispatch for one role and model (AG2).
3. Say what the numbers leave out: unpriced responses (fast mode, or a model missing from `scripts/prices.json`, which
   names its source and the date it was checked), and that cost is a lower bound.

The report covers activity and cost. The quality of each role's output (AG9–AG15) needs GitHub's data and comes with
the scorecard.
