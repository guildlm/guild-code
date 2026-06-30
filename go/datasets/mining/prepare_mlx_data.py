# -*- coding: utf-8 -*-
"""Bridge the mined corpora into MLX-LM training directories.

`mlx_lm lora` (the local M1 trainer) reads a directory with train.jsonl +
valid.jsonl. This turns the stage 3-5 outputs into those dirs:

  DAPT (continued pretraining, raw next-token):
      go_dapt_mined.jsonl  (+ optional stdlib go_corpus.jsonl)  -> {"text": ...}
      -> <out>/dapt/{train,valid}.jsonl

  go-dev SFT (apply-change + bug-fix edits):
      mined_dev.jsonl + mined_bugfix.jsonl  -> {"messages": [...]}
      -> <out>/godev/{train,valid}.jsonl

  go-review SFT (review comments):
      mined_review.jsonl  -> {"messages": [...]}
      -> <out>/goreview/{train,valid}.jsonl

Deterministic (seeded shuffle, no Math.random concerns — plain Python), with a
held-out valid split and optional caps so one source can't dominate.

Usage:
  python prepare_mlx_data.py --out ../../../../.mlx-data-mined
  python prepare_mlx_data.py --merge-stdlib --dapt-cap 60000 --sft-cap 0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_STDLIB = os.path.join(_HERE, "..", "pretrain", "go_corpus.jsonl")


def load_jsonl(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def dedup_text(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        t = r.get("text", "")
        h = hashlib.sha256(t.encode("utf-8", "ignore")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append({"text": t})
    return out


def dedup_messages(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        msgs = r.get("messages")
        if not msgs:
            continue
        key = hashlib.sha256(
            json.dumps(msgs, sort_keys=True).encode("utf-8", "ignore")
        ).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append({"messages": msgs})
    return out


def write_split(rows: list[dict], out_dir: str, valid_frac: float, rng: random.Random):
    if not rows:
        return 0, 0
    os.makedirs(out_dir, exist_ok=True)
    rng.shuffle(rows)
    n_valid = max(1, int(len(rows) * valid_frac)) if len(rows) > 20 else max(1, len(rows) // 10)
    n_valid = min(n_valid, len(rows) - 1) if len(rows) > 1 else 0
    valid, train = rows[:n_valid], rows[n_valid:]
    for name, part in (("train", train), ("valid", valid)):
        with open(os.path.join(out_dir, f"{name}.jsonl"), "w", encoding="utf-8") as fh:
            for r in part:
                fh.write(json.dumps(r) + "\n")
    return len(train), len(valid)


def cap(rows: list[dict], n: int, rng: random.Random) -> list[dict]:
    if n and len(rows) > n:
        rng.shuffle(rows)
        return rows[:n]
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(_HERE, "..", "..", "..", "..",
                                                  ".mlx-data-mined"))
    ap.add_argument("--merge-stdlib", action="store_true",
                    help="include the stdlib go_corpus.jsonl in the DAPT split")
    ap.add_argument("--dapt-cap", type=int, default=0, help="max DAPT docs (0=all)")
    ap.add_argument("--sft-cap", type=int, default=0, help="max SFT rows/role (0=all)")
    ap.add_argument("--valid-frac", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = os.path.abspath(args.out)
    summary = {}

    # --- DAPT ---
    dapt = load_jsonl(os.path.join(_HERE, "go_dapt_mined.jsonl"))
    if args.merge_stdlib:
        dapt += load_jsonl(_STDLIB)
    dapt = dedup_text(dapt)
    dapt = cap(dapt, args.dapt_cap, rng)
    summary["dapt"] = write_split(dapt, os.path.join(out, "dapt"),
                                  args.valid_frac, rng)

    # --- go-dev SFT (apply-change + bug-fix) ---
    dev = load_jsonl(os.path.join(_HERE, "mined_dev.jsonl")) \
        + load_jsonl(os.path.join(_HERE, "mined_bugfix.jsonl"))
    dev = dedup_messages(dev)
    dev = cap(dev, args.sft_cap, rng)
    summary["godev"] = write_split(dev, os.path.join(out, "godev"),
                                   args.valid_frac, rng)

    # --- go-review SFT ---
    rev = dedup_messages(load_jsonl(os.path.join(_HERE, "mined_review.jsonl")))
    rev = cap(rev, args.sft_cap, rng)
    summary["goreview"] = write_split(rev, os.path.join(out, "goreview"),
                                      args.valid_frac, rng)

    print(f"MLX data dirs written under {out}:")
    for role, (ntr, nva) in summary.items():
        print(f"  {role:<10} train={ntr:<7} valid={nva}")
    if all(t == 0 for t, _ in summary.values()):
        print("\n! no input found — run the mining stages first", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
