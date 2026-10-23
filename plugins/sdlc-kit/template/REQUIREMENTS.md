# Requirements

What {{project}} must do, language-neutral. Each requirement has an ID (`AREA-nn`) that tests carry in their names,
and acceptance criteria a test can check. How it is built is in `ARCHITECTURE.md`; who builds it when is in
`docs/plan/`.

## 1. Purpose and users

{{Who it is for, the problem it solves, and what is out of scope.}}

## 2. Requirements

Write each so a test can decide it: a trigger and a response ("When X, the system shall Y"), or Given/When/Then. Name
the edge states (empty, too large, cancelled, the dependency down) instead of leaving them to the implementer.

| ID | Requirement | Acceptance criteria |
|---|---|---|
| {{AREA-01}} | {{When …, the system shall …}} | {{Observable outcomes, edge states included}} |

## 3. Quality requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| {{SEC-01}} | {{External input is validated at the boundary before use}} | {{…}} |
| {{OBS-01}} | {{Each request emits a trace with …}} | {{…}} |

## 4. Decisions

| # | Decision | Why | Date |
|---|---|---|---|
| D1 | {{…}} | {{…}} | {{…}} |
