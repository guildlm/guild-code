#!/usr/bin/env python3
"""One command for every integrity gate in the crucible. Model-free, so it can run in CI.

The benchmarks in this directory produced conclusions that turned out to be harness
artefacts twice in one session: an unterminated ```go fence scored as invalid Go (in THREE
harnesses), and a keyword rule a canned checklist could game. Each fix arrived with its own
checker, and a checker nobody runs is not a gate. This runs all of them.

Every check here is deterministic and needs no model or GPU — only the Go toolchain and
goimports — which is exactly why it can gate CI, unlike the mutation suite in builder/
that needs generated artefacts.

    python verify_pipeline.py     # exit 0 = every gate green

Gates:
  1. selector/tag/fence/repair self-tests (mlx_test_bench --self-test)
  2. verify_bench itself FIRES on a bad bench (verify_bench --self-test) — the checker that
     gates every bench below is proven non-vacuous with planted broken/degenerate fixtures
  3. ONE fence implementation shared by all three harnesses — a re-copied extract_code is
     how the same bug reappears in a fourth
  4. benchmark data integrity (verify_bench on each bench)
  5. review scoring is still gameable under the recorded rule, and still NOT gameable
     under the strict one, and the strict one still credits genuine reviews

Deliberately NOT a gate here: check_contamination.py. It is model-free too, but it needs
the training corpora (--train), which are gitignored and 170MB+ — absent from any CI
checkout, so wiring it would fail for lack of data, not for real contamination. It stays a
local pre-flight; run it by hand when a bench or a training set changes.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(cmd, expect_zero=True):
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=900)
    ok = (p.returncode == 0) if expect_zero else (p.returncode != 0)
    return ok, p.stdout + p.stderr


def main() -> int:
    failures = []

    def gate(name, ok, detail=""):
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(name)

    ok, out = run([PY, "mlx_test_bench.py", "--self-test"])
    gate("self-tests (selector, tag, fence, import repair)", ok, out.strip()[-300:])

    # verify_bench is the gate on the benches below; this proves the gate itself FIRES.
    # It builds tiny fixtures the checker MUST flag (broken/degenerate/echo/duplicate) plus
    # clean controls it must pass — so a regression that no-ops a check goes red here rather
    # than letting the real-bench gates stay vacuously green.
    ok, out = run([PY, "verify_bench.py", "--self-test"])
    gate("verify_bench fires on bad benches (self-test)", ok, out.strip()[-300:])

    # A shared import is the only thing stopping a fourth copy of the fence bug: assert the
    # harnesses are literally running the same function object, not similar-looking code.
    try:
        sys.path.insert(0, HERE)
        import bench_compare
        import mlx_bench
        import mlx_test_bench
        same = (mlx_bench.extract_code is mlx_test_bench.extract_code
                and bench_compare.extract_code is mlx_test_bench.extract_code)
        gate("all three harnesses share ONE extract_code", same,
             "a harness has its own copy again — the fence bug can diverge")
    except Exception as e:  # noqa: BLE001
        gate("all three harnesses share ONE extract_code", False, f"{type(e).__name__}: {e}")

    for bench, expect_ok in (("go_dev_bench", True), ("go_edit_bench", True),
                             ("go_test_bench_hard", True), ("go_test_bench", False)):
        path = os.path.join("data", f"{bench}.jsonl")
        ok, out = run([PY, "verify_bench.py", path], expect_zero=expect_ok)
        # go_test_bench is EXPECTED to fail: it carries no witness/naive tests, so it cannot
        # be verified. Pinning that expectation means the day someone adds them, this gate
        # fails and tells us to flip the flag — rather than silently keeping a known-bad bench.
        label = f"verify_bench {bench}" + ("" if expect_ok else " (expected UNVERIFIABLE)")
        gate(label, ok, out.strip()[-300:])

    ok, out = run([PY, "probe_review_scoring.py"])
    if ok:
        gameable = "SHOTGUN  keyword        min-kw=1: scores 7/8" in out
        immune = "SHOTGUN  discriminative min-kw=1: scores 0/8" in out
        genuine = "positive control: 3/3" in out
        gate("review scoring: recorded rule still gameable (7/8)", gameable)
        gate("review scoring: strict rule not gameable (0/8)", immune)
        gate("review scoring: strict rule still credits genuine reviews (3/3)", genuine)
    else:
        gate("review scoring probe runs", False, out.strip()[-300:])

    print()
    if failures:
        print(f"FAIL — {len(failures)} gate(s): {failures}")
        return 1
    print("OK — every crucible integrity gate is green (model-free).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
