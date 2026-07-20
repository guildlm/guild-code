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


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_bench.py <bench.jsonl>")
        return 2
    tasks = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
    ids = [t["id"] for t in tasks]
    dups = sorted({i for i in ids if ids.count(i) > 1})

    broken, degenerate, no_ref = [], [], []
    for t in tasks:
        test = t["metadata"]["tests"]
        ref = t.get("reference")
        if not ref:
            no_ref.append(t["id"])
        elif not runs_green(ref, test):
            broken.append(t["id"])
        if runs_green("package sandbox\n", test):
            degenerate.append(t["id"])

    print(f"tasks {len(tasks)}  unique ids {len(set(ids))}  duplicates {dups or 'none'}")
    print(f"reference FAILS its own test (BROKEN):   {len(broken)} {broken}")
    print(f"passes on EMPTY impl (DEGENERATE):       {len(degenerate)} {degenerate}")
    print(f"no reference field (unchecked solvable): {len(no_ref)} {no_ref}")

    bad = bool(dups or broken or degenerate)
    print("\n" + ("OK — every task is solvable and non-degenerate."
                  if not bad else "FAIL — see broken/degenerate/duplicate lists above."))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
