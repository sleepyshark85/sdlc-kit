#!/usr/bin/env python3
"""Before a Bash command: enforces the git and GitHub rules of docs/conventions.md, and runs the project's checks.

A repository opts in with `.sdlc/checks.toml` at its top level (see the template's copy). The agent's rules apply to
every command of the line, wherever it runs, when the session's project opted in (the call's folder or
`CLAUDE_PROJECT_DIR` is in an opted-in repository): `gh pr merge` only with `--auto`, which waits for the required
checks; no change to branch protection, rulesets, repository settings, merges or branch refs through the API; and an
agent other than the reviewer never posts a verdict, never uses the reviewer's token and never prints the environment
that holds it (`env`, `printenv` with no name or the token's, `export` or `export -p`, `set` with no arguments,
`declare` or `typeset` with no names, bare or with `-p` or `-x`). The git rules and checks apply to each git
command in the repository it acts on, when that repository opted in: no commit on the default branch and no push to
it; branch names with an allowed prefix; files staged in their own command before a commit; no force push and no
remote branch deletion; the reviewer never commits or pushes.

Every simple command of the line is checked: those separated by `;`, `&`, `|`, `&&`, `||` or newlines; inside
subshells, `{ …; }` groups, `if` and loop bodies; after `!`, leading assignments and the wrappers `time`, `env`,
`command`, `exec`, `nohup` and `xargs`; in `bash`, `sh` or `zsh` `-c` scripts and `eval` text; in `$(…)` and backtick
command substitutions, quoted or not; and in a heredoc or here-string fed or piped into a shell (`sh <<EOF`,
`cat <<EOF | sh`). The hook guards against mistakes and casual misuse, not against a determined adversary: branch
protection and the review gate are the server-side backstop.

Checks come from `.sdlc/checks.toml`: before a commit that stages a component's code, its `before_commit` commands;
before a push that changes the component, its `before_push` commands. Which paths a component owns is decided by the
template's `.sdlc/sdlc_paths.py`, which CI's change detector shares. CI runs the same checks; these find a failure
before the commit or push instead of after it.

Each block is logged beside the session's transcripts (<session>/git-gate/<agent>.jsonl: time, agent type and the
reason's first line, never the command) for the agent-team report in docs/measuring.md."""
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
from datetime import datetime, timezone

HOOKS = os.path.dirname(os.path.abspath(__file__))
SDLC_PATHS = os.path.join(os.path.dirname(HOOKS), "template", ".sdlc", "sdlc_paths.py")
DEFAULT_BRANCH = "main"
PREFIXES = ("feature/", "fix/", "refactor/", "docs/", "chore/", "test/")
REVIEWER_TOKEN = "SDLC_REVIEWER_TOKEN"
TOKEN_EXPANSION = re.compile(r"\$\{?" + REVIEWER_TOKEN + r"\b")
VERDICT = "**Verdict:"
# Each block is logged beside the session's transcripts, as <session>/git-gate/<agent>.jsonl, for the agent-team
# report: its rule (the reason's first line), never the command, which may hold a secret.
BLOCK_LOG = "git-gate"
MAIN = "main"

SEPARATORS = set(";&|\n()")
PUNCTUATION = "".join(sorted(SEPARATORS)) + "<>"
# A heredoc's body is input to a command, never a command line of its own: from "<<WORD" to the line holding only
# WORD. The rest of the "<<WORD" line stays, as it holds more of the command line.
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?[ \t]*(['\"]?)(\w+)\1(?P<rest>[^\n]*)\n(?P<body>.*?)^[ \t]*\2[ \t]*$",
                     re.S | re.M)
HEREDOC_MARK = "\0heredoc"
ASSIGNMENT = re.compile(r"^\w+=")
KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "{", "}", "!"}
# Commands that run the command after their own options, with the options that take a value.
WRAPPERS = {
    "time": set(),
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"},
    "command": set(),
    "exec": {"-a"},
    "nohup": set(),
    "xargs": {"-a", "-d", "-E", "-I", "-L", "-n", "-P", "-s"},
}
PIPES = {"|", "|&"}
# Builtins that list every variable, exported ones included, when given no names: bare, or with -p or -x.
DECLARES = ("declare", "typeset")
DECLARE_LISTING_FLAGS = "px"
SHELLS = {"bash", "sh", "zsh"}
SHELL_VALUE_OPTIONS = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}

