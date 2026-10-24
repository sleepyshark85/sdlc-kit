# The SDLC

How a project built with this kit goes from a requirement to merged code, who does what, and how the process itself is
measured and changed. The rules agents follow are in the template's
[`docs/conventions.md`](../plugins/sdlc-kit/template/docs/conventions.md); each practice and the part of the kit
that covers it are in the [README](../README.md#best-practices-and-where-the-kit-covers-them).

## The premise

AI agents speed the whole SDLC up, but don't change the fundamentals of a CI/CD-era SDLC: DORA's 2025 report calls
AI an amplifier, faster for teams with strong practices and faster at producing instability for teams without them.
What agents change is the cost of each activity, and the kit is built on the new costs:

| Activity | With agents | So the kit… |
|---|---|---|
| Writing code | Nearly free | puts the effort into specifying (requirements, tasks) and verifying (review, tests, mutation) |
| Verifying code | The bottleneck | spends review on judgement, and gives tools everything a tool can check |
| Tests, mutation, property tests | Cheap | makes a high bar affordable: good code, not working code |
| Knowledge transfer | Every agent starts cold | writes everything down: conventions, plans, briefs, decisions |

Three fundamentals become load-bearing: **verification is the product** (an agent optimizes against the check it can
see, so a weak check is worse than none); **review is independent** (a fresh reviewer per PR, with its own identity);
and **the written process is code** (agents, skills and hooks are versioned, reviewed and measured).

## Roles

| Role | Who | Does | Never |
|---|---|---|---|
| Owner | A person | Sets requirements and the bar, decides escalations, applies repository settings, reads the scorecard | Reads every diff |
| Lead | The main Claude Code session | Plans waves, dispatches agents, sets auto-merge on approval | Reads diffs or full logs; merges without an approval |
| Developer | `developer` agent (Opus) | Builds one task, self-checks, opens its PR | Widens a task; merges |
| Fixer | `fixer` agent (Sonnet) | Fixes small, bounded findings and merge conflicts | Widens a fix |
| Reviewer | `reviewer` agent (Opus), new per PR | Judges the PR against the bar; posts the verdict the gate reads | Commits, pushes or edits |

## The flow

```text
requirement ──► wave plan (plan-wave) ──► plan PR reviewed for its decomposition
                                              │
          ┌───────────────────────────────────┘
          ▼  for each task, in order (parallel only when they share no file)
   developer: build, self-check, PR ──► reviewer: verdict ──► fixer or developer: fixes ──┐
          ▲                                   │  approve                                 │ round ≤ 3
          │                                   ▼                                          │
          │                     lead: gh pr merge --auto ──► merged when checks pass     │
          └──────────────────────────────────────────────────────────────────────────────┘
                                              │  round 3 still failing
                                              ▼
                                       owner decides (owner-decision)
```

1. **Plan.** The `plan-wave` skill turns requirements into tasks of one behaviour or one contract, each S or M in
   size, each dark, flagged, switch-on or technical. The plan is a PR, reviewed against its decomposition checklist.
2. **Build.** The lead dispatches one task per developer with the `dispatch` skill. The developer builds it, runs
   mutation testing on its diff, re-reads the diff against the bar, and opens the PR with its assumptions.
3. **Review.** A new reviewer judges the PR against the conventions, the architecture and the quality bar, and posts
   `**Verdict: APPROVE** at <sha>` or the must-fixes, each with a cause label. At most three rounds.
4. **Merge.** The lead sets auto-merge; GitHub merges once the review gate and every required check pass on an
   up-to-date branch. A dark or flagged task changes no behaviour with the defaults, so `main` shows only finished
   features; the switch-on task releases the feature.
5. **Learn.** At the end of a wave the owner reads the scorecard. A process change names the metric it should move,
   and is kept or reverted on it.

## Guards

What keeps that flow safe is mostly mechanical, so it holds whatever an agent does:

| Layer | Guard |
|---|---|
| The agent's session | The git hook: no commit on `main` or push to it, branch prefixes, staged files, no force push, merge only with `--auto`, no settings changes, the reviewer never commits, only the reviewer posts verdicts; each component's checks before a commit and a push. The context hook: a warning at 150k and 300k tokens. Permission rules for destructive commands |
| GitHub | Branch protection with every required check, up to date, admins included; the review gate trusting only the reviewer's identity and the owner's; merge commits only |
| CI | Build with warnings as errors, tests on two systems, format, locked restore, vulnerable packages, CodeQL, diff-scoped mutation with survivors in the summary, the docs' links; weekly full mutation against the floor, flaky-test runs, Scorecard |

## Measuring

Four layers, as watching only the first two is how teams conclude AI made them faster while it made them worse:

| Layer | Question | Measures |
|---|---|---|
| Cost | What did it spend? | Tokens by role per merged PR; live API spend against its cap |
| Flow | How fast does work move? | Lead time; review rounds per PR; PR size |
| Quality | Is what moved good? | Change failure rate (`Escaped from:` lines); rework rate; must-fixes by cause; mutation scores; open alerts |
| People | What did it take from the owner? | Escalations (`owner-decision`); one merged PR per wave read in full, and what review missed |

The kit's first version carries the conventions these measures need (cause labels, `Escaped from:`, the
`owner-decision` label, size in the plan); the scorecard script that reads them is [planned](../README.md#planned).

## Changing the process

- The kit is the one source of the process: a change lands here first, by PR, and projects take it with a plugin
  update. Files a project copied from the template (workflows, the review gate, the conventions) are updated by hand
  until the planned `sync` skill exists.
- A process change says which metric it should move. A practice marked *trial* in the README stays a trial until a
  project's scorecard shows it moved its metric; one that doesn't is dropped.
- Officina, where these practices were found, is the kit's testbed.
