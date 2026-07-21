# -*- coding: utf-8 -*-
"""Build go_test_bench_hard.jsonl — the same 18 tasks with mutants that have TEETH.

WHY. Measured across four arms (base/specialist x greedy/+goimports), every valid test
in go_test_bench caught its mutant: caught-given-valid was 18/18 of the valid ones, every
time. A benchmark whose every planted bug dies to any test that merely compiles is not
measuring test quality — it is measuring whether the model emits valid Go. The original
mutants are gross (whole function replaced by `return a`), so a single happy-path
assertion kills them.

This is the project's own teeth lens turned on its benchmark: a green suite is not a
defended contract, and a caught mutant is not a test with teeth.

WHAT. Each task gets a HARD mutant: a bug that only manifests on an EDGE CASE (empty
input, single element, boundary value, negative, non-ASCII, nil-vs-empty, integer
division). A happy-path test still passes against it; only a test that probes the edge
catches it. So the hard bench separates thorough tests from lucky ones.

EVERY hard mutant is validated by three checks before it is written out — no mutant is
trusted because it looks right:
  1. WITNESS test passes on correct, FAILS on hard mutant  -> the mutant is a real bug
     and is reachable (a mutant nothing can catch is worse than no mutant).
  2. NAIVE happy-path test passes on correct AND on the hard mutant -> the mutant really
     is hard; it survives the shallow test the original could not.
  3. NAIVE test FAILS on the ORIGINAL mutant -> quantifies the claim that the original
     bench is gross, rather than asserting it.
Check 3 is the one that turns "these mutants look easy" into evidence.
"""
import json
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "data", "go_test_bench.jsonl")
OUT = os.path.join(HERE, "data", "go_test_bench_hard.jsonl")

T = "func Test%s(t *testing.T) {\n%s\n}\n"


def _test(body: str, imports: str = '"testing"') -> str:
    return f"package sandbox\n\nimport (\n\t{imports}\n)\n\n" + T % ("X", body)


