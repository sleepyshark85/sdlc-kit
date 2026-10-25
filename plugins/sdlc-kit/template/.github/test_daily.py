"""Tests for daily.py, the daily run's suites with the defaults and with the flags on. Run with
`python3 -m unittest discover -s .github`."""
import contextlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_tooling import HERE, load

daily = load("daily")

TABLE = "| Flag | Feature | Added by | Switch-on | Removal task | State |\n|---|---|---|---|---|---|\n"
EXITS_WITH_FLAG_A = [sys.executable, "-c", "import os, sys; sys.exit(0 if os.environ.get('F_A') == 'true' else 3)"]
FAILS = [sys.executable, "-c", "import sys; sys.exit(5)"]


def touches(path):
    return [sys.executable, "-c", f"open({path!r}, 'w').close()"]


class InProgressFlagsTest(unittest.TestCase):
    def test_the_flags_in_progress_are_those_off(self):
        cases = {
            "# Release flags\n\n" + TABLE + "| `NewCart` | SHOP-01 | W1-T2 | W1-T5 | W2-T1 | off |\n"
            "| OldTax | SHOP-02 | W1-T3 | W1-T4 | W3-T1 | on |\n| Gone | SHOP-03 | W1-T1 | W1-T2 | W2-T2 | removed |\n"
            "| Beta_2 | SHOP-04 | W2-T1 | W2-T3 | W3-T2 | off |\n| Dash | -- | W2-T1 | W2-T3 | W3-T2 | off |\n\n"
            "Text after the table | with a bar.\n\n| Another table |\n":
                ["NewCart", "Beta_2", "Dash"],
            "| State | Flag |\n| :-- | --: |\n| off | A |\n": ["A"],
            "Flag | State\n\n| Flag | State |\n|---|---|\n| A | off |\n": ["A"],
            TABLE: [],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(expected, daily.in_progress_flags(text))

    def test_the_templates_placeholder_row_is_no_flag(self):
        with open(os.path.join(os.path.dirname(HERE), "docs", "flags.md"), encoding="utf-8") as file:
            self.assertEqual([], daily.in_progress_flags(file.read()))

    def test_a_table_the_run_cannot_read_is_refused_with_its_reason(self):
        cases = {
            "# Release flags\n\nNone yet.\n": "has no table with the columns Flag and State",
            "| Flag | Feature |\n|---|---|\n| A | X |\n": "has no table with the columns Flag and State",
            TABLE + "| New Cart | X | W1 | W2 | W3 | off |\n": "the flag `New Cart` is not a name",
            TABLE + "| 2fa | X | W1 | W2 | W3 | off |\n": "the flag `2fa` is not a name",
            "| State | Flag |\n|---|---|\n| -off | -A |\n": "the flag `-A` is not a name",
            TABLE + "| --- | X | W1 | W2 | W3 | off |\n": "the flag `---` is not a name",
            TABLE + "| A | X | W1 | W2 | W3 | Off |\n": "A's state `Off` is not one of off, on, removed",
            TABLE + "| A | X | W1 | W2 | off |\n": "has 5 cells, the table 6",
        }
        for text, reason in cases.items():
            with self.subTest(text=text):
                with self.assertRaisesRegex(daily.DailyError, reason):
                    daily.in_progress_flags(text)

    def test_generated_tables_give_their_off_flags(self):
        seed = random.randrange(2 ** 32)
        generate = random.Random(seed)
        for _ in range(200):
            columns = ["Flag", "Feature", "State", "Removal task"]
            generate.shuffle(columns)
            rows = [(f"F{index}_{generate.randrange(100)}", generate.choice(["off", "on", "removed"]))
                    for index in range(generate.randrange(6))]
            lines = [self.row(generate, columns), self.row(generate, ["---"] * len(columns))]
            for flag, state in rows:
                cells = {"Flag": f"`{flag}`" if generate.random() < 0.5 else flag, "State": state}
                lines.append(self.row(generate, [cells.get(column, "x") for column in columns]))
            text = "# Flags\n\nSome text.\n\n" + "\n".join(lines) + "\n\nMore text.\n"
            with self.subTest(seed=seed, text=text):
                self.assertEqual([flag for flag, state in rows if state == "off"], daily.in_progress_flags(text))

    def test_generated_text_is_read_or_refused_with_a_reason(self):
        seed = random.randrange(2 ** 32)
        generate = random.Random(seed)
        pieces = ["|", " ", "\n", "Flag", "State", "off", "on", "-", ":", "`", "{{", "x", "A_1"]
        for _ in range(500):
            text = "".join(generate.choice(pieces) for _ in range(generate.randrange(60)))
            with self.subTest(seed=seed, text=text):
                try:
                    flags = daily.in_progress_flags(text)
                except daily.DailyError:
                    continue
                self.assertTrue(all(daily.FLAG_NAME.match(flag) for flag in flags))

    @staticmethod
    def row(generate, cells):
        pad = " " * generate.randrange(3)
        return "|" + "|".join(pad + cell + pad for cell in cells) + "|" + pad


class FlagEnvironmentTest(unittest.TestCase):
    def test_each_flag_gets_its_variable_set_to_true(self):
        component = {"name": "web", "flag_variable": "FLAG_{flag}"}

        self.assertEqual({"FLAG_A": "true", "FLAG_B_2": "true"}, daily.flag_environment(component, ["A", "B_2"]))

    def test_no_flag_needs_no_variable(self):
        self.assertEqual({}, daily.flag_environment({"name": "web"}, []))

    def test_a_component_that_cannot_turn_a_flag_on_is_refused(self):
        for component in ({"name": "web"}, {"name": "web", "flag_variable": "FLAG"}):
            with self.subTest(component=component):
                with self.assertRaisesRegex(daily.DailyError, "web has a daily suite but its flag_variable"):
                    daily.flag_environment(component, ["A"])


class RunSuitesTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="daily-")
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name
        os.makedirs(os.path.join(self.root, "web"))

    def run_quietly(self, components, flags):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            return daily.run_suites(self.root, components, flags), output.getvalue()

    def test_a_suite_runs_in_its_directory_with_the_flags_on(self):
        components = [{"name": "web", "directory": "web", "flag_variable": "F_{flag}",
                       "daily": [EXITS_WITH_FLAG_A, touches("ran")]}]

        failures, output = self.run_quietly(components, ["A"])

        self.assertEqual(([], True), (failures, os.path.exists(os.path.join(self.root, "web", "ran"))))
        self.assertEqual(f"::group::web: {' '.join(EXITS_WITH_FLAG_A)}\n::endgroup::\n"
                         f"::group::web: {' '.join(touches('ran'))}\n::endgroup::\n", output)

    def test_without_the_flags_the_suite_inherits_the_environment(self):
        with mock.patch.dict(os.environ, {"F_A": "true"}):
            failures, _ = self.run_quietly([{"name": "web", "directory": "web", "daily": [EXITS_WITH_FLAG_A]}], [])

        self.assertEqual([], failures)

    def test_a_flag_turned_on_overrides_the_inherited_value(self):
        with mock.patch.dict(os.environ, {"F_A": "false"}):
            failures, _ = self.run_quietly([{"name": "web", "directory": "web", "flag_variable": "F_{flag}",
                                             "daily": [EXITS_WITH_FLAG_A]}], ["A"])

        self.assertEqual([], failures)

    def test_a_directory_that_is_missing_or_a_file_is_the_components_failure(self):
        open(os.path.join(self.root, "notes"), "w").close()
        components = [{"name": "api", "directory": "api", "daily": [touches("never")]},
                      {"name": "docs", "directory": "notes", "daily": [touches("never")]},
                      {"name": "web", "directory": "web", "daily": [touches("web")]}]

        failures, _ = self.run_quietly(components, [])

        self.assertEqual((["api: its directory `api` is not a directory",
                           "docs: its directory `notes` is not a directory"], True),
                         (failures, os.path.exists(os.path.join(self.root, "web", "web"))))

    def test_a_suite_killed_by_a_signal_fails(self):
        killed = subprocess.CompletedProcess([], -9)  # how POSIX reports a process SIGKILL ended
        with mock.patch.object(daily.subprocess, "run", return_value=killed):
            failures, _ = self.run_quietly([{"name": "web", "directory": "web", "daily": [FAILS]}], [])

        self.assertEqual([f"web: `{' '.join(FAILS)}` failed with exit code -9"], failures)

    def test_a_failure_stops_its_component_and_not_the_others(self):
        components = [{"name": "web", "directory": "web", "daily": [FAILS, touches("after")]},
                      {"name": "api", "daily": [["no-such-command-w-daily"], touches("never")]},
                      {"name": "docs", "before_push": [FAILS]},
                      {"name": "cli", "daily": [touches("cli")]}]

        failures, _ = self.run_quietly(components, [])

        self.assertEqual([f"web: `{' '.join(FAILS)}` failed with exit code 5",
                          "api: `no-such-command-w-daily` is not on PATH"], failures)
        self.assertEqual((False, False, True), tuple(os.path.exists(os.path.join(self.root, *path)) for path in
                                                     (("web", "after"), ("never",), ("cli",))))

    def test_a_component_without_its_flag_variable_stops_the_run_before_any_suite(self):
        components = [{"name": "cli", "daily": [touches("cli")]},
                      {"name": "web", "directory": "web", "daily": [touches("web")]}]

        with self.assertRaisesRegex(daily.DailyError, "cli has a daily suite but its flag_variable"):
            self.run_quietly(components, ["A"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "web", "web")))

    def test_no_suite_is_said_and_passes(self):
        for component in ({"name": "web", "before_push": [FAILS]}, {"name": "web", "daily": []}):
            with self.subTest(component=component):
                self.assertEqual(([], f"No component in {daily.sdlc_paths.CONFIG} names a daily suite; nothing to "
                                      "run.\n"), self.run_quietly([component], ["A"]))


class MainTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="daily-main-")
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name
        os.makedirs(os.path.join(self.root, ".sdlc"))
        os.makedirs(os.path.join(self.root, "docs"))
        self.write(os.path.join("docs", "flags.md"), TABLE + "| A | X | W1 | W2 | W3 | off |\n")
        patch = mock.patch.object(daily, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def write(self, path, text):
        with open(os.path.join(self.root, path), "w", encoding="utf-8") as file:
            file.write(text)

    def main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            return daily.main(argv), output.getvalue()

    def components(self, flag_variable):
        command = ", ".join(json.dumps(part) for part in EXITS_WITH_FLAG_A)
        self.write(os.path.join(".sdlc", "checks.toml"),
                   f"[[component]]\nname = 'web'\ndaily = [[{command}]]\n{flag_variable}")

    def test_each_run_reads_the_flags_it_needs(self):
        self.components("flag_variable = 'F_{flag}'\n")

        self.assertEqual([0, 1], [self.main(["flags-on"])[0], self.main(["defaults"])[0]])

    def test_a_failure_is_annotated_with_its_run(self):
        self.components("flag_variable = 'F_{flag}'\n")

        code, output = self.main(["defaults"])

        self.assertEqual(1, code)
        self.assertIn(f"::error title=Daily run (defaults) failed::web: `{' '.join(EXITS_WITH_FLAG_A)}` failed with "
                      "exit code 3\n", output)

    def test_the_flags_on_run_names_its_flags(self):
        self.components("flag_variable = 'F_{flag}'\n")

        self.assertIn("Flags on: A\n", self.main(["flags-on"])[1])

    def test_with_no_flag_in_progress_the_flags_on_run_says_so(self):
        self.components("")
        self.write(os.path.join("docs", "flags.md"), TABLE + "| A | X | W1 | W2 | W3 | on |\n")

        self.assertIn("No flag is in progress: this run is the defaults'.\n", self.main(["flags-on"])[1])

    def test_a_configuration_the_run_cannot_use_is_annotated(self):
        self.components("")

        self.assertEqual((1, "Flags on: A\n::error title=Daily run (flags-on) failed::web has a daily suite but its "
                             "flag_variable does not name the variable that turns a flag on (with {flag} for the "
                             "flag)\n"), self.main(["flags-on"]))

    def test_an_unknown_run_prints_the_usage(self):
        for argv in ([], ["nightly"], ["defaults", "flags-on"]):
            with self.subTest(argv=argv):
                self.assertEqual((64, ""), self.main(argv))


if __name__ == "__main__":
    unittest.main()
