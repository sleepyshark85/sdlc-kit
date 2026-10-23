# Wave {{n}}: {{goal}}

The `plan-wave` skill fills this page; the plan PR is reviewed for its decomposition before any task starts. One
section per task, in delivery order.

| Task | Outcome | Kind | Depends on | Size |
|---|---|---|---|---|
| T1 | {{…}} | {{dark, switch-on, technical}} | — | {{S, M}} |

## T1: {{outcome, one line}}

- **Delivers:** {{the user-facing or technical outcome}}
- **Requirements:** {{IDs}}
- **Acceptance criteria**, for this task, not the whole feature:
  - {{criterion}} · edge states: {{empty, too large, cancelled, the dependency down…}}
- **Contracts:** introduces {{…}}; uses {{…}}
- **Invariants extended:** {{the property tests this task adds cases to, or none}}
- **Kind:** {{dark (how it stays dark: not wired in, not public, behind the existing contract), switch-on, or
  technical}}
- **Depends on:** {{tasks, or none}}
- **Out of scope:** {{…}}
- **Expected size:** {{S under about 150 changed production lines, M under about 400; L means split it}}
