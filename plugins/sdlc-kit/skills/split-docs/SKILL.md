---
name: split-docs
description: Grows a project's short REQUIREMENTS.md or ARCHITECTURE.md into the full req42 or arc42 structure (docs/requirements/ or docs/architecture/, one file per area or subsystem), moving text without rewording it. Use when a document passes a split trigger in the conventions (Docs grow by splitting), when plan-wave finds one, or at new-project when the owner's spec is already that large.
argument-hint: "requirements | architecture"
---

# Split a document into its full form

Document: `$ARGUMENTS`. The short forms suit a small project; the full forms keep a large one readable in parts and
let parallel tasks edit different files. The split is one-way, one document per PR, and moves text: it rewords,
adds and drops nothing beyond what the steps below say. At `new-project`, before the first commit, there is no
branch or PR yet: skip steps 2 and 8, and leave no stub (step 5): the root file is deleted.

1. **Name the trigger** that fired (`docs/conventions.md`, *Docs grow by splitting*); it goes in the PR.
2. **Branch** `docs/split-requirements` or `docs/split-architecture`.
3. **Create the files** from `${CLAUDE_PLUGIN_ROOT}/skills/split-docs/templates/requirements/` or `…/architecture/`:
   the index (`README.md`), one file per area or subsystem named after it in lower case (`api.md`), and the shared
   files. Keep the template's section numbers: they are req42's and arc42's, and briefs cite them.
4. **Move each section** as the [mapping](#mapping) says. IDs never change. A full-form section the short form had no
   text for keeps the template's one line: "n/a" with the reason, or an open question for the owner.
5. **Leave a stub** in place of the root file, so links and habits still land: its title, one line with the date and
   the trigger, and a link to the new index.
6. **Update the pointers:** `CLAUDE.md` *Where things are*, the conventions' references, and any open wave plan in
   `docs/plan/` that cites a section of the old file. For requirements, each row of `docs/traceability.md` moves to
   its area file's *Traceability* section, and `docs/traceability.md` becomes a stub too.
7. **Check:** `python3 .github/links.py` passes, and every non-blank line of the old file is in a new file, except
   headings and the lines the PR lists as reworded.
8. **Open the PR** as a mechanical change: the trigger, the mapping used, "moves text, rewords nothing" with the
   check's result, and the lines it did reword (headings, the stub). The reviewer checks the content arrived whole.

## Mapping

### Requirements (req42)

| Short form | Full form |
|---|---|
| §1 Purpose and scope: goal | `README.md` §1 Vision and goals |
| §1: users and stakeholders | `README.md` §2 Stakeholders |
| §1: in and out of scope | `README.md` §3 Scope and context |
| §1: constraints | `README.md` §7 Constraints |
| §2 Requirements, each area's rows | `<area>.md` *Requirements*, one file per ID prefix, listed in `README.md` §4 |
| §3 Quality requirements | `quality.md` |
| §4 Glossary | `glossary.md` |
| §5 Open questions and assumptions | `README.md` §12 Risks, assumptions and open questions |
| `docs/traceability.md` rows | `<area>.md` or `quality.md` *Traceability* |

### Architecture (arc42)

| Short form | Full form |
|---|---|
| §1 Context and goals: quality goals | `README.md` §1 Introduction and goals |
| §1: the context | `README.md` §3 Context and scope |
| §1: strategy | `README.md` §4 Solution strategy |
| §2 Components and layers | `README.md` §5 level 1 (subsystems and the dependency rule); each subsystem's components to `<subsystem>.md` *Components* |
| §3 Contracts | Between subsystems: `README.md` §5; inside one: `<subsystem>.md` *Interfaces* |
| §4 Flows | Across subsystems: `README.md` §6; inside one: `<subsystem>.md` *Flows* |
| §5 Runtime model | `concepts.md` §8.1 |
| §6 Threat model | System-wide: `concepts.md` §8.2; one subsystem's own inputs: `<subsystem>.md` *Threats* |
| §7 Risks and technical debt | `README.md` §11 |

Constraints (arc42 §2), decisions (§9), quality requirements (§10) and the glossary (§12) are not repeated: the
architecture's index points to the requirements, `docs/decisions.md` and the glossary.
