<!-- Structure after req42 (https://req42.de). -->
# {{AREA}}: {{area name}}

The requirements of one area (req42 §4), and the tests that check them. {{What the area covers, in a line.}}

## Requirements

Each in an EARS pattern: "The system shall …", "When …", "While …", "If …, then …" (the edge states: empty, too
large, cancelled, the dependency down) or "Where …". Each requirement's acceptance criteria are numbered (`.1`,
`.2`…), and a task in the plan cites them as `AREA-01.2`.

| ID | Requirement | Acceptance criteria |
|---|---|---|
| {{AREA-01}} | {{When …, the system shall …}} | {{.1 an observable outcome · .2 an edge state: …}} |

## Models

{{This area's own domain model or process, or "n/a".}}

## Traceability

Test names carry the requirement ID; a requirement without a test shows up as an empty row.

| Requirement | Tests |
|---|---|
| {{AREA-01}} | {{…}} |
