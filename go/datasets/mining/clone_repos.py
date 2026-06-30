# -*- coding: utf-8 -*-
"""Stage 2 of the GitHub Go mining pipeline — clone the selected repos.

Reads repos.jsonl (from select_repos.py) and clones each repo into a local,
gitignored cache. We use a *bounded-depth* clone so a single pass gives us both
things the recipe needs, cheaply and at $0:
  - the HEAD working tree            -> raw .go for the DAPT corpus (stage 3)
  - the last N commits of history    -> (message, diff) task data (stage 4)

Design notes:
  - Parallel (git clone is network/IO bound) with a small worker pool.
  - Resumable: a repo whose clone dir is already a valid git repo is skipped.
  - Disk-aware: stops launching new clones once free space drops below a floor.
  - Size-aware: --max-size-kb skips mega-repos (e.g. kubernetes) for small runs.
  - Per-clone timeout so one slow repo can't wedge the pool.

Usage:
  python clone_repos.py                                  # clone all of repos.jsonl
  python clone_repos.py --repos repos.smoke.jsonl --limit 15 --max-size-kb 150000
  python clone_repos.py --depth 400 --jobs 6
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CACHE = os.path.join(_HERE, "repos")


def slug(full_name: str) -> str:
    return full_name.replace("/", "__")


def is_valid_clone(path: str) -> bool:
    return os.path.isdir(os.path.join(path, ".git"))


def free_gb(path: str) -> float:
    st = shutil.disk_usage(path)
    return st.free / 1e9


def clone_one(repo: dict, cache: str, depth: int, timeout: int) -> tuple[str, str, float]:
    """Returns (full_name, status, size_gb_of_clone)."""
    fn = repo["full_name"]
    dest = os.path.join(cache, slug(fn))
    if is_valid_clone(dest):
        return fn, "skip-exists", _dir_gb(dest)
    # clean a partial/failed dir
    if os.path.exists(dest):
        shutil.rmtree(dest, ignore_errors=True)
    url = repo.get("clone_url") or f"https://github.com/{fn}.git"
    branch = repo.get("default_branch") or "main"
    cmd = [
        "git", "clone",
        "--depth", str(depth),
        "--single-branch",
        "--no-tags",
        "--quiet",
        url, dest,
    ]
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest, ignore_errors=True)
        return fn, "timeout", 0.0
    if out.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        return fn, f"err:{out.stderr.strip()[:80]}", 0.0
    return fn, "cloned", _dir_gb(dest)


def _dir_gb(path: str) -> float:
    total = 0
    for dp, _d, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total / 1e9


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default=os.path.join(_HERE, "repos.jsonl"))
    ap.add_argument("--cache", default=_DEFAULT_CACHE)
    ap.add_argument("--depth", type=int, default=400,
                    help="commit depth to fetch (history for mining + HEAD tree)")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="clone at most N repos")
    ap.add_argument("--max-size-kb", type=int, default=0,
                    help="skip repos whose GitHub size_kb exceeds this (0=no cap)")
    ap.add_argument("--min-free-gb", type=float, default=20.0,
                    help="stop launching clones when free disk drops below this")
    ap.add_argument("--timeout", type=int, default=600, help="per-clone seconds")
    args = ap.parse_args()

    os.makedirs(args.cache, exist_ok=True)
    with open(args.repos, encoding="utf-8") as fh:
        repos = [json.loads(l) for l in fh if l.strip()]

    if args.max_size_kb:
        before = len(repos)
        repos = [r for r in repos if r.get("size_kb", 0) <= args.max_size_kb]
        print(f"size filter (<= {args.max_size_kb} KB): {before} -> {len(repos)}")
    if args.limit:
        repos = repos[: args.limit]

    print(f"cloning {len(repos)} repos into {args.cache} "
          f"(depth={args.depth}, jobs={args.jobs}, free={free_gb(args.cache):.0f}GB)")

    counts: dict[str, int] = {}
    cloned_gb = 0.0
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futures = {}
        it = iter(repos)
        # prime the pool, then refill as each finishes (disk-guarded)
        for _ in range(min(args.jobs, len(repos))):
            try:
                r = next(it)
            except StopIteration:
                break
            futures[ex.submit(clone_one, r, args.cache, args.depth, args.timeout)] = r

        while futures:
            for fut in as_completed(list(futures)):
                r = futures.pop(fut)
                fn, status, gb = fut.result()
                done += 1
                key = status.split(":")[0]
                counts[key] = counts.get(key, 0) + 1
                cloned_gb += gb if status == "cloned" else 0.0
                tag = "✓" if status in ("cloned", "skip-exists") else "✗"
                print(f"  [{done:4d}/{len(repos)}] {tag} {fn:<45} {status:<14} "
                      f"({gb:.2f}GB, free {free_gb(args.cache):.0f}GB)")
                # refill one, unless disk is low
                if free_gb(args.cache) < args.min_free_gb:
                    print(f"  ! free disk < {args.min_free_gb}GB — stopping new clones")
                    it = iter(())  # drain
                try:
                    nr = next(it)
                    futures[ex.submit(clone_one, nr, args.cache, args.depth, args.timeout)] = nr
                except StopIteration:
                    pass
                break  # re-enter as_completed with the refilled set

    dt = time.time() - t0
    print(f"\ndone in {dt/60:.1f} min. status: {counts}. "
          f"added ~{cloned_gb:.1f}GB. cache: {args.cache}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