COMMIT_VALUE_FLAGS = "mFCct"
COMMIT_VALUE_OPTIONS = {"--author", "--date", "--file", "--template", "--fixup", "--squash", "--cleanup", "--message",
                        "--reuse-message", "--reedit-message", "--trailer"}
COMMIT_STAGING_FLAGS = "aio"
COMMIT_STAGING_OPTIONS = {"--all", "--include", "--only", "--pathspec-from-file"}

GH_POSTS = (["pr", "comment"], ["pr", "review"], ["issue", "comment"])
BODY_OPTIONS = ("-b", "--body")
BODY_FILE_OPTIONS = ("-F", "--body-file")
POST_VALUE_OPTIONS = {*BODY_OPTIONS, *BODY_FILE_OPTIONS, "-R", "--repo"}
API_VALUE_OPTIONS = {"-X", "--method", "-H", "--header", "-f", "-F", "--field", "--raw-field", "--input", "-q", "--jq",
                     "-t", "--template", "--hostname", "--cache", "-p", "--preview"}
API_METHOD_OPTIONS = ("-X", "--method")
API_FIELDS = {"-f", "--raw-field", "-F", "--field"}
API_FILE_FIELDS = {"-F", "--field"}
API_INPUT = "--input"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
STDIN = "-"
# Text the shell replaces before gh sees it, so the hook cannot read it.
SUBSTITUTION = re.compile(r"\$\(|`")
EXPANSION = re.compile(r"\$|`")
# The GraphQL document's field: its `$name` are GraphQL variables, not the shell's.
GRAPHQL_QUERY = "query"
GRAPHQL_ENDPOINT = "graphql"
# GitHub endpoints whose change weakens the merge rules or goes round them: the repository and its settings, branch
# protection, rulesets, a pull request's merge, and branch refs.
GUARDED_ENDPOINT = re.compile(
    r"^/?repos/[^/]+/[^/]+(/(branches/[^/]+/protection|rulesets|pulls/[^/]+/merge|git/refs)(/.*)?)?/?(\?.*)?$")
GUARDED_MUTATION = re.compile(
    r"\b(\w*BranchProtectionRule|\w*RepositoryRuleset|updateRepository|mergePullRequest|deleteRef|updateRefs?)\b")

COMMIT_STAGES = ("Blocked: stage files in their own command before committing (no add/rm/mv in the same line, no "
                 "commit -a, -i, -o or pathspec), so the checks see what the commit holds.")
BRANCH_DELETION = "Blocked: branches are deleted by the merge (GitHub deletes a merged branch), never by hand."
FORCE_PUSH = "Blocked: never force-push; add commits, and merge the base instead of rebasing."


