#!/usr/bin/env python3
"""Integrity gate for a go_*_bench.jsonl before its pass@1 numbers are trusted.

A fair scoring harness (bench_compare.py / mlx_bench.py) still reports garbage if the
BENCHMARK ITSELF is unsound. Two ways it can be, both caught here with the same
`go test` the harness uses (stdlib-only, offline):

  - BROKEN task: the task's own reference solution does NOT pass its hidden test.
    Then no model can pass it either — the task silently caps every score below 100%
    for the wrong reason, and a "specialist < base" gap could be pure task noise.
  - DEGENERATE task: the hidden test passes on an EMPTY impl (package sandbox with
    nothing in it). Then the test does not require the solution at all and every
    model scores it free — inflating pass@1 and hiding real capability differences.
    This is the teeth insight (a green test that defends nothing) applied to a bench.
  - ECHO-DEGENERATE task (EDIT benches only): the task carries a flawed `original`
    in its metadata, and that original already PASSES the hidden test. Then a model
    that echoes back the unchanged code it was handed in the prompt scores a pass —
    a stronger degeneracy than the empty-impl one, because for an EDIT task the
    trivial answer is the original it was given, not an empty file, and a test can
    exercise-nothing-new while still failing on empty.

Also checks the file parses and ids are unique. Needs the Go toolchain.

Usage:  verify_bench.py <bench.jsonl>
  exit 0 = every task is solvable (ref green) and non-degenerate (empty impl red);
  exit 1 = at least one broken or degenerate task (listed).
"""
import json
import os
import subprocess
import sys
import tempfile

MODULE = "sandbox"


def runs_green(code: str, test: str) -> bool:
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(code)
        open(os.path.join(d, "impl_test.go"), "w").write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        try:
            p = subprocess.run(
                ["go", "test", "./..."], cwd=d, capture_output=True, text=True,
                timeout=60, env=env,
            )
        except subprocess.TimeoutExpired:
            return False
        return p.returncode == 0


def check_test_bench(tasks):
    """Same two failure modes for a TEST-WRITING bench, where the artefact under test is
    the test rather than the implementation.

      BROKEN     — the task's own witness test does not pass on the correct impl AND fail
                   on the mutant, i.e. the planted bug is unreachable and no model can
                   score it.
      DEGENERATE — the mutant dies to the task's naive happy-path test, so any test that
                   merely runs scores the point. That is the flaw measured on the original
                   go_test_bench: 16/18 of its mutants are gross, which is why every arm
                   there reported caught-given-valid of 100%.

    Only checkable when the bench carries witness_test / naive_test (go_test_bench_hard
    does; the original does not, which is itself worth reporting).
    """
    broken, degenerate, unchecked = [], [], []
    for t in tasks:
        m = t["metadata"]
        witness, naive = m.get("witness_test"), m.get("naive_test")
        if not witness or not naive:
            unchecked.append(t["id"])
            continue
        if not (runs_green(m["correct"], witness) and not runs_green(m["mutant"], witness)):
            broken.append(t["id"])
        if not runs_green(m["mutant"], naive):
            degenerate.append(t["id"])
    return broken, degenerate, unchecked


def check_code_bench(tasks):
    """The BROKEN / DEGENERATE / ECHO-DEGENERATE failure modes for an impl-writing bench.

    Returns (broken, degenerate, echo_degenerate, no_ref) id lists, mirroring
    check_test_bench so the two branches read the same and can share a self-test.
    """
    broken, degenerate, echo_degenerate, no_ref = [], [], [], []
    for t in tasks:
        test = t["metadata"]["tests"]
        ref = t.get("reference")
        if not ref:
            no_ref.append(t["id"])
        elif not runs_green(ref, test):
            broken.append(t["id"])
        if runs_green("package sandbox\n", test):
            degenerate.append(t["id"])
        # EDIT-bench only: the flawed original the model is handed must FAIL, or a
        # verbatim echo of the prompt scores a pass. Skipped when absent (gen benches).
        original = t["metadata"].get("original")
        if original is not None and runs_green(original, test):
            echo_degenerate.append(t["id"])
    return broken, degenerate, echo_degenerate, no_ref


