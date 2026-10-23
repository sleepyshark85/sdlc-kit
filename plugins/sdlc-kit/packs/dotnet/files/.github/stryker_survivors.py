#!/usr/bin/env python3
"""Writes the mutants that survived a Stryker.NET run as a Markdown table, for the job summary, so the developer and
the reviewer see them on the checks page instead of in the log. Reads every mutation-report.json under the given
folders (Stryker's json reporter, the mutation-testing-elements schema). Usage: stryker_survivors.py <folder>..."""
import glob
import json
import os
import sys

# Mutants the tests never caught: they ran and passed, or no test covered them.
SURVIVING = {"Survived", "NoCoverage"}


def survivors(report):
    """(file, line, mutator, status) for each surviving mutant of a report, in file and line order."""
    rows = []
    for path, file in report.get("files", {}).items():
        for mutant in file.get("mutants", []):
            if mutant.get("status") in SURVIVING:
                rows.append((path, mutant["location"]["start"]["line"], mutant.get("mutatorName", "?"),
                             mutant["status"]))
    return sorted(rows)


def table(rows, root):
    if not rows:
        return "No surviving mutants.\n"
    lines = ["| File | Line | Mutator | Status |", "|---|---|---|---|"]
    lines += [f"| {os.path.relpath(path, root) if os.path.isabs(path) else path} | {line} | {mutator} | {status} |"
              for path, line, mutator, status in rows]
    return f"{len(rows)} surviving mutants:\n\n" + "\n".join(lines) + "\n"


def main():
    rows = []
    for folder in sys.argv[1:]:
        for path in glob.glob(os.path.join(folder, "**", "mutation-report.json"), recursive=True):
            with open(path, encoding="utf-8") as file:
                rows += survivors(json.load(file))
    print(table(rows, os.getcwd()), end="")


if __name__ == "__main__":
    main()
