# -*- coding: utf-8 -*-
"""Report on the mined corpora — how much real Go data the recipe produced.

Summarizes the stage 3-5 outputs so we can plan DAPT (token budget) and SFT
(role balance, per-repo skew) before training. Read-only, fast.

Usage:
  python dataset_stats.py
"""
from __future__ import annotations

import json
import os
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))


def iter_jsonl(path: str):
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass


def human(n: float) -> str:
    for unit in ("", "K", "M", "B"):
        if abs(n) < 1000:
            return f"{n:.1f}{unit}"
        n /= 1000
    return f"{n:.1f}T"


def stat_dapt(path: str, label: str):
    docs = chars = 0
    for r in iter_jsonl(path):
        t = r.get("text", "")
        if t:
            docs += 1
            chars += len(t)
    if docs:
        print(f"  {label:<22} {docs:>7} docs  ~{human(chars/4)} tokens "
              f"({human(chars)} chars)")
    return docs, chars


def stat_sft(path: str, label: str):
    n = chars = 0
    for r in iter_jsonl(path):
        msgs = r.get("messages", [])
        if not msgs:
            continue
        n += 1
        chars += sum(len(m.get("content", "")) for m in msgs)
    if n:
        avg = chars // n if n else 0
        print(f"  {label:<22} {n:>7} examples  avg {human(avg)} chars "
              f"(~{human(chars/4)} tokens total)")
    return n


def main() -> int:
    print("=== DAPT corpus (continued-pretraining text) ===")
    md, mc = stat_dapt(os.path.join(_HERE, "go_dapt_mined.jsonl"), "mined")
    sd, sc = stat_dapt(os.path.join(_HERE, "..", "pretrain", "go_corpus.jsonl"),
                       "stdlib (existing)")
    if md or sd:
        print(f"  {'COMBINED':<22} {md+sd:>7} docs  ~{human((mc+sc)/4)} tokens")

    print("\n=== SFT task data (git history) ===")
    stat_sft(os.path.join(_HERE, "mined_dev.jsonl"), "go-dev (feature/refactor)")
    stat_sft(os.path.join(_HERE, "mined_bugfix.jsonl"), "go-dev (bug-fix)")
    stat_sft(os.path.join(_HERE, "mined_review.jsonl"), "go-review")

    # category + per-repo distribution from the commit metadata
    meta = list(iter_jsonl(os.path.join(_HERE, "mined_commits.jsonl")))
    if meta:
        cats = Counter(m.get("category") for m in meta)
        repos = Counter(m.get("repo") for m in meta)
        print(f"\n=== mined commit categories ({len(meta)} total) ===")
        for c, n in cats.most_common():
            print(f"  {c:<12} {n}")
        print(f"\n=== top contributing repos (of {len(repos)}) ===")
        for r, n in repos.most_common(12):
            print(f"  {n:>5}  {r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
