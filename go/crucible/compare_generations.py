# -*- coding: utf-8 -*-
"""Per-task base-vs-specialist comparison from saved generations — no model, $0.

The aggregate pass@1 gap (e.g. base 44 vs specialist 40) does not say whether the
specialist loses SYSTEMATICALLY or on a few tasks, nor whether it WINS anywhere. This
reads two --save-generations files, scores each task the same way the bench does
(optionally after goimports), and reports the win/loss/tie breakdown per task.

    compare_generations.py --base d_base.jsonl --spec d_v4.jsonl [--repair imports]

Scoring is imported from the bench, so this cannot drift from a live run.
"""
import argparse
import json
import os

from mlx_bench import compiles, runs_green
from mlx_test_bench import _goimports, _repair_imports

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in open(path) if l.strip()}


def verdict(code, test, exe):
    if exe:
        code = _repair_imports(code, exe)
    ok = runs_green(code, test)
    return ok, (ok or compiles(code))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="baseline generations JSONL")
    ap.add_argument("--spec", required=True, help="specialist generations JSONL")
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_dev_bench.jsonl"))
    ap.add_argument("--repair", choices=("none", "imports"), default="none")
    args = ap.parse_args()

    tests = {json.loads(l)["id"]: json.loads(l)["metadata"]["tests"]
             for l in open(args.bench) if l.strip()}
    base, spec = load(args.base), load(args.spec)
    ids = [i for i in tests if i in base and i in spec]

    exe = ""
    if args.repair == "imports":
        exe = _goimports()
        if not exe:
            raise SystemExit("--repair imports requested but goimports not found")

    both, neither, base_only, spec_only = [], [], [], []
    for i in ids:
        b_ok, _ = verdict(base[i]["code"], tests[i], exe)
        s_ok, _ = verdict(spec[i]["code"], tests[i], exe)
        (both if b_ok and s_ok else
         neither if not b_ok and not s_ok else
         base_only if b_ok else spec_only).append(i)

    blabel = base[ids[0]].get("label", "base")
    slabel = spec[ids[0]].get("label", "spec")
    rep = "" if not exe else " (+goimports)"
    print(f"per-task compare{rep}: {blabel} vs {slabel}  ·  {len(ids)} tasks\n")
    print(f"  both pass          {len(both):>3}")
    print(f"  {blabel[:16]:<16} ONLY {len(base_only):>3}  (base wins)  {base_only}")
    print(f"  {slabel[:16]:<16} ONLY {len(spec_only):>3}  (spec wins)  {spec_only}")
    print(f"  neither passes     {len(neither):>3}  {neither}")
    net = len(base_only) - len(spec_only)
    print(f"\n  net = base_wins - spec_wins = {len(base_only)} - {len(spec_only)} = "
          f"{'+' if net >= 0 else ''}{net} in base's favour")
    print(f"  aggregate: base {len(both)+len(base_only)}/{len(ids)} · "
          f"spec {len(both)+len(spec_only)}/{len(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
