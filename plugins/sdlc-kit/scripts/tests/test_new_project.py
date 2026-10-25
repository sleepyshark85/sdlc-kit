"""Tests for new_project.py, on the kit's real template and packs. Run:
python3 -m unittest discover -s plugins/sdlc-kit/scripts/tests"""
import importlib.util
import json
import os
import tempfile
import tomllib
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "new_project.py")
spec = importlib.util.spec_from_file_location("new_project", SCRIPT)
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)
rules_spec = importlib.util.spec_from_file_location(
    "workflow_rules", os.path.join(kit.TEMPLATE, ".github", "workflow_rules.py"))
workflow_rules = importlib.util.module_from_spec(rules_spec)
rules_spec.loader.exec_module(workflow_rules)


class NewProjectTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="new-project-")
        self.addCleanup(scratch.cleanup)
        self.target = os.path.join(scratch.name, "shop")

    def read(self, *path):
        with open(os.path.join(self.target, *path), encoding="utf-8") as file:
            return file.read()

    def test_a_project_is_named_and_has_the_template(self):
        kit.create(self.target, "Shop", [])

        self.assertIn("# Shop — working notes", self.read("CLAUDE.md"))
        self.assertNotIn("{{project}}", self.read("README.md"))
        self.assertTrue(os.path.exists(os.path.join(self.target, ".github", "review_gate.py")))

    def test_a_non_empty_folder_is_refused(self):
        os.makedirs(self.target)
        with open(os.path.join(self.target, "keep.txt"), "w", encoding="utf-8") as file:
            file.write("mine\n")

        with self.assertRaisesRegex(kit.KitError, "is not empty"):
            kit.create(self.target, "Shop", [])

    def test_the_dotnet_pack_registers_everywhere_the_template_needs_it(self):
        checks = kit.create(self.target, "Shop", ["dotnet"])

        with open(os.path.join(self.target, ".sdlc", "checks.toml"), "rb") as file:
            components = tomllib.load(file)["component"]
        self.assertEqual(["dotnet"], [component["name"] for component in components])
        self.assertIn("          - language: csharp\n            build-mode: none\n",
                      self.read(".github", "workflows", "codeql.yml"))
        self.assertIn("package-ecosystem: nuget", self.read(".github", "dependabot.yml"))
        hooks = json.loads(self.read(".claude", "settings.json"))["hooks"]["PostToolUse"]
        self.assertEqual('python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/cs-rules.py"', hooks[0]["hooks"][0]["command"])
        self.assertTrue(os.path.exists(os.path.join(self.target, ".github", "workflows", "dotnet.yml")))
        self.assertIn("dotnet-ubuntu", checks)

    def test_the_dotnet_pack_sets_up_its_toolchain_before_the_daily_suite(self):
        kit.create(self.target, "Shop", ["dotnet"])

        daily = self.read(".github", "workflows", "daily.yml")
        self.assertIn("    steps:\n      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n\n"
                      "      - uses: actions/setup-dotnet@a98b56852c35b8e3190ac28c8c2271da59106c68 # v6.0.0\n"
                      "        with:\n          global-json-file: dotnet/global.json\n\n      - name: Suite\n", daily)
        self.assertEqual([], workflow_rules.breaches("daily.yml", daily))

    def test_the_dotnet_component_names_its_daily_suite_and_flag_variable(self):
        kit.create(self.target, "Shop", ["dotnet"])

        with open(os.path.join(self.target, ".sdlc", "checks.toml"), "rb") as file:
            component = tomllib.load(file)["component"][0]
        self.assertEqual(([["dotnet", "restore", "--locked-mode"],
                           ["dotnet", "test", "--configuration", "Release", "--nologo", "--blame-hang-timeout", "2m"]],
                          "Flags__{flag}"),
                         (component["daily"], component["flag_variable"]))

    def test_a_daily_run_without_its_suite_step_is_refused(self):
        kit.create(self.target, "Shop", [])
        daily = os.path.join(self.target, ".github", "workflows", "daily.yml")
        kit.write(daily, kit.read(daily).replace("      - name: Suite\n", "      - name: Tests\n"))

        with self.assertRaisesRegex(kit.KitError, "daily.yml has no suite step"):
            kit.add_pack(self.target, "dotnet")

    def test_adding_a_pack_twice_changes_nothing(self):
        kit.create(self.target, "Shop", ["dotnet"])
        before = [self.read(".github", "workflows", name) for name in ("codeql.yml", "daily.yml")]

        kit.add_pack(self.target, "dotnet")

        self.assertEqual(before, [self.read(".github", "workflows", name) for name in ("codeql.yml", "daily.yml")])

    def test_an_unknown_pack_is_refused(self):
        kit.create(self.target, "Shop", [])

        with self.assertRaisesRegex(kit.KitError, "No pack named cobol"):
            kit.add_pack(self.target, "cobol")

    def test_an_unknown_pack_leaves_no_project_behind(self):
        with self.assertRaisesRegex(kit.KitError, "No pack named dotnett"):
            kit.create(self.target, "Shop", ["dotnet", "dotnett"])

        self.assertFalse(os.path.exists(self.target))

    def test_a_pack_never_replaces_a_project_file(self):
        kit.create(self.target, "Shop", [])
        os.makedirs(os.path.join(self.target, "dotnet"))
        with open(os.path.join(self.target, "dotnet", "global.json"), "w", encoding="utf-8") as file:
            file.write("{}\n")

        with self.assertRaisesRegex(kit.KitError, "already exists"):
            kit.add_pack(self.target, "dotnet")


if __name__ == "__main__":
    unittest.main()
