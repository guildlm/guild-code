# -*- coding: utf-8 -*-
"""Batch 8 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that pretty-prints a Config struct as indented JSON using json.MarshalIndent (two-space indent). Print the result.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
)

type Config struct {
	Name string   `json:"name"`
	Port int      `json:"port"`
	Tags []string `json:"tags"`
}

func main() {
	c := Config{Name: "server", Port: 8080, Tags: []string{"prod", "eu"}}

	b, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(string(b))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic merge[K comparable, V any](a, b map[K]V) map[K]V that returns a new map with all entries of both, where b wins on key conflicts. Print the merged map in sorted key order.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// merge returns a new map containing every entry of a and b; on a key collision
// the value from b takes precedence. Neither input is modified.
func merge[K comparable, V any](a, b map[K]V) map[K]V {
	out := make(map[K]V, len(a)+len(b))
	for k, v := range a {
		out[k] = v
	}
	for k, v := range b {
		out[k] = v
	}
	return out
}

func main() {
	m := merge(
		map[string]int{"a": 1, "b": 2},
		map[string]int{"b": 20, "c": 3},
	)

	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Printf("%s=%d\\n", k, m[k])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic IndexFunc[T any](s []T, pred func(T) bool) int returning the index of the first matching element (or -1), and use it to find the first even number.",
        "response": '''```go
package main

import "fmt"

// IndexFunc returns the index of the first element of s for which pred is true,
// or -1 if none match.
func IndexFunc[T any](s []T, pred func(T) bool) int {
	for i, v := range s {
		if pred(v) {
			return i
		}
	}
	return -1
}

func main() {
	nums := []int{3, 7, 8, 11}
	i := IndexFunc(nums, func(n int) bool { return n%2 == 0 })
	fmt.Println("first even at index:", i) // 2
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that parses a hexadecimal string into an int64 with strconv.ParseInt and then formats that value back out in binary and octal with strconv.FormatInt. Print each.",
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
)

func main() {
	// base 16, fits in 64 bits
	n, err := strconv.ParseInt("ff", 16, 64)
	if err != nil {
		fmt.Println("parse error:", err)
		return
	}
	fmt.Println("decimal:", n)
	fmt.Println("binary: ", strconv.FormatInt(n, 2))
	fmt.Println("octal:  ", strconv.FormatInt(n, 8))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that measures how long a piece of work takes using time.Now and time.Since, and prints whether it took at least 15ms.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	start := time.Now()

	// simulate some work
	time.Sleep(15 * time.Millisecond)

	elapsed := time.Since(start) // shorthand for time.Now().Sub(start)
	fmt.Printf("elapsed: %v\\n", elapsed)
	fmt.Printf("at least 15ms: %t\\n", elapsed >= 15*time.Millisecond)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic chunk[T any](s []T, size int) [][]T that splits a slice into consecutive sub-slices of at most size elements, and print the chunks of a 7-element slice in groups of 3.",
        "response": '''```go
package main

import "fmt"

// chunk splits s into consecutive sub-slices of at most size elements. The last
// chunk may be shorter. The sub-slices share s's backing array.
func chunk[T any](s []T, size int) [][]T {
	if size <= 0 {
		return nil
	}
	out := make([][]T, 0, (len(s)+size-1)/size)
	for i := 0; i < len(s); i += size {
		end := i + size
		if end > len(s) {
			end = len(s)
		}
		out = append(out, s[i:end])
	}
	return out
}

func main() {
	fmt.Println(chunk([]int{1, 2, 3, 4, 5, 6, 7}, 3)) // [[1 2 3] [4 5 6] [7]]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating cancellable stream production: a generator sends values but stops early when a done channel is closed. main reads two values, then the deferred close(done) halts the producer cleanly.",
        "response": '''```go
package main

import "fmt"

// gen emits nums on a channel but abandons the rest as soon as done is closed,
// so the producer goroutine never leaks.
func gen(done <-chan struct{}, nums ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for _, n := range nums {
			select {
			case out <- n:
			case <-done:
				return
			}
		}
	}()
	return out
}

func main() {
	done := make(chan struct{})
	defer close(done) // signal the producer to stop when main returns

	stream := gen(done, 1, 2, 3, 4, 5)
	fmt.Println(<-stream)
	fmt.Println(<-stream)
	// We only needed two values; the deferred close(done) stops the generator.
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program showing that comparable structs can be compared with == and used as map keys. Define a Point{X, Y int}, compare instances, and use one as a map key.",
        "response": '''```go
package main

import "fmt"

type Point struct {
	X, Y int
}

func main() {
	a := Point{1, 2}
	b := Point{1, 2}
	c := Point{3, 4}

	// Structs with all-comparable fields compare field-by-field.
	fmt.Println("a == b:", a == b) // true
	fmt.Println("a == c:", a == c) // false

	// ...and can therefore be used as map keys.
	seen := map[Point]bool{a: true}
	fmt.Println("seen b:", seen[b]) // true, since b == a
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program where a deferred closure modifies a named return value. Show a compute function returning n*2 but adding 1 in a defer, and print compute(5).",
        "response": '''```go
package main

import "fmt"

// compute returns n*2, then a deferred closure increments the named return
// value before the function actually hands it back to the caller.
func compute(n int) (result int) {
	defer func() {
		result++ // runs after `return result` has set result, before returning
	}()
	result = n * 2
	return result
}

func main() {
	fmt.Println(compute(5)) // 5*2 = 10, then +1 = 11
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program using the bytes package on a []byte: check whether it contains a substring, count its whitespace-separated fields, and upper-case it. Print each result.",
        "response": '''```go
package main

import (
	"bytes"
	"fmt"
)

func main() {
	data := []byte("the quick brown fox")

	fmt.Println("contains 'quick':", bytes.Contains(data, []byte("quick")))
	fmt.Println("field count:     ", len(bytes.Fields(data)))
	fmt.Println("upper:           ", string(bytes.ToUpper(data)))
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; the appended item never appears in the caller. Explain why and fix it:\n\n```go\nfunc addItem(items []string, v string) {\n\titems = append(items, v)\n}\n\nfunc main() {\n\titems := []string{\"a\"}\n\taddItem(items, \"b\")\n\tfmt.Println(items) // prints [a]\n}\n```",
        "response": '''**Bug: a slice is passed by value, so `append` inside the function can't grow the caller's slice.** A slice is a small header (pointer, len, cap) copied when passed. `append` may write into the shared backing array, but it returns a header with an updated `len` (and possibly a new array if it reallocated). That updated header is assigned to the function's *local* `items` and then thrown away on return — `main`'s `items` still has `len 1`.

**Fix A — return the new slice and reassign at the call site (idiomatic):**

```go
func addItem(items []string, v string) []string {
	return append(items, v)
}

func main() {
	items := []string{"a"}
	items = addItem(items, "b")
	fmt.Println(items) // [a b]
}
```

**Fix B — pass a pointer to the slice** when you must mutate in place:

```go
func addItem(items *[]string, v string) {
	*items = append(*items, v)
}
// call: addItem(&items, "b")
```

Prefer Fix A — returning the slice is the standard Go idiom (it's exactly why `append` returns a value you're expected to reassign). Reach for `*[]T` only when a method must grow a slice field through a pointer receiver.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code's error strategy and recommend an idiomatic change:\n\n```go\nfunc mustParse(s string) int {\n\tn, err := strconv.Atoi(s)\n\tif err != nil {\n\t\tpanic(err)\n\t}\n\treturn n\n}\n\n// used as: total += mustParse(userInput)\n```",
        "response": '''**Issue: panicking on an expected, recoverable condition.** Parsing user input that might be malformed is a normal, anticipated failure — not a programmer bug. `panic` unwinds the stack and (without a `recover`) crashes the program, which is a hostile way to handle "the user typed something wrong." In Go, expected failures are returned as `error` values.

**Idiomatic fix — return the error and let the caller decide:**

```go
func parse(s string) (int, error) {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, fmt.Errorf("parse %q: %w", s, err)
	}
	return n, nil
}

// caller:
n, err := parse(userInput)
if err != nil {
	// report it, skip it, prompt again — caller's choice
}
```

When is `panic` appropriate? Only for truly unrecoverable situations or clear programmer errors (an impossible switch case, a violated invariant). The `Must…` naming convention (`regexp.MustCompile`, `template.Must`) signals "panics on error" and is reserved for **package-level initialization with constant, known-good inputs** — where a failure means the program is fundamentally broken and can't run. It's wrong for runtime/user data.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; go vet complains about the cancel function and it leaks resources. Explain and fix:\n\n```go\nfunc doRequest() string {\n\tctx, _ := context.WithTimeout(context.Background(), time.Second)\n\treturn fetch(ctx)\n}\n```",
        "response": '''**Bug: the `cancel` function is discarded with `_`, leaking the context.** `context.WithTimeout` returns a `cancel` func that must always be called — it releases the context's timer and any goroutines/resources associated with the deadline. Throwing it away means those resources live until the timeout fires (and `go vet` reports: *"the cancel function returned by context.WithTimeout should be called, not discarded, to avoid a context leak"*).

**Fix — capture `cancel` and `defer` it:**

```go
func doRequest() string {
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel() // release resources as soon as doRequest returns
	return fetch(ctx)
}
```

`defer cancel()` runs on every return path. Calling `cancel` early (before the deadline) is not just allowed but expected — once `fetch` returns you no longer need the timer, so releasing it immediately is correct. This rule applies to all of `WithCancel`, `WithTimeout`, and `WithDeadline`: always `defer cancel()`.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write subtests verifying FIFO behavior and empty handling for this queue:\n\n```go\ntype Queue[T any] struct{ items []T }\nfunc (q *Queue[T]) Enqueue(v T) { q.items = append(q.items, v) }\nfunc (q *Queue[T]) Dequeue() (T, bool) {\n\tvar z T\n\tif len(q.items) == 0 { return z, false }\n\tv := q.items[0]\n\tq.items = q.items[1:]\n\treturn v, true\n}\n```",
        "response": '''```go
func TestQueue(t *testing.T) {
	t.Run("empty dequeue", func(t *testing.T) {
		var q Queue[int]
		if v, ok := q.Dequeue(); ok || v != 0 {
			t.Fatalf("Dequeue() = (%d, %v), want (0, false)", v, ok)
		}
	})

	t.Run("FIFO order", func(t *testing.T) {
		var q Queue[int]
		for _, v := range []int{1, 2, 3} {
			q.Enqueue(v)
		}
		for _, want := range []int{1, 2, 3} { // first in, first out
			got, ok := q.Dequeue()
			if !ok {
				t.Fatalf("Dequeue() ok=false, want a value")
			}
			if got != want {
				t.Errorf("Dequeue() = %d, want %d", got, want)
			}
		}
		if _, ok := q.Dequeue(); ok {
			t.Errorf("Dequeue() after draining: ok=true, want false")
		}
	})
}
```

The two subtests isolate the contract: dequeuing an empty queue returns the zero value plus `false`, and a sequence of enqueues dequeues in first-in-first-out order (the inverse of the stack test's LIFO). The final empty-check confirms the queue drains rather than re-yielding stale elements.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a testable example with non-deterministic output order for a function that prints a map's keys, using the // Unordered output: directive:\n\n```go\n// PrintCounts prints each word and its count, one per line.\nfunc PrintCounts(counts map[string]int) {\n\tfor w, c := range counts {\n\t\tfmt.Printf(\"%s=%d\\n\", w, c)\n\t}\n}\n```",
        "response": '''```go
func ExamplePrintCounts() {
	PrintCounts(map[string]int{"a": 1, "b": 2, "c": 3})
	// Unordered output:
	// a=1
	// b=2
	// c=3
}
```

Map iteration order in Go is intentionally randomized, so a normal `// Output:` block (which requires an exact, ordered match) would make this example flaky. The `// Unordered output:` directive tells `go test` to split both the expected and actual output into lines and compare them as **sets** — every expected line must appear, in any order. Use it whenever the output is correct but its ordering isn't guaranteed (ranging a map, collecting from goroutines). If order actually matters, sort before printing and use `// Output:` instead.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain when deferred function arguments are evaluated in Go, and what this prints:\n\n```go\nfunc main() {\n\ti := 0\n\tdefer fmt.Println(\"deferred:\", i)\n\ti = 10\n\tfmt.Println(\"immediate:\", i)\n}\n```",
        "response": '''This prints:

```
immediate: 10
deferred: 0
```

The key rule: **a deferred call's arguments are evaluated at the moment the `defer` statement runs, not when the deferred function actually executes.**

Walking through it:
- `i := 0` sets `i` to 0.
- `defer fmt.Println("deferred:", i)` — the `defer` statement executes *now*, so its arguments are evaluated *now*: the string and the current value of `i` (which is `0`) are captured and saved. The *call itself* is postponed until `main` returns.
- `i = 10` changes `i`, but that has no effect on the already-captured argument.
- `fmt.Println("immediate:", i)` prints `10`.
- `main` returns, and the deferred call runs with its captured argument: `deferred: 0`.

The practical consequence: if you want a deferred call to observe the *final* value of a variable, don't pass it as an argument — capture it in a **closure** instead, because the closure reads the variable when it runs:

```go
defer func() { fmt.Println("deferred:", i) }() // prints 10
```

This distinction is why `defer file.Close()` captures the specific `file` value at defer time (good — you close exactly that file), while logging the result of an operation usually needs the closure form to see the latest state.''',
    },
]
