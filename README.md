# sdlc-kit

An SDLC for building software with AI agents, packaged for new projects: a Claude Code plugin (agents, skills,
hooks) and the project template it scaffolds (requirements and architecture skeletons, conventions, CI, the review
gate, repository settings), with language packs. Its practices come from the
[Officina](https://github.com/sleepyshark85/officina) project, where they were found and measured, and from industry
practice (DORA, NIST SSDF, OWASP, OpenSSF).

- **The process:** [`docs/sdlc.md`](docs/sdlc.md): the premise, roles, flow, guards and measures.
- **What is measured, and how:** [`docs/measuring.md`](docs/measuring.md): each practice's metrics by phase, their
  collectors, and the agent team's activity, cost and quality.
- **The rules agents follow:** the template's [`docs/conventions.md`](plugins/sdlc-kit/template/docs/conventions.md).

## Getting started

1. Install the plugin in Claude Code:
   `/plugin marketplace add sleepyshark85/sdlc-kit`, then `/plugin install sdlc-kit@sdlc-kit`.
2. Start a project: `/sdlc-kit:new-project <folder> <name> dotnet`. The skill scaffolds it, fills the requirements
   and architecture with you, and gives you the steps only you can take: the first commit, the reviewer's GitHub
   identity, and `scripts/setup-repo.sh` for the repository settings.
3. Plan the first wave: `/sdlc-kit:plan-wave <goal>`. Then the main session dispatches each task with
   `/sdlc-kit:dispatch`.

Prerequisites: Claude Code, the GitHub CLI, Git 2.39 or later (for the review gate), Python 3.11 or later, and each
pack's tools (the .NET SDK for `dotnet`).

## Structure

```text
.claude-plugin/marketplace.json     the marketplace: this repository serves the plugin below
docs/sdlc.md                        the SDLC: premise, roles, flow, guards, measures, how the process changes
docs/measuring.md                   every metric by phase and practice, its collector, and what it tells
plugins/sdlc-kit/
  .claude-plugin/plugin.json        the plugin's name and version; projects update with the plugin
  agents/
    developer.md                    builds one task, self-checks, opens the PR (Opus)
    fixer.md                        small, bounded fixes and merge conflicts (Sonnet)
    reviewer.md                     judges a PR, posts the verdict the gate reads, never commits (Opus)
  skills/
    dispatch/                       the lead's briefs (developer, fix, review, merge-check), agent rules, lead's routine
    plan-wave/                      tasks of one behaviour or contract (dark, flagged, switch-on, technical), checklist
    new-project/                    scaffolds a project and walks the owner through their steps
    split-docs/                     grows the short requirements or architecture into full req42 or arc42 (templates/)
  hooks/
    hooks.json                      wires the two hooks into every session that has the plugin
    git-gate.py                     git and GitHub rules, and the project's checks before a commit and a push,
                                    in a repository with .sdlc/checks.toml
    context-size.py                 logs each agent's context size; warns at 150k and 300k tokens
    tests/
  scripts/
    new_project.py                  creates a project from the template; adds packs
    tests/
  template/                         copied into a new project
    CLAUDE.md                       the project's working notes; imports the conventions
    README.md                       the project's readme skeleton
    REQUIREMENTS.md                 short req42: requirements with IDs and EARS criteria, quality, glossary, questions
    ARCHITECTURE.md                 short arc42: components, contracts, flows, runtime and threat model; no code
    docs/conventions.md             how we work (split triggers included), required checks, tests, the bar, design rules
    docs/decisions.md               design and platform decisions, dependencies, required checks, mutation floors
    docs/traceability.md            requirement → tests
    docs/flags.md                   the release flags of unfinished features, with their removal tasks
    docs/plan/template.md           a wave's plan: one section per task
    .sdlc/checks.toml               components, their paths and checks (read by the hook and changes.py)
    .sdlc/sdlc_paths.py             which component a path belongs to; shared by the hook and changes.py
    .claude/settings.json           permission rules: read-only commands allowed, destructive ones denied
    .github/
      review_gate.py                the review gate: a verdict naming the newest commit, from a trusted login
      changes.py                    which component a PR changes; docs-only PRs skip the builds
      links.py                      checks the Markdown's relative links and anchors
      workflow_rules.py             every workflow: top-level permissions, actions pinned by commit sha
      test_*.py                     the tooling's tests, run by the quality workflow
      dependabot.yml                weekly updates of the pinned actions (and each pack's ecosystem)
      workflows/                    review, quality, codeql, scorecard
    scripts/setup-repo.sh           branch protection, merge settings, REVIEWERS, secret scanning (the owner runs it)
  packs/
    dotnet/
      pack.toml                     what the pack registers: component, CodeQL language, Dependabot, hook, checks
      files/                        copied over the project: dotnet/ build files, docs/languages/dotnet.md,
                                    .NET and mutation workflows, the survivors summary, the C# file-rules hook
                                    and its tests (.github/test_cs_rules.py)
.github/workflows/                  the kit's own CI (kit.yml) and review gate (review.yml)
.sdlc/checks.toml                   the kit follows its own git rules (branch prefixes; no components)
```

## Best practices and where the kit covers them

Each practice, the industry source or reason behind it, the parts of the kit that cover it, and its status:

- **Enforced:** a hook, check or script fails without it.
- **Reported:** a scheduled job measures it; nothing fails.
- **Guided:** an agent definition, skill or template asks for it, and the reviewer checks it.
- **Trial:** a practice not yet proven by a project's metrics; [`docs/sdlc.md`](docs/sdlc.md#changing-the-process)
  says how it is kept or dropped.
- **Planned:** not in this version; see [Planned](#planned).

### 1. Requirements and plan

| Practice | Why | Covered by | Status |
|---|---|---|---|
| Spec before code, reviewed like code | Spec-driven development (GitHub Spec Kit, Kiro): the spec is what agents build from | `template/REQUIREMENTS.md`, `template/ARCHITECTURE.md`; conventions *How we work* (docs through PRs); `new-project` step 2 | Guided |
| Structured, testable requirements with edge states | EARS: each criterion maps to a test | `template/REQUIREMENTS.md` §2; `split-docs` area template | Guided |
| Criteria numbered once, cited by tasks | A criterion restated in a plan drifts from its requirement, and coverage can't be checked | `template/REQUIREMENTS.md` §2 (`AREA-01.2`); `plan-wave` *Tasks* and checklist; `template/docs/plan/template.md` (`Reads:`) | Trial |
| Docs sized to the project: short forms, split by trigger into req42 and arc42 | A long single spec costs every agent context, and parallel tasks collide on it | `template/REQUIREMENTS.md`, `template/ARCHITECTURE.md` (short forms); conventions *Docs grow by splitting*; `split-docs`; `plan-wave` step 2; `cs-rules.py` reads both forms | Trial |
| Traceability: every requirement has an ID, every test names it | A requirement without a test shows up | conventions *Tests*; `template/docs/traceability.md` (each area file's section once split); `developer` step 5 | Guided |
| Ambiguity surfaced, not filled | Agents fill gaps silently and plausibly | *Assumptions* section: `developer` step 8, `reviewer` check 3, conventions; `plan-wave` step 1 | Trial |
| Small, deliverable tasks of one behaviour or contract | Small batches (DORA); review cost grows faster than size | `plan-wave` *Tasks*; `template/docs/plan/template.md`; `dispatch` check *The task*; `developer` step 4 (stop and split) | Trial |
| The plan's decomposition reviewed before building | Shared criteria left unowned when a feature is split late | `plan-wave` steps 3–4 and *Decomposition checklist* | Trial |

### 2. Design

| Practice | Why | Covered by | Status |
|---|---|---|---|
| Decision records | Decisions outlive the people and sessions that made them | `template/docs/decisions.md` (arc42 §9), the one place for them | Guided |
| Language-neutral architecture (concepts, contracts, flows) | One design, any implementation; code-level views drift | `template/ARCHITECTURE.md` (arc42); conventions *Short docs*; `reviewer` check 8 | Guided |
| Contract first at task seams | Parallel agents each invent their side of a seam | `plan-wave` *Contract first*; `template/ARCHITECTURE.md` §3 | Guided |
| Fitness functions: architecture rules as tests | A design rule erodes silently without a check | `template/ARCHITECTURE.md` §2 (a dependency test); .NET pack: `PublicApiAnalyzers` | Guided |
| Threat model, LLM threats included | OWASP Top 10 for LLM Applications, OWASP agentic guidance | `template/ARCHITECTURE.md` §6 (full form: `concepts.md` §8.2); `reviewer` check 5 | Guided |

### 3. Coding

| Practice | Why | Covered by | Status |
|---|---|---|---|
| Context files and templates for agents | Every agent starts cold | `template/CLAUDE.md`, conventions, `docs/languages/`; the `dispatch` skill's templates | Guided |
| One change per PR; mechanical changes on their own | Reviewable diffs; a rename re-run instead of read | conventions *How we work*; quality bar *PR scope* | Guided |
| Mechanical rules are tools, not reviews | Review capacity is the bottleneck | `git-gate.py` with `.sdlc/checks.toml`; .NET pack: warnings as errors, analyzers, `.editorconfig`, `cs-rules.py`, `dotnet format` | Enforced |
| The developer self-checks before review | Cheaper than a review round | `developer` step 6 (mutation on the diff, diff re-read, base merged) | Guided |
| The code quality bar: good code, not working code | AI code is plausible and subtly wrong | conventions *Code quality bar*; `reviewer` check 6 | Guided |
| Least privilege for agents | The coding agent is an attack surface | `template/.claude/settings.json` (deny rules); `git-gate.py`: no force push, no branch deletion, merge only with `--auto`, no repository settings | Enforced |
| Unfinished work merges but is off on `main`; one switch-on task releases it | Trunk-based small PRs; `main` shows only finished features for the daily run and demos | `plan-wave` *Off on `main` until switched on* (composition, release flags, expand then contract); `developer` step 3; `reviewer` check 4; quality bar *PR scope*; `dotnet.md` (composition and the `Flags` class) | Trial |
| Release flags bounded: listed, off by default, one check point, removed within two waves of the switch-on | Flags are cheap to add and costly to keep; each doubles the paths to test | `template/docs/flags.md`; `plan-wave` (the leak table, removal tasks, checklist); quality bar *PR scope*; `reviewer` check 4 | Trial |
| Old code reshaped before the feature: preparatory refactor, parallel change, branch by abstraction | A feature that touches much old code merges in small PRs only once restructuring is apart from behaviour | `plan-wave` *When the feature changes old code*; `reviewer` check 4 (a refactor keeps behaviour) | Trial |
| AI authorship visible, a person accountable | Accountability stays with a person | `developer` step 8 (attribution line); owner decides after round 3 | Guided |

### 4. Security

| Practice | Why | Covered by | Status |
|---|---|---|---|
| Static analysis on every PR and weekly | NIST SSDF | `template/.github/workflows/codeql.yml`; each pack's language row | Enforced |
| Dependency vulnerabilities | NIST SSDF | `template/.github/dependabot.yml`; .NET pack `dotnet-quality` (vulnerable packages, weekly too) | Enforced |
| Secret scanning with push protection, non-provider patterns, validity checks | Secrets leak through agents too | `scripts/setup-repo.sh` | Enforced (once run) |
| New dependencies justified | Package hallucination (slopsquatting) | quality bar *Dependencies*; `docs/decisions.md` *Dependencies* | Guided |
| Least-privilege workflow tokens | OpenSSF Scorecard | every workflow's top-level `permissions`, checked by `workflow_rules.py` in the `quality` workflow | Enforced |
| Actions pinned by commit sha, kept current | OpenSSF Scorecard, SLSA | every workflow, checked by `workflow_rules.py`; `dependabot.yml` (`github-actions`) | Enforced |
| OpenSSF Scorecard | Supply-chain hygiene, measured | `template/.github/workflows/scorecard.yml` | Reported |
| Locked dependency restores | Reproducible builds | .NET pack: `RestorePackagesWithLockFile`, `--locked-mode` in CI | Enforced |
| SBOM and build provenance | SLSA | — | Planned |

### 5. Testing

| Practice | Why | Covered by | Status |
|---|---|---|---|
| Only boundaries faked; fast, deterministic tests | Tests are the agent's check on its own work | conventions *Tests* | Guided |
| Mutation testing on each PR's changed code | Google's diff-scoped mutation; a weak test passes review otherwise | .NET pack `dotnet-mutation.yml`; `developer` step 6; quality bar *Mutation* | Enforced |
| Survivors visible on the PR | Agents fix what they can see | .NET pack `stryker_survivors.py` → job summary | Enforced |
| Full mutation runs held to a floor | A floor that only reports erodes | .NET pack: weekly run fails below `break`; floors in `docs/decisions.md` | Enforced |
| Property and fuzz tests for parsers and validators | They find what examples miss | conventions *Tests* | Guided |
| Generated tests kept only if they kill a mutant or pin a criterion | Meta's TestGen-LLM and mutation-guided generation | conventions *Tests*; `developer` step 6 | Guided |
| Flaky tests found, not retried | A flaky test is a bug | .NET pack `dotnet-flaky` (weekly, five runs, two systems) | Enforced |
| Golden files change only on purpose | Silent regeneration hides regressions | conventions *Tests* | Guided |

### 6. Merge and release

| Practice | Why | Covered by | Status |
|---|---|---|---|
| Protected trunk: required checks, up to date, admins included | Trunk-based development | `scripts/setup-repo.sh`; conventions *Required checks* | Enforced |
| Approval pinned to the exact commit | A later commit needs its own review | `review_gate.py`, `review.yml` (clean merges of `main` carry over) | Enforced |
| Independent review: a fresh reviewer per PR, its own identity | A model reviewing a model shares its blind spots; an agent must not approve itself | `reviewer`; `REVIEWERS` in `review_gate.py`; `git-gate.py` (only the reviewer posts verdicts, uses `SDLC_REVIEWER_TOKEN` or prints the environment; the reviewer never commits); `setup-repo.sh` trusts the reviewer login only, as the other agents post as the owner | Trial |
| Briefs carry facts, not conclusions | An agent handed a hypothesis tends to confirm it | `dispatch` check *Facts, not conclusions*; review template; `reviewer` | Trial |
| Bounded review: three rounds, then the owner | Endless rounds hide a disagreement | `reviewer` *The verdict*; `dispatch` (`owner-decision` label) | Guided |
| Merge only when the checks pass; merge commits only | No merge around the gate | `git-gate.py` (`gh pr merge --auto` only); `setup-repo.sh` | Enforced |
| CI scoped to the change; docs-only PRs skip builds | Verification capacity spent where it matters | `changes.py`; each workflow's `changes` job (never a path filter) | Enforced |
| Docs' links checked | Docs are the agents' input | `links.py` in the `quality` workflow | Enforced |
| Semantic versions, API compatibility check | Library releases | .NET pack `PublicApiAnalyzers` (the public surface in the diff); the rest is planned | Planned |

### 7. The AI process itself

| Practice | Why | Covered by | Status |
|---|---|---|---|
| A clear AI policy: roles, models, autonomy | DORA 2025: the first capability that makes AI pay off | `docs/sdlc.md` *Roles*; conventions *Who codes and reviews*; agents' `model` | Guided |
| Instructions versioned and released | The written process is code | this plugin (`plugin.json` version, bumped by hand when a change should reach projects); changes by PR | Guided |
| Each process change names the metric it should move | Instructions are evaluated, not judged by impression | conventions *How we work*; `dispatch` lead's routine; `docs/sdlc.md` | Trial |
| Context budget per agent | Context is a hidden cost; recall drops as it grows | `context-size.py` (warns at 150k and 300k); `dispatch` (resume only under the warning) | Guided |
| The lead reads reports, not diffs | The lead's context is the costliest | `dispatch` *Lead's routine*; `agent-rules.md` *Report* | Guided |
| A cause on every must-fix | Rework measured by cause, by script | `reviewer` *The verdict*; conventions *Code quality bar* | Guided |
| Escaped defects traced to their PR | Change failure rate | `fixer` (`Escaped from: #n`) | Guided |
| Scorecard: cost, flow, quality and people per wave | Throughput alone inflates with AI | [`docs/measuring.md`](docs/measuring.md) (the metrics and collectors); the conventions above; the collectors and the script are planned | Planned |
| The agent team measured by role and model: activity, cost, quality | Choosing each role's model and instructions on evidence | [`docs/measuring.md`](docs/measuring.md#the-agent-team); the dispatch log and the script are planned | Planned |

### 8. Products that run a model

| Practice | Why | Covered by | Status |
|---|---|---|---|
| Threat model against the OWASP LLM Top 10 | Prompt injection through tool results and data | `template/ARCHITECTURE.md` §6 | Guided |
| Evals, OpenTelemetry generative-AI telemetry, red teaming, model change as a release | LLMOps | — | Planned |

## Planned

- **The scorecard:** the collectors [`docs/measuring.md`](docs/measuring.md#building-it) lists as new, then a script
  that reads them per wave: a port of Officina's `sdlc-metrics.py` and `agent-usage.py`, made generic.
- **A `sync` skill** that shows how a project's copied template files differ from the kit's current version.
- **More packs:** Go and Ruby (from Officina's implementations), with their mutation tools.
- **Releases:** semantic versions, API compatibility checks, SBOM and provenance, per pack.
- **An `llm` pack:** evals, generative-AI telemetry conventions, injection tests, model changes as releases.

## Developing the kit

See [`CLAUDE.md`](CLAUDE.md): every change by pull request, generic content only, this README's table updated with
each practice change, and the tests in `.github/workflows/kit.yml` green.
