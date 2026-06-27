# -*- coding: utf-8 -*-
"""Batch 10 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that builds a small binary search tree and returns its in-order traversal (which yields sorted order) using recursion. Print the traversal.",
        "response": '''```go
package main

import "fmt"

type node struct {
	val         int
	left, right *node
}

// inorder appends left subtree, node, right subtree -> ascending order for a BST.
func inorder(n *node, out *[]int) {
	if n == nil {
		return
	}
	inorder(n.left, out)
	*out = append(*out, n.val)
	inorder(n.right, out)
}

func main() {
	root := &node{val: 4,
		left:  &node{val: 2, left: &node{val: 1}, right: &node{val: 3}},
		right: &node{val: 6, left: &node{val: 5}, right: &node{val: 7}},
	}
	var out []int
	inorder(root, &out)
	fmt.Println(out) // [1 2 3 4 5 6 7]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a balanced(s string) bool function that checks whether brackets ()[]{} are correctly matched and nested, using a stack. Test it on a few strings.",
        "response": '''```go
package main

import "fmt"

// balanced reports whether every opening bracket is closed by the matching kind
// in the correct order.
func balanced(s string) bool {
	closeToOpen := map[rune]rune{')': '(', ']': '[', '}': '{'}
	var stack []rune
	for _, r := range s {
		switch r {
		case '(', '[', '{':
			stack = append(stack, r)
		case ')', ']', '}':
			if len(stack) == 0 || stack[len(stack)-1] != closeToOpen[r] {
				return false
			}
			stack = stack[:len(stack)-1]
		}
	}
	return len(stack) == 0
}

func main() {
	for _, s := range []string{"({[]})", "(]", "((("} {
		fmt.Printf("%q -> %t\\n", s, balanced(s))
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses sort.Search to binary-search a sorted slice for a value, reporting the index if found or the insertion point if not.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

func main() {
	s := []int{1, 3, 5, 7, 9, 11}
	x := 7

	// sort.Search returns the smallest index i where the predicate is true.
	i := sort.Search(len(s), func(i int) bool { return s[i] >= x })
	if i < len(s) && s[i] == x {
		fmt.Printf("found %d at index %d\\n", x, i)
	} else {
		fmt.Printf("%d not found; insertion point %d\\n", x, i)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that renders a greeting from a text/template with named fields, writing the result to standard output.",
        "response": '''```go
package main

import (
	"os"
	"text/template"
)

func main() {
	const tmpl = "Hello {{.Name}}, you have {{.Count}} new messages.\\n"

	// Must panics if the template is malformed -- fine for a constant template.
	t := template.Must(template.New("greet").Parse(tmpl))

	data := struct {
		Name  string
		Count int
	}{Name: "Alice", Count: 3}

	if err := t.Execute(os.Stdout, data); err != nil {
		panic(err)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a mergeSorted(a, b []int) []int function that merges two already-sorted slices into one sorted slice in linear time. Print the merge of two slices.",
        "response": '''```go
package main

import "fmt"

// mergeSorted merges two ascending slices into one ascending slice in O(n+m).
func mergeSorted(a, b []int) []int {
	out := make([]int, 0, len(a)+len(b))
	i, j := 0, 0
	for i < len(a) && j < len(b) {
		if a[i] <= b[j] {
			out = append(out, a[i])
			i++
		} else {
			out = append(out, b[j])
			j++
		}
	}
	out = append(out, a[i:]...) // append whatever remains (one of these is empty)
	out = append(out, b[j:]...)
	return out
}

func main() {
	fmt.Println(mergeSorted([]int{1, 3, 5, 9}, []int{2, 4, 6}))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that stores values concurrently in a sync.Map from several goroutines, then sums all stored values with Range. Print the total.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var m sync.Map // safe for concurrent use without an explicit mutex

	var wg sync.WaitGroup
	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			m.Store(i, i*i)
		}(i)
	}
	wg.Wait()

	total := 0
	m.Range(func(_, v any) bool {
		total += v.(int)
		return true // returning false would stop the iteration early
	})
	fmt.Println("sum of squares:", total) // 0+1+4+9+16 = 30
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing a Caesar cipher: a function that shifts letters by n (preserving case and leaving non-letters untouched). Encode a message and decode it back.",
        "response": '''```go
package main

import "fmt"

// caesar shifts each ASCII letter forward by shift (mod 26), leaving other runes
// unchanged. Decoding is caesar(text, 26-shift).
func caesar(s string, shift int) string {
	shift = ((shift % 26) + 26) % 26 // normalize to 0..25
	out := []rune(s)
	for i, r := range out {
		switch {
		case r >= 'a' && r <= 'z':
			out[i] = 'a' + (r-'a'+rune(shift))%26
		case r >= 'A' && r <= 'Z':
			out[i] = 'A' + (r-'A'+rune(shift))%26
		}
	}
	return string(out)
}

func main() {
	enc := caesar("Hello, World!", 3)
	fmt.Println("encoded:", enc)
	fmt.Println("decoded:", caesar(enc, -3))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that run-length-encodes a string (e.g. \"aaabbbcccd\" -> \"a3b3c3d1\") using strings.Builder, and print the result.",
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
	"strings"
)

// rle returns the run-length encoding of s: each run of a rune becomes the rune
// followed by its count.
func rle(s string) string {
	if s == "" {
		return ""
	}
	runes := []rune(s)
	var b strings.Builder
	count := 1
	for i := 1; i <= len(runes); i++ {
		if i < len(runes) && runes[i] == runes[i-1] {
			count++
			continue
		}
		b.WriteRune(runes[i-1])
		b.WriteString(strconv.Itoa(count))
		count = 1
	}
	return b.String()
}

func main() {
	fmt.Println(rle("aaabbbcccd")) // a3b3c3d1
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that generates a reproducible sequence of dice rolls using a seeded math/rand source (so the output is deterministic for tests). Print five rolls.",
        "response": '''```go
package main

import (
	"fmt"
	"math/rand"
)

func main() {
	// A seeded source produces the same sequence every run -- ideal for tests
	// and reproducible simulations.
	r := rand.New(rand.NewSource(42))

	rolls := make([]int, 5)
	for i := range rolls {
		rolls[i] = r.Intn(6) + 1 // 1..6
	}
	fmt.Println("dice rolls:", rolls)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that parses a URL with net/url and prints its host, path, and two query parameters.",
        "response": '''```go
package main

import (
	"fmt"
	"net/url"
)

func main() {
	u, err := url.Parse("https://example.com:8080/search?q=golang&page=2")
	if err != nil {
		fmt.Println("parse error:", err)
		return
	}

	q := u.Query() // parses the raw query once
	fmt.Println("host:", u.Host)
	fmt.Println("path:", u.Path)
	fmt.Println("q:   ", q.Get("q"))
	fmt.Println("page:", q.Get("page"))
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it panics with an index-out-of-range. Explain the off-by-one bugs and fix:\n\n```go\nfunc adjacentSums(nums []int) []int {\n\tvar out []int\n\tfor i := 0; i <= len(nums); i++ {\n\t\tout = append(out, nums[i]+nums[i+1])\n\t}\n\treturn out\n}\n```",
        "response": '''**Two off-by-one errors, both causing out-of-range panics.**

1. The loop condition `i <= len(nums)` lets `i` reach `len(nums)`, but the last valid index is `len(nums)-1`. So `nums[i]` itself goes out of range on the final iteration.
2. The body reads `nums[i+1]`, so even `i == len(nums)-1` is too far — the last index you can safely pair is `len(nums)-2`.

For a function pairing each element with the next one, the loop must stop at `len(nums)-1` (exclusive of the last element, since it has no successor):

**Fix:**

```go
func adjacentSums(nums []int) []int {
	if len(nums) < 2 {
		return nil // no adjacent pairs
	}
	out := make([]int, 0, len(nums)-1)
	for i := 0; i < len(nums)-1; i++ {
		out = append(out, nums[i]+nums[i+1])
	}
	return out
}
```

The condition is now `i < len(nums)-1`, so the highest `i` is `len(nums)-2` and `nums[i+1]` is at most `len(nums)-1` — both in range. The `len(nums) < 2` guard handles empty/single-element input, which would otherwise make `len(nums)-1` underflow the loop logic. When indexing `i+1` in a loop, the bound is almost always `len-1`, not `len`.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it crashes with 'fatal error: concurrent map writes'. Explain and give two fixes:\n\n```go\nfunc main() {\n\tm := map[int]int{}\n\tvar wg sync.WaitGroup\n\tfor i := 0; i < 100; i++ {\n\t\twg.Add(1)\n\t\tgo func(i int) {\n\t\t\tdefer wg.Done()\n\t\t\tm[i] = i * i\n\t\t}(i)\n\t}\n\twg.Wait()\n\tfmt.Println(len(m))\n}\n```",
        "response": '''**Bug: built-in maps are not safe for concurrent writes.** Many goroutines call `m[i] = ...` at once. Unlike a data race on an `int` (which `-race` flags but often "works"), the Go runtime actively **detects** concurrent map access and aborts the program: `fatal error: concurrent map writes`. This is intentional — the map's internal structure can corrupt under concurrent mutation.

**Fix A — guard the map with a `sync.Mutex`:**

```go
var (
	mu sync.Mutex
	m  = map[int]int{}
)
// inside the goroutine:
mu.Lock()
m[i] = i * i
mu.Unlock()
```

**Fix B — use `sync.Map`, designed for concurrent use:**

```go
var m sync.Map
// inside the goroutine:
m.Store(i, i*i)
```

Choose Fix A for the common case (a regular map with a mutex is simplest and fastest for most workloads). Reach for `sync.Map` (Fix B) only in its sweet spot: keys written once and read many times, or disjoint key sets per goroutine. Either way, **a plain map shared across goroutines always needs external synchronization** — for reads too, if any goroutine writes.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; truncating some inputs produces invalid (mojibake) output. Explain and fix:\n\n```go\nfunc truncate(s string, n int) string {\n\tif len(s) > n {\n\t\treturn s[:n]\n\t}\n\treturn s\n}\n```",
        "response": '''**Bug: slicing a string by `len`/byte index can cut a multi-byte UTF-8 character in half.** `len(s)` is the length in **bytes**, and `s[:n]` slices on a byte boundary. For ASCII that's fine, but a character like `é` (2 bytes) or `世` (3 bytes) can straddle index `n`, so `s[:n]` ends mid-sequence and yields an invalid UTF-8 string (it prints as `�` / mojibake).

**Fix — count and cut by runes:**

```go
func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) > n {
		return string(r[:n])
	}
	return s
}
```

Converting to `[]rune` makes `n` mean "n characters," and slicing `r[:n]` always lands on a character boundary. If you care about allocation on the hot path, iterate runes and track a byte cutoff instead:

```go
func truncate(s string, n int) string {
	count := 0
	for i := range s { // range over a string yields rune-start byte indices
		if count == n {
			return s[:i]
		}
		count++
	}
	return s
}
```

Both produce valid UTF-8. The rule: never index or slice a string by a byte offset you computed from `len` when the text may be non-ASCII — use `[]rune`, `range`, or the `unicode/utf8` package. (Note "characters" here means runes; user-perceived grapheme clusters like emoji-with-modifiers need a dedicated library.)''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a table-driven test for this recursive function:\n\n```go\n// Sum returns the sum of a slice using recursion.\nfunc Sum(nums []int) int {\n\tif len(nums) == 0 {\n\t\treturn 0\n\t}\n\treturn nums[0] + Sum(nums[1:])\n}\n```",
        "response": '''```go
func TestSum(t *testing.T) {
	tests := []struct {
		name string
		in   []int
		want int
	}{
		{"empty", nil, 0},
		{"single", []int{5}, 5},
		{"several", []int{1, 2, 3, 4}, 10},
		{"with negatives", []int{-2, 5, -3}, 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Sum(tt.in); got != tt.want {
				t.Errorf("Sum(%v) = %d, want %d", tt.in, got, tt.want)
			}
		})
	}
}
```

The cases pin the recursion's base case (`nil`/empty -> 0), the single-element case (one recursive step), a multi-element sum, and a mix of signs. Testing the empty and single cases explicitly is important for recursive functions, since that's where the termination condition lives and where off-by-one or missing-base-case bugs surface.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go native fuzz test (FuzzXxx) for a round-trip property of this pair of functions, asserting decode(encode(s)) == s:\n\n```go\nfunc encode(s string) string { return base64.StdEncoding.EncodeToString([]byte(s)) }\nfunc decode(s string) (string, error) {\n\tb, err := base64.StdEncoding.DecodeString(s)\n\treturn string(b), err\n}\n```",
        "response": '''```go
func FuzzRoundTrip(f *testing.F) {
	// Seed corpus: the fuzzer mutates from these to explore the input space.
	f.Add("")
	f.Add("hello")
	f.Add("世界 🚀")

	f.Fuzz(func(t *testing.T, s string) {
		out, err := decode(encode(s))
		if err != nil {
			t.Fatalf("decode(encode(%q)) errored: %v", s, err)
		}
		if out != s {
			t.Errorf("round trip mismatch: got %q, want %q", out, s)
		}
	})
}
```

This is a **property-based** test: instead of hard-coding inputs, it asserts an invariant — encoding then decoding any string must return the original — and lets Go's built-in fuzzer (`go test -fuzz=FuzzRoundTrip`) generate thousands of mutated inputs, including tricky bytes and multi-byte runes, to try to break it. The `f.Add(...)` calls seed the corpus with interesting starting points. Round-trip properties (`decode∘encode == id`, `unmarshal∘marshal == id`) are ideal fuzz targets because the oracle is the input itself — no need to precompute expected outputs. Any failing input is automatically saved to `testdata/fuzz/` as a regression case.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain what the `go` keyword does and how goroutines differ from OS threads, using this snippet:\n\n```go\ngo doWork()\nfmt.Println(\"started\")\n```",
        "response": '''The `go` keyword launches `doWork()` as a **goroutine** — a function call that runs concurrently. `go doWork()` schedules the call and returns *immediately*, so `fmt.Println("started")` runs without waiting for `doWork` to finish. (A subtle consequence here: if `main` returns before `doWork` completes, the program exits and `doWork` may never finish — goroutines don't keep the program alive.)

How goroutines differ from OS threads:
- **Cheap.** A goroutine starts with a tiny stack (~2 KB) that grows and shrinks on demand. OS threads reserve a large fixed stack (often 1–8 MB). You can run hundreds of thousands of goroutines; you can't run that many threads.
- **M:N scheduling.** Go's runtime multiplexes many goroutines onto a small pool of OS threads (sized to `GOMAXPROCS`, usually the number of CPU cores). The Go scheduler — not the OS — decides which goroutine runs on which thread, and switches between them at function calls, channel ops, and blocking syscalls. Context switches are cheap because they happen in user space.
- **Blocking is cooperative-friendly.** When a goroutine blocks (on a channel, mutex, or I/O), the scheduler parks it and runs another goroutine on that thread instead of blocking the whole thread. So blocking one goroutine doesn't waste a CPU.

What goroutines are **not**: they aren't automatically parallel safety. Concurrency (structuring work as independent goroutines) is separate from synchronization — multiple goroutines touching shared data still need channels, `sync.Mutex`, etc., or you get data races. And `go f()` gives you no handle to wait on or get a result from; you coordinate completion explicitly with a `sync.WaitGroup`, a channel, or `errgroup`. The mental model: `go` is "run this concurrently, I'm not waiting" — pair it with a synchronization primitive whenever you need the result or need to know it finished.''',
    },
]