def load_sdlc_paths():
    """The kit's shared rule for which component a path belongs to."""
    spec = importlib.util.spec_from_file_location("sdlc_paths", SDLC_PATHS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sdlc_paths = load_sdlc_paths()


def git(cwd, *args):
    try:
        run = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    except OSError:
        # A folder the line creates before using it, such as `mkdir x && cd x && git init`.
        return ""
    return run.stdout.strip() if run.returncode == 0 else ""


class Blocked(Exception):
    """A command the hook refuses, with the reason shown to the agent."""


def block(reason):
    raise Blocked(reason)


def log_block(payload, reason):
    """Appends the block to the session's log; a payload without a transcript (not from Claude Code) logs nothing."""
    transcript = payload.get("transcript_path")
    if not transcript:
        return
    agent = payload.get("agent_id") or MAIN
    path = os.path.join(os.path.splitext(transcript)[0], BLOCK_LOG, f"{agent}.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "agent_type": payload.get("agent_type") or MAIN, "rule": reason.split("\n", 1)[0]}
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def resolve(cwd, path):
    return os.path.normpath(path if os.path.isabs(path) else os.path.join(cwd, path))


def is_reviewer(agent_type):
    """Whether the calling agent is the reviewer; a plugin's agent type carries the plugin's name as a prefix."""
    return (agent_type or "").split(":")[-1] == "reviewer"


def load_config(root):
    """The project's checks, or None when the repository has not opted in to the rules."""
    if not root:
        return None
    try:
        return sdlc_paths.load(root)
    except FileNotFoundError:
        return None
    except tomllib.TOMLDecodeError as error:
        block(f"Blocked: {sdlc_paths.CONFIG} does not parse ({error}); fix it first.")


def mark_heredocs(text, bodies):
    """The text with each heredoc's body moved to bodies and replaced by a mark naming it."""
    def mark(match):
        bodies.append(match["body"])
        return f"<< {HEREDOC_MARK}{len(bodies) - 1}{match['rest']}"

    return HEREDOC.sub(mark, text)


def closing_parenthesis(text, start):
    """Where the `)` closing a `$(` that ends just before start is, or None; quoted parentheses don't count."""
    depth, quote, escaped = 1, None, False
    for at in range(start, len(text)):
        char = text[at]
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote:
            quote = None if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return at
    return None


def substitutions(text):
    """The commands of each backtick and quoted `$(…)` substitution in the text, which the shell runs before the
    command holding them. An unquoted `$(…)` is left out: the lexer splits it at its parentheses, so its commands are
    already the line's own."""
    found, quote, escaped, at = [], None, False, 0
    while at < len(text):
        char = text[at]
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote == "'":
            quote = None if char == "'" else quote
        elif char == "`":
            end = text.find("`", at + 1)
            while end > 0 and text[end - 1] == "\\":
                end = text.find("`", end + 1)
            if end < 0:
                break
            found.append(text[at + 1:end])
            at = end
        elif quote == '"' and text.startswith("$(", at) and not text.startswith("$((", at):
            end = closing_parenthesis(text, at + 2)
            if end is None:
                break
            found.append(text[at + 2:end])
            at = end
        elif char == '"':
            quote = None if quote else char
        elif char == "'" and not quote:
            quote = char
        at += 1
    return found


def commands(text, bodies):
    """Each simple command in the text, as its words without redirections, with the text a heredoc or here-string
    gives it as input (or None); a later stage of a pipeline is given the earlier stage's input, as the earlier stage
    may pass it on. Quoted text, newlines included, stays one word. The text's heredocs are marked in bodies."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    words, stdin, redirect = [], None, None
    for token in lexer:
        if redirect:
            if redirect == "<<" and token.startswith(HEREDOC_MARK):
                stdin = bodies[int(token.removeprefix(HEREDOC_MARK))]
            elif redirect == "<<<":
                stdin = token
            redirect = None
        elif token and set(token) <= SEPARATORS:
            if words:
                yield words, stdin
            words, stdin = [], stdin if token in PIPES else None
        elif token and set(token) <= set(PUNCTUATION):
            # A redirection: its target is the next word, and a file descriptor before it (2>) is not an argument.
            if words and words[-1].isdigit():
                words.pop()
            redirect = token
        else:
            words.append(token)
    if words:
        yield words, stdin


def skip_options(words, takes_value):
    """The words after a command's leading options; an option in takes_value consumes the next word."""
    while words and words[0].startswith("-") and words[0] != STDIN:
        option, words = words[0], words[1:]
        if option == "--":
            break
        if option in takes_value:
            words = words[1:]
    return words


def unwrap(words):
    """The command the words run: without leading assignments, shell keywords and wrappers such as `time` or `env`.
    A bare `env` is returned as it is, since it prints the environment."""
    while words:
        first = words[0]
        if ASSIGNMENT.match(first) or first in KEYWORDS:
            words = words[1:]
        elif first in WRAPPERS:
            rest = skip_options(words[1:], WRAPPERS[first])
            if first == "env" and all(ASSIGNMENT.match(word) for word in rest):
                return ["env"]
            words = rest
        else:
            return words
    return words


def shell_script(args, stdin):
    """The script a shell runs: its -c text, or the input it reads when it is given no script file."""
    words, takes_script = iter(args), False
    for arg in words:
        if arg in SHELL_VALUE_OPTIONS:
            next(words, None)
        elif arg.startswith(("-", "+")):
            takes_script = takes_script or (not arg.startswith("--") and "c" in arg)
        else:
            return arg if takes_script else None
    return stdin


def commit_stages_files(rest):
    """Whether a git commit stages files itself: -a, -i, -o, a pathspec, or a cluster holding one, such as -am."""
    words = iter(rest)
    for arg in words:
        if arg == "--":
            return next(words, None) is not None
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name in COMMIT_STAGING_OPTIONS:
                return True
            if name in COMMIT_VALUE_OPTIONS and "=" not in arg:
                next(words, None)
        elif arg.startswith("-") and arg != STDIN:
            for at, flag in enumerate(arg[1:], 1):
                if flag in COMMIT_STAGING_FLAGS:
                    return True
                if flag in COMMIT_VALUE_FLAGS:
                    if at == len(arg) - 1:
                        next(words, None)
                    break
        else:
            return True
    return False


def gh_options(args, takes_value):
    """A gh command's (option, value) pairs and its positional arguments. `--name=value` and `-Xvalue` are split, an
    option in takes_value consumes the next word, and any other option has no value."""
    pairs, positional, words = [], [], iter(args)
    for arg in words:
        if arg.startswith("--") and "=" in arg:
            pairs.append(tuple(arg.split("=", 1)))
        elif not arg.startswith("--") and len(arg) > 2 and arg[:2] in takes_value:
            pairs.append((arg[:2], arg[2:]))
        elif arg in takes_value:
            pairs.append((arg, next(words, "")))
        elif arg.startswith("-") and arg != STDIN:
            pairs.append((arg, None))
        else:
            positional.append(arg)
    return pairs, positional


def api_writes(pairs):
    """Whether a `gh api` command writes: an explicit write method, or fields, which make gh send a POST."""
    method = next((value.upper() for option, value in pairs if option in API_METHOD_OPTIONS), None)
    fields = any(option in API_FIELDS or option == API_INPUT for option, _ in pairs)
    return method in WRITE_METHODS or (method is None and fields)


class Sent:
    """The text a gh posting command sends, and the parts of it the hook cannot read."""

    def __init__(self, cwd):
        self.cwd = cwd
        self.texts = []
        self.unreadable = []

    def literal(self, option, value, expansion=EXPANSION):
        if expansion.search(value):
            self.unreadable.append(f"{option} {value}")
        else:
            self.texts.append(value)

    def file(self, option, path):
        if path == STDIN or EXPANSION.search(path):
            self.unreadable.append(f"{option} {path}")
            return
        try:
            with open(resolve(self.cwd, path), encoding="utf-8") as file:
                self.texts.append(file.read())
        except OSError:
            # Missing when the hook runs, such as a file the same line writes.
            self.unreadable.append(f"{option} {path}")

    def field(self, option, value):
        name, _, content = value.partition("=")
        if option in API_FILE_FIELDS and content.startswith("@"):
            self.file(option, content[1:])
        else:
            self.literal(option, content, SUBSTITUTION if name == GRAPHQL_QUERY else EXPANSION)


def sent_by(cwd, pairs, api):
    """What a gh posting command sends: --body and --body-file, or `gh api`'s fields and --input."""
    sent = Sent(cwd)
    for option, value in pairs:
        if value is None:
            continue
        if api and option in API_FIELDS:
            sent.field(option, value)
        elif api and option == API_INPUT:
            sent.file(option, value)
        elif not api and option in BODY_OPTIONS:
            sent.literal(option, value)
        elif not api and option in BODY_FILE_OPTIONS:
            sent.file(option, value)
    return sent


class Line:
    """One Bash tool call's command line, checked command by command. The hook runs before the whole line, so every
    rule sees the repository as it was before any of it ran."""

    def __init__(self, cwd, agent_type, project=None):
        self.cwd = cwd
        self.reviewer = is_reviewer(agent_type)
        self.branches = {}
        self.checks = []
        self.staged = None
        self.staging = False
        self.configs = {}
        self.bodies = []
        # The agent's rules follow the session's project, not the folders the line moves to. The call's folder may
        # be outside it, left there by an earlier call's `cd`, so the project's own folder counts too.
        self.opted_in = any(self.config(folder) is not None for folder in (cwd, project) if folder)

    def config(self, here):
        """The checks of the repository a folder is in, or None when it has not opted in."""
        root = git(here, "rev-parse", "--show-toplevel")
        if root not in self.configs:
            self.configs[root] = load_config(root)
        return self.configs[root]

    def branch(self, here):
        return self.branches.get(here) or git(here, "branch", "--show-current")

    def evaluate(self, text):
        """Checks each command of a command line; a shell script, `eval` text or command substitution inside it goes
        through here too."""
        text = mark_heredocs(text, self.bodies)
        for script in substitutions(text):
            self.evaluate(script)
        try:
            parsed = list(commands(text, self.bodies))
        except ValueError:
            # Unbalanced quotes: the shell will reject it too, but never let a commit on the default branch through.
            if re.search(r"\bgit\b[^\n]*\bcommit\b", text) and self.config(self.cwd) is not None \
                    and self.branch(self.cwd) == DEFAULT_BRANCH:
                block(f"Blocked: never commit on {DEFAULT_BRANCH}. Create a branch first.")
            return
        for words, stdin in parsed:
            self.check_command(unwrap(words), stdin)

    def check_command(self, words, stdin):
        if not words:
            return
        name, args = os.path.basename(words[0]), words[1:]
        if name == "cd" and args:
            self.cwd = resolve(self.cwd, args[0])
        elif name in SHELLS:
            script = shell_script(args, stdin)
            if script:
                self.evaluate(script)
        elif name == "eval":
            self.evaluate(" ".join(args))
        elif name == "gh":
            self.check_gh(args)
        elif name == "git":
            self.check_git(args)
        elif name in ("env", "printenv", "export", "set", *DECLARES):
            self.check_environment(name, args)

    def check_environment(self, name, args):
        """A non-reviewer never prints the environment, which holds the reviewer's token."""
        lists_variables = name in DECLARES and all(arg.startswith("-") for arg in args) and (
            not args or any(flag in arg for arg in args for flag in DECLARE_LISTING_FLAGS))
        prints = (name == "env" or (name == "printenv" and (not args or REVIEWER_TOKEN in args))
                  or (name == "export" and args in ([], ["-p"])) or (name == "set" and not args) or lists_variables)
        if prints and not self.reviewer and self.opted_in:
            block("Blocked: only the reviewer reads the environment that holds the reviewer's token; print the "
                  "variables you need by name.")

    def check_gh(self, args):
        if not self.opted_in:
            return
        api = args[:1] == ["api"]
        pairs, positional = gh_options(args[1:], API_VALUE_OPTIONS) if api else gh_options(args, POST_VALUE_OPTIONS)
        writes = api and api_writes(pairs)
        if args[:2] in GH_POSTS or writes:
            sent = sent_by(self.cwd, pairs, api)
            if sent.unreadable and not self.reviewer:
                block(f"Blocked: the hook can't read this body ({', '.join(sent.unreadable)}), and only the reviewer "
                      "posts verdicts. Pass a literal --body, or write the body to a file in its own command and pass "
                      "--body-file <path>.")
            if any(VERDICT in text for text in sent.texts + args) and not self.reviewer:
                block("Blocked: only the reviewer posts verdicts (docs/conventions.md, Who codes and reviews).")
        if args[:2] == ["pr", "merge"] and "--auto" not in args:
            block("Blocked: merge with `gh pr merge --auto`, which waits for the required checks and the review gate.")
        if args[:2] in (["repo", "edit"], ["repo", "delete"], ["repo", "rename"]):
            block("Blocked: repository settings are the owner's; ask the owner.")
        if writes:
            endpoint = positional[0] if positional else ""
            mutation = endpoint == GRAPHQL_ENDPOINT and any(GUARDED_MUTATION.search(text)
                                                            for text in sent.texts + args)
            if GUARDED_ENDPOINT.match(endpoint) or mutation:
                block("Blocked: branch protection, rulesets, repository settings, merges and branch refs are the "
                      "owner's through the API; merge with `gh pr merge --auto`, or ask the owner.")

    def check_git(self, args):
        here = self.cwd
        while args and args[0].startswith("-"):
            if args[0] in ("-C", "-c") and len(args) > 1:
                here = resolve(here, args[1]) if args[0] == "-C" else here
                args = args[2:]
            else:
                args = args[1:]
        config = self.config(here)
        if not args or config is None:
            return
        verb, rest = args[0], args[1:]
        branch = self.branch(here)
        positional = [arg for arg in rest if not arg.startswith("-")]

        if verb in ("push", "commit") and self.reviewer:
            block("Blocked: the reviewer judges a change and never commits or pushes it.")
        if verb == "push":
            pushed = check_push(rest, branch)
            self.checks.append(lambda: before_push(here, pushed, config))
        elif verb in ("add", "rm", "mv"):
            self.staging = True
        elif verb == "commit":
            if branch == DEFAULT_BRANCH:
                block(f"Blocked: never commit on {DEFAULT_BRANCH}. Create a branch first.")
            if self.staging or commit_stages_files(rest):
                block(COMMIT_STAGES)
            self.staged = git(here, "diff", "--cached", "--name-status")
            self.checks.append(lambda: before_commit(here, config))

        new = new_branch(verb, rest, positional)
        if new is None and verb in ("switch", "checkout"):
            # Moving to an existing branch; checkout also takes paths, so only a name that is a branch counts.
            target = positional[0] if positional else None
            if target and "--" not in rest and (verb == "switch" or len(positional) == 1) and any(
                    git(here, "rev-parse", "--verify", "--quiet", ref)
                    for ref in (f"refs/heads/{target}", f"refs/remotes/origin/{target}")):
                self.branches[here] = target
        if new:
            prefixes = tuple(config.get("branch_prefixes", PREFIXES))
            # Resetting the local default branch to the remote's is normal; any other new branch needs a prefix.
            if new != DEFAULT_BRANCH and not new.startswith(prefixes):
                block(f"Blocked: branch '{new}' needs one of the prefixes {', '.join(prefixes)}.")
            if verb in ("switch", "checkout"):
                self.branches[here] = new

    def finish(self):
        """Runs the checks, once every command in the line has passed the rules, and shows what a commit stages."""
        for run in self.checks:
            run()
        if self.staged is not None:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "Files staged for this commit; check each one was changed on purpose:\n"
                                     + (self.staged or "(none)"),
            }}))


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
    for component in sdlc_paths.components(config):
        pattern = re.compile(component.get("code", "."))
        files = [path for path in staged
                 if component["name"] in sdlc_paths.owners(config, path) and pattern.search(path)]
        if files:
            touched.append(component)
            code += files
    partly = set(code) & set(git(here, "diff", "--name-only").splitlines())
    if partly:
        block("Blocked: these staged files also have unstaged changes; stage or stash them first:\n"
              + "\n".join(sorted(partly)))
    run_checks(root, touched, "before_commit")


