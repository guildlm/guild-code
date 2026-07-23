# -*- coding: utf-8 -*-
"""Realizable vs oracle ensemble on saved generations — no model, $0.

ensemble_ceiling.py reports the ORACLE union (it knows which model passes the hidden
test). A real router cannot see the hidden test; on go_dev_bench its only visible signal
is compile/vet. This asks: how much of the oracle's +N is actually CAPTURABLE by a
compile-gated router?

Policy 'compile-first': try models in order, pick the FIRST candidate that compiles
(after goimports); score whether that pick passes the hidden test. Base is tried first
(it is the best single model), so the router only leaves base when base does NOT compile.

The point it usually makes: base's WRONG answers still compile, so a compile-only gate
keeps them and captures little of the oracle gap -> the ensemble needs a TEST signal
(the real Builder loop has one; this bench does not hand it to the router).

    realizable_router.py --base d_base.jsonl --spec d_v4.jsonl d_final.jsonl ... [order matters]

Model-free: imports the bench scorer.
"""
import argparse
import json
import os

from mlx_bench import compiles, runs_green
from mlx_test_bench import _goimports, _repair_imports

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in open(path) if l.strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--spec", nargs="+", required=True)
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_dev_bench.jsonl"))
    args = ap.parse_args()

    tasks = [json.loads(l) for l in open(args.bench) if l.strip()]
    tests = {t["id"]: t["metadata"]["tests"] for t in tasks}
    exe = _goimports()
    if not exe:
        raise SystemExit("goimports not found (required — the visible gate is compile)")

    fleet = [("base", load(args.base))] + [
        (os.path.basename(p).replace("go_dev_bench_", "").replace("_greedy.jsonl", ""), load(p))
        for p in args.spec]

    router_pass, base_pass, oracle_pass, routed_away = 0, 0, 0, 0
    for tid, test in tests.items():
        cands = [(name, _repair_imports(g[tid]["code"], exe)) for name, g in fleet if tid in g]
        if not cands:
            continue
        # base score (first member, assumed base)
        b_ok = runs_green(cands[0][1], test)
        base_pass += b_ok
        # oracle: any candidate passes the hidden test
        oracle_pass += any(runs_green(c, test) for _, c in cands)
        # realizable: first candidate that COMPILES, score its hidden-test result
        pick = next((c for _, c in cands if compiles(c)), cands[0][1])
        if pick is not cands[0][1]:
            routed_away += 1
        router_pass += runs_green(pick, test)

    n = len(tests)
    print(f"realizable router (compile-first, base-first) over {n} tasks\n")
    print(f"  base alone                 {base_pass}/{n}")
    print(f"  compile-gated router       {router_pass}/{n}   (routed away from base on {routed_away} tasks)")
    print(f"  ORACLE union (upper bound) {oracle_pass}/{n}")
    print(f"\n  captured by a compile gate: {router_pass - base_pass} of the "
          f"{oracle_pass - base_pass} oracle gain")
    if oracle_pass > base_pass and router_pass <= base_pass:
        print("  => a compile-only gate captures NONE of it: base's wrong answers compile,\n"
              "     so the ensemble needs a TEST signal, not just compile/vet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
