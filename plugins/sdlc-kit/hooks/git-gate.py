#!/usr/bin/env python3
"""Before a Bash command: enforces the git and GitHub rules of docs/conventions.md, and runs the project's checks.

Rules for every agent: no commit on the default branch and no push to it; branch names with an allowed prefix; files
staged in their own command before a commit; no force push and no remote branch deletion; `gh pr merge` only with
`--auto`, which waits for the required checks; no change to branch protection, rulesets or repository settings. The
reviewer never commits or pushes. Any other agent never posts a verdict or uses the reviewer's token.

Checks come from `.sdlc/checks.toml` at the repository root (see the template's copy): before a commit that stages a
component's code, its `before_commit` commands; before a push that changes it beyond docs, its `before_push`
commands. Without that file only the rules apply. CI runs the same checks; these find a failure before the commit or
push instead of after it."""
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib

DEFAULT_BRANCH = "main"
PREFIXES = ("feature/", "fix/", "refactor/", "docs/", "chore/", "test/")
DOCS = r"\.(md|html|svg|png)$"
CONFIG = os.path.join(".sdlc", "checks.toml")
REVIEWER_TOKEN = "SDLC_REVIEWER_TOKEN"
VERDICT = "**Verdict:"
OPERATORS = set(";&|\n")
# A heredoc's body is input to a command, never a command: from "<<WORD" to the line holding only WORD.
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
# GitHub endpoints whose change weakens the merge rules: branch protection, rulesets, the repository's settings.
GUARDED_ENDPOINT = re.compile(r"^/?repos/[^/]+/[^/]+(/(branches/[^/]+/protection.*|rulesets.*))?/?$")
GUARDED_MUTATION = re.compile(r"\b(\w*BranchProtectionRule|\w*RepositoryRuleset|updateRepository)\b")
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def git(cwd, *args):
    run = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return run.stdout.strip() if run.returncode == 0 else ""


