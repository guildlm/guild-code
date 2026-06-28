# -*- coding: utf-8 -*-
"""Build (and self-verify) the go-dev held-out benchmark for crucible.

This is the objective yardstick for the GuildLM thesis "a narrow Go specialist
beats a general LLM": a set of spec->code tasks, each with a HIDDEN Go test. At
eval time crucible's `go_functional` evaluator drops the model's prediction +
the hidden test into a sandbox module and runs `go test`; pass@1 is the score.
Run the same benchmark through the specialist and through a general-LLM baseline
and compare pass@1 — no subjective judging.

Each task's `reference` is a known-good solution; this script verifies that
reference+test actually compiles and passes with the real local Go toolchain, so
the benchmark itself is sound before we ever score a model against it.

Usage:
    python build_go_dev_bench.py            # verify + write data/go_dev_bench.jsonl
    python build_go_dev_bench.py --no-write # verify only
"""
import json
import os
import subprocess
import sys
import tempfile

MODULE = "sandbox"

# (id, prompt, reference, test) — reference must make `test` pass.
TASKS = [
    (
        "reverse_runes",
        "Write a Go function Reverse(s string) string that reverses s by runes (Unicode-safe), in package sandbox.",
        "package sandbox\n\nfunc Reverse(s string) string {\n\tr := []rune(s)\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tr[i], r[j] = r[j], r[i]\n\t}\n\treturn string(r)\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestReverse(t *testing.T) {\n\tcases := map[string]string{"abc": "cba", "": "", "héllo": "olléh", "世界": "界世"}\n\tfor in, want := range cases {\n\t\tif got := Reverse(in); got != want {\n\t\t\tt.Errorf("Reverse(%q)=%q want %q", in, got, want)\n\t\t}\n\t}\n}\n',
    ),
    (
        "word_count",
        "Write a Go function WordCount(s string) map[string]int that counts whitespace-separated words, in package sandbox. Use strings.Fields.",
        'package sandbox\n\nimport "strings"\n\nfunc WordCount(s string) map[string]int {\n\tm := make(map[string]int)\n\tfor _, w := range strings.Fields(s) {\n\t\tm[w]++\n\t}\n\treturn m\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestWordCount(t *testing.T) {\n\tm := WordCount("a b a  c a")\n\tif m["a"] != 3 || m["b"] != 1 || m["c"] != 1 {\n\t\tt.Fatalf("got %v", m)\n\t}\n\tif len(WordCount("   ")) != 0 {\n\t\tt.Fatal("blank should be empty")\n\t}\n}\n',
    ),
    (
        "dedup_stable",
        "Write a Go function Dedup(in []int) []int that returns a new slice with duplicates removed, preserving first-seen order, in package sandbox.",
        "package sandbox\n\nfunc Dedup(in []int) []int {\n\tseen := make(map[int]struct{}, len(in))\n\tout := make([]int, 0, len(in))\n\tfor _, v := range in {\n\t\tif _, ok := seen[v]; ok {\n\t\t\tcontinue\n\t\t}\n\t\tseen[v] = struct{}{}\n\t\tout = append(out, v)\n\t}\n\treturn out\n}\n",
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestDedup(t *testing.T) {\n\tif got := Dedup([]int{1, 1, 2, 3, 2, 1}); !reflect.DeepEqual(got, []int{1, 2, 3}) {\n\t\tt.Errorf("got %v", got)\n\t}\n\tif got := Dedup(nil); len(got) != 0 {\n\t\tt.Errorf("nil -> %v", got)\n\t}\n}\n',
    ),
    (
        "is_palindrome",
        "Write a Go function IsPalindrome(s string) bool that ignores case and considers only letters and digits, in package sandbox.",
        'package sandbox\n\nimport "unicode"\n\nfunc IsPalindrome(s string) bool {\n\tvar r []rune\n\tfor _, c := range s {\n\t\tif unicode.IsLetter(c) || unicode.IsDigit(c) {\n\t\t\tr = append(r, unicode.ToLower(c))\n\t\t}\n\t}\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tif r[i] != r[j] {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestIsPalindrome(t *testing.T) {\n\tcases := map[string]bool{"A man, a plan, a canal: Panama": true, "Madam": true, "12321": true, "": true, "hello": false}\n\tfor in, want := range cases {\n\t\tif got := IsPalindrome(in); got != want {\n\t\t\tt.Errorf("IsPalindrome(%q)=%v want %v", in, got, want)\n\t\t}\n\t}\n}\n',
    ),
    (
        "map_generic",
        "Write a generic Go function Map[T, U any](s []T, f func(T) U) []U that applies f to each element, in package sandbox.",
        "package sandbox\n\nfunc Map[T, U any](s []T, f func(T) U) []U {\n\tout := make([]U, len(s))\n\tfor i, v := range s {\n\t\tout[i] = f(v)\n\t}\n\treturn out\n}\n",
        'package sandbox\n\nimport (\n\t"strconv"\n\t"testing"\n)\n\nfunc TestMap(t *testing.T) {\n\tgot := Map([]int{1, 2, 3}, strconv.Itoa)\n\tif len(got) != 3 || got[0] != "1" || got[2] != "3" {\n\t\tt.Errorf("got %v", got)\n\t}\n}\n',
    ),
    (
        "errors_wrap",
        "Write a Go function ParsePort(s string) (int, error) that parses a port and wraps a sentinel ErrBadPort (var ErrBadPort = errors.New(\"bad port\")) with %w when out of 1..65535 or non-numeric, in package sandbox.",
        'package sandbox\n\nimport (\n\t"errors"\n\t"fmt"\n\t"strconv"\n)\n\nvar ErrBadPort = errors.New("bad port")\n\nfunc ParsePort(s string) (int, error) {\n\tn, err := strconv.Atoi(s)\n\tif err != nil {\n\t\treturn 0, fmt.Errorf("%q: %w", s, ErrBadPort)\n\t}\n\tif n < 1 || n > 65535 {\n\t\treturn 0, fmt.Errorf("%d: %w", n, ErrBadPort)\n\t}\n\treturn n, nil\n}\n',
        'package sandbox\n\nimport (\n\t"errors"\n\t"testing"\n)\n\nfunc TestParsePort(t *testing.T) {\n\tif p, err := ParsePort("8080"); err != nil || p != 8080 {\n\t\tt.Fatalf("8080 -> %d %v", p, err)\n\t}\n\tif _, err := ParsePort("0"); !errors.Is(err, ErrBadPort) {\n\t\tt.Fatal("0 should wrap ErrBadPort")\n\t}\n\tif _, err := ParsePort("x"); !errors.Is(err, ErrBadPort) {\n\t\tt.Fatal("x should wrap ErrBadPort")\n\t}\n}\n',
    ),
    (
        "lru_touch",
        "Write a Go type Counter in package sandbox with a thread-safe Inc(key string) and Get(key string) int using sync.Mutex and a map.",
        'package sandbox\n\nimport "sync"\n\ntype Counter struct {\n\tmu sync.Mutex\n\tm  map[string]int\n}\n\nfunc NewCounter() *Counter { return &Counter{m: make(map[string]int)} }\n\nfunc (c *Counter) Inc(key string) {\n\tc.mu.Lock()\n\tc.m[key]++\n\tc.mu.Unlock()\n}\n\nfunc (c *Counter) Get(key string) int {\n\tc.mu.Lock()\n\tdefer c.mu.Unlock()\n\treturn c.m[key]\n}\n',
        'package sandbox\n\nimport (\n\t"sync"\n\t"testing"\n)\n\nfunc TestCounter(t *testing.T) {\n\tc := NewCounter()\n\tvar wg sync.WaitGroup\n\tfor i := 0; i < 100; i++ {\n\t\twg.Add(1)\n\t\tgo func() { defer wg.Done(); c.Inc("x") }()\n\t}\n\twg.Wait()\n\tif c.Get("x") != 100 {\n\t\tt.Errorf("got %d want 100", c.Get("x"))\n\t}\n}\n',
    ),
    (
        "json_roundtrip",
        "Write a Go type Point struct{X, Y int} with json tags x,y and a function Encode(p Point) (string, error) returning compact JSON, in package sandbox.",
        'package sandbox\n\nimport "encoding/json"\n\ntype Point struct {\n\tX int `json:"x"`\n\tY int `json:"y"`\n}\n\nfunc Encode(p Point) (string, error) {\n\tb, err := json.Marshal(p)\n\treturn string(b), err\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestEncode(t *testing.T) {\n\ts, err := Encode(Point{X: 1, Y: 2})\n\tif err != nil || s != `{"x":1,"y":2}` {\n\t\tt.Errorf("got %q err %v", s, err)\n\t}\n}\n',
    ),
    (
        "sort_by_len",
        "Write a Go function SortByLen(ss []string) that sorts ss in place by ascending string length (stable), in package sandbox. Use sort.SliceStable.",
        'package sandbox\n\nimport "sort"\n\nfunc SortByLen(ss []string) {\n\tsort.SliceStable(ss, func(i, j int) bool { return len(ss[i]) < len(ss[j]) })\n}\n',
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestSortByLen(t *testing.T) {\n\tss := []string{"ccc", "a", "bb", "dd"}\n\tSortByLen(ss)\n\tif !reflect.DeepEqual(ss, []string{"a", "bb", "dd", "ccc"}) {\n\t\tt.Errorf("got %v", ss)\n\t}\n}\n',
    ),
    (
        "chunk_slice",
        "Write a generic Go function Chunk[T any](s []T, n int) [][]T that splits s into chunks of at most n (n>=1), in package sandbox.",
        "package sandbox\n\nfunc Chunk[T any](s []T, n int) [][]T {\n\tif n < 1 {\n\t\tn = 1\n\t}\n\tvar out [][]T\n\tfor i := 0; i < len(s); i += n {\n\t\tend := i + n\n\t\tif end > len(s) {\n\t\t\tend = len(s)\n\t\t}\n\t\tout = append(out, s[i:end])\n\t}\n\treturn out\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestChunk(t *testing.T) {\n\tgot := Chunk([]int{1, 2, 3, 4, 5}, 2)\n\tif len(got) != 3 || len(got[0]) != 2 || len(got[2]) != 1 {\n\t\tt.Errorf("got %v", got)\n\t}\n}\n',
    ),
    (
        "max_generic",
        "Write a generic Go function Max[T int | int64 | float64](xs ...T) (T, bool) returning the max and false if empty, in package sandbox.",
        "package sandbox\n\nfunc Max[T int | int64 | float64](xs ...T) (T, bool) {\n\tvar m T\n\tif len(xs) == 0 {\n\t\treturn m, false\n\t}\n\tm = xs[0]\n\tfor _, v := range xs[1:] {\n\t\tif v > m {\n\t\t\tm = v\n\t\t}\n\t}\n\treturn m, true\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestMax(t *testing.T) {\n\tif m, ok := Max(3, 7, 2); !ok || m != 7 {\n\t\tt.Errorf("got %d %v", m, ok)\n\t}\n\tif _, ok := Max[int](); ok {\n\t\tt.Error("empty should be false")\n\t}\n}\n',
    ),
    (
        "trim_prefix_all",
        "Write a Go function CountVowels(s string) int that counts ASCII vowels (aeiou, case-insensitive), in package sandbox.",
        'package sandbox\n\nimport "strings"\n\nfunc CountVowels(s string) int {\n\tn := 0\n\tfor _, c := range strings.ToLower(s) {\n\t\tswitch c {\n\t\tcase \'a\', \'e\', \'i\', \'o\', \'u\':\n\t\t\tn++\n\t\t}\n\t}\n\treturn n\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestCountVowels(t *testing.T) {\n\tif got := CountVowels("Hello World"); got != 3 {\n\t\tt.Errorf("got %d want 3", got)\n\t}\n\tif got := CountVowels("xyz"); got != 0 {\n\t\tt.Errorf("got %d want 0", got)\n\t}\n}\n',
    ),
    (
        "group_parity",
        "Write a Go function GroupParity(xs []int) map[string][]int that groups xs into keys \"even\" and \"odd\" preserving order, in package sandbox.",
        'package sandbox\n\nfunc GroupParity(xs []int) map[string][]int {\n\tout := map[string][]int{}\n\tfor _, x := range xs {\n\t\tif x%2 == 0 {\n\t\t\tout["even"] = append(out["even"], x)\n\t\t} else {\n\t\t\tout["odd"] = append(out["odd"], x)\n\t\t}\n\t}\n\treturn out\n}\n',
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestGroupParity(t *testing.T) {\n\tg := GroupParity([]int{1, 2, 3, 4})\n\tif !reflect.DeepEqual(g["even"], []int{2, 4}) || !reflect.DeepEqual(g["odd"], []int{1, 3}) {\n\t\tt.Errorf("got %v", g)\n\t}\n}\n',
    ),
    (
        "flatten",
        "Write a generic Go function Flatten[T any](in [][]T) []T concatenating the sub-slices in order, in package sandbox.",
        "package sandbox\n\nfunc Flatten[T any](in [][]T) []T {\n\tvar out []T\n\tfor _, s := range in {\n\t\tout = append(out, s...)\n\t}\n\treturn out\n}\n",
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestFlatten(t *testing.T) {\n\tif got := Flatten([][]int{{1, 2}, {3}, {}}); !reflect.DeepEqual(got, []int{1, 2, 3}) {\n\t\tt.Errorf("got %v", got)\n\t}\n}\n',
    ),
    (
        "title_case",
        "Write a Go function Title(s string) string that upcases the first letter of each whitespace-separated word (rune-aware), in package sandbox.",
        'package sandbox\n\nimport (\n\t"strings"\n\t"unicode"\n)\n\nfunc Title(s string) string {\n\twords := strings.Fields(s)\n\tfor i, w := range words {\n\t\tr := []rune(w)\n\t\tr[0] = unicode.ToUpper(r[0])\n\t\twords[i] = string(r)\n\t}\n\treturn strings.Join(words, " ")\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestTitle(t *testing.T) {\n\tif got := Title("hello world"); got != "Hello World" {\n\t\tt.Errorf("got %q", got)\n\t}\n}\n',
    ),
    (
        "counts",
        "Write a generic Go function Counts[T comparable](xs []T) map[T]int returning how many times each element appears, in package sandbox.",
        "package sandbox\n\nfunc Counts[T comparable](xs []T) map[T]int {\n\tm := make(map[T]int)\n\tfor _, x := range xs {\n\t\tm[x]++\n\t}\n\treturn m\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestCounts(t *testing.T) {\n\tc := Counts([]string{"a", "b", "a"})\n\tif c["a"] != 2 || c["b"] != 1 {\n\t\tt.Errorf("got %v", c)\n\t}\n}\n',
    ),
    (
        "atoi_sum",
        "Write a Go function SumDigits(s string) (int, error) that sums the decimal digits in s, returning an error wrapping strconv via fmt.Errorf %w on a non-digit, in package sandbox.",
        'package sandbox\n\nimport (\n\t"fmt"\n\t"strconv"\n)\n\nfunc SumDigits(s string) (int, error) {\n\tsum := 0\n\tfor _, c := range s {\n\t\tn, err := strconv.Atoi(string(c))\n\t\tif err != nil {\n\t\t\treturn 0, fmt.Errorf("SumDigits(%q): %w", s, err)\n\t\t}\n\t\tsum += n\n\t}\n\treturn sum, nil\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestSumDigits(t *testing.T) {\n\tif n, err := SumDigits("123"); err != nil || n != 6 {\n\t\tt.Fatalf("123 -> %d %v", n, err)\n\t}\n\tif _, err := SumDigits("1a"); err == nil {\n\t\tt.Error("1a should error")\n\t}\n}\n',
    ),
    (
        "rune_at",
        "Write a Go function RuneAt(s string, n int) (rune, bool) returning the n-th rune (0-based) and false if out of range, in package sandbox.",
        "package sandbox\n\nfunc RuneAt(s string, n int) (rune, bool) {\n\tr := []rune(s)\n\tif n < 0 || n >= len(r) {\n\t\treturn 0, false\n\t}\n\treturn r[n], true\n}\n",
        'package sandbox\n\nimport "testing"\n\nfunc TestRuneAt(t *testing.T) {\n\tif r, ok := RuneAt("héllo", 1); !ok || r != \'é\' {\n\t\tt.Errorf("got %q %v", r, ok)\n\t}\n\tif _, ok := RuneAt("ab", 5); ok {\n\t\tt.Error("out of range should be false")\n\t}\n}\n',
    ),
    (
        "keys_sorted",
        "Write a Go function SortedKeys(m map[string]int) []string returning the map keys in sorted order, in package sandbox.",
        'package sandbox\n\nimport "sort"\n\nfunc SortedKeys(m map[string]int) []string {\n\tks := make([]string, 0, len(m))\n\tfor k := range m {\n\t\tks = append(ks, k)\n\t}\n\tsort.Strings(ks)\n\treturn ks\n}\n',
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestSortedKeys(t *testing.T) {\n\tif got := SortedKeys(map[string]int{"b": 1, "a": 2, "c": 3}); !reflect.DeepEqual(got, []string{"a", "b", "c"}) {\n\t\tt.Errorf("got %v", got)\n\t}\n}\n',
    ),
]


