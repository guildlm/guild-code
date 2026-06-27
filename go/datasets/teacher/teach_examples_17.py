# -*- coding: utf-8 -*-
"""Batch 17 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that computes a large factorial (25!) using math/big to avoid integer overflow, and print the exact result.",
        "response": '''```go
package main

import (
	"fmt"
	"math/big"
)

// factorial computes n! exactly using arbitrary-precision integers.
func factorial(n int) *big.Int {
	result := big.NewInt(1)
	for i := int64(2); i <= int64(n); i++ {
		result.Mul(result, big.NewInt(i)) // result *= i, in place
	}
	return result
}

func main() {
	// 25! overflows int64; big.Int holds it exactly.
	fmt.Println("25! =", factorial(25))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that removes all even numbers from a slice in place using slices.DeleteFunc (Go 1.21+), and print the result.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	nums := []int{1, 2, 3, 4, 5, 6}

	// DeleteFunc removes every element for which the predicate is true,
	// compacting the slice in place.
	nums = slices.DeleteFunc(nums, func(n int) bool { return n%2 == 0 })
	fmt.Println(nums) // [1 3 5]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that converts a fixed UTC time into another time zone with time.LoadLocation and Time.In, printing both formatted with the zone abbreviation. Handle the load error.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	t := time.Date(2026, time.June, 27, 16, 0, 0, 0, time.UTC)

	loc, err := time.LoadLocation("America/New_York")
	if err != nil {
		fmt.Println("could not load zone:", err)
		return
	}

	fmt.Println("UTC:", t.Format("2006-01-02 15:04 MST"))
	fmt.Println("NY: ", t.In(loc).Format("2006-01-02 15:04 MST"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that decodes JSON using json.Decoder with UseNumber so large integers keep full precision (decoded as json.Number rather than float64). Read an int and a float back.",
        "response": '''```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
)

func main() {
	data := `{"big": 123456789012345678, "price": 9.99}`

	dec := json.NewDecoder(bytes.NewReader([]byte(data)))
	dec.UseNumber() // keep numbers as json.Number, avoiding float64 precision loss

	var m map[string]json.Number
	if err := dec.Decode(&m); err != nil {
		fmt.Println("decode error:", err)
		return
	}

	big, _ := m["big"].Int64()
	price, _ := m["price"].Float64()
	fmt.Println("big:  ", big)   // exact, not rounded to a float
	fmt.Println("price:", price)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating sync.Cond: a consumer goroutine Waits until an item is available in a shared queue, and a producer appends an item and Signals. Print the consumed item.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var mu sync.Mutex
	cond := sync.NewCond(&mu)
	var queue []int
	done := make(chan struct{})

	go func() { // consumer
		mu.Lock()
		for len(queue) == 0 {
			cond.Wait() // atomically unlocks, blocks, re-locks on wake
		}
		item := queue[0]
		queue = queue[1:]
		mu.Unlock()
		fmt.Println("consumed:", item)
		close(done)
	}()

	mu.Lock() // producer
	queue = append(queue, 42)
	mu.Unlock()
	cond.Signal() // wake one waiter

	<-done
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that demonstrates the difference between a method value (bound to a receiver) and a method expression (receiver passed explicitly), using a Calc type.",
        "response": '''```go
package main

import "fmt"

type Calc struct{ base int }

func (c Calc) Add(x int) int { return c.base + x }

func main() {
	c := Calc{base: 10}

	// Method value: c is captured now; call it like a plain func(int) int.
	add := c.Add
	fmt.Println(add(5)) // 15

	// Method expression: receiver is an explicit first argument.
	addExpr := Calc.Add
	fmt.Println(addExpr(c, 7)) // 17
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that solves the Towers of Hanoi recursively, collecting the moves, and prints how many moves were made for 3 disks plus the first and last move.",
        "response": '''```go
package main

import "fmt"

// hanoi records the moves to transfer n disks from `from` to `to` using `via`.
func hanoi(n int, from, to, via string, moves *[]string) {
	if n == 0 {
		return
	}
	hanoi(n-1, from, via, to, moves)
	*moves = append(*moves, fmt.Sprintf("%s->%s", from, to))
	hanoi(n-1, via, to, from, moves)
}

func main() {
	var moves []string
	hanoi(3, "A", "C", "B", &moves)

	fmt.Println("moves:", len(moves)) // 2^3 - 1 = 7
	fmt.Println("first:", moves[0], "last:", moves[len(moves)-1])
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic frequency[T comparable](s []T) map[T]int that counts occurrences, and print the counts of a string slice in sorted key order.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// frequency counts how many times each distinct element appears in s.
func frequency[T comparable](s []T) map[T]int {
	freq := make(map[T]int)
	for _, v := range s {
		freq[v]++
	}
	return freq
}

func main() {
	f := frequency([]string{"a", "b", "a", "c", "b", "a"})

	keys := make([]string, 0, len(f))
	for k := range f {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Printf("%s:%d ", k, f[k])
	}
	fmt.Println() // a:3 b:2 c:1
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program showing context cancellation propagating from a parent to several derived child contexts: three goroutines each wait on their own child context, and cancelling the parent stops them all.",
        "response": '''```go
package main

import (
	"context"
	"fmt"
	"sync"
)

func main() {
	parent, cancel := context.WithCancel(context.Background())

	var wg sync.WaitGroup
	for i := 1; i <= 3; i++ {
		child, childCancel := context.WithCancel(parent) // derived from parent
		defer childCancel()
		wg.Add(1)
		go func(ctx context.Context, id int) {
			defer wg.Done()
			<-ctx.Done() // unblocks when parent (and thus child) is cancelled
			fmt.Printf("child %d stopped: %v\\n", id, ctx.Err())
		}(child, i)
	}

	cancel() // cancelling the parent cancels every derived child
	wg.Wait()
	fmt.Println("all children cancelled")
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating strings.SplitN (limited splits) and splitting a cleaned path into components. Print both results.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

func main() {
	// SplitN caps the number of substrings; the last one keeps the remainder.
	fmt.Println(strings.SplitN("a,b,c,d,e", ",", 3)) // [a b c,d,e]

	// Trim the leading/trailing separator before splitting to avoid empty parts.
	path := "/usr/local/bin/"
	parts := strings.Split(strings.Trim(path, "/"), "/")
	fmt.Println(parts) // [usr local bin]
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; the returned data has garbage trailing bytes. Explain and fix:\n\n```go\nfunc readAll(r io.Reader) ([]byte, error) {\n\tbuf := make([]byte, 1024)\n\tvar out []byte\n\tfor {\n\t\tn, err := r.Read(buf)\n\t\tout = append(out, buf...)\n\t\tif err == io.EOF {\n\t\t\treturn out, nil\n\t\t}\n\t\tif err != nil {\n\t\t\treturn nil, err\n\t\t}\n\t}\n}\n```",
        "response": '''**Bug: it appends the whole `buf`, not just the `n` bytes that were read.** `io.Reader.Read` returns `n` — the number of bytes actually written into `buf` — which is often *less* than `len(buf)`. Appending `buf...` (all 1024 bytes) every iteration tacks on stale/zero bytes beyond position `n`, corrupting the result with garbage. There's also a subtle ordering issue: `Read` can return `n > 0` *and* `io.EOF` together, but here the append already used the full buffer.

**Fix — append only `buf[:n]`, and process `n` before checking the error:**

```go
func readAll(r io.Reader) ([]byte, error) {
	buf := make([]byte, 1024)
	var out []byte
	for {
		n, err := r.Read(buf)
		out = append(out, buf[:n]...) // only the bytes actually read
		if err == io.EOF {
			return out, nil // n may be >0 on the same call as EOF; we already kept it
		}
		if err != nil {
			return nil, err
		}
	}
}
```

The two `io.Reader` contract rules this fixes: **always use `buf[:n]`** (a Reader may fill only part of the buffer), and **handle `n > 0` before treating EOF as "done"**, since a Reader is allowed to return data and `io.EOF` in the same call. In practice you'd just call `io.ReadAll(r)`, which gets all of this right — but when you must loop manually, `buf[:n]` is the critical detail.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; only the first setup runs even though it's called with different names. Explain the sync.Once semantics and how to fix it for per-key initialization:\n\n```go\nvar once sync.Once\n\nfunc setup(name string) {\n\tonce.Do(func() {\n\t\tfmt.Println(\"setting up\", name)\n\t})\n}\n```",
        "response": '''**Behavior: `sync.Once.Do` runs the function exactly once, ever — for that `Once` value.** After the first `Do`, every subsequent call (even with a *different* function literal) is a no-op. So `setup("a"); setup("b")` prints only `setting up a`. That's correct if you want a single global initialization, but it's a bug if you intended "set up each distinct name once."

**Fix A — if you really want one-time global init,** the code is fine, but don't pass per-call data that you expect to take effect; the `name` from later calls is silently ignored. Make the intent explicit by taking no argument:

```go
var once sync.Once
func setupOnce() { once.Do(func() { /* global init */ }) }
```

**Fix B — for *per-key* once semantics, use a map of `Once` (guarded by a mutex), or `sync.OnceFunc`/`OnceValue` (Go 1.21+):**

```go
var (
	mu    sync.Mutex
	onces = map[string]*sync.Once{}
)

func setup(name string) {
	mu.Lock()
	o, ok := onces[name]
	if !ok {
		o = &sync.Once{}
		onces[name] = o
	}
	mu.Unlock()

	o.Do(func() { fmt.Println("setting up", name) })
}
```

Now each distinct `name` gets its own `Once`, so each is initialized exactly once. The key insight: a single `sync.Once` is a one-shot latch tied to *that value*, independent of arguments — for "once per X," you need one `Once` per X.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; the producer goroutine leaks. Explain why and fix it with cancellation:\n\n```go\nfunc counter() <-chan int {\n\tout := make(chan int)\n\tgo func() {\n\t\tfor i := 0; ; i++ {\n\t\t\tout <- i\n\t\t}\n\t}()\n\treturn out\n}\n\n// caller: c := counter(); fmt.Println(<-c) // takes one value and moves on\n```",
        "response": '''**Bug: the producer goroutine runs forever and leaks.** `counter` starts an infinite loop sending on an unbuffered channel. The caller receives one value and stops reading, so the next `out <- i` blocks **permanently** — the goroutine is parked on that send for the life of the program, holding its stack and the channel. Every call to `counter()` whose consumer doesn't drain it forever leaks another goroutine.

**Fix — give the consumer a way to stop the producer, via a done channel or context:**

```go
func counter(done <-chan struct{}) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for i := 0; ; i++ {
			select {
			case out <- i:
			case <-done: // consumer signalled "stop"
				return   // goroutine exits, no leak
			}
		}
	}()
	return out
}

// caller:
done := make(chan struct{})
c := counter(done)
fmt.Println(<-c)
close(done) // tell the producer to stop (use defer close(done) in real code)
```

The `select { case out <- i: case <-done: return }` lets the producer notice cancellation even while trying to send. `context.Context` is the idiomatic equivalent when cancellation needs to propagate across layers (`case <-ctx.Done():`). The general rule: **a goroutine that produces values must have a way to be told to stop** — otherwise any consumer that quits early leaks it. Goroutine leaks are silent (no error, just growing memory/goroutine count), so always pair an unbounded producer with a done/context signal, and verify with tools like `goleak` in tests.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test for this generic frequency counter:\n\n```go\nfunc Frequency[T comparable](s []T) map[T]int { /* ... */ }\n```",
        "response": '''```go
func TestFrequency(t *testing.T) {
	t.Run("strings", func(t *testing.T) {
		got := Frequency([]string{"a", "b", "a", "c", "b", "a"})
		want := map[string]int{"a": 3, "b": 2, "c": 1}
		if !maps.Equal(got, want) {
			t.Errorf("Frequency = %v, want %v", got, want)
		}
	})

	t.Run("ints", func(t *testing.T) {
		got := Frequency([]int{1, 1, 1, 2})
		want := map[int]int{1: 3, 2: 1}
		if !maps.Equal(got, want) {
			t.Errorf("Frequency = %v, want %v", got, want)
		}
	})

	t.Run("empty", func(t *testing.T) {
		got := Frequency([]int{})
		if len(got) != 0 {
			t.Errorf("Frequency([]) = %v, want empty", got)
		}
	})
}
```

`maps.Equal` compares the two maps key-for-key, which is exactly right here because counting is order-independent — there's no slice ordering to worry about. The subtests instantiate the generic with two different type parameters (`string` and `int`) to confirm it works across types, plus the empty-input case (which should yield an empty, non-nil map). Counting functions are a good fit for map-equality assertions rather than per-key checks.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test asserting the Towers of Hanoi move count is 2^n - 1 for several disk counts:\n\n```go\n// HanoiMoves returns the sequence of moves to solve n disks.\nfunc HanoiMoves(n int) []string { /* ... */ }\n```",
        "response": '''```go
func TestHanoiMoveCount(t *testing.T) {
	for n := 0; n <= 6; n++ {
		moves := HanoiMoves(n)
		want := (1 << n) - 1 // 2^n - 1
		if len(moves) != want {
			t.Errorf("HanoiMoves(%d): got %d moves, want %d", n, len(moves), want)
		}
	}
}

func TestHanoiThreeDisks(t *testing.T) {
	// For 3 disks A->C via B, the exact optimal sequence is well known.
	want := []string{"A->C", "A->B", "C->B", "A->C", "B->A", "B->C", "A->C"}
	if got := HanoiMoves(3); !slices.Equal(got, want) {
		t.Errorf("HanoiMoves(3) = %v, want %v", got, want)
	}
}
```

The first test checks the mathematical invariant: solving `n` disks takes exactly `2^n - 1` moves (computed cheaply as `(1 << n) - 1`), across a range including the base case `n == 0` (zero moves). The second pins the *exact* optimal move sequence for 3 disks — an invariant count alone wouldn't catch a recursion that makes the right *number* of moves in the wrong *order*, so verifying the concrete sequence for a small case adds that coverage. Combining a general property test with one exact small-case test is a strong pattern for recursive algorithms.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain what context.Context is for in Go and how cancellation, deadlines, and values work, using this signature:\n\n```go\nfunc fetch(ctx context.Context, url string) ([]byte, error)\n```",
        "response": '''`context.Context` is Go's standard mechanism for **carrying cancellation signals, deadlines, and request-scoped values across API boundaries and goroutines**. By convention it's the **first parameter** of any function that does I/O, blocks, or spawns goroutines — hence `fetch(ctx, url)`. The point is that a caller can tell everything happening underneath "stop now," and that signal propagates down the whole call tree.

The three things a context conveys:

**1. Cancellation.** You derive a cancellable context and get a `cancel` function:
```go
ctx, cancel := context.WithCancel(parent)
defer cancel()
```
Calling `cancel()` closes `ctx.Done()` (a channel) and sets `ctx.Err()` to `context.Canceled`. Code deep inside `fetch` watches `ctx.Done()` — e.g. `select { case <-ctx.Done(): return ctx.Err() ... }`, and the `net/http` client cancels the in-flight request — so the work stops promptly instead of running uselessly. Cancellation **propagates to all derived (child) contexts**, so cancelling a parent cancels everything spawned from it.

**2. Deadlines / timeouts.** `context.WithTimeout(parent, d)` or `WithDeadline(parent, t)` give a context that auto-cancels when time runs out (`ctx.Err()` becomes `context.DeadlineExceeded`). This is how you bound a slow operation: pass the timeout context to `fetch`, and a hung network call is abandoned at the deadline. Always `defer cancel()` even for timeout contexts, to release the timer immediately when you finish early.

**3. Request-scoped values.** `context.WithValue(parent, key, val)` attaches data (a request ID, auth token, trace span) that flows with the request. Use this sparingly — only for cross-cutting, request-scoped metadata, never for passing ordinary function parameters — and use an unexported key type to avoid collisions.

How they compose: contexts form a **tree**. `context.Background()` is the root (used in `main`/init/tests); every `WithCancel`/`WithTimeout`/`WithValue` derives a child. Cancelling or timing out a node cancels its whole subtree, but never affects its parent. So a server creates a per-request context, hands it to handlers, and they pass it down to `fetch`, the DB, etc. — one signal cleanly tears down the entire request's work.

Practical rules: take `ctx` as the first arg and pass it down (don't store it in a struct); always `defer cancel()` for the cancel funcs you create; check `ctx.Err()`/`<-ctx.Done()` in long loops and before/after blocking calls; and don't pass `nil` — use `context.Background()` or `context.TODO()` when you don't have one yet.''',
    },
]
