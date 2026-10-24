---
name: plan-wave
description: Plans a wave of work as small, deliverable tasks (one behaviour or one contract each), marks each dark, switch-on or technical, and writes the plan page for its decomposition review. Use before any building starts on a feature, a phase or a batch of requirements.
argument-hint: "[wave goal]"
---

# Plan a wave

Goal: `$ARGUMENTS`. Small PRs come from small tasks decided here, never from splitting a finished feature.

1. Read the requirements the wave covers (`REQUIREMENTS.md`, or the index and area files of `docs/requirements/`)
   and the architecture sections they touch (`ARCHITECTURE.md`, or `docs/architecture/`). List what the requirements
   leave open, and their open questions, and ask the owner before planning around a guess.
2. Decompose into tasks with the rules below, and write `docs/plan/wave-<n>.md` from `docs/plan/template.md`.
   **Check the split triggers** (`docs/conventions.md`, *Docs grow by splitting*): if a document passes one, or would
   once the wave's tasks land, split it with the `split-docs` skill first, in its own PR, and cite the new files.
3. Check the plan against the [decomposition checklist](#decomposition-checklist).
4. Open the plan's PR (`docs/plan-wave-<n>`) and dispatch a reviewer on it, briefed with the checklist. No task
   starts before the plan merges.

## Tasks

- **A task is deliverable:** it leaves `main` working, is reviewable on its own, and its tests prove its outcome
  without the next task. It may be user-facing or technical (a contract and its test, a refactor that keeps
  behaviour, a port with a fake); a horizontal layer with no user is not one.
- **One behaviour or one contract per task.** A task is the smallest set of acceptance criteria that can be delivered
  alone, plus any enabling task it needs first (a contract, a walking skeleton).
- **Vertical first:** a thin end-to-end path, then tasks that thicken it.
- **Contract first:** when a task introduces a contract that a later task builds against, the contract and its
  contract test are a task of their own, and land first.
- **Invariants are not tasks.** A property test or a bound (no write before its audit entry, at most N concurrent
  runs) starts with the first task that builds the mechanism, and each later task extends it.
- **Acceptance criteria are cited, not copied:** a task lists the requirements' numbered criteria it delivers
  (`AREA-01.2`), so their text lives in one place. A criterion too large for one task is split in the requirements
  first, by PR, into numbered criteria of its own. The task adds only what is its own: how it stays dark, a contract
  test, a limit until a later task.
- **Each task names what to read:** the files and sections its developer needs (`Reads:`), never a whole document.
- **Size:** S under about 150 changed production lines, M under about 400. An L is split. Tests are counted apart and
  stay in the same task as the code they cover.
- **Detail goes into boundaries, not internals:** contracts and criteria are exact; class structure is left to the
  developer.

## Dark until switched on

A feature built over several tasks merges dark. Every task before the last is **dark** and changes no behaviour;
the **switch-on** task wires it in, small and revertible, and is the feature's release. Composition is the switch:
an unfinished feature is not registered, wired into the application or given a command, and a library type stays
non-public, until its switch-on task. Replacing a behaviour uses branch by abstraction: the new implementation behind
the existing contract, a small switch-over task, then the old one deleted.

A dark task's PR says "behaviour-neutral", with evidence, and the reviewer checks it:

| Leak | Rule for a dark task |
|---|---|
| Existing behaviour edited | No existing test assertion or golden file changes |
| Database schema | Additions only; a removal or change comes after the switch-on (expand, then contract) |
| Persisted or shared formats | Never in a dark task: they are live once merged |
| Registration | Not registered at all: a registered, unused component can still change behaviour |
| Dependencies and startup | Named in the PR, as they run whether the feature is on or not |

A feature-flag system waits until something is deployed: without a deployment its gains (canaries, gradual rollout,
a kill switch, per-user targeting) don't apply, and each flag doubles the paths to test. Where wiring is not enough,
a plain setting read once at startup is allowed, with a removal task in the plan.

## Decomposition checklist

- [ ] Each task is deliverable alone, and dark, switch-on or technical.
- [ ] Each task holds one behaviour or one contract, and its expected size is S or M.
- [ ] Each numbered criterion of the wave's requirements is cited by exactly one task, edge states included.
- [ ] Each task's `Reads:` names files and sections, never a whole document.
- [ ] Each contract another task builds against lands first, with its contract test.
- [ ] Each invariant names the task that starts it.
- [ ] The order works: no task needs one that comes after it.
- [ ] Parallel tasks share no file, docs included.
- [ ] Each feature has exactly one switch-on task.

## Example

A feature "tools and audit", once planned as one PR of 2,400 lines:

| Task | Delivers | Kind |
|---|---|---|
| T1 | A tool from a typed function; a call becomes a result; one reply's results in call order. The property test over runs starts | Dark |
| T2 | The schema validator: invalid input becomes an error result | Dark |
| T3 | A failing handler becomes an error result; truncation | Dark |
| T4 | Approval: a denial becomes an error result; an unattended run denies | Dark |
| T5 | The audit recorder: a write whose attempt can't be audited never runs | Dark |
| T6 | Reads overlap, writes don't | Dark |
| T7 | The application registers the tools | Switch-on |
