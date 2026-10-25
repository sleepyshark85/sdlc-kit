#!/usr/bin/env python3
"""Writes a wave's scorecard for the owner (docs/measuring.md, *The scorecard*).

  scorecard.py wave <n> [--out <folder>] [--project <folder>]

Run it from inside the project's checkout, with gh signed in. The wave's window runs from the merge of its plan PR
(branch docs/plan-wave-<n>) to the merge of the next wave's, or to now while there is none. A merged PR belongs to the
wave its facts block's task names (W<n>-T<m>), and a PR without such a task to the window it merged in. The scorecard
goes to wave-<n>.md in ~/.sdlc/scorecards/<repository>/, or in --out, never inside a git checkout: agents never see
it. --project is the folder of the project's session files, as for agent_report.py, which prices the agent team.

This slice writes the summary: DORA's five keys (MN11, MG1, MN2, MN3, MN4), the daily run (MN1), cost (LN1, LN5) and
the owner's load (LN2). A number the kit has no collector for yet reads "no data", never 0."""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import agent_report  # noqa: E402  (found through the path above)

review_gate = agent_report.load_module("review_gate", os.path.join(os.path.dirname(SCRIPTS), "template", ".github",
                                                                   "review_gate.py"))

WAVE = "wave"
SCORECARDS = os.path.join("~", ".sdlc", "scorecards")
GIT_FOLDER = ".git"
GH_TIMEOUT_SECONDS = 120
PR_LIMIT = 1000
PLAN_BRANCH = "docs/plan-wave-{}"
# The fields read from GitHub's answers, each named once: gh's --json and --jq field lists are built from them.
REPOSITORY_NAME = "nameWithOwner"
NUMBER, CREATED, MERGED, BODY = "number", "createdAt", "mergedAt", "body"
LABELS, FILES, COMMENTS, MERGE_COMMIT = "labels", "files", "comments", "mergeCommit"
NAME, PATH, OID = "name", "path", "oid"
AUTHORED, MESSAGE, PARENTS = "authored", "message", "parents"
CONCLUSION, COMPLETED = "conclusion", "completed_at"
PLAN_FIELDS = ",".join((NUMBER, MERGED))
PR_FIELDS = ",".join((NUMBER, CREATED, MERGED, BODY, LABELS, FILES, COMMENTS, MERGE_COMMIT))
COMMITS = "repos/{}/pulls/{}/commits"
COMMIT_FIELDS = (f".[] | {{{AUTHORED}: .commit.author.date, {MESSAGE}: .commit.message, "
                 f"{PARENTS}: (.parents | length)}}")
# Every check run of the commit: GitHub's default (filter=latest) keeps only the newest of each name, which would drop
# all but the last daily run on a head that stays main's for days.
CHECK_RUNS = "repos/{}/commits/{}/check-runs?filter=all"
CHECK_RUN_FIELDS = f".check_runs[] | {{{NAME}, {CONCLUSION}, {COMPLETED}}}"
MERGE_PARENTS = 2
DAILY_RUNS = ("daily (defaults)", "daily (flags-on)")
GREEN = "success"
RED = frozenset({"failure", "timed_out"})
OWNER_DECISION = "owner-decision"
FACTS = re.compile(r"<!--\s*sdlc\s*\n(.*?)-->", re.DOTALL)
TASK_ID = re.compile(r"W(\d+)-T\d+")
AI_TRAILER = re.compile(r"^Co-Authored-By:.*<noreply@anthropic\.com>", re.IGNORECASE | re.MULTILINE)
TASK, KIND, ESCAPED_FROM = "task", "kind", "escaped-from"
NONE = "none"
UNSTATED = "unstated"
FIX, SWITCH_ON = "fix", "switch-on"
PHASES = ("building", "waiting for review", "rework", "waiting to merge")
NO_DATA = "no data"


class ScorecardError(Exception):
    """A reason the scorecard can't be written, for the owner."""


