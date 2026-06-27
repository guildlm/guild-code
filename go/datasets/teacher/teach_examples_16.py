# -*- coding: utf-8 -*-
"""Batch 16 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that parses CSV data (with a header row) from an in-memory string using encoding/csv, skipping the header and printing each record.",
        "response": '''```go
package main

import (
	"encoding/csv"
	"fmt"
	"strings"
)

func main() {
	data := "name,age\\nAda,36\\nTim,15"

	r := csv.NewReader(strings.NewReader(data))
	records, err := r.ReadAll()
	if err != nil {
		fmt.Println("csv error:", err)
		return
	}

	for _, rec := range records[1:] { // records[0] is the header
		fmt.Printf("%s is %s\\n", rec[0], rec[1])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining a generic Set[T comparable] with a constructor and an Intersect method, then print the sorted intersection of two int sets.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

type Set[T comparable] map[T]struct{}

func NewSet[T comparable](items ...T) Set[T] {
	s := make(Set[T], len(items))
	for _, it := range items {
		s[it] = struct{}{}
	}
	return s
}

// Intersect returns a new set of the elements present in both s and o.
func (s Set[T]) Intersect(o Set[T]) Set[T] {
	out := make(Set[T])
	for k := range s {
		if _, ok := o[k]; ok {
			out[k] = struct{}{}
		}
	}
	return out
}

func main() {
	a := NewSet(1, 2, 3, 4)
	b := NewSet(3, 4, 5)

	common := a.Intersect(b)
	keys := make([]int, 0, len(common))
	for k := range common {
		keys = append(keys, k)
	}
	sort.Ints(keys)
	fmt.Println("intersection:", keys) // [3 4]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing merge sort recursively (split, sort halves, merge). Sort and print a sample slice.",
        "response": '''```go
package main

import "fmt"

func mergeSort(s []int) []int {
	if len(s) <= 1 {
		return s
	}
	mid := len(s) / 2
	left := mergeSort(s[:mid])
	right := mergeSort(s[mid:])
	return merge(left, right)
}

// merge combines two sorted slices into one sorted slice.
func merge(a, b []int) []int {
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
	out = append(out, a[i:]...)
	out = append(out, b[j:]...)
	return out
}

func main() {
	fmt.Println(mergeSort([]int{5, 2, 8, 1, 9, 3})) // [1 2 3 5 8 9]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses context.WithDeadline to bound an operation; the operation takes longer than the deadline, so the program should report the deadline error.",
        "response": '''```go
package main

import (
	"context"
	"fmt"
	"time"
)

func main() {
	deadline := time.Now().Add(30 * time.Millisecond)
	ctx, cancel := context.WithDeadline(context.Background(), deadline)
	defer cancel()

	select {
	case <-time.After(100 * time.Millisecond): // the "work" takes 100ms
		fmt.Println("work completed")
	case <-ctx.Done():
		fmt.Println("deadline hit:", ctx.Err()) // context deadline exceeded
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that parses a float with strconv.ParseFloat and formats it back with strconv.FormatFloat in both fixed-point (2 decimals) and scientific notation.",
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
)

func main() {
	f, err := strconv.ParseFloat("3.14159", 64)
	if err != nil {
		fmt.Println("parse error:", err)
		return
	}

	fmt.Println("parsed:    ", f)
	fmt.Println("2 decimals:", strconv.FormatFloat(f, 'f', 2, 64)) // 3.14
	fmt.Println("scientific:", strconv.FormatFloat(f, 'e', 3, 64)) // 3.142e+00
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic SortedKeys[K cmp.Ordered, V any](m map[K]V) []K helper that returns a map's keys in sorted order, and use it to print a map deterministically.",
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
	"slices"
)

// SortedKeys returns m's keys sorted ascending -- handy for deterministic
// iteration, since ranging a map is randomized.
func SortedKeys[K cmp.Ordered, V any](m map[K]V) []K {
	keys := make([]K, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	return keys
}

func main() {
	m := map[string]int{"banana": 2, "apple": 1, "cherry": 3}
	for _, k := range SortedKeys(m) {
		fmt.Printf("%s=%d\\n", k, m[k])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses an atomic.Bool as a one-shot ready flag set by a goroutine and read by main after synchronization. Print the flag.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

func main() {
	var ready atomic.Bool // race-free boolean flag

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		// ... perform setup ...
		ready.Store(true)
	}()
	wg.Wait()

	fmt.Println("ready:", ready.Load())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating string trimming with strings.TrimPrefix, strings.TrimRight, and strings.TrimFunc, printing each result.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
	"unicode"
)

func main() {
	s := "***Hello, World!!!"

	fmt.Println(strings.TrimPrefix(s, "***")) // Hello, World!!!
	fmt.Println(strings.TrimRight(s, "!"))    // ***Hello, World

	// TrimFunc strips leading/trailing runes for which the predicate is true.
	trimmed := strings.TrimFunc(s, func(r rune) bool {
		return !unicode.IsLetter(r) && r != ',' && r != ' '
	})
	fmt.Println(trimmed) // Hello, World
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that wraps two sentinel errors at once with fmt.Errorf using multiple %w verbs (Go 1.20+), and shows errors.Is finding both.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

var (
	errValidation = errors.New("validation failed")
	errDatabase   = errors.New("database unavailable")
)

func main() {
	// Since Go 1.20, fmt.Errorf accepts multiple %w verbs.
	err := fmt.Errorf("save failed: %w; also %w", errValidation, errDatabase)

	fmt.Println(err)
	fmt.Println("is validation:", errors.Is(err, errValidation))
	fmt.Println("is database:  ", errors.Is(err, errDatabase))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that performs an iterative depth-first traversal of a directed graph using an explicit stack, returning the visitation order from a start node. Print the order.",
        "response": '''```go
package main

import "fmt"

// dfs returns nodes in depth-first visitation order using an explicit stack.
func dfs(graph map[int][]int, start int) []int {
	visited := map[int]bool{}
	stack := []int{start}
	var order []int

	for len(stack) > 0 {
		n := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if visited[n] {
			continue
		}
		visited[n] = true
		order = append(order, n)

		// Push neighbors in reverse so the smallest is processed first.
		neighbors := graph[n]
		for i := len(neighbors) - 1; i >= 0; i-- {
			if !visited[neighbors[i]] {
				stack = append(stack, neighbors[i])
			}
		}
	}
	return order
}

func main() {
	graph := map[int][]int{1: {2, 3}, 2: {4}, 3: {4}, 4: {}}
	fmt.Println(dfs(graph, 1)) // [1 2 4 3]
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it panics with a nil pointer dereference at the end of the list. Explain the missing base case and fix:\n\n```go\ntype Node struct {\n\tVal  int\n\tNext *Node\n}\n\nfunc (n *Node) Sum() int {\n\treturn n.Val + n.Next.Sum()\n}\n```",
        "response": '''**Bug: the recursion has no base case for the end of the list.** Each call does `n.Next.Sum()`, but the last node's `Next` is `nil`. Calling `Sum()` on a `nil *Node` then dereferences `n.Val` inside the method on a nil receiver, panicking with an invalid-memory / nil-pointer dereference. The recursion never stops at the tail.

**Fix — handle the nil receiver as the base case:**

```go
func (n *Node) Sum() int {
	if n == nil {
		return 0 // empty list / past the tail contributes nothing
	}
	return n.Val + n.Next.Sum()
}
```

A subtle but useful Go detail: it's legal to call a pointer-receiver method on a `nil` pointer — the method runs with `n == nil`, and as long as it checks for that before dereferencing, nothing panics. So putting the `if n == nil` guard at the top of `Sum` cleanly terminates the recursion when `Next` is nil. This "nil receiver is a valid empty case" pattern is common for recursive linked structures (lists, trees): the base case is `n == nil`, and every method that walks `Next`/`Left`/`Right` should start by checking it.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it doesn't compile. Explain why you can't modify a struct field through a map, and give two fixes:\n\n```go\ntype Counter struct{ N int }\n\nfunc tally(words []string) map[string]Counter {\n\tm := map[string]Counter{}\n\tfor _, w := range words {\n\t\tm[w].N++\n\t}\n\treturn m\n}\n```",
        "response": '''**Why it fails: map values are not addressable.** `m[w]` returns a *copy* of the stored `Counter`, and Go won't let you assign to a field of a non-addressable value — so `m[w].N++` is a compile error: `cannot assign to struct field m[w].N in map`. (If it *were* allowed, you'd be mutating a throwaway copy, which is exactly the trap the language prevents.)

**Fix A — store pointers, which *are* addressable through the map:**

```go
func tally(words []string) map[string]*Counter {
	m := map[string]*Counter{}
	for _, w := range words {
		c, ok := m[w]
		if !ok {
			c = &Counter{}
			m[w] = c
		}
		c.N++
	}
	return m
}
```

**Fix B — read, modify, write the whole struct back:**

```go
func tally(words []string) map[string]Counter {
	m := map[string]Counter{}
	for _, w := range words {
		c := m[w] // copy (zero value if absent)
		c.N++
		m[w] = c // store the updated copy
	}
	return m
}
```

If the only field is a count, the simplest answer is `map[string]int` with `m[w]++`, which works because the *whole value* is replaced (you're not modifying a field of a copy). Use Fix A (pointer values) when the struct is large or you want callers to share/mutate the same instance; use Fix B (read-modify-write) when you want value semantics. The rule: you can replace a whole map value (`m[k] = v`), but you cannot assign to a field of a struct value held in a map.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; on older Go versions every goroutine fetches the same URL. Explain the loop-variable capture and give a version-safe fix:\n\n```go\nfunc fetchAll(urls []string) {\n\tvar wg sync.WaitGroup\n\tfor _, url := range urls {\n\t\twg.Add(1)\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\t\t\tfetch(url)\n\t\t}()\n\t}\n\twg.Wait()\n}\n```",
        "response": '''**Bug: the goroutine closure captures the loop variable `url` by reference.** Before Go 1.22, `url` is a single variable reused across iterations. The goroutines start asynchronously and read `url` *later* — by which time the loop has advanced (or finished), so most or all of them observe the **last** URL. You end up fetching the final URL several times and missing others.

Go 1.22+ changed range loops to create a fresh `url` per iteration, so this exact code is correct there. But it's still flagged by linters, breaks on older toolchains, and relying on the version is fragile.

**Version-safe fixes:**

```go
// 1. Pass the value as an argument (bound at call time):
for _, url := range urls {
	wg.Add(1)
	go func(url string) {
		defer wg.Done()
		fetch(url)
	}(url)
}

// 2. Or shadow with a per-iteration copy:
for _, url := range urls {
	url := url
	wg.Add(1)
	go func() {
		defer wg.Done()
		fetch(url)
	}()
}
```

Both give each goroutine its own `url`. Option 1 (argument) is the most explicit and is my preference for goroutines, because the value is captured exactly where `go` is written. This is the single most common Go concurrency bug; whenever you launch a goroutine inside a loop, make sure each one captures its own copy of the loop variables (and run `go vet`/`go test -race`, which help catch it).''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a property-style Go test for merge sort, asserting the output is sorted and is a permutation of the input:\n\n```go\n// MergeSort returns a sorted copy of s.\nfunc MergeSort(s []int) []int { /* ... */ }\n```",
        "response": '''```go
func TestMergeSort(t *testing.T) {
	inputs := [][]int{
		nil,
		{1},
		{2, 1},
		{5, 2, 8, 1, 9, 3},
		{4, 4, 4, 1},
		{-3, 0, -1, 2, -3},
	}

	for _, in := range inputs {
		got := MergeSort(in)

		if !sort.IntsAreSorted(got) {
			t.Errorf("MergeSort(%v) = %v, not sorted", in, got)
		}
		if !sameMultiset(in, got) {
			t.Errorf("MergeSort(%v) = %v, not a permutation of input", in, got)
		}
	}
}

// sameMultiset reports whether a and b contain the same elements with the same
// counts (order-independent).
func sameMultiset(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	counts := map[int]int{}
	for _, v := range a {
		counts[v]++
	}
	for _, v := range b {
		counts[v]--
	}
	for _, c := range counts {
		if c != 0 {
			return false
		}
	}
	return true
}
```

Like any sort, correctness has two properties worth checking directly rather than hard-coding expected outputs: the result is **ordered** (`sort.IntsAreSorted`) and it's a **permutation** of the input — same elements, same multiplicities (`sameMultiset`). The multiset check catches a sort that silently drops or duplicates elements, which an "is it sorted?" check alone would miss. The cases include the empty and single-element base cases, duplicates, and negatives.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test for a generic Set's Intersect method:\n\n```go\ntype Set[T comparable] map[T]struct{}\nfunc NewSet[T comparable](items ...T) Set[T] { /* ... */ }\nfunc (s Set[T]) Intersect(o Set[T]) Set[T] { /* ... */ }\n```",
        "response": '''```go
// toSorted is a small helper to compare sets order-independently.
func toSorted(s Set[int]) []int {
	out := make([]int, 0, len(s))
	for k := range s {
		out = append(out, k)
	}
	sort.Ints(out)
	return out
}

func TestSetIntersect(t *testing.T) {
	tests := []struct {
		name string
		a, b Set[int]
		want []int
	}{
		{"overlap", NewSet(1, 2, 3, 4), NewSet(3, 4, 5), []int{3, 4}},
		{"disjoint", NewSet(1, 2), NewSet(3, 4), []int{}},
		{"identical", NewSet(1, 2), NewSet(1, 2), []int{1, 2}},
		{"empty operand", NewSet(1, 2), NewSet[int](), []int{}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := toSorted(tt.a.Intersect(tt.b))
			if !slices.Equal(got, tt.want) {
				t.Errorf("Intersect = %v, want %v", got, tt.want)
			}
		})
	}
}
```

Because a set has no inherent order, the test converts the result to a sorted slice (`toSorted`) before comparing with `slices.Equal` — comparing sets directly by iteration order would be flaky. The cases pin the meaningful behaviors: partial overlap, fully disjoint sets (empty result), identical sets (result equals input), and intersection with an empty set (empty result). The disjoint and empty cases use `[]int{}` to assert the result has no elements.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain Go's memory model and 'happens-before' at a practical level — why data races are a bug and how channels/mutexes fix them — using this racy snippet:\n\n```go\nvar done bool\nvar result int\ngo func() { result = 42; done = true }()\nfor !done { }\nfmt.Println(result)\n```",
        "response": '''This snippet has a **data race** and is broken, even though it looks like it should print `42`.

**What the memory model guarantees (and doesn't).** Go's memory model defines when a read is guaranteed to observe a particular write, via a **happens-before** relationship. Within a single goroutine, statements happen-before in program order. But **across goroutines**, one goroutine's writes are only guaranteed visible to another if there's an explicit synchronization event connecting them (channel op, mutex, `sync/atomic`, `WaitGroup`, etc.). Without that, the compiler and CPU are free to reorder, cache, or never-propagate the writes — there is *no* guarantee about ordering or visibility.

**Why the snippet is wrong on two counts:**
1. **The race itself is undefined behavior.** One goroutine writes `done`/`result` while `main` reads `done` in the spin loop, with no synchronization. The Go spec says a program with a data race has undefined behavior for those accesses — `go run -race` will report it.
2. **It may hang or print 0.** Because there's no happens-before edge, `main` may never observe `done` becoming `true` (it could read a cached `false` forever), or it may see `done == true` *before* it sees `result == 42` (the writes can be observed out of order). So the loop can spin forever, or print `0`.

**The fix is to introduce a happens-before edge.** A channel does this cleanly:

```go
done := make(chan struct{})
var result int
go func() {
	result = 42
	close(done) // everything before this is visible to a receiver after it
}()
<-done            // receiving establishes happens-before
fmt.Println(result) // guaranteed 42
```

The send/close *happens-before* the corresponding receive, and within the goroutine `result = 42` happens-before the `close`. By transitivity, `result = 42` happens-before the `fmt.Println` — so `42` is guaranteed and visible. A `sync.Mutex` (unlock happens-before the next lock), `sync.WaitGroup` (`Done` happens-before `Wait` returns), or `sync/atomic` give the same kind of guarantee.

**Practical takeaways:** never coordinate goroutines through plain shared variables; use a channel, mutex, `WaitGroup`, or atomics. Don't assume "it printed 42 on my machine" means it's correct — races are timing- and hardware-dependent. And make `-race` part of your test runs (`go test -race`), since it's the most reliable way to catch these.''',
    },
]
