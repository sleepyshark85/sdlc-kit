---
name: new-project
description: Starts a new project from the sdlc-kit template, with the language packs it needs, and walks the owner through the steps only they can take (the first commit, the repository settings, the reviewer's identity). Use when the owner asks to create, start or scaffold a new project or repository with this SDLC.
argument-hint: "<folder> <project name> [pack...]"
---

# Start a new project

Arguments: `$ARGUMENTS` (a folder, the project's name, and packs such as `dotnet`). Ask for any that are missing; the
packs available are the folders in `${CLAUDE_PLUGIN_ROOT}/packs/`.

1. **Create it:**
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/new_project.py" create <folder> "<name>" <pack>...`
   It refuses a folder that isn't empty, and prints the required checks to pass to `setup-repo.sh`.
2. **Fill the skeletons with the owner,** before any code: the purpose and requirements in `REQUIREMENTS.md`
   (testable criteria with their edge states), the components, contracts and threat model in `ARCHITECTURE.md`, the
   first platform decisions in `docs/decisions.md`. Leave a section the owner can't answer yet as a question, not a
   guess.
3. **The owner's steps,** which the git hook blocks for agents. Give them as `!` commands for the owner to run:
   - create the repository and push the first commit to `main`:
     `git init -b main && git add -A && git commit -m "Start from sdlc-kit" && gh repo create <owner>/<name> --private --source . --push`
   - create the reviewer's GitHub identity (a second account or a GitHub App), add it as a collaborator, and export
     its token as `SDLC_REVIEWER_TOKEN` in the environment Claude Code runs in;
   - apply the settings: `bash scripts/setup-repo.sh <owner>/<name> <reviewer login> <the printed checks>`.
4. **Plan the first wave** with the `plan-wave` skill, on a `docs/` branch. Its first task is usually the walking
   skeleton: the component's solution or module, one test, and CI green.

Adding a language later: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/new_project.py" add-pack <folder> <pack>` on a
branch, then the owner reruns `setup-repo.sh` with the new checks.
