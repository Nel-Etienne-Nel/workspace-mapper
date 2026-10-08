#!/usr/bin/env python3
"""
Scan a directory and print a tree view for workspace maps (CLAUDE.md / CONTEXT.md / REFERENCES.md).
Respects common ignore patterns and limits depth to keep output readable.

With --check, also reports drift: paths named in docs that don't exist, folders with a CONTEXT.md
that no map routes to, stale or undated "Now" sections, and sub-folder CLAUDE.md files that follow
the older layout.
"""

import os
import re
import sys
import argparse
from datetime import date
from urllib.parse import unquote

IGNORE = {
    ".git", ".DS_Store", "__pycache__", "node_modules", ".venv", "venv",
    ".env", ".idea", ".vscode", "dist", "build", ".next", ".nuxt",
    "*.pyc", "*.pyo", ".claude",
}

DOC_FILES = ["CLAUDE.md", "CONTEXT.md", "REFERENCES.md", "STATUS.md"]
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
PATH_CHECKED_DOCS = ("CLAUDE.md", "CONTEXT.md", "REFERENCES.md")  # STATUS.md is history; not checked
FS_ROOTS = ("/Users/", "/home/", "/Volumes/")
FILE_EXTS = {
    "md", "txt", "csv", "json", "jsonl", "yml", "yaml", "toml", "ini", "xml", "html", "css",
    "py", "ipynb", "js", "mjs", "ts", "tsx", "jsx", "sh", "sql", "pdf", "docx", "xlsx", "pptx",
    "png", "jpg", "jpeg", "svg", "webp", "gif", "mp4", "zip", "skill", "example",
}
PLACEHOLDER_CHARS = "*<>{}|=[]()@"
# Naming-convention examples, not real paths: `NN - Name/`, `SEC-YYYY-NNNN Title.md`, `Lesson X.Y - Title.md`
PLACEHOLDER_RE = re.compile(r"(?<![A-Za-z])(N{1,4}|X\.Y|YYYY|MM|DD|Name|Title)(?![a-z])")


def should_ignore(name):
    if name in IGNORE:
        return True
    for pattern in IGNORE:
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True
    return False


def is_repo(dir_path):
    return os.path.exists(os.path.join(dir_path, ".git"))


def doc_marker(dir_path):
    """Return a short marker showing which doc files exist in dir_path, and whether it's a repo."""
    present = [f for f in DOC_FILES if os.path.isfile(os.path.join(dir_path, f))]
    marker = "  [" + ", ".join(present) + "]" if present else ""
    if is_repo(dir_path):
        marker += "  (repo)"
    return marker


def scan(path, prefix="", depth=0, max_depth=3):
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return

    entries = [e for e in entries if not should_ignore(e.name)]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if entry.is_dir() else ""
        marker = doc_marker(entry.path) if entry.is_dir() else ""
        print(f"{prefix}{connector}{entry.name}{suffix}{marker}")

        if entry.is_dir() and depth < max_depth:
            extension = "    " if is_last else "│   "
            scan(entry.path, prefix + extension, depth + 1, max_depth)


# ---------------------------------------------------------------------------
# Drift check
# ---------------------------------------------------------------------------

