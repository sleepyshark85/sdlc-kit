"""Tests for scorecard.py. GitHub is the one system boundary: gh is replaced by recorded JSON (fixtures/scorecard/),
answered by the exact command, so an unexpected call fails the test. Run:
python3 -m unittest discover -s plugins/sdlc-kit/scripts/tests"""
import contextlib
import dataclasses
import importlib.util
import io
import json
import os
import random
import string
import tempfile
import unittest
from unittest import mock

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scorecard.py")
spec = importlib.util.spec_from_file_location("scorecard", SCRIPT)
scorecard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorecard)

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "scorecard")
REPOSITORY = "example/project"
WAVE_2_START = "2026-10-08T00:00:00Z"
WAVE_1_START = "2026-10-01T00:00:00Z"
NOW = "2026-10-20T00:00:00Z"
PR_FIELDS = "number,createdAt,mergedAt,body,labels,files,comments,mergeCommit"
COMMIT_JQ = ".[] | {authored: .commit.author.date, message: .commit.message, parents: (.parents | length)}"
CHECK_RUN_JQ = ".check_runs[] | {name, conclusion, completed_at}"
OPUS = "claude-opus-5-5"
MILLION = 1_000_000
SEEDS = range(200)


def time(text):
    return scorecard.agent_report.parse_time(text)


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as file:
        return json.load(file)


def json_lines(items):
    """What gh prints for --jq over a list: one JSON value per line."""
    return "".join(json.dumps(item) + "\n" for item in items)


def commits_call(number):
    return "api", f"repos/{REPOSITORY}/pulls/{number}/commits", "--paginate", "--jq", COMMIT_JQ


def check_runs_call(sha):
    return "api", f"repos/{REPOSITORY}/commits/{sha}/check-runs?filter=all", "--paginate", "--jq", CHECK_RUN_JQ


class Recorded:
    """gh, answering each command the scorecard makes with its recorded output, and keeping the calls."""

    def __init__(self, since=WAVE_1_START, check_runs=None):
        self.calls = []
        self.answers = {("repo", "view", "--json", "nameWithOwner"): json.dumps({"nameWithOwner": REPOSITORY}),
                        ("pr", "list", "--state", "merged", "--limit", "1000", "--json", PR_FIELDS,
                         "--search", f"merged:>={since}"): json.dumps(fixture("prs.json"))}
        for wave, plans in fixture("plans.json").items():
            self.answers[("pr", "list", "--state", "merged", "--head", f"docs/plan-wave-{wave}",
                          "--json", "number,mergedAt")] = json.dumps(plans)
        runs = fixture("check-runs.json") if check_runs is None else check_runs
        commits = fixture("commits.json")
        for pr in fixture("prs.json"):
            sha = pr["mergeCommit"]["oid"]
            self.answers[check_runs_call(sha)] = json_lines(runs.get(sha, []))
            self.answers[commits_call(pr["number"])] = json_lines(commits[str(pr["number"])])

    def __call__(self, *args):
        self.calls.append(args)
        return self.answers[args]


def render(facts):
    return "<!-- sdlc\n" + "".join(f"{key}: {value}\n" for key, value in facts.items()) + "-->"


