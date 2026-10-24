"""Tests for .claude/hooks/cs-rules.py's requirement IDs. Run with `python3 -m unittest discover -s .github`."""
import importlib.util
import os
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "cs_rules", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude", "hooks",
                             "cs-rules.py"))
cs_rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs_rules)


def write(root, relative, text):
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


class RequirementIdsTest(unittest.TestCase):
    def test_the_short_form_names_the_prefixes(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "REQUIREMENTS.md", "| ID | Requirement |\n|---|---|\n| API-01 | When … |\n")

            ids = cs_rules.requirement_ids(root)

        self.assertIsNotNone(ids.search("// API-01"))
        self.assertIsNone(ids.search("// SEC-01"))

    def test_the_split_form_names_the_prefixes_of_every_file(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "REQUIREMENTS.md", "# Requirements\n\nSplit: see docs/requirements/README.md.\n")
            write(root, os.path.join("docs", "requirements", "api.md"), "| API-01 | When … |\n")
            write(root, os.path.join("docs", "requirements", "quality.md"), "| SEC-02 | Security | … |\n")

            ids = cs_rules.requirement_ids(root)

        self.assertIsNotNone(ids.search("// API-01"))
        self.assertIsNotNone(ids.search("// SEC-02"))

    def test_the_split_form_without_a_root_file_names_the_prefixes(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, os.path.join("docs", "requirements", "api.md"), "| API-01 | When … |")
            write(root, os.path.join("docs", "requirements", "orders.md"), "| ORD-01 | When … |\n")

            ids = cs_rules.requirement_ids(root)

        self.assertIsNotNone(ids.search("// API-01"))
        self.assertIsNotNone(ids.search("// ORD-01"))

    def test_an_unreadable_requirements_file_is_an_error_not_a_skipped_file(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "docs", "requirements", "broken.md"))

            with self.assertRaises(OSError):
                cs_rules.requirement_ids(root)

    def test_no_requirements_means_no_check(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(cs_rules.requirement_ids(root))


if __name__ == "__main__":
    unittest.main()
