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
import sys


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


def bodies_of(tasks, min_body):
    """Map task id -> normalised reference body, dropping bodies too short to be evidence."""
    bodies = {}
    for t in tasks:
        ref = t.get("reference", "")
        body = norm(re.sub(r"^package \w+", "", ref))
        if len(body) >= min_body:
            bodies[t["id"]] = body
    return bodies


def find_leaks(bodies, train_paths):
    """Return {task id -> sorted training files whose text contains the body verbatim}."""
    leaks: dict[str, set[str]] = {tid: set() for tid in bodies}
    for path in train_paths:
        for doc in train_docs(path):
            nd = norm(doc)
            for tid, body in bodies.items():
                if body in nd:
                    leaks[tid].add(path)
    return {tid: sorted(w) for tid, w in leaks.items() if w}


def _self_test() -> int:
    """Prove the matcher FIRES on a planted leak and stays quiet otherwise — a
    contamination checker that silently stopped matching would report every future
    training set 'clean', the most dangerous false-negative a credibility gate can have.

    Uses synthetic fixtures, no real corpora and no Go toolchain, so it can run in CI even
    though the full check (which needs the 170MB+ gitignored training sets) cannot.
    """
    import tempfile

    LONG = "package sandbox\n\nfunc Add(a, b, c int) int {\n\treturn a + b + c\n}\n"
    SHORT = "package sandbox\n\nfunc A() {}\n"  # body < min_body, must be ignored
    tasks = [{"id": "leaked", "reference": LONG},
             {"id": "clean", "reference": "package sandbox\n\nfunc Sub(a, b int) int {\n\treturn a - b - a - b\n}\n"},
             {"id": "tiny", "reference": SHORT}]

    fails = []

    def want(label, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            fails.append(label)

    bodies = bodies_of(tasks, min_body=40)
    want("short body excluded from checking", "tiny" not in bodies and {"leaked", "clean"} <= set(bodies))

    with tempfile.TemporaryDirectory() as d:
        import os
        # a chat SFT doc that embeds the leaked reference verbatim (whitespace differs)
        leak_train = os.path.join(d, "sft.jsonl")
        with open(leak_train, "w") as f:
            f.write(json.dumps({"messages": [{"role": "assistant",
                     "content": "Here you go:\n\nfunc Add(a, b, c int) int { return a + b + c }\n"}]}) + "\n")
        # a raw-text DAPT doc with only unrelated Go
        clean_train = os.path.join(d, "dapt.jsonl")
        with open(clean_train, "w") as f:
            f.write(json.dumps({"text": "package main\nfunc main() { println(42) }\n"}) + "\n")

        hit = find_leaks(bodies, [leak_train])
        want("planted leak is caught", list(hit) == ["leaked"] and hit["leaked"] == [leak_train])

        want("unrelated corpus is clean", find_leaks(bodies, [clean_train]) == {})

    print(f"\ncheck_contamination self-test: {len(fails)} failure(s)"
          + (f" {fails}" if fails else " — matcher fires on a leak, quiet otherwise"))
    return 1 if fails else 0


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return _self_test()

    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--train", action="append", required=True, help="training JSONL; repeatable")
    ap.add_argument("--min-body", type=int, default=40, help="ignore reference bodies shorter than this")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(args.bench) if l.strip()]
    bodies = bodies_of(tasks, args.min_body)
    hit = find_leaks(bodies, args.train)

    print(f"bench {len(tasks)} tasks ({len(bodies)} with a checkable reference) "
          f"vs {len(args.train)} training file(s)\n")
    for tid, where in hit.items():
        print(f"  LEAK  {tid:<18} in: {', '.join(w.split('/')[-2] + '/' + w.split('/')[-1] for w in where)}")
    print(f"\n{len(hit)}/{len(bodies)} reference bodies found VERBATIM in training "
          f"({'CONTAMINATION' if hit else 'none — clean'}).")
    return 1 if hit else 0


if __name__ == "__main__":
    raise SystemExit(main())