def find_docs(root):
    """Yield (dir_path, filename) for every doc file under root, skipping ignored dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_ignore(d)]
        for f in DOC_FILES:
            if f in filenames:
                yield dirpath, f


def tree_paths(lines):
    """Rebuild relative paths from a ├── / └── tree inside a fenced code block."""
    paths, stack = [], []
    for line in lines:
        m = re.search(r"(├──|└──)\s?", line)
        if not m:
            continue
        depth = m.start() // 4
        text = line[m.end():].split("←")[0].split("#")[0].rstrip()
        if not text:
            continue
        is_dir = text.endswith("/")
        name = text[:-1] if is_dir else text
        stack = stack[:depth] + [name]
        if not (any(c in name for c in PLACEHOLDER_CHARS) or PLACEHOLDER_RE.search(name)):  # rules/<client>.json
            paths.append("/".join(stack))
    return paths


def looks_like_path(token):
    """Backticked text counts as a path only if it plainly is one: a folder (trailing /) or a file
    with an extension. Skips commands, placeholders, URL routes, hostnames and repo slugs."""
    token = re.sub(r":\d+(-\d+)?$", "", token)  # file.md:19-20
    if not token or token.startswith(("http", "~", "$", "-", "@")) or "..." in token:
        return False
    if any(c in token for c in PLACEHOLDER_CHARS) or PLACEHOLDER_RE.search(token):
        return False
    if token in DOC_FILES:  # "read that folder's `CONTEXT.md`" is generic, not a path
        return False
    if token.startswith("/") and not token.startswith(FS_ROOTS):
        return False  # /chat, /api/sessions, /mnt/... — routes or sandbox paths
    first = token.lstrip("./").split("/")[0]
    if "." in first and "/" in token.lstrip("./"):
        return False  # shop.myshopify.com/api
    if " " in token and not (token.endswith("/") or token.endswith(".md")):
        return False
    if token.endswith("/"):
        return True
    last = token.split("/")[-1]
    ext = last.rsplit(".", 1)[-1].lower() if "." in last.strip(".") else ""
    if "/" not in token:
        return ext == "md"  # bare names: only docs pointing at docs (`SETUP.md`), not `cart.js`
    return ext in FILE_EXTS


def referenced_paths(text):
    """Paths named in a doc, as (path, strict) pairs. Tree entries and markdown links are strict:
    they must resolve where written. Backticked names are loose: found anywhere in the tree is fine."""
    refs, prose, fence = [], [], []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_fence:
                refs.extend((p, True) for p in tree_paths(fence))
                fence = []
            in_fence = not in_fence
            continue
        (fence if in_fence else prose).append(line)
    body = "\n".join(prose)
    for t in re.findall(r"`([^`\n]+)`", body):
        if looks_like_path(t):
            refs.append((re.sub(r":\d+(-\d+)?$", "", t), False))
    for t in re.findall(r"\]\(([^)\s]+)\)", body):
        if not t.startswith(("http", "#", "mailto:")):
            refs.append((unquote(t), True))
    return refs


def index_tree(root):
    """All relative paths under root (files and dirs), for loose lookups."""
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_ignore(d)]
        rel_dir = os.path.relpath(dirpath, root)
        for name in dirnames + filenames:
            paths.append(name if rel_dir == "." else f"{rel_dir}/{name}")
    return paths


def path_exists(ref, doc_dir, root, strict=True, index=()):
    ref = ref.split("#")[0].rstrip("/")
    if not ref:
        return True
    candidates = [ref] if os.path.isabs(ref) else [os.path.join(doc_dir, ref), os.path.join(root, ref)]
    # Tree roots are written as "project/..." — also try with the first segment dropped.
    first, _, rest = ref.partition("/")
    if rest and first == os.path.basename(doc_dir):
        candidates.append(os.path.join(doc_dir, rest))
    if any(os.path.exists(c) for c in candidates):
        return True
    if not strict:
        tail = ref.lstrip("./")
        return any(p == tail or p.endswith("/" + tail) for p in index)
    return False


def now_date(text):
    """Return (has_now, date_or_None) for a CONTEXT.md's Now section."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^#{1,4}\s+Now\b", line, re.IGNORECASE):
            for candidate in lines[i:i + 4]:
                m = DATE_RE.search(candidate)
                if m:
                    return True, m.group(1)
            return True, None
    return False, None


def status_date(text):
    for line in text.splitlines()[:15]:
        if "updated" in line.lower():
            m = DATE_RE.search(line)
            if m:
                return m.group(1)
    return None


def nearest_router(dir_path, root):
    """Closest ancestor (up to root) that has a CLAUDE.md or CONTEXT.md; return (dir, [texts])."""
    current = os.path.dirname(dir_path)
    while True:
        texts = []
        for f in ("CLAUDE.md", "CONTEXT.md"):
            p = os.path.join(current, f)
            if os.path.isfile(p):
                texts.append((f, read(p)))
        if texts:
            return current, texts
        if os.path.samefile(current, root) or os.path.dirname(current) == current:
            return None, []
        current = os.path.dirname(current)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def days_old(iso):
    try:
        return (date.today() - date.fromisoformat(iso)).days
    except ValueError:
        return None


