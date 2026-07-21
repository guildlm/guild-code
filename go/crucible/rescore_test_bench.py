# -*- coding: utf-8 -*-
"""Re-score saved go-test generations against a different bench — no model, no GPU, $0.

Every scoring question so far has cost a full model re-run, because no bench persisted
what the model wrote. mlx_test_bench --save-generations fixes that; this is the consumer:
point it at a saved run and a bench file, and it recomputes the score with go test alone.

The motivating use: the original mutants are gross (16/18 die to one happy-path
assertion), so re-scoring the SAME generations against go_test_bench_hard.jsonl asks
"do these tests have TEETH?" without generating a single new token.

    python rescore_test_bench.py --generations base_greedy.jsonl \
        --bench data/go_test_bench_hard.jsonl

Scoring is imported from mlx_test_bench rather than reimplemented, so a re-score and a
live run cannot silently drift apart. (Importing it is cheap: mlx_lm is imported inside
main(), not at module scope.)
"""
import argparse
import json
import os

from mlx_test_bench import _go_test, _has_valid, _verdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", required=True, help="JSONL from --save-generations")
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_test_bench_hard.jsonl"))
    ap.add_argument("--select", choices=("oracle", "valid"), default="valid")
    args = ap.parse_args()

    bench = {}
    for line in open(args.bench):
        t = json.loads(line)
        bench[t["id"]] = t["metadata"]
    gens = [json.loads(l) for l in open(args.generations)]
    unknown = [g["id"] for g in gens if g["id"] not in bench]
    if unknown:
        # Scoring a subset silently would report a smaller denominator as if it were the
        # whole bench, which reads as a different result rather than a mismatch.
        raise SystemExit(f"generations contain ids absent from the bench: {unknown}")

    label = gens[0].get("label", "?") if gens else "?"
    tag = gens[0].get("tag", "?") if gens else "?"
    passed, valid_n, flips, detail = 0, 0, [], []
    for g in gens:
        meta = bench[g["id"]]
        cands = []
        for c in g["candidates"]:
            ok_correct = _go_test(meta["correct"], c["code"])
            cands.append((ok_correct, ok_correct and not _go_test(meta["mutant"], c["code"])))
        ok = _verdict(cands, args.select)
        has_valid = _has_valid(cands)
        passed += ok
        valid_n += has_valid
        detail.append(f"{'+' if ok else ('v' if has_valid else '-')}{g['id']}")
        if ok != g.get("verdict"):
            flips.append(f"{g['id']}:{'+' if g.get('verdict') else '-'}->{'+' if ok else '-'}")

    n = len(gens)
    rate = f"{passed}/{valid_n}" if valid_n else "n/a"
    print(f"{label} [{tag}] re-scored on {os.path.basename(args.bench)} ({args.select}):")
    print(f"  bug-catch = {passed}/{n}  [{' '.join(detail)}]")
    print(f"  decomposition: valid-test {valid_n}/{n} · caught-given-valid {rate}")
    print(f"  vs original scoring: {len(flips)} task(s) changed  [{' '.join(flips) or 'none'}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
