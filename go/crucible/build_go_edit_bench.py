# -*- coding: utf-8 -*-
"""Build (and self-verify) the go-EDIT held-out benchmark for crucible.

The dev benchmark measures from-scratch generation. This one measures the
capability the user cares about for real backends: EDITING existing code. Each
task shows a flawed Go file + a change request; the model must output the
corrected file, scored by a HIDDEN test that only passes if the fix is right.
Same record schema as go_dev_bench, so `bench_compare.py --bench
data/go_edit_bench.jsonl` runs it unchanged.

Every `reference` (the correct edit) is verified to pass its hidden test with
the real local Go toolchain, so the benchmark is sound before scoring a model.

Usage:
    python build_go_edit_bench.py            # verify + write data/go_edit_bench.jsonl
    python build_go_edit_bench.py --no-write # verify only
"""
import json
import os
import subprocess
import sys
import tempfile

MODULE = "sandbox"


def _prompt(req: str, original: str) -> str:
    return (
        "Edit this Go code as requested, in package sandbox. Output the complete "
        f"corrected file in one ```go block, standard library only.\n\n"
        f"Request: {req}\n\nOriginal:\n```go\n{original}```"
    )


# (id, request, original_flawed, reference_correct, hidden_test)
TASKS = [
    (
        "divide_error",
        "Make Divide return (int, error) and a sentinel ErrDivByZero instead of panicking when b == 0.",
        "package sandbox\n\nfunc Divide(a, b int) int { return a / b }\n",
        'package sandbox\n\nimport "errors"\n\nvar ErrDivByZero = errors.New("divide by zero")\n\nfunc Divide(a, b int) (int, error) {\n\tif b == 0 {\n\t\treturn 0, ErrDivByZero\n\t}\n\treturn a / b, nil\n}\n',
        'package sandbox\n\nimport (\n\t"errors"\n\t"testing"\n)\n\nfunc TestDivide(t *testing.T) {\n\tif q, err := Divide(6, 3); err != nil || q != 2 {\n\t\tt.Fatalf("6/3 = %d, %v", q, err)\n\t}\n\tif _, err := Divide(1, 0); !errors.Is(err, ErrDivByZero) {\n\t\tt.Fatal("1/0 should wrap ErrDivByZero")\n\t}\n}\n',
    ),
    (
        "sum_off_by_one",
        "Fix the bug so Sum returns the sum of all elements and never panics.",
        "package sandbox\n\nfunc Sum(nums []int) int {\n\tvar total int\n\tfor i := 1; i <= len(nums); i++ {\n\t\ttotal += nums[i]\n\t}\n\treturn total\n}\n",
        "package sandbox\n\nfunc Sum(nums []int) int {\n\ttotal := 0\n\tfor _, n := range nums {\n\t\ttotal += n\n\t}\n\treturn total\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestSum(t *testing.T) {\n\tif got := Sum([]int{1, 2, 3}); got != 6 {\n\t\tt.Errorf("got %d want 6", got)\n\t}\n\tif got := Sum(nil); got != 0 {\n\t\tt.Errorf("nil got %d want 0", got)\n\t}\n}\n',
    ),
    (
        "nilmap_set",
        "Make the zero-value Registry usable: Set must not panic on a nil map.",
        "package sandbox\n\ntype Registry struct{ m map[string]int }\n\nfunc (r *Registry) Set(k string, v int) { r.m[k] = v }\n\nfunc (r *Registry) Get(k string) int { return r.m[k] }\n",
        "package sandbox\n\ntype Registry struct{ m map[string]int }\n\nfunc (r *Registry) Set(k string, v int) {\n\tif r.m == nil {\n\t\tr.m = make(map[string]int)\n\t}\n\tr.m[k] = v\n}\n\nfunc (r *Registry) Get(k string) int { return r.m[k] }\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestRegistry(t *testing.T) {\n\tvar r Registry\n\tr.Set("a", 1)\n\tif r.Get("a") != 1 {\n\t\tt.Fatalf("got %d", r.Get("a"))\n\t}\n}\n',
    ),
    (
        "wrapped_errors",
        "Fix Classify so it detects a wrapped ErrNotFound (Lookup wraps it with %w).",
        'package sandbox\n\nimport (\n\t"errors"\n\t"fmt"\n)\n\nvar ErrNotFound = errors.New("not found")\n\nfunc Lookup(id int) error { return fmt.Errorf("lookup %d: %w", id, ErrNotFound) }\n\nfunc Classify(err error) string {\n\tif err == ErrNotFound {\n\t\treturn "missing"\n\t}\n\treturn "other"\n}\n',
        'package sandbox\n\nimport (\n\t"errors"\n\t"fmt"\n)\n\nvar ErrNotFound = errors.New("not found")\n\nfunc Lookup(id int) error { return fmt.Errorf("lookup %d: %w", id, ErrNotFound) }\n\nfunc Classify(err error) string {\n\tif errors.Is(err, ErrNotFound) {\n\t\treturn "missing"\n\t}\n\treturn "other"\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestClassify(t *testing.T) {\n\tif got := Classify(Lookup(1)); got != "missing" {\n\t\tt.Errorf("got %q want missing", got)\n\t}\n\tif got := Classify(nil); got != "other" {\n\t\tt.Errorf("nil got %q want other", got)\n\t}\n}\n',
    ),
    (
        "reverse_unicode",
        "Reverse corrupts multi-byte runes because it reverses bytes. Make it rune-safe.",
        "package sandbox\n\nfunc Reverse(s string) string {\n\tb := []byte(s)\n\tfor i, j := 0, len(b)-1; i < j; i, j = i+1, j-1 {\n\t\tb[i], b[j] = b[j], b[i]\n\t}\n\treturn string(b)\n}\n",
        "package sandbox\n\nfunc Reverse(s string) string {\n\tr := []rune(s)\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tr[i], r[j] = r[j], r[i]\n\t}\n\treturn string(r)\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestReverse(t *testing.T) {\n\tif got := Reverse("héllo"); got != "olléh" {\n\t\tt.Errorf("got %q", got)\n\t}\n\tif got := Reverse("世界"); got != "界世" {\n\t\tt.Errorf("got %q", got)\n\t}\n}\n',
    ),
    (
        "toptwo_alias",
        "TopTwo mutates the caller's slice and panics on short input. Don't mutate the argument and guard the length.",
        'package sandbox\n\nimport "sort"\n\nfunc TopTwo(xs []int) []int {\n\tsort.Sort(sort.Reverse(sort.IntSlice(xs)))\n\treturn xs[:2]\n}\n',
        'package sandbox\n\nimport "sort"\n\nfunc TopTwo(xs []int) []int {\n\tcp := append([]int(nil), xs...)\n\tsort.Sort(sort.Reverse(sort.IntSlice(cp)))\n\tn := 2\n\tif len(cp) < n {\n\t\tn = len(cp)\n\t}\n\treturn cp[:n]\n}\n',
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestTopTwo(t *testing.T) {\n\tin := []int{3, 1, 2}\n\tgot := TopTwo(in)\n\tif !reflect.DeepEqual(got, []int{3, 2}) {\n\t\tt.Errorf("got %v", got)\n\t}\n\tif !reflect.DeepEqual(in, []int{3, 1, 2}) {\n\t\tt.Errorf("argument mutated: %v", in)\n\t}\n\tif got := TopTwo([]int{5}); len(got) != 1 {\n\t\tt.Errorf("short slice -> %v", got)\n\t}\n}\n',
    ),
    (
        "palindrome_alnum",
        "Make IsPalindrome ignore case and consider only letters and digits.",
        "package sandbox\n\nfunc IsPalindrome(s string) bool {\n\tr := []rune(s)\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tif r[i] != r[j] {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n",
        'package sandbox\n\nimport "unicode"\n\nfunc IsPalindrome(s string) bool {\n\tvar r []rune\n\tfor _, c := range s {\n\t\tif unicode.IsLetter(c) || unicode.IsDigit(c) {\n\t\t\tr = append(r, unicode.ToLower(c))\n\t\t}\n\t}\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tif r[i] != r[j] {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestIsPalindrome(t *testing.T) {\n\tif !IsPalindrome("A man, a plan, a canal: Panama") {\n\t\tt.Error("Panama should be a palindrome")\n\t}\n\tif IsPalindrome("hello") {\n\t\tt.Error("hello is not a palindrome")\n\t}\n}\n',
    ),
    (
        "max_empty_guard",
        "Max panics on an empty slice. Change it to return (int, bool) with false when empty.",
        "package sandbox\n\nfunc Max(xs []int) int {\n\tm := xs[0]\n\tfor _, v := range xs[1:] {\n\t\tif v > m {\n\t\t\tm = v\n\t\t}\n\t}\n\treturn m\n}\n",
        "package sandbox\n\nfunc Max(xs []int) (int, bool) {\n\tif len(xs) == 0 {\n\t\treturn 0, false\n\t}\n\tm := xs[0]\n\tfor _, v := range xs[1:] {\n\t\tif v > m {\n\t\t\tm = v\n\t\t}\n\t}\n\treturn m, true\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestMax(t *testing.T) {\n\tif m, ok := Max([]int{3, 7, 2}); !ok || m != 7 {\n\t\tt.Errorf("got %d %v", m, ok)\n\t}\n\tif _, ok := Max(nil); ok {\n\t\tt.Error("empty should be false")\n\t}\n}\n',
    ),
]


def verify(reference: str, test: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "go.mod"), "w").write(f"module {MODULE}\n\ngo 1.23\n")
        open(os.path.join(d, "impl.go"), "w").write(reference)
        open(os.path.join(d, "impl_test.go"), "w").write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        proc = subprocess.run(
            ["go", "test", "./..."], cwd=d, capture_output=True, text=True, timeout=60, env=env
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def main() -> int:
    write = "--no-write" not in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "data", "go_edit_bench.jsonl")

    rows, ok_all = [], True
    for tid, req, original, ref, test in TASKS:
        ok, diag = verify(ref, test)
        print(f"  [{'PASS' if ok else 'FAIL'}] {tid}")
        if not ok:
            ok_all = False
            print("    ", diag.replace("\n", " ")[:200])
            continue
        rows.append(
            {
                "id": tid,
                "prompt": _prompt(req, original),
                "reference": ref,
                "prediction": ref,  # placeholder; the model fills this at eval time
                "metadata": {"module": MODULE, "tests": test},
            }
        )

    print(f"\n{len(rows)}/{len(TASKS)} edit tasks verified sound")
    if write and ok_all:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"wrote {out}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
