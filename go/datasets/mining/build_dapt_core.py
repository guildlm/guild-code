#!/usr/bin/env python3
"""Subsample the full mined DAPT corpus into a high-quality core that fits a
free Kaggle GPU session budget.

Selection: repos ranked by GitHub stars; per-repo token cap keeps diversity
(one mega-repo can't eat the budget); doc-level filters drop stubs and
single-file monsters. Deterministic (seeded shuffle) so the core is
reproducible from the same inputs.

Usage:
  python3 build_dapt_core.py \
      --corpus go_dapt_mined.jsonl --repos repos.jsonl \
      --out go_dapt_core.jsonl --target-mtok 45
"""
import argparse
import json
import random

CHARS_PER_TOKEN = 3.4  # empirical for Go source under BPE code tokenizers

MIN_DOC_CHARS = 300     # drop near-empty stubs / build tags only
MAX_DOC_CHARS = 30_000  # drop generated-ish monsters; seq-2048 chunks anyway


def est_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def load_stars(repos_path: str) -> dict:
    stars = {}
    with open(repos_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            # corpus source dirs are owner__repo
            key = r["full_name"].replace("/", "__")
            stars[key] = int(r.get("stars", 0))
    return stars


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="go_dapt_mined.jsonl")
    ap.add_argument("--repos", default="repos.jsonl")
    ap.add_argument("--out", default="go_dapt_core.jsonl")
    ap.add_argument("--target-mtok", type=float, default=45.0,
                    help="core size budget in millions of tokens")
    ap.add_argument("--repo-cap-ktok", type=float, default=250.0,
                    help="max tokens contributed by a single repo (thousands)")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    stars = load_stars(args.repos)
    budget = int(args.target_mtok * 1_000_000)
    repo_cap = int(args.repo_cap_ktok * 1_000)

    # Pass 1: index docs per repo (offsets only — corpus is 1.2GB).
    per_repo = {}  # repo -> list[(offset, tokens)]
    dropped_short = dropped_long = 0
    with open(args.corpus, "rb") as f:
        offset = 0
        for line in f:
            row = json.loads(line)
            n = len(row["text"])
            if n < MIN_DOC_CHARS:
                dropped_short += 1
            elif n > MAX_DOC_CHARS:
                dropped_long += 1
            else:
                repo = row["source"].split("/", 1)[0]
                per_repo.setdefault(repo, []).append((offset, est_tokens(row["text"])))
            offset += len(line)

    # Rank repos by stars desc; unknown repos rank last.
    ranked = sorted(per_repo, key=lambda r: stars.get(r, 0), reverse=True)

    rng = random.Random(args.seed)
    picked = []  # offsets
    total = 0
    used_repos = 0
    for repo in ranked:
        if total >= budget:
            break
        docs = per_repo[repo][:]
        rng.shuffle(docs)  # sample across the repo, not just its first dirs
        repo_tok = 0
        took = False
        for off, tok in docs:
            if total >= budget or repo_tok + tok > repo_cap:
                continue
            picked.append(off)
            repo_tok += tok
            total += tok
            took = True
        if took:
            used_repos += 1

    rng.shuffle(picked)  # decorrelate repo order for training

    with open(args.corpus, "rb") as src, open(args.out, "wb") as out:
        for off in picked:
            src.seek(off)
            out.write(src.readline())

    print(f"core: {len(picked)} docs, ~{total/1e6:.1f}M tokens, "
          f"{used_repos} repos (of {len(per_repo)})")
    print(f"filtered: {dropped_short} short, {dropped_long} long")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
