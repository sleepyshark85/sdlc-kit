---
name: plan-wave
description: Plans a wave of work as small, deliverable tasks (one behaviour or one contract each), marks each dark, flagged, switch-on or technical, and writes the plan page for its decomposition review. Use before any building starts on a feature, a phase or a batch of requirements.
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
  first, by PR, into numbered criteria of its own. The task adds only what is its own: how it stays off, a contract
  test, a limit until a later task.
- **Each task names what to read:** the files and sections its developer needs (`Reads:`), never a whole document.
- **Size:** S under about 150 changed production lines, M under about 400. An L is split. Tests are counted apart and
  stay in the same task as the code they cover.
- **Detail goes into boundaries, not internals:** contracts and criteria are exact; class structure is left to the
  developer.

## Off on `main` until switched on

PRs merge as soon as they are approved, and `main` always shows only finished features: the daily run and any demo
use its defaults. An unfinished feature is off on `main` in one of three ways:

| The feature… | Off on `main` by | Kind of its tasks |
|---|---|---|
| Is new code beside the old | **Composition:** not registered, wired into the application or given a command, and a library type stays non-public | Dark |
| Changes old code paths, when 1–3 of *When the feature changes old code* don't fit | **A release flag**, off by default, checked at one point | Flagged |
| Changes a schema or a persisted or shared format | Neither: **expand, then contract**. Data written in a new format stays written, whatever a flag says | Dark (expand), switch-on, technical (contract) |

The **switch-on** task is the feature's release, small and revertible: it wires the feature in, or flips its flag's
default to on. A flag's **removal** task (the flag and the old path deleted) follows within two waves of its
switch-on. The plan PR that plans a flag writes its row in `docs/flags.md` and lists its removal task; the switch-on
and removal tasks update the row's *State*, so no two parallel tasks edit the same row.

A dark or flagged task's PR says "behaviour-neutral with defaults", with evidence, and the reviewer checks it:

| Leak | Rule while the feature is off |
|---|---|
| Existing behaviour edited | No existing test assertion or golden file changes |
| Database schema | Additions only; a removal or change comes after the switch-on (expand, then contract) |
| Persisted or shared formats | Never: they are live once merged, flag or not |
| Registration | Dark: not registered at all, as a registered, unused component can still change behaviour. Flagged: registered only behind its flag, at its one check point, so nothing it adds runs with the flag off |
| Dependencies and startup | Named in the PR, as they run whether the feature is on or not |
| The flag | In `docs/flags.md`, off by default, read at one point; the task's tests cover it off and on |

### When the feature changes old code

Most of "it touches a lot of old code" is restructuring, not new behaviour: separate the two, and the restructuring
merges early because it keeps behaviour. Plan with the first of these that fits:

1. **Preparatory refactor** (technical): reshape the old code so the feature fits, behaviour unchanged. A large one
   is a mechanical PR that names its recipe. It also makes the seam where a flag is checked once.
2. **Parallel change** (expand, migrate, contract): the new shape beside the old, callers moved in small PRs, the old
   shape removed. For contracts, schemas, formats and settings.
3. **Branch by abstraction:** the old behaviour behind a contract, the new one built dark behind the same contract,
   one small task switching over, the old one deleted.
4. **A release flag** at the seam, for new behaviour that must sit in old code paths while it is unfinished.
5. **A visible increment:** a piece useful on its own ships as its own small release, a switch-on of its own, instead
   of being hidden.
6. **Last resort, stacked PRs released together:** each slice still its own reviewed PR, the stack merged as one. The
   plan says why 1–5 don't fit, and the owner approves it.

## Decomposition checklist

- [ ] Each task is deliverable alone, and dark, flagged, switch-on or technical.
- [ ] Each task holds one behaviour or one contract, and its expected size is S or M.
- [ ] Each numbered criterion of the wave's requirements is cited by exactly one task, edge states included.
- [ ] Each task's `Reads:` names files and sections, never a whole document.
- [ ] Each contract another task builds against lands first, with its contract test.
- [ ] Each invariant names the task that starts it.
- [ ] The order works: no task needs one that comes after it.
- [ ] Parallel tasks share no file, docs included.
- [ ] Each feature has exactly one switch-on task, and each flag a removal task within two waves of its switch-on.
- [ ] Each flag has its row in `docs/flags.md`, written by this plan, and each flagged task names it.
- [ ] Each schema or persisted-format change is planned as expand, switch-on, contract.
- [ ] A stacked-PR release says why 1–5 of *When the feature changes old code* don't fit, and has the owner's
  approval.
- [ ] Each change to old behaviour is a switch-on, a visible increment or behind a flag, and the restructuring it
  needs comes first as preparatory refactors.

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
