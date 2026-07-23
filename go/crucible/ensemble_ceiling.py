# -*- coding: utf-8 -*-
"""The ensemble ceiling from saved generations — no model, $0.

No single specialist beats base on go_dev_bench, but several solve a FEW tasks base
misses. This asks the algorithm question directly: how many tasks does AT LEAST ONE
model solve (best-of-across-models), and how many does the base miss that some
specialist rescues? That union is the ceiling a model-routing / best-of-N loop could
reach — the "capability = model x algorithm" claim, quantified.

    ensemble_ceiling.py --base d_base.jsonl --spec d_v4.jsonl d_final.jsonl ... [--repair imports]

Scoring is imported from the bench, so this cannot drift from a live run.
"""
import argparse
import json
import os

from mlx_bench import compiles, runs_green  # noqa: F401  (compiles kept for parity)
from mlx_test_bench import _goimports, _repair_imports

HERE = os.path.dirname(os.path.abspath(__file__))


def pass_set(path, tests, exe):
    """Task ids this generation file passes (optionally after goimports)."""
    ok = set()
    for line in open(path):
        if not line.strip():
            continue
        g = json.loads(line)
        code = g["code"]
        if exe:
            code = _repair_imports(code, exe)
        if g["id"] in tests and runs_green(code, tests[g["id"]]):
            ok.add(g["id"])
    return ok


def label_of(path):
    for line in open(path):
        if line.strip():
            return json.loads(line).get("label", os.path.basename(path))
    return os.path.basename(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--spec", nargs="+", required=True, help="specialist generation files")
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_dev_bench.jsonl"))
    ap.add_argument("--repair", choices=("none", "imports"), default="imports")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(args.bench) if l.strip()]
    tests = {t["id"]: t["metadata"]["tests"] for t in tasks}
    n = len(tests)

    exe = ""
    if args.repair == "imports":
        exe = _goimports()
        if not exe:
            raise SystemExit("--repair imports requested but goimports not found")

    base = pass_set(args.base, tests, exe)
    specs = {label_of(p): pass_set(p, tests, exe) for p in args.spec}

    rep = " (+goimports)" if exe else ""
    print(f"ensemble ceiling{rep} over {n} tasks\n")
    print(f"  base                       {len(base):>3}/{n}")
    for lab, s in specs.items():
        print(f"  {lab[:24]:<24}   {len(s):>3}/{n}")

    union_all = set(base)
    for s in specs.values():
        union_all |= s
    rescued = union_all - base  # tasks base misses that SOME model solves
    print(f"\n  best single model          {max([len(base)] + [len(s) for s in specs.values()]):>3}/{n}")
    print(f"  UNION base+specialists     {len(union_all):>3}/{n}  (+{len(union_all)-len(base)} over base)")
    print(f"  tasks base MISSES but a specialist rescues: {sorted(rescued)}")
    # which specialist rescues each
    for tid in sorted(rescued):
        who = [lab for lab, s in specs.items() if tid in s]
        print(f"    {tid:<18} <- {who}")
    only_none = n - len(union_all)
    print(f"\n  tasks NO model solves: {only_none}  "
          f"{sorted(set(tests) - union_all) if only_none else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
