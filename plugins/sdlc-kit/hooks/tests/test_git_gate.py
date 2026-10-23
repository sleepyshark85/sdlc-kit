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
        self.write("docs/guide.md", "docs\n")
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

    def test_the_rest_of_a_heredoc_line_is_checked(self):
        self.assert_blocked("cat <<'EOF' > notes.md && git push origin HEAD:main\nbody\nEOF", "never push to main")

    def test_a_command_inside_a_wrapper_is_checked(self):
        for command in ("( git push origin HEAD:main )", "if true; then git push origin HEAD:main; fi",
                        "while true; do git push origin HEAD:main; done", "{ git push origin HEAD:main; }",
                        "! git push origin HEAD:main", "time -p git push origin HEAD:main",
                        "env -u BAR FOO=1 git push origin HEAD:main", "env -i git push origin HEAD:main",
                        "command git push origin HEAD:main", "exec git push origin HEAD:main",
                        "nohup git push origin HEAD:main", "echo x | xargs -n 1 git push origin HEAD:main",
                        'bash -c "git push origin HEAD:main"', "sh -lc 'git push origin HEAD:main'",
                        "zsh -c 'cd . && git push origin HEAD:main'", 'eval "git push origin HEAD:main"',
                        "bash <<'EOF'\ngit push origin HEAD:main\nEOF", "bash <<< 'git push origin HEAD:main'"):
            with self.subTest(command=command):
                self.assert_blocked(command, "never push to main")

    def test_a_command_substitution_is_checked(self):
        for command in ("echo `git push origin HEAD:main`", 'echo "`git push origin HEAD:main`"',
                        'echo "$(git push origin HEAD:main)"', 'echo "$(echo `git push origin HEAD:main`)"'):
            with self.subTest(command=command):
                self.assert_blocked(command, "never push to main")

    def test_a_single_quoted_substitution_is_text(self):
        self.assert_allowed("echo '`git push origin HEAD:main`' '$(git push origin HEAD:main)'")

    def test_a_heredoc_piped_into_a_shell_is_checked(self):
        for command in ("cat <<EOF | sh\ngit push origin HEAD:main\nEOF",
                        "cat <<'EOF' | tr a a | bash\ngit push origin HEAD:main\nEOF",
                        "cat <<< 'git push origin HEAD:main' | sh"):
            with self.subTest(command=command):
                self.assert_blocked(command, "never push to main")

    def test_a_commit_message_from_a_heredoc_substitution_is_allowed(self):
        self.assert_allowed("git commit -m \"$(cat <<'EOF'\nFix it (now)\n\ngit push origin main\nEOF\n)\"")

    def scratch_folder(self, prefix):
        """A new folder outside the repository, spelled with forward slashes for the command line."""
        folder = tempfile.TemporaryDirectory(prefix=prefix)
        self.addCleanup(folder.cleanup)
        return folder.name.replace("\\", "/")

    def test_the_agent_rules_apply_after_leaving_the_project(self):
        outside = self.scratch_folder("git-gate-outside-")
        for command, says in ((f'cd {outside} && gh pr comment 1 -R o/r --body "**Verdict: APPROVE** at abc"',
                               "only the reviewer posts verdicts"),
                              (f"cd {outside} && gh pr merge 1 -R o/r --merge", "gh pr merge --auto"),
                              (f"cd {outside} && env", "only the reviewer reads the environment"),
                              (f'cd {outside} && echo "$SDLC_REVIEWER_TOKEN"', "only the reviewer uses")):
            with self.subTest(command=command):
                self.assert_blocked(command, says, agent_type="sdlc-kit:fixer")

    def test_the_git_rules_follow_the_repository_a_command_acts_on(self):
        plain = self.scratch_folder("git-gate-plain-")
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=plain, check=True)
        self.assert_allowed(f"git -C {plain} commit -m x")

    def test_a_commit_in_a_subshell_after_moving_to_main_is_blocked(self):
        self.assert_blocked("git checkout main; (git commit -m x)", "never commit on main")

    def test_a_commit_that_stages_files_itself_is_blocked(self):
        self.write("app/main.py", "print(2)\n")
        for command in ("git commit app/main.py -m x", "git commit -m x -- app/main.py", "git commit -i -m x",
                        "git commit --only -m x", "git commit -qm x app/main.py", "git commit --include -m x",
                        "git commit --pathspec-from-file=paths.txt -m x"):
            with self.subTest(command=command):
                self.assert_blocked(command, "stage files in their own command")

    def test_commit_options_with_values_are_not_pathspecs(self):
        for command in ('git commit -m "fix app/main.py"', "git commit -qm x", "git commit --message=x",
                        "git commit -F msg.txt", "git commit -m x --author 'A <a@example.com>'",
                        "git commit -m x 2>&1 | tail -1", "git commit --trailer 'Co-Authored-By: A' -m x"):
            with self.subTest(command=command):
                self.assert_allowed(command)

    def test_a_verdict_in_any_body_form_is_found(self):
        self.write("v.md", "**Verdict: APPROVE** at abc\n")
        for command in ("gh pr comment 5 --body-file=v.md", "gh pr comment 5 -F v.md",
                        "gh pr review 5 --body-file v.md",
                        "gh api repos/o/r/issues/5/comments -F body=@v.md",
                        "gh api repos/o/r/issues/5/comments --field=body=@v.md",
                        "gh api repos/o/r/issues/5/comments --input v.md",
                        'gh issue comment 5 --body="**Verdict: APPROVE** at abc"'):
            with self.subTest(command=command):
                self.assert_blocked(command, "only the reviewer posts verdicts", agent_type="sdlc-kit:fixer")

    def test_a_body_the_hook_cannot_read_is_blocked(self):
        for command in ("gh pr comment 5 --body-file - <<'X'\n**Verdict: APPROVE** at abc\nX",
                        'gh pr comment 5 --body "$(cat v.md)"', "gh pr comment 5 --body `cat v.md`",
                        'B=x; gh pr comment 5 --body "$B"', "cat v.md | gh pr comment 5 -F -",
                        "gh pr comment 5 --body-file later.md", "gh api repos/o/r/issues/5/comments -F body=@-",
                        "gh api repos/o/r/issues/5/comments --input -",
                        'gh api repos/o/r/issues/5/comments -f body="$(cat v.md)"'):
            with self.subTest(command=command):
                self.assert_blocked(command, "can't read this body", agent_type="sdlc-kit:fixer")

    def test_readable_bodies_and_graphql_variables_are_allowed(self):
        self.write("notes.md", "Fixed in abc.\n")
        for command in ("gh pr comment 5 --body-file notes.md", "gh pr comment 5 --body 'Fixed.'",
                        "gh api graphql -f query='query($n: Int!) { viewer { login } }' -F n=5"):
            with self.subTest(command=command):
                self.assert_allowed(command, agent_type="sdlc-kit:fixer")

    def test_the_reviewer_posts_a_verdict_from_stdin(self):
        self.assert_allowed("gh pr comment 5 --body-file - <<'X'\n**Verdict: APPROVE** at abc\nX",
                            agent_type="sdlc-kit:reviewer")

    def test_printing_the_environment_is_blocked(self):
        for command in ("env", "env | grep TOKEN", "env FOO=1", "printenv", "printenv SDLC_REVIEWER_TOKEN", "export -p",
                        "export", "set", "set | grep SDLC"):
            with self.subTest(command=command):
                self.assert_blocked(command, "only the reviewer reads the environment", agent_type="sdlc-kit:fixer")
        self.assert_allowed("printenv HOME", agent_type="sdlc-kit:fixer")
        self.assert_allowed("set -e", agent_type="sdlc-kit:fixer")
        self.assert_allowed("env", agent_type="sdlc-kit:reviewer")

    def test_naming_the_token_without_expanding_it_is_allowed(self):
        self.assert_allowed("grep -rn SDLC_REVIEWER_TOKEN .", agent_type="sdlc-kit:fixer")
        self.assert_blocked('echo "${SDLC_REVIEWER_TOKEN}"', "only the reviewer uses", agent_type="sdlc-kit:fixer")

    def test_the_api_endpoint_is_found_after_option_values(self):
        for command in ('gh api -H "Accept: application/vnd.github+json" -X PATCH repos/o/r -f allow_squash_merge=true',
                        'gh api -X DELETE -H "Accept: application/vnd.github+json" repos/o/r/branches/main/protection',
                        "gh api --method=PATCH repos/o/r -f x=1", "gh api -XDELETE repos/o/r/rulesets/5",
                        "gh api -X PUT repos/o/r/pulls/1/merge", "gh api -X DELETE repos/o/r/git/refs/heads/x",
                        "gh api -X PATCH repos/o/r/git/refs/heads/x -F force=true",
                        "gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'",
                        "gh api graphql -f query='mutation { deleteRef(input: {}) { clientMutationId } }'"):
            with self.subTest(command=command):
                self.assert_blocked(command, "the owner's")


class NoConfigTest(unittest.TestCase):
    """A repository without .sdlc/checks.toml has not opted in: the hook enforces nothing there."""

    def test_nothing_is_enforced(self):
        scratch = tempfile.TemporaryDirectory(prefix="git-gate-plain-")
        self.addCleanup(scratch.cleanup)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=scratch.name, check=True)
        for command in ("git commit -m first", "git checkout -b wip", "git push origin main", "env",
                        'GH_TOKEN="$SDLC_REVIEWER_TOKEN" gh pr comment 5 --body "**Verdict: APPROVE** at abc"'):
            with self.subTest(command=command):
                payload = {"tool_input": {"command": command}, "cwd": scratch.name, "agent_type": "sdlc-kit:fixer"}
                run = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True)
                self.assertEqual(0, run.returncode, run.stderr)


if __name__ == "__main__":
    unittest.main()
