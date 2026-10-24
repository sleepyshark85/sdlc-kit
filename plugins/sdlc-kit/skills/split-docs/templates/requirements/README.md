<!-- Structure after req42 (https://req42.de). -->
# Requirements

What the project must do, language-neutral, in [req42](https://req42.de)'s structure; the section numbers are
req42's. Each requirement has an ID (`AREA-nn`) that tests carry in their names. This page is the index and holds what
every area shares; each area's requirements are in their own file. How it is built is in `docs/architecture/`; who
builds it when is in `docs/plan/`; the decisions taken are in `docs/decisions.md`.

## 1. Vision and goals

- **Goal:** {{the problem it solves, in one or two sentences}}
- {{Each further goal it is measured by, a bullet each.}}

## 2. Stakeholders

- **Users and stakeholders:** {{who uses it, who else has a stake, and what each expects}}

## 3. Scope and context

- **In scope:** {{…}} · **Out of scope:** {{…}}
- **Business context:** {{the people and systems it exchanges information with, and what they exchange}}

## 4. Functional requirements

One file per area, named after its ID prefix. Each requirement is written in an [EARS](https://alistairmavin.com/ears/)
pattern with its edge states, as each area file says.

| Prefix | Area | File |
|---|---|---|
| {{API}} | {{…}} | {{`api.md`}} |

## 5. Domain models

{{The domain's concepts and how they relate, or the business processes, where a picture says it better than rows;
"n/a" otherwise. A model of one area only goes in that area's file.}}

## 6. Quality requirements

In `quality.md`.

## 7. Constraints

- **Constraints:** {{what is fixed from outside: platform, regulation, deadline, an existing system}}

## 8. Glossary

In `glossary.md`.

## 9–11. Resources, team and roadmap

Not used: the agents are the team, and `docs/plan/` holds the waves.

## 12. Risks, assumptions and open questions

A task that depends on an open question waits for its answer.

| # | Question or assumption | Owner's answer |
|---|---|---|
| Q1 | {{…}} | {{open}} |