def verify(reference: str, test: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "go.mod"), "w") as fh:
            fh.write(f"module {MODULE}\n\ngo 1.23\n")
        with open(os.path.join(d, "impl.go"), "w") as fh:
            fh.write(reference)
        with open(os.path.join(d, "impl_test.go"), "w") as fh:
            fh.write(test)
        env = dict(os.environ, GOPROXY="off", GOFLAGS="-mod=mod")
        proc = subprocess.run(
            ["go", "test", "./..."], cwd=d, capture_output=True, text=True, timeout=60, env=env
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def main() -> int:
    write = "--no-write" not in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "data", "go_dev_bench.jsonl")

    rows, ok_all = [], True
    for tid, prompt, ref, test in TASKS:
        ok, diag = verify(ref, test)
        print(f"  [{'PASS' if ok else 'FAIL'}] {tid}")
        if not ok:
            ok_all = False
            print("    ", diag.replace("\n", " ")[:200])
            continue
        rows.append(
            {
                "id": tid,
                "prompt": prompt,
                "reference": ref,
                "prediction": ref,  # placeholder; replaced by the model at eval time
                "metadata": {"module": MODULE, "tests": test},
            }
        )

    print(f"\n{len(rows)}/{len(TASKS)} tasks verified sound")
    if write and ok_all:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"wrote {out}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
