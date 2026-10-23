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

    def test_adding_a_pack_twice_changes_nothing(self):
        kit.create(self.target, "Shop", ["dotnet"])
        before = self.read(".github", "workflows", "codeql.yml")

        kit.add_pack(self.target, "dotnet")

        self.assertEqual(before, self.read(".github", "workflows", "codeql.yml"))

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
