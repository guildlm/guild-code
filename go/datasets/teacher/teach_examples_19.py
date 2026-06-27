# -*- coding: utf-8 -*-
"""Batch 19 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that base64-encodes a string and decodes it back using encoding/base64, printing both.",
        "response": '''```go
package main

import (
	"encoding/base64"
	"fmt"
)

func main() {
	data := []byte("GuildLM")

	enc := base64.StdEncoding.EncodeToString(data)
	fmt.Println("encoded:", enc)

	dec, err := base64.StdEncoding.DecodeString(enc)
	if err != nil {
		fmt.Println("decode error:", err)
		return
	}
	fmt.Println("decoded:", string(dec))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that prints an aligned table (columns separated by tabs) using text/tabwriter so the columns line up regardless of content width.",
        "response": '''```go
package main

import (
	"fmt"
	"os"
	"text/tabwriter"
)

func main() {
	// minwidth, tabwidth, padding, padchar, flags
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)

	fmt.Fprintln(w, "NAME\\tAGE\\tCITY")
	fmt.Fprintln(w, "Ada\\t36\\tLondon")
	fmt.Fprintln(w, "Tim\\t5\\tNYC")

	w.Flush() // tabwriter buffers; Flush computes column widths and writes
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic Clamp[T cmp.Ordered](v, lo, hi T) T that constrains a value to a range, and demonstrate it on ints and floats.",
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
)

// Clamp returns v limited to the inclusive range [lo, hi].
func Clamp[T cmp.Ordered](v, lo, hi T) T {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func main() {
	fmt.Println(Clamp(15, 0, 10))      // 10
	fmt.Println(Clamp(-3, 0, 10))      // 0
	fmt.Println(Clamp(5, 0, 10))       // 5
	fmt.Println(Clamp(2.5, 1.0, 2.0))  // 2
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing in-place quicksort with a Lomuto partition (recursive on index ranges). Sort and print a sample slice.",
        "response": '''```go
package main

import "fmt"

// quicksort sorts s[lo..hi] in place using a Lomuto partition around s[hi].
func quicksort(s []int, lo, hi int) {
	if lo >= hi {
		return
	}
	pivot := s[hi]
	i := lo
	for j := lo; j < hi; j++ {
		if s[j] < pivot {
			s[i], s[j] = s[j], s[i]
			i++
		}
	}
	s[i], s[hi] = s[hi], s[i] // put pivot in its final place
	quicksort(s, lo, i-1)
	quicksort(s, i+1, hi)
}

func main() {
	s := []int{5, 2, 9, 1, 5, 6}
	quicksort(s, 0, len(s)-1)
	fmt.Println(s) // [1 2 5 5 6 9]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses a time.Ticker as a simple rate limiter, counting how many ticks occur within a fixed window, and reports an approximate count. Stop the ticker.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	ticker := time.NewTicker(10 * time.Millisecond)
	defer ticker.Stop()

	deadline := time.After(55 * time.Millisecond)
	ticks := 0

loop:
	for {
		select {
		case <-ticker.C:
			ticks++ // here you'd do one rate-limited unit of work
		case <-deadline:
			break loop // labeled break exits the for, not just the select
		}
	}

	fmt.Println("about 5 ticks:", ticks >= 4 && ticks <= 6)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a dedup(s []string) []string that removes duplicates while preserving first-seen order, using a set for membership. Print the result.",
        "response": '''```go
package main

import "fmt"

// dedup returns s with duplicates removed, keeping the first occurrence order.
func dedup(s []string) []string {
	seen := make(map[string]struct{}, len(s))
	var out []string
	for _, v := range s {
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		out = append(out, v)
	}
	return out
}

func main() {
	fmt.Println(dedup([]string{"a", "b", "a", "c", "b", "a"})) // [a b c]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that runs several tasks concurrently and aggregates all their errors with errors.Join (using a buffered channel + WaitGroup). Print the combined error.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
	"sync"
)

// runAll runs every task concurrently and returns all errors joined (nil if none).
func runAll(tasks []func() error) error {
	errCh := make(chan error, len(tasks)) // buffered so senders never block
	var wg sync.WaitGroup
	for _, task := range tasks {
		wg.Add(1)
		go func(t func() error) {
			defer wg.Done()
			if err := t(); err != nil {
				errCh <- err
			}
		}(task)
	}
	wg.Wait()
	close(errCh)

	var errs []error
	for err := range errCh {
		errs = append(errs, err)
	}
	return errors.Join(errs...)
}

func main() {
	err := runAll([]func() error{
		func() error { return nil },
		func() error { return errors.New("task 2 failed") },
		func() error { return errors.New("task 3 failed") },
	})
	fmt.Println("result:", err)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that reports how many bits are needed to represent several unsigned integers using math/bits.Len. Print each.",
        "response": '''```go
package main

import (
	"fmt"
	"math/bits"
)

func main() {
	for _, n := range []uint{0, 1, 5, 16, 255} {
		// bits.Len(n) is the minimum number of bits to represent n (0 for n==0).
		fmt.Printf("%3d needs %d bits\\n", n, bits.Len(n))
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that lexicographically compares two int slices with slices.Compare (Go 1.21+), printing the result for an unequal and an equal pair.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	a := []int{1, 2, 3}
	b := []int{1, 2, 4}

	// Compare returns -1, 0, or 1 (lexicographic, element by element).
	fmt.Println("a vs b:", slices.Compare(a, b)) // -1 (3 < 4 at index 2)
	fmt.Println("a vs a:", slices.Compare(a, a)) // 0
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing a small ordered map that remembers insertion order: a Set method and an Each method that iterates keys in the order they were first added. Print the entries.",
        "response": '''```go
package main

import "fmt"

// orderedMap is a map that iterates keys in insertion order.
type orderedMap struct {
	keys   []string
	values map[string]int
}

func newOrderedMap() *orderedMap {
	return &orderedMap{values: make(map[string]int)}
}

func (o *orderedMap) Set(k string, v int) {
	if _, exists := o.values[k]; !exists {
		o.keys = append(o.keys, k) // record order only on first insert
	}
	o.values[k] = v
}

func (o *orderedMap) Each(f func(k string, v int)) {
	for _, k := range o.keys {
		f(k, o.values[k])
	}
}

func main() {
	m := newOrderedMap()
	m.Set("z", 1)
	m.Set("a", 2)
	m.Set("m", 3)
	m.Set("z", 9) // update keeps original position

	m.Each(func(k string, v int) { fmt.Printf("%s=%d ", k, v) })
	fmt.Println() // z=9 a=2 m=3  (insertion order, not sorted)
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it hides real bugs. Explain why a bare recover is dangerous and what to do instead:\n\n```go\nfunc process(data []byte) {\n\tdefer func() { recover() }()\n\trisky(data)\n}\n```",
        "response": '''**Anti-pattern: a bare `recover()` that swallows every panic silently.** This `defer` catches *any* panic from `risky` and discards it — no log, no error returned, nothing. A nil-pointer dereference, an out-of-range index, a real logic bug: all vanish, and the program limps on in an unknown state. You've converted loud, debuggable crashes into silent corruption.

**Fix — recover only at a deliberate boundary, and surface what happened (convert to an error and/or log; optionally re-panic on truly unexpected ones):**

```go
func process(data []byte) (err error) {
	defer func() {
		if r := recover(); r != nil {
			// Turn the panic into an error the caller can handle.
			err = fmt.Errorf("process panicked: %v", r)
			// Optionally log a stack for diagnosis:
			// log.Printf("panic: %v\\n%s", r, debug.Stack())
		}
	}()
	risky(data)
	return nil
}
```

Guidelines for `recover`:
- It only works inside a **deferred** function, and only catches panics from the same goroutine.
- Use it at **well-defined boundaries** — a request handler that shouldn't take down the server, a worker that should isolate one job's failure, a library that must not let a panic cross its API. Not as a blanket "ignore errors."
- **Always do something with the recovered value**: convert it to an `error` (via a named return), log it with a stack (`runtime/debug.Stack`), increment a metric. Never `recover()` and drop it.
- Remember panics don't cross goroutines: a `go func(){...}()` that panics crashes the whole program regardless of a `recover` in the parent, so each goroutine that can panic needs its own deferred recover.

And the bigger principle: `panic`/`recover` is **not** general error handling — expected failures should be returned as `error` values. Reserve panics for truly exceptional conditions, and when you do recover, never recover *silently*.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; two times that represent the same instant sometimes compare unequal. Explain and fix:\n\n```go\nfunc sameInstant(a, b time.Time) bool {\n\treturn a == b\n}\n```",
        "response": '''**Bug: `==` on `time.Time` compares more than the instant.** A `time.Time` contains a wall-clock reading, an optional **monotonic clock** reading, and a `*Location`. The `==` operator compares all of those struct fields, so two `Time`s that denote the *same instant* can be unequal because:
- one carries a monotonic reading (from `time.Now()`) and the other doesn't (e.g. from `time.Parse` or after `t.Round(0)`),
- they're in different `Location`s (e.g. UTC vs `America/New_York`) even at the same instant,
- they were constructed differently.

So `==` is unreliable for "do these mean the same time?"

**Fix — use the `Equal` method, which compares instants:**

```go
func sameInstant(a, b time.Time) bool {
	return a.Equal(b)
}
```

`a.Equal(b)` reports whether they represent the same time instant, **ignoring location** and handling the monotonic-vs-wall-clock detail correctly — `10:00 UTC` and `06:00 EDT` (the same moment) are `Equal` but not `==`. Related rules: use `a.Before(b)` / `a.After(b)` for ordering (not `<`/`>`, which don't exist on `Time` anyway), and if you need to *store* a `Time` for later `==` comparison or use it as a map key, strip the monotonic clock first with `t = t.Round(0)`. In short: never use `==` to compare `time.Time` for instant equality — use `Equal`.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it panics on some inputs. Explain and fix:\n\n```go\nfunc firstTwo(s []int) (int, int) {\n\treturn s[0], s[1]\n}\n```",
        "response": '''**Bug: it indexes `s[0]` and `s[1]` without checking the length.** If `s` is `nil`, empty, or has a single element, `s[0]` or `s[1]` is out of range and panics (`index out of range`). The function silently assumes the caller always passes at least two elements — an assumption nothing enforces.

**Fix — validate the length and report the problem instead of panicking:**

```go
func firstTwo(s []int) (int, int, bool) {
	if len(s) < 2 {
		return 0, 0, false // not enough elements
	}
	return s[0], s[1], true
}
```

Returning an `ok bool` (or an `error`) lets the caller handle short input deliberately:

```go
if a, b, ok := firstTwo(s); ok {
	// use a, b
}
```

The principle: **never index a slice (or array) by a position you haven't proven is in range.** Validate `len(s)` before fixed-index access, especially at API boundaries where input size isn't guaranteed. A panic here is a crash for what is really a normal "too few elements" case — surface it as data (`ok`/`error`) so callers can respond. (If two elements truly is an unbreakable precondition of an internal helper, document it and consider a `[2]int` array parameter so the type system enforces the count.)''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test verifying that an ordered map iterates keys in insertion order:\n\n```go\ntype OrderedMap struct{ /* keys []string; values map[string]int */ }\nfunc NewOrderedMap() *OrderedMap\nfunc (o *OrderedMap) Set(k string, v int)\nfunc (o *OrderedMap) Each(f func(k string, v int))\n```",
        "response": '''```go
func TestOrderedMapInsertionOrder(t *testing.T) {
	m := NewOrderedMap()
	m.Set("z", 1)
	m.Set("a", 2)
	m.Set("m", 3)
	m.Set("z", 9) // updating an existing key must NOT change its position

	var keys []string
	var vals []int
	m.Each(func(k string, v int) {
		keys = append(keys, k)
		vals = append(vals, v)
	})

	wantKeys := []string{"z", "a", "m"} // first-insertion order, not sorted
	wantVals := []int{9, 2, 3}          // z updated to 9 but stays first

	if !slices.Equal(keys, wantKeys) {
		t.Errorf("keys = %v, want %v", keys, wantKeys)
	}
	if !slices.Equal(vals, wantVals) {
		t.Errorf("vals = %v, want %v", vals, wantVals)
	}
}
```

The whole point of an ordered map is the iteration order, so the test asserts the exact key sequence with `slices.Equal` — a plain `map[string]int` would iterate randomly and fail this. The crucial case is `Set("z", 9)` *after* other inserts: it verifies that **updating** an existing key changes its value but keeps its original position (the key isn't re-appended). Without that case, a buggy implementation that re-orders keys on update would still pass. The "z", "a", "m" choice (not alphabetical) also guards against an implementation that accidentally sorts.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test for a concurrent task runner that aggregates errors:\n\n```go\n// RunAll runs every task concurrently and returns all errors joined (nil if none).\nfunc RunAll(tasks []func() error) error\n```",
        "response": '''```go
func TestRunAll(t *testing.T) {
	t.Run("all succeed", func(t *testing.T) {
		err := RunAll([]func() error{
			func() error { return nil },
			func() error { return nil },
		})
		if err != nil {
			t.Errorf("got %v, want nil", err)
		}
	})

	t.Run("aggregates failures", func(t *testing.T) {
		errA := errors.New("a failed")
		errB := errors.New("b failed")
		err := RunAll([]func() error{
			func() error { return errA },
			func() error { return nil },
			func() error { return errB },
		})
		if err == nil {
			t.Fatal("expected an error, got nil")
		}
		// errors.Join lets us detect each underlying error regardless of order.
		if !errors.Is(err, errA) || !errors.Is(err, errB) {
			t.Errorf("err = %v, want it to wrap both errA and errB", err)
		}
	})

	t.Run("empty is nil", func(t *testing.T) {
		if err := RunAll(nil); err != nil {
			t.Errorf("RunAll(nil) = %v, want nil", err)
		}
	})
}
```

Because the tasks run concurrently, error *order* is non-deterministic — so the failure test asserts with `errors.Is(err, errA)` and `errors.Is(err, errB)` rather than comparing the joined message string. That's the right way to test `errors.Join` output: check that each expected error is *detectable* in the result, independent of ordering. The "all succeed" case pins that a fully-successful run returns `nil` (not an empty non-nil error), and the empty-input case covers the boundary. Running this under `go test -race` additionally checks the runner's concurrency is sound.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Give a thorough explanation of Go's defer statement: ordering, when arguments are evaluated, and the common idioms, using this snippet:\n\n```go\nfunc copyFile(dst, src string) (err error) {\n\tin, err := os.Open(src)\n\tif err != nil { return err }\n\tdefer in.Close()\n\t// ...\n\treturn nil\n}\n```",
        "response": '''`defer` schedules a function call to run **when the surrounding function returns** — whether it returns normally, via an early `return`, or while unwinding from a `panic`. It's Go's mechanism for "do this cleanup no matter how we leave," which is why `defer in.Close()` sits right after a successful `os.Open`: the file is guaranteed to close on every exit path.

The rules that matter:

**1. LIFO ordering.** Multiple deferred calls run in **reverse** order of registration (a stack). So:
```go
defer fmt.Print("a")
defer fmt.Print("b") // prints "b" then "a"
```
This is exactly what you want for paired setup/teardown: open A, open B, then on the way out close B, then close A — resources are released in the opposite order they were acquired.

**2. Arguments are evaluated at the `defer` statement, not when the call runs.** The deferred function's arguments (and the receiver) are computed *immediately* and captured:
```go
i := 0
defer fmt.Println(i) // captures 0 now
i = 10               // doesn't affect the captured value
// prints 0
```
To observe the *final* value instead, defer a **closure**, which reads the variable when it executes: `defer func() { fmt.Println(i) }()` prints 10. This distinction is a frequent source of confusion.

**3. A deferred closure can modify named return values.** Because deferred calls run *after* the `return` expression is evaluated but *before* control actually leaves, a closure can inspect or change a named return — the basis of the recover-to-error idiom:
```go
func copyFile(dst, src string) (err error) {
	// ...
	defer func() {
		if cerr := out.Close(); cerr != nil && err == nil {
			err = cerr // surface a close error if nothing else failed
		}
	}()
}
```
This is important for *writable* resources: closing a file you wrote to can fail (flush errors), and `defer out.Close()` alone would silently drop that error — so file *writes* often use the closure form to capture the close error, while a read-only `defer in.Close()` can ignore it.

**Common idioms:**
- **Resource cleanup:** `defer f.Close()`, `defer conn.Close()`, `defer rows.Close()` — placed immediately after the resource is acquired (and after its error check, so you never defer on a nil resource).
- **Unlocking:** `mu.Lock(); defer mu.Unlock()` — robust to multiple returns and panics, the standard way to avoid forgotten unlocks.
- **Recover boundary:** `defer func(){ if r := recover(); r != nil { ... } }()` to turn a panic into an error at an API boundary.
- **Timing/tracing:** `defer func(t time.Time){ log.Printf("took %v", time.Since(t)) }(time.Now())` — capturing the start time via the eager argument evaluation.

**Cost and caveats:** `defer` is cheap (heavily optimized in modern Go) — don't avoid it for clarity's sake. But note its scope is the **function**, not the block: a `defer` inside a `for` loop does *not* run at the end of each iteration; it stacks up and runs when the whole function returns. For per-iteration cleanup, extract the loop body into its own function so each call's `defer` fires promptly (this is the fix for the "too many open files" leak when opening files in a loop). The mental model: `defer` = "run this on the way out of *this function*, last-registered-first, with arguments frozen at registration time."''',
    },
]