# id -> (hard mutant source, witness test body, naive happy-path test body)
HARD = {
    "add": (
        "package sandbox\n\nfunc Add(a, b int) int {\n\tif a < 0 && b < 0 {\n\t\treturn a + b + 1\n\t}\n\treturn a + b\n}\n",
        '\tif Add(-2, -3) != -5 {\n\t\tt.Errorf("Add(-2,-3) = %d", Add(-2, -3))\n\t}',
        '\tif Add(1, 2) != 3 {\n\t\tt.Error("Add(1,2)")\n\t}',
    ),
    "max": (
        "package sandbox\n\nfunc Max(a, b int) int {\n\tif a > b {\n\t\tif a < 0 {\n\t\t\treturn b\n\t\t}\n\t\treturn a\n\t}\n\treturn b\n}\n",
        '\tif Max(-1, -5) != -1 {\n\t\tt.Errorf("Max(-1,-5) = %d", Max(-1, -5))\n\t}',
        '\tif Max(3, 5) != 5 || Max(5, 3) != 5 {\n\t\tt.Error("Max happy path")\n\t}',
    ),
    "is_even": (
        "package sandbox\n\nfunc IsEven(n int) bool {\n\tif n < 0 {\n\t\treturn true\n\t}\n\treturn n%2 == 0\n}\n",
        '\tif IsEven(-3) {\n\t\tt.Error("IsEven(-3) should be false")\n\t}',
        '\tif !IsEven(2) || IsEven(3) {\n\t\tt.Error("IsEven happy path")\n\t}',
    ),
    "reverse_runes": (
        "package sandbox\n\nfunc Reverse(s string) string {\n\tr := []rune(s)\n\tif len(r) < 2 {\n\t\treturn s + \" \"\n\t}\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tr[i], r[j] = r[j], r[i]\n\t}\n\treturn string(r)\n}\n",
        '\tif Reverse("") != "" {\n\t\tt.Errorf("Reverse(\\"\\") = %q", Reverse(""))\n\t}',
        '\tif Reverse("hello") != "olleh" {\n\t\tt.Error("Reverse happy path")\n\t}',
    ),
    "abs": (
        "package sandbox\n\nfunc Abs(n int) int {\n\tif n < -1 {\n\t\treturn -n\n\t}\n\treturn n\n}\n",
        '\tif Abs(-1) != 1 {\n\t\tt.Errorf("Abs(-1) = %d", Abs(-1))\n\t}',
        '\tif Abs(-5) != 5 || Abs(5) != 5 || Abs(0) != 0 {\n\t\tt.Error("Abs happy path")\n\t}',
    ),
    "clamp": (
        "package sandbox\n\nfunc Clamp(v, lo, hi int) int {\n\tif v < lo {\n\t\treturn lo\n\t}\n\tif v > hi+1 {\n\t\treturn hi\n\t}\n\treturn v\n}\n",
        '\tif Clamp(11, 0, 10) != 10 {\n\t\tt.Errorf("Clamp(11,0,10) = %d", Clamp(11, 0, 10))\n\t}',
        '\tif Clamp(5, 0, 10) != 5 || Clamp(-3, 0, 10) != 0 || Clamp(50, 0, 10) != 10 {\n\t\tt.Error("Clamp happy path")\n\t}',
    ),
    "contains": (
        "package sandbox\n\nfunc Contains(s []int, x int) bool {\n\tfor i := 0; i < len(s)-1; i++ {\n\t\tif s[i] == x {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n",
        '\tif !Contains([]int{1, 2, 3}, 3) {\n\t\tt.Error("Contains must find the LAST element")\n\t}',
        '\tif !Contains([]int{1, 2, 3}, 2) || Contains([]int{1, 2, 3}, 9) {\n\t\tt.Error("Contains happy path")\n\t}',
    ),
    "count_vowels": (
        "package sandbox\n\nimport \"strings\"\n\nfunc CountVowels(s string) int {\n\tn := 0\n\tfor _, c := range strings.ToLower(s) {\n\t\tswitch c {\n\t\tcase 'a', 'e', 'i', 'o':\n\t\t\tn++\n\t\t}\n\t}\n\treturn n\n}\n",
        '\tif CountVowels("under") != 2 {\n\t\tt.Errorf("CountVowels(\\"under\\") = %d", CountVowels("under"))\n\t}',
        '\tif CountVowels("hello") != 2 {\n\t\tt.Error("CountVowels happy path")\n\t}',
    ),
    "sum": (
        "package sandbox\n\nfunc Sum(xs []int) int {\n\tif len(xs) == 1 {\n\t\treturn 0\n\t}\n\ts := 0\n\tfor _, x := range xs {\n\t\ts += x\n\t}\n\treturn s\n}\n",
        '\tif Sum([]int{7}) != 7 {\n\t\tt.Errorf("Sum([7]) = %d", Sum([]int{7}))\n\t}',
        '\tif Sum([]int{1, 2, 3}) != 6 || Sum(nil) != 0 {\n\t\tt.Error("Sum happy path")\n\t}',
    ),
    "gcd": (
        "package sandbox\n\nfunc GCD(a, b int) int {\n\tif a == 0 {\n\t\treturn 0\n\t}\n\tfor b != 0 {\n\t\ta, b = b, a%b\n\t}\n\treturn a\n}\n",
        '\tif GCD(0, 5) != 5 {\n\t\tt.Errorf("GCD(0,5) = %d", GCD(0, 5))\n\t}',
        '\tif GCD(12, 8) != 4 || GCD(9, 3) != 3 {\n\t\tt.Error("GCD happy path")\n\t}',
    ),
    "last": (
        "package sandbox\n\nfunc Last(xs []int) (int, bool) {\n\tif len(xs) == 0 {\n\t\treturn 0, false\n\t}\n\tif len(xs) == 1 {\n\t\treturn 0, true\n\t}\n\treturn xs[len(xs)-1], true\n}\n",
        '\tif v, ok := Last([]int{7}); v != 7 || !ok {\n\t\tt.Errorf("Last([7]) = %d,%v", v, ok)\n\t}',
        '\tif v, ok := Last([]int{1, 2, 3}); v != 3 || !ok {\n\t\tt.Error("Last happy path")\n\t}\n\tif _, ok := Last(nil); ok {\n\t\tt.Error("Last(nil)")\n\t}',
    ),
    "is_sorted": (
        "package sandbox\n\nfunc IsSorted(xs []int) bool {\n\tfor i := 1; i < len(xs)-1; i++ {\n\t\tif xs[i] < xs[i-1] {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n",
        '\tif IsSorted([]int{1, 2, 0}) {\n\t\tt.Error("IsSorted must see a violation at the END")\n\t}',
        '\tif !IsSorted([]int{1, 2, 3}) || IsSorted([]int{3, 1, 2}) {\n\t\tt.Error("IsSorted happy path")\n\t}',
    ),
    "repeat": (
        "package sandbox\n\nimport \"strings\"\n\nfunc Repeat(s string, n int) string {\n\tif n <= 1 {\n\t\treturn s\n\t}\n\treturn strings.Repeat(s, n)\n}\n",
        '\tif Repeat("a", 0) != "" {\n\t\tt.Errorf("Repeat(a,0) = %q", Repeat("a", 0))\n\t}',
        '\tif Repeat("ab", 3) != "ababab" {\n\t\tt.Error("Repeat happy path")\n\t}',
    ),
    "is_prime": (
        "package sandbox\n\nfunc IsPrime(n int) bool {\n\tif n < 1 {\n\t\treturn false\n\t}\n\tfor i := 2; i*i <= n; i++ {\n\t\tif n%i == 0 {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n",
        '\tif IsPrime(1) {\n\t\tt.Error("1 is not prime")\n\t}',
        '\tif !IsPrime(2) || IsPrime(4) || !IsPrime(97) {\n\t\tt.Error("IsPrime happy path")\n\t}',
    ),
    "dedup_order": (
        "package sandbox\n\nfunc Dedup(xs []int) []int {\n\tseen := map[int]bool{}\n\tvar out []int\n\tfor _, x := range xs {\n\t\tif !seen[x] {\n\t\t\tseen[x] = true\n\t\t\tout = append(out, x)\n\t\t}\n\t}\n\treturn out\n}\n",
        '\tgot := Dedup([]int{})\n\tif got == nil {\n\t\tt.Error("Dedup([]) must return an empty slice, not nil")\n\t}',
        '\tgot := Dedup([]int{1, 2, 1, 3})\n\tif !reflect.DeepEqual(got, []int{1, 2, 3}) {\n\t\tt.Errorf("Dedup = %v", got)\n\t}',
    ),
    "median": (
        "package sandbox\n\nimport \"sort\"\n\nfunc Median(xs []int) float64 {\n\tc := append([]int(nil), xs...)\n\tsort.Ints(c)\n\tn := len(c)\n\tif n%2 == 1 {\n\t\treturn float64(c[n/2])\n\t}\n\treturn float64((c[n/2-1] + c[n/2]) / 2)\n}\n",
        '\tif Median([]int{1, 2}) != 1.5 {\n\t\tt.Errorf("Median([1,2]) = %v", Median([]int{1, 2}))\n\t}',
        '\tif Median([]int{3, 1, 2}) != 2 {\n\t\tt.Error("Median happy path")\n\t}',
    ),
    "title_each": (
        "package sandbox\n\nimport \"strings\"\n\nfunc Title(s string) string {\n\tw := strings.Fields(s)\n\tfor i, x := range w {\n\t\tr := []rune(x)\n\t\tif r[0] >= 'a' && r[0] <= 'z' {\n\t\t\tr[0] = r[0] - 32\n\t\t}\n\t\tw[i] = string(r)\n\t}\n\treturn strings.Join(w, \" \")\n}\n",
        '\tif Title("ñino") != "Ñino" {\n\t\tt.Errorf("Title(ñino) = %q", Title("ñino"))\n\t}',
        '\tif Title("hello world") != "Hello World" {\n\t\tt.Error("Title happy path")\n\t}',
    ),
    "clamp_pair": (
        "package sandbox\n\nfunc Clamp(v, lo, hi int) int {\n\tif v < lo-1 {\n\t\treturn lo\n\t}\n\tif v > hi {\n\t\treturn hi\n\t}\n\treturn v\n}\n",
        '\tif Clamp(-1, 0, 10) != 0 {\n\t\tt.Errorf("Clamp(-1,0,10) = %d", Clamp(-1, 0, 10))\n\t}',
        '\tif Clamp(5, 0, 10) != 5 || Clamp(-9, 0, 10) != 0 || Clamp(50, 0, 10) != 10 {\n\t\tt.Error("Clamp happy path")\n\t}',
    ),
}

