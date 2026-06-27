# -*- coding: utf-8 -*-
"""Batch 14 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that defines command-line flags with the flag package (a --name string and a --count int with defaults) and greets accordingly. With no arguments the defaults should apply.",
        "response": '''```go
package main

import (
	"flag"
	"fmt"
)

func main() {
	name := flag.String("name", "world", "name to greet")
	count := flag.Int("count", 1, "number of greetings")
	flag.Parse() // reads os.Args; with none, the defaults are used

	for i := 0; i < *count; i++ {
		fmt.Printf("Hello, %s!\\n", *name)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that encodes a map to indented JSON by writing through a json.Encoder with SetIndent into a bytes.Buffer, then prints the buffer.",
        "response": '''```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
)

func main() {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetIndent("", "  ")

	// json sorts map keys, so the output is deterministic.
	if err := enc.Encode(map[string]int{"b": 2, "a": 1}); err != nil {
		fmt.Println("encode error:", err)
		return
	}
	fmt.Print(buf.String())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic Join[T Stringer](items []T, sep string) string constrained to types implementing a Stringer interface, and use it on a slice of Points.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

// Stringer is the constraint: T must have a String() string method.
type Stringer interface {
	String() string
}

func Join[T Stringer](items []T, sep string) string {
	parts := make([]string, len(items))
	for i, it := range items {
		parts[i] = it.String()
	}
	return strings.Join(parts, sep)
}

type Point struct{ X, Y int }

func (p Point) String() string { return fmt.Sprintf("(%d,%d)", p.X, p.Y) }

func main() {
	pts := []Point{{1, 2}, {3, 4}, {5, 6}}
	fmt.Println(Join(pts, " -> "))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that formats a fixed time in RFC3339, prints its Unix timestamp, and prints the weekday. Use a UTC time.Date so the output is deterministic.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	t := time.Date(2026, time.June, 27, 14, 30, 0, 0, time.UTC)

	fmt.Println("RFC3339: ", t.Format(time.RFC3339))
	fmt.Println("unix:    ", t.Unix())
	fmt.Println("weekday: ", t.Weekday())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses slices.IndexFunc to find the first element matching a predicate and slices.ContainsFunc to test membership by predicate, on a slice of names.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	names := []string{"al", "bob", "carol", "dan"}

	// First name longer than 2 characters.
	i := slices.IndexFunc(names, func(s string) bool { return len(s) > 2 })
	fmt.Printf("first len>2: index %d (%q)\\n", i, names[i])

	has := slices.ContainsFunc(names, func(s string) bool { return s == "carol" })
	fmt.Println("contains carol:", has)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a custom StatusError type that implements both Error() and an Is(target error) bool method, so errors.Is matches by status code even through wrapping. Demonstrate matching and non-matching codes.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

type StatusError struct {
	Code int
}

func (e StatusError) Error() string { return fmt.Sprintf("status %d", e.Code) }

// Is lets errors.Is compare by Code instead of by identity.
func (e StatusError) Is(target error) bool {
	t, ok := target.(StatusError)
	return ok && t.Code == e.Code
}

func main() {
	err := fmt.Errorf("request failed: %w", StatusError{Code: 404})

	fmt.Println("is 404:", errors.Is(err, StatusError{Code: 404}))
	fmt.Println("is 500:", errors.Is(err, StatusError{Code: 500}))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that builds an inverted index from a set of documents: a map from each word to the sorted list of document ids containing it. Print a couple of postings.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
	"strings"
)

// invertIndex maps each word to the sorted ids of documents containing it.
func invertIndex(docs map[string]string) map[string][]string {
	idx := map[string][]string{}
	for id, text := range docs {
		for _, w := range strings.Fields(text) {
			idx[w] = append(idx[w], id)
		}
	}
	for _, ids := range idx {
		sort.Strings(ids) // deterministic ordering
	}
	return idx
}

func main() {
	docs := map[string]string{
		"d1": "go is fast",
		"d2": "go is fun",
	}
	idx := invertIndex(docs)
	fmt.Println("go ->", idx["go"])
	fmt.Println("is ->", idx["is"])
	fmt.Println("fast ->", idx["fast"])
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that generates all permutations of a small int slice recursively, and prints how many there are plus the first permutation.",
        "response": '''```go
package main

import "fmt"

// permute returns every ordering of nums. It copies at the leaves so the
// returned slices don't alias each other.
func permute(nums []int) [][]int {
	if len(nums) <= 1 {
		return [][]int{append([]int(nil), nums...)}
	}
	var result [][]int
	for i := range nums {
		rest := make([]int, 0, len(nums)-1)
		rest = append(rest, nums[:i]...)
		rest = append(rest, nums[i+1:]...)
		for _, p := range permute(rest) {
			result = append(result, append([]int{nums[i]}, p...))
		}
	}
	return result
}

func main() {
	perms := permute([]int{1, 2, 3})
	fmt.Println("count:", len(perms)) // 6
	fmt.Println("first:", perms[0])
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic MapErr[T, U any](s []T, f func(T) (U, error)) ([]U, error) that maps each element but stops at the first error (reporting the index). Demonstrate a success and a failure using strconv.Atoi.",
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
)

// MapErr applies f to every element, short-circuiting on the first error.
func MapErr[T, U any](s []T, f func(T) (U, error)) ([]U, error) {
	out := make([]U, len(s))
	for i, v := range s {
		u, err := f(v)
		if err != nil {
			return nil, fmt.Errorf("index %d: %w", i, err)
		}
		out[i] = u
	}
	return out, nil
}

func main() {
	nums, err := MapErr([]string{"1", "2", "3"}, strconv.Atoi)
	fmt.Println(nums, err) // [1 2 3] <nil>

	_, err = MapErr([]string{"1", "x"}, strconv.Atoi)
	fmt.Println("error:", err) // index 1: ...
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a positiveMod(a, b int) int helper that always returns a non-negative remainder (unlike Go's %), and use it to wrap an index around a slice. Print a wrapped lookup.",
        "response": '''```go
package main

import "fmt"

// positiveMod returns a result in [0, b) even for negative a, unlike Go's %
// operator, which keeps the sign of the dividend.
func positiveMod(a, b int) int {
	return ((a % b) + b) % b
}

func main() {
	days := []string{"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}

	// "3 days before Monday" should wrap to Friday, not panic.
	idx := positiveMod(0-3, len(days))
	fmt.Printf("index %d -> %s\\n", idx, days[idx]) // index 4 -> Fri
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; json.Unmarshal returns an error and the struct stays empty. Explain and fix:\n\n```go\nfunc parse(data []byte) (User, error) {\n\tvar u User\n\terr := json.Unmarshal(data, u)\n\treturn u, err\n}\n```",
        "response": '''**Bug: `json.Unmarshal` is given a value, not a pointer.** Unmarshal needs somewhere to *write* the decoded data, so it requires a pointer to the destination. Passing `u` (a copy of the struct) gives it nothing it can modify, and it returns the error `json: Unmarshal(non-pointer main.User)`. Even if it didn't error, writing into a copy wouldn't affect the returned `u`.

**Fix — pass the address:**

```go
func parse(data []byte) (User, error) {
	var u User
	if err := json.Unmarshal(data, &u); err != nil {
		return User{}, fmt.Errorf("parse user: %w", err)
	}
	return u, nil
}
```

`&u` lets Unmarshal populate the struct in place. This is the same rule as `fmt.Sscanf`, `flag.IntVar`, and any API that fills in a result: it needs a pointer to the thing it writes. A useful tell — if a decode "succeeds" but your value is all zeros, or you get a `non-pointer`/`nil` error, you almost certainly forgot the `&`. (Note Unmarshal also needs the destination's fields to be *exported* to populate them.)''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it panics for some inputs because of how Go handles negative modulo. Explain and fix:\n\n```go\nfunc rotateLeft(s []int, n int) []int {\n\tk := n % len(s)\n\treturn append(s[k:], s[:k]...)\n}\n// rotateLeft(s, -1) panics\n```",
        "response": '''**Bug: Go's `%` keeps the sign of the dividend, so `n % len(s)` can be negative.** For `rotateLeft(s, -1)` with `len(s) == 3`, `k = -1 % 3 == -1`. Then `s[k:]` is `s[-1:]`, which panics with `slice bounds out of range [-1:]`. The code assumes `k` is always in `[0, len(s))`, which is true in many languages but not Go for negative `n`.

**Fix — normalize the modulo into the non-negative range:**

```go
func rotateLeft(s []int, n int) []int {
	if len(s) == 0 {
		return s
	}
	k := ((n % len(s)) + len(s)) % len(s) // always in [0, len(s))
	return append(s[k:], s[:k]...)
}
```

`((n % m) + m) % m` shifts any negative remainder back into `[0, m)` while leaving non-negative results unchanged, so `rotateLeft(s, -1)` rotates the same as `rotateLeft(s, len(s)-1)`. I also guarded the empty-slice case, since `n % 0` would itself panic. Remember this whenever a remainder is used as an index, ring-buffer position, or wrap-around offset and the input can be negative.

(Aside: `append(s[k:], s[:k]...)` mutates `s`'s backing array; if the caller must keep the original, build the result into a fresh slice instead.)''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go fan-in; it panics with 'close of closed channel'. Explain and fix:\n\n```go\nfunc merge(chs []<-chan int) <-chan int {\n\tout := make(chan int)\n\tfor _, ch := range chs {\n\t\tgo func(c <-chan int) {\n\t\t\tfor v := range c {\n\t\t\t\tout <- v\n\t\t\t}\n\t\t\tclose(out)\n\t\t}(ch)\n\t}\n\treturn out\n}\n```",
        "response": '''**Bug: every fan-in goroutine closes `out`.** A channel must be closed exactly once. The first goroutine to finish draining its input closes `out`; when a second goroutine finishes and also calls `close(out)`, it panics with `close of closed channel`. Worse, any goroutine still doing `out <- v` after the first close panics with `send on closed channel`. So this races between several illegal operations.

**Fix — close `out` exactly once, after *all* producers are done, using a `sync.WaitGroup`:**

```go
func merge(chs []<-chan int) <-chan int {
	out := make(chan int)
	var wg sync.WaitGroup
	wg.Add(len(chs))
	for _, ch := range chs {
		go func(c <-chan int) {
			defer wg.Done()
			for v := range c {
				out <- v
			}
		}(ch)
	}
	// A single closer goroutine waits for all producers, then closes once.
	go func() {
		wg.Wait()
		close(out)
	}()
	return out
}
```

The pattern: each producer only *sends* (never closes); one dedicated goroutine `wg.Wait()`s for all of them and performs the single `close(out)`. The rules this enforces — *only the sender closes, exactly once, and only when no more sends will happen* — are exactly what the buggy version violated.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test for this generic, error-short-circuiting map, covering both the success and first-error paths:\n\n```go\nfunc MapErr[T, U any](s []T, f func(T) (U, error)) ([]U, error) { /* ... */ }\n```",
        "response": '''```go
func TestMapErr(t *testing.T) {
	t.Run("all succeed", func(t *testing.T) {
		got, err := MapErr([]string{"1", "2", "3"}, strconv.Atoi)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !slices.Equal(got, []int{1, 2, 3}) {
			t.Errorf("got %v, want [1 2 3]", got)
		}
	})

	t.Run("stops at first error", func(t *testing.T) {
		got, err := MapErr([]string{"1", "x", "3"}, strconv.Atoi)
		if err == nil {
			t.Fatal("expected an error, got nil")
		}
		if got != nil {
			t.Errorf("on error, result should be nil, got %v", got)
		}
		// The error should identify the failing index (1).
		if !strings.Contains(err.Error(), "index 1") {
			t.Errorf("error %q, want it to mention index 1", err.Error())
		}
	})
}
```

The success subtest checks the mapped values with `slices.Equal`. The failure subtest verifies the three parts of the short-circuit contract: an error is returned, the result slice is `nil` (not a partially-filled slice), and the error pinpoints *which* element failed (`index 1`). Testing that the result is nil on error is important — it documents that callers shouldn't use the output when `err != nil`.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test verifying that a custom error type's Is method makes errors.Is match by code (even through wrapping), for:\n\n```go\ntype StatusError struct{ Code int }\nfunc (e StatusError) Error() string { return fmt.Sprintf(\"status %d\", e.Code) }\nfunc (e StatusError) Is(target error) bool {\n\tt, ok := target.(StatusError); return ok && t.Code == e.Code\n}\n```",
        "response": '''```go
func TestStatusErrorIs(t *testing.T) {
	// Wrap so we also prove Is works through the %w chain.
	err := fmt.Errorf("request failed: %w", StatusError{Code: 404})

	tests := []struct {
		name   string
		target error
		want   bool
	}{
		{"same code matches", StatusError{Code: 404}, true},
		{"different code does not", StatusError{Code: 500}, false},
		{"unrelated error does not", errors.New("boom"), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := errors.Is(err, tt.target); got != tt.want {
				t.Errorf("errors.Is(err, %v) = %v, want %v", tt.target, got, tt.want)
			}
		})
	}
}
```

This proves the custom `Is` method does its job: a `StatusError` with the same `Code` matches even though `err` is a *different* wrapped value (so plain identity comparison would fail), a different code does not match, and an unrelated error type does not match. The "different code" case is the crucial one — it confirms `Is` actually compares `Code` rather than matching any `StatusError`. Testing through `fmt.Errorf("...: %w", ...)` also verifies that `errors.Is` unwraps to reach the custom matcher.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain Go's exported vs unexported identifiers and the special init() function, using this snippet:\n\n```go\npackage store\n\nvar registry = map[string]int{}\n\nfunc init() { registry[\"default\"] = 1 }\n\nfunc Count() int { return len(registry) }\n```",
        "response": '''Two Go fundamentals are at play here: **visibility by capitalization** and the **`init` function**.

**Exported vs unexported (the case rule).** Go has no `public`/`private` keywords. Instead, an identifier's *first letter* decides its visibility across package boundaries:
- **Capitalized** = exported: visible to code that imports the package. Here `Count` is exported, so another package can call `store.Count()`.
- **lowercase** = unexported: visible only *within* its own package. `registry` and `init` are lowercase, so outside `store` nobody can touch the map directly — they must go through `Count()` (or other exported functions). This is how Go does encapsulation: expose a small capitalized API, keep the implementation lowercase. The rule applies to every identifier — types, functions, struct fields, methods, constants, variables. (A struct field must be exported for `encoding/json` and reflection to see it, which is why JSON-mapped fields are capitalized.)

**The `init` function.** `init` is special:
- It takes no arguments and returns nothing, and you never call it yourself — the Go runtime calls it automatically.
- It runs **once**, after all package-level variables are initialized, and **before `main` starts**. So by the time any exported function runs, `registry` already contains `"default"`.
- A file (or package) may have **multiple** `init` functions; they run in the order they're declared, and a package's `init`s run after the `init`s of every package it imports. This gives a deterministic startup order across the whole import graph.
- Use it for one-time setup that can't be a simple variable initializer: registering drivers (`database/sql`), validating configuration, building lookup tables, compiling regexes into package vars.

Caveats: keep `init` light and side-effect-light — heavy or failure-prone work hidden in `init` makes packages surprising to import and hard to test (you can't easily skip it). Prefer explicit constructors/`Setup()` functions when initialization can fail or needs parameters; reserve `init` for genuinely automatic, can't-fail wiring.''',
    },
]
