# Developer brief

For one task of the wave plan. Agent: `developer`, with `isolation: "worktree"`. A small fix with an obvious approach
goes to [fix](fix.md) instead.

```text
Build {{task id}}: {{the task's outcome, one line}}.
Acceptance criteria and kind (dark, flagged, switch-on or technical): docs/plan/{{wave file}}, section {{task id}}.

Branch `{{branch}}` from `origin/{{base}}`; open the PR against `{{base}}`{{, stacked on #N, or nothing}}.
Read first: {{the task's Reads line from the plan, e.g. "REQUIREMENTS API-01…03; ARCHITECTURE §3, §5"}}.
Your files: {{paths}}. Other agents own {{paths and who, or "nothing: no one else is working"}}.
Scratch prefix: `{{prefix}}-`. Live API cap: {{"$X for the whole task" or "no live calls"}}.

The review applies every row of the code quality bar in docs/conventions.md. Do your agent definition's self-check
before opening the PR. Follow the dispatch skill's agent-rules.md. Stop once the PR is open.
```
