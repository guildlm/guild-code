# -*- coding: utf-8 -*-
"""Re-score saved reviews under any scoring rule — no model, no GPU, $0.

Companion to rescore_test_bench.py. The reviews themselves are the expensive part; the
rule applied to them is a one-line decision that was previously locked behind a full model
run. With --save-generations on mlx_review_bench, comparing the original keyword rule
against --score discriminative costs nothing.

    python rescore_review_bench.py --generations r_base.jsonl

Prints every rule side by side, so the question "how much of the recorded score survives a
rule that a generic checklist cannot game?" is answered in one shot. Scoring is imported
from mlx_review_bench, so a re-score and a live run cannot drift apart.
"""
import argparse
import json
import os

from mlx_review_bench import hits, scores

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", required=True, help="JSONL from --save-generations")
    ap.add_argument("--bench", default=os.path.join(HERE, "data", "go_review_bench.jsonl"))
    args = ap.parse_args()

    bench = {}
    for line in open(args.bench):
        t = json.loads(line)
        bench[t["id"]] = t["metadata"]["keywords"]
    gens = [json.loads(l) for l in open(args.generations)]
    unknown = [g["id"] for g in gens if g["id"] not in bench]
    if unknown:
        raise SystemExit(f"generations contain ids absent from the bench: {unknown}")

    label = gens[0].get("label", "?") if gens else "?"
    print(f"{label} re-scored on {os.path.basename(args.bench)} ({len(gens)} reviews):")
    for rule in ("keyword", "discriminative"):
        for min_kw in (1, 2):
            passed, detail = 0, []
            for g in gens:
                ok = scores(g["review"], g["id"], bench, rule, min_kw)
                passed += ok
                detail.append(f"{'+' if ok else '-'}{g['id']}")
            print(f"  {rule:14} min-kw={min_kw}: {passed}/{len(gens)}  [{' '.join(detail)}]")
    # How many keywords each review actually matched — a review scraping by on one generic
    # keyword is a different result from one that names the defect three ways.
    counts = sorted((len(hits(g["review"], bench[g["id"]])), g["id"]) for g in gens)
    print("  own-keyword hits per task: " + ", ".join(f"{i}={n}" for n, i in counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
