# -*- coding: utf-8 -*-
"""Batch 7 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that stably sorts a slice of {name, score} entries by ascending score using sort.SliceStable, preserving the original order among equal scores. Print the result.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

type entry struct {
	name  string
	score int
}

func main() {
	entries := []entry{
		{"a", 2}, {"b", 1}, {"c", 2}, {"d", 1},
	}

	// SliceStable keeps equal-score entries in their original relative order.
	sort.SliceStable(entries, func(i, j int) bool {
		return entries[i].score < entries[j].score
	})

	for _, e := range entries {
		fmt.Printf("%s:%d ", e.name, e.score)
	}
	fmt.Println() // b:1 d:1 a:2 c:2
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with an isPalindrome function that ignores case, spaces, and punctuation (letters and digits only, rune-aware), and test it on a sentence and a non-palindrome.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
	"unicode"
)

// isPalindrome reports whether s reads the same forwards and backwards,
// considering only letters and digits and ignoring case.
func isPalindrome(s string) bool {
	var clean []rune
	for _, r := range strings.ToLower(s) {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			clean = append(clean, r)
		}
	}
	for i, j := 0, len(clean)-1; i < j; i, j = i+1, j-1 {
		if clean[i] != clean[j] {
			return false
		}
	}
	return true
}

func main() {
	for _, s := range []string{"A man, a plan, a canal: Panama", "hello"} {
		fmt.Printf("%q -> %t\\n", s, isPalindrome(s))
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that demonstrates common strings package operations on a sample string: trim, upper-case, contains, replace-all, split, and count. Print each result.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

func main() {
	s := "  Hello, World, Go  "
	s = strings.TrimSpace(s)

	fmt.Println("upper:    ", strings.ToUpper(s))
	fmt.Println("has 'Go': ", strings.Contains(s, "Go"))
	fmt.Println("replaced: ", strings.ReplaceAll(s, ", ", " | "))
	fmt.Println("split:    ", strings.Split(s, ", "))
	fmt.Println("count 'l':", strings.Count(s, "l"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that writes several formatted lines through a bufio.Writer into a bytes.Buffer, flushes it, and prints the buffer's contents. Explain (in a comment) why the flush is required.",
        "response": '''```go
package main

import (
	"bufio"
	"bytes"
	"fmt"
)

func main() {
	var buf bytes.Buffer
	w := bufio.NewWriter(&buf)

	for i := 1; i <= 3; i++ {
		fmt.Fprintf(w, "line %d\\n", i)
	}

	// bufio.Writer accumulates data in memory; without Flush the buffered bytes
	// would never reach the underlying buffer.
	if err := w.Flush(); err != nil {
		fmt.Println("flush error:", err)
		return
	}
	fmt.Print(buf.String())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic Pair[A, B any] type and a zip function that pairs up two slices element-wise (truncating to the shorter length). Print the pairs.",
        "response": '''```go
package main

import "fmt"

// Pair holds two values of independent types.
type Pair[A, B any] struct {
	First  A
	Second B
}

// zip combines as and bs index-by-index, stopping at the shorter slice.
func zip[A, B any](as []A, bs []B) []Pair[A, B] {
	n := min(len(as), len(bs))
	out := make([]Pair[A, B], n)
	for i := 0; i < n; i++ {
		out[i] = Pair[A, B]{First: as[i], Second: bs[i]}
	}
	return out
}

func main() {
	pairs := zip([]string{"a", "b", "c"}, []int{1, 2, 3})
	for _, p := range pairs {
		fmt.Printf("%s=%d\\n", p.First, p.Second)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that attaches a request-scoped user to a context with context.WithValue (using an unexported key type) and reads it back in a handler, also showing the anonymous (missing value) case.",
        "response": '''```go
package main

import (
	"context"
	"fmt"
)

// ctxKey is unexported so no other package can collide with this key.
type ctxKey string

const userKey ctxKey = "user"

func handle(ctx context.Context) {
	if user, ok := ctx.Value(userKey).(string); ok {
		fmt.Println("handling request for:", user)
	} else {
		fmt.Println("anonymous request")
	}
}

func main() {
	ctx := context.WithValue(context.Background(), userKey, "alice")
	handle(ctx)
	handle(context.Background())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a custom *HTTPError type and a function that returns it wrapped two layers deep, then use errors.As to recover the typed error and read its status code.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

type HTTPError struct {
	Code int
}

func (e *HTTPError) Error() string { return fmt.Sprintf("http %d", e.Code) }

func fetch() error {
	// Two layers of wrapping around the typed error.
	return fmt.Errorf("fetch failed: %w",
		fmt.Errorf("transport error: %w", &HTTPError{Code: 503}))
}

func main() {
	err := fetch()

	var he *HTTPError
	if errors.As(err, &he) { // walks the whole %w chain
		fmt.Println("status code:", he.Code)
	}
	fmt.Println("full error:", err)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a mutex-guarded safe map type that 100 goroutines increment concurrently, then print the final count (which must be 100).",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

type safeMap struct {
	mu sync.Mutex
	m  map[string]int
}

func newSafeMap() *safeMap { return &safeMap{m: make(map[string]int)} }

func (s *safeMap) inc(key string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.m[key]++
}

func (s *safeMap) get(key string) int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.m[key]
}

func main() {
	sm := newSafeMap()
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			sm.inc("hits")
		}()
	}
	wg.Wait()
	fmt.Println("hits:", sm.get("hits"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that produces the first 10 Fibonacci numbers via a generator goroutine that sends on a channel and closes it when done; main ranges over the channel and prints them.",
        "response": '''```go
package main

import "fmt"

// fibGen streams the first n Fibonacci numbers on a channel, closing it at the end.
func fibGen(n int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out) // lets the consumer's range terminate
		a, b := 0, 1
		for i := 0; i < n; i++ {
			out <- a
			a, b = b, a+b
		}
	}()
	return out
}

func main() {
	for v := range fibGen(10) {
		fmt.Print(v, " ")
	}
	fmt.Println()
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a removeAt function that deletes the element at a given index from an int slice while preserving order, and demonstrate removing the middle element.",
        "response": '''```go
package main

import "fmt"

// removeAt returns s with the element at index i removed, preserving order.
// It modifies the backing array, so the original slice should not be reused.
func removeAt(s []int, i int) []int {
	return append(s[:i], s[i+1:]...)
}

func main() {
	s := []int{10, 20, 30, 40, 50}
	s = removeAt(s, 2) // drop 30
	fmt.Println(s)     // [10 20 40 50]
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it skips some elements and can panic. Explain the mutate-while-ranging bug and fix it:\n\n```go\nfunc removeOdds(nums []int) []int {\n\tfor i, n := range nums {\n\t\tif n%2 != 0 {\n\t\t\tnums = append(nums[:i], nums[i+1:]...)\n\t\t}\n\t}\n\treturn nums\n}\n```",
        "response": '''**Bug: mutating the slice's length while ranging over it.** `range nums` captures the slice's length once, at the start. When you delete an element with `append(nums[:i], nums[i+1:]...)`, everything after `i` shifts left by one — but the loop index `i` keeps advancing, so the element that moved into position `i` is **skipped**. With consecutive odds you miss some, and because the loop bound was fixed at the original length, late iterations can index past the now-shorter slice and panic.

**Fix — build a new (filtered) slice instead of mutating in place:**

```go
func removeOdds(nums []int) []int {
	out := nums[:0] // reuse backing array, or use a fresh []int{}
	for _, n := range nums {
		if n%2 == 0 {
			out = append(out, n)
		}
	}
	return out
}
```

Filtering forward into `out` visits every element exactly once and never desynchronizes the index. The `nums[:0]` trick reuses the existing backing array (zero new allocation); use a fresh slice if you must keep the original intact. General rule: never add to or delete from a slice/map while ranging over it — collect into a new container.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; malformed input is silently treated as zero. Explain the problem and show a robust version:\n\n```go\nfunc sum(strs []string) int {\n\ttotal := 0\n\tfor _, s := range strs {\n\t\tn, _ := strconv.Atoi(s)\n\t\ttotal += n\n\t}\n\treturn total\n}\n```",
        "response": '''**Problem: the `strconv.Atoi` error is discarded with `_`.** When a token isn't a valid integer (`"12x"`, `""`, `"3.5"`), `Atoi` returns `(0, err)`; ignoring `err` means that token silently contributes `0`. The function can't tell "the value was 0" from "the value was garbage," so bad data produces a quietly wrong total instead of a clear failure.

**Fix — surface the error, identifying the offending token:**

```go
func sum(strs []string) (int, error) {
	total := 0
	for _, s := range strs {
		n, err := strconv.Atoi(s)
		if err != nil {
			return 0, fmt.Errorf("invalid number %q: %w", s, err)
		}
		total += n
	}
	return total, nil
}
```

Now the caller learns exactly which input was bad and can decide how to handle it. If skipping invalid tokens is genuinely the intended behavior, that should be explicit (e.g. a documented "lenient" variant), not an accidental side effect of dropping the error. Ignoring returned errors is one of the most common sources of silent bugs in Go — `errcheck`/`golangci-lint` flags it.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it prints 0,1,2 then deadlocks. Explain why and fix it:\n\n```go\nfunc main() {\n\tch := make(chan int)\n\tgo func() {\n\t\tfor i := 0; i < 3; i++ {\n\t\t\tch <- i\n\t\t}\n\t}()\n\tfor v := range ch {\n\t\tfmt.Println(v)\n\t}\n}\n```",
        "response": '''**Bug: ranging over a channel that is never closed.** `for v := range ch` keeps receiving until the channel is **closed**. The producer goroutine sends `0, 1, 2` and then returns *without* closing `ch`, so after the third value the `range` blocks waiting for a fourth that never comes. Since no goroutine can make progress, the runtime aborts: `fatal error: all goroutines are asleep - deadlock!`.

**Fix — close the channel when the producer is done:**

```go
func main() {
	ch := make(chan int)
	go func() {
		defer close(ch) // signals the range loop to stop
		for i := 0; i < 3; i++ {
			ch <- i
		}
	}()
	for v := range ch {
		fmt.Println(v)
	}
}
```

`close(ch)` (best placed in a `defer` so it runs even on early return) makes the `range` terminate after draining the buffered/sent values. The rule: the **sender** closes the channel, never the receiver, and only once — closing tells receivers "no more values are coming."''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test that creates a temporary resource and registers its teardown with t.Cleanup, testing this function that writes a file:\n\n```go\n// Save writes content to path, creating it.\nfunc Save(path, content string) error {\n\treturn os.WriteFile(path, []byte(content), 0o644)\n}\n```",
        "response": '''```go
func TestSave(t *testing.T) {
	path := filepath.Join(t.TempDir(), "data.txt")

	// Register teardown next to setup; it runs when the test (and subtests) finish.
	t.Cleanup(func() {
		_ = os.Remove(path) // t.TempDir auto-removes too; shown for the pattern
	})

	if err := Save(path, "hello"); err != nil {
		t.Fatalf("Save: %v", err)
	}

	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if string(got) != "hello" {
		t.Errorf("content = %q, want %q", got, "hello")
	}
}
```

`t.Cleanup` registers teardown right where the resource is created, so setup and cleanup read together and cleanups run in LIFO order even if the test fails or calls `t.Fatal`. It composes better than a trailing `defer` when helpers create resources, because the helper can register its own cleanup. (`t.TempDir()` already auto-removes its directory; the explicit `Remove` here just illustrates the pattern.)''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a table-driven test that asserts both the value and the error message substring for this function:\n\n```go\n// Sqrt returns the square root of x, or an error for negatives.\nfunc Sqrt(x float64) (float64, error) {\n\tif x < 0 {\n\t\treturn 0, fmt.Errorf(\"Sqrt: negative input %g\", x)\n\t}\n\treturn math.Sqrt(x), nil\n}\n```",
        "response": '''```go
func TestSqrt(t *testing.T) {
	tests := []struct {
		name       string
		in         float64
		want       float64
		wantErrSub string // empty = expect no error
	}{
		{"perfect square", 9, 3, ""},
		{"zero", 0, 0, ""},
		{"two", 2, math.Sqrt2, ""},
		{"negative", -4, 0, "negative input"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Sqrt(tt.in)
			if tt.wantErrSub != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErrSub) {
					t.Fatalf("err = %v, want containing %q", err, tt.wantErrSub)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if math.Abs(got-tt.want) > 1e-9 {
				t.Errorf("Sqrt(%g) = %g, want %g", tt.in, got, tt.want)
			}
		})
	}
}
```

Two details worth noting: floating-point results are compared with an epsilon (`1e-9`), never `==`; and the error case checks a **substring** of the message (`strings.Contains`) rather than the exact string, so the test won't break if the wording is tweaked while still verifying the meaningful part ("negative input").''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain the difference between a nil slice and an empty slice in Go, and what this snippet prints:\n\n```go\nvar a []int          // nil slice\nb := []int{}         // empty, non-nil slice\nfmt.Println(a == nil, b == nil, len(a), len(b))\n```",
        "response": '''This prints `true false 0 0`.

- `var a []int` declares a **nil slice**: its internal header has a nil backing-array pointer, `len 0`, and `cap 0`. So `a == nil` is `true`.
- `b := []int{}` is an **empty but non-nil slice**: it points at a (zero-length) array, with `len 0`, `cap 0`. So `b == nil` is `false`.
- Both have `len 0`, which is the key practical point.

What's the same — and why it usually doesn't matter:
- You can `range` over, take `len()`/`cap()` of, and `append` to a **nil** slice exactly as if it were empty. `append(a, 1)` works fine and allocates as needed. So most code should treat "nil" and "empty" identically and just check `len(s) == 0`, never `s == nil`.

Where the distinction *does* matter:
- **JSON:** a nil slice marshals to `null`, an empty slice marshals to `[]`. If an API must return `[]`, initialize with `[]int{}` (or `make([]int, 0)`).
- **Explicit nil checks:** code that compares `== nil` will behave differently — which is exactly why relying on that comparison is discouraged.

Idiom: return a nil slice for "no results" (it's free — no allocation), accept either form on input, and only construct an empty non-nil slice when an external format specifically needs `[]` rather than `null`. The same logic applies to maps: a nil map reads as empty but **panics on write**, so maps you intend to write must be `make`-d.''',
    },
]
