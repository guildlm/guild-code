# -*- coding: utf-8 -*-
"""Stage 4 of the GitHub Go mining pipeline — THE GOLD MINE.

Mine each cloned repo's git history into *real* task-SFT data for exactly the
user's tasks, instead of synthetic examples:

  * a feature/refactor commit = (before files -> commit message -> after files)
    -> "apply this change" maintenance data for go-dev
  * a bug-fix commit          = (buggy before -> fix)
    -> bug-solving data
  * (PR review comments are mined separately by mine_pr_reviews.py)

This is the lever the plateaued thin-synthetic SFT never had: thousands of real
senior-Go-dev edits, each grounded in a real codebase and a real intent.

How it works (two passes, $0, all local git):
  Pass 1 — one `git log --name-status` per repo: cheaply list non-merge commits
           with subject/body and changed-file statuses. Classify + filter in
           Python (commit type, file count, .go-only, size, junk-subject skip).
  Pass 2 — only for kept commits: `git show sha~1:path` / `git show sha:path`
           to fetch before/after file contents, and emit chat examples.

Output (chat {"messages":[...]} schema, same as the existing SFT corpora):
  mined_dev.jsonl      feature/refactor/perf edits   (go-dev)
  mined_bugfix.jsonl   bug-fix edits                 (go-dev / bug-solving)
  mined_commits.jsonl  one metadata row per kept commit (for analysis/audit)
  + *.sample.jsonl committed previews

Usage:
  python mine_git_history.py
  python mine_git_history.py --max-commits 300 --max-files 1 --sample 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CACHE = os.path.join(_HERE, "repos")

SYS_DEV = "You are GuildLM go-dev, a Go development specialist from the GuildLM Code Guild."

# Commit-message classification (checked in priority order).
_BUGFIX = re.compile(
    r"\b(fix(es|ed)?|bug|bugfix|patch|resolv\w+|crash|panic|leak|races?|"
    r"deadlock|regression|broken|incorrect|wrong|overflow|off.by.one|"
    r"nil pointer|npe|segfault|hang)\b", re.I)
_PERF = re.compile(
    r"\b(perf|performance|optimiz\w+|faster|speed.?up|reduce alloc\w*|"
    r"latency|throughput)\b", re.I)
_FEATURE = re.compile(
    r"\b(add(s|ed)?|implement\w*|support|feature|introduce\w*|new |enable\w*|"
    r"allow\w*)\b", re.I)
_REFACTOR = re.compile(
    r"\b(refactor\w*|simplif\w+|cleanup|clean up|restructur\w+|extract\w*|"
    r"deduplicat\w+|reorganiz\w+|tidy)\b", re.I)

# Junk subjects we never want as a training instruction.
_JUNK = re.compile(
    r"^\s*(merge|revert|wip|bump|chore|ci\b|build\(deps\)|"
    r"docs?\b|doc:|release|gofmt|format|lint|typo|"
    r"update (deps|dependencies|go\.mod|go\.sum|changelog|version|readme)|"
    r"v?\d+\.\d+\.\d+)", re.I)

_SKIP_PATH = re.compile(r"(^|/)(vendor|testdata|third_party|node_modules)/")
_GEN_NAME = re.compile(
    r"(\.pb\.go|\.pb\.gw\.go|\.gen\.go|_generated\.go|zz_generated|bindata\.go|"
    r"_string\.go)$")


def git(repo: str, *args: str, timeout: int = 60) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True, text=True, timeout=timeout,
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
        )
    except subprocess.TimeoutExpired:
        return ""
    return out.stdout if out.returncode == 0 else ""


def classify(subject: str, files: list[tuple[str, str]]) -> str | None:
    """Return commit category, or None to skip."""
    if _JUNK.match(subject):
        return None
    go = [f for st, f in files if f.endswith(".go")]
    if not go:
        return None
    # bug-fix wins (most valuable + most specific signal)
    if _BUGFIX.search(subject):
        return "bugfix"
    if _PERF.search(subject):
        return "perf"
    if _FEATURE.search(subject):
        return "feature"
    if _REFACTOR.search(subject):
        return "refactor"
    return None


def parse_log(raw: str) -> list[dict]:
    """Parse the delimited `git log --name-status` stream into commit dicts."""
    commits = []
    # each commit block starts with \x01
    for chunk in raw.split("\x01"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        # message part \x1f name-status part
        if "\x1f" not in chunk:
            head, rest = chunk, ""
        else:
            head, rest = chunk.split("\x1f", 1)
        parts = head.split("\x1e")
        if len(parts) < 3:
            continue
        sha, subject, body = parts[0].strip(), parts[1].strip(), parts[2].strip()
        files: list[tuple[str, str]] = []
        for line in rest.splitlines():
            line = line.strip()
            if not line or "\t" not in line:
                continue
            cols = line.split("\t")
            status = cols[0]
            # renames: "R100\told\tnew" -> use the new path, treat as modify
            path = cols[-1]
            files.append((status[0], path))
        commits.append({"sha": sha, "subject": subject, "body": body,
                        "files": files})
    return commits


def good_file(status: str, path: str) -> bool:
    if status != "M":  # only modifications give a clean before->after pair
        return False
    if not path.endswith(".go") or path.endswith("_test.go"):
        return False
    if _SKIP_PATH.search(path) or _GEN_NAME.search(os.path.basename(path)):
        return False
    return True


def build_instruction(category: str, subject: str, body: str) -> str:
    # keep only the first paragraph of the body (drop sign-offs / fixes-#refs)
    para = body.split("\n\n")[0].strip() if body else ""
    para = re.sub(r"(?im)^(signed-off-by|co-authored-by|fixes|closes|refs?)\b.*$",
                  "", para).strip()
    desc = subject if not para else f"{subject}\n\n{para}"
    desc = desc[:600]
    if category == "bugfix":
        return ("There is a bug in this Go code. Fix it.\n\n"
                f"BUG / FIX DESCRIPTION: {desc}")
    return ("You are maintaining an existing Go project. Apply this change:\n\n"
            f"CHANGE REQUEST: {desc}")


def make_example(repo_path: str, label: str, c: dict, category: str,
                 files: list[str], max_file_chars: int) -> dict | None:
    sha = c["sha"]
    blocks_before, blocks_after = [], []
    for path in files:
        before = git(repo_path, "show", f"{sha}~1:{path}")
        after = git(repo_path, "show", f"{sha}:{path}")
        if not before or not after or before == after:
            return None
        if len(before) > max_file_chars or len(after) > max_file_chars:
            return None
        base = os.path.basename(path)
        blocks_before.append((base, before))
        blocks_after.append((base, after))

    instr = build_instruction(category, c["subject"], c["body"])
    if len(files) == 1:
        base, before = blocks_before[0]
        user = f"{instr}\n\nHere is the current `{base}`:\n```go\n{before}\n```"
        _, after = blocks_after[0]
        assistant = f"```go\n{after}\n```"
    else:
        parts = [instr, "\nHere are the current files:"]
        for base, before in blocks_before:
            parts.append(f"\n`{base}`:\n```go\n{before}\n```")
        user = "\n".join(parts)
        ap = ["Here are the updated files:"]
        for base, after in blocks_after:
            ap.append(f"\n`{base}`:\n```go\n{after}\n```")
        assistant = "\n".join(ap)

    return {"messages": [
        {"role": "system", "content": SYS_DEV},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=_DEFAULT_CACHE)
    ap.add_argument("--max-commits", type=int, default=400,
                    help="newest non-merge commits to scan per repo")
    ap.add_argument("--max-files", type=int, default=1,
                    help="max changed .go files per kept commit (1 = cleanest)")
    ap.add_argument("--max-file-chars", type=int, default=6500,
                    help="skip commits whose before/after file exceeds this")
    ap.add_argument("--min-subject", type=int, default=12)
    ap.add_argument("--per-repo-cap", type=int, default=150,
                    help="max examples mined per repo (mixture balance)")
    ap.add_argument("--sample", type=int, default=0)
    args = ap.parse_args()

    if not os.path.isdir(args.cache):
        sys.exit(f"no clone cache at {args.cache} — run clone_repos.py first")

    fmt = "\x01%H\x1e%s\x1e%b\x1f"
    dev, bugfix, meta = [], [], []
    by_cat: dict[str, int] = {}

    repos = sorted(d for d in os.listdir(args.cache)
                   if os.path.isdir(os.path.join(args.cache, d, ".git")))
    for label in repos:
        repo_path = os.path.join(args.cache, label)
        raw = git(repo_path, "log", "--no-merges", f"-n{args.max_commits}",
                  "--name-status", f"--format={fmt}", timeout=120)
        if not raw:
            print(f"  {label}: (no log)")
            continue
        commits = parse_log(raw)
        kept = 0
        for c in commits:
            if kept >= args.per_repo_cap:
                break
            if len(c["subject"]) < args.min_subject:
                continue
            category = classify(c["subject"], c["files"])
            if not category:
                continue
            go_mods = [p for st, p in c["files"] if good_file(st, p)]
            other_go = [p for st, p in c["files"]
                        if p.endswith(".go") and p not in go_mods]
            # require the commit's .go changes to be exactly our modify set
            if not go_mods or other_go:
                continue
            if len(go_mods) > args.max_files:
                continue
            ex = make_example(repo_path, label, c, category, go_mods,
                              args.max_file_chars)
            if ex is None:
                continue
            (bugfix if category == "bugfix" else dev).append(ex)
            meta.append({"repo": label, "sha": c["sha"], "category": category,
                         "files": go_mods, "subject": c["subject"][:160]})
            by_cat[category] = by_cat.get(category, 0) + 1
            kept += 1
        print(f"  {label:<32} {len(commits):4d} commits scanned -> {kept:3d} mined")

    out = {
        "mined_dev.jsonl": dev,
        "mined_bugfix.jsonl": bugfix,
    }
    for name, rows in out.items():
        with open(os.path.join(_HERE, name), "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    with open(os.path.join(_HERE, "mined_commits.jsonl"), "w", encoding="utf-8") as fh:
        for m in meta:
            fh.write(json.dumps(m) + "\n")

    if args.sample:
        for name, rows in out.items():
            sname = name.replace(".jsonl", ".sample.jsonl")
            with open(os.path.join(_HERE, sname), "w", encoding="utf-8") as fh:
                for r in rows[: args.sample]:
                    # trim long code blocks so the committed sample stays small
                    trimmed = {"messages": [
                        {**m, "content": m["content"][:1200]} for m in r["messages"]
                    ]}
                    fh.write(json.dumps(trimmed) + "\n")

    print(f"\nmined: dev={len(dev)} bugfix={len(bugfix)} "
          f"(by category: {by_cat})")
    print(f"-> mined_dev.jsonl, mined_bugfix.jsonl, mined_commits.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
