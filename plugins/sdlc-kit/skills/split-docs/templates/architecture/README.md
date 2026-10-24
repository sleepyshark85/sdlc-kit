# Architecture

The concepts, subsystems, contracts and flows of the project, language-neutral, in [arc42](https://arc42.org)'s
structure; the section numbers are arc42's. **No code, type, package or API names here.** This page is the index and
the system-wide view; each subsystem has its own file, and the crosscutting concepts are in `concepts.md`. A change to
a shared rule changes these pages first.

## 1. Introduction and goals

The top quality goals, each citing its quality requirement ID:

| Goal | Requirement |
|---|---|
| {{…}} | {{SEC-01}} |

## 2. Constraints

In the requirements, §7.

## 3. Context and scope

{{The system, its users and the external systems it talks to, with the channel each uses; a diagram if it helps.}}

## 4. Solution strategy

{{The few choices that shape everything else, each in a line, with its decision in `docs/decisions.md`.}}

## 5. Building blocks, level 1

| Subsystem | Responsibility | Depends on | File |
|---|---|---|---|
| {{…}} | {{…}} | {{…}} | {{`orders.md`}} |

The dependency rule: {{which subsystem or layer may depend on which}}. A dependency test enforces it.

Contracts between subsystems: each one's operations, their inputs and outputs, and their failure modes. A contract
that a later task builds against lands first, with its contract test (the `plan-wave` skill's contract-first rule).

## 6. Runtime view

{{The flows that cross subsystems, step by step, failure and cancellation included. A flow inside one subsystem goes in
its file.}}

## 7. Deployment view

{{Where it runs: environments, nodes, what is deployed where, and how it is configured; "n/a" until something is
deployed.}}

## 8. Crosscutting concepts

In `concepts.md`: the runtime model, the threat model and the other concepts every subsystem follows.

## 9. Architecture decisions

In `docs/decisions.md`.

## 10. Quality requirements

The quality requirements are in the requirements' `quality.md`. The scenarios below show how the architecture meets
the goals in §1:

| Scenario | Requirement | How the architecture meets it |
|---|---|---|
| {{…}} | {{…}} | {{…}} |

## 11. Risks and technical debt

| Risk or debt | Effect | What we do about it |
|---|---|---|
| {{…}} | {{…}} | {{…}} |

## 12. Glossary

In the requirements' `glossary.md`.
