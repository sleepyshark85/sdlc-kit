# sdlc-kit — working notes for Claude sessions

A Claude Code plugin and project template that carry an SDLC for building software with AI agents. The process is
defined in [`docs/sdlc.md`](docs/sdlc.md); the [README](README.md) maps each practice to the parts that cover it.

## Rules for changing the kit

- **Every change through a branch and a pull request** to `main`, reviewed by a fresh reviewer; the kit follows the
  process it ships. Branch prefixes: `feature/`, `fix/`, `refactor/`, `docs/`, `chore/`, `test/`.
- **Generic only.** Nothing project-specific in the plugin or the template: no project's requirement IDs, paths or
  design rules. A language's rules go in its pack.
- **A change to a practice updates the README's table** in the same PR: its coverage and its status.
- **A process change names the metric it should move** (docs/sdlc.md, *Changing the process*).
- **Release:** bump `version` in `plugins/sdlc-kit/.claude-plugin/plugin.json` when a merged change should reach
  projects; note what changed in the PR.
- **Tests before a PR,** as `.github/workflows/kit.yml` runs them:
  - `python3 -B -m unittest discover -s plugins/sdlc-kit/hooks/tests`
  - `python3 -B -m unittest discover -s plugins/sdlc-kit/scripts/tests`
  - in `plugins/sdlc-kit/template`: `python3 -B -m unittest discover -s .github`
  - `python3 plugins/sdlc-kit/template/.github/links.py`
  - `python3 plugins/sdlc-kit/template/.github/workflow_rules.py .github/workflows plugins/sdlc-kit/template/.github/workflows plugins/sdlc-kit/packs/dotnet/files/.github/workflows`
- Python scripts use the standard library only (3.11+), so a new project needs nothing installed for its tooling.
