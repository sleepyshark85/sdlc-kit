# Architecture

The concepts, components, contracts and flows of {{project}}, language-neutral: **no code, type, package or API names
here.** Implementation detail lives in the code and its comments, and each language's design notes map these sections
to their mechanisms. A change to a shared rule changes this page first; decisions are in `docs/decisions.md`.

This is the short form of [arc42](https://arc42.org) (by Gernot Starke and Peter Hruschka, CC BY-SA 4.0). When it
passes a split trigger (`docs/conventions.md`, *Docs grow by splitting*), the `split-docs` skill moves it into the full
structure under `docs/architecture/`, which adds the deployment view once something is deployed.

## 1. Context and goals

{{The system, its users and the external systems it talks to; a diagram if it helps.}}

- **Quality goals:** {{the top three, each citing its quality requirement ID}}
- **Strategy:** {{the few choices that shape everything else, each in a line}}

## 2. Components and layers

| Component | Responsibility | Depends on |
|---|---|---|
| {{…}} | {{…}} | {{…}} |

The dependency rule: {{which layer may depend on which}}. A dependency test enforces it.

## 3. Contracts

Each contract between components: its operations, their inputs and outputs, and their failure modes. A contract that
a later task builds against lands first, with its contract test (the `plan-wave` skill's contract-first rule).

## 4. Flows

{{The main flows, step by step: request handling, background work, failure and cancellation.}}

## 5. Runtime model

Concurrency, cancellation, timeouts, persistence points and event order, each with the rule every implementation
keeps.

## 6. Threat model

Each untrusted input, what it could make the system do, and the rule that stops it. Each mitigation names its test.

| Input | Threat | Mitigation | Test |
|---|---|---|---|
| {{User input}} | {{Injection}} | {{Validated at the boundary; parameterized queries}} | {{…}} |

For a system that runs a language model, add a row for each OWASP Top 10 for LLM Applications category that applies
(prompt injection, sensitive information disclosure, excessive agency, improper output handling, unbounded
consumption…) and say why the others don't.

## 7. Risks and technical debt

| Risk or debt | Effect | What we do about it |
|---|---|---|
| {{…}} | {{…}} | {{…}} |
