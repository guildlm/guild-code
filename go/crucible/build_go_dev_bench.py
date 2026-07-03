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
    # ---- harder, multi-step tasks (more discriminating) ----
    (
        "balanced",
        "Write a Go function Balanced(s string) bool reporting whether the brackets ()[]{} in s are correctly balanced and nested, ignoring other characters, in package sandbox.",
        'package sandbox\n\nfunc Balanced(s string) bool {\n\tpairs := map[rune]rune{\')\': \'(\', \']\': \'[\', \'}\': \'{\'}\n\tvar st []rune\n\tfor _, c := range s {\n\t\tswitch c {\n\t\tcase \'(\', \'[\', \'{\':\n\t\t\tst = append(st, c)\n\t\tcase \')\', \']\', \'}\':\n\t\t\tif len(st) == 0 || st[len(st)-1] != pairs[c] {\n\t\t\t\treturn false\n\t\t\t}\n\t\t\tst = st[:len(st)-1]\n\t\t}\n\t}\n\treturn len(st) == 0\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestBalanced(t *testing.T) {\n\tcases := map[string]bool{"(a[b]{c})": true, "": true, "([)]": false, "(((": false, "x)y": false, "{[()]}": true}\n\tfor in, want := range cases {\n\t\tif got := Balanced(in); got != want {\n\t\t\tt.Errorf("Balanced(%q)=%v want %v", in, got, want)\n\t\t}\n\t}\n}\n',
    ),
    (
        "merge_intervals",
        "Write a Go function Merge(in [][2]int) [][2]int that merges overlapping closed intervals and returns them sorted by start, in package sandbox.",
        'package sandbox\n\nimport "sort"\n\nfunc Merge(in [][2]int) [][2]int {\n\tif len(in) == 0 {\n\t\treturn nil\n\t}\n\tcp := make([][2]int, len(in))\n\tcopy(cp, in)\n\tsort.Slice(cp, func(i, j int) bool { return cp[i][0] < cp[j][0] })\n\tout := [][2]int{cp[0]}\n\tfor _, iv := range cp[1:] {\n\t\tlast := &out[len(out)-1]\n\t\tif iv[0] <= last[1] {\n\t\t\tif iv[1] > last[1] {\n\t\t\t\tlast[1] = iv[1]\n\t\t\t}\n\t\t} else {\n\t\t\tout = append(out, iv)\n\t\t}\n\t}\n\treturn out\n}\n',
        'package sandbox\n\nimport (\n\t"reflect"\n\t"testing"\n)\n\nfunc TestMerge(t *testing.T) {\n\tgot := Merge([][2]int{{1, 3}, {2, 6}, {8, 10}, {15, 18}})\n\twant := [][2]int{{1, 6}, {8, 10}, {15, 18}}\n\tif !reflect.DeepEqual(got, want) {\n\t\tt.Errorf("got %v want %v", got, want)\n\t}\n\tif got := Merge([][2]int{{1, 4}, {4, 5}}); !reflect.DeepEqual(got, [][2]int{{1, 5}}) {\n\t\tt.Errorf("touching: got %v", got)\n\t}\n}\n',
    ),
    (
        "roman",
        "Write a Go function RomanToInt(s string) int converting a valid uppercase Roman numeral to its integer value (handle subtractive pairs like IV, IX), in package sandbox.",
        'package sandbox\n\nfunc RomanToInt(s string) int {\n\tval := map[byte]int{\'I\': 1, \'V\': 5, \'X\': 10, \'L\': 50, \'C\': 100, \'D\': 500, \'M\': 1000}\n\ttotal := 0\n\tfor i := 0; i < len(s); i++ {\n\t\tv := val[s[i]]\n\t\tif i+1 < len(s) && v < val[s[i+1]] {\n\t\t\ttotal -= v\n\t\t} else {\n\t\t\ttotal += v\n\t\t}\n\t}\n\treturn total\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestRomanToInt(t *testing.T) {\n\tcases := map[string]int{"III": 3, "IV": 4, "IX": 9, "LVIII": 58, "MCMXCIV": 1994}\n\tfor in, want := range cases {\n\t\tif got := RomanToInt(in); got != want {\n\t\t\tt.Errorf("RomanToInt(%q)=%d want %d", in, got, want)\n\t\t}\n\t}\n}\n',
    ),
    (
        "rle_decode",
        "Write a Go function Decode(s string) string that expands a run-length encoding like \"a3b2c1\" into \"aaabbc\" (each letter followed by a one-or-more-digit count), in package sandbox.",
        'package sandbox\n\nimport (\n\t"strings"\n)\n\nfunc Decode(s string) string {\n\tvar b strings.Builder\n\tr := []rune(s)\n\tfor i := 0; i < len(r); {\n\t\tch := r[i]\n\t\ti++\n\t\tn := 0\n\t\tfor i < len(r) && r[i] >= \'0\' && r[i] <= \'9\' {\n\t\t\tn = n*10 + int(r[i]-\'0\')\n\t\t\ti++\n\t\t}\n\t\tfor k := 0; k < n; k++ {\n\t\t\tb.WriteRune(ch)\n\t\t}\n\t}\n\treturn b.String()\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestDecode(t *testing.T) {\n\tif got := Decode("a3b2c1"); got != "aaabbc" {\n\t\tt.Errorf("got %q", got)\n\t}\n\tif got := Decode("x10"); got != "xxxxxxxxxx" {\n\t\tt.Errorf("multi-digit: got %q", got)\n\t}\n}\n',
    ),
    (
        "caesar",
        "Write a Go function Caesar(s string, n int) string shifting each ASCII letter by n positions (wrapping within its case), leaving non-letters unchanged, in package sandbox.",
        'package sandbox\n\nfunc Caesar(s string, n int) string {\n\tn = ((n % 26) + 26) % 26\n\tout := []rune(s)\n\tfor i, c := range out {\n\t\tswitch {\n\t\tcase c >= \'a\' && c <= \'z\':\n\t\t\tout[i] = \'a\' + (c-\'a\'+rune(n))%26\n\t\tcase c >= \'A\' && c <= \'Z\':\n\t\t\tout[i] = \'A\' + (c-\'A\'+rune(n))%26\n\t\t}\n\t}\n\treturn string(out)\n}\n',
        'package sandbox\n\nimport "testing"\n\nfunc TestCaesar(t *testing.T) {\n\tif got := Caesar("abcXYZ", 3); got != "defABC" {\n\t\tt.Errorf("got %q", got)\n\t}\n\tif got := Caesar("Hello, World!", 13); got != "Uryyb, Jbeyq!" {\n\t\tt.Errorf("rot13: got %q", got)\n\t}\n}\n',
    ),
]

