#!/usr/bin/env python3
"""The daily run on `main` (.github/workflows/daily.yml): each component's `daily` suite from .sdlc/checks.toml, run
in the component's directory, either with the defaults or with every in-progress release flag on. A flag is in
progress while its row in docs/flags.md says `off`; the component's `flag_variable` names the environment variable
that turns one on, `{flag}` standing for the flag's name, and the run sets it to `true`. A component stops at its
first failing command; the others still run. Prints an error annotation naming the run and each failing command,
and exits 1 if any failed.

Usage: daily.py defaults|flags-on"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".sdlc"))
import sdlc_paths  # noqa: E402  (found through the path above)

DEFAULTS = "defaults"
FLAGS_ON = "flags-on"
FLAGS_FILE = os.path.join("docs", "flags.md")
FLAG_COLUMN = "Flag"
STATE_COLUMN = "State"
IN_PROGRESS = "off"
STATES = (IN_PROGRESS, "on", "removed")
PLACEHOLDER = "{{"
FLAG_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
SEPARATOR_CELL = re.compile(r":?-+:?\Z")
NAME = "name"
DIRECTORY = "directory"
SUITE = "daily"
FLAG_VARIABLE = "flag_variable"
FLAG_SLOT = "{flag}"
ON_VALUE = "true"
GROUP = "::group::{}"  # GitHub's workflow commands
END_GROUP = "::endgroup::"
ERROR = "::error title={}::{}"


class DailyError(Exception):
    """A configuration the run cannot use, with what to fix."""


def cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def flag_rows(text):
    """The rows of docs/flags.md's flag table, each as {column: cell}; raises DailyError when there is no table."""
    lines = text.splitlines()
    for at, line in enumerate(lines):
        header = cells(line) if line.lstrip().startswith("|") else []
        if FLAG_COLUMN in header and STATE_COLUMN in header:
            break
    else:
        raise DailyError(f"{FLAGS_FILE} has no table with the columns {FLAG_COLUMN} and {STATE_COLUMN}")
    rows = []
    for line in lines[at + 1:]:
        if not line.lstrip().startswith("|"):
            break
        row = cells(line)
        if all(SEPARATOR_CELL.match(cell) for cell in row):
            continue
        if len(row) != len(header):
            raise DailyError(f"{FLAGS_FILE}: the row `{line.strip()}` has {len(row)} cells, the table {len(header)}")
        rows.append(dict(zip(header, row)))
    return rows


def in_progress_flags(text):
    """The flags docs/flags.md's text lists as in progress, in its order. The template's placeholder row is skipped;
    raises DailyError on a flag that is not a name or a state that is not one of STATES."""
    flags = []
    for row in flag_rows(text):
        flag, state = row[FLAG_COLUMN].strip("`"), row[STATE_COLUMN]
        if flag.startswith(PLACEHOLDER):
            continue
        if not FLAG_NAME.match(flag):
            raise DailyError(f"{FLAGS_FILE}: the flag `{flag}` is not a name (letters, digits and underscores)")
        if state not in STATES:
            raise DailyError(f"{FLAGS_FILE}: {flag}'s state `{state}` is not one of {', '.join(STATES)}")
        if state == IN_PROGRESS:
            flags.append(flag)
    return flags


def flag_environment(component, flags):
    """The environment variables that turn each flag on for a component's suite; raises DailyError when there are
    flags and the component's `flag_variable` has no slot for them."""
    if not flags:
        return {}
    pattern = component.get(FLAG_VARIABLE, "")
    if FLAG_SLOT not in pattern:
        raise DailyError(f"{component[NAME]} has a {SUITE} suite but its {FLAG_VARIABLE} does not name the "
                         f"variable that turns a flag on (with {FLAG_SLOT} for the flag)")
    return {pattern.replace(FLAG_SLOT, flag): ON_VALUE for flag in flags}


def run_component(root, component, environment):
    """Runs a component's suite in its directory until a command fails; returns that failure's message (or that its
    directory is missing), or None."""
    name = component[NAME]
    directory = os.path.join(root, component.get(DIRECTORY, ""))
    if not os.path.isdir(directory):
        return f"{name}: its {DIRECTORY} `{component[DIRECTORY]}` is not a directory"
    for command in component[SUITE]:
        shown = " ".join(command)
        print(GROUP.format(f"{name}: {shown}"), flush=True)
        try:
            code = subprocess.run(command, cwd=directory, env=environment).returncode
        except FileNotFoundError:
            return f"{name}: `{command[0]}` is not on PATH"
        finally:
            print(END_GROUP, flush=True)
        if code != 0:
            return f"{name}: `{shown}` failed with exit code {code}"
    return None


def run_suites(root, components, flags):
    """Runs each component's suite with the flags on; returns the failures' messages. Raises DailyError before
    running anything when a component cannot turn the flags on."""
    suites = [(component, os.environ | flag_environment(component, flags))
              for component in components if component.get(SUITE)]
    if not suites:
        print(f"No component in {sdlc_paths.CONFIG} names a {SUITE} suite; nothing to run.")
    failures = [run_component(root, component, environment) for component, environment in suites]
    return [failure for failure in failures if failure]


def main(argv):
    if len(argv) != 1 or argv[0] not in (DEFAULTS, FLAGS_ON):
        print(__doc__, file=sys.stderr)
        return 64
    run = argv[0]
    try:
        flags = []
        if run == FLAGS_ON:
            with open(os.path.join(ROOT, FLAGS_FILE), encoding="utf-8") as file:
                flags = in_progress_flags(file.read())
            print(f"Flags on: {', '.join(flags)}" if flags else "No flag is in progress: this run is the defaults'.")
        failures = run_suites(ROOT, sdlc_paths.components(sdlc_paths.load(ROOT)), flags)
    except DailyError as error:
        failures = [str(error)]
    for failure in failures:
        print(ERROR.format(f"Daily run ({run}) failed", failure))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
