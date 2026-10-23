# Decisions

The platform decisions of {{project}}: languages, frameworks, dependencies and the checks each adds. Requirement-level
decisions are in `REQUIREMENTS.md` §4.

## Platform

| # | Decision | Why | Date |
|---|---|---|---|
| P1 | {{…}} | {{…}} | {{…}} |

## Dependencies

Every dependency, as the quality bar's *Dependencies* row asks.

| Dependency | Why the standard library is not enough | Licence | Maintained (latest release) |
|---|---|---|---|
| {{…}} | {{…}} | {{…}} | {{…}} |

## Required checks

The template's (`review`, `quality`, `codeql (actions)`) plus each pack's; `scripts/setup-repo.sh` takes the pack's
as arguments.

| Workflow | Check | Added by |
|---|---|---|
| {{…}} | {{…}} | {{…}} |

## Mutation floors

| Package | Floor | Why this number |
|---|---|---|
| {{…}} | {{…}} | {{…}} |
