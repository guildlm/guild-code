# -*- coding: utf-8 -*-
"""Batch 15 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that removes consecutive duplicate elements from a slice using slices.Compact, and print the result (noting it only removes adjacent duplicates).",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	s := []int{1, 1, 2, 3, 3, 3, 4, 1}

	// Compact removes only *consecutive* duplicates (sort first to dedupe fully).
	s = slices.Compact(s)
	fmt.Println(s) // [1 2 3 4 1]  -- the trailing 1 stays (not adjacent to the first)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic GroupBy[T any, K comparable](s []T, key func(T) K) map[K][]T that partitions a slice by a key function. Group numbers into 'even'/'odd' and print each group sorted.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// GroupBy partitions s into buckets keyed by key(element).
func GroupBy[T any, K comparable](s []T, key func(T) K) map[K][]T {
	groups := map[K][]T{}
	for _, v := range s {
		k := key(v)
		groups[k] = append(groups[k], v)
	}
	return groups
}

func main() {
	nums := []int{1, 2, 3, 4, 5, 6}
	byParity := GroupBy(nums, func(n int) string {
		if n%2 == 0 {
			return "even"
		}
		return "odd"
	})

	for _, k := range []string{"even", "odd"} {
		sort.Ints(byParity[k])
		fmt.Printf("%s: %v\\n", k, byParity[k])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that shuffles a slice in place reproducibly using a seeded math/rand source and rand.Shuffle. Print the shuffled slice.",
        "response": '''```go
package main

import (
	"fmt"
	"math/rand"
)

func main() {
	r := rand.New(rand.NewSource(7)) // seeded -> deterministic order

	deck := []int{1, 2, 3, 4, 5}
	r.Shuffle(len(deck), func(i, j int) {
		deck[i], deck[j] = deck[j], deck[i]
	})
	fmt.Println(deck)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic ToMap[T any, K comparable](s []T, key func(T) K) map[K]T that indexes a slice of structs by a key field. Index users by ID and look one up.",
        "response": '''```go
package main

import "fmt"

type User struct {
	ID   int
	Name string
}

// ToMap indexes s by key(element). On duplicate keys, the last element wins.
func ToMap[T any, K comparable](s []T, key func(T) K) map[K]T {
	m := make(map[K]T, len(s))
	for _, v := range s {
		m[key(v)] = v
	}
	return m
}

func main() {
	users := []User{{ID: 1, Name: "Ada"}, {ID: 2, Name: "Tim"}}
	byID := ToMap(users, func(u User) int { return u.ID })

	fmt.Println("user 2 is", byID[2].Name) // Tim
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that computes the digital root of an integer recursively (repeatedly sum the digits until a single digit remains). Print digitalRoot(9875).",
        "response": '''```go
package main

import "fmt"

// digitalRoot repeatedly sums the decimal digits of n until one digit remains.
func digitalRoot(n int) int {
	if n < 10 {
		return n
	}
	sum := 0
	for n > 0 {
		sum += n % 10
		n /= 10
	}
	return digitalRoot(sum)
}

func main() {
	// 9+8+7+5 = 29 -> 2+9 = 11 -> 1+1 = 2
	fmt.Println(digitalRoot(9875)) // 2
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating method 'overriding' via struct embedding: a base type with a Name method, embedded in a derived type that defines its own Name, showing both the promoted-and-shadowed and the explicit base call.",
        "response": '''```go
package main

import "fmt"

type base struct{}

func (base) Name() string { return "base" }

// derived embeds base but defines its own Name, shadowing the promoted one.
type derived struct {
	base
}

func (derived) Name() string { return "derived" }

func main() {
	d := derived{}
	fmt.Println(d.Name())      // derived  -- the outer method shadows base.Name
	fmt.Println(d.base.Name()) // base     -- still reachable explicitly
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that implements ROT13 using strings.Map with a rune-transforming function, and print the encoding of 'Hello'.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

func main() {
	// strings.Map applies a per-rune transform; returning the rune unchanged
	// leaves non-letters alone.
	rot13 := func(r rune) rune {
		switch {
		case r >= 'a' && r <= 'z':
			return 'a' + (r-'a'+13)%26
		case r >= 'A' && r <= 'Z':
			return 'A' + (r-'A'+13)%26
		}
		return r
	}

	fmt.Println(strings.Map(rot13, "Hello, World")) // Uryyb, Jbeyq
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing a request/response pattern over channels: a server goroutine reads requests carrying a reply channel and sends back the square. main sends one request and prints the reply.",
        "response": '''```go
package main

import "fmt"

// request carries an input plus the channel the reply should be sent on.
type request struct {
	n     int
	reply chan int
}

func main() {
	requests := make(chan request)

	go func() { // server: handle requests until the channel closes
		for req := range requests {
			req.reply <- req.n * req.n
		}
	}()

	reply := make(chan int)
	requests <- request{n: 7, reply: reply}
	fmt.Println("7^2 =", <-reply) // 49

	close(requests)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that builds a 3x4 grid as a [][]int, filling each cell with row*cols+col, and prints the grid row by row.",
        "response": '''```go
package main

import "fmt"

func main() {
	const rows, cols = 3, 4

	grid := make([][]int, rows)
	for i := range grid {
		grid[i] = make([]int, cols) // each row needs its own backing slice
		for j := range grid[i] {
			grid[i][j] = i*cols + j
		}
	}

	for _, row := range grid {
		fmt.Println(row)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that starts a time.NewTimer and stops it before it fires, reporting whether the stop succeeded. Use a goroutine that stops the timer early.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	timer := time.NewTimer(50 * time.Millisecond)
	done := make(chan struct{})

	go func() {
		time.Sleep(20 * time.Millisecond)
		// Stop returns true if it stopped the timer before it fired.
		if timer.Stop() {
			fmt.Println("timer stopped before firing")
		} else {
			fmt.Println("timer had already fired")
		}
		close(done)
	}()

	<-done
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; the counts never change. Explain the range-copy bug and fix:\n\n```go\ntype Item struct{ Count int }\n\nfunc incrementAll(items []Item) {\n\tfor _, it := range items {\n\t\tit.Count++\n\t}\n}\n```",
        "response": '''**Bug: `range` yields a copy of each element.** In `for _, it := range items`, `it` is a *copy* of `items[i]`, not the element itself. `it.Count++` increments the copy, which is discarded at the end of the iteration — the slice's actual elements are never touched. After the call, every `Count` is unchanged.

**Fix — mutate through the index:**

```go
func incrementAll(items []Item) {
	for i := range items {
		items[i].Count++ // addresses the real element
	}
}
```

Indexing with `items[i]` refers to the element in the backing array, so the increment persists. (Alternatively, a slice of pointers `[]*Item` would let `it.Count++` work because each `it` is a pointer to the original — but for value structs, index access is simpler and avoids the extra indirection.) The rule: to modify slice elements in place, range over the **index** (`for i := range s { s[i]... }`), not the value copy. The two-value form `for _, v := range s` is for *reading* elements, not writing them.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go method; the second call deadlocks. Explain why and fix:\n\n```go\nfunc (c *Cache) Get(k string) (int, bool) {\n\tc.mu.Lock()\n\tv, ok := c.m[k]\n\tif !ok {\n\t\treturn 0, false\n\t}\n\tc.mu.Unlock()\n\treturn v, true\n}\n```",
        "response": '''**Bug: the early-return path never unlocks the mutex.** When the key is missing, the function returns at `return 0, false` *without* calling `c.mu.Unlock()`. The mutex stays locked forever, so the next call that tries `c.mu.Lock()` blocks indefinitely — a deadlock. Only the found-path unlocks, so the bug shows up specifically after a cache miss.

**Fix — `defer` the unlock right after locking, so every return path releases it:**

```go
func (c *Cache) Get(k string) (int, bool) {
	c.mu.Lock()
	defer c.mu.Unlock() // runs on every return, found or not
	v, ok := c.m[k]
	return v, ok
}
```

`defer c.mu.Unlock()` placed immediately after `Lock()` is the idiomatic pattern precisely because it's robust to multiple return statements, early returns, and panics — the unlock can't be skipped. Manually pairing `Lock`/`Unlock` is error-prone the moment a function grows more than one exit. (Here the logic also simplifies, since `v, ok := c.m[k]` already returns the right zero value on a miss.)''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it pins a CPU core at 100% and has a data race. Explain and fix:\n\n```go\nfunc waitFor(done *bool) {\n\tfor !*done {\n\t\t// busy spin until done\n\t}\n}\n```",
        "response": '''**Two problems:**

1. **Busy-wait burns a CPU.** The `for !*done {}` loop spins as fast as the core can run, doing no useful work and consuming 100% of a CPU until the flag flips. It also starves other goroutines on that thread.
2. **Data race on `*done`.** One goroutine reads `*done` in a tight loop while another writes it, with no synchronization. That's a data race (`go test -race` flags it); without a memory barrier the reader may *never* observe the write, so the loop can spin forever even after `done` is set.

**Fix — signal completion with a channel, which both blocks efficiently and synchronizes memory:**

```go
func waitFor(done <-chan struct{}) {
	<-done // parks the goroutine until the channel is closed/sent
}

// producer:
done := make(chan struct{})
go func() {
	// ... work ...
	close(done) // wakes every receiver, with a proper happens-before edge
}()
waitFor(done)
```

Receiving from a channel parks the goroutine (zero CPU while waiting) and establishes a happens-before relationship, so the waiter is guaranteed to see all writes made before the `close`. If you specifically need a boolean flag rather than a one-shot signal, use `sync.WaitGroup` for "wait for N tasks," or `atomic.Bool` with `Load`/`Store` for a properly synchronized flag — but a channel is usually the clearest tool. Never coordinate goroutines with an unsynchronized shared variable in a spin loop.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test for this generic GroupBy, checking that elements are partitioned correctly:\n\n```go\nfunc GroupBy[T any, K comparable](s []T, key func(T) K) map[K][]T { /* ... */ }\n```",
        "response": '''```go
func TestGroupBy(t *testing.T) {
	nums := []int{1, 2, 3, 4, 5, 6}

	got := GroupBy(nums, func(n int) string {
		if n%2 == 0 {
			return "even"
		}
		return "odd"
	})

	want := map[string][]int{
		"odd":  {1, 3, 5},
		"even": {2, 4, 6},
	}

	if len(got) != len(want) {
		t.Fatalf("got %d groups, want %d", len(got), len(want))
	}
	for k, wantVals := range want {
		if !slices.Equal(got[k], wantVals) {
			t.Errorf("group %q = %v, want %v", k, got[k], wantVals)
		}
	}
}
```

Because `GroupBy` appends in input order, each bucket preserves the relative order of the source slice, so the expected `odd`/`even` slices are exactly `{1,3,5}`/`{2,4,6}` and can be compared with `slices.Equal`. The test checks both the number of groups and the contents of each. (If `GroupBy` made no ordering guarantee, you'd sort each bucket before comparing, or compare as multisets — but here in-order append is part of the observable behavior worth pinning.)''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a table-driven test for this recursive digital-root function:\n\n```go\n// DigitalRoot repeatedly sums digits until a single digit remains.\nfunc DigitalRoot(n int) int { /* ... */ }\n```",
        "response": '''```go
func TestDigitalRoot(t *testing.T) {
	tests := []struct {
		in   int
		want int
	}{
		{0, 0},
		{5, 5},        // already single digit
		{10, 1},       // 1+0
		{99, 9},       // 9+9=18 -> 1+8=9
		{9875, 2},     // 29 -> 11 -> 2
		{123456, 3},   // 21 -> 3
	}

	for _, tt := range tests {
		t.Run(fmt.Sprintf("%d", tt.in), func(t *testing.T) {
			if got := DigitalRoot(tt.in); got != tt.want {
				t.Errorf("DigitalRoot(%d) = %d, want %d", tt.in, got, tt.want)
			}
		})
	}
}
```

The cases exercise the base case (single-digit inputs return themselves, including `0`), one round of summing (`10 -> 1`), and multi-round reductions (`9875` needs three passes). Using `fmt.Sprintf("%d", tt.in)` as the subtest name makes each case individually addressable with `go test -run TestDigitalRoot/9875`. Recursive numeric functions like this are well suited to table tests: each row is a tiny, independent property of the form input→output, and the base case is the row most likely to be wrong.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain how Go uses composition (struct embedding) instead of inheritance, using this snippet:\n\n```go\ntype Logger struct{ prefix string }\nfunc (l Logger) Log(msg string) { fmt.Println(l.prefix, msg) }\n\ntype Service struct {\n\tLogger\n\tname string\n}\n```",
        "response": '''Go has **no inheritance** — no classes, no `extends`, no subtype hierarchy. Instead it offers **composition via embedding**: you put one type inside another as an unnamed field, and its fields and methods are **promoted** to the outer type.

In the snippet, `Service` embeds `Logger` (the field has a type but no name). Because of promotion:
- You can call `svc.Log("hi")` directly — even though `Log` is defined on `Logger`, it's promoted onto `Service`, so it reads as if `Service` "has" a `Log` method.
- You can also reach the embedded value explicitly as `svc.Logger`, and access its field `svc.Logger.prefix` (promoted to `svc.prefix` too, if unambiguous).

How this differs from inheritance:
- **"Has-a", not "is-a".** `Service` *contains* a `Logger`; it is **not** a subtype of `Logger`. A `*Service` does not substitute for a `*Logger` in a type sense. Promotion is a syntactic convenience (method forwarding), not subtyping.
- **No virtual dispatch / overriding.** If `Service` defines its own `Log`, it *shadows* the promoted one for calls on `Service`, but `Logger`'s own methods still call `Logger`'s `Log` — there's no dynamic dispatch back into the "subclass." Embedding forwards calls; it doesn't create a vtable. (This is why the earlier "override" example only shadows, and the base method is still reachable as `svc.Logger.Log`.)
- **Interfaces provide the polymorphism.** Where other languages use base classes for polymorphism, Go uses **interfaces**, satisfied implicitly. If `Service` should be usable wherever something `Loggable` is expected, you define a small interface and let `Service` satisfy it (often *via* the promoted method) — composition for code reuse, interfaces for substitutability.

Why Go favors this: composition avoids the fragile deep hierarchies and tight coupling of inheritance. You assemble behavior by embedding small, focused types (a `sync.Mutex`, an `io.Reader`, a `Logger`) and expose capabilities through interfaces. The guideline "**accept interfaces, embed/return concrete types**" follows directly: embed to reuse implementation, and depend on interfaces to stay flexible.''',
    },
]
