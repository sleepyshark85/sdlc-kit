# Requirements

What {{project}} must do, language-neutral. Each requirement has an ID (`AREA-nn`) that tests carry in their names,
and acceptance criteria a test can check. How it is built is in `ARCHITECTURE.md`; who builds it when is in
`docs/plan/`; the decisions taken are in `docs/decisions.md`.

This is the short form of [req42](https://req42.de). When it passes a split trigger (`docs/conventions.md`, *Docs
grow by splitting*), the `split-docs` skill moves it into the full structure under `docs/requirements/`.

## 1. Purpose and scope

- **Goal:** {{the problem it solves, in one or two sentences}}
- **Users and stakeholders:** {{who uses it, who else has a stake, and what each expects}}
- **In scope:** {{…}} · **Out of scope:** {{…}}
- **Constraints:** {{what is fixed from outside: platform, regulation, deadline, an existing system}}

## 2. Requirements

One row per requirement, grouped by area (the ID's prefix). Write each in an [EARS](https://alistairmavin.com/ears/)
pattern so a test can decide it, and name its edge states instead of leaving them to the implementer. Number each
requirement's acceptance criteria (`.1`, `.2`…): a task in the plan cites `AREA-01.2` instead of restating it.

| Pattern | Form |
|---|---|
| Always | The system shall … |
| Event | When …, the system shall … |
| State | While …, the system shall … |
| Unwanted | If …, then the system shall … (the edge states: empty, too large, cancelled, the dependency down) |
| Optional | Where …, the system shall … |

| ID | Requirement | Acceptance criteria |
|---|---|---|
| {{AREA-01}} | {{When …, the system shall …}} | {{.1 an observable outcome · .2 an edge state: …}} |

## 3. Quality requirements

Each measurable, grouped by quality characteristic (security, reliability, performance, observability…).

| ID | Requirement | Acceptance criteria |
|---|---|---|
| {{SEC-01}} | {{External input is validated at the boundary before use}} | {{.1 …}} |
| {{OBS-01}} | {{Each request emits a trace with …}} | {{.1 …}} |

## 4. Glossary

The domain's terms, used in this sense everywhere: in the docs, the code and the tests.

| Term | Meaning | Not to be confused with |
|---|---|---|
| {{…}} | {{…}} | {{…}} |

## 5. Open questions and assumptions

What the owner has not decided yet. A task that depends on an open question waits for its answer.

| # | Question or assumption | Owner's answer |
|---|---|---|
| Q1 | {{…}} | {{open}} |
