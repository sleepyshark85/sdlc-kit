# Measuring the SDLC

What a project built with this kit records, in which phase, for which practice, how it is collected, and what each
number tells the owner. [`sdlc.md`](sdlc.md#measuring) gives the four layers (cost, flow, quality, people); this page
is their detail. Each practice is a row of the README's
[table](../README.md#best-practices-and-where-the-kit-covers-them).

Status of each collector and metric:

- **Exists:** the kit records it today.
- **New:** to be built by the recording and scorecard PRs (see [Building it](#building-it)).
- **Pending:** depends on a practice not yet in the kit (release flags).

## Principles

- **Two numbers per practice.** *Adherence*: was the practice followed? *Effect*: did it do its job? Adherence
  without effect is ceremony; effect without adherence can't be traced to a practice. An *Enforced* practice needs
  only its blocks and bypasses counted; a *Guided* or *Trial* one needs both numbers.
- **Computed, not claimed.** A number comes from GitHub, git, the docs, CI or the hooks. Agents state only what no
  tool can know (the task, its kind, its planned size, the criteria it delivers), and the reviewer checks those
  against the diff. Sizes, times and counts are always computed.
- **Agents never see the scorecard.** An agent optimizes against the check it can see (`sdlc.md`, *The premise*): a
  developer shown its first-round approval rate learns to game it. The scorecard is for the owner; no brief cites it.
- **Per wave, trends over levels.** A wave is the unit: the scorecard compares each number with the waves before.
- **A metric without an action is dropped.** Each row below says what to do when the number goes the wrong way.

## Collectors

| ID | Collector | What it records | How | Status |
|---|---|---|---|---|
| C1 | Pull requests | Branch, title, description, labels, changed files and lines, opened, merged and closed times, merged by | `gh api` (REST and GraphQL) | Exists |
| C2 | Verdict comments | Verdict, the head sha it names, round, each must-fix with its cause label, late findings, author | `gh api` issue comments, parsed by the format in `agents/reviewer.md` | Exists |
| C3 | PR facts block | The facts only the author knows (below) | Written by the developer or fixer when it opens the PR; checked by the reviewer | New |
| C4 | Git history | Commits and their times, merge commits, `Conflicts:` trailers, when a line (a requirement ID, a decision) first appeared | `git log`, `git blame`, `git show` | Exists; trailer New |
| C5 | The project's docs | Requirements, criteria, open questions, traceability, plans, decisions, the flag registry | Parsed from Markdown tables (`REQUIREMENTS.md` or `docs/requirements/`, `docs/plan/`, `docs/decisions.md`, `docs/flags.md`) | Exists; flags Pending |
| C6 | Hook block log | Each action `git-gate.py` blocked: time, session, agent, rule. Never the command: it may hold a secret | One JSON line per block in `<session>/git-gate/<agent>.jsonl`, beside the transcripts, as `context-size.py` does | New |
| C7 | Context-size log | Each agent's context size after each tool call, and the warnings | `context-size.py` → `<session>/context-sizes/<agent>.jsonl` | Exists |
| C8 | Session transcripts | Tokens per call (input, output, cache read and write) per agent and role | The transcripts' `usage` fields, under `~/.claude/projects/<project>/` | Exists |
| C9 | CI runs | Each check's conclusion, duration and attempt; the mutation reports | `gh api` check runs and workflow runs; the `mutation-reports` artifact the .NET pack uploads | Exists |
| C10 | Security alerts | Code scanning, Dependabot and secret scanning alerts: severity, opened, fixed; the OpenSSF Scorecard result | `gh api` alerts endpoints; the Scorecard workflow's SARIF | Exists |
| C11 | Daily run on `main` | The full suite on `main` with default settings, and again with every in-progress flag on | A scheduled workflow (`daily.yml`) whose result is a check run on `main` | New; flags-on run Pending |
| C12 | Escape records | `Escaped from: #n` and `Should have caught: <practice>` in a fix PR | C3's block, written by the fixer or developer | `Escaped from` Exists; the cause New |
| C13 | Owner audit | Once per wave: a strict re-review of one random merged PR, and the owner's own read of one PR in full | A reviewer dispatched by the lead on a merged PR; the findings go into the scorecard PR | New |
| C14 | Code health | File and function sizes, duplication, analyzer suppressions, TODOs | A pack-provided command that writes JSON (the language decides how) | New |
| C15 | Dispatch log | Each agent the lead starts or resumes: time, agent id, role (agent type), model, the brief's first line (task, PR and round), the agent's outcome when it returns | A plugin hook after the Agent tool, appending one JSON line to `<session>/dispatches.jsonl`; the brief's first line follows the `dispatch` templates, so it parses | New |

### The PR facts block

Every PR description ends with an HTML comment the scorecard reads; it renders as nothing on GitHub:

```text
<!-- sdlc
task: W3-T2                      the plan's task, or none
kind: dark                       dark | switch-on | technical | flagged | fix | docs | process
planned: S                       the plan's size, or none
criteria: API-01.2, API-01.3     the numbered criteria it delivers, or none
reads: docs/requirements/api.md; ARCHITECTURE §3
metric: rework rate              a process change only: the metric it should move
escaped-from: #41                a fix of merged code only
should-have-caught: criteria     criteria | tests | mutation | review | design | threat-model | none
-->
```

The reviewer checks it like the rest of the description: a wrong kind or a missing `escaped-from` is a `[process]`
must-fix.

## Metrics by phase

Each table: the metric, the practice it measures, adherence (A) or effect (E), its collector, and what it tells you
and the action when it goes the wrong way.

### 1. Specify: requirements and architecture

| ID | Metric | Practice | A/E | From | Tells you · act when |
|---|---|---|---|---|---|
| SP1 | Share of feature PRs whose criteria existed on `main` before the PR's first commit | Spec before code | A | C3, C4 | Below 100%: code leads the spec, and the requirement written after it describes instead of specifies. Write the requirement first |
| SP2 | Share of requirements in an EARS pattern with numbered criteria | Structured, testable requirements | A | C5 | Low: criteria a test can't decide. Rewrite them before planning |
| SP3 | Open questions: count, median age, answered this wave | Ambiguity surfaced | E | C5, C4 | Ages growing: the owner is the bottleneck and tasks wait. Schedule the answers |
| SP4 | Documents past a split trigger and not split | Docs sized to the project | A | C5 | Any: split before the next plan |
| SP5 | Threat rows without a test; LLM categories neither covered nor ruled out | Threat model | A | C5 | Any: a mitigation nothing proves |
| SP6 | Decisions without a reason or date; dependencies in a lock file without a decision line | Decision records; New dependencies justified | A | C5, C4 | Any: a choice the next agent will undo |

### 2. Plan: waves and tasks

| ID | Metric | Practice | A/E | From | Tells you · act when |
|---|---|---|---|---|---|
| PL1 | Planned sizes: count of S, M and L | Small, deliverable tasks | A | C5 | Any L: split it before the plan merges |
| PL2 | Criteria of the wave's requirements cited by no task, or by more than one | Criteria numbered once, cited by tasks | A | C5 | Any: a gap or an overlap in the decomposition. Fix the plan (a candidate to become Enforced) |
| PL3 | Plan PR rounds and must-fixes | The plan's decomposition reviewed | E | C1, C2 | Many: the decomposition rules are unclear to the planner |
| PL4 | Tasks without `Reads:`, or whose `Reads:` names a whole document | Docs sized; context budget | A | C5 | Any: agents read more than they need |
| PL5 | Tasks added, split (the developer's "stop and split") or dropped after the plan merged | Small tasks; decomposition | E | C4 (plan history), C3 | Many: the plan guessed. Look at which rule each change broke |
| PL6 | Merge conflicts per wave, on docs and on code | Parallel tasks share no file; docs split | E | C4 (`Conflicts:` trailers) | Rising: parallel tasks overlap. Split the hot file or serialize the tasks |

### 3. Build: the developer's PR

| ID | Metric | Practice | A/E | From | Tells you · act when |
|---|---|---|---|---|---|
| BU1 | Changed production and test lines per PR, against the planned size | Small tasks; one change per PR | E | C1, C3 | Above the plan: scope creep or a bad estimate. Read PL5 with it |
| BU2 | Surviving mutants on the PR's first head | The developer self-checks | E | C9 | Any: the self-check was skipped or weak |
| BU3 | Requirements and criteria without a test; test IDs that name no requirement | Traceability | A, E | C5, C4 (test names) | Any: an untested promise, or a test whose purpose is lost |
| BU4 | Hook blocks by rule and by role | Mechanical rules are tools; least privilege | A | C6 | A rule blocked often: its instruction is unclear, or an agent drifts. Fix the instruction, not the hook |
| BU5 | PRs without an *Assumptions* section; assumptions per PR | Ambiguity surfaced | A | C1 | Missing: gaps filled silently. Many per PR: the spec is thin there |
| BU6 | Agents past the context warnings, by role | Context budget per agent | E | C7 | Rising: briefs or tasks too large, or agents resumed too long |

### 4. Review

| ID | Metric | Practice | A/E | From | Tells you · act when |
|---|---|---|---|---|---|
| RV1 | Rounds per PR; first-round approval rate | The quality bar; the developer self-checks | E | C2 | Many rounds: the developer and the bar disagree. Read RV2 for where |
| RV2 | Must-fixes by cause (`[tests]`, `[quality]`, `[bug]`, `[contract]`, `[ac]`, `[process]`), per PR and per 100 changed lines | The quality bar; a cause on every must-fix | E | C2, C1 | The top cause names the guidance to improve: `[ac]` the spec or plan, `[tests]` the test rules, `[contract]` the architecture |
| RV3 | Time from PR opened to first verdict; from a verdict to the next round | Review capacity | E | C1, C2 | Rising: review is the bottleneck. Smaller PRs, or more reviewers in parallel |
| RV4 | PRs at round 3 still failing (`owner-decision`) | Bounded review | E | C1 | Any: a disagreement the process can't settle. The owner's ruling becomes a rule |
| RV5 | Late findings (missed in an earlier round) | Independent review | E | C2 | Many: rounds are inconsistent |
| RV6 | Dark or flagged PRs with a behaviour-change must-fix | Unfinished work merges dark | E | C2, C3 | Any: the leak table is not followed. Find which row leaked |
| RV7 | Reviewer recall: must-fixes the audit found that the PR's review missed | Independent review | E | C13 | The main measure of review quality. Any `[bug]` missed: tighten the reviewer's checks |
| RV8 | Verdicts by a login other than the reviewer's; merges without an approval naming the head | Independent review; approval pinned | A | C2, C1 | Any: the gate was bypassed. Find how |

### 5. Merge

| ID | Metric | Practice | A/E | From | Tells you · act when |
|---|---|---|---|---|---|
| MG1 | Lead time, first commit to merge, split into building, waiting for review, rework and waiting to merge | Small batches; flow | E | C1, C2, C4 | The largest part is where flow is lost |
| MG2 | Merges not made by auto-merge | Merge only when the checks pass | A | C1 | Any: a manual merge around the gate |
| MG3 | CI duration and failure rate per check | CI scoped to the change | E | C9 | Slow or failing often: verification capacity spent badly |
| MG4 | Re-run jobs (attempt above 1); flaky tests found by the weekly run | Flaky tests found, not retried | A, E | C9 | Any re-run: a flake was retried instead of fixed |

### 6. On `main`: what merged

| ID | Metric | Practice | A/E | From | Tells you · act when |
|---|---|---|---|---|---|
| MN1 | Daily run result; hours `main` was red; time back to green | `main` always shows finished features | E | C11 | Red: unfinished work leaked or a test is broken. Fix before new work merges |
| MN2 | Change failure rate: fix PRs with `escaped-from` per merged PR | DORA | E | C12, C1 | Rising: defects pass every guard |
| MN3 | Time to restore: from the escaping PR's fix opened to merged | DORA | E | C12, C1 | Long: fixes are hard. Look at the escaping code's tests |
| MN4 | Rework rate: unplanned fix PRs that touch code merged in the last two waves | DORA | E | C3, C4 | Rising: work merges before it is done |
| MN5 | Escapes by `should-have-caught` | Every guard | E | C12 | The practice named most is the one to change this wave |
| MN6 | Open security alerts by severity and age; time to fix; new per wave | Static analysis; dependency vulnerabilities; secret scanning | E | C10 | Ageing high-severity alerts: schedule them as tasks |
| MN7 | OpenSSF Scorecard score and its failing checks | Supply-chain hygiene | E | C10 | A drop: a setting or workflow regressed |
| MN8 | Mutation score per package against its floor (weekly full run) | Full mutation runs held to a floor | E | C9 | Near the floor: tests are weakening |
| MN9 | Flags past their removal task; flags open | Release flags | A, E | C5 (`docs/flags.md`) | Any past removal: flag debt. Plan its removal now. Pending |
| MN10 | Code health trends: largest files and functions, duplication, suppressions, TODOs | The code quality bar | E | C14 | A trend upward: the bar erodes between reviews |
| MN11 | Merged PRs per wave by kind; features switched on | Throughput | E | C1, C3 | Read with MN2 and MN4: throughput alone inflates with AI |

### 7. Learn: the process itself

| ID | Metric | Practice | A/E | From | Tells you · act when |
|---|---|---|---|---|---|
| LN1 | Tokens and cost by role, per merged PR, per wave and per feature switched on | Context budget; cost | E | C8 | A role whose cost rises: its briefs or tasks grow. Compare with BU6 |
| LN2 | The owner's load: escalations, audit time, commits by the owner | A person accountable | E | C1, C13 | Rising: the process pushes decisions back to the owner |
| LN3 | Each process change's metric, before and after (the next one or two waves) | Each process change names its metric | E | C3 (`metric`), earlier scorecards | No movement: revert it. A Trial practice that moved its metric becomes Guided or Enforced |
| LN4 | The kit's version during the wave | Instructions versioned and released | A | The installed plugin's `plugin.json`, read by the scorecard | Attributes a change in the numbers to a kit release |

## The agent team

The same data, cut by **agent role** (lead, developer, fixer, reviewer) and by **model**, to see how the team
works, what each role costs and how good its output is. The dispatch log (C15) ties each agent to its task and PR;
its transcript (C8, `<session>/subagents/agent-<id>.jsonl`) gives its activity and cost; GitHub (C1, C2, C12) gives
the quality of what it produced.

### Activity

| ID | Metric | Per | From | Tells you · act when |
|---|---|---|---|---|
| AG1 | Dispatches and resumes per wave | Role | C15 | Many resumes of one role: its tasks or briefs are too large for one context |
| AG2 | Turns, tool calls and wall-clock time per dispatch; the tool mix (reads, edits, shell, searches) | Role, model | C8 | A role whose calls per task rise: it searches for what its brief should have named. Check the `Reads:` lines |
| AG3 | Dispatch to outcome: a developer's time to an open PR; a reviewer's time to a verdict; a fixer's time to a pushed fix | Role | C15, C1, C2 | The slowest step of the flow, by role |
| AG4 | Tool errors, permission denials and hook blocks per dispatch | Role | C8, C6 | Rising: the agent fights its environment. Fix the instruction or the permission rule |

### Cost

| ID | Metric | Per | From | Tells you · act when |
|---|---|---|---|---|
| AG5 | Tokens (input, output, cache read, cache write) and cost per dispatch | Role, model | C8 | The cost table behind LN1 |
| AG6 | Cost per merged PR and per feature switched on, split by role | Role | C8, C15, C1 | Which role a PR's cost goes to. Review costing more than building is expected; a lead's share rising is not |
| AG7 | Cache read share of input tokens | Role | C8 | Low: briefs or contexts change in ways that defeat prompt caching |
| AG8 | Peak context per dispatch; dispatches past the warnings | Role | C7 | Read with BU6: large contexts cost on every step and recall less |

### Quality of each role's output

| ID | Metric | Role | From | Tells you · act when |
|---|---|---|---|---|
| AG9 | First-round approval rate; must-fixes per 100 changed lines by cause; survivors at the first head; escapes from its PRs | Developer | C2, C1, C9, C12 | The developer's quality. A cause that dominates names its weak point |
| AG10 | PR descriptions whose claims the reviewer refuted (a `[process]` must-fix on a claim) | Developer, fixer | C2 | Any: reports can't be trusted unchecked. Tighten the self-check |
| AG11 | Fixes that needed another round; fixes wider than their finding (changed lines against the finding's scope); hand-backs to a developer | Fixer | C2, C1, C15 | Rising: the fixer gets work above its size, or its model is too small for it |
| AG12 | Recall: must-fixes the audit found that the review missed (RV7). Precision: must-fixes withdrawn after the developer disputed them, or overruled by the owner | Reviewer | C13, C2 | Low recall: defects pass review. Low precision: review costs rounds on non-issues. Both feed the reviewer's instructions |
| AG13 | Late findings; agreement between a strict re-review and the first review of the same head | Reviewer | C2, C13 | Low agreement: verdicts depend on the reviewer more than on the code |
| AG14 | Briefs that named a whole document or a conclusion; re-dispatches caused by a brief's error; diffs or full logs the lead read itself | Lead | C15, C8 | Any: the lead spends its own context, the costliest, or steers a reviewer |
| AG15 | Escalations the lead took to the owner, against the PRs at round 3 | Lead | C1 | The lead escalating less than round 3 needs: decisions taken without the owner |

### Comparing models

Each metric above grouped by model answers whether a role could use a cheaper model, or needs a stronger one: for
example the fixer's AG11 on a smaller model against its AG5 savings. A model change for a role is a process change:
it names the metric it should move (LN3), runs for a wave, and is kept or reverted on the scorecard.

Per-agent numbers are reported by role and model, never as a ranking of single agents: one dispatch is a sample of
one, and each table shows its count (n) beside the number.

## The scorecard

`scorecard.py wave <n>` (standard library and `gh`) runs at the end of a wave and writes
`docs/scorecards/wave-<n>.md`, which merges by PR like any doc.

- **The wave's window:** from its plan PR's merge to the next plan PR's merge. A PR belongs to the wave its `task`
  names; a PR without one (a fix, a docs change) to the window it merged in.
- **Sections:**
  - the summary: DORA's five keys (MN2–MN4, MG1, MN11), cost (LN1) and the owner's load (LN2);
  - one row per README practice, with its adherence and effect numbers, the trend, and for a Trial practice the
    suggestion to keep or drop it;
  - escapes by cause (MN5), alerts (MN6), the audit's findings (RV7);
  - the agent team: activity, cost and quality by role and by model (AG1–AG15);
  - the numbers past a threshold, each with the action from the tables above.
- **The owner reads it** and decides: Trial practices kept or dropped, and the process changes for the next wave,
  each naming its metric (LN3).
- **Privacy:** transcripts and hook logs are read locally and only their totals reach the scorecard.

## Building it

| PR | What it adds | Metrics it enables |
|---|---|---|
| Recording | The PR facts block (C3) in the developer, fixer and reviewer definitions; `git-gate.py`'s block log (C6); the `Conflicts:` trailer (C4); `Should have caught:` (C12); the daily run on `main` (C11); the owner audit in the lead's routine (C13); the dispatch log hook (C15); a `withdrawn` marker on a must-fix the reviewer drops after a dispute (C2) | All but MN9 and MN10 have their data |
| Scorecard | `scorecard.py`, its tests, and the scorecard page's template | Every metric above with data |
| Release flags | `docs/flags.md` and the flags-on daily run | MN9, MN1 with flags on |
| Each pack | The code-health command (C14) | MN10 |
