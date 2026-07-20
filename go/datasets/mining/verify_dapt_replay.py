#!/usr/bin/env python3
"""Pre-flight check for a REPLAY-MIX DAPT corpus before an (expensive) Kaggle run.

Recipe 1 (pure next-token on raw Go over the INSTRUCT base) damaged chat behaviour:
the model stopped emitting <|im_end|>, rambled, and failed every Builder run. The fix
(build_dapt_replay.py) interleaves chat-FORMATTED docs so the special tokens stay
in-distribution. This script confirms that fix actually landed in the file — the whole
point of the replay slice is worthless if the replay docs are not chat-terminated.

Checks (model-free, streams the file so a 200MB+ corpus is fine):
  - every line is valid JSON with `text` and `source`;
  - the replay fraction (replay chars / total chars) is in a sane band;
  - EVERY replay doc carries <|im_start|>/<|im_end|> and ENDS with <|im_end|> — the
    exact token recipe-1 stopped emitting. This is the gate: less than 100% here means
    the replay slice will not hold chat behaviour and the run will waste GPU;
  - core docs are raw Go, not stray chat docs (a chat token in a core doc is reported
    but tolerated — a handful of mined Go files legitimately quote the tokens).

Usage:  verify_dapt_replay.py <corpus.jsonl> [--min-frac 0.15] [--max-frac 0.35]
  exit 0 = safe to DAPT; exit 1 = a gate failed (details printed).
"""
import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--min-frac", type=float, default=0.15)
    ap.add_argument("--max-frac", type=float, default=0.35)
    args = ap.parse_args()

    n = bad = 0
    core_d = core_c = rep_d = rep_c = 0
    has_start = has_end = ends_end = core_contam = 0
    for line in open(args.corpus):
        if not line.strip():
            continue
        n += 1
        try:
            r = json.loads(line)
            t, s = r["text"], r["source"]
        except Exception:
            bad += 1
            continue
        if s.startswith("replay"):
            rep_d += 1
            rep_c += len(t)
            has_start += "<|im_start|>" in t
            has_end += "<|im_end|>" in t
            ends_end += t.rstrip().endswith("<|im_end|>")
        else:
            core_d += 1
            core_c += len(t)
            core_contam += "<|im_start|>" in t

    tot = core_c + rep_c
    frac = rep_c / tot if tot else 0.0
    print(f"lines {n}  malformed {bad}")
    print(f"core   {core_d} docs  {core_c/1e6:.1f}M chars")
    print(f"replay {rep_d} docs  {rep_c/1e6:.1f}M chars")
    print(f"replay fraction  {frac:.2%}  (band {args.min_frac:.0%}-{args.max_frac:.0%})")
    if rep_d:
        print(f"replay chat-integrity  im_start {has_start/rep_d:.1%} | "
              f"im_end {has_end/rep_d:.1%} | ENDS-with-im_end {ends_end/rep_d:.1%}")
    print(f"core docs quoting a chat token  {core_contam} (tolerated: raw Go may quote them)")

    fails = []
    if bad:
        fails.append(f"{bad} malformed line(s)")
    if rep_d == 0:
        fails.append("no replay docs — chat behaviour will collapse")
    elif ends_end != rep_d:
        fails.append(f"{rep_d - ends_end} replay doc(s) do NOT end with <|im_end|> "
                     f"— the recipe-1 failure the replay slice exists to prevent")
    if not (args.min_frac <= frac <= args.max_frac):
        fails.append(f"replay fraction {frac:.1%} outside band "
                     f"{args.min_frac:.0%}-{args.max_frac:.0%}")

    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nOK — corpus is well-formed and chat-terminated; safe to DAPT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