# Bench v2 (2026-07-03): 24 HARDER tasks — concurrency, net/http, io, json,
# generics, container/heap, errors.As — added because the original 24 saturate
# near 19/24 for a good code base (±2 noise dominated every comparison). The
# original ids are unchanged for continuity; v2 ids extend the same file.
HARD_TASKS = [
    (
        "safe_counter",
        "Write a Go type Counter with methods Inc() and Value() int that is safe for concurrent use (use sync.Mutex), in package sandbox.",
        "package sandbox\n\nimport \"sync\"\n\ntype Counter struct {\n\tmu sync.Mutex\n\tn  int\n}\n\nfunc (c *Counter) Inc() {\n\tc.mu.Lock()\n\tc.n++\n\tc.mu.Unlock()\n}\n\nfunc (c *Counter) Value() int {\n\tc.mu.Lock()\n\tdefer c.mu.Unlock()\n\treturn c.n\n}\n",
        "package sandbox\n\nimport (\n\t\"sync\"\n\t\"testing\"\n)\n\nfunc TestCounter(t *testing.T) {\n\tvar c Counter\n\tvar wg sync.WaitGroup\n\tfor i := 0; i < 100; i++ {\n\t\twg.Add(1)\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\t\t\tfor j := 0; j < 10; j++ {\n\t\t\t\tc.Inc()\n\t\t\t}\n\t\t}()\n\t}\n\twg.Wait()\n\tif c.Value() != 1000 {\n\t\tt.Fatalf(\"got %d want 1000\", c.Value())\n\t}\n}\n",
    ),
    (
        "merge_channels",
        "Write a Go function Merge(a, b <-chan int) <-chan int that fans-in both channels into one output channel and closes it when both inputs are closed, in package sandbox.",
        "package sandbox\n\nimport \"sync\"\n\nfunc Merge(a, b <-chan int) <-chan int {\n\tout := make(chan int)\n\tvar wg sync.WaitGroup\n\tdrain := func(c <-chan int) {\n\t\tdefer wg.Done()\n\t\tfor v := range c {\n\t\t\tout <- v\n\t\t}\n\t}\n\twg.Add(2)\n\tgo drain(a)\n\tgo drain(b)\n\tgo func() {\n\t\twg.Wait()\n\t\tclose(out)\n\t}()\n\treturn out\n}\n",
        "package sandbox\n\nimport (\n\t\"sort\"\n\t\"testing\"\n)\n\nfunc TestMerge(t *testing.T) {\n\ta := make(chan int)\n\tb := make(chan int)\n\tgo func() {\n\t\tfor _, v := range []int{1, 3, 5} {\n\t\t\ta <- v\n\t\t}\n\t\tclose(a)\n\t}()\n\tgo func() {\n\t\tfor _, v := range []int{2, 4} {\n\t\t\tb <- v\n\t\t}\n\t\tclose(b)\n\t}()\n\tvar got []int\n\tfor v := range Merge(a, b) {\n\t\tgot = append(got, v)\n\t}\n\tsort.Ints(got)\n\tif len(got) != 5 || got[0] != 1 || got[4] != 5 {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n}\n",
    ),
    (
        "http_sum_handler",
        "Write a Go http.HandlerFunc SumHandler that reads JSON {\"a\": int, \"b\": int} from a POST body and responds with JSON {\"sum\": int} and status 200; malformed JSON gets status 400. Package sandbox.",
        "package sandbox\n\nimport (\n\t\"encoding/json\"\n\t\"net/http\"\n)\n\nfunc SumHandler(w http.ResponseWriter, r *http.Request) {\n\tvar in struct {\n\t\tA int `json:\"a\"`\n\t\tB int `json:\"b\"`\n\t}\n\tif err := json.NewDecoder(r.Body).Decode(&in); err != nil {\n\t\thttp.Error(w, \"bad json\", http.StatusBadRequest)\n\t\treturn\n\t}\n\tw.Header().Set(\"Content-Type\", \"application/json\")\n\tjson.NewEncoder(w).Encode(map[string]int{\"sum\": in.A + in.B})\n}\n",
        "package sandbox\n\nimport (\n\t\"encoding/json\"\n\t\"net/http\"\n\t\"net/http/httptest\"\n\t\"strings\"\n\t\"testing\"\n)\n\nfunc TestSumHandler(t *testing.T) {\n\trec := httptest.NewRecorder()\n\treq := httptest.NewRequest(http.MethodPost, \"/sum\", strings.NewReader(`{\"a\":2,\"b\":3}`))\n\tSumHandler(rec, req)\n\tif rec.Code != http.StatusOK {\n\t\tt.Fatalf(\"status %d\", rec.Code)\n\t}\n\tvar out map[string]int\n\tif err := json.NewDecoder(rec.Body).Decode(&out); err != nil || out[\"sum\"] != 5 {\n\t\tt.Fatalf(\"body %v err %v\", out, err)\n\t}\n\trec2 := httptest.NewRecorder()\n\tSumHandler(rec2, httptest.NewRequest(http.MethodPost, \"/sum\", strings.NewReader(\"{oops\")))\n\tif rec2.Code != http.StatusBadRequest {\n\t\tt.Fatalf(\"bad json status %d\", rec2.Code)\n\t}\n}\n",
    ),
    (
        "line_count",
        "Write a Go function CountLines(r io.Reader) (int, error) that counts lines using bufio.Scanner, in package sandbox.",
        "package sandbox\n\nimport (\n\t\"bufio\"\n\t\"io\"\n)\n\nfunc CountLines(r io.Reader) (int, error) {\n\tsc := bufio.NewScanner(r)\n\tn := 0\n\tfor sc.Scan() {\n\t\tn++\n\t}\n\treturn n, sc.Err()\n}\n",
        "package sandbox\n\nimport (\n\t\"strings\"\n\t\"testing\"\n)\n\nfunc TestCountLines(t *testing.T) {\n\tn, err := CountLines(strings.NewReader(\"a\\nb\\nc\"))\n\tif err != nil || n != 3 {\n\t\tt.Fatalf(\"got %d err %v\", n, err)\n\t}\n\tn, _ = CountLines(strings.NewReader(\"\"))\n\tif n != 0 {\n\t\tt.Fatalf(\"empty got %d\", n)\n\t}\n}\n",
    ),
    (
        "top_k_words",
        "Write a Go function TopK(s string, k int) []string returning the k most frequent whitespace-separated words, most frequent first, ties broken alphabetically, in package sandbox.",
        "package sandbox\n\nimport (\n\t\"sort\"\n\t\"strings\"\n)\n\nfunc TopK(s string, k int) []string {\n\tfreq := map[string]int{}\n\tfor _, w := range strings.Fields(s) {\n\t\tfreq[w]++\n\t}\n\twords := make([]string, 0, len(freq))\n\tfor w := range freq {\n\t\twords = append(words, w)\n\t}\n\tsort.Slice(words, func(i, j int) bool {\n\t\tif freq[words[i]] != freq[words[j]] {\n\t\t\treturn freq[words[i]] > freq[words[j]]\n\t\t}\n\t\treturn words[i] < words[j]\n\t})\n\tif k > len(words) {\n\t\tk = len(words)\n\t}\n\treturn words[:k]\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestTopK(t *testing.T) {\n\tgot := TopK(\"b a b c a b\", 2)\n\tif !reflect.DeepEqual(got, []string{\"b\", \"a\"}) {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n\tgot = TopK(\"x y\", 5)\n\tif !reflect.DeepEqual(got, []string{\"x\", \"y\"}) {\n\t\tt.Fatalf(\"ties got %v\", got)\n\t}\n}\n",
    ),
    (
        "sort_people",
        "Write a Go function SortPeople(p []Person) that sorts by Age ascending then Name ascending, with type Person struct{ Name string; Age int }, in package sandbox.",
        "package sandbox\n\nimport \"sort\"\n\ntype Person struct {\n\tName string\n\tAge  int\n}\n\nfunc SortPeople(p []Person) {\n\tsort.Slice(p, func(i, j int) bool {\n\t\tif p[i].Age != p[j].Age {\n\t\t\treturn p[i].Age < p[j].Age\n\t\t}\n\t\treturn p[i].Name < p[j].Name\n\t})\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestSortPeople(t *testing.T) {\n\tp := []Person{{\"b\", 30}, {\"a\", 30}, {\"c\", 20}}\n\tSortPeople(p)\n\twant := []Person{{\"c\", 20}, {\"a\", 30}, {\"b\", 30}}\n\tif !reflect.DeepEqual(p, want) {\n\t\tt.Fatalf(\"got %v\", p)\n\t}\n}\n",
    ),
    (
        "camel_to_snake",
        "Write a Go function CamelToSnake(s string) string converting camelCase to snake_case (an underscore before each upper-case letter, lower-cased), in package sandbox.",
        "package sandbox\n\nimport (\n\t\"strings\"\n\t\"unicode\"\n)\n\nfunc CamelToSnake(s string) string {\n\tvar b strings.Builder\n\tfor i, r := range s {\n\t\tif unicode.IsUpper(r) {\n\t\t\tif i > 0 {\n\t\t\t\tb.WriteByte('_')\n\t\t\t}\n\t\t\tb.WriteRune(unicode.ToLower(r))\n\t\t} else {\n\t\t\tb.WriteRune(r)\n\t\t}\n\t}\n\treturn b.String()\n}\n",
        "package sandbox\n\nimport \"testing\"\n\nfunc TestCamelToSnake(t *testing.T) {\n\tcases := map[string]string{\"fooBarBaz\": \"foo_bar_baz\", \"foo\": \"foo\", \"FooBar\": \"foo_bar\", \"\": \"\"}\n\tfor in, want := range cases {\n\t\tif got := CamelToSnake(in); got != want {\n\t\t\tt.Errorf(\"%q -> %q want %q\", in, got, want)\n\t\t}\n\t}\n}\n",
    ),
    (
        "ring_buffer",
        "Write a Go type Ring created with NewRing(cap int) with methods Push(v int) (evicting the oldest when full) and Items() []int (oldest to newest), in package sandbox.",
        "package sandbox\n\ntype Ring struct {\n\tbuf []int\n\tcap int\n}\n\nfunc NewRing(cap int) *Ring {\n\treturn &Ring{cap: cap}\n}\n\nfunc (r *Ring) Push(v int) {\n\tr.buf = append(r.buf, v)\n\tif len(r.buf) > r.cap {\n\t\tr.buf = r.buf[1:]\n\t}\n}\n\nfunc (r *Ring) Items() []int {\n\tout := make([]int, len(r.buf))\n\tcopy(out, r.buf)\n\treturn out\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestRing(t *testing.T) {\n\tr := NewRing(3)\n\tfor _, v := range []int{1, 2, 3, 4, 5} {\n\t\tr.Push(v)\n\t}\n\tif got := r.Items(); !reflect.DeepEqual(got, []int{3, 4, 5}) {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n}\n",
    ),
    (
        "errors_as_code",
        "Write a Go error type *NotFoundError with field Code int and method Error() string, plus func CodeOf(err error) int that returns the Code from anywhere in a wrapped chain via errors.As, or -1. Package sandbox.",
        "package sandbox\n\nimport (\n\t\"errors\"\n\t\"fmt\"\n)\n\ntype NotFoundError struct {\n\tCode int\n}\n\nfunc (e *NotFoundError) Error() string {\n\treturn fmt.Sprintf(\"not found (code %d)\", e.Code)\n}\n\nfunc CodeOf(err error) int {\n\tvar nf *NotFoundError\n\tif errors.As(err, &nf) {\n\t\treturn nf.Code\n\t}\n\treturn -1\n}\n",
        "package sandbox\n\nimport (\n\t\"fmt\"\n\t\"testing\"\n)\n\nfunc TestCodeOf(t *testing.T) {\n\terr := fmt.Errorf(\"outer: %w\", fmt.Errorf(\"mid: %w\", &NotFoundError{Code: 404}))\n\tif got := CodeOf(err); got != 404 {\n\t\tt.Fatalf(\"got %d\", got)\n\t}\n\tif got := CodeOf(fmt.Errorf(\"plain\")); got != -1 {\n\t\tt.Fatalf(\"plain got %d\", got)\n\t}\n}\n",
    ),
    (
        "group_anagrams",
        "Write a Go function GroupAnagrams(words []string) [][]string grouping anagrams together; sort words within each group and groups by their first word. Package sandbox.",
        "package sandbox\n\nimport \"sort\"\n\nfunc GroupAnagrams(words []string) [][]string {\n\tgroups := map[string][]string{}\n\tfor _, w := range words {\n\t\tb := []byte(w)\n\t\tsort.Slice(b, func(i, j int) bool { return b[i] < b[j] })\n\t\tk := string(b)\n\t\tgroups[k] = append(groups[k], w)\n\t}\n\tout := make([][]string, 0, len(groups))\n\tfor _, g := range groups {\n\t\tsort.Strings(g)\n\t\tout = append(out, g)\n\t}\n\tsort.Slice(out, func(i, j int) bool { return out[i][0] < out[j][0] })\n\treturn out\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestGroupAnagrams(t *testing.T) {\n\tgot := GroupAnagrams([]string{\"eat\", \"tea\", \"tan\", \"ate\", \"nat\", \"bat\"})\n\twant := [][]string{{\"ate\", \"eat\", \"tea\"}, {\"bat\"}, {\"nat\", \"tan\"}}\n\tif !reflect.DeepEqual(got, want) {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n}\n",
    ),
    (
        "lower_bound",
        "Write a Go function LowerBound(s []int, target int) int returning the index of the FIRST element >= target in sorted s (len(s) if none), using binary search, in package sandbox.",
        "package sandbox\n\nfunc LowerBound(s []int, target int) int {\n\tlo, hi := 0, len(s)\n\tfor lo < hi {\n\t\tmid := (lo + hi) / 2\n\t\tif s[mid] < target {\n\t\t\tlo = mid + 1\n\t\t} else {\n\t\t\thi = mid\n\t\t}\n\t}\n\treturn lo\n}\n",
        "package sandbox\n\nimport \"testing\"\n\nfunc TestLowerBound(t *testing.T) {\n\ts := []int{1, 3, 3, 5, 8}\n\tcases := map[int]int{0: 0, 1: 0, 3: 1, 4: 3, 8: 4, 9: 5}\n\tfor target, want := range cases {\n\t\tif got := LowerBound(s, target); got != want {\n\t\t\tt.Errorf(\"LowerBound(%d)=%d want %d\", target, got, want)\n\t\t}\n\t}\n}\n",
    ),
    (
        "rotate_matrix",
        "Write a Go function Rotate(m [][]int) that rotates an NxN matrix 90 degrees clockwise IN PLACE, in package sandbox.",
        "package sandbox\n\nfunc Rotate(m [][]int) {\n\tn := len(m)\n\tfor i := 0; i < n; i++ {\n\t\tfor j := i + 1; j < n; j++ {\n\t\t\tm[i][j], m[j][i] = m[j][i], m[i][j]\n\t\t}\n\t}\n\tfor i := 0; i < n; i++ {\n\t\tfor l, r := 0, n-1; l < r; l, r = l+1, r-1 {\n\t\t\tm[i][l], m[i][r] = m[i][r], m[i][l]\n\t\t}\n\t}\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestRotate(t *testing.T) {\n\tm := [][]int{{1, 2}, {3, 4}}\n\tRotate(m)\n\tif !reflect.DeepEqual(m, [][]int{{3, 1}, {4, 2}}) {\n\t\tt.Fatalf(\"got %v\", m)\n\t}\n}\n",
    ),
    (
        "parse_query",
        "Write a Go function ParseQuery(q string) map[string][]string parsing \"a=1&b=2&a=3\" into {\"a\":[\"1\",\"3\"],\"b\":[\"2\"]} (no URL-decoding; skip empty pairs and pairs without '='), in package sandbox.",
        "package sandbox\n\nimport \"strings\"\n\nfunc ParseQuery(q string) map[string][]string {\n\tout := map[string][]string{}\n\tfor _, pair := range strings.Split(q, \"&\") {\n\t\tif pair == \"\" {\n\t\t\tcontinue\n\t\t}\n\t\tk, v, ok := strings.Cut(pair, \"=\")\n\t\tif !ok {\n\t\t\tcontinue\n\t\t}\n\t\tout[k] = append(out[k], v)\n\t}\n\treturn out\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestParseQuery(t *testing.T) {\n\tgot := ParseQuery(\"a=1&b=2&a=3&&junk\")\n\twant := map[string][]string{\"a\": {\"1\", \"3\"}, \"b\": {\"2\"}}\n\tif !reflect.DeepEqual(got, want) {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n}\n",
    ),
    (
        "once_config",
        "Write a Go function GetConfig() *Config that lazily creates a single shared Config exactly once using sync.Once, with type Config struct{ Loaded bool }, in package sandbox.",
        "package sandbox\n\nimport \"sync\"\n\ntype Config struct {\n\tLoaded bool\n}\n\nvar (\n\tcfgOnce sync.Once\n\tcfg     *Config\n)\n\nfunc GetConfig() *Config {\n\tcfgOnce.Do(func() {\n\t\tcfg = &Config{Loaded: true}\n\t})\n\treturn cfg\n}\n",
        "package sandbox\n\nimport (\n\t\"sync\"\n\t\"testing\"\n)\n\nfunc TestGetConfig(t *testing.T) {\n\tvar wg sync.WaitGroup\n\tptrs := make([]*Config, 50)\n\tfor i := 0; i < 50; i++ {\n\t\twg.Add(1)\n\t\tgo func(i int) {\n\t\t\tdefer wg.Done()\n\t\t\tptrs[i] = GetConfig()\n\t\t}(i)\n\t}\n\twg.Wait()\n\tfor _, p := range ptrs {\n\t\tif p != ptrs[0] || !p.Loaded {\n\t\t\tt.Fatal(\"not a single shared instance\")\n\t\t}\n\t}\n}\n",
    ),
    (
        "worker_pool_sum",
        "Write a Go function ParallelSum(nums []int, workers int) int summing nums using exactly `workers` goroutines reading from a shared jobs channel, in package sandbox.",
        "package sandbox\n\nimport \"sync\"\n\nfunc ParallelSum(nums []int, workers int) int {\n\tjobs := make(chan int)\n\tvar mu sync.Mutex\n\ttotal := 0\n\tvar wg sync.WaitGroup\n\tfor i := 0; i < workers; i++ {\n\t\twg.Add(1)\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\t\t\tfor v := range jobs {\n\t\t\t\tmu.Lock()\n\t\t\t\ttotal += v\n\t\t\t\tmu.Unlock()\n\t\t\t}\n\t\t}()\n\t}\n\tfor _, v := range nums {\n\t\tjobs <- v\n\t}\n\tclose(jobs)\n\twg.Wait()\n\treturn total\n}\n",
        "package sandbox\n\nimport \"testing\"\n\nfunc TestParallelSum(t *testing.T) {\n\tnums := make([]int, 100)\n\twant := 0\n\tfor i := range nums {\n\t\tnums[i] = i\n\t\twant += i\n\t}\n\tif got := ParallelSum(nums, 4); got != want {\n\t\tt.Fatalf(\"got %d want %d\", got, want)\n\t}\n}\n",
    ),
    (
        "status_stringer",
        "Write a Go type Status int with constants Pending=0, Active=1, Done=2 and a String() string method returning \"pending\", \"active\", \"done\" (or \"unknown\"), in package sandbox.",
        "package sandbox\n\ntype Status int\n\nconst (\n\tPending Status = iota\n\tActive\n\tDone\n)\n\nfunc (s Status) String() string {\n\tswitch s {\n\tcase Pending:\n\t\treturn \"pending\"\n\tcase Active:\n\t\treturn \"active\"\n\tcase Done:\n\t\treturn \"done\"\n\tdefault:\n\t\treturn \"unknown\"\n\t}\n}\n",
        "package sandbox\n\nimport (\n\t\"fmt\"\n\t\"testing\"\n)\n\nfunc TestStatusString(t *testing.T) {\n\tif fmt.Sprint(Active) != \"active\" || fmt.Sprint(Status(9)) != \"unknown\" {\n\t\tt.Fatalf(\"got %v %v\", Active, Status(9))\n\t}\n}\n",
    ),
    (
        "json_omitempty",
        "Write a Go type User struct with fields Name string (json \"name\") and Email string (json \"email\", omitempty), plus func RenderUser(u User) (string, error) returning its compact JSON, in package sandbox.",
        "package sandbox\n\nimport \"encoding/json\"\n\ntype User struct {\n\tName  string `json:\"name\"`\n\tEmail string `json:\"email,omitempty\"`\n}\n\nfunc RenderUser(u User) (string, error) {\n\tb, err := json.Marshal(u)\n\treturn string(b), err\n}\n",
        "package sandbox\n\nimport \"testing\"\n\nfunc TestRenderUser(t *testing.T) {\n\ts, err := RenderUser(User{Name: \"ada\"})\n\tif err != nil || s != `{\"name\":\"ada\"}` {\n\t\tt.Fatalf(\"got %q err %v\", s, err)\n\t}\n\ts, _ = RenderUser(User{Name: \"ada\", Email: \"a@b.c\"})\n\tif s != `{\"name\":\"ada\",\"email\":\"a@b.c\"}` {\n\t\tt.Fatalf(\"got %q\", s)\n\t}\n}\n",
    ),
    (
        "upper_reader",
        "Write a Go type UpperReader wrapping an io.Reader so Read returns the same bytes upper-cased (ASCII), with constructor NewUpperReader(r io.Reader) *UpperReader, in package sandbox.",
        "package sandbox\n\nimport \"io\"\n\ntype UpperReader struct {\n\tr io.Reader\n}\n\nfunc NewUpperReader(r io.Reader) *UpperReader {\n\treturn &UpperReader{r: r}\n}\n\nfunc (u *UpperReader) Read(p []byte) (int, error) {\n\tn, err := u.r.Read(p)\n\tfor i := 0; i < n; i++ {\n\t\tif p[i] >= 'a' && p[i] <= 'z' {\n\t\t\tp[i] -= 32\n\t\t}\n\t}\n\treturn n, err\n}\n",
        "package sandbox\n\nimport (\n\t\"io\"\n\t\"strings\"\n\t\"testing\"\n)\n\nfunc TestUpperReader(t *testing.T) {\n\tb, err := io.ReadAll(NewUpperReader(strings.NewReader(\"Hello, Go!\")))\n\tif err != nil || string(b) != \"HELLO, GO!\" {\n\t\tt.Fatalf(\"got %q err %v\", b, err)\n\t}\n}\n",
    ),
    (
        "min_heap",
        "Write a Go min-heap of ints using container/heap: type IntHeap implementing heap.Interface, plus func PopAllSorted(vals []int) []int that heapifies and pops all values in ascending order. Package sandbox.",
        "package sandbox\n\nimport \"container/heap\"\n\ntype IntHeap []int\n\nfunc (h IntHeap) Len() int            { return len(h) }\nfunc (h IntHeap) Less(i, j int) bool  { return h[i] < h[j] }\nfunc (h IntHeap) Swap(i, j int)       { h[i], h[j] = h[j], h[i] }\nfunc (h *IntHeap) Push(x interface{}) { *h = append(*h, x.(int)) }\nfunc (h *IntHeap) Pop() interface{} {\n\told := *h\n\tn := len(old)\n\tv := old[n-1]\n\t*h = old[:n-1]\n\treturn v\n}\n\nfunc PopAllSorted(vals []int) []int {\n\th := IntHeap(append([]int(nil), vals...))\n\theap.Init(&h)\n\tout := make([]int, 0, len(vals))\n\tfor h.Len() > 0 {\n\t\tout = append(out, heap.Pop(&h).(int))\n\t}\n\treturn out\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestPopAllSorted(t *testing.T) {\n\tgot := PopAllSorted([]int{5, 1, 4, 2, 3})\n\tif !reflect.DeepEqual(got, []int{1, 2, 3, 4, 5}) {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n}\n",
    ),
    (
        "filter_generic",
        "Write a generic Go function Filter[T any](s []T, keep func(T) bool) []T returning elements for which keep is true, preserving order, in package sandbox.",
        "package sandbox\n\nfunc Filter[T any](s []T, keep func(T) bool) []T {\n\tout := make([]T, 0, len(s))\n\tfor _, v := range s {\n\t\tif keep(v) {\n\t\t\tout = append(out, v)\n\t\t}\n\t}\n\treturn out\n}\n",
        "package sandbox\n\nimport (\n\t\"reflect\"\n\t\"testing\"\n)\n\nfunc TestFilter(t *testing.T) {\n\tgot := Filter([]int{1, 2, 3, 4}, func(v int) bool { return v%2 == 0 })\n\tif !reflect.DeepEqual(got, []int{2, 4}) {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n\tif got := Filter([]string{}, func(string) bool { return true }); len(got) != 0 {\n\t\tt.Fatalf(\"empty got %v\", got)\n\t}\n}\n",
    ),
    (
        "truncate_hour",
        "Write a Go function BucketByHour(ts []time.Time) map[time.Time]int counting timestamps per hour bucket (truncate each to the hour with Truncate), in package sandbox.",
        "package sandbox\n\nimport \"time\"\n\nfunc BucketByHour(ts []time.Time) map[time.Time]int {\n\tout := map[time.Time]int{}\n\tfor _, t := range ts {\n\t\tout[t.Truncate(time.Hour)]++\n\t}\n\treturn out\n}\n",
        "package sandbox\n\nimport (\n\t\"testing\"\n\t\"time\"\n)\n\nfunc TestBucketByHour(t *testing.T) {\n\tbase := time.Date(2024, 1, 2, 10, 0, 0, 0, time.UTC)\n\tts := []time.Time{base.Add(5 * time.Minute), base.Add(59 * time.Minute), base.Add(61 * time.Minute)}\n\tgot := BucketByHour(ts)\n\tif got[base] != 2 || got[base.Add(time.Hour)] != 1 {\n\t\tt.Fatalf(\"got %v\", got)\n\t}\n}\n",
    ),
    (
        "ctx_cancel_worker",
        "Write a Go function CountUntil(ctx context.Context, ch <-chan int) int that consumes ints from ch and returns how many it received when ctx is cancelled OR ch is closed, in package sandbox.",
        "package sandbox\n\nimport \"context\"\n\nfunc CountUntil(ctx context.Context, ch <-chan int) int {\n\tn := 0\n\tfor {\n\t\tselect {\n\t\tcase <-ctx.Done():\n\t\t\treturn n\n\t\tcase _, ok := <-ch:\n\t\t\tif !ok {\n\t\t\t\treturn n\n\t\t\t}\n\t\t\tn++\n\t\t}\n\t}\n}\n",
        "package sandbox\n\nimport (\n\t\"context\"\n\t\"testing\"\n)\n\nfunc TestCountUntil(t *testing.T) {\n\tch := make(chan int)\n\tgo func() {\n\t\tfor i := 0; i < 4; i++ {\n\t\t\tch <- i\n\t\t}\n\t\tclose(ch)\n\t}()\n\tif got := CountUntil(context.Background(), ch); got != 4 {\n\t\tt.Fatalf(\"closed got %d\", got)\n\t}\n\tctx, cancel := context.WithCancel(context.Background())\n\tcancel()\n\tif got := CountUntil(ctx, make(chan int)); got != 0 {\n\t\tt.Fatalf(\"cancelled got %d\", got)\n\t}\n}\n",
    ),
    (
        "chunk_reader",
        "Write a Go function ReadChunks(r io.Reader, size int) ([][]byte, error) reading r fully and splitting the bytes into chunks of at most `size`, in package sandbox.",
        "package sandbox\n\nimport \"io\"\n\nfunc ReadChunks(r io.Reader, size int) ([][]byte, error) {\n\tdata, err := io.ReadAll(r)\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\tvar out [][]byte\n\tfor len(data) > 0 {\n\t\tn := size\n\t\tif n > len(data) {\n\t\t\tn = len(data)\n\t\t}\n\t\tchunk := make([]byte, n)\n\t\tcopy(chunk, data[:n])\n\t\tout = append(out, chunk)\n\t\tdata = data[n:]\n\t}\n\treturn out, nil\n}\n",
        "package sandbox\n\nimport (\n\t\"strings\"\n\t\"testing\"\n)\n\nfunc TestReadChunks(t *testing.T) {\n\tchunks, err := ReadChunks(strings.NewReader(\"abcdefg\"), 3)\n\tif err != nil || len(chunks) != 3 {\n\t\tt.Fatalf(\"got %d chunks err %v\", len(chunks), err)\n\t}\n\tif string(chunks[0]) != \"abc\" || string(chunks[2]) != \"g\" {\n\t\tt.Fatalf(\"got %q %q\", chunks[0], chunks[2])\n\t}\n}\n",
    ),
    (
        "middleware_chain",
        "Write a Go function Chain(h http.Handler, mws ...func(http.Handler) http.Handler) http.Handler applying middlewares so the FIRST one in the list is the OUTERMOST, in package sandbox.",
        "package sandbox\n\nimport \"net/http\"\n\nfunc Chain(h http.Handler, mws ...func(http.Handler) http.Handler) http.Handler {\n\tfor i := len(mws) - 1; i >= 0; i-- {\n\t\th = mws[i](h)\n\t}\n\treturn h\n}\n",
        "package sandbox\n\nimport (\n\t\"net/http\"\n\t\"net/http/httptest\"\n\t\"testing\"\n)\n\nfunc TestChain(t *testing.T) {\n\tvar order []string\n\tmw := func(name string) func(http.Handler) http.Handler {\n\t\treturn func(next http.Handler) http.Handler {\n\t\t\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {\n\t\t\t\torder = append(order, name)\n\t\t\t\tnext.ServeHTTP(w, r)\n\t\t\t})\n\t\t}\n\t}\n\th := Chain(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {\n\t\torder = append(order, \"handler\")\n\t}), mw(\"a\"), mw(\"b\"))\n\th.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest(http.MethodGet, \"/\", nil))\n\tif len(order) != 3 || order[0] != \"a\" || order[1] != \"b\" || order[2] != \"handler\" {\n\t\tt.Fatalf(\"order %v\", order)\n\t}\n}\n",
    ),
]

TASKS = TASKS + HARD_TASKS


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
