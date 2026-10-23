#!/usr/bin/env python3
"""Prints `<component>=true` when a pull request changes that component, else `<component>=false`, for a workflow's
`changes` job to put in $GITHUB_OUTPUT. Each workflow runs on every pull request and skips its jobs on false, which a
required check counts as passing; a path filter would leave a required check unreported and block the merge. Which
paths belong to which component is .sdlc/sdlc_paths.py's rule, shared with the git hook. Outside a pull request it
prints true."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".sdlc"))
import sdlc_paths  # noqa: E402  (found through the path above)


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
        config = sdlc_paths.load(ROOT)
        changed = any(component in sdlc_paths.owners(config, path) for path in changed_paths())
    if not changed:
        print(f"Nothing of {component} changed; its jobs are skipped.", file=sys.stderr)
    print(f"{component}={'true' if changed else 'false'}")


if __name__ == "__main__":
    main()
