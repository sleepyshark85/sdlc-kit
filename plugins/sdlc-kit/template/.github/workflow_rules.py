#!/usr/bin/env python3
"""Checks the GitHub workflows' supply-chain rules: every workflow declares its token's `permissions` at the top level,
and every action it uses, other than the repository's own (`./…`), is pinned to a full commit sha; Dependabot keeps
the pins current. Prints one line per breach and exits 1 if there is any.

Usage: workflow_rules.py [folder...]   (default: .github/workflows)"""
import os
import re
import sys

DEFAULT_FOLDER = os.path.join(".github", "workflows")
WORKFLOW_SUFFIXES = (".yml", ".yaml")
TOP_LEVEL_PERMISSIONS = re.compile(r"^permissions:", re.M)
USES = re.compile(r"^[ \t]*(?:-[ \t]+)?uses:[ \t]*['\"]?([^'\"\s#]+)", re.M)
PINNED = re.compile(r"@[0-9a-f]{40}$")
LOCAL_ACTION = "./"


def breaches(name, text):
    """What a workflow's text breaks, one message per breach, each naming the workflow."""
    problems = [] if TOP_LEVEL_PERMISSIONS.search(text) else [f"{name}: no top-level permissions"]
    for action in USES.findall(text):
        if not action.startswith(LOCAL_ACTION) and not PINNED.search(action):
            problems.append(f"{name}: {action} is not pinned to a commit sha")
    return problems


def workflows(folder):
    return sorted(os.path.join(folder, name) for name in os.listdir(folder) if name.endswith(WORKFLOW_SUFFIXES))


def main(folders):
    problems = []
    for folder in folders or [DEFAULT_FOLDER]:
        for path in workflows(folder):
            with open(path, encoding="utf-8") as file:
                problems += breaches(path, file.read())
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
