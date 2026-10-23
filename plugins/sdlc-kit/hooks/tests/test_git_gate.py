"""Tests for git-gate.py: each runs the hook as Claude Code does, on a scratch repository. Run:
python3 -m unittest discover -s plugins/sdlc-kit/hooks/tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "git-gate.py")
BLOCKED = 2

CHECKS = """\
branch_prefixes = ["feature/", "fix/"]
shared = ["testdata/"]

[[component]]
name = "app"
paths = ["app/"]
code = '\\.py$'
directory = "app"
before_commit = [["{python}", "-c", "open('../commit-ran', 'a').write('app\\\\n')"]]
before_push = [["{python}", "-c", "open('../push-ran', 'a').write('app\\\\n')"]]

[[component]]
name = "web"
paths = ["web/"]
code = '\\.js$'
directory = "web"
before_commit = [["{python}", "-c", "import sys; sys.exit(1)"]]
before_push = [["{python}", "-c", "open('../push-ran', 'a').write('web\\\\n')"]]
"""


class GitGateTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="git-gate-")
        self.addCleanup(scratch.cleanup)
        self.repo = os.path.realpath(scratch.name)
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.write(".sdlc/checks.toml", CHECKS.replace("{python}", sys.executable.replace("\\", "/")))
        self.write("app/main.py", "print(1)\n")
        self.write("web/main.js", "1\n")
        self.git("add", "--all")
        self.git("commit", "--quiet", "--message", "start")
        self.git("update-ref", "refs/remotes/origin/main", "main")
        self.git("switch", "--quiet", "--create", "feature/x")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, check=True).stdout

    def write(self, path, content):
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as file:
            file.write(content)

    def ran(self, name):
        path = os.path.join(self.repo, name)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as file:
            return file.read().split()

    def hook(self, command, agent_type=None):
        payload = {"tool_input": {"command": command}, "cwd": self.repo}
        if agent_type:
            payload["agent_type"] = agent_type
        return subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True)

    def assert_blocked(self, command, says, agent_type=None):
        run = self.hook(command, agent_type)
        self.assertEqual(BLOCKED, run.returncode, run.stderr)
        self.assertIn(says, run.stderr)

    def assert_allowed(self, command, agent_type=None):
        run = self.hook(command, agent_type)
        self.assertEqual(0, run.returncode, run.stderr)

    def test_a_commit_on_main_is_blocked(self):
        self.git("switch", "--quiet", "main")
        self.assert_blocked("git commit -m x", "never commit on main")

    def test_a_push_to_main_is_blocked(self):
        for command in ("git push origin main", "git push origin HEAD:main", "git push origin feature/x:refs/heads/main",
                        "git push --all"):
            with self.subTest(command=command):
                self.assert_blocked(command, "main")

    def test_a_force_push_is_blocked(self):
        for command in ("git push -f", "git push --force-with-lease origin feature/x", "git push origin +feature/x"):
            with self.subTest(command=command):
                self.assert_blocked(command, "never force-push")

    def test_deleting_a_remote_branch_is_blocked(self):
        for command in ("git push origin --delete feature/y", "git push origin :feature/y"):
            with self.subTest(command=command):
                self.assert_blocked(command, "deleted by the merge")

    def test_a_branch_without_an_allowed_prefix_is_blocked(self):
        self.assert_blocked("git switch -c wip", "needs one of the prefixes feature/, fix/")

    def test_a_branch_with_a_prefix_from_the_config_is_allowed(self):
        self.assert_allowed("git switch -c fix/thing")

    def test_staging_in_the_commit_line_is_blocked(self):
        for command in ("git add . && git commit -m x", "git commit -am x"):
            with self.subTest(command=command):
                self.assert_blocked(command, "stage files in their own command")

    def test_a_commit_runs_the_checks_of_the_components_it_stages(self):
        self.write("app/main.py", "print(2)\n")
        self.git("add", "app/main.py")
        run = self.hook("git commit -m x")
        self.assertEqual((0, ["app"]), (run.returncode, self.ran("commit-ran")), run.stderr)
        self.assertIn("app/main.py", json.loads(run.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_a_failing_commit_check_blocks_the_commit(self):
        self.write("web/main.js", "2\n")
        self.git("add", "web/main.js")
        self.assert_blocked("git commit -m x", "web's before_commit check")

    def test_a_staged_file_with_unstaged_changes_is_blocked(self):
        self.write("app/main.py", "print(2)\n")
        self.git("add", "app/main.py")
        self.write("app/main.py", "print(3)\n")
        self.assert_blocked("git commit -m x", "also have unstaged changes")

    def test_a_push_tests_the_components_the_branch_changes_beyond_docs(self):
        self.write("app/main.py", "print(2)\n")
        self.write("web/README.md", "docs\n")
        self.git("add", "--all")
        self.git("commit", "--quiet", "--message", "change")
        self.assert_allowed("git push origin feature/x")
        self.assertEqual(["app"], self.ran("push-ran"))

    def test_a_shared_path_tests_every_component(self):
        self.write("testdata/case.json", "{}\n")
        self.git("add", "--all")
        self.git("commit", "--quiet", "--message", "change")
        self.assert_allowed("git push origin feature/x")
        self.assertEqual(["app", "web"], sorted(self.ran("push-ran")))

    def test_the_reviewer_never_commits_or_pushes(self):
        for command in ("git commit -m x", "git push origin feature/x"):
            with self.subTest(command=command):
                self.assert_blocked(command, "the reviewer judges", agent_type="sdlc-kit:reviewer")

    def test_only_the_reviewer_posts_a_verdict(self):
        command = 'gh pr comment 5 --body "**Verdict: APPROVE** at abc"'
        self.assert_blocked(command, "only the reviewer posts verdicts", agent_type="sdlc-kit:developer")
        self.assert_blocked(command, "only the reviewer posts verdicts")
        self.assert_allowed(command, agent_type="sdlc-kit:reviewer")

    def test_a_verdict_in_a_body_file_is_found(self):
        self.write("body.md", "**Verdict: APPROVE** at abc\n")
        self.assert_blocked("gh pr comment 5 --body-file body.md", "only the reviewer posts verdicts")

    def test_reading_verdicts_is_allowed(self):
        self.assert_allowed('gh pr view 5 --comments | grep "**Verdict:"')

    def test_only_the_reviewer_uses_the_reviewer_token(self):
        command = 'GH_TOKEN="$SDLC_REVIEWER_TOKEN" gh pr comment 5 --body "fine"'
        self.assert_blocked(command, "only the reviewer uses", agent_type="sdlc-kit:fixer")
        self.assert_allowed(command, agent_type="sdlc-kit:reviewer")

    def test_a_merge_waits_for_the_checks(self):
        self.assert_blocked("gh pr merge 5 --merge", "gh pr merge --auto")
        self.assert_allowed("gh pr merge 5 --auto --merge --delete-branch")

    def test_repository_settings_and_protection_are_the_owners(self):
        for command in ("gh repo edit --enable-auto-merge",
                        "gh api -X DELETE repos/o/r/branches/main/protection",
                        "gh api repos/{owner}/{repo}/rulesets -f name=x",
                        "gh api -X PATCH repos/o/r -f allow_squash_merge=true",
                        "gh api graphql -f query='mutation { deleteBranchProtectionRule(input: {}) { clientMutationId } }'"):
            with self.subTest(command=command):
                self.assert_blocked(command, "the owner's")

    def test_ordinary_gh_writes_are_allowed(self):
        for command in ("gh api repos/o/r/issues/5/comments -f body=thanks", "gh pr create --fill",
                        "gh api repos/o/r/branches/main/protection"):
            with self.subTest(command=command):
                self.assert_allowed(command)

    def test_a_heredoc_body_is_not_a_command(self):
        self.assert_allowed("cat <<'EOF' > notes.md\ngit push origin main\nEOF")


if __name__ == "__main__":
    unittest.main()
