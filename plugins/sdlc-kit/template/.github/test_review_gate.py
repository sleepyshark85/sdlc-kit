"""Tests for review_gate.py: each builds a pull request in a scratch repository and runs the gate on it as the review
workflow does. Run with `python3 -m unittest discover -s .github`."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

GATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_gate.py")
BLOCK = "a\nb\nc\nd\ne\nf\n"
TEN_LINES = "".join(f"{n}\n" for n in range(1, 11))


def verdict(state, commit, by="OWNER", login="owner"):
    return {"author_association": by, "user": {"login": login},
            "body": f"**Verdict: {state}** at {commit}\n\nChecked."}


def approve(commit, by="OWNER", login="owner"):
    return verdict("APPROVE", commit, by, login)


def request_changes(commit, by="OWNER"):
    return verdict("CHANGES REQUESTED", commit, by)


def waiting(head, reason=None):
    description = f"Waiting for a verdict naming {head[:7]} in full"
    return "pending", f"{description}; {reason}" if reason else description


def carried(approved):
    return "success", f"Approval at {approved[:7]} carried over clean merges of main"


class ReviewGateTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="review-gate-")
        self.addCleanup(scratch.cleanup)
        self.repo = scratch.name
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.commit({"app.txt": "one\ntwo\nthree\n", "other.txt": "other\n"})
        self.git("switch", "--quiet", "--create", "pr")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True,
                              check=True).stdout.strip()

    def write(self, files):
        for path, content in files.items():
            with open(os.path.join(self.repo, path), "w", encoding="utf-8") as file:
                file.write(content)

    def commit(self, files):
        self.write(files)
        self.git("add", "--all")
        self.git("commit", "--quiet", "--message", "change")
        return self.git("rev-parse", "HEAD")

    def on_main(self, files):
        self.git("switch", "--quiet", "main")
        self.commit(files)
        self.git("switch", "--quiet", "pr")

    def merge_main(self):
        self.git("merge", "--quiet", "--no-edit", "--no-ff", "main")
        return self.git("rev-parse", "HEAD")

    def amend_merge(self, files):
        self.write(files)
        self.git("add", "--all")
        self.git("commit", "--quiet", "--amend", "--no-edit")
        return self.git("rev-parse", "HEAD")

    def gate(self, *comments, base="main", reviewers=""):
        self.git("update-ref", f"refs/remotes/origin/{base}", base)
        env = {**os.environ, "REVIEWERS": reviewers}
        run = subprocess.run([sys.executable, GATE, self.git("rev-parse", "pr"), base, "main"], cwd=self.repo,
                             input=json.dumps(comments), capture_output=True, text=True, env=env)
        if run.returncode != 0:
            self.fail(f"review_gate.py exited {run.returncode}: {run.stderr.strip()}")
        return tuple(run.stdout.rstrip("\n").split("\t"))

    def test_an_approval_naming_the_head_passes(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})

        self.assertEqual(("success", f"Approved at {head[:7]}"), self.gate(approve(head)))

    def test_without_a_verdict_it_waits(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})

        self.assertEqual(waiting(head), self.gate())

    def test_changes_requested_at_the_head_fail(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})

        self.assertEqual(("failure", f"Changes requested at {head[:7]}"),
                         self.gate(approve(head), request_changes(head)))

    def test_changes_requested_quoting_an_approval_fail(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        verdict = request_changes(head)
        verdict["body"] += f"\n\nReplaces **Verdict: APPROVE** at {head}."

        self.assertEqual(("failure", f"Changes requested at {head[:7]}"), self.gate(approve(head), verdict))

    def test_a_verdict_naming_the_head_but_approving_another_commit_fails(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        head = self.commit({"app.txt": "one\ntwo\nthree\nfive\n"})
        verdict = approve(approved)
        verdict["body"] += f"\n\nThe next commit, {head}, is not reviewed."

        self.assertEqual(("failure", f"Changes requested at {head[:7]}"), self.gate(verdict))

    def test_a_comment_that_is_not_a_verdict_is_ignored(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        remark = {"author_association": "OWNER", "body": f"Merged after {head}."}

        self.assertEqual(("success", f"Approved at {head[:7]}"), self.gate(approve(head), remark))

    def test_a_short_sha_is_not_a_verdict(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})

        self.assertEqual(waiting(head), self.gate(approve(head[:7])))

    def test_a_verdict_by_someone_who_is_not_a_collaborator_is_ignored(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})

        for author in ("CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "NONE"):
            with self.subTest(author=author):
                self.assertEqual(("success", f"Approved at {head[:7]}"),
                                 self.gate(approve(head), request_changes(head, by=author)))
                self.assertEqual(waiting(head), self.gate(approve(head, by=author)))

    def test_with_reviewers_named_only_their_verdicts_count(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        by_developer = approve(head, login="owner")

        self.assertEqual(waiting(head), self.gate(by_developer, reviewers="review-bot"))
        self.assertEqual(("success", f"Approved at {head[:7]}"),
                         self.gate(by_developer, approve(head, login="review-bot"), reviewers="review-bot, owner2"))

    def test_with_reviewers_named_a_collaborators_changes_requested_do_not_count(self):
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})

        self.assertEqual(("success", f"Approved at {head[:7]}"),
                         self.gate(approve(head, login="review-bot"), request_changes(head), reviewers="review-bot"))

    def test_an_approval_carries_over_a_clean_merge_of_the_base(self):
        rejected = self.commit({"app.txt": "one\ntwo\nthree\nfive\n"})
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        self.merge_main()

        self.assertEqual(carried(approved), self.gate(request_changes(rejected), approve(approved)))

    def test_an_approval_carries_over_several_clean_merges_when_the_base_changed_the_same_file(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.on_main({"app.txt": "zero\none\ntwo\nthree\n"})
        self.merge_main()
        self.on_main({"other.txt": "other\nmore\n"})
        self.merge_main()

        self.assertEqual(carried(approved), self.gate(approve(approved)))

    def test_an_approval_by_a_non_collaborator_does_not_carry(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        head = self.merge_main()

        self.assertEqual(waiting(head), self.gate(approve(approved, by="CONTRIBUTOR")))

    def test_an_approval_does_not_carry_over_merges_of_a_base_other_than_the_default_branch(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.git("switch", "--quiet", "--create", "stack", "main")
        self.commit({"sneaked.txt": "unreviewed\n"})
        self.git("switch", "--quiet", "pr")
        self.git("merge", "--quiet", "--no-edit", "stack")
        head = self.git("rev-parse", "HEAD")

        self.assertEqual(waiting(head, "approvals carry over merges of main only"),
                         self.gate(approve(approved), base="stack"))

    def test_an_approval_does_not_carry_over_merges_leaving_more_than_one_merge_base(self):
        # The first merge drops the side branch's line, which the second merge, of the trunk only, doesn't bring back.
        self.git("switch", "--quiet", "--create", "side", "main")
        side = self.commit({"other.txt": "other\nchecked\n"})
        self.on_main({"app.txt": "zero\none\ntwo\nthree\n"})
        trunk = self.git("rev-parse", "main")
        self.git("switch", "--quiet", "main")
        self.git("merge", "--quiet", "--no-edit", "--no-ff", "side")
        self.git("switch", "--quiet", "pr")
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.git("merge", "--quiet", "--no-edit", "--strategy=ours", side)
        self.git("merge", "--quiet", "--no-edit", "--no-ff", trunk)
        head = self.git("rev-parse", "HEAD")

        self.assertEqual(waiting(head, "it has more than one merge base with the base"), self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_commit_of_the_author(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        self.merge_main()
        head = self.commit({"app.txt": "one\ntwo\nthree\nfour\nfive\n"})

        self.assertEqual(waiting(head, f"{head[:7]} is not a merge of the base"), self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_merge_of_another_branch(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.git("switch", "--quiet", "--create", "side", "main")
        self.commit({"other.txt": "other\nmore\n"})
        self.git("switch", "--quiet", "pr")
        self.git("merge", "--quiet", "--no-edit", "side")
        head = self.git("rev-parse", "HEAD")

        self.assertEqual(waiting(head, f"{head[:7]} is not a merge of the base"), self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_an_octopus_merge(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.git("switch", "--quiet", "--create", "side", "main")
        self.commit({"side.txt": "side\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        self.git("merge", "--quiet", "--no-edit", "main", "side")
        head = self.git("rev-parse", "HEAD")

        self.assertEqual(waiting(head, f"{head[:7]} is not a merge of the base"), self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_merge_whose_resolution_changed_the_change(self):
        approved = self.commit({"app.txt": "one\nTWO\nthree\n"})
        self.on_main({"app.txt": "one\n2\nthree\n"})
        conflict = subprocess.run(["git", "merge", "--quiet", "--no-edit", "main"], cwd=self.repo, capture_output=True)
        self.assertEqual(1, conflict.returncode)
        self.write({"app.txt": "one\nTWO 2\nthree\n"})
        self.git("commit", "--quiet", "--no-edit", "--all")
        head = self.git("rev-parse", "HEAD")

        self.assertEqual(waiting(head, f"its content is not a clean merge of {approved[:7]}"),
                         self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_merge_that_adds_content(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        self.merge_main()
        head = self.amend_merge({"sneaked.txt": "unreviewed\n"})

        self.assertEqual(waiting(head, f"its content is not a clean merge of {approved[:7]}"),
                         self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_merge_that_changes_whitespace_in_the_change(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\n    four\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        self.merge_main()
        head = self.amend_merge({"app.txt": "one\ntwo\nthree\n  four\n"})

        self.assertEqual(waiting(head, f"its content is not a clean merge of {approved[:7]}"),
                         self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_merge_that_changes_a_binary_file_of_the_change(self):
        approved = self.commit({"app.bin": "\0one\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        self.merge_main()
        head = self.amend_merge({"app.bin": "\0two\n"})

        self.assertEqual(waiting(head, f"its content is not a clean merge of {approved[:7]}"),
                         self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_merge_that_moves_the_change_to_identical_code(self):
        # The added line keeps its context, only in the other copy of the block, so the patch ids are equal.
        self.on_main({"app.txt": f"first\n{BLOCK}middle\n{BLOCK}last\n"})
        self.git("reset", "--quiet", "--hard", "main")
        extended = BLOCK.replace("c\n", "c\nadded\n")
        approved = self.commit({"app.txt": f"first\n{BLOCK}middle\n{extended}last\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        self.merge_main()
        head = self.amend_merge({"app.txt": f"first\n{extended}middle\n{BLOCK}last\n"})

        self.assertEqual(waiting(head, f"its content is not a clean merge of {approved[:7]}"),
                         self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_clean_merge_that_already_made_part_of_the_change(self):
        self.on_main({"app.txt": TEN_LINES})
        self.git("reset", "--quiet", "--hard", "main")
        approved = self.commit({"app.txt": TEN_LINES.replace("1\n", "one\n").replace("10\n", "ten\n")})
        self.on_main({"app.txt": TEN_LINES.replace("1\n", "one\n")})
        head = self.merge_main()

        self.assertEqual(waiting(head, f"its diff differs from {approved[:7]}"), self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_a_clean_merge_that_changed_whitespace_around_the_change(self):
        self.on_main({"app.txt": TEN_LINES})
        self.git("reset", "--quiet", "--hard", "main")
        approved = self.commit({"app.txt": TEN_LINES.replace("10\n", "ten\n")})
        self.on_main({"app.txt": TEN_LINES.replace("8\n", "8 \n")})
        head = self.merge_main()

        self.assertEqual(waiting(head, f"its diff differs from {approved[:7]}"), self.gate(approve(approved)))

    def test_an_approval_does_not_carry_over_when_a_later_verdict_requests_changes(self):
        approved = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        head = self.merge_main()

        self.assertEqual(waiting(head, "the newest verdict approves none of its commits"),
                         self.gate(approve(approved), request_changes(approved)))

    def test_an_approval_of_a_commit_of_the_base_does_not_carry(self):
        base = self.git("rev-parse", "main")
        reviewed = self.commit({"app.txt": "one\ntwo\nthree\nfour\n"})
        self.on_main({"other.txt": "other\nmore\n"})
        head = self.merge_main()
        verdict = approve(base)
        verdict["body"] += f"\n\nReviewed {reviewed}."

        self.assertEqual(waiting(head, "the newest verdict approves none of its commits"), self.gate(verdict))


class ReviewGateImportTest(unittest.TestCase):
    def test_importing_the_gate_decides_nothing(self):
        spec = importlib.util.spec_from_file_location("review_gate", GATE)
        module = importlib.util.module_from_spec(spec)
        output = io.StringIO()
        # Run as a script with these arguments, the gate would fail on their count.
        with contextlib.redirect_stdout(output), mock.patch("sys.argv", ["review_gate.py"]):
            spec.loader.exec_module(module)
        self.assertEqual((output.getvalue(), module.VERDICT_PREFIX), ("", "**Verdict:"))



class GitVersionTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("review_gate", GATE)
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)

    def test_a_git_older_than_the_gate_needs_is_too_old(self):
        self.assertTrue(self.gate.too_old("git version 2.38.1"))
        self.assertTrue(self.gate.too_old("git version 2.31.1.windows.1"))
        self.assertTrue(self.gate.too_old("git version 1.99.0"))

    def test_the_oldest_git_the_gate_needs_and_newer_ones_are_not(self):
        self.assertFalse(self.gate.too_old("git version 2.39.0"))
        self.assertFalse(self.gate.too_old("git version 2.47.1 (Apple Git-154)"))
        self.assertFalse(self.gate.too_old("git version 3.0.0"))

    def test_an_unreadable_version_counts_as_too_old(self):
        self.assertTrue(self.gate.too_old(""))
        self.assertTrue(self.gate.too_old("git version unknown"))

    def test_the_gate_refuses_a_git_too_old_before_reading_anything(self):
        with (mock.patch.object(self.gate, "git", return_value="git version 2.31.1\n"),
              mock.patch.object(self.gate, "decide") as decide,
              mock.patch("sys.argv", ["review_gate.py", "0" * 40, "main", "main"]),
              self.assertRaises(SystemExit) as stopped):
            self.gate.main()
        self.assertEqual("The review gate needs Git 2.39 or later; `git version` says: git version 2.31.1",
                         stopped.exception.code)
        decide.assert_not_called()

    def test_the_gate_decides_on_a_git_new_enough(self):
        with (mock.patch.object(self.gate, "git", return_value="git version 2.39.0\n"),
              mock.patch.object(self.gate, "decide", return_value=("pending", "waiting")) as decide,
              mock.patch("sys.argv", ["review_gate.py", "0" * 40, "main", "main"]),
              mock.patch("sys.stdin", io.StringIO("[]")),
              contextlib.redirect_stdout(io.StringIO()) as output):
            self.gate.main()
        decide.assert_called_once()
        self.assertEqual("pending\twaiting\n", output.getvalue())


if __name__ == "__main__":
    unittest.main()