def check(root, stale_days):
    broken, unrouted, stale, older = [], [], [], []
    rel = lambda p: os.path.relpath(p, root)
    index = index_tree(root)

    for doc_dir, name in find_docs(root):
        doc_path = os.path.join(doc_dir, name)
        text = read(doc_path)

        if name in PATH_CHECKED_DOCS:
            seen = set()
            for ref, strict in referenced_paths(text):
                key = ref.rstrip("/")
                if key not in seen and not path_exists(ref, doc_dir, root, strict, index):
                    seen.add(key)
                    broken.append(f"{rel(doc_path)} → `{ref}`")

        if name == "CONTEXT.md":
            has_now, d = now_date(text)
            if has_now and d is None:
                stale.append(f"{rel(doc_path)}: Now section has no date")
            elif d and (age := days_old(d)) is not None and age > stale_days:
                stale.append(f"{rel(doc_path)}: Now last updated {d} ({age} days ago)")

        if name == "STATUS.md":
            d = status_date(text)
            if d is None:
                stale.append(f"{rel(doc_path)}: no 'Last updated' date")
            elif (age := days_old(d)) is not None and age > stale_days:
                stale.append(f"{rel(doc_path)}: last updated {d} ({age} days ago)")

        if os.path.abspath(doc_dir) == os.path.abspath(root):
            continue

        if name == "CLAUDE.md" and not is_repo(doc_dir):
            older.append(f"{rel(doc_path)}: sub-folder map in a non-repo folder (CONTEXT.md candidate)")

        if name == "CONTEXT.md" and not os.path.isfile(os.path.join(doc_dir, "CLAUDE.md")):
            router_dir, texts = nearest_router(doc_dir, root)
            if router_dir is None:
                unrouted.append(f"{rel(doc_path)}: no CLAUDE.md or CONTEXT.md above it")
            else:
                folder_rel = os.path.relpath(doc_dir, router_dir)
                folder_name = os.path.basename(doc_dir)
                if not any(folder_rel in t or folder_name in t for _, t in texts):
                    routers = ", ".join(rel(os.path.join(router_dir, f)) for f, _ in texts)
                    unrouted.append(f"{rel(doc_path)}: not mentioned in {routers}")

    sections = [
        ("Broken paths (named in a doc, missing on disk)", broken),
        ("Unrouted (CONTEXT.md that no map points to)", unrouted),
        (f"Stale or undated (older than {stale_days} days)", stale),
        ("Older layout (review, may be intentional)", older),
    ]
    print("\nDrift check")
    print("=" * 11)
    total = 0
    for title, items in sections:
        print(f"\n{title}: {len(items) or 'none'}")
        for item in items:
            print(f"  - {item}")
        total += len(items)
    print(f"\n{total} finding(s). Heuristic — read each one before changing anything.")


def main():
    parser = argparse.ArgumentParser(description="Scan a directory for workspace mapping")
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan (default: current)")
    parser.add_argument("--depth", type=int, default=2, help="Max tree depth to print (default: 2)")
    parser.add_argument("--check", action="store_true", help="Also report drift in the docs")
    parser.add_argument("--stale-days", type=int, default=30, help="Age after which Now/STATUS is stale")
    parser.add_argument("--no-tree", action="store_true", help="With --check, skip the tree output")
    args = parser.parse_args()

    target = os.path.abspath(args.path)
    if not os.path.isdir(target):
        print(f"Error: '{target}' is not a directory", file=sys.stderr)
        sys.exit(1)

    if not args.no_tree:
        print(f"{os.path.basename(target)}/{doc_marker(target)}")
        scan(target, max_depth=args.depth)

    if args.check:
        check(target, args.stale_days)


if __name__ == "__main__":
    main()