def commands(text):
    """Each simple command in the text, as words; quoted text, newlines included, stays one word."""
    lexer = shlex.shlex(HEREDOC.sub("", text), posix=True, punctuation_chars=";&|\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    words = []
    for token in lexer:
        if token and set(token) <= OPERATORS:
            if words:
                yield words
            words = []
        else:
            words.append(token)
    if words:
        yield words


def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def resolve(cwd, path):
    return os.path.normpath(path if os.path.isabs(path) else os.path.join(cwd, path))


def is_reviewer(agent_type):
    """Whether the calling agent is the reviewer; a plugin's agent type carries the plugin's name as a prefix."""
    return (agent_type or "").split(":")[-1] == "reviewer"


def load_config(root):
    """The project's checks, or an empty configuration when it has none."""
    path = os.path.join(root, CONFIG)
    if not root or not os.path.exists(path):
        return {}
    with open(path, "rb") as file:
        try:
            return tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            block(f"Blocked: {CONFIG} does not parse ({error}); fix it first.")


def owners(config, path):
    """The components a path belongs to: those whose path prefixes match it, or all of them for a shared path."""
    components = config.get("component", [])
    if path.startswith(tuple(config.get("shared", []))):
        return components
    return [component for component in components if path.startswith(tuple(component.get("paths", [""])))]


def check(cwd, command, failure):
    """Runs a check; a failure, or a missing command, blocks with the check's last lines."""
    try:
        run = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        block(f"{failure}\n'{command[0]}' is not on PATH (README.md lists the prerequisites).")
    if run.returncode != 0:
        tail = "\n".join((run.stdout + run.stderr).strip().splitlines()[-30:])
        block(f"{failure}\n{tail}")


def run_checks(root, components, step):
    for component in components:
        directory = os.path.join(root, component.get("directory", ""))
        for command in component.get(step, []):
            check(directory, command, f"Blocked: {component['name']}'s {step} check `{' '.join(command)}` fails; "
                                      "fix it, then try again.")


def before_commit(here, config):
    """The checks of each component whose code the commit stages. They read the working tree, so every staged code
    file must have no unstaged changes."""
    root = git(here, "rev-parse", "--show-toplevel")
    staged = git(here, "diff", "--cached", "--name-only").splitlines()
    touched, code = [], []
    for component in config.get("component", []):
        pattern = re.compile(component.get("code", "."))
        files = [path for path in staged if component in owners(config, path) and pattern.search(path)]
        if files:
            touched.append(component)
            code += files
    partly = set(code) & set(git(here, "diff", "--name-only").splitlines())
    if partly:
        block("Blocked: these staged files also have unstaged changes; stage or stash them first:\n"
              + "\n".join(sorted(partly)))
    run_checks(root, touched, "before_commit")


def before_push(here, branch, config):
    """The tests of each component the branch changes beyond docs, against the default branch."""
    root = git(here, "rev-parse", "--show-toplevel")
    base = git(here, "merge-base", f"origin/{DEFAULT_BRANCH}", branch or "HEAD")
    docs = re.compile(config.get("docs", DOCS))
    if base:
        changed = git(here, "diff", "--no-renames", "--name-only", base, branch or "HEAD").splitlines()
        touched = [c for c in config.get("component", [])
                   if any(c in owners(config, path) for path in changed if not docs.search(path))]
    else:
        touched = config.get("component", [])
    run_checks(root, touched, "before_push")


def stages_all(rest):
    """Whether commit options stage every tracked change themselves: -a, --all, or -a in a cluster such as -am."""
    for arg in rest:
        if arg in ("-a", "--all"):
            return True
        if re.fullmatch(r"-[A-Za-z]+", arg):
            for flag in arg[1:]:
                if flag == "a":
                    return True
                if flag in "mFCct":
                    break
    return False


def body_files(cwd, rest):
    """The text of the files a gh command takes its body from (--body-file, -F)."""
    texts = []
    for flag, value in zip(rest, rest[1:]):
        if flag in ("--body-file", "-F") and value != "-":
            try:
                with open(resolve(cwd, value), encoding="utf-8") as file:
                    texts.append(file.read())
            except OSError:
                pass
    return texts


def api_writes(rest):
    """Whether a `gh api` command writes: an explicit write method, or fields, which make gh send a POST."""
    method = next((value.upper() for flag, value in zip(rest, rest[1:]) if flag in ("-X", "--method")), None)
    fields = any(arg in ("-f", "-F", "--field", "--raw-field", "--input") for arg in rest)
    return method in WRITE_METHODS or (method is None and fields)


def check_gh(cwd, rest, agent_type):
    """The rules for a gh command."""
    api = rest[:1] == ["api"]
    posts = rest[:2] in (["pr", "comment"], ["pr", "review"], ["issue", "comment"]) or (api and api_writes(rest))
    if posts and not is_reviewer(agent_type) and (
            any(VERDICT in arg for arg in rest) or any(VERDICT in body for body in body_files(cwd, rest))):
        block("Blocked: only the reviewer posts verdicts (docs/conventions.md, Who codes and reviews).")
    if rest[:2] == ["pr", "merge"] and "--auto" not in rest:
        block("Blocked: merge with `gh pr merge --auto`, which waits for the required checks and the review gate.")
    if rest[:2] in (["repo", "edit"], ["repo", "delete"], ["repo", "rename"]):
        block("Blocked: repository settings are the owner's; ask the owner.")
    if api and api_writes(rest):
        endpoint = next((arg for arg in rest[1:] if not arg.startswith("-") and "/" in arg), "")
        mutation = rest[1:2] == ["graphql"] and any(GUARDED_MUTATION.search(arg) for arg in rest)
        if GUARDED_ENDPOINT.match(endpoint) or mutation:
            block("Blocked: branch protection, rulesets and repository settings are the owner's; ask the owner.")


def check_push(rest, branch):
    """The rules for a git push; returns the branch it pushes."""
    if "--all" in rest or "--mirror" in rest:
        block(f"Blocked: pushing every branch pushes {DEFAULT_BRANCH} too. Push the branch itself.")
    if any(arg in ("-f", "--force", "--force-with-lease", "--force-if-includes") or arg.startswith("--force")
           for arg in rest):
        block("Blocked: never force-push; add commits, and merge the base instead of rebasing.")
    if "-d" in rest or "--delete" in rest:
        block("Blocked: branches are deleted by the merge (`gh pr merge --auto --delete-branch`), never by hand.")
    refspecs = [arg for arg in rest if not arg.startswith("-")][1:]
    if any(spec.startswith("+") for spec in refspecs):
        block("Blocked: never force-push; add commits, and merge the base instead of rebasing.")
    if any(spec.startswith(":") for spec in refspecs):
        block("Blocked: branches are deleted by the merge (`gh pr merge --auto --delete-branch`), never by hand.")
    targets = [spec.split(":")[-1] for spec in refspecs] or [branch]
    targets = [branch if target in ("HEAD", "@") else target.removeprefix("refs/heads/") for target in targets]
    if DEFAULT_BRANCH in targets:
        block(f"Blocked: never push to {DEFAULT_BRANCH}. Push a branch and open a pull request.")
    sources = [spec.split(":")[0] for spec in refspecs]
    return branch if not sources or sources[0] in ("", "HEAD", "@") else sources[0]


def new_branch(verb, rest, positional):
    """The branch a command creates, or None."""
    if verb in ("switch", "checkout"):
        for flag in ("-c", "-C", "-b", "-B", "--create", "--force-create"):
            if flag in rest and rest.index(flag) + 1 < len(rest):
                return rest[rest.index(flag) + 1]
    elif verb == "worktree" and rest[:1] == ["add"] and "-b" in rest and rest.index("-b") + 1 < len(rest):
        return rest[rest.index("-b") + 1]
    elif verb == "branch" and len(positional) in (1, 2) and not any(arg.startswith("-") for arg in rest):
        return positional[0]
    return None


def main():
    payload = json.load(sys.stdin)
    text = payload.get("tool_input", {}).get("command", "")
    cwd = payload.get("cwd") or "."
    agent_type = payload.get("agent_type")
    if not is_reviewer(agent_type) and REVIEWER_TOKEN in text:
        block("Blocked: only the reviewer uses the reviewer's token.")
    branches, checks, staged, staging = {}, [], None, False
    try:
        parsed = list(commands(text))
    except ValueError:
        # Unbalanced quotes: the shell will reject it too, but never let a commit on the default branch through.
        if git(cwd, "branch", "--show-current") == DEFAULT_BRANCH and re.search(r"\bgit\b[^\n]*\bcommit\b", text):
            block(f"Blocked: never commit on {DEFAULT_BRANCH}. Create a branch first.")
        return

    for words in parsed:
        # Leading assignments, such as GH_TOKEN=… gh …, belong to the command that follows them.
        while words and re.match(r"^\w+=", words[0]):
            words = words[1:]
        if not words:
            continue
        if words[0] == "cd" and len(words) > 1:
            cwd = resolve(cwd, words[1])
            continue
        if words[0] == "gh":
            check_gh(cwd, words[1:], agent_type)
            continue
        if words[0] != "git":
            continue
        here, args = cwd, words[1:]
        while args and args[0].startswith("-"):
            if args[0] in ("-C", "-c") and len(args) > 1:
                here = resolve(here, args[1]) if args[0] == "-C" else here
                args = args[2:]
            else:
                args = args[1:]
        if not args:
            continue
        verb, rest = args[0], args[1:]
        branch = branches.get(here) or git(here, "branch", "--show-current")
        positional = [arg for arg in rest if not arg.startswith("-")]
        config = load_config(git(here, "rev-parse", "--show-toplevel"))

        if verb in ("push", "commit") and is_reviewer(agent_type):
            block("Blocked: the reviewer judges a change and never commits or pushes it.")
        if verb == "push":
            pushed = check_push(rest, branch)
            checks.append(lambda here=here, pushed=pushed, config=config: before_push(here, pushed, config))
        elif verb in ("add", "rm", "mv"):
            staging = True
        elif verb == "commit":
            if branch == DEFAULT_BRANCH:
                block(f"Blocked: never commit on {DEFAULT_BRANCH}. Create a branch first.")
            # This hook runs before the whole line, so it sees the index only as it was before the line ran.
            if staging or stages_all(rest):
                block("Blocked: stage files in their own command before committing (no add/rm/mv in the same line, "
                      "no commit -a), so the checks see what the commit holds.")
            staged = git(here, "diff", "--cached", "--name-status")
            checks.append(lambda here=here, config=config: before_commit(here, config))

        new = new_branch(verb, rest, positional)
        if new is None and verb in ("switch", "checkout"):
            # Moving to an existing branch; checkout also takes paths, so only a name that is a branch counts.
            target = positional[0] if positional else None
            if target and "--" not in rest and (verb == "switch" or len(positional) == 1) and any(
                    git(here, "rev-parse", "--verify", "--quiet", ref)
                    for ref in (f"refs/heads/{target}", f"refs/remotes/origin/{target}")):
                branches[here] = target
        if new:
            prefixes = tuple(config.get("branch_prefixes", PREFIXES))
            # Resetting the local default branch to the remote's is normal; any other new branch needs a prefix.
            if new != DEFAULT_BRANCH and not new.startswith(prefixes):
                block(f"Blocked: branch '{new}' needs one of the prefixes {', '.join(prefixes)}.")
            if verb in ("switch", "checkout"):
                branches[here] = new

    # Run only once every command in the line has passed the rules above.
    for run in checks:
        run()
    if staged is not None:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "Files staged for this commit; check each one was changed on purpose:\n"
                                 + (staged or "(none)"),
        }}))


if __name__ == "__main__":
    main()
