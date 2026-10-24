# Wave {{n}}: {{goal}}

The `plan-wave` skill fills this page; the plan PR is reviewed for its decomposition before any task starts. One
section per task, in delivery order.

| Task | Outcome | Kind | Depends on | Size |
|---|---|---|---|---|
| T1 | {{…}} | {{dark, flagged, switch-on, technical}} | — | {{S, M}} |

## T1: {{outcome, one line}}

- **Delivers:** {{the user-facing or technical outcome}}
- **Requirements:** {{IDs}}
- **Reads:** {{the files and sections the developer reads, e.g. "REQUIREMENTS §2 API; ARCHITECTURE §3" or
  "docs/requirements/api.md; docs/architecture/orders.md"}}
- **Acceptance criteria:** {{the requirements' criteria this task delivers, by number: AREA-01.1, AREA-01.2}}
  - {{only what this task adds of its own: how it stays off, a contract test, a limit until a later task}}
- **Contracts:** introduces {{…}}; uses {{…}}
- **Invariants extended:** {{the property tests this task adds cases to, or none}}
- **Kind:** {{dark (how it stays off: not wired in, not public, behind the existing contract), flagged (its flag
  in `docs/flags.md`), switch-on (wires it in or flips the default), or technical (a refactor or a flag's
  removal)}}
- **Depends on:** {{tasks, or none}}
- **Out of scope:** {{…}}
- **Expected size:** {{S under about 150 changed production lines, M under about 400; L means split it}}
