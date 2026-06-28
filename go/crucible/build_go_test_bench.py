# -*- coding: utf-8 -*-
"""Build (and self-verify) the go-TEST benchmark via mutation testing.

go_dev_bench measures generation and go_edit_bench measures editing. This one
objectively measures the go-test specialist's real job — writing tests that
catch bugs. Each task gives the model a function and asks for a test; the test is
scored by MUTATION testing:
  - it must PASS against the correct implementation (the test is valid), AND
  - it must FAIL against a planted buggy mutant (the test actually discriminates).
A test that does both genuinely tests the behaviour; one that trivially passes
everything does not. This is far stronger than judging test text by eye.

Every reference test here is self-verified to pass-on-correct AND fail-on-mutant
with the real Go toolchain, so the benchmark is sound before scoring a model.

Usage:
    python build_go_test_bench.py            # verify + write data/go_test_bench.jsonl
    python build_go_test_bench.py --no-write
"""
import json
import os
import subprocess
import sys
import tempfile

MODULE = "sandbox"


def _go_test(impl: str, test: str) -> bool:
    """True if `go test` passes for impl + test."""
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(impl)
        open(os.path.join(d, "impl_test.go"), "w").write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        try:
            p = subprocess.run(
                ["go", "test", "./..."], cwd=d, capture_output=True, text=True, timeout=60, env=env
            )
        except subprocess.TimeoutExpired:
            return False
        return p.returncode == 0


def discriminates(correct: str, mutant: str, test: str) -> bool:
    """A good test passes on the correct impl and fails on the buggy mutant."""
    return _go_test(correct, test) and not _go_test(mutant, test)


