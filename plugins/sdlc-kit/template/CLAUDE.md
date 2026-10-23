# {{project}} — working notes for Claude sessions

{{One paragraph: what the project is, who uses it, and where it stands.}}

The conventions every change follows (workflow, tests, quality bar, design rules):

@docs/conventions.md

## Where things are

- `REQUIREMENTS.md`: what to build, with IDs such as `API-03`, and the decisions taken.
- `ARCHITECTURE.md`: concepts, components, contracts, flows and threats. **No code, type or API names.**
- `docs/plan/`: the waves of tasks (the `plan-wave` skill writes them from `docs/plan/template.md`).
- `docs/decisions.md`: platform decisions, dependencies and the required checks each language adds.
- `docs/languages/`: each language's rules, added by its pack.
- `.sdlc/checks.toml`: each component's paths and the checks the git hook runs before a commit and a push.

## The process

The `sdlc-kit` plugin provides the agents (`developer`, `fixer`, `reviewer`), the skills (`dispatch`, `plan-wave`)
and the hooks. The main session is the lead: it plans a wave with `plan-wave`, dispatches each task with
`dispatch`, and sets auto-merge once a task's reviewer approves. It never reads diffs or full logs itself.
