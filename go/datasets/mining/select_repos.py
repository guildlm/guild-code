# -*- coding: utf-8 -*-
"""Stage 1 of the GitHub Go mining pipeline — discover high-quality Go repos.

The GuildLM real-data recipe needs thousands of clean, idiomatic, permissively
licensed Go repositories. This script queries the GitHub search API (via the
authenticated `gh` CLI, which is $0 on the free tier) and writes a manifest of
candidate repos to clone.

Two problems the GitHub search API forces us to solve:
  1. Search returns at most 1000 results per query. To gather thousands of repos
     we *bucket by star ranges* (stars:5000..8000, stars:3000..5000, ...). Each
     bucket is its own <=1000-result query, so the union far exceeds 1000.
  2. Lots of high-star "Go" repos are not code (awesome-lists, books, tutorials).
     We filter by permissive license, a size floor/ceiling, drop obvious list/doc
     repos by name+topic, and skip archived/fork repos. A second code-fraction
     check happens after clone (build_dapt_corpus / mine_git_history).

Output: repos.jsonl, one object per repo:
  {full_name, clone_url, stars, license, size_kb, default_branch, pushed_at,
   description, topics}

Usage:
  python select_repos.py                       # default buckets, ~thousands
  python select_repos.py --min-stars 200 --max-repos 300   # smaller first batch
  python select_repos.py --out repos.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))

# Permissive licenses we can use for both DAPT text and git-history SFT.
# (GitHub license keys.) Copyleft (GPL/AGPL/LGPL) is deliberately excluded.
PERMISSIVE = {
    "mit",
    "apache-2.0",
    "bsd-3-clause",
    "bsd-2-clause",
    "isc",
    "mpl-2.0",
    "unlicense",
    "0bsd",
}

# Names/topics that signal a non-code repo (lists, books, courses, awesome-*).
_BAD_NAME_TOKENS = (
    "awesome",
    "interview",
    "tutorial",
    "example",
    "examples",
    "demo",
    "book",
    "course",
    "guide",
    "roadmap",
    "cheatsheet",
    "handbook",
    "learn",
    "study",
    "notes",
    "blog",
    "docs",
    "documentation",
    "hello-world",
    "boilerplate",
    "template",
)
_BAD_TOPICS = {
    "awesome",
    "awesome-list",
    "list",
    "books",
    "tutorial",
    "tutorials",
    "course",
    "education",
    "interview",
    "roadmap",
    "cheatsheet",
}


def gh_search(query: str, per_page: int, max_pages: int) -> list[dict]:
    """Run a paged GitHub repo search via `gh api`. Returns raw item dicts."""
    items: list[dict] = []
    for page in range(1, max_pages + 1):
        cmd = [
            "gh", "api", "-X", "GET", "search/repositories",
            "-f", f"q={query}",
            "-f", "sort=stars",
            "-f", "order=desc",
            "-f", f"per_page={per_page}",
            "-f", f"page={page}",
        ]
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
        except subprocess.TimeoutExpired:
            print(f"    ! timeout on page {page}", file=sys.stderr)
            break
        if out.returncode != 0:
            err = out.stderr.strip()
            # secondary-rate-limit / abuse -> back off and retry once
            if "rate limit" in err.lower() or "secondary" in err.lower():
                print("    ! rate limited; sleeping 30s", file=sys.stderr)
                time.sleep(30)
                continue
            print(f"    ! gh error page {page}: {err[:200]}", file=sys.stderr)
            break
        try:
            data = json.loads(out.stdout)
        except json.JSONDecodeError:
            break
        page_items = data.get("items", [])
        items.extend(page_items)
        total = data.get("total_count", 0)
        if len(page_items) < per_page or len(items) >= total:
            break
        # be gentle with the search API (30 req/min authenticated)
        time.sleep(2.0)
    return items


def default_buckets(min_stars: int) -> list[tuple[int, int]]:
    """Star ranges (low, high) descending. high=0 means open-ended (>= low)."""
    edges = [
        100000, 50000, 30000, 20000, 15000, 10000, 8000, 6000,
        5000, 4000, 3000, 2500, 2000, 1500, 1200, 1000,
        800, 600, 500, 400, 300, 250, 200, 150, 100,
    ]
    edges = [e for e in edges if e >= min_stars]
    if not edges or edges[-1] != min_stars:
        edges.append(min_stars)
    buckets: list[tuple[int, int]] = [(edges[0], 0)]  # top bucket open-ended
    for i in range(len(edges) - 1):
        hi, lo = edges[i], edges[i + 1]
        buckets.append((lo, hi - 1))
    return buckets


def keep(item: dict) -> tuple[bool, str]:
    """Quality gate. Returns (keep?, reason-if-dropped)."""
    if item.get("archived"):
        return False, "archived"
    if item.get("fork"):
        return False, "fork"
    if item.get("disabled"):
        return False, "disabled"
    lic = (item.get("license") or {}).get("key")
    if lic not in PERMISSIVE:
        return False, f"license:{lic}"
    size_kb = item.get("size", 0)  # in KB
    if size_kb < 50:
        return False, "too-small"
    if size_kb > 2_000_000:  # >2GB working tree, skip mega-monorepos
        return False, "too-large"
    name = (item.get("name") or "").lower()
    full = (item.get("full_name") or "").lower()
    for tok in _BAD_NAME_TOKENS:
        if tok in name:
            return False, f"name:{tok}"
    topics = set(item.get("topics") or [])
    if topics & _BAD_TOPICS:
        return False, "topic"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(_HERE, "repos.jsonl"))
    ap.add_argument("--min-stars", type=int, default=100)
    ap.add_argument("--max-repos", type=int, default=0,
                    help="stop after collecting this many (0 = all buckets)")
    ap.add_argument("--per-page", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=10,
                    help="pages per (bucket x license) query; 10*100=1000 cap")
    ap.add_argument("--licenses", default=",".join(sorted(PERMISSIVE)),
                    help="comma list of license keys to query")
    args = ap.parse_args()

    licenses = [l.strip() for l in args.licenses.split(",") if l.strip()]
    buckets = default_buckets(args.min_stars)
    print(f"buckets: {buckets}")
    print(f"licenses: {licenses}")

    seen: set[str] = set()
    kept: list[dict] = []
    drop_counts: dict[str, int] = {}

    for (lo, hi) in buckets:
        star_q = f"stars:>={lo}" if hi == 0 else f"stars:{lo}..{hi}"
        for lic in licenses:
            q = f"language:Go {star_q} license:{lic} archived:false fork:false"
            items = gh_search(q, args.per_page, args.max_pages)
            new = 0
            for it in items:
                fn = it.get("full_name")
                if not fn or fn in seen:
                    continue
                ok, reason = keep(it)
                if not ok:
                    drop_counts[reason.split(":")[0]] = drop_counts.get(
                        reason.split(":")[0], 0) + 1
                    continue
                seen.add(fn)
                kept.append({
                    "full_name": fn,
                    "clone_url": it.get("clone_url"),
                    "stars": it.get("stargazers_count", 0),
                    "license": (it.get("license") or {}).get("key"),
                    "size_kb": it.get("size", 0),
                    "default_branch": it.get("default_branch", "main"),
                    "pushed_at": it.get("pushed_at"),
                    "description": (it.get("description") or "")[:300],
                    "topics": it.get("topics") or [],
                })
                new += 1
            print(f"  {star_q:>18} license:{lic:<12} -> {len(items):4d} hits, "
                  f"+{new:3d} kept (total {len(kept)})")
            time.sleep(2.5)  # search API is 30 req/min — pace between queries
            if args.max_repos and len(kept) >= args.max_repos:
                kept = kept[: args.max_repos]
                break
        if args.max_repos and len(kept) >= args.max_repos:
            break

    kept.sort(key=lambda r: r["stars"], reverse=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r) + "\n")

    print(f"\nselected {len(kept)} repos -> {args.out}")
    print(f"drops: {drop_counts}")
    if kept:
        print("top 10:")
        for r in kept[:10]:
            print(f"  {r['stars']:>7}*  {r['full_name']:<40} {r['license']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
