# -*- coding: utf-8 -*-
"""Re-score saved go_dev_bench generations, optionally after a repair — no model, $0.

Completes the offline trio (test / review / dev). The point it makes concrete: a
POST-HOC DETERMINISTIC repair never needs the model again. Greedy generation is
deterministic, so re-running mlx_bench with --repair imports reproduces byte-identical
code and only differs in the goimports call — which is a subprocess, not a GPU pass. That
re-run costs ~7 minutes per model; this costs seconds and answers the same question.

    python rescore_dev_bench.py --generations d_base.jsonl --repair imports

Reports pass@1 with the same compiles / passes-given-compiles decomposition as the live
bench, plus which tasks the repair flipped. Scoring and repair are imported from the
benches themselves, so offline and live results cannot drift.
"""
import argparse
import json
import os

from mlx_bench import compiles, runs_green
from mlx_test_bench import _goimports, _repair_imports

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", required=True, help="JSONL from --save-generations")
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_dev_bench.jsonl"))
    ap.add_argument("--repair", choices=("none", "imports"), default="none")
    args = ap.parse_args()

    bench = {}
    for line in open(args.bench):
        t = json.loads(line)
        bench[t["id"]] = t["metadata"]["tests"]
    gens = [json.loads(l) for l in open(args.generations)]
    unknown = [g["id"] for g in gens if g["id"] not in bench]
    if unknown:
        raise SystemExit(f"generations contain ids absent from the bench: {unknown}")

    exe = ""
    if args.repair == "imports":
        exe = _goimports()
        if not exe:
            raise SystemExit("--repair imports requested but goimports was not found")

    label = gens[0].get("label", "?") if gens else "?"
    passed, built, n_repaired, flips, detail = 0, 0, 0, [], []
    for g in gens:
        code = g["code"]
        if exe:
            fixed = _repair_imports(code, exe)
            n_repaired += fixed != code
            code = fixed
        ok = runs_green(code, bench[g["id"]])
        builds = ok or compiles(code)
        passed += ok
        built += builds
        detail.append(f"{'+' if ok else ('v' if builds else '-')}{g['id']}")
        if ok != g.get("verdict"):
            flips.append(f"{g['id']}:{'+' if g.get('verdict') else '-'}->{'+' if ok else '-'}")

    n = len(gens)
    tag = label + ("" if not exe else " +imports")
    print(f"{tag} re-scored offline ({args.repair}):")
    print(f"  pass@1 = {passed}/{n}  [{' '.join(detail)}]")
    print(f"  decomposition: compiles {built}/{n} · passes-given-compiles "
          f"{f'{passed}/{built}' if built else 'n/a'}")
    if exe:
        print(f"  repair: goimports changed {n_repaired} generation(s)")
    print(f"  vs saved verdicts: {len(flips)} changed  [{' '.join(flips) or 'none'}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
