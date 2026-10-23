"""Which component a path belongs to, from .sdlc/checks.toml. The git hook (before a commit and a push) and
.github/changes.py (which component's CI a pull request runs) both decide with this module, so they always agree.

A path belongs to a component when it is under one of its paths or is one of its workflows
(`.github/workflows/<name>.yml` or `<name>-*.yml`); a shared path belongs to every component. Docs (the `docs`
pattern, outside .github/, .claude/ and .sdlc/) belong to none. Any other path, such as scripts/ or the tooling,
belongs to every component: when in doubt, everything runs."""
import os
import re
import tomllib

CONFIG = os.path.join(".sdlc", "checks.toml")
DOCS = r"\.(md|png|svg|jpg)$"
TOOLING = (".github/", ".claude/", ".sdlc/")


def load(root):
    """The project's configuration; raises FileNotFoundError when the project has none."""
    with open(os.path.join(root, CONFIG), "rb") as file:
        return tomllib.load(file)


def components(config):
    """The project's components, each a [[component]] table of the configuration."""
    return config.get("component", [])


def owners(config, path):
    """The names of the components a path belongs to."""
    names = {component["name"] for component in components(config)}
    if path.startswith(tuple(config.get("shared", []))):
        return names
    for component in components(config):
        workflow = f".github/workflows/{component['name']}"
        if path.startswith(tuple(component.get("paths", []))) or path == f"{workflow}.yml" \
                or path.startswith(f"{workflow}-"):
            return {component["name"]}
    if re.search(config.get("docs", DOCS), path) and not path.startswith(TOOLING):
        return set()
    return names