def run_gh(*args):
    """gh's output for the arguments: the scorecard's one reader of GitHub, which the tests replace."""
    done = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=GH_TIMEOUT_SECONDS)
    if done.returncode:
        raise ScorecardError(f"gh {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout


def facts_of(body):
    """The PR description's facts block (docs/conventions.md) as {line: value}; the last block counts, and a
    description without one has none."""
    blocks = FACTS.findall(body or "")
    pairs = (line.split(":", 1) for line in (blocks[-1].splitlines() if blocks else []) if ":" in line)
    return {key.strip(): value.strip() for key, value in pairs}


def stated(facts, line):
    """Whether the facts block gives the line a value: neither missing, empty nor none."""
    return facts.get(line, NONE) not in ("", NONE)


def task_wave(facts):
    """The wave the PR's task names, or None for a PR without a planned task."""
    match = TASK_ID.fullmatch(facts.get(TASK, ""))
    return int(match.group(1)) if match else None


def hours(start, end):
    """The hours from one time to another."""
    return (end - start).total_seconds() / 3600


def own_commits(commits):
    """LN2: the commits no AI co-author trailer names, merge commits apart: git writes their message, with no
    trailer, whoever merges."""
    return sum(1 for commit in commits
               if commit[PARENTS] < MERGE_PARENTS and not AI_TRAILER.search(commit[MESSAGE]))


@dataclass
class Merge:
    """A merged PR as gh pr list gives it, as much as wave membership, MN4 and the daily run read."""
    number: int
    merged: datetime
    facts: dict
    files: frozenset
    merge_commit: str

    @classmethod
    def of(cls, item):
        """From its gh pr list item."""
        return cls(item[NUMBER], agent_report.parse_time(item[MERGED]), facts_of(item[BODY]),
                   frozenset(file[PATH] for file in item[FILES]), item[MERGE_COMMIT][OID])


@dataclass
class PullRequest(Merge):
    """A PR of the wave, with its review and its commits."""
    opened: datetime
    labels: frozenset
    verdicts: list
    first_commit: datetime
    own_commits: int

    @classmethod
    def of_wave(cls, item, commits):
        """From its gh pr list item and its commits. Verdicts are the times of the comments before the merge that
        start as the review gate's do."""
        merge = Merge.of(item)
        posted = [agent_report.parse_time(comment[CREATED]) for comment in item[COMMENTS]
                  if comment[BODY].startswith(review_gate.VERDICT_PREFIX)]
        return cls(**vars(merge), opened=agent_report.parse_time(item[CREATED]),
                   labels=frozenset(label[NAME] for label in item[LABELS]),
                   verdicts=sorted(time for time in posted if time < merge.merged),
                   first_commit=min(agent_report.parse_time(commit[AUTHORED]) for commit in commits),
                   own_commits=own_commits(commits))

    def phases(self):
        """MG1's lead time in hours: first commit to opened, to the first verdict, to the last, to the merge. A PR
        with no verdict spends its review time waiting for one."""
        first, last = (self.verdicts[0], self.verdicts[-1]) if self.verdicts else (self.merged, self.merged)
        return [hours(self.first_commit, self.opened), hours(self.opened, first), hours(first, last),
                hours(last, self.merged)]


@dataclass
class Plan:
    """A wave's merged plan PR."""
    number: int
    merged: datetime


@dataclass
class Window:
    """A wave's window, and the start of the wave before it, from which MN4 counts the code a fix reworks."""
    wave: int
    plan: Plan
    next_plan: Plan | None
    previous_start: datetime
    now: datetime

    @property
    def until(self):
        """The window's end: the next wave's plan PR's merge, or now while there is none."""
        return self.next_plan.merged if self.next_plan else self.now

    def holds(self, moment):
        """Whether the moment is in the window: from its start, and before its end."""
        return self.plan.merged <= moment < self.until


def plan_of(gh, wave):
    """The wave's merged plan PR (the first merged, if its branch was used twice), or None."""
    plans = [Plan(item[NUMBER], agent_report.parse_time(item[MERGED])) for item in json.loads(
        gh("pr", "list", "--state", "merged", "--head", PLAN_BRANCH.format(wave), "--json", PLAN_FIELDS))]
    return min(plans, key=lambda plan: plan.merged, default=None)


def window_of(gh, wave, now):
    """The wave's window, from its plan PR and the plan PRs of the waves before and after it; refused without a
    merged plan PR."""
    plan = plan_of(gh, wave)
    if plan is None:
        raise ScorecardError(f"Wave {wave} has no merged plan PR (branch {PLAN_BRANCH.format(wave)}).")
    previous = plan_of(gh, wave - 1) if wave > 1 else None
    return Window(wave, plan, plan_of(gh, wave + 1), previous.merged if previous else plan.merged, now)


def merged_since(gh, since):
    """gh pr list's item for every PR merged since the time, refusing more than one call reads rather than counting
    part of them."""
    items = json.loads(gh("pr", "list", "--state", "merged", "--limit", str(PR_LIMIT), "--json", PR_FIELDS,
                          "--search", f"merged:>={since.strftime('%Y-%m-%dT%H:%M:%SZ')}"))
    if len(items) >= PR_LIMIT:
        raise ScorecardError(f"{PR_LIMIT} or more PRs merged since {since:%Y-%m-%d}: past what one call reads.")
    return items


def in_wave(merge, window):
    """Whether the merged PR is the wave's: its task names the wave, or it has none and merged in the window."""
    named = task_wave(merge.facts)
    return named == window.wave if named is not None else window.holds(merge.merged)


def json_lines(text):
    """The values gh prints for --jq over a list, one JSON value per line."""
    return [json.loads(line) for line in text.splitlines()]


def read_wave(gh, repository, window):
    """Every PR merged since the wave before as a Merge, and the wave's own PRs by number, with their commits: only
    they need those, at one call each (gh pr list's commits would pass GitHub's limit on a query's size)."""
    items = merged_since(gh, window.previous_start)
    merges = [Merge.of(item) for item in items]
    prs = [PullRequest.of_wave(item, json_lines(gh("api", COMMITS.format(repository, merge.number), "--paginate",
                                                   "--jq", COMMIT_FIELDS)))
           for item, merge in zip(items, merges) if in_wave(merge, window)]
    return merges, sorted(prs, key=lambda pr: pr.number)


def daily_runs(gh, repository, heads, window):
    """Each daily run in the window as (completed, conclusion), oldest first, by its check's name. The run checks
    main's head, and every head of main was a PR's merge commit."""
    runs = defaultdict(list)
    for sha in heads:
        for run in json_lines(gh("api", CHECK_RUNS.format(repository, sha), "--paginate", "--jq", CHECK_RUN_FIELDS)):
            if run[NAME] not in DAILY_RUNS or not run[COMPLETED]:
                continue
            completed = agent_report.parse_time(run[COMPLETED])
            if window.holds(completed):
                runs[run[NAME]].append((completed, run[CONCLUSION]))
    return {name: sorted(found) for name, found in runs.items()}


def red_spells(runs, until):
    """MN1: each spell from a red run to the next green one, as (hours, back to green); a spell still red at the
    window's end runs to it."""
    spells, red_since = [], None
    for completed, conclusion in runs:
        if conclusion in RED and red_since is None:
            red_since = completed
        elif conclusion == GREEN and red_since is not None:
            spells.append((hours(red_since, completed), True))
            red_since = None
    return spells + ([(hours(red_since, until), False)] if red_since else [])


def reworks(prs, recent):
    """MN4: the unplanned fixes that change a file a PR merged before them in the last two waves changed."""
    return [pr for pr in prs if pr.facts.get(KIND) == FIX and task_wave(pr.facts) is None
            and any(other.merged < pr.merged and other.files & pr.files for other in recent)]


def team_by_role(folder, window):
    """LN1: the agent team's totals in the window by role, as {role: (agents, Totals)}; empty without sessions."""
    agents = agent_report.read_team(folder, agent_report.sessions_in(folder), window.plan.merged,
                                    window.until) if os.path.isdir(folder) else []
    by_agent = agent_report.priced(agents, *agent_report.load_prices())[0]
    agents_by_role, totals_by_role = Counter(), defaultdict(agent_report.Totals)
    for agent, totals in by_agent.items():
        agents_by_role[agent.role] += 1
        totals_by_role[agent.role].absorb(totals)
    return {role: (agents_by_role[role], totals) for role, totals in totals_by_role.items()}


@dataclass
class Reading:
    """Everything a wave's scorecard shows, read before any of it is written."""
    repository: str
    window: Window
    recent: list
    prs: list
    runs: dict
    team: dict


def read(gh, repository, window, folder):
    """The wave's reading: every PR merged since the wave before and the wave's own, the daily runs on main's heads
    in the window, and the agent team from the session files in the folder."""
    recent, prs = read_wave(gh, repository, window)
    heads = [merge.merge_commit for merge in recent if window.holds(merge.merged)]
    return Reading(repository, window, recent, prs, daily_runs(gh, repository, heads, window),
                   team_by_role(folder, window))


def share(part, whole):
    """The part of the whole, with its percentage when there is a whole."""
    return f"{part} of {whole} ({part / whole:.0%})" if whole else f"{part} of 0"


def hours_text(value):
    """Hours as the scorecard writes them."""
    return f"{value:.1f} h"


def spread_text(values):
    """The median and the longest of hours."""
    return f"{hours_text(median(values))} / {hours_text(max(values))}"


def per(total, count):
    """A cost per item, or - with no items."""
    return agent_report.money(total / count) if count else "-"


def switched_on(prs):
    """How many of the PRs switch a feature on."""
    return sum(1 for pr in prs if pr.facts.get(KIND) == SWITCH_ON)


def lead_time(prs):
    """MG1: the median from first commit to merge, and the median of each phase."""
    if not prs:
        return "no PRs"
    phases = zip(PHASES, zip(*(pr.phases() for pr in prs)))
    return (f"{hours_text(median(hours(pr.first_commit, pr.merged) for pr in prs))}: "
            + ", ".join(f"{phase} {hours_text(median(values))}" for phase, values in phases))


def restore_time(escapes):
    """MN3: from each escape's fix opened to merged, the median and the longest."""
    if not escapes:
        return "no fixes"
    restore = [hours(pr.opened, pr.merged) for pr in escapes]
    return f"{spread_text(restore)} (n={len(restore)})"


def flow_rows(prs, recent):
    """MN11, MG1, MN2, MN3 and MN4."""
    kinds = Counter(pr.facts.get(KIND) or UNSTATED for pr in prs)
    escapes = [pr for pr in prs if stated(pr.facts, ESCAPED_FROM)]
    return [
        ["MN11", "Merged PRs by kind", ", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items()))
         or "none"],
        ["MN11", "Features switched on", switched_on(prs)],
        ["MG1", "Lead time, first commit to merge (median)", lead_time(prs)],
        ["MN2", "Change failure rate: fixes with `escaped-from`", share(len(escapes), len(prs))],
        ["MN3", "Time to restore: the fix opened to merged (median / longest)", restore_time(escapes)],
        ["MN4", "Rework rate: unplanned fixes of the last two waves' code", share(len(reworks(prs, recent)), len(prs))],
    ]


def daily_run(runs, until):
    """MN1 for one daily run: its runs, red runs, hours red, and the time back to green of the spells that ended."""
    spells = red_spells(runs, until)
    back = [spell for spell, green in spells if green]
    return (f"{len(runs)}, {sum(1 for _, conclusion in runs if conclusion in RED)}, "
            f"{hours_text(sum(spell for spell, _ in spells))}, {spread_text(back) if back else NONE}"
            + ("; red at the window's end" if len(back) < len(spells) else ""))


def daily_rows(runs, until):
    """MN1, one row per daily run; no data when the project has no daily run."""
    return [["MN1", f"Daily run `{name}`: runs, red, hours red, back to green (median / longest)",
             daily_run(runs[name], until) if name in runs else NO_DATA] for name in DAILY_RUNS]


def team_cost(team, prs):
    """LN1: the team's cost in all, per merged PR and per feature switched on."""
    if not team:
        return NO_DATA
    total = agent_report.Totals()
    for _, totals in team.values():
        total.absorb(totals)
    return (f"{agent_report.money(total.cost)}; {per(total.cost, len(prs))} per merged PR; "
            f"{per(total.cost, switched_on(prs))} per feature switched on"
            + (f" (unpriced requests: {total.unpriced})" if total.unpriced else ""))


def cost_rows(team, prs):
    """LN1, LN5 and LN2."""
    return [
        ["LN1", "The agent team's cost", team_cost(team, prs)],
        ["LN5", "Live API spend", NO_DATA],
        ["LN2", "Escalations to the owner (`owner-decision`)", sum(1 for pr in prs if OWNER_DECISION in pr.labels)],
        ["LN2", "The owner's audit time", NO_DATA],
        ["LN2", "The owner's own commits (no AI co-author, merges apart)", sum(pr.own_commits for pr in prs)],
    ]


def role_table(team):
    """LN1 by role: agents, requests, tokens by kind (as team-report shows them) and cost, the costliest first."""
    return agent_report.table(
        ["Role", "Agents", "Requests", "Input", "Cache write", "Cache read", "Output", "Cost"],
        [[role, agents, totals.requests, f"{totals.fresh:,}", f"{totals.writes:,}", f"{totals.read:,}",
          f"{totals.output:,}", agent_report.money(totals.cost)]
         for role, (agents, totals) in sorted(team.items(), key=lambda item: (-item[1][1].cost, item[0]))])


def scorecard(reading):
    """The scorecard's Markdown, from the reading alone."""
    window, prs = reading.window, reading.prs
    end = (f"{window.next_plan.merged:%Y-%m-%d %H:%M} UTC (plan PR #{window.next_plan.number})" if window.next_plan
           else f"{window.now:%Y-%m-%d %H:%M} UTC, in progress")
    parts = [
        f"# Wave {window.wave}: {reading.repository}",
        f"From {window.plan.merged:%Y-%m-%d %H:%M} UTC (plan PR #{window.plan.number}) to {end}. "
        f"{len(prs)} merged PRs: " + (", ".join(f"#{pr.number}" for pr in prs) or "none") + ".",
        "## Summary",
        agent_report.table(["ID", "Metric", "Value"], flow_rows(prs, reading.recent)
                           + daily_rows(reading.runs, window.until) + cost_rows(reading.team, prs)),
        "No data: LN5 (no collector reads the reports' `Live spend:` lines yet), the owner's audit time (the owner "
        "records it here), and a daily run the project doesn't have.",
    ]
    if reading.team:
        parts += ["## Cost by role (LN1)", role_table(reading.team)]
    return "\n\n".join(parts) + "\n"


def inside_checkout(folder):
    """Whether the folder is inside a git checkout: a .git in it or in a folder above it."""
    path = os.path.abspath(folder)
    while not os.path.exists(os.path.join(path, GIT_FOLDER)):
        if os.path.dirname(path) == path:
            return False
        path = os.path.dirname(path)
    return True


def main(argv, gh=run_gh, now=None):
    """Writes the scorecard the arguments ask for and prints its path; 1 with the reason when it can't."""
    parser = argparse.ArgumentParser(description="A wave's scorecard, for the owner.")
    commands = parser.add_subparsers(dest="command", required=True)
    wave = commands.add_parser(WAVE, help="the scorecard of one wave")
    wave.add_argument("n", type=int, help="the wave's number")
    wave.add_argument("--out", help="the folder to write to (default: ~/.sdlc/scorecards/<repository>)")
    wave.add_argument("--project", help="the project's folder of session files (default: the current folder's)")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("a wave's number starts at 1")
    try:
        repository = json.loads(gh("repo", "view", "--json", REPOSITORY_NAME))[REPOSITORY_NAME]
        out = args.out or os.path.join(os.path.expanduser(SCORECARDS), repository.split("/")[-1])
        if inside_checkout(out):
            raise ScorecardError(f"{out} is inside a git checkout, where agents would see the scorecard.")
        window = window_of(gh, args.n, now or datetime.now(timezone.utc))
        reading = read(gh, repository, window, args.project or agent_report.project_folder(os.getcwd()))
    except ScorecardError as error:
        print(error, file=sys.stderr)
        return 1
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{WAVE}-{args.n}.md")
    with open(path, "w", encoding="utf-8") as file:
        file.write(scorecard(reading))
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