def before_push(here, branch, config):
    """The tests of each component the branch changes, against the default branch."""
    root = git(here, "rev-parse", "--show-toplevel")
    base = git(here, "merge-base", f"origin/{DEFAULT_BRANCH}", branch or "HEAD")
    components = sdlc_paths.components(config)
    if base:
        changed = git(here, "diff", "--no-renames", "--name-only", base, branch or "HEAD").splitlines()
        owned = set().union(*(sdlc_paths.owners(config, path) for path in changed))
        components = [component for component in components if component["name"] in owned]
    run_checks(root, components, "before_push")


def check_push(rest, branch):
    """The rules for a git push; returns the branch it pushes."""
    if "--all" in rest or "--mirror" in rest:
        block(f"Blocked: pushing every branch pushes {DEFAULT_BRANCH} too. Push the branch itself.")
    if any(arg in ("-f", "--force", "--force-with-lease", "--force-if-includes") or arg.startswith("--force")
           for arg in rest):
        block(FORCE_PUSH)
    if "-d" in rest or "--delete" in rest:
        block(BRANCH_DELETION)
    refspecs = [arg for arg in rest if not arg.startswith("-")][1:]
    if any(spec.startswith("+") for spec in refspecs):
        block(FORCE_PUSH)
    if any(spec.startswith(":") for spec in refspecs):
        block(BRANCH_DELETION)
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
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    line = Line(payload.get("cwd") or project or ".", payload.get("agent_type"), project)
    try:
        if not line.reviewer and TOKEN_EXPANSION.search(text) and line.opted_in:
            block("Blocked: only the reviewer uses the reviewer's token.")
        line.evaluate(text)
        line.finish()
    except Blocked as blocked:
        log_block(payload, str(blocked))
        print(blocked, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
