"""Tests for agent_report.py, on session files written the way Claude Code writes them. Run:
python3 -m unittest discover -s plugins/sdlc-kit/scripts/tests"""
import importlib.util
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
PRICES = {
    "claude-opus-5-5": {"input": 4, "cache_write_5m": 5, "cache_write_1h": 8, "cache_read": 0.2, "output": 20},
    "claude-haiku-5-5": {"input": 0.1, "cache_write_5m": 0.125, "cache_write_1h": 0.2, "cache_read": 0.01,
                         "output": 0.5, "long": {"over": 100000, "input": 0.5, "cache_write_5m": 0.625,
                                                 "cache_write_1h": 1, "cache_read": 0.05, "output": 2.5}},
}


def usage(fresh=0, write_5m=0, write_1h=0, read=0, output=0):
    return {"input_tokens": fresh, "cache_creation_input_tokens": write_5m + write_1h, "cache_read_input_tokens": read,
            "output_tokens": output,
            "cache_creation": {"ephemeral_5m_input_tokens": write_5m, "ephemeral_1h_input_tokens": write_1h}}


def response(message_id, time, blocks=(), model="claude-opus-5-5", **tokens):
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

    def subagent(self, agent_id, agent_type, description, entries):
        self.write(os.path.join(SESSION, "subagents", f"agent-{agent_id}.jsonl"), entries)
        self.write(os.path.join(SESSION, "subagents", f"agent-{agent_id}.meta.json"),
                   [{"agentType": agent_type, "description": description}])

    def agents(self, since=None, until=None):
        return {agent.id: agent for agent in report.session_agents(self.folder, SESSION, since, until)}

    def test_a_response_written_as_several_entries_counts_once(self):
        first = response("m1", "2026-10-24T10:00:00Z", [tool_use("b1", "Bash")], fresh=10, output=5)
        self.write(f"{SESSION}.jsonl", [first, first, response("m1", "2026-10-24T10:00:01Z", [tool_use("b2", "Read")],
                                                               fresh=10, output=5)])

        lead = self.agents()["lead"]

        self.assertEqual((1, {"Bash": 1, "Read": 1}), (len(lead.responses), dict(lead.tools)))

    def test_a_response_costs_each_kind_of_token_at_its_price(self):
        spent = report.cost("claude-opus-5-5", usage(fresh=1_000_000, write_5m=1_000_000, write_1h=1_000_000,
                                                     read=1_000_000, output=1_000_000), PRICES)

        self.assertAlmostEqual(4 + 5 + 8 + 0.2 + 20, spent)

    def test_a_long_prompt_pays_the_long_prices_where_a_model_has_them(self):
        short = report.cost("claude-haiku-5-5", usage(read=100_000, output=1_000_000), PRICES)
        long = report.cost("claude-haiku-5-5", usage(fresh=1, read=100_000, output=1_000_000), PRICES)

        self.assertAlmostEqual(0.5 + 0.001, short)
        self.assertAlmostEqual(2.5 + 0.005 + 0.0000005, long)

    def test_a_model_without_a_price_is_unpriced(self):
        self.assertIsNone(report.cost("claude-new-model", usage(fresh=10), PRICES))

    def test_subagents_get_their_role_description_resumes_and_blocks(self):
        self.write(f"{SESSION}.jsonl", [response("m1", "2026-10-24T10:00:00Z", fresh=1),
                                        tool_result("2026-10-24T10:01:00Z", resumed="a1"),
                                        tool_result("2026-10-24T10:02:00Z", resumed="a1")])
        self.subagent("a1", "sdlc-kit:reviewer", "Review PR #2",
                      [response("r1", "2026-10-24T10:00:30Z", fresh=1), tool_result("2026-10-24T10:00:40Z", True)])
        self.write(os.path.join(SESSION, "git-gate", "a1.jsonl"),
                   [{"time": "2026-10-24T10:00:35Z", "agent_type": "sdlc-kit:reviewer", "rule": "Blocked: x"}])

        reviewer = self.agents()["a1"]

        self.assertEqual(("reviewer", "Review PR #2", 2, 1, 1),
                         (reviewer.role, reviewer.description, reviewer.resumes, reviewer.blocks, reviewer.errors))

    def test_the_window_keeps_only_what_happened_inside_it(self):
        self.write(f"{SESSION}.jsonl", [response("m1", "2026-10-23T23:59:59Z", fresh=1),
                                        response("m2", "2026-10-24T08:00:00Z", fresh=1),
                                        response("m3", "2026-10-25T00:00:00Z", fresh=1)])

        lead = self.agents(since="2026-10-24", until="2026-10-25")["lead"]

        self.assertEqual(["m2"], list(lead.responses))

    def test_an_agent_without_responses_in_the_window_is_left_out(self):
        self.write(f"{SESSION}.jsonl", [response("m1", "2026-10-24T10:00:00Z", fresh=1)])
        self.subagent("a1", "general-purpose", "Idle", [response("r1", "2026-10-20T10:00:00Z", fresh=1)])

        self.assertEqual(["lead"], list(self.agents(since="2026-10-24")))

    def test_the_report_sums_each_role_and_lists_unpriced_models(self):
        self.write(f"{SESSION}.jsonl", [response("m1", "2026-10-24T10:00:00Z", fresh=1_000_000, output=0)])
        self.subagent("a1", "sdlc-kit:developer", "Build T1",
                      [response("d1", "2026-10-24T10:00:00Z", model="claude-new-model", read=300, output=7)])

        text = report.report(list(self.agents().values()), PRICES)

        self.assertIn("| lead | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0% | 1,000,000 | 1 / 1 | $4.00 |", text)
        self.assertIn("| developer | 1 | 0 | 1 | 0 | 0 | 0 | 7 | 100% | 300 | 0 / 0 | $0.00 |", text)
        self.assertIn("Unpriced models (not in prices.json, counted as $0): claude-new-model.", text)

    def test_the_project_folder_is_named_after_the_project_path(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self.folder}):
            folder = report.project_folder(os.path.join(self.folder, "my.repo"))

        self.assertEqual(os.path.join(self.folder, "projects"), os.path.dirname(folder))
        self.assertTrue(os.path.basename(folder).endswith("-my-repo"))
        self.assertNotRegex(os.path.basename(folder), r"[^A-Za-z0-9-]")

    def test_the_shipped_prices_cover_every_field_the_cost_needs(self):
        with open(report.PRICES, encoding="utf-8") as file:
            models = json.load(file)["models"]

        for model, price in models.items():
            with self.subTest(model=model):
                self.assertIsNotNone(report.cost(model, usage(fresh=1, write_5m=1, write_1h=1, read=1, output=1),
                                                 models))


if __name__ == "__main__":
    unittest.main()