class FactsBlockTest(unittest.TestCase):
    """The facts block parser (C3), on generated descriptions; a failure names its seed."""

    def generated_facts(self, rng):
        keys = {"".join(rng.choices(string.ascii_lowercase + "-", k=rng.randint(1, 12))).strip("-") or "k"
                for _ in range(rng.randint(0, 8))}
        value_characters = string.ascii_letters + string.digits + " #:;,.§/-"
        return {key: "".join(rng.choices(value_characters, k=rng.randint(1, 30))).strip() or "v" for key in keys}

    def test_C3_a_generated_facts_block_parses_back_to_its_lines(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                facts = self.generated_facts(rng)
                prose = "".join(rng.choices(string.ascii_letters + " \n#*`", k=rng.randint(0, 200)))

                self.assertEqual(facts, scorecard.facts_of(f"{prose}\n\n{render(facts)}\n\n{prose}"))

    def test_C3_any_description_parses_to_text_lines_without_failing(self):
        pieces = ["<!--", "-->", "sdlc", "\n", ":", " ", "task", "W2-T1", "<!-- sdlc\n", "x"]
        for seed in SEEDS:
            with self.subTest(seed=seed):
                rng = random.Random(seed)

                facts = scorecard.facts_of("".join(rng.choices(pieces, k=rng.randint(0, 40))))

                self.assertTrue(all(isinstance(key, str) and isinstance(value, str) and "\n" not in key + value
                                    for key, value in facts.items()))

    def test_C3_the_last_block_counts_and_a_description_without_one_has_no_facts(self):
        body = f"{render({'kind': 'dark'})}\nquoted above\n{render({'kind': 'fix', 'task': 'none'})}"

        self.assertEqual({"kind": "fix", "task": "none"}, scorecard.facts_of(body))
        self.assertEqual({}, scorecard.facts_of("No block. <!-- a comment -->"))
        self.assertEqual({}, scorecard.facts_of(None))

    def test_C3_a_line_is_read_without_the_spaces_around_its_name_and_value(self):
        self.assertEqual({"task": "W2-T1"}, scorecard.facts_of("<!-- sdlc\n  task :  W2-T1  \n-->"))

    def test_C3_a_task_names_its_wave_and_none_names_no_wave(self):
        cases = {"W12-T3": 12, "none": None, "T3": None, "W2-T": None, "W2-T1 extra": None}
        for task, wave in cases.items():
            with self.subTest(task=task):
                self.assertEqual(wave, scorecard.task_wave({"task": task}))
        self.assertIsNone(scorecard.task_wave({}))


class WaveTest(unittest.TestCase):
    def window(self, wave=2, now=NOW):
        return scorecard.window_of(Recorded(), wave, time(now))

    def wave_2(self):
        window = self.window()
        return (window, *scorecard.read_wave(Recorded(), REPOSITORY, window))

    def by_number(self, prs):
        return {pr.number: pr for pr in prs}

    def test_the_window_runs_from_the_first_plan_merge_to_the_next_waves(self):
        window = self.window()

        self.assertEqual((20, time(WAVE_2_START), 30, time("2026-10-15T00:00:00Z"), time(WAVE_1_START)),
                         (window.plan.number, window.plan.merged, window.next_plan.number, window.until,
                          window.previous_start))
        self.assertTrue(window.holds(time(WAVE_2_START)))
        self.assertFalse(window.holds(time("2026-10-15T00:00:00Z")))

    def test_a_wave_in_progress_runs_to_now_and_the_first_wave_has_no_wave_before(self):
        third, first = self.window(3), self.window(1)

        self.assertEqual((None, time(NOW)), (third.next_plan, third.until))
        self.assertEqual(time(WAVE_1_START), first.previous_start)

    def test_a_wave_without_a_merged_plan_pr_is_refused(self):
        with self.assertRaisesRegex(scorecard.ScorecardError,
                                    r"Wave 4 has no merged plan PR \(branch docs/plan-wave-4\)"):
            self.window(4)

    def test_a_pr_belongs_to_the_wave_its_task_names_else_to_the_window_it_merged_in(self):
        _, _, prs = self.wave_2()

        self.assertEqual([20, 21, 22, 23, 25, 26], sorted(pr.number for pr in prs))

    def test_a_pr_whose_task_names_wave_0_is_in_no_window_it_merged_in(self):
        window, _, prs = self.wave_2()
        stray = dataclasses.replace(self.by_number(prs)[25], facts={"task": "W0-T1"})

        self.assertFalse(scorecard.in_wave(stray, window))

    def test_a_scorecard_past_what_one_call_reads_is_refused(self):
        many = json.dumps([fixture("prs.json")[0]] * 1000)

        with self.assertRaisesRegex(scorecard.ScorecardError, "1000 or more PRs merged since 2026-10-01"):
            scorecard.merged_since(lambda *args: many, time(WAVE_1_START))

    def test_MG1_lead_time_splits_into_building_review_wait_rework_and_merge_wait(self):
        prs = self.by_number(self.wave_2()[2])

        self.assertEqual([14, 6, 12, 6], prs[21].phases())
        self.assertEqual([6, 18, 0, 0], prs[25].phases())

    def test_MN11_MG1_MN2_MN3_MN4_the_flow_rows(self):
        _, recent, prs = self.wave_2()

        self.assertEqual([
            ["MN11", "Merged PRs by kind", "dark 1, docs 1, fix 2, switch-on 1, unstated 1"],
            ["MN11", "Features switched on", 1],
            ["MG1", "Lead time, first commit to merge (median)",
             "26.0 h: building 6.0 h, waiting for review 9.0 h, rework 0.0 h, waiting to merge 6.0 h"],
            ["MN2", "Change failure rate: fixes with `escaped-from`", "1 of 6 (17%)"],
            ["MN3", "Time to restore: the fix opened to merged (median / longest)", "12.0 h / 12.0 h (n=1)"],
            ["MN4", "Rework rate: unplanned fixes of the last two waves' code", "1 of 6 (17%)"],
        ], scorecard.flow_rows(prs, recent))

    def test_MN2_MN3_escapes_count_only_a_stated_escaped_from_and_restore_takes_median_and_longest(self):
        _, recent, prs = self.wave_2()
        numbers = self.by_number(prs)
        second = dataclasses.replace(numbers[26], facts={**numbers[26].facts, "escaped-from": "#21"})
        empty = dataclasses.replace(numbers[25], facts={"escaped-from": ""})

        rows = scorecard.flow_rows([numbers[23], second, empty], recent)

        self.assertEqual(["2 of 3 (67%)", "9.0 h / 12.0 h (n=2)"], [rows[3][2], rows[4][2]])
        self.assertEqual("none", numbers[26].facts["escaped-from"])

    def test_MN11_MG1_MN2_MN3_a_wave_with_no_prs_says_so(self):
        rows = scorecard.flow_rows([], [])

        self.assertEqual(["none", 0, "no PRs", "0 of 0", "no fixes", "0 of 0"], [row[2] for row in rows])

    def test_MN4_rework_is_an_unplanned_fix_of_a_file_merged_before_it_in_the_last_two_waves(self):
        _, recent, prs = self.wave_2()
        fix = self.by_number(prs)[23]
        planned = dataclasses.replace(fix, facts={**fix.facts, "task": "W2-T3"})
        not_a_fix = dataclasses.replace(fix, facts={**fix.facts, "kind": "technical"})

        self.assertEqual([23], [pr.number for pr in scorecard.reworks(prs, recent)])
        self.assertEqual([], scorecard.reworks([planned, not_a_fix], recent))

    def test_MN4_a_fix_of_a_file_only_a_later_pr_changes_is_not_rework(self):
        _, recent, prs = self.wave_2()
        numbers = self.by_number(prs)
        later = dataclasses.replace(numbers[22], files=numbers[26].files)

        self.assertLess(numbers[26].merged, later.merged)
        self.assertEqual([], scorecard.reworks([numbers[26]], [*recent, later]))

    def test_LN2_the_owners_own_commits_leave_out_ai_trailers_in_any_case_and_merge_commits(self):
        trailer = "Fix\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        commits = [{"message": "By hand", "parents": 1}, {"message": trailer, "parents": 1},
                   {"message": "Merge branch 'main' into feature/x", "parents": 2}]

        self.assertEqual(1, scorecard.own_commits(commits))

    def test_MN1_each_daily_run_counts_its_runs_red_runs_hours_red_and_time_back_to_green(self):
        window, recent, _ = self.wave_2()
        heads = [pr.merge_commit for pr in recent if window.holds(pr.merged)]

        runs = scorecard.daily_runs(Recorded(), REPOSITORY, heads, window)
        rows = scorecard.daily_rows(runs, window.until)

        self.assertEqual({"daily (defaults)", "daily (flags-on)"}, set(runs))
        metric = "runs, red, hours red, back to green (median / longest)"
        # flags-on went red and back to green on one head (2111…), which GitHub's default filter would hide.
        self.assertEqual([["MN1", f"Daily run `daily (defaults)`: {metric}",
                           "6, 2, 53.0 h, 41.0 h / 41.0 h; red at the window's end"],
                          ["MN1", f"Daily run `daily (flags-on)`: {metric}",
                           "5, 3, 100.0 h, 24.0 h / 24.0 h; red at the window's end"]], rows)

    def test_MN1_a_daily_run_never_red_has_no_time_back_to_green(self):
        runs = [(time("2026-10-08T00:00:00Z"), "success")]

        self.assertEqual("1, 0, 0.0 h, none", scorecard.daily_run(runs, time("2026-10-09T00:00:00Z")))

    def test_MN1_a_project_without_the_daily_run_has_no_data_not_zero(self):
        window = self.window()

        rows = scorecard.daily_rows(scorecard.daily_runs(Recorded(check_runs={}), REPOSITORY,
                                                         ["2022222222222222222222222222222222222222"], window),
                                    window.until)

        self.assertEqual(["no data", "no data"], [row[2] for row in rows])

    def test_MN1_red_lasts_from_the_first_red_run_to_the_next_green_one(self):
        runs = [(time("2026-10-08T00:00:00Z"), "failure"), (time("2026-10-08T06:00:00Z"), "timed_out"),
                (time("2026-10-08T10:00:00Z"), "success"), (time("2026-10-08T11:00:00Z"), "success")]

        self.assertEqual([(10.0, True)], scorecard.red_spells(runs, time("2026-10-09T00:00:00Z")))
        self.assertEqual([], scorecard.red_spells([(time("2026-10-08T00:00:00Z"), "cancelled")],
                                                  time("2026-10-09T00:00:00Z")))


class TeamTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="scorecard-")
        self.addCleanup(scratch.cleanup)
        self.folder = scratch.name
        prices = os.path.join(self.folder, "prices.json")
        with open(prices, "w", encoding="utf-8") as file:
            json.dump({"us_only_multiplier": 1.1, "models": {OPUS: {
                "input": 4, "cache_write_5m": 5, "cache_write_1h": 8, "cache_read": 0.2, "output": 20}}}, file)
        patch = mock.patch.object(scorecard.agent_report, "PRICES", prices)
        patch.start()
        self.addCleanup(patch.stop)
        self.sessions = os.path.join(self.folder, "sessions")

    def transcript(self, path, *responses, model=OPUS):
        full = os.path.join(self.sessions, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file:
            for message_id, moment, output in responses:
                file.write(json.dumps({"type": "assistant", "timestamp": moment, "message": {
                    "id": message_id, "model": model, "usage": {"output_tokens": output}, "content": []}}) + "\n")

    def write_team(self):
        self.transcript("s1.jsonl", ("m0", "2026-10-07T00:00:00Z", MILLION), ("m1", "2026-10-09T00:00:00Z", MILLION),
                        ("m2", "2026-10-16T00:00:00Z", MILLION))
        self.transcript(os.path.join("s1", "subagents", "agent-a1.jsonl"), ("m3", "2026-10-10T00:00:00Z", 2 * MILLION))
        with open(os.path.join(self.sessions, "s1", "subagents", "agent-a1.meta.json"), "w", encoding="utf-8") as file:
            json.dump({"agentType": "sdlc-kit:developer"}, file)

    def run_main(self, *argv, gh=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scorecard.main(["wave", *argv, "--project", self.sessions], gh=gh or Recorded(), now=time(NOW))
        return code, out.getvalue(), err.getvalue()

    def test_LN1_the_team_cost_in_the_window_per_merged_pr_and_per_feature_switched_on(self):
        self.write_team()
        window = scorecard.window_of(Recorded(), 2, time(NOW))
        prs = scorecard.read_wave(Recorded(), REPOSITORY, window)[1]

        team = scorecard.team_by_role(self.sessions, window)

        self.assertEqual({"developer": 1, "lead": 1}, {role: agents for role, (agents, _) in team.items()})
        self.assertEqual("$60.00; $10.00 per merged PR; $60.00 per feature switched on", scorecard.team_cost(team, prs))
        self.assertEqual("$60.00; - per merged PR; - per feature switched on", scorecard.team_cost(team, []))

    def test_LN1_unpriced_requests_are_named_beside_the_cost(self):
        self.transcript("s1.jsonl", ("m1", "2026-10-09T00:00:00Z", MILLION), ("m2", "2026-10-09T01:00:00Z", 1),
                        model="claude-unknown-1")
        window = scorecard.window_of(Recorded(), 2, time(NOW))

        cost = scorecard.team_cost(scorecard.team_by_role(self.sessions, window), [])

        self.assertEqual("$0.00; - per merged PR; - per feature switched on (unpriced requests: 2)", cost)

    def test_LN1_without_session_files_in_the_window_the_cost_has_no_data(self):
        window = scorecard.window_of(Recorded(), 2, time(NOW))

        self.assertEqual({}, scorecard.team_by_role(self.sessions, window))
        self.transcript("s1.jsonl", ("m1", "2026-10-16T00:00:00Z", MILLION))
        self.assertEqual({}, scorecard.team_by_role(self.sessions, window))
        self.assertEqual("no data", scorecard.team_cost(None, []))

    def test_LN1_LN5_LN2_main_writes_the_summary_to_the_folder_asked_for(self):
        self.write_team()
        out = os.path.join(self.folder, "cards")
        gh = Recorded()

        code, printed, _ = self.run_main("2", "--out", out, gh=gh)

        path = os.path.join(out, "wave-2.md")
        with open(path, encoding="utf-8") as file:
            text = file.read()
        self.assertEqual((0, path + "\n"), (code, printed))
        self.assertEqual({check_runs_call(sha) for sha in ["2022222222222222222222222222222222222222",
                                                           "2111111111111111111111111111111111111111",
                                                           "2333333333333333333333333333333333333333",
                                                           "2444444444444444444444444444444444444444",
                                                           "2555555555555555555555555555555555555555",
                                                           "2666666666666666666666666666666666666666"]}
                         | {commits_call(number) for number in [20, 21, 22, 23, 25, 26]},
                         {call for call in gh.calls if call[0] == "api"})
        self.assertTrue(text.startswith(
            f"# Wave 2: {REPOSITORY}\n\nFrom 2026-10-08 00:00 UTC (plan PR #20) to 2026-10-15 00:00 UTC (plan PR #30). "
            "6 merged PRs: #20, #21, #22, #23, #25, #26.\n\n## Summary\n\n| ID | Metric | Value |\n|---|---|---|\n"))
        for row in ["| MN4 | Rework rate: unplanned fixes of the last two waves' code | 1 of 6 (17%) |",
                    "| MN1 | Daily run `daily (flags-on)`: runs, red, hours red, back to green (median / longest) "
                    "| 5, 3, 100.0 h, 24.0 h / 24.0 h; red at the window's end |",
                    "| LN1 | The agent team's cost | $60.00; $10.00 per merged PR; $60.00 per feature switched on |",
                    "| LN5 | Live API spend | no data |",
                    "| LN2 | Escalations to the owner (`owner-decision`) | 1 |",
                    "| LN2 | The owner's audit time | no data |",
                    "| LN2 | The owner's own commits (no AI co-author, merges apart) | 2 |",
                    "## Cost by role (LN1)\n\n"
                    "| Role | Agents | Requests | Input | Cache write | Cache read | Output | Cost |\n"
                    "|---|---|---|---|---|---|---|---|\n"
                    "| developer | 1 | 1 | 0 | 0 | 0 | 2,000,000 | $40.00 |\n"
                    "| lead | 1 | 1 | 0 | 0 | 0 | 1,000,000 | $20.00 |\n"]:
            self.assertIn(row, text)

    def test_LN1_the_cost_by_role_shows_each_kind_of_token_and_orders_equal_costs_by_role(self):
        lead = scorecard.agent_report.Totals(requests=2, fresh=1000, writes=2000, read=30000, output=400, cost=5.0)
        developer = scorecard.agent_report.Totals(requests=1, output=10, cost=5.0)

        table = scorecard.role_table({"lead": (1, lead), "developer": (2, developer)})

        self.assertEqual("| Role | Agents | Requests | Input | Cache write | Cache read | Output | Cost |\n"
                         "|---|---|---|---|---|---|---|---|\n"
                         "| developer | 2 | 1 | 0 | 0 | 0 | 10 | $5.00 |\n"
                         "| lead | 1 | 2 | 1,000 | 2,000 | 30,000 | 400 | $5.00 |", table)

    def test_main_writes_the_first_waves_scorecard(self):
        code, printed, _ = self.run_main("1", "--out", self.folder)

        self.assertEqual((0, os.path.join(self.folder, "wave-1.md") + "\n"), (code, printed))

    def test_LN1_a_wave_in_progress_without_sessions_says_so_and_has_no_cost_table(self):
        code, printed, _ = self.run_main("3", "--out", self.folder, gh=Recorded(since=WAVE_2_START))

        with open(printed.strip(), encoding="utf-8") as file:
            text = file.read()
        self.assertEqual(0, code)
        self.assertIn("to 2026-10-20 00:00 UTC, in progress.", text)
        self.assertIn("| LN1 | The agent team's cost | no data |", text)
        self.assertNotIn("## Cost by role", text)

    def test_MN11_main_says_when_a_wave_has_no_merged_prs(self):
        gh = Recorded()
        empty = [key for key in gh.answers if "--search" in key]
        gh.answers[empty[0]] = "[]"

        code, printed, _ = self.run_main("2", "--out", self.folder, gh=gh)

        with open(printed.strip(), encoding="utf-8") as file:
            self.assertIn("0 merged PRs: none.", file.read())
        self.assertEqual(0, code)

    def test_main_writes_to_the_owners_scorecard_folder_by_default(self):
        home = os.path.join(self.folder, "home")
        with mock.patch.dict(os.environ, {"HOME": home, "USERPROFILE": home}):
            code, printed, _ = self.run_main("2")

        self.assertEqual((0, os.path.join(home, ".sdlc", "scorecards", "project", "wave-2.md") + "\n"),
                         (code, printed))

    def test_main_refuses_a_folder_inside_a_checkout(self):
        os.makedirs(os.path.join(self.folder, "repo", ".git"))
        out = os.path.join(self.folder, "repo", "notes", "cards")

        code, printed, error = self.run_main("2", "--out", out)

        self.assertEqual((1, ""), (code, printed))
        self.assertIn("inside a git checkout", error)
        self.assertFalse(os.path.exists(out))

    def test_main_reports_a_reason_it_cannot_write_the_scorecard(self):
        def failing(*args):
            raise scorecard.ScorecardError("gh repo view failed: not logged in")

        code, printed, error = self.run_main("2", "--out", self.folder, gh=failing)

        self.assertEqual((1, "", "gh repo view failed: not logged in\n"), (code, printed, error))

    def test_main_refuses_a_wave_number_below_one(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            scorecard.main(["wave", "0"], gh=Recorded())

        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
