#!/usr/bin/env python3
"""Creates a project from the kit's template, and adds language packs to it.

  new_project.py create <target folder> <project name> [pack...]
  new_project.py add-pack <project folder> <pack>

`create` copies template/ into a new or empty folder, names the project in its files, and adds each pack. `add-pack`
copies the pack's files/ over the project (never replacing a file), and registers the pack where the template's files
need it, as the pack's pack.toml says: its component in .sdlc/checks.toml, its CodeQL language, its Dependabot
ecosystem and its after-edit hook. It prints the pack's required checks, for scripts/setup-repo.sh. Adding a pack
twice changes nothing."""
import json
import os
import shutil
import sys
import tomllib

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(KIT, "template")
PACKS = os.path.join(KIT, "packs")
NAME = "{{project}}"
NAMED_FILES = ("CLAUDE.md", "README.md", "REQUIREMENTS.md", "ARCHITECTURE.md", os.path.join("docs", "decisions.md"))
CODEQL_MATRIX = "        include:\n"


class KitError(Exception):
    """A request the kit refuses, with the reason for the owner."""


def read(path):
    with open(path, encoding="utf-8") as file:
        return file.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(text)


def create(target, name, packs):
    if os.path.exists(target) and os.listdir(target):
        raise KitError(f"{target} is not empty; a project starts in a new or empty folder.")
    for pack in packs:
        load_manifest(pack)
    shutil.copytree(TEMPLATE, target, dirs_exist_ok=True)
    for relative in NAMED_FILES:
        path = os.path.join(target, relative)
        write(path, read(path).replace(NAME, name))
    return [check for pack in packs for check in add_pack(target, pack)]


def load_manifest(pack):
    """A pack's pack.toml; refuses a name the kit has no pack for."""
    path = os.path.join(PACKS, pack, "pack.toml")
    if not os.path.isfile(path):
        raise KitError(f"No pack named {pack}; the kit has: {', '.join(sorted(os.listdir(PACKS)))}.")
    with open(path, "rb") as file:
        return tomllib.load(file)


def add_pack(project, pack):
    """Adds a pack to a project; returns its required checks."""
    folder = os.path.join(PACKS, pack)
    manifest = load_manifest(pack)
    checks = os.path.join(project, ".sdlc", "checks.toml")
    with open(checks, "rb") as file:
        if pack in (component["name"] for component in tomllib.load(file).get("component", [])):
            return manifest["required_checks"]
    copy_files(os.path.join(folder, "files"), project)
    write(checks, read(checks).rstrip("\n") + "\n" + manifest["component"])
    add_codeql_language(os.path.join(project, ".github", "workflows", "codeql.yml"), manifest["codeql"])
    add_dependabot_ecosystem(os.path.join(project, ".github", "dependabot.yml"), manifest["dependabot"])
    add_after_edit_hook(os.path.join(project, ".claude", "settings.json"), manifest["after_edit_hook"])
    return manifest["required_checks"]


def copy_files(source, project):
    """Copies a pack's files into the project, refusing to replace any: a pack adds, it never overwrites."""
    for root, _, names in os.walk(source):
        for name in names:
            relative = os.path.relpath(os.path.join(root, name), source)
            if os.path.exists(os.path.join(project, relative)):
                raise KitError(f"{relative} already exists; the pack would replace it.")
    shutil.copytree(source, project, dirs_exist_ok=True)


def add_codeql_language(path, row):
    text = read(path)
    if CODEQL_MATRIX not in text:
        raise KitError(f"{path} has no matrix to add {row['language']} to.")
    entry = f"          - language: {row['language']}\n            build-mode: {row['build-mode']}\n"
    write(path, text.replace(CODEQL_MATRIX, CODEQL_MATRIX + entry, 1))


def add_dependabot_ecosystem(path, entry):
    write(path, read(path).rstrip("\n") + f"\n  - package-ecosystem: {entry['package-ecosystem']}\n"
                f"    directory: {entry['directory']}\n    schedule:\n      interval: weekly\n")


def add_after_edit_hook(path, script):
    settings = json.loads(read(path))
    hooks = settings.setdefault("hooks", {}).setdefault("PostToolUse", [])
    hooks.append({"matcher": "Edit|Write", "hooks": [
        {"type": "command", "command": f'python3 "$CLAUDE_PROJECT_DIR/{script}"', "timeout": 10}]})
    write(path, json.dumps(settings, indent=2) + "\n")


def main(argv):
    try:
        if argv[:1] == ["create"] and len(argv) >= 3:
            checks = create(argv[1], argv[2], argv[3:])
        elif argv[:1] == ["add-pack"] and len(argv) == 3:
            checks = add_pack(argv[1], argv[2])
        else:
            print(__doc__, file=sys.stderr)
            return 64
    except KitError as error:
        print(error, file=sys.stderr)
        return 1
    print("Required checks to pass to scripts/setup-repo.sh: " + " ".join(f'"{check}"' for check in checks))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
