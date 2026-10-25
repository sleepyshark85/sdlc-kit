---
name: scorecard
description: Writes a wave's scorecard for the owner at the end of the wave, outside the repository (~/.sdlc/scorecards/<repository>/wave-<n>.md), from GitHub and this project's local session files. Its summary today holds DORA's five keys, the daily run, the agent team's cost and the owner's load. For the owner, who runs it as /scorecard.
argument-hint: "<wave number> [--out <folder>] [--project <folder>]"
disable-model-invocation: true
---

# Write the wave's scorecard

For the owner only, so only the owner's `/scorecard` runs it: no agent invokes it on its own, and its numbers never
go into a brief or reach an agent, as an agent shown its numbers optimizes for them (`docs/measuring.md`,
*Principles*). The file is written outside every checkout for the same reason.

1. At the end of a wave, once the next wave's plan PR has merged (before that, the window runs to now and the
   scorecard says the wave is in progress), run
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scorecard.py" wave $ARGUMENTS` from the project's folder, with `gh` signed
   in. It prints the path it wrote.
2. Show the owner the summary table as it is, then at most three lines on what stands out, each tied to its metric in
   `docs/measuring.md` with the action its row names: a change failure or rework rate that rose against the last
   scorecard (MN2, MN4), a lead-time phase that dominates (MG1), a red daily run (MN1), a cost per merged PR that grew
   (LN1).
3. Say what the numbers leave out: each "no data" row and why (no collector yet, or the owner records it, such as the
   audit time), and that cost is a lower bound (`team-report`).

The owner decides from it: process changes for the next wave, each by PR naming its metric (LN3), citing the
decision, never the scorecard's numbers by role.
