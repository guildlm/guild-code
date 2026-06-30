# -*- coding: utf-8 -*-
"""Stage 5 of the GitHub Go mining pipeline — PR review comments -> go-review data.

The third real-data signal (after DAPT text and git-history edits): real human
code-review feedback. For each repo we fetch the *inline review comments* on pull
requests via the GitHub API (`gh api`, $0 free-tier). Each such comment carries a
`diff_hunk` — the exact code the reviewer was looking at — so the pair

    (diff hunk of a Go change)  ->  (the reviewer's comment)

is exactly go-review training data: given a code change, produce a useful review.

Unlike stages 3-4 this reads the GitHub API, not the local clone (review comments
live on PRs, not in git history). It still only needs the repo list.

Quality filtering (PR comment streams are noisy):
  - .go paths only
  - drop bots (dependabot/codecov/github-actions/…) and bot-typed users
  - drop thread replies (keep self-contained top-level review comments)
  - drop trivial chatter (LGTM / nit-only / thanks / done / emoji / very short)
  - require a non-empty diff_hunk within size bounds; dedup

Output: mined_review.jsonl ({"messages":[...]}, go-review system prompt) +
mined_review.sample.jsonl preview.

Usage:
  python mine_pr_reviews.py                         # uses repos.jsonl
  python mine_pr_reviews.py --repos repos.smoke.jsonl --max-pages 3 --sample 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))

SYS_REVIEW = "You are GuildLM go-review, a Go code review specialist from the GuildLM Code Guild."

_BOT_LOGIN = re.compile(
    r"(\[bot\]|dependabot|codecov|github-actions|renovate|mergify|"
    r"sonarcloud|coveralls|stale|allcontributors|imgbot|snyk)", re.I)

# Trivial / non-substantive review chatter we don't want as a target.
_TRIVIAL = re.compile(
    r"^\s*(lgtm|looks good|nice|thanks?|thank you|done|\+1|same|ditto|"
    r"ok|okay|agreed?|👍|✅|🎉|fixed|good catch|ack)\b[\s.!]*$", re.I)
_NIT_ONLY = re.compile(r"^\s*(nit|typo|style)\s*:?\s*$", re.I)


def gh_json(path: str, params: dict[str, str], timeout: int = 60):
    cmd = ["gh", "api", "-X", "GET", path]
    for k, v in params.items():
        cmd += ["-f", f"{k}={v}"]
    for _attempt in range(2):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        if out.returncode == 0:
            try:
                return json.loads(out.stdout)
            except json.JSONDecodeError:
                return None
        err = out.stderr.lower()
        if "rate limit" in err or "secondary" in err or "abuse" in err:
            time.sleep(30)
            continue
        return None
    return None


def clean_body(body: str) -> str:
    if not body:
        return ""
    # strip GitHub suggestion blocks' fences markers but keep the suggestion text,
    # and collapse quoted reply lines
    lines = [l for l in body.splitlines() if not l.lstrip().startswith(">")]
    return "\n".join(lines).strip()


def keep_comment(c: dict, min_body: int, max_hunk: int) -> bool:
    if c.get("in_reply_to_id"):
        return False  # thread reply — not self-contained
    user = (c.get("user") or {})
    if user.get("type") == "Bot" or _BOT_LOGIN.search(user.get("login") or ""):
        return False
    path = c.get("path") or ""
    if not path.endswith(".go") or path.endswith("_test.go"):
        return False
    hunk = c.get("diff_hunk") or ""
    if not hunk or len(hunk) > max_hunk or "\n" not in hunk:
        return False
    body = clean_body(c.get("body") or "")
    if len(body) < min_body or _TRIVIAL.match(body) or _NIT_ONLY.match(body):
        return False
    return True


def make_example(c: dict) -> dict:
    hunk = c["diff_hunk"]
    body = clean_body(c["body"])
    path = c.get("path") or "code"
    user = ("You are reviewing a Go pull request. Here is a change in "
            f"`{os.path.basename(path)}`:\n```diff\n{hunk}\n```\n\n"
            "Give your code-review comment on this change.")
    return {"messages": [
        {"role": "system", "content": SYS_REVIEW},
        {"role": "user", "content": user},
        {"role": "assistant", "content": body},
    ]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default=os.path.join(_HERE, "repos.jsonl"))
    ap.add_argument("--out", default=os.path.join(_HERE, "mined_review.jsonl"))
    ap.add_argument("--max-pages", type=int, default=5,
                    help="comment pages per repo (100/page, newest first)")
    ap.add_argument("--per-repo-cap", type=int, default=120)
    ap.add_argument("--min-body", type=int, default=25)
    ap.add_argument("--max-hunk", type=int, default=4000)
    ap.add_argument("--limit-repos", type=int, default=0)
    ap.add_argument("--sample", type=int, default=0)
    args = ap.parse_args()

    if not os.path.isfile(args.repos):
        sys.exit(f"no repo list at {args.repos} — run select_repos.py first")
    with open(args.repos, encoding="utf-8") as fh:
        repos = [json.loads(l)["full_name"] for l in fh if l.strip()]
    if args.limit_repos:
        repos = repos[: args.limit_repos]

    examples, seen = [], set()
    for fn in repos:
        kept = 0
        for page in range(1, args.max_pages + 1):
            data = gh_json(
                f"repos/{fn}/pulls/comments",
                {"per_page": "100", "page": str(page),
                 "sort": "created", "direction": "desc"},
            )
            if not data:
                break
            for c in data:
                if kept >= args.per_repo_cap:
                    break
                if not keep_comment(c, args.min_body, args.max_hunk):
                    continue
                key = (c.get("diff_hunk", "")[:120], (c.get("body") or "")[:80])
                if key in seen:
                    continue
                seen.add(key)
                examples.append(make_example(c))
                kept += 1
            if len(data) < 100 or kept >= args.per_repo_cap:
                break
            time.sleep(1.0)  # gentle on the core API
        print(f"  {fn:<40} -> {kept:3d} review comments")

    with open(args.out, "w", encoding="utf-8") as fh:
        for e in examples:
            fh.write(json.dumps(e) + "\n")
    if args.sample:
        with open(args.out.replace(".jsonl", ".sample.jsonl"), "w") as fh:
            for e in examples[: args.sample]:
                trimmed = {"messages": [
                    {**m, "content": m["content"][:1200]} for m in e["messages"]
                ]}
                fh.write(json.dumps(trimmed) + "\n")

    print(f"\nmined {len(examples)} review examples -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