NEEDS_REFLECT = {"dedup_order"}


def go_test(impl: str, test: str) -> bool:
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write("module sandbox\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(impl)
        open(os.path.join(d, "impl_test.go"), "w").write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        p = subprocess.run(["go", "test", "./..."], cwd=d, capture_output=True, text=True,
                           timeout=90, env=env)
        return p.returncode == 0


def main() -> int:
    tasks = [json.loads(l) for l in open(BENCH)]
    missing = [t["id"] for t in tasks if t["id"] not in HARD]
    if missing:
        raise SystemExit(f"no hard mutant authored for: {missing}")

    rows, failures = [], []
    for t in tasks:
        tid = t["id"]
        hard, witness_body, naive_body = HARD[tid]
        imports = '"testing"\n\t"reflect"' if tid in NEEDS_REFLECT else '"testing"'
        witness = _test(witness_body, imports='"testing"')
        naive = _test(naive_body, imports=imports)
        correct, gross = t["metadata"]["correct"], t["metadata"]["mutant"]

        checks = {
            # 1. the hard mutant is a REAL, reachable bug
            "witness passes on correct": go_test(correct, witness),
            "witness FAILS on hard mutant": not go_test(hard, witness),
            # 2. the hard mutant genuinely survives a shallow test
            "naive passes on correct": go_test(correct, naive),
            "naive SURVIVES hard mutant": go_test(hard, naive),
        }
        bad = [k for k, v in checks.items() if not v]
        # 3. CLASSIFY the original mutant (not a pass/fail): does the same happy-path test
        # kill it? Blanket-failing here would have let me assert "all the originals are
        # gross" when two of them are not, so the check reports instead of judging.
        original_gross = not go_test(gross, naive) if not bad else None
        status = "OK  " if not bad else "FAIL"
        note = "" if bad else ("original=GROSS" if original_gross else "original=already-subtle")
        print(f"{status} {tid:14} {note}" + ("" if not bad else "-> " + "; ".join(bad)))
        if bad:
            failures.append(tid)
            continue

        row = dict(t)
        row["metadata"] = dict(t["metadata"])
        row["metadata"]["mutant"] = hard
        row["metadata"]["gross_mutant"] = gross
        row["metadata"]["original_gross"] = original_gross
        row["metadata"]["witness_test"] = witness
        row["metadata"]["naive_test"] = naive
        rows.append(row)

    if failures:
        print(f"\n{len(failures)} task(s) failed validation; NOT writing {OUT}")
        return 1
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    gross_n = sum(1 for r in rows if r["metadata"]["original_gross"])
    subtle = [r["id"] for r in rows if not r["metadata"]["original_gross"]]
    print(f"\nall {len(rows)} hard mutants validated (real bug, reachable, survives a naive test)")
    print(f"original bench: {gross_n}/{len(rows)} mutants die to a single happy-path assertion"
          f" — already-subtle: {subtle or 'none'}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
