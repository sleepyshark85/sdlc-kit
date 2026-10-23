#!/usr/bin/env python3
"""Prints `<component>=true` when a pull request changes that component, else `<component>=false`, for a workflow's
`changes` job to put in $GITHUB_OUTPUT. Each workflow runs on every pull request and skips its jobs on false, which a
required check counts as passing; a path filter would leave a required check unreported and block the merge.

Components and their paths come from .sdlc/checks.toml. A path belongs to a component when it is under one of its
paths or is its workflow (`.github/workflows/<name>.yml` or `<name>-*.yml`); a shared path belongs to every component.
Docs (Markdown and images outside .github/, .claude/ and .sdlc/) belong to none, so a docs-only pull request skips
every component's build and tests; the quality workflow still checks its links. Any other path, such as scripts/ or
this file, belongs to every component: when in doubt, everything runs. Outside a pull request it prints true."""
import os
import re
import subprocess
import sys
import tomllib

CONFIG = os.path.join(".sdlc", "checks.toml")
DOCS = re.compile(r"\.(md|png|svg|jpg)$")
TOOLING = (".github/", ".claude/", ".sdlc/")


def owners(config, path):
    """The names of the components a path belongs to."""
    components = config.get("component", [])
    names = {component["name"] for component in components}
    if path.startswith(tuple(config.get("shared", []))):
        return names
    for component in components:
        workflow = f".github/workflows/{component['name']}"
        if path.startswith(tuple(component.get("paths", []))) or path == f"{workflow}.yml" \
                or path.startswith(f"{workflow}-"):
            return {component["name"]}
    if DOCS.search(path) and not path.startswith(TOOLING):
        return set()
    return names


def changed_paths():
    base = f"origin/{os.environ['GITHUB_BASE_REF']}"
    # Without --no-renames a file moved between components lists only its new path, hiding the side it left.
    return subprocess.run(["git", "diff", "--no-renames", "--name-only", f"{base}...HEAD"],
                          capture_output=True, text=True, check=True).stdout.splitlines()


def main():
    component = sys.argv[1]
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        changed = True
    else:
        with open(CONFIG, "rb") as file:
            config = tomllib.load(file)
        changed = any(component in owners(config, path) for path in changed_paths())
    if not changed:
        print(f"Nothing of {component} changed; its jobs are skipped.", file=sys.stderr)
    print(f"{component}={'true' if changed else 'false'}")


if __name__ == "__main__":
    main()
