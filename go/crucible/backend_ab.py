# -*- coding: utf-8 -*-
"""Compare saved go_dev_bench generations across builds/backends of the same model — the
quantization A/B, tabulated instead of counted by hand.
    python backend_ab.py  7b-mlx=data/go_dev_bench_base7b_greedy.jsonl \
                          7b-ollama=data/go_dev_bench_base7b_served_t0.jsonl \
                          30b-mlx=data/go_dev_bench_qwen3coder30b_greedy.jsonl \
                          30b-ollama=data/go_dev_bench_qwen3coder30b_served_t0.jsonl
Prints, per file: pass@1, compiles, the 1-space-indent fingerprint count (lines indented
by exactly one space — gofmt never emits that; it marks a lossy build), and for every
pair sharing a model prefix ("7b-", "30b-"): agreement, and the tasks that flipped.
Raw verdicts only (as saved); run rescore_dev_bench.py for the +goimports view.
"""
import itertools
import json
import sys


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in open(path)}


def fingerprint(code: str) -> bool:
    return any(l.startswith(" ") and not l.startswith("  ") for l in code.splitlines())


def main(argv):
    runs = {}
    for a in argv:
        name, path = a.split("=", 1)
        runs[name] = load(path)
    ids = None
    print(f"{'run':14} {'pass@1':>7} {'compiles':>9} {'1-space':>8}")
    for name, r in runs.items():
        ids = ids or list(r)
        p = sum(v["verdict"] for v in r.values()); c = sum(v["compiles"] for v in r.values())
        f = sum(fingerprint(v["code"]) for v in r.values())
        print(f"{name:14} {p:>4}/{len(r):<2} {c:>5}/{len(r):<3} {f:>5}/{len(r)}")
    print()
    for a, b in itertools.combinations(runs, 2):
        pa, pb = a.split("-")[0], b.split("-")[0]
        if pa != pb:
            continue
        ra, rb = runs[a], runs[b]
        same = sum(ra[i]["verdict"] == rb[i]["verdict"] for i in ids)
        only_a = sorted(i for i in ids if ra[i]["verdict"] and not rb[i]["verdict"])
        only_b = sorted(i for i in ids if rb[i]["verdict"] and not ra[i]["verdict"])
        byte_same = sum(ra[i]["code"] == rb[i]["code"] for i in ids)
        print(f"{a} vs {b}: verdict agreement {same}/{len(ids)} · byte-identical code {byte_same}/{len(ids)}")
        print(f"   only {a}: {only_a}")
        print(f"   only {b}: {only_b}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
