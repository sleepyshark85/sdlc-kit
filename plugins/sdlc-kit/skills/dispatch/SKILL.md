---
name: dispatch
description: Writes the brief for a developer, fixer or reviewer agent from a template, so every dispatch carries the same fixed requirements. Use whenever the lead sends an agent to build a task, fix review findings, review a pull request, or bring a pull request up to date with its base.
argument-hint: "[developer|fix|review|merge-check]"
---

# Dispatch an agent

Kind asked for: `$0` (`developer`, `fix`, `review` or `merge-check`).

1. Open the kind's template: [developer](templates/developer.md), [fix](templates/fix.md),
   [review](templates/review.md), [merge-check](templates/merge-check.md). It names the agent to use and holds the
   brief.
2. Fill every `{{…}}` placeholder. Don't copy rules into the brief: it points to the project's
   `docs/conventions.md`, its language rules and [agent-rules.md](agent-rules.md).
3. Check the brief before sending it:
   - **The task:** a developer brief names one task of the wave plan, never a whole feature.
   - **Sections:** named ones (`ARCHITECTURE §3`, `docs/decisions.md P4`), never a whole document.
   - **Branch and base:** the base is the branch the PR sits on, and a stacked one names that PR.
   - **Files:** with agents working in parallel, each brief lists its own files, and no two briefs share one.
   - **Facts, not conclusions:** a reviewer brief may point at a part or a claim to verify, never at what to find.
   - **Scratch prefix:** unique among the agents running now (the task id, plus the round).
   - **Live cost cap:** a dollar figure, or "no live calls".
4. Send it with the Agent tool, as the template says.

## Lead's routine

- Never read diffs, conflict hunks, whole files or full logs yourself: use `head` or `grep`, or dispatch a
  merge-check, a fixer or a reviewer, and act on its short report.
- Set auto-merge (`gh pr merge N --auto --merge`; GitHub deletes the merged branch) in the same step as reading an
  approving report with nothing in `Needs the lead`. The required `review` check means it merges only on an approving
  verdict on its head; to doubt an approval, ask for a strict re-review by a new reviewer, which counts as one of the
  PR's rounds.
- Handle each report in one step: decide and send the next brief.
- Review rounds run without the lead: the agent that fixes a verdict sends the next round to the PR's reviewer
  ([fix](templates/fix.md)). Only the lead dispatches a new reviewer, takes round 3's outcome to the owner (and labels
  the PR `owner-decision`) and sets auto-merge.
- Resume an agent only for the same PR and while its context is under the context hook's first warning (the hook's
  `--report` shows each agent's size); otherwise dispatch a fresh one.
- **Round 3 to the owner:** the owner's ruling goes on the PR as a comment, one line per open must-fix:
  `**Owner: upheld** <number and label>` (it is fixed before the merge) or `**Owner: overruled** <number and label>`.
- **The audit, once per wave** after its last merge: a new reviewer re-reviews one merged PR picked at random, with
  the [review](templates/review.md) brief's *Audit* text, and checks that PR's briefs against step 3 above. The owner
  also reads one PR in full and notes the time it took. Both go to the owner for the scorecard, never to a brief.
- Keep a status note in the project memory, and update it when the context hook warns and at the end of a session.
- A PR that changes the process (agents, skills, hooks, conventions) names the metric it should move.
