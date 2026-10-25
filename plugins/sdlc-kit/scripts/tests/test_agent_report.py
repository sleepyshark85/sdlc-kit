"""Tests for agent_report.py, on session files written the way Claude Code writes them. Run:
python3 -m unittest discover -s plugins/sdlc-kit/scripts/tests"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from unittest import mock

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent_report.py")
spec = importlib.util.spec_from_file_location("agent_report", SCRIPT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

SESSION = "s1"
OPUS = "claude-opus-5-5"
PRICES = {
    OPUS: {"input": 4, "cache_write_5m": 5, "cache_write_1h": 8, "cache_read": 0.2, "output": 20},
    "claude-opus-5": {"input": 5, "cache_write_5m": 6.25, "cache_write_1h": 10, "cache_read": 0.5, "output": 25},
    "claude-haiku-4-5": {"input": 1, "cache_write_5m": 1.25, "cache_write_1h": 2, "cache_read": 0.1, "output": 5},
    "claude-haiku-5-5": {"input": 0.1, "cache_write_5m": 0.125, "cache_write_1h": 0.2, "cache_read": 0.01,
                         "output": 0.5, "long": {"over": 100000, "input": 0.5, "cache_write_5m": 0.625,
                                                 "cache_write_1h": 1, "cache_read": 0.05, "output": 2.5}},
}
US_ONLY = 1.1
MILLION = 1_000_000


def usage(fresh=0, write_5m=0, write_1h=0, read=0, output=0, speed="standard", geo="global"):
    return {"input_tokens": fresh, "cache_creation_input_tokens": write_5m + write_1h, "cache_read_input_tokens": read,
            "output_tokens": output, "speed": speed, "inference_geo": geo,
            "cache_creation": {"ephemeral_5m_input_tokens": write_5m, "ephemeral_1h_input_tokens": write_1h}}


def assistant(message_id, time, blocks=(), model=OPUS, **tokens):
    return {"type": "assistant", "timestamp": time,
            "message": {"id": message_id, "model": model, "usage": usage(**tokens), "content": list(blocks)}}


def tool_use(block_id, name):
    return {"type": "tool_use", "id": block_id, "name": name, "input": {}}


def tool_result(time, is_error=False, resumed=None):
    entry = {"type": "user", "timestamp": time,
             "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "is_error": is_error}]}}
    if resumed:
        entry["toolUseResult"] = {"success": True, "resumedAgentId": resumed}
    return entry


def response(model=OPUS, **tokens):
    return report.response_of({"model": model, "usage": usage(**tokens)}, report.parse_time("2026-10-24T10:00:00Z"))


class AgentReportTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="agent-report-")
        self.addCleanup(scratch.cleanup)
        self.folder = scratch.name

    def write(self, path, entries):
        full = os.path.join(self.folder, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file:
            file.writelines(json.dumps(entry) + "\n" for entry in entries)

    def subagent(self, agent_id, agent_type, entries, session=SESSION):
        self.write(os.path.join(session, "subagents", f"agent-{agent_id}.jsonl"), entries)
        self.write(os.path.join(session, "subagents", f"agent-{agent_id}.meta.json"), [{"agentType": agent_type}])

    def agents(self, since=None, until=None, sessions=(SESSION,)):
        seen = set()
        found = [agent for session in sessions for agent in report.session_agents(
            self.folder, session, since and report.parse_time(since), until and report.parse_time(until), seen)]
        return {(agent.session, agent.id): agent for agent in found}

    def test_a_response_written_as_several_entries_counts_once(self):
        first = assistant("m1", "2026-10-24T10:00:00Z", [tool_use("b1", "Bash")], fresh=10, output=5)
        self.write(f"{SESSION}.jsonl", [first, first, assistant("m1", "2026-10-24T10:00:01Z",
                                                                [tool_use("b2", "Read")], fresh=10, output=5)])

        lead = self.agents()[(SESSION, "lead")]

        self.assertEqual((1, {"Bash": 1, "Read": 1}), (len(lead.responses), dict(lead.tools)))

    def test_a_message_copied_into_another_session_counts_once(self):
        entry = assistant("m1", "2026-10-24T10:00:00Z", fresh=10)
        self.write("s1.jsonl", [entry])
        self.write("s2.jsonl", [entry, assistant("m2", "2026-10-24T10:00:01Z", fresh=10)])

        agents = self.agents(sessions=("s1", "s2"))

        self.assertEqual([1, 1], [len(agent.responses) for agent in agents.values()])

    def test_a_message_without_usage_is_not_a_response(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z"),
                                        assistant("m2", "2026-10-24T10:00:01Z", output=3)])

        self.assertEqual(1, len(self.agents()[(SESSION, "lead")].responses))

    def test_a_response_costs_each_kind_of_token_at_its_price(self):
        spent = report.cost(response(fresh=MILLION, write_5m=2 * MILLION, write_1h=3 * MILLION, read=4 * MILLION,
                                     output=5 * MILLION), PRICES, US_ONLY)

        self.assertAlmostEqual(4 + 5 * 2 + 8 * 3 + 0.2 * 4 + 20 * 5, spent)

    def test_a_1h_cache_write_count_above_all_cache_writes_is_capped_at_them(self):
        moment = report.parse_time("2026-10-24T10:00:00Z")
        written = report.response_of({"model": OPUS, "usage": {"cache_creation_input_tokens": 10,
                                                               "cache_creation": {"ephemeral_1h_input_tokens": 50}}},
                                     moment)

        self.assertEqual((0, 10), (written.write_5m, written.write_1h))

    def test_a_response_without_a_message_id_is_left_out(self):
        nameless = assistant(None, "2026-10-24T10:00:00Z", fresh=1)
        self.write(f"{SESSION}.jsonl", [nameless, nameless, assistant("m1", "2026-10-24T10:00:01Z", fresh=1)])

        self.assertEqual(1, len(self.agents()[(SESSION, "lead")].responses))

    def test_a_line_that_does_not_parse_and_a_block_that_is_not_an_object_are_skipped(self):
        entry = assistant("m1", "2026-10-24T10:00:00Z", ["thinking", tool_use("b1", "Bash")], fresh=1)
        result = tool_result("2026-10-24T10:00:01Z", is_error=True)
        result["message"]["content"].insert(0, "text")
        path = os.path.join(self.folder, f"{SESSION}.jsonl")
        with open(path, "w", encoding="utf-8") as file:
            file.write('{"type": "assistant", "timest\n' + json.dumps(entry) + "\n" + json.dumps(result) + "\n")

        lead = self.agents()[(SESSION, "lead")]

        self.assertEqual((1, {"Bash": 1}, 1), (len(lead.responses), dict(lead.tools), lead.errors))

    def test_a_subagent_without_a_meta_file_and_a_tool_without_a_name_are_counted_as_unknown(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", fresh=1)])
        self.write(os.path.join(SESSION, "subagents", "agent-a1.jsonl"),
                   [assistant("r1", "2026-10-24T10:00:00Z", [{"type": "tool_use", "id": "b1"}], fresh=1)])

        agent = self.agents()[(SESSION, "a1")]

        self.assertEqual(("unknown", {"?": 1}), (agent.role, dict(agent.tools)))

    def test_a_long_prompt_pays_the_long_prices_where_a_model_has_them(self):
        short = report.cost(response("claude-haiku-5-5", read=100_000, output=MILLION), PRICES, US_ONLY)
        long = report.cost(response("claude-haiku-5-5", fresh=1, read=100_000, output=MILLION), PRICES, US_ONLY)

        self.assertAlmostEqual(0.5 + 0.001, short)
        self.assertAlmostEqual(2.5 + 0.005 + 0.0000005, long)

    def test_a_dated_model_id_takes_its_models_price(self):
        self.assertAlmostEqual(5, report.cost(response("claude-haiku-4-5-20251001", output=MILLION), PRICES, US_ONLY))
        self.assertIsNone(report.cost(response("claude-haiku-4-50", output=MILLION), PRICES, US_ONLY))

    def test_a_model_whose_id_extends_another_takes_its_own_price(self):
        for model in (OPUS, OPUS + "-20260101"):
            with self.subTest(model=model):
                self.assertAlmostEqual(20, report.cost(response(model, output=MILLION), PRICES, US_ONLY))
        self.assertAlmostEqual(25, report.cost(response("claude-opus-5", output=MILLION), PRICES, US_ONLY))

    def test_a_time_with_an_offset_is_read_in_utc(self):
        self.assertEqual(report.parse_time("2026-10-24T10:00:00Z"), report.parse_time("2026-10-24T12:00:00+02:00"))

    def test_an_entry_with_an_unreadable_time_is_skipped(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "yesterday", fresh=1), assistant("m0", 1729764000, fresh=1),
                                        assistant("m2", "2026-10-24T10:00:00Z", fresh=1)])
        self.write(os.path.join(SESSION, "git-gate", "main.jsonl"),
                   [{"time": "soon", "rule": "force-push"}, {"time": "2026-10-24T10:00:01Z", "rule": "force-push"}])

        lead = self.agents()[(SESSION, "lead")]

        self.assertEqual((1, 1), (len(lead.responses), lead.blocks))

    def test_us_only_routing_costs_its_multiplier_more(self):
        self.assertAlmostEqual(22, report.cost(response(output=MILLION, geo="us"), PRICES, US_ONLY))

    def test_fast_mode_and_an_unknown_model_are_unpriced(self):
        self.assertIsNone(report.cost(response(output=1, speed="fast"), PRICES, US_ONLY))
        self.assertIsNone(report.cost(response("claude-new-model", output=1), PRICES, US_ONLY))

    def test_subagents_get_their_role_resumes_errors_and_blocks_in_the_window(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", fresh=1),
                                        tool_result("2026-10-24T10:01:00Z", resumed="a1"),
                                        tool_result("2026-10-24T10:02:00Z", resumed="a1")])
        self.subagent("a1", "sdlc-kit:reviewer", [assistant("r1", "2026-10-24T10:00:30Z", fresh=1),
                                                  tool_result("2026-10-24T10:00:40Z", is_error=True),
                                                  tool_result("2026-10-24T10:00:41Z")])
        self.write(os.path.join(SESSION, "git-gate", "a1.jsonl"),
                   [{"time": "2026-10-24T10:00:35Z", "agent_type": "sdlc-kit:reviewer", "rule": "force-push"},
                    {"time": "2026-10-23T10:00:35Z", "agent_type": "sdlc-kit:reviewer", "rule": "force-push"}])

        reviewer = self.agents(since="2026-10-24")[(SESSION, "a1")]

        self.assertEqual(("reviewer", 2, 1, 1), (reviewer.role, reviewer.resumes, reviewer.blocks, reviewer.errors))

    def test_the_leads_blocks_are_read_from_the_main_log(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", fresh=1)])
        self.write(os.path.join(SESSION, "git-gate", "main.jsonl"),
                   [{"time": "2026-10-24T10:00:01Z", "agent_type": "main", "rule": "push-to-default"}])

        self.assertEqual(1, self.agents()[(SESSION, "lead")].blocks)

    def test_the_window_includes_its_start_and_excludes_its_end(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-23T23:59:59Z", fresh=1),
                                        assistant("m2", "2026-10-24T00:00:00Z", fresh=1),
                                        assistant("m3", "2026-10-24T23:59:59.500Z", fresh=1),
                                        assistant("m4", "2026-10-25T00:00:00Z", fresh=1)])

        lead = self.agents(since="2026-10-24", until="2026-10-25")[(SESSION, "lead")]

        self.assertEqual(2, len(lead.responses))

    def test_an_agent_without_responses_in_the_window_is_left_out(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", fresh=1)])
        self.subagent("a1", "general-purpose", [assistant("r1", "2026-10-20T10:00:00Z", fresh=1)])

        self.assertEqual([(SESSION, "lead")], list(self.agents(since="2026-10-24")))

    def test_an_agents_model_peak_and_minutes(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", model="claude-haiku-4-5", fresh=9),
                                        assistant("m2", "2026-10-24T10:30:00Z", fresh=4),
                                        assistant("m3", "2026-10-24T10:45:00Z", fresh=5, read=2)])

        lead = self.agents()[(SESSION, "lead")]

        self.assertEqual((OPUS, 9, 45.0), (lead.model(), lead.peak(), lead.minutes()))

    def test_an_agent_at_a_warning_threshold_is_past_it(self):
        self.assertEqual((True, False), (report.past(150_000, 150_000), report.past(149_999, 150_000)))

    def test_the_report_renders_each_table(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", [tool_use("b1", "Agent")],
                                                  fresh=MILLION)])
        self.subagent("a1", "sdlc-kit:developer",
                      [assistant("d1", "2026-10-24T10:00:00Z", model="claude-new-model", write_5m=40, read=300,
                                 output=7),
                       assistant("d2", "2026-10-24T10:10:00Z", [tool_use("b2", "Bash")], write_1h=2, output=1)])

        text = report.report(list(self.agents().values()), PRICES, US_ONLY)

        for row in ("| lead | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0% | 1,000,000 | 1 / 1 | $4.00 |",
                    "| developer | 1 | 0 | 2 | 1 | 0 | 0 | 8 | 88% | 340 | 0 / 0 | $0.00 |",
                    f"| {OPUS} | 2 | 2 | 1,000,000 | 2 | 0 | 1 | $4.00 |",
                    "| claude-new-model | 1 | 1 | 0 | 40 | 300 | 7 | $0.00 (+1 unpriced) |",
                    f"| lead | {OPUS} | 1 | 1 / 1 | 1 / 1 | 0 / 0 | 1,000,000 / 1,000,000 | 0 / 0 | 0 / 0 | 0 / 0 "
                    "| $4.00 / $4.00 |",
                    "| developer | claude-new-model | 1 | 2 / 2 | 1 / 1 | 10 / 10 | 0 / 0 | 42 / 42 | 300 / 300 "
                    "| 8 / 8 | $0.00 / $0.00 |",
                    "| developer | Bash 1 |",
                    "Unpriced (fast mode, or not in prices.json), counted as $0: claude-new-model."):
            with self.subTest(row=row):
                self.assertIn(row, text)

    def test_roles_are_listed_by_cost_highest_first(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", output=MILLION)])
        self.subagent("a1", "sdlc-kit:developer", [assistant("d1", "2026-10-24T10:00:00Z", output=1)])

        text = report.report(list(self.agents().values()), PRICES, US_ONLY)

        per_dispatch = text[text.index("## Per dispatch"):]
        self.assertLess(text.index("| lead | 1 |"), text.index("| developer | 1 |"))
        self.assertLess(per_dispatch.index(f"| lead | {OPUS} |"), per_dispatch.index(f"| developer | {OPUS} |"))
        self.assertNotIn("Unpriced", text)

    def test_roles_that_cost_the_same_are_listed_by_name(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", output=1)])
        self.subagent("a1", "sdlc-kit:reviewer", [assistant("r1", "2026-10-24T10:00:00Z", output=1)])
        self.subagent("a2", "sdlc-kit:developer", [assistant("d1", "2026-10-24T10:00:00Z", output=1)])

        text = report.report(list(self.agents().values()), PRICES, US_ONLY)

        self.assertLess(text.index("| developer | 1 |"), text.index("| lead | 1 |"))
        self.assertLess(text.index("| lead | 1 |"), text.index("| reviewer | 1 |"))

    def test_a_role_and_models_dispatches_show_their_median_and_largest(self):
        self.write(f"{SESSION}.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", fresh=1)])
        tools = {"a1": [], "a2": ["Bash"], "a3": ["Bash", "Read", "Grep"]}
        for agent_id, requests in (("a1", 1), ("a2", 2), ("a3", 4)):
            entries = [assistant(f"{agent_id}-{n}", f"2026-10-24T10:{n * 10:02d}:00Z", output=MILLION)
                       for n in range(requests)]
            entries[0]["message"]["content"] = [tool_use(f"{agent_id}-t{i}", name)
                                                for i, name in enumerate(tools[agent_id])]
            self.subagent(agent_id, "sdlc-kit:developer", entries)

        text = report.report(list(self.agents().values()), PRICES, US_ONLY)

        self.assertIn(f"| developer | {OPUS} | 3 | 2 / 4 | 1 / 3 | 10 / 30 | 0 / 0 | 0 / 0 | 0 / 0 "
                      "| 2,000,000 / 4,000,000 | $40.00 / $80.00 |", text)
        self.assertIn("| developer | Bash 2, Read 1, Grep 1 |", text)

    def test_the_project_folder_is_named_after_the_project_path(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.folder}):
            folder = report.project_folder(os.path.join(self.folder, "my.repo"))

        self.assertEqual(os.path.join(self.folder, "projects"), os.path.dirname(folder))
        self.assertTrue(os.path.basename(folder).endswith("-my-repo"))
        self.assertNotRegex(os.path.basename(folder), r"[^A-Za-z0-9-]")

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = report.main(["--project", self.folder, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_main_reports_the_sessions_asked_for_at_the_shipped_prices(self):
        with open(report.PRICES, encoding="utf-8") as file:
            shipped = json.load(file)
        self.write("s1.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", output=MILLION, geo="us")])
        self.write("s2.jsonl", [assistant("m2", "2026-10-24T10:00:00Z", model="claude-haiku-4-5", output=1)])

        code, text, _ = self.run_main("--session", "s1")
        every = self.run_main()[1]

        us_cost = report.money(shipped["models"][OPUS]["output"] * shipped["us_only_multiplier"])
        self.assertEqual(0, code)
        self.assertIn(f"| {OPUS} | 1 | 1 | 0 | 0 | 0 | 1,000,000 | {us_cost} |", text)
        self.assertNotIn("claude-haiku-4-5", text)
        self.assertIn("claude-haiku-4-5", every)

    def test_main_fails_without_session_files_or_activity_in_the_window(self):
        self.write("s1.jsonl", [assistant("m1", "2026-10-24T10:00:00Z", output=1)])

        missing = self.run_main("--project", os.path.join(self.folder, "missing"))
        empty = self.run_main("--since", "2026-10-25")

        self.assertEqual((1, ""), missing[:2])
        self.assertIn("No session files", missing[2])
        self.assertEqual((1, "", "No agent activity in that window.\n"), empty)

    def test_the_shipped_prices_cover_every_field_the_cost_needs(self):
        with open(report.PRICES, encoding="utf-8") as file:
            shipped = json.load(file)

        for model in shipped["models"]:
            with self.subTest(model=model):
                self.assertIsNotNone(report.cost(response(model, fresh=1, write_5m=1, write_1h=1, read=1, output=1),
                                                 shipped["models"], shipped["us_only_multiplier"]))


if __name__ == "__main__":
    unittest.main()
