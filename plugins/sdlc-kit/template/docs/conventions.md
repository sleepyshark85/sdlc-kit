# Conventions

How we build this project with AI agents. The SDLC behind these rules, and why each one exists, is the kit's
[`docs/sdlc.md`](https://github.com/sleepyshark85/sdlc-kit/blob/main/docs/sdlc.md); each language's own rules are in
`docs/languages/`. Where the two disagree, the language's rules win for how code is written, and this page wins for
what the code must do.

## How we work

- **Every change goes through a branch and a pull request** to `main`, docs included. Never push to `main`. A PR
  merges when the reviewer has approved its newest commit, the [required checks](#required-checks) pass, the branch
  is up to date and the review threads are resolved. Branches: `feature/`, `fix/`, `refactor/`, `docs/`, `chore/` or
  `test/` and a slug.
- **Small tasks make small PRs.** Work is planned as tasks of one behaviour or one contract each (the `plan-wave`
  skill), and each task is one PR. A developer who finds a task larger than planned stops and proposes a split.
- **Unfinished work merges, but is off on `main`.** PRs merge once approved, and `main` with its defaults shows only
  finished features, for the daily run and any demo. New code stays unwired until its switch-on task; old code is
  reshaped first (a refactor, a parallel change, branch by abstraction), and only what still has to sit in old code
  paths goes behind a release flag, off by default and listed in `docs/flags.md`; a schema or format change goes
  expand, then contract. Every task before the switch-on is behaviour-neutral with the defaults, and says so in
  its PR (`plan-wave`, *Off on `main` until switched on*).
- **One change per PR.** A mechanical change (rename, move, reformat) is its own PR and names the command that made it.
- **Hooks enforce the mechanical rules** (the plugin's `git-gate.py`, with this project's `.sdlc/checks.toml`): no
  commit on `main` or push to it, branch prefixes, staged files before a commit, no force push, merges only with
  `--auto`, no change to the repository's settings, the reviewer never commits, only the reviewer posts verdicts, and
  each component's checks before a commit and a push. A blocked action says why; fix the cause, never work around it.
- **The simplest thing that works.** Build only what the task's acceptance criteria need: no abstraction without a
  current user, no setting without a known case, no optimization without a measured target.
- **Short docs:** tables and diagrams over prose; cite requirement IDs instead of restating them. The architecture
  names no type or API.
- **Docs grow by splitting.** The requirements and the architecture start in their short forms (`REQUIREMENTS.md`,
  `ARCHITECTURE.md`). The lead moves one into its full form, req42's `docs/requirements/` or arc42's
  `docs/architecture/` with a file per area or subsystem, with the `split-docs` skill in a PR of its own, when any
  of these holds:

  | Trigger | Requirements | Architecture |
  |---|---|---|
  | Length | Over about 300 lines | Over about 300 lines |
  | Breadth | A fourth area (ID prefix) | A component with components of its own (a subsystem) |
  | Contention | Two parallel tasks of a wave would edit it | Two parallel tasks of a wave would edit it |

  Once split, a document stays split, and agents read the index and then only the files their task names.
- **Short code comments:** say what the code cannot, briefly; no requirement IDs (test names carry them).
- **Who codes and reviews:** the plugin's agents. `developer` (Opus) for tasks and anything risky, `fixer` (Sonnet)
  only for small, well-bounded fixes, `reviewer` (Opus) for every PR. **Each PR gets a new reviewer**, kept for that
  PR's rounds only; at most 3 rounds, then the owner decides. The lead writes every brief with the `dispatch` skill.
- **Every PR description has an *Assumptions* section:** each point the spec left open, the choice made and why, or
  "none". The reviewer checks each against the requirements.
- **A process change names its metric:** a PR that changes agents, skills, hooks or these conventions says which
  scorecard metric it should move, and the next scorecard keeps or reverts it.
- **Every PR description ends with its facts block,** which the scorecard reads and GitHub renders as nothing. Each
  line holds what only the author knows; the reviewer checks it against the diff, and a wrong or missing line is a
  `[process]` must-fix. The block, with an example value on each line:

  ```text
  <!-- sdlc
  task: W3-T2
  kind: dark
  planned: S
  criteria: API-01.2, API-01.3
  reads: docs/requirements/api.md; ARCHITECTURE §3
  metric: rework rate
  escaped-from: #41
  should-have-caught: criteria
  -->
  ```

  | Line | Holds |
  |---|---|
  | `task` | The plan's task, or `none` |
  | `kind` | `dark`, `flagged`, `switch-on`, `technical`, `fix`, `docs` or `process` |
  | `planned` | The plan's size, or `none` |
  | `criteria` | The numbered criteria it delivers, or `none` |
  | `reads` | What its developer read: the task's `Reads:` line |
  | `metric` | A process change only: the metric it should move |
  | `escaped-from` | A fix of merged code only: the PR that introduced the defect |
  | `should-have-caught` | With `escaped-from`: `criteria`, `tests`, `mutation`, `review`, `design`, `threat-model` or `none` |

- **A merge that resolves conflicts says which files:** its commit message ends with `Conflicts: <file>, <file>`.

## Required checks

Branch protection on `main` (applied by `scripts/setup-repo.sh`) requires these, and the branch to be up to date:

| Workflow | Check |
|---|---|
| `.github/workflows/review.yml` | `review`: an approval naming the PR's newest commit, as *The review gate* below says |
| `.github/workflows/quality.yml` | `quality`: the tooling's tests and the docs' links |
| `.github/workflows/codeql.yml` | `codeql (<language>)`, one per row of its matrix |
| Each language pack's workflows | Listed in `docs/decisions.md` |

- **The review gate** (`.github/review_gate.py`) passes when the newest verdict naming the PR's newest commit is
  `**Verdict: APPROVE** at <that full sha>`, posted by a trusted author: the logins in the `REVIEWERS` repository
  variable, which holds the reviewer agent's identity only. The other agents post as the owner, so the owner's login
  is not trusted: an owner who approves by hand posts with the reviewer identity. An approval carries over clean
  merges of `main` into the PR; anything else waits for a new verdict. The script's docstring has the exact rule.
- **A component's CI runs only when the PR changes it** (`.github/changes.py`); its jobs are skipped otherwise, which
  a required check counts as passing. Never add a path filter: a required check that never reports blocks the merge.

## Tests

- **Tests replace only system boundaries:** external services and models, the network, the clock, environment and
  secrets, the human, storage where a real one is impractical. Everything inside the project is tested with real
  objects; prefer a real database in a container over a fake.
- **Fast and deterministic:** a flaky test, or one over a second offline, is a bug to fix, never something to retry.
- **Test names carry the requirement ID** they check, with the criterion's number where a test checks one
  (`API_01_2_…`), and `docs/traceability.md` maps them (each area file's *Traceability* section, once the
  requirements are split).
- **Every parser and validator has generated-input tests** (property or fuzz tests); a failure prints its seed.
- **Golden files change only on purpose**, through an explicit update flag, and the diff is reviewed like code.
- **A new test earns its place:** it kills a mutant that survives without it, or pins an acceptance criterion.

## Code quality bar

**The bar is good code, not working code.** The reviewer applies it to every changed line as its next maintainer
would read it; anything below is a must-fix, however correct the code is.

| Area | Must-fix |
|---|---|
| Names and comments | A name that doesn't say what a thing is or does; a comment that restates the code, or code so unclear it needs one |
| Structure | Duplication; a function doing more than one thing; deep nesting; a long parameter list; a lint or analyzer rule suppressed to let any of these through |
| Literals | A string the code depends on spelled inline instead of named once: a command, a name or value of an external system (a header, an environment variable, a response field), a persisted key, or any repeated string. A test spells what it expects itself |
| API and contracts | A public item that could be private, or one without a doc comment; a contract of more than three members without a reason; a contract with one implementation and no consumer that swaps it |
| Errors | Handling an error twice (returning and logging it); catching too broadly; swallowing an error or losing its cause; a bug turned into a silent default; a permanent failure treated as transient |
| Concurrency and resources | A thread or task without an owner that waits for it and can stop it; shared mutable state not guarded by its owner; a queue without a known bound; a resource not released on every path |
| Security and data | A secret in code or committed config; external input used before it is validated at the boundary; a query that isn't parameterized; a secret or personal data reaching logs, errors or telemetry |
| Observability | A new path without the logs, traces and metrics the requirements name; a log level that doesn't fit the event |
| Performance and bounds | Unbounded growth (collection, queue, retry, pagination); I/O without a timeout or cancellation; queries in a loop; a new query on an unindexed column |
| Dependencies | A new dependency without a line in `docs/decisions.md` saying why the standard library is not enough, its licence, and that it is maintained |
| Idiom and size | Code that fights the language's idiom; a workaround larger than its problem; an abstraction or option without a current user |
| PR scope | More than one change in a PR; a lock or generated file that doesn't match its source; a dark or flagged PR that changes behaviour with the defaults; a flag not in `docs/flags.md`, checked in more than one place, or past its removal task |
| Tests | A test that would pass with the behaviour broken; an error test that doesn't pin which failure it is; logic deciding what a test asserts (case tables and property tests are welcome) |
| Mutation | A surviving mutant in the changed code: kill it, delete what makes it equivalent, or show in the PR why it is equivalent |

- **"It works" or "a reviewer accepted it before" never approves** code the reviewer would not write.
- **A rule turned off needs a reason the reviewer agrees with**, on the line that turns it off.
- **Claims are reproduced, not trusted:** a constraint an agent reports becomes a rule only once it is shown.
- **Nits are true trivia** and never block; everything in the table is a must-fix.
- **Each must-fix carries one cause label:** `[tests]`, `[quality]`, `[bug]`, `[contract]`, `[ac]` or `[process]`.

## Design rules

The project's own rules that code must keep: layers, data flow, runtime model, and what must never happen. A change
to one changes the architecture first.

- *(Add the project's design rules here as it grows.)*
