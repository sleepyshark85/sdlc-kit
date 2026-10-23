"""Tests for .sdlc/sdlc_paths.py (which changes.py and the git hook share), links.py and workflow_rules.py. Run with
`python3 -m unittest discover -s .github`."""
import importlib.util
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, folder=HERE):
    spec = importlib.util.spec_from_file_location(name, os.path.join(folder, f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sdlc_paths = load("sdlc_paths", os.path.join(os.path.dirname(HERE), ".sdlc"))
links = load("links")
workflow_rules = load("workflow_rules")

CONFIG = {
    "shared": ["testdata/"],
    "component": [{"name": "dotnet", "paths": ["dotnet/"]}, {"name": "web", "paths": ["web/"]}],
}


class OwnersTest(unittest.TestCase):
    def test_each_path_belongs_to_its_owners(self):
        cases = {
            "dotnet/src/App.cs": {"dotnet"},
            "web/index.ts": {"web"},
            ".github/workflows/dotnet.yml": {"dotnet"},
            ".github/workflows/dotnet-mutation.yml": {"dotnet"},
            "testdata/case.json": {"dotnet", "web"},
            "docs/conventions.md": set(),
            "README.md": set(),
            "dotnet/README.md": {"dotnet"},
            ".claude/agents/reviewer.md": {"dotnet", "web"},
            ".github/workflows/review.yml": {"dotnet", "web"},
            "scripts/setup-repo.sh": {"dotnet", "web"},
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(expected, sdlc_paths.owners(CONFIG, path))

    def test_the_docs_pattern_comes_from_the_configuration(self):
        config = {**CONFIG, "docs": r"\.html$"}
        self.assertEqual((set(), {"dotnet", "web"}),
                         (sdlc_paths.owners(config, "docs/page.html"), sdlc_paths.owners(config, "docs/notes.md")))


class WorkflowRulesTest(unittest.TestCase):
    def test_each_breach_is_reported(self):
        sha = "3d3c42e5aac5ba805825da76410c181273ba90b1"
        cases = {
            f"permissions:\n  contents: read\njobs:\n  a:\n    steps:\n      - uses: actions/checkout@{sha} # v7\n": [],
            "permissions: read-all\njobs:\n  a:\n    uses: ./.github/workflows/shared.yml\n": [],
            f"jobs:\n  a:\n    permissions:\n      contents: read\n    steps:\n      - uses: actions/checkout@{sha}\n":
                ["w.yml: no top-level permissions"],
            "permissions: {}\njobs:\n  a:\n    steps:\n      - uses: actions/checkout@v7\n":
                ["w.yml: actions/checkout@v7 is not pinned to a commit sha"],
            "permissions: {}\njobs:\n  a:\n    steps:\n      - name: x\n        uses: 'o/a@main'\n":
                ["w.yml: o/a@main is not pinned to a commit sha"],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(expected, workflow_rules.breaches("w.yml", text))


class LinksTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="links-")
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name

    def write(self, path, text):
        full = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file:
            file.write(text)

    def test_slugs_follow_github(self):
        cases = {
            "How we work": "how-we-work",
            "Small tasks (step 2)": "small-tasks-step-2",
            "The `review` gate": "the-review-gate",
            "1. Requirements and plan": "1-requirements-and-plan",
            "Merge & release": "merge--release",
        }
        for heading, expected in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(expected, links.slug(heading))

    def test_a_repeated_heading_gets_a_number(self):
        self.assertEqual({"notes", "notes-1"}, links.anchors("## Notes\n\n## Notes\n"))

    def test_broken_files_and_anchors_are_reported_and_good_ones_pass(self):
        self.write("docs/a.md", "# A\n\n## How we work\n\n```\n[not a link](missing.md)\n```\n")
        self.write("README.md", "[ok](docs/a.md#how-we-work) [self](#readme) [web](https://example.com)\n"
                                "[gone](docs/b.md) [bad](docs/a.md#nowhere) ![img](logo.png)\n\n# Readme\n")

        problems = links.broken_links(self.root, ["README.md", "docs/a.md"])

        self.assertEqual([("README.md", "docs/b.md", "no such file"),
                          ("README.md", "docs/a.md#nowhere", "no such heading")], problems)

    def test_markdown_files_are_the_tracked_ones(self):
        subprocess.run(["git", "init", "--quiet"], cwd=self.root, check=True)
        self.write("tracked.md", "x\n")
        self.write("untracked.md", "x\n")
        subprocess.run(["git", "add", "tracked.md"], cwd=self.root, check=True)

        self.assertEqual(["tracked.md"], links.markdown_files(self.root))


if __name__ == "__main__":
    unittest.main()
