#!/usr/bin/env python3
"""Train-test contamination gate: is a benchmark's answer in the training data?

The classic way a pass@1 number lies. If a task's reference solution is verbatim in
the training corpus, a model trained on it can MEMORISE the answer, and its pass on
that task measures recall, not capability. This checks the go_*_bench references
against any training JSONL (chat {"messages":[...]} SFT sets and/or raw {"text":...}
DAPT corpora), streaming so a 170MB+ corpus is fine.

A function body lives inside ONE training document, so an exact reference-body match
against a single training doc is unambiguous leakage. Single shared LINES (a
`for i := 0; i < n; i++` idiom) are NOT reported — they are common Go, not leakage.

Usage:
  check_contamination.py --bench data/go_dev_bench.jsonl \
      --train ~/.../.mlx-data-godev-mixed-v4-7b/train.jsonl \
      --train ~/.../go/datasets/mining/go_dapt_core.jsonl
  exit 0 = no reference-body leaked; exit 1 = at least one leaked (listed).
"""
import argparse
import json
import re


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def train_docs(path: str):
    """Yield each training document's text, from chat or raw-text JSONL."""
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if "messages" in obj:
            for m in obj["messages"]:
                yield m.get("content", "")
        elif "text" in obj:
            yield obj["text"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--train", action="append", required=True, help="training JSONL; repeatable")
    ap.add_argument("--min-body", type=int, default=40, help="ignore reference bodies shorter than this")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(args.bench) if l.strip()]
    bodies = {}
    for t in tasks:
        ref = t.get("reference", "")
        body = norm(re.sub(r"^package \w+", "", ref))
        if len(body) >= args.min_body:
            bodies[t["id"]] = body

    leaks: dict[str, set[str]] = {tid: set() for tid in bodies}
    for path in args.train:
        for doc in train_docs(path):
            nd = norm(doc)
            for tid, body in bodies.items():
                if body in nd:
                    leaks[tid].add(path)

    hit = {tid: sorted(w) for tid, w in leaks.items() if w}
    print(f"bench {len(tasks)} tasks ({len(bodies)} with a checkable reference) "
          f"vs {len(args.train)} training file(s)\n")
    for tid, where in hit.items():
        print(f"  LEAK  {tid:<18} in: {', '.join(w.split('/')[-2] + '/' + w.split('/')[-1] for w in where)}")
    print(f"\n{len(hit)}/{len(bodies)} reference bodies found VERBATIM in training "
          f"({'CONTAMINATION' if hit else 'none — clean'}).")
    return 1 if hit else 0


if __name__ == "__main__":
    raise SystemExit(main())