# (id, prompt, correct_impl, buggy_mutant, reference_test)
TASKS = [
    (
        "add",
        "Write a Go test (package sandbox) for Add(a, b int) int, which returns a+b.",
        "package sandbox\n\nfunc Add(a, b int) int { return a + b }\n",
        "package sandbox\n\nfunc Add(a, b int) int { return a - b }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestAdd(t *testing.T) {\n\tif Add(2, 3) != 5 {\n\t\tt.Fatal("2+3 should be 5")\n\t}\n\tif Add(0, 0) != 0 {\n\t\tt.Fatal("0+0 should be 0")\n\t}\n}\n',
    ),
    (
        "max",
        "Write a Go test (package sandbox) for Max(a, b int) int, which returns the larger of a and b.",
        "package sandbox\n\nfunc Max(a, b int) int {\n\tif a > b {\n\t\treturn a\n\t}\n\treturn b\n}\n",
        "package sandbox\n\nfunc Max(a, b int) int { return a }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestMax(t *testing.T) {\n\tif Max(1, 2) != 2 {\n\t\tt.Fatal("Max(1,2) should be 2")\n\t}\n\tif Max(5, 3) != 5 {\n\t\tt.Fatal("Max(5,3) should be 5")\n\t}\n}\n',
    ),
    (
        "is_even",
        "Write a Go test (package sandbox) for IsEven(n int) bool, true when n is even.",
        "package sandbox\n\nfunc IsEven(n int) bool { return n%2 == 0 }\n",
        "package sandbox\n\nfunc IsEven(n int) bool { return n%2 == 1 }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestIsEven(t *testing.T) {\n\tif !IsEven(4) {\n\t\tt.Fatal("4 is even")\n\t}\n\tif IsEven(3) {\n\t\tt.Fatal("3 is odd")\n\t}\n}\n',
    ),
    (
        "reverse_runes",
        "Write a Go test (package sandbox) for Reverse(s string) string, which reverses s by runes (Unicode-safe).",
        "package sandbox\n\nfunc Reverse(s string) string {\n\tr := []rune(s)\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tr[i], r[j] = r[j], r[i]\n\t}\n\treturn string(r)\n}\n",
        "package sandbox\n\nfunc Reverse(s string) string {\n\tb := []byte(s)\n\tfor i, j := 0, len(b)-1; i < j; i, j = i+1, j-1 {\n\t\tb[i], b[j] = b[j], b[i]\n\t}\n\treturn string(b)\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestReverse(t *testing.T) {\n\tif Reverse("abc") != "cba" {\n\t\tt.Fatal("ascii")\n\t}\n\tif Reverse("世界") != "界世" {\n\t\tt.Fatal("unicode must reverse by rune")\n\t}\n}\n',
    ),
    (
        "abs",
        "Write a Go test (package sandbox) for Abs(n int) int, the absolute value of n.",
        "package sandbox\n\nfunc Abs(n int) int {\n\tif n < 0 {\n\t\treturn -n\n\t}\n\treturn n\n}\n",
        "package sandbox\n\nfunc Abs(n int) int { return n }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestAbs(t *testing.T) {\n\tif Abs(-3) != 3 {\n\t\tt.Fatal("Abs(-3) should be 3")\n\t}\n\tif Abs(4) != 4 {\n\t\tt.Fatal("Abs(4) should be 4")\n\t}\n}\n',
    ),
    (
        "clamp",
        "Write a Go test (package sandbox) for Clamp(v, lo, hi int) int, constraining v to [lo, hi].",
        "package sandbox\n\nfunc Clamp(v, lo, hi int) int {\n\tif v < lo {\n\t\treturn lo\n\t}\n\tif v > hi {\n\t\treturn hi\n\t}\n\treturn v\n}\n",
        "package sandbox\n\nfunc Clamp(v, lo, hi int) int {\n\tif v < lo {\n\t\treturn lo\n\t}\n\treturn v\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestClamp(t *testing.T) {\n\tif Clamp(12, 0, 10) != 10 {\n\t\tt.Fatal("above hi should clamp to 10")\n\t}\n\tif Clamp(-1, 0, 10) != 0 {\n\t\tt.Fatal("below lo should clamp to 0")\n\t}\n\tif Clamp(5, 0, 10) != 5 {\n\t\tt.Fatal("in range unchanged")\n\t}\n}\n',
    ),
    (
        "contains",
        "Write a Go test (package sandbox) for Contains(s []int, x int) bool, true when x is in s.",
        "package sandbox\n\nfunc Contains(s []int, x int) bool {\n\tfor _, v := range s {\n\t\tif v == x {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n",
        "package sandbox\n\nfunc Contains(s []int, x int) bool { return false }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestContains(t *testing.T) {\n\tif !Contains([]int{1, 2, 3}, 2) {\n\t\tt.Fatal("2 is present")\n\t}\n\tif Contains([]int{1, 2, 3}, 9) {\n\t\tt.Fatal("9 is absent")\n\t}\n}\n',
    ),
    (
        "count_vowels",
        "Write a Go test (package sandbox) for CountVowels(s string) int, counting ASCII vowels case-insensitively.",
        "package sandbox\n\nimport \"strings\"\n\nfunc CountVowels(s string) int {\n\tn := 0\n\tfor _, c := range strings.ToLower(s) {\n\t\tswitch c {\n\t\tcase 'a', 'e', 'i', 'o', 'u':\n\t\t\tn++\n\t\t}\n\t}\n\treturn n\n}\n",
        "package sandbox\n\nfunc CountVowels(s string) int {\n\tn := 0\n\tfor _, c := range s {\n\t\tif c == 'a' {\n\t\t\tn++\n\t\t}\n\t}\n\treturn n\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestCountVowels(t *testing.T) {\n\tif CountVowels("Hello World") != 3 {\n\t\tt.Fatal("Hello World has 3 vowels")\n\t}\n\tif CountVowels("AEIOU") != 5 {\n\t\tt.Fatal("case-insensitive, all 5")\n\t}\n}\n',
    ),
    (
        "sum",
        "Write a Go test (package sandbox) for Sum(xs []int) int, the sum of all elements.",
        "package sandbox\n\nfunc Sum(xs []int) int {\n\ts := 0\n\tfor _, x := range xs {\n\t\ts += x\n\t}\n\treturn s\n}\n",
        "package sandbox\n\nfunc Sum(xs []int) int {\n\ts := 0\n\tfor _, x := range xs[1:] {\n\t\ts += x\n\t}\n\treturn s\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestSum(t *testing.T) {\n\tif Sum([]int{1, 2, 3}) != 6 {\n\t\tt.Fatal("1+2+3 should be 6")\n\t}\n\tif Sum([]int{5}) != 5 {\n\t\tt.Fatal("single element")\n\t}\n}\n',
    ),
    (
        "gcd",
        "Write a Go test (package sandbox) for GCD(a, b int) int, the greatest common divisor.",
        "package sandbox\n\nfunc GCD(a, b int) int {\n\tfor b != 0 {\n\t\ta, b = b, a%b\n\t}\n\treturn a\n}\n",
        "package sandbox\n\nfunc GCD(a, b int) int { return a }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestGCD(t *testing.T) {\n\tif GCD(12, 8) != 4 {\n\t\tt.Fatal("gcd(12,8) should be 4")\n\t}\n\tif GCD(7, 13) != 1 {\n\t\tt.Fatal("coprime gcd should be 1")\n\t}\n}\n',
    ),
    (
        "last",
        "Write a Go test (package sandbox) for Last(xs []int) (int, bool), the last element and false if empty.",
        "package sandbox\n\nfunc Last(xs []int) (int, bool) {\n\tif len(xs) == 0 {\n\t\treturn 0, false\n\t}\n\treturn xs[len(xs)-1], true\n}\n",
        "package sandbox\n\nfunc Last(xs []int) (int, bool) {\n\tif len(xs) == 0 {\n\t\treturn 0, false\n\t}\n\treturn xs[0], true\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestLast(t *testing.T) {\n\tif v, ok := Last([]int{1, 2, 3}); !ok || v != 3 {\n\t\tt.Fatalf("last = %d,%v want 3,true", v, ok)\n\t}\n\tif _, ok := Last(nil); ok {\n\t\tt.Fatal("empty should be false")\n\t}\n}\n',
    ),
    (
        "is_sorted",
        "Write a Go test (package sandbox) for IsSorted(xs []int) bool, true when xs is non-decreasing.",
        "package sandbox\n\nfunc IsSorted(xs []int) bool {\n\tfor i := 1; i < len(xs); i++ {\n\t\tif xs[i] < xs[i-1] {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n",
        "package sandbox\n\nfunc IsSorted(xs []int) bool { return true }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestIsSorted(t *testing.T) {\n\tif !IsSorted([]int{1, 2, 2, 3}) {\n\t\tt.Fatal("non-decreasing is sorted")\n\t}\n\tif IsSorted([]int{3, 1, 2}) {\n\t\tt.Fatal("3,1,2 is not sorted")\n\t}\n}\n',
    ),
    (
        "repeat",
        "Write a Go test (package sandbox) for Repeat(s string, n int) string, s concatenated n times (empty for n<=0).",
        'package sandbox\n\nimport "strings"\n\nfunc Repeat(s string, n int) string {\n\tif n <= 0 {\n\t\treturn ""\n\t}\n\treturn strings.Repeat(s, n)\n}\n',
        'package sandbox\n\nimport "strings"\n\nfunc Repeat(s string, n int) string {\n\treturn strings.Repeat(s, n+1)\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestRepeat(t *testing.T) {\n\tif Repeat("ab", 3) != "ababab" {\n\t\tt.Fatal("ab x3")\n\t}\n\tif Repeat("x", 0) != "" {\n\t\tt.Fatal("n<=0 should be empty")\n\t}\n}\n',
    ),
    # ---- harder mutants: a trivial / one-case test won't catch these ----
    (
        "is_prime",
        "Write a Go test (package sandbox) for IsPrime(n int) bool (n<2 is not prime).",
        "package sandbox\n\nfunc IsPrime(n int) bool {\n\tif n < 2 {\n\t\treturn false\n\t}\n\tfor i := 2; i*i <= n; i++ {\n\t\tif n%i == 0 {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n",
        "package sandbox\n\nfunc IsPrime(n int) bool { return n%2 != 0 }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestIsPrime(t *testing.T) {\n\tif !IsPrime(7) || !IsPrime(2) || !IsPrime(13) {\n\t\tt.Fatal("primes")\n\t}\n\tif IsPrime(9) || IsPrime(1) || IsPrime(0) || IsPrime(15) {\n\t\tt.Fatal("non-primes")\n\t}\n}\n',
    ),
    (
        "dedup_order",
        "Write a Go test (package sandbox) for Dedup(xs []int) []int removing duplicates while preserving first-seen order.",
        "package sandbox\n\nfunc Dedup(xs []int) []int {\n\tseen := map[int]bool{}\n\tout := []int{}\n\tfor _, x := range xs {\n\t\tif !seen[x] {\n\t\t\tseen[x] = true\n\t\t\tout = append(out, x)\n\t\t}\n\t}\n\treturn out\n}\n",
        "package sandbox\n\nfunc Dedup(xs []int) []int { return xs }\n",
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestDedup(t *testing.T) {\n\tif got := Dedup([]int{1, 1, 2, 3, 2, 1}); !reflect.DeepEqual(got, []int{1, 2, 3}) {\n\t\tt.Fatalf("got %v", got)\n\t}\n}\n',
    ),
    (
        "median",
        "Write a Go test (package sandbox) for Median(xs []int) float64 (sorted-middle; average of two middles for even length; assume non-empty).",
        "package sandbox\n\nimport \"sort\"\n\nfunc Median(xs []int) float64 {\n\tc := append([]int(nil), xs...)\n\tsort.Ints(c)\n\tn := len(c)\n\tif n%2 == 1 {\n\t\treturn float64(c[n/2])\n\t}\n\treturn float64(c[n/2-1]+c[n/2]) / 2\n}\n",
        "package sandbox\n\nimport \"sort\"\n\nfunc Median(xs []int) float64 {\n\tc := append([]int(nil), xs...)\n\tsort.Ints(c)\n\treturn float64(c[len(c)/2])\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestMedian(t *testing.T) {\n\tif Median([]int{3, 1, 2}) != 2 {\n\t\tt.Fatal("odd")\n\t}\n\tif Median([]int{4, 1, 3, 2}) != 2.5 {\n\t\tt.Fatal("even must average the two middles")\n\t}\n}\n',
    ),
    (
        "title_each",
        "Write a Go test (package sandbox) for Title(s string) string upcasing the first letter of each space-separated word.",
        'package sandbox\n\nimport (\n\t"strings"\n\t"unicode"\n)\n\nfunc Title(s string) string {\n\tw := strings.Fields(s)\n\tfor i, x := range w {\n\t\tr := []rune(x)\n\t\tr[0] = unicode.ToUpper(r[0])\n\t\tw[i] = string(r)\n\t}\n\treturn strings.Join(w, " ")\n}\n',
        'package sandbox\n\nimport (\n\t"strings"\n\t"unicode"\n)\n\nfunc Title(s string) string {\n\tr := []rune(s)\n\tif len(r) > 0 {\n\t\tr[0] = unicode.ToUpper(r[0])\n\t}\n\treturn string(r)\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestTitle(t *testing.T) {\n\tif Title("hello world go") != "Hello World Go" {\n\t\tt.Fatal("each word must be capitalised")\n\t}\n}\n',
    ),
    (
        "clamp_pair",
        "Write a Go test (package sandbox) for Clamp(v, lo, hi int) int constraining v to [lo, hi].",
        "package sandbox\n\nfunc Clamp(v, lo, hi int) int {\n\tif v < lo {\n\t\treturn lo\n\t}\n\tif v > hi {\n\t\treturn hi\n\t}\n\treturn v\n}\n",
        "package sandbox\n\nfunc Clamp(v, lo, hi int) int {\n\tif v > hi {\n\t\treturn hi\n\t}\n\treturn v\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestClamp(t *testing.T) {\n\tif Clamp(99, 0, 10) != 10 {\n\t\tt.Fatal("above")\n\t}\n\tif Clamp(-5, 0, 10) != 0 {\n\t\tt.Fatal("below must clamp to lo")\n\t}\n}\n',
    ),
]


def main() -> int:
    write = "--no-write" not in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "data", "go_test_bench.jsonl")

    rows, ok_all = [], True
    for tid, prompt, correct, mutant, test in TASKS:
        ok = discriminates(correct, mutant, test)
        print(f"  [{'PASS' if ok else 'FAIL'}] {tid}")
        if not ok:
            ok_all = False
            continue
        rows.append(
            {
                "id": tid,
                "prompt": prompt,
                "reference": test,
                "metadata": {"module": MODULE, "correct": correct, "mutant": mutant},
            }
        )

    print(f"\n{len(rows)}/{len(TASKS)} test-tasks discriminate (pass-correct + fail-mutant)")
    if write and ok_all:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"wrote {out}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