def _self_test() -> int:
    """Prove verify_bench actually FIRES on a bad bench — a checker nobody has seen catch
    anything is indistinguishable from a no-op (the teeth insight, turned on this file).

    Each fixture below is a task the checker MUST flag, plus a clean control it must pass.
    If a future edit silently defeats a check (an inverted condition, a dropped branch),
    the corresponding assert here goes red instead of the pipeline staying vacuously green.
    Model-free: only the Go toolchain, same as the real gate.
    """
    ADD_REF = "package sandbox\n\nfunc Add(a, b int) int { return a + b }\n"
    ADD_WRONG = "package sandbox\n\nfunc Add(a, b int) int { return a - b }\n"
    ADD_TEST = ('package sandbox\n\nimport "testing"\n\n'
                'func TestAdd(t *testing.T) { if Add(1, 2) != 3 { t.Fatal("bad") } }\n')
    # A test that references nothing in the impl: it passes even on an empty package.
    EMPTY_OK_TEST = 'package sandbox\n\nimport "testing"\n\nfunc TestNothing(t *testing.T) {}\n'

    def code_task(tid, ref, test, original=None):
        m = {"tests": test}
        if original is not None:
            m["original"] = original
        return {"id": tid, "reference": ref, "metadata": m}

    fails = []

    def want(label, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            fails.append(label)

    # --- impl-writing branch (check_code_bench) ---
    b, d, e, nr = check_code_bench([code_task("clean", ADD_REF, ADD_TEST)])
    want("clean impl task: no flags", not (b or d or e or nr))

    b, d, e, nr = check_code_bench([code_task("broken", ADD_WRONG, ADD_TEST)])
    want("wrong reference -> BROKEN", b == ["broken"] and not d)

    b, d, e, nr = check_code_bench([code_task("degen", ADD_REF, EMPTY_OK_TEST)])
    want("empty impl passes -> DEGENERATE", d == ["degen"])

    b, d, e, nr = check_code_bench([code_task("echo", ADD_REF, ADD_TEST, original=ADD_REF)])
    want("original already passes -> ECHO-DEGENERATE", e == ["echo"])

    b, d, e, nr = check_code_bench([code_task("noref", None, ADD_TEST)])
    want("missing reference -> no_ref", nr == ["noref"])

    # --- test-writing branch (check_test_bench) ---
    # correct impl the test should pass on; mutant a good witness catches but a naive misses.
    CORRECT = "package sandbox\n\nfunc Abs(x int) int { if x < 0 { return -x }; return x }\n"
    MUTANT = "package sandbox\n\nfunc Abs(x int) int { return x }\n"  # wrong for negatives
    WITNESS = ('package sandbox\n\nimport "testing"\n\n'
               'func TestAbs(t *testing.T) { if Abs(-3) != 3 { t.Fatal("neg") } }\n')
    NAIVE = ('package sandbox\n\nimport "testing"\n\n'
             'func TestAbs(t *testing.T) { if Abs(3) != 3 { t.Fatal("pos") } }\n')

    def test_task(tid, correct, mutant, witness, naive):
        return {"id": tid, "metadata": {"correct": correct, "mutant": mutant,
                                        "witness_test": witness, "naive_test": naive}}

    # clean: witness catches the mutant, and the mutant survives the naive test (so it is
    # a real, non-shallow bug). Neither flag should fire.
    b, d, u = check_test_bench([test_task("clean", CORRECT, MUTANT, WITNESS, NAIVE)])
    want("clean test task: no flags", not (b or d or u))

    # witness that also passes on the mutant does not isolate the bug -> BROKEN
    b, d, u = check_test_bench([test_task("nowit", CORRECT, MUTANT, NAIVE, NAIVE)])
    want("witness misses the mutant -> BROKEN", b == ["nowit"] and not d)

    # a mutant the naive (shallow) test already kills is too easy -> DEGENERATE
    b, d, u = check_test_bench([test_task("shallow", CORRECT, MUTANT, WITNESS, WITNESS)])
    want("mutant dies to the naive test -> DEGENERATE", d == ["shallow"] and not b)

    b, d, u = check_test_bench([test_task("unchk", CORRECT, MUTANT, None, None)])
    want("no witness/naive fields -> unchecked", u == ["unchk"])

    print(f"\nverify_bench self-test: {len(fails)} failure(s)" + (f" {fails}" if fails else " — all checks fire"))
    return 1 if fails else 0


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return _self_test()
    if len(sys.argv) != 2:
        print("usage: verify_bench.py <bench.jsonl> | --self-test")
        return 2
    tasks = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
    ids = [t["id"] for t in tasks]
    dups = sorted({i for i in ids if ids.count(i) > 1})

    if tasks and "tests" not in tasks[0]["metadata"]:
        broken, degenerate, unchecked = check_test_bench(tasks)
        print(f"tasks {len(tasks)}  unique ids {len(set(ids))}  duplicates {dups or 'none'}")
        print(f"[test-writing bench] witness does not isolate the bug (BROKEN): "
              f"{len(broken)} {broken}")
        print(f"[test-writing bench] mutant dies to a naive test (DEGENERATE): "
              f"{len(degenerate)} {degenerate}")
        print(f"no witness/naive fields (unchecked): {len(unchecked)} {unchecked}")
        bad = bool(dups or broken or degenerate)
        if unchecked and len(unchecked) == len(tasks):
            # A gate that verified NOTHING must never print OK. This branch fired on the
            # original go_test_bench, which carries no witness/naive tests — reporting it
            # green would be the same vacuous pass this whole gate exists to catch.
            print("\nUNVERIFIABLE — no task carries witness/naive tests, so nothing was "
                  "checked. Build a hard bench (build_go_test_bench_hard.py) to gate this.")
            return 1
        print("\n" + ("OK — every mutant is reachable and survives a shallow test."
                      if not bad else "FAIL — see lists above."))
        return 1 if bad else 0

    broken, degenerate, echo_degenerate, no_ref = check_code_bench(tasks)

    print(f"tasks {len(tasks)}  unique ids {len(set(ids))}  duplicates {dups or 'none'}")
    print(f"reference FAILS its own test (BROKEN):   {len(broken)} {broken}")
    print(f"passes on EMPTY impl (DEGENERATE):       {len(degenerate)} {degenerate}")
    print(f"flawed original PASSES (ECHO-DEGENERATE):{len(echo_degenerate)} {echo_degenerate}")
    print(f"no reference field (unchecked solvable): {len(no_ref)} {no_ref}")

    bad = bool(dups or broken or degenerate or echo_degenerate)
    if no_ref and len(no_ref) == len(tasks):
        # Same rule as the test-writing branch: with no reference anywhere, solvability was
        # never checked, so "OK" would be a green that verified nothing.
        print("\nUNVERIFIABLE — no task carries a reference solution, so solvability was "
              "never checked (the degenerate check still ran).")
        return 1
    print("\n" + ("OK — every task is solvable and non-degenerate."
                  if not bad else "FAIL — see broken/degenerate/duplicate lists above."))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
