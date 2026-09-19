# -*- coding: utf-8 -*-
"""Why do self-written tests fail on the task's own REFERENCE solution? Classify each failure by
the Go toolchain's first error line, so 'validity 2/48' is a diagnosis and not a number.
    python selftest_autopsy.py data/router_selftests_30b.jsonl [data/router_selftests_7b.jsonl ...]
"""
import collections
import json
import os
import re
import subprocess
import sys
import tempfile

MODULE = "sandbox"
BENCH = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(os.path.dirname(__file__), "data", "go_dev_bench.jsonl"))}


def run(code, test):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(code)
        open(os.path.join(d, "impl_test.go"), "w").write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        try:
            p = subprocess.run(["go", "test", "./..."], cwd=d, capture_output=True, text=True, timeout=60, env=env)
        except subprocess.TimeoutExpired:
            return "TIMEOUT", ""
        return ("PASS" if p.returncode == 0 else "FAIL"), (p.stderr + p.stdout)


def classify(test, out):
    if not test.strip():
        return "empty"
    if "redeclared" in out or "redeclared in this block" in out:
        return "REDECLARES the function under test"
    if re.search(r"undefined: \w+", out):
        return "UNDEFINED symbol (guessed a name/signature the spec did not give): " + re.search(r"undefined: (\w+)", out).group(1)
    if "cannot use" in out or "too many arguments" in out or "not enough arguments" in out or "mismatched types" in out:
        return "SIGNATURE mismatch"
    if "package sandbox" not in test:
        return "WRONG package clause"
    if "func Test" not in test:
        return "NO Test func"
    if "--- FAIL" in out:
        return "compiled, ASSERTION failed on the reference (over-specified or wrong expectation)"
    if "imported and not used" in out or "missing import" in out or "undefined:" in out:
        return "IMPORT problem"
    return "OTHER: " + (out.strip().splitlines() or [""])[0][:100]


def main(paths):
    for p in paths:
        rows = [json.loads(l) for l in open(p)]
        counts = collections.Counter()
        examples = {}
        for r in rows:
            ref = BENCH[r["id"]]["reference"]
            status, out = run(ref, r["test"])
            key = "valid" if status == "PASS" else classify(r["test"], out)
            counts[key] += 1
            examples.setdefault(key, r["id"])
        print(f"== {p}  ({rows[0]['writer']})")
        for k, v in counts.most_common():
            print(f"  {v:>2}  {k}   e.g. {examples[k]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
