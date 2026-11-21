# Measuring the SDLC

What a project built with this kit records, in which phase, how it is collected, and what each number tells the
owner. [`sdlc.md`](sdlc.md#measuring) gives the four layers (cost, flow, quality, people); this page is their detail.
[Coverage](#coverage-every-practice) maps each practice of the README's
[table](../README.md#best-practices-and-where-the-kit-covers-them) to its metrics.

Status of each collector and metric:

- **Exists:** the kit records it today.
- **New:** to be built by the recording and scorecard PRs (see [Building it](#building-it)).
- **Core or candidate:** of the metrics below, only the [core metrics](#the-core-metrics) are built ahead of need;
  every other one is a candidate, designed here and built once a decision needs it.

## The core metrics

The scorecard is built for the decisions the owner takes after a wave, not for the catalogue below. Each core metric
answers one of them:

| The owner's decision | Core metrics | Built |
|---|---|---|
| Do defects escape, and which guard do we change? | MN2 change failure rate; MN5 escapes by `should-have-caught` | MN2; MN5 next |
| Does work merge before it is done? | MN4 rework rate | Yes |
| Where does work wait? | MG1 lead time by phase | Yes |
| Where do the developer and the bar disagree: which guidance do we fix? | RV1 rounds and first-round approval; RV2 must-fixes by cause | Next |
| Does review catch what it should? | RV7 reviewer recall, from the owner's audit | Next |
| What does a merged PR cost, and in which role? | LN1 cost by role per merged PR | Yes |
| What does the process take from the owner? | LN2 the owner's load | Yes |

Beside them, MN11 (merged PRs by kind) keeps throughput in view, and MN1 (the daily run) is core once a project adds
the daily run. LN3, a process change's metric before and after, is read on these.

**A candidate becomes core** when, after a real wave, the owner names a decision the core metrics couldn't settle and
the candidate would. The PR that builds it names that decision, as a process change names its metric. A candidate no
decision has needed after a project's first few waves is a sign the catalogue, not the scorecard, should shrink.

## Principles

- **Two numbers per practice.** *Adherence* (A): was the practice followed? *Effect* (E): did it do its job?
  Adherence without effect is ceremony; effect without adherence can't be traced to a practice. An *Enforced*
  practice's adherence is its blocks and bypasses; a practice with no meaningful number says why.
- **Computed, not claimed.** A number comes from GitHub, git, the docs, CI or the hooks. Agents state only what no
  tool can know (the task, its kind, its planned size, the criteria it delivers), and the reviewer checks those
  against the diff. Sizes, times and counts are always computed.
- **Agents never see the scorecard.** An agent optimizes against the check it can see (`sdlc.md`, *The premise*): a
  developer shown its first-round approval rate learns to game it. So scorecards live outside the repository, with
  the owner, and no brief cites them.
- **Per wave, trends over levels.** A wave is the unit: the scorecard compares each number with the waves before.
- **A metric without an action is dropped.** Each row below says what to do when the number goes the wrong way.
- **A metric is built when a decision needs it.** A designed metric costs nothing; a built one costs code, tests and
  the owner's reading time every wave. So the scorecard builds the [core metrics](#the-core-metrics) first, and the
  rest only on demand.

## Collectors

| ID | Collector | What it records | How | Status |
|---|---|---|---|---|
| C1 | Pull requests | Branch, title, description, labels, changed files and lines, opened, merged and closed times, merged by, and the timeline's auto-merge events | `gh api` (REST, GraphQL and the timeline) | Exists |
| C2 | Verdict comments | Verdict, the head sha it names, author; each must-fix with its cause label and its `(late)` or `(claim)` marker, and those `Withdrawn:` after the developer's `Disputed:` answer; the owner's ruling on a round-3 PR. A round is counted from the order of verdicts | `gh api` issue comments, parsed by the formats in `agents/reviewer.md` (*The verdict*) and the `dispatch` skill (*Round 3 to the owner*) | Exists |
| C3 | PR facts block | The facts only the author knows (below) | Written by the developer or fixer when it opens the PR, in the format of the template's `docs/conventions.md`; checked by the reviewer | Exists |
| C4 | Git history | Commits, their authors and times, merge commits, `Conflicts:` trailers, when a line (a requirement ID, a decision) first appeared, test names | `git log`, `git blame`, `git show`, `git grep`; the trailer is written by the merge-check brief | Exists |
| C5 | The project's docs | Requirements, numbered criteria, open questions, traceability, plans and their `Reads:` lines, decisions, mutation floors, the flag registry | Parsed from Markdown tables (`REQUIREMENTS.md` or `docs/requirements/`, `docs/plan/`, `docs/decisions.md`, `docs/flags.md`) | Exists |
| C6 | Hook block log | Each action `git-gate.py` blocked: time, session, agent, rule. Never the command: it may hold a secret | One JSON line per block in `<session>/git-gate/<agent>.jsonl` (time, agent type, and the rule as a fixed key such as `force-push`), beside the transcripts, as `context-size.py` does | Exists |
| C7 | Context-size log | Each agent's context size after each tool call; the warnings are derived from the hook's thresholds | `context-size.py` → `<session>/context-sizes/<agent>.jsonl` (time, agent type, tokens) | Exists |
| C8 | Session transcripts | Tokens per call (input, output, cache read and write), turns and tool calls, per agent and role | The transcripts' `usage` fields and tool calls, under `~/.claude/projects/<project>/` | Exists |
| C9 | CI runs | Each check's conclusion, duration and attempt; the mutation reports | `gh api` check runs and workflow runs; the `mutation-reports` artifact the .NET pack uploads | Exists |
| C10 | Security alerts | Code scanning, Dependabot and secret scanning alerts: severity, opened, fixed; the OpenSSF Scorecard result | `gh api` alerts endpoints; the Scorecard workflow's SARIF | Exists |
| C11 | Daily run on `main` | The full suite on `main` with default settings, and again with every in-progress flag on | The template's scheduled workflow (`daily.yml`, with `.github/daily.py`), daily and on demand: each component's `daily` suite from `.sdlc/checks.toml`, which its pack writes, and each flag turned on through the component's `flag_variable`. Its results are the check runs `daily (defaults)` and `daily (flags-on)` on `main`'s head commit | Exists |
| C12 | Escape records | The facts block's `escaped-from` and `should-have-caught` lines in a fix PR | C3's block, written by the fixer or developer | Exists |
| C13 | Owner audit | Once per wave: a strict re-review of one random merged PR; the owner's check of that PR's briefs against `dispatch`'s brief checks; and the owner's own read of one PR in full, with the time it took | The `dispatch` skill's *The audit* and the review brief's *Audit* text: a comment starting `**Audit** at <sha>` on the merged PR. The owner, who alone reads the lead's session, records the brief check, their read and its time in the scorecard | Exists |
| C14 | Code health | File and function sizes, duplication, analyzer suppressions, TODOs; tests that fake a type of the project itself; parsers and validators without a property or fuzz test; each test's duration | A pack-provided command that writes JSON, and the pack's test report uploaded like `mutation-reports` (the language decides how) | New |
| C15 | Dispatch log | Each agent the lead starts or resumes: time, agent id, role (agent type), model, the whole brief, and the agent's report when it returns (its outcome and `Live spend:` line) | Read from the session files, no hook needed: the lead's transcript holds each Agent call (brief, resolved model, agent id) and each SendMessage resume; each subagent's `.meta.json` holds its type and description, and its transcript its report. `scripts/agent_report.py` reads them locally, never published | Exists |
| C16 | Repository settings | Branch protection or rulesets on `main` (required checks, up to date, admins), merge settings, `security_and_analysis` (secret scanning, push protection) | `gh api` repository, branch protection and rulesets endpoints | New |

### The PR facts block

Every PR description ends with an HTML comment that holds the facts only its author knows: the task, its kind, the
planned size, the criteria it delivers, what its developer read, a process change's metric, and for a fix of merged
code the PR it escaped from and the guard that should have caught it. Its format is in the template's
[`docs/conventions.md`](../plugins/sdlc-kit/template/docs/conventions.md#how-we-work), which agents read; the
reviewer checks it against the diff.

## Metrics by phase

Each table: the metric, adherence (A) or effect (E), its collectors, and what it tells you with the action when it
goes the wrong way. [Coverage](#coverage-every-practice) says which practice each one measures.

### 1. Specify: requirements and architecture

| ID | Metric | A/E | From | Tells you · act when |
|---|---|---|---|---|
| SP1 | Share of feature PRs whose criteria existed on `main` before the PR's first commit | A | C3, C4 | Below 100%: code leads the spec. Write the requirement first |
| SP2 | Share of requirements in an EARS pattern with numbered criteria | A | C5 | Low: criteria a test can't decide. Rewrite them before planning |
| SP3 | Open questions: count, median age, answered this wave | E | C5, C4 | Ages growing: the owner is the bottleneck and tasks wait. Schedule the answers |
| SP4 | Documents past a split trigger and not split | A | C5 | Any: split before the next plan |
| SP5 | Threat rows without a test; LLM categories neither covered nor ruled out | A | C5 | Any: a mitigation nothing proves |
| SP6 | Decisions without a reason or date; dependencies in a lock file without a decision line | A | C5, C4 | Any: a choice the next agent will undo |
| SP7 | Type, package or API names in the architecture: its words matched against the code's public names | A | C5, C4 | Any: the architecture drifts toward the code and stops being language-neutral |
| SP8 | Spec PRs (requirements, architecture) merged with a reviewer's approval | A | C1, C2 | Below 100%: a spec merged unreviewed |

### 2. Plan: waves and tasks

| ID | Metric | A/E | From | Tells you · act when |
|---|---|---|---|---|
| PL1 | Planned sizes: count of S, M and L | A | C5 | Any L: split it before the plan merges |
| PL2 | Criteria of the wave's requirements cited by no task, or by more than one | A | C5 | Any: a gap or an overlap in the decomposition. Fix the plan (a candidate to become Enforced) |
| PL3 | Plan PR rounds and must-fixes | E | C1, C2 | Many: the decomposition rules are unclear to the planner |
| PL4 | Tasks without `Reads:`, or whose `Reads:` names a whole document | A | C5 | Any: agents read more than they need |
| PL5 | Tasks added, split (the developer's "stop and split") or dropped after the plan merged | E | C4 (plan history), C3 | Many: the plan guessed. Look at which rule each change broke |
| PL6 | Merge conflicts per wave, on docs and on code | E | C4 (`Conflicts:` trailers) | Rising: parallel tasks overlap. Split the hot file or serialize the tasks |
| PL7 | Contracts another task builds against that landed after their first user, or without a contract test | A | C5, C3, C4 | Any: two tasks each invented their side of a seam |
| PL8 | Feature waves that needed stacked PRs or a flag | E | C5, C1 | Rising: restructuring is not planned ahead of behaviour |

### 3. Build: the developer's PR

| ID | Metric | A/E | From | Tells you · act when |
|---|---|---|---|---|
| BU1 | Changed production and test lines per PR, against the planned size | E | C1, C3 | Above the plan: scope creep or a bad estimate. Read PL5 with it |
| BU2 | Surviving mutants on the PR's first head | E | C9 | Any: the self-check was skipped or weak |
| BU3 | Requirements and criteria without a test; test IDs that name no requirement | A, E | C5, C4 | Any: an untested promise, or a test whose purpose is lost |
| BU4 | Hook blocks by rule and by role | A | C6 | A rule blocked often: its instruction is unclear, or an agent drifts. Fix the instruction, not the hook |
| BU5 | PRs without an *Assumptions* section; assumptions per PR | A | C1 | Missing: gaps filled silently. Many per PR: the spec is thin there |
| BU6 | Agents past the context warnings, by role | E | C7 | Rising: briefs or tasks too large, or agents resumed too long |
| BU7 | PRs whose facts block says more than one kind, or a mechanical PR without its command | A | C3, C1 | Any: changes mixed in one PR |
| BU8 | PR descriptions without the attribution line | A | C1 | Any: AI authorship hidden |
| BU9 | Changed tests that fake something inside the project; tests over a second | A | C14 | Any: tests check the fake, not the code |
| BU10 | Parsers and validators without a property or fuzz test | A | C14 | Any: inputs no example covers |
| BU11 | New tests that kill no mutant and pin no criterion | A | C9, C5 | Any: a test that costs time and checks nothing new |
| BU12 | Golden files changed without the update flag in the PR, or without the reviewer noting the diff | A | C1, C2 | Any: a regression regenerated away |

### 4. Review

| ID | Metric | A/E | From | Tells you · act when |
|---|---|---|---|---|
| RV1 | Rounds per PR; first-round approval rate | E | C2 | Many rounds: the developer and the bar disagree. Read RV2 for where |
| RV2 | Must-fixes by cause (`[tests]`, `[quality]`, `[bug]`, `[contract]`, `[ac]`, `[process]`), per PR and per 100 changed lines | E | C2, C1 | The top cause names the guidance to improve: `[ac]` the spec or plan, `[tests]` the test rules, `[contract]` the architecture |
| RV3 | Time from PR opened to first verdict; from a verdict to the next round | E | C1, C2 | Rising: review is the bottleneck. Smaller PRs, or more reviewers in parallel |
| RV4 | PRs at round 3 still failing (`owner-decision`); PRs given a fourth round | A, E | C1, C2 | A fourth round: the bound was ignored. Many at round 3: a disagreement the process can't settle; the owner's ruling becomes a rule |
| RV5 | Late findings (missed in an earlier round) | E | C2 | Many: rounds are inconsistent |
| RV6 | Dark or flagged PRs with a behaviour-change must-fix | E | C2, C3 | Any: the leak table is not followed. Find which row leaked |
| RV7 | Reviewer recall: must-fixes the audit found that the PR's review missed | E | C13 | The main measure of review quality. Any `[bug]` missed: tighten the reviewer's checks |
| RV8 | Verdicts by a login other than the reviewer's; merges without an approval naming the head | A | C2, C1 | Any: the gate was bypassed. Find how |
| RV9 | Must-fixes without a cause label | A | C2 | Any: rework can't be counted by cause |

### 5. Merge

| ID | Metric | A/E | From | Tells you · act when |
|---|---|---|---|---|
| MG1 | Lead time, first commit to merge, split into building, waiting for review, rework and waiting to merge | E | C1, C2, C4 | The largest part is where flow is lost |
| MG2 | Merges not made by auto-merge; merges that are not merge commits | A | C1 (timeline), C4 | Any: a merge around the gate |
| MG3 | CI duration and failure rate per check; docs-only PRs that ran a build | E, A | C9, C1 | Slow or failing often: verification capacity spent badly. A docs-only build: the change detector missed |
| MG4 | Re-run jobs (attempt above 1); flaky tests found by the weekly run | A, E | C9 | Any re-run: a flake was retried instead of fixed |
| MG5 | Required checks, protection rules or security settings missing against `docs/conventions.md`, `docs/decisions.md` and `setup-repo.sh` | A | C16, C5 | Any: a setting drifted. The owner reruns `setup-repo.sh` |

### 6. On `main`: what merged

| ID | Metric | A/E | From | Tells you · act when |
|---|---|---|---|---|
| MN1 | Daily run result; hours `main` was red; time back to green | E | C11 | Red: unfinished work leaked or a test is broken. Fix before new work merges |
| MN2 | Change failure rate: fix PRs with `escaped-from` per merged PR | E | C12, C1 | Rising: defects pass every guard |
| MN3 | Time to restore: from the escaping PR's fix opened to merged | E | C12, C1 | Long: fixes are hard. Look at the escaping code's tests |
| MN4 | Rework rate: unplanned fix PRs that touch code merged in the last two waves | E | C3, C4 | Rising: work merges before it is done |
| MN5 | Escapes by `should-have-caught` | E | C12 | The practice named most is the one to change this wave |
| MN6 | Open security alerts by severity and age; time to fix; new per wave | E | C10 | Ageing high-severity alerts: schedule them as tasks |
| MN7 | OpenSSF Scorecard score and its failing checks (token permissions, pinned dependencies, branch protection among them) | E | C10 | A drop: a setting or workflow regressed |
| MN8 | Mutation score per package against its floor (weekly full run) | E | C9, C5 | Near the floor: tests are weakening |
| MN9 | Flags past their removal task; flags open | A, E | C5 (`docs/flags.md`) | Any past removal: flag debt. Plan its removal now |
| MN10 | Code health trends: largest files and functions, duplication, suppressions, TODOs | E | C14 | A trend upward: the bar erodes between reviews |
| MN11 | Merged PRs per wave by kind; features switched on | E | C1, C3 | Read with MN2 and MN4: throughput alone inflates with AI |
| MN12 | Broken links found on `main`; workflow-rule failures | A | C9 | Any: a check that should have blocked the PR didn't run |

### 7. Learn: the process itself

| ID | Metric | A/E | From | Tells you · act when |
|---|---|---|---|---|
| LN1 | Tokens and cost by role, per merged PR, per wave and per feature switched on | E | C8 | A role whose cost rises: its briefs or tasks grow. Compare with BU6 |
| LN2 | The owner's load: escalations, audit time, the owner's own commits | E | C1, C13, C4 | Rising: the process pushes decisions back to the owner |
| LN3 | Each process change's metric, before and after (the next one or two waves); process PRs without a `metric` | E, A | C3, earlier scorecards | No movement: revert it. A Trial practice that moved its metric becomes Guided or Enforced |
| LN4 | The kit's version during the wave | A | No collector: the scorecard reads the installed plugin's `plugin.json` | Attributes a change in the numbers to a kit release |
| LN5 | Live API spend per wave and per role, against each brief's cap | E, A | C15 (the reports' `Live spend:`) | Over a cap: an agent spent past its brief. Rising: live calls replace tests that would use a fake |

## The agent team

The same data, cut by **agent role** (lead, developer, fixer, reviewer) and by **model**, to see how the team
works, what each role costs and how good its output is. The dispatch log (C15) ties each agent to its task and PR;
its transcript (C8, `<session>/subagents/agent-<id>.jsonl`) gives its activity and cost; GitHub (C1, C2, C12) gives
the quality of what it produced. The owner's `team-report` skill (`scripts/agent_report.py`) reports AG1, AG5 and AG7
today, and AG2 (no turns), AG4 (no permission denials apart from tool errors) and AG8 in part; the rest come with
the scorecard.

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
| AG8 | Peak context per dispatch; dispatches past the warnings | Role | C8 (the warnings' thresholds from C7's hook) | Read with BU6: large contexts cost on every step and recall less |

### Quality of each role's output

| ID | Metric | Role | From | Tells you · act when |
|---|---|---|---|---|
| AG9 | First-round approval rate; must-fixes per 100 changed lines by cause; survivors at the first head; escapes from its PRs | Developer | C2, C1, C9, C12 | The developer's quality. A cause that dominates names its weak point |
| AG10 | Claims in a PR description the reviewer refuted (must-fixes marked `claim`) | Developer, fixer | C2 | Any: reports can't be trusted unchecked. Tighten the self-check |
| AG11 | Fixes that needed another round; fixes wider than their finding (changed lines against the finding's scope); hand-backs to a developer | Fixer | C2, C1, C15 | Rising: the fixer gets work above its size, or its model is too small for it |
| AG12 | Recall: must-fixes the audit found that the review missed (RV7). Precision: must-fixes `withdrawn` after a dispute, or overruled in the owner's ruling | Reviewer | C13, C2 | Low recall: defects pass review. Low precision: review costs rounds on non-issues. Both feed the reviewer's instructions |
| AG13 | Late findings; agreement between a strict re-review and the first review of the same head | Reviewer | C2, C13 | Low agreement: verdicts depend on the reviewer more than on the code |
| AG14 | Briefs that named a whole document or a conclusion; re-dispatches caused by a brief's error; `gh pr diff` or full logs the lead read itself | Lead | C15 (the briefs), C8 | Any: the lead spends its own context, the costliest, or steers a reviewer |
| AG15 | Escalations the lead took to the owner, against the PRs at round 3 | Lead | C1 | The lead escalating less than round 3 needs: decisions taken without the owner |

### Comparing models

Each metric above grouped by model answers whether a role could use a cheaper model, or needs a stronger one: for
example the fixer's AG11 on a smaller model against its AG5 savings. A model change for a role is a process change:
it names the metric it should move (LN3), runs for a wave, and is kept or reverted on the scorecard.

Per-agent numbers are reported by role and model, never as a ranking of single agents: one dispatch is a sample of
one, and each table shows its count (n) beside the number.

## Coverage: every practice

Each row of the README's table, with its adherence and effect metrics, or why it has none.

### Requirements and plan

| Practice | Adherence | Effect |
|---|---|---|
| Spec before code, reviewed like code | SP1, SP8 | MN5 (`criteria` escapes) |
| Structured, testable requirements with edge states | SP2 | BU3; RV2 (`[ac]`) |
| Criteria numbered once, cited by tasks | PL2 | RV2 (`[ac]`); PL3 |
| Docs sized to the project | SP4, PL4 | PL6; AG2 |
| Traceability | BU3 (test IDs naming no requirement) | BU3 (requirements without a test) |
| Ambiguity surfaced, not filled | BU5 | SP3; RV2 (`[ac]`) |
| Small, deliverable tasks of one behaviour or contract | PL1 | BU1; PL5; MG1 |
| The plan's decomposition reviewed before building | PL3 (plan PRs reviewed) | PL5; PL2 |

### Design

| Practice | Adherence | Effect |
|---|---|---|
| Decision records | SP6 | MN5 (`design` escapes) |
| Language-neutral architecture | SP7 | None: its gain (one design for any implementation) shows only when a second language arrives |
| Contract first at task seams | PL7 | RV2 (`[contract]`) |
| Fitness functions | None: a dependency test is code the reviewer checks once; MG3 counts its failures on PRs | MN5 (`design` escapes) |
| Threat model, LLM threats included | SP5 | MN5 (`threat-model` escapes); MN6 |

### Coding

| Practice | Adherence | Effect |
|---|---|---|
| Context files and templates for agents | AG14 | AG2 (searching for what a brief should name) |
| One change per PR; mechanical changes on their own | BU7 | RV3; MG1 |
| Mechanical rules are tools, not reviews | BU4 | RV2 (no `[process]` must-fix for what a hook enforces) |
| The developer self-checks before review | BU2 | RV1 |
| The code quality bar | RV2 (raised) | RV1; MN10; MN4 |
| Least privilege for agents | BU4; AG4 | MN5 (`none` escapes caused by an agent's action) |
| Unfinished work merges but is off on `main`; one switch-on task releases it | RV6 | MN1 |
| Release flags bounded: listed, off by default, one check point, removed within two waves of the switch-on | MN9 (past removal); RV2 (`[process]` must-fixes on flags) | MN1 (flags on); MN9 (open flags) |
| Old code reshaped before the feature | PL8 | BU1; MG1 (for features touching old code) |
| AI authorship visible, a person accountable | BU8 | None: accountability shows only when something escapes, and MN5 traces each escape to its PR |

### Security

| Practice | Adherence | Effect |
|---|---|---|
| Static analysis on every PR and weekly | MG5 (the check required) | MN6 |
| Dependency vulnerabilities | MG5 | MN6 |
| Secret scanning with push protection | MG5 (`security_and_analysis`) | MN6 (secret alerts) |
| New dependencies justified | SP6 | MN6 (Dependabot alerts on them) |
| Least-privilege workflow tokens | MN12 (workflow rules) | MN7 (token permissions) |
| Actions pinned by commit sha, kept current | MN12 (workflow rules) | MN7 (pinned dependencies); MN6 |
| OpenSSF Scorecard | Reported: the run itself | MN7 |
| Locked dependency restores | MG3 (restore failures) | None: a reproducible build shows only as the absence of "works on my machine" |
| SBOM and build provenance | Planned | Planned |

### Testing

| Practice | Adherence | Effect |
|---|---|---|
| Only boundaries faked; fast, deterministic tests | BU9 | MG4; MN5 (`tests` escapes) |
| Mutation testing on each PR's changed code | BU2 | MN8 |
| Survivors visible on the PR | None: the summary step is part of the mutation job, which MG3 counts | BU2 |
| Full mutation runs held to a floor | MG3 (the weekly job) | MN8 |
| Property and fuzz tests for parsers and validators | BU10 | MN5 (`tests` escapes in parsers) |
| Generated tests kept only if they kill a mutant or pin a criterion | BU11 | MG3 (suite time); MN8 |
| Flaky tests found, not retried | MG4 (re-runs) | MG4 (flakes found) |
| A daily run of the full suite on `main`, with the defaults and with every in-progress flag on | MN1 (a run each day) | MN1 (red runs, hours red, time back to green) |
| Golden files change only on purpose | BU12 | MN5 (`tests` escapes) |

### Merge and release

| Practice | Adherence | Effect |
|---|---|---|
| Protected trunk | MG5 | MN1 |
| Approval pinned to the exact commit | RV8 | MN2 |
| Independent review: a fresh reviewer per PR | RV8; AG1 (reviewers resumed across PRs) | RV7; AG12; AG13 |
| Briefs carry facts, not conclusions | AG14 | AG13 |
| Bounded review: three rounds, then the owner | RV4 (fourth rounds) | RV4 (round-3 failures); LN2 |
| Merge only when the checks pass; merge commits only | MG2 | MN1 |
| CI scoped to the change | MG3 (docs-only builds) | MG3 (duration) |
| Docs' links checked | MN12 | AG2 |
| Semantic versions, API compatibility check | Planned | Planned |

### The AI process itself

| Practice | Adherence | Effect |
|---|---|---|
| A clear AI policy: roles, models, autonomy | AG1 (roles dispatched as the policy says) | AG5–AG13 by role and model |
| Instructions versioned and released | LN4 | LN3 |
| Each process change names the metric it should move | LN3 (process PRs without a `metric`) | LN3 |
| Context budget per agent | BU6 | AG8; LN1 |
| The lead reads reports, not diffs | AG14 | AG6 (the lead's share of cost) |
| A cause on every must-fix | RV9 | RV2 (possible at all) |
| Escaped defects traced to their PR | MN2 (fix PRs with `escaped-from`) | MN5 |
| Scorecard per wave | This page | LN3 |
| The agent team measured by role and model | C15's coverage of dispatches | AG1–AG15 |

### Products that run a model

| Practice | Adherence | Effect |
|---|---|---|
| Threat model against the OWASP LLM Top 10 | SP5 | MN5 (`threat-model` escapes) |
| Evals, telemetry, red teaming, model change as a release | Planned | Planned |

## The scorecard

`scorecard.py wave <n>` (standard library and `gh`) runs at the end of a wave and writes `wave-<n>.md` to the owner's
scorecard folder, outside the repository and any agent's checkout (by default `~/.sdlc/scorecards/<repository>/`,
named after the repository without its owner). The owner runs it with the `scorecard` skill.

- **The wave's window:** from its plan PR's merge (the PR of branch `docs/plan-wave-<n>`) to the next plan PR's
  merge, or to now while there is none. A PR belongs to the wave its `task` names (`W<n>-T<m>`); a PR without one
  (a fix, a docs change) to the window it merged in.
- **How the summary counts:**
  - MG1's phases: first commit to opened (building), to the first verdict (waiting for review), to the last verdict
    before the merge (rework), to the merge (waiting to merge); a PR with no verdict waits for review until it
    merges. A verdict is a comment starting as the review gate's do. Each phase is the median over the wave's PRs.
  - MN4 compares files: an unplanned fix (`kind: fix`, no task) is rework when it changes a file a PR merged before
    it changed, since the start of the wave before.
  - MN1 reads every daily check run on each of `main`'s heads in the window (every head a PR's merge commit), not
    only the latest of each name, since a head can stay `main`'s for days: hours red run from a red run to the next
    green one, or to the window's end; the time back to green is the median and the longest of the red spells that
    ended green in the window, and a spell still red at the end is named.
  - LN1's cost by role shows each role's tokens by kind (input, cache write, cache read, output) as `team-report`
    does.
  - LN2's own commits are the commits of the wave's PRs that no AI `Co-Authored-By` trailer names (in any case),
    merge commits apart: git writes a merge's message, with no trailer, whoever merges.
  - A number whose collector doesn't exist yet reads "no data", never 0.
- **Sections,** the summary first, then the rest of the core; each other section comes only with the candidates it
  reads:
  - the summary: DORA's five keys (MN2–MN4, MG1, MN11), the daily run (MN1), cost (LN1, LN5) and the owner's load
    (LN2);
  - the rest of the core: rounds and must-fixes by cause (RV1, RV2), escapes by guard (MN5), the audit's recall
    (RV7), and each core metric's trend;
  - one row per README practice, from [Coverage](#coverage-every-practice): its numbers, the trend, and for a
    Trial practice the suggestion to keep or drop it;
  - alerts (MN6, MN7);
  - the agent team: activity, cost and quality by role and by model (AG1–AG15);
  - the numbers past a threshold, each with the action from the tables above.
- **The owner reads it** and decides: Trial practices kept or dropped, and the process changes for the next wave,
  each by PR, naming its metric (LN3). Those PRs cite the decision, never the scorecard's numbers by role.
- **Privacy:** transcripts, briefs and hook logs are read locally and only their totals reach the scorecard.

## Building it

Done, then next, then the candidates. A candidate row is built only as the [core metrics](#the-core-metrics) say: when
a decision after a real wave needs one of its metrics, and then only that metric.

| PR | What it adds | Metrics it enables |
|---|---|---|
| Recording | Done: the PR facts block (C3) in the conventions and the developer, fixer and reviewer definitions; `git-gate.py`'s block log (C6); the `Conflicts:` trailer (C4); `should-have-caught` (C12); the owner audit in the lead's routine (C13); the `(claim)` and `Withdrawn:` markers and the owner's ruling format (C2) | All but MN1, MN9, MN10 and those needing C14 |
| Scorecard: summary | Done: `scorecard.py wave <n>`, its window and facts block reader, and the summary; the owner's `scorecard` skill. The cost comes from `agent_report.py`. LN5 and the owner's audit time read "no data" | MN1, MN2, MN3, MN4, MG1, MN11; LN1; LN2 (escalations, own commits) |
| Release flags | Done (`docs/flags.md`, and the flags-on daily run) | MN9, PL8; MN1 with flags on |
| Daily run | Done: the scheduled run on `main` with defaults and with flags on (C11), its suite and flag variable named by each pack | MN1 |
| Scorecard: the rest of the core | Next: the verdicts' rounds and must-fixes by cause (C2), escapes by `should-have-caught` (C12), the audit's findings (C13), and each core metric's trend against the earlier scorecards | RV1, RV2, RV7, MN5; the core's trends; LN3 |
| Candidate: practices | One row per README practice from [Coverage](#coverage-every-practice) | The practices' adherence and effect |
| Candidate: escapes and alerts | Alerts (C10) and the OpenSSF result | MN6, MN7 |
| Candidate: review and build | The rest of the verdicts' markers (C2), sizes against the plan, CI runs (C9) and the hook block log (C6) | RV3–RV6, RV8, RV9, BU1–BU8, BU11, BU12, MG2–MG4, MN8, MN12 |
| Candidate: specs and plans | The project's docs (C5) and their history (C4) | SP1–SP8, PL1–PL8, MN9 |
| Candidate: agent team | Quality by role and model, joined to the dispatch log (C15); the reports' `Live spend:` lines | AG1–AG15; LN5 |
| Candidate: settings and thresholds | The repository settings (C16), the kit's version, and the numbers past a threshold with their actions | MG5, LN4 |
| Candidate: each pack | The code-health command and the test report (C14) | MN10, BU9, BU10 |
