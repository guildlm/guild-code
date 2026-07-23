# -*- coding: utf-8 -*-
"""Measure how gameable go_review_bench's keyword scoring is. Model-free, deterministic.

The audit recorded a SUSPICION — generic keywords (loop / once / leak / shared) that "a
rambling review could hit by chance" — but never measured it, so the weakness stayed an
opinion. This scores two canned reviews that identify NO specific defect:

  VAGUE   — a plausible non-answer of the kind a model produces when it has nothing.
            Must score 0/8. Anything above 0 means the bench credits saying nothing.
  SHOTGUN — a generic Go-pitfalls checklist, naming common failure modes without ever
            saying which one applies here. This is the CEILING of gaming the rule: an
            upper bound on what a review with zero comprehension can score.

Same shape as the two other integrity gates in this directory: verify_bench.py checks an
EMPTY implementation scores 0, and build_go_test_bench_hard.py checks a NAIVE test still
passes. A benchmark should be probed with something known to be worthless.

The probes are written to be plausible review prose, NOT reverse-engineered from the
keyword lists — the point is to estimate accidental hits, and tuning the text against the
answer key would measure my aim instead of the bench.
"""
import json
import os

from mlx_review_bench import hits, scores

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "data", "go_review_bench.jsonl")

VAGUE = """
This code could be improved. The implementation looks mostly reasonable, but I would add
error handling around the operations that can fail, and cover it with unit tests. Some of
the naming could be clearer, and a short doc comment on the exported function would help
future readers. Consider validating the inputs and handling edge cases explicitly.
"""

SHOTGUN = """
A few things to check in Go code like this. Make sure any map is initialized with make
before you write to it. Watch out for the loop variable capture problem when a closure is
started inside a loop, since every closure can end up sharing the same variable. A defer
inside a loop does not run until the function returns, so file descriptors can leak and
accumulate. Slices share a backing array, so appending can overwrite aliased data when the
capacity allows. Concurrent access needs a mutex or another way to synchronise, otherwise
you get a data race. A method on a value receiver copies the struct, which is wrong when
it holds a mutex. And a channel should only be closed once, by its owner, or it will panic
on a second close. Errors should be wrapped with %w so callers can use errors.Is.
"""


# POSITIVE CONTROLS. A rule that scores every review 0 would pass the probes above just as
# well as a good one, so the stricter rule has to be shown to still credit a review that
# genuinely pinpoints the defect. These name one defect each, in ordinary review prose.
GENUINE = {
    "double_close": """
        The channel is closed twice — the producer closes it when the loop ends and the
        caller closes it again afterwards, which panics on the second close. It should be
        closed exactly once, by the single owner of the channel.
    """,
    "nil_map_write": """
        Writing to a nil map panics at runtime. The map is declared but never initialized,
        so it has to be created with make(map[...]...) before the first write, or built
        lazily on first use.
    """,
    "loopvar_capture": """
        Every goroutine closes over the same loop variable rather than its own copy, so
        they all observe whichever value the closure sees last. This is the classic loop
        variable capture bug before Go 1.22; pass the value in as a parameter.
    """,
}


def main() -> int:
    tasks = [json.loads(l) for l in open(BENCH)]
    bench = {t["id"]: t["metadata"]["keywords"] for t in tasks}
    print(f"go_review_bench: {len(tasks)} tasks · probing the scoring rules with reviews that "
          f"identify NOTHING\n")
    for name, text in (("VAGUE", VAGUE), ("SHOTGUN", SHOTGUN)):
        for rule in ("keyword", "discriminative"):
            for min_kw in (1, 2):
                passed, detail = 0, []
                for t in tasks:
                    if scores(text, t["id"], bench, rule, min_kw):
                        passed += 1
                        detail.append(f"{t['id']}({'|'.join(hits(text, bench[t['id']]))})")
                print(f"{name:8} {rule:14} min-kw={min_kw}: scores {passed}/{len(tasks)}"
                      + (f"  [{' '.join(detail)}]" if detail else ""))
        print()

    good = 0
    for tid, review in GENUINE.items():
        ok = scores(review, tid, bench, "discriminative", 1)
        good += ok
        print(f"GENUINE  discriminative {tid:20}: {'SCORES' if ok else 'MISSED (false negative!)'}"
              f"  own={len(hits(review, bench[tid]))} keywords")
    print(f"positive control: {good}/{len(GENUINE)} genuine reviews still score under the "
          f"stricter rule\n")

    # SOLVABILITY — the verify_bench analogue for a review bench. verify_bench checks the
    # reference solution passes its own test; here the exemplary correct REVIEW (the task's
    # `reference`) must pass the recorded scoring rule. If the gold answer cannot score its
    # own task, the task is unsound and no model could pass it either — a "specialist < base"
    # gap on it would be pure task noise. Gated in verify_pipeline.
    solvable, unsound = 0, []
    for t in tasks:
        ref = t.get("reference") or ""
        if scores(ref, t["id"], bench, "keyword", 1):
            solvable += 1
        else:
            unsound.append(t["id"])
    print(f"gold references pass recorded rule (keyword min-kw=1): {solvable}/{len(tasks)}"
          + (f"  UNSOUND: {unsound}" if unsound else ""))
    # For the record, not gated: under the strict discriminative rule a concise gold review
    # can still miss (nil_map_write names one keyword, not a strict argmax over every other
    # task) — which is exactly why the recorded rule stays the default.
    disc = sum(bool(scores(t.get("reference") or "", t["id"], bench, "discriminative", 1))
               for t in tasks)
    print(f"  (for the record, gold references under discriminative: {disc}/{len(tasks)})\n")

    # An echoed keyword is free: the review can copy it out of the prompt without
    # understanding anything.
    echo = [(t["id"], [k for k in t["metadata"]["keywords"] if k.lower() in t["prompt"].lower()])
            for t in tasks]
    echo = [(i, k) for i, k in echo if k]
    print(f"echo-degenerate tasks (keyword present in the prompt itself): {len(echo)}/{len(tasks)}"
          + (f"  {echo}" if echo else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
