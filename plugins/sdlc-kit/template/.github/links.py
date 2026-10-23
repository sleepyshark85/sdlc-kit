#!/usr/bin/env python3
"""Checks the relative links of the repository's Markdown: each target file exists, and each #anchor names a heading
of its target, as GitHub renders it. External links are not fetched. Prints one line per broken link and exits 1 if
there is any. Usage: links.py [root]"""
import os
import re
import subprocess
import sys

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.M)
FENCE = re.compile(r"^(```|~~~).*?^\1", re.M | re.S)
EXTERNAL = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def slug(heading):
    """GitHub's anchor for a heading: lower case, markup and punctuation dropped, spaces as hyphens."""
    text = re.sub(r"`|\*|_(?=\w)|(?<=\w)_|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", heading.strip().lower())
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(text):
    """Every heading's anchor; a repeated heading gets -1, -2… as on GitHub."""
    seen, result = {}, set()
    for heading in HEADING.findall(FENCE.sub("", text)):
        base = slug(heading)
        count = seen.get(base, 0)
        result.add(base if count == 0 else f"{base}-{count}")
        seen[base] = count + 1
    return result


def markdown_files(root):
    listed = subprocess.run(["git", "ls-files", "*.md"], cwd=root, capture_output=True, text=True, check=True)
    return listed.stdout.splitlines()


def broken_links(root, files):
    """(file, link, reason) for each relative link that does not resolve."""
    texts, problems = {}, []

    def read(path):
        if path not in texts:
            with open(os.path.join(root, path), encoding="utf-8") as file:
                texts[path] = file.read()
        return texts[path]

    for source in files:
        for target in LINK.findall(FENCE.sub("", read(source))):
            if EXTERNAL.match(target):
                continue
            path, _, anchor = target.partition("#")
            resolved = os.path.normpath(os.path.join(os.path.dirname(source), path)).replace("\\", "/") if path \
                else source
            if not os.path.exists(os.path.join(root, resolved)):
                problems.append((source, target, "no such file"))
            elif anchor and resolved.endswith(".md") and anchor not in anchors(read(resolved)):
                problems.append((source, target, "no such heading"))
    return problems


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    problems = broken_links(root, markdown_files(root))
    for source, target, reason in problems:
        print(f"{source}: {target}: {reason}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
