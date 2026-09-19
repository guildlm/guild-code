# -*- coding: utf-8 -*-
"""A self-written test has two properties, and validity is only one of them.
  validity     = passes the task's REFERENCE solution                 (is it right about the spec?)
  teeth        = fails a candidate the hidden bench says is WRONG      (does it bite?)
  false alarm  = fails a candidate the hidden bench says is RIGHT      (does it bite the innocent?)
Computed from saved router_selftests_*.jsonl (self verdicts per candidate, after the pipeline that
produced the file) joined with the candidates' saved hidden verdicts. Nothing generated.
    python writer_teeth.py data/router_selftests_v2_*.jsonl
"""
import json
import sys

C = {"30b": "data/go_dev_bench_qwen3coder30b_served_t0.jsonl", "7b": "data/go_dev_bench_base7b_greedy.jsonl"}


def load(p):
    return {json.loads(l)["id"]: json.loads(l) for l in open(p)}


def main(paths):
    hidden = {n: {i: bool(r["verdict"]) for i, r in load(p).items()} for n, p in C.items()}
    print(f"{'writer':44} {'valid':>6} {'teeth':>9} {'false alarm':>12}   (teeth = wrong candidates failed; false alarm = right candidates failed)")
    for p in paths:
        rows = load(p)
        writer = next(iter(rows.values())).get("writer", "?")
        valid = sum(bool(r.get("valid_on_reference")) for r in rows.values())
        wrong = right = bite = alarm = 0
        for i, r in rows.items():
            s = r.get("self", {})
            for n in C:
                if hidden[n][i]:
                    right += 1; alarm += (not s.get(n, False))
                else:
                    wrong += 1; bite += (not s.get(n, False))
        print(f"{writer:44} {valid:>3}/48 {bite:>4}/{wrong:<4} {alarm:>6}/{right:<4}   {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
