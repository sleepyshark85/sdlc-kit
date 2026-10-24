# Reviewer brief

Agent: `reviewer`, new for each PR, and new again for a strict re-review.

A new reviewer gets:

```text
Review PR #{{n}}, round {{1, or the next round for a strict re-review}} of 3: {{task id and outcome, or what the PR changes}}. Head {{full sha}}, base `{{base}}`{{, stacked on #N, or nothing}}.
Acceptance criteria and kind: {{"docs/plan/<wave file>, section <task id>", or the task the PR answers}}.
Read: {{named sections, e.g. "ARCHITECTURE §3, §5; docs/languages/dotnet.md"}}.
{{A part or a claim to verify, e.g. "the cancellation path" or "its claim that two survivors are equivalent", never what to conclude; or nothing}}
Scratch prefix: `{{prefix}}-`. Live API cap: {{"$X" or "no live calls"}}.

You review this PR only. Apply the code quality bar in docs/conventions.md strictly, to every changed line. Post the
verdict as your agent definition says. Follow the dispatch skill's agent-rules.md.
```

A strict re-review gets the same brief without earlier verdicts, so it forms its own view.

The same reviewer's later rounds, by `SendMessage` from the lead or from the agent that fixed the verdict:

```text
Round {{2 or 3}} of 3 for PR #{{n}} at {{full head sha}}, replying to your verdict at {{sha}}: {{one line per fix, and one `Disputed: <number and label> <reason>` per finding answered instead}}. Check CI, post a verdict naming the head, and reply in the short format.
```

## Audit

Once per wave, a new reviewer on one merged PR picked at random (the lead's routine, *The audit*):

```text
Audit merged PR #{{n}}, merged at {{merge commit sha}}: review it as if it were open, strictly, against the
conventions, the architecture and the quality bar. It has merged, so post no verdict: post one comment starting
"**Audit** at {{merge commit sha}}" with the must-fixes its review missed, each with its cause label, or "none".
Scratch prefix: `{{prefix}}-`. Live API cap: {{"$X" or "no live calls"}}.
Follow the dispatch skill's agent-rules.md, and reply in its short format.
```
