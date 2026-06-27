# -*- coding: utf-8 -*-
"""Batch 13 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining a custom io.Reader that wraps another reader and upper-cases ASCII letters as bytes flow through. Use it with io.ReadAll over a strings.Reader and print the result.",
        "response": '''```go
package main

import (
	"fmt"
	"io"
	"strings"
)

// upperReader wraps r and upper-cases ASCII letters in each Read.
type upperReader struct {
	r io.Reader
}

func (u upperReader) Read(p []byte) (int, error) {
	n, err := u.r.Read(p)
	for i := 0; i < n; i++ {
		if p[i] >= 'a' && p[i] <= 'z' {
			p[i] -= 'a' - 'A'
		}
	}
	return n, err
}

func main() {
	r := upperReader{r: strings.NewReader("hello, world")}
	out, err := io.ReadAll(r)
	if err != nil {
		fmt.Println("read error:", err)
		return
	}
	fmt.Println(string(out)) // HELLO, WORLD
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses slices.BinarySearch on a sorted slice to find a present and an absent value, reporting the index and whether it was found.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	s := []int{1, 3, 5, 7, 9}

	if i, found := slices.BinarySearch(s, 7); found {
		fmt.Printf("7 found at index %d\\n", i)
	}
	// On a miss, i is the index where the value would be inserted to stay sorted.
	if i, found := slices.BinarySearch(s, 6); !found {
		fmt.Printf("6 not found; insert at index %d\\n", i)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating slices.Max, slices.Min, and slices.Reverse on an int slice. Print each result.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	s := []int{3, 1, 4, 1, 5, 9}

	fmt.Println("max:", slices.Max(s))
	fmt.Println("min:", slices.Min(s))

	slices.Reverse(s) // in place
	fmt.Println("reversed:", s)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a custom multiError type that aggregates several errors and implements Unwrap() []error, so errors.Is can find any of the wrapped errors. Demonstrate errors.Is finding two sentinels.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

// multiError aggregates multiple errors. Implementing Unwrap() []error lets
// errors.Is/As traverse all of them (supported since Go 1.20).
type multiError struct {
	errs []error
}

func (m *multiError) Error() string {
	return fmt.Sprintf("%d errors occurred", len(m.errs))
}

func (m *multiError) Unwrap() []error { return m.errs }

var (
	errDisk    = errors.New("disk full")
	errNetwork = errors.New("network down")
)

func main() {
	err := &multiError{errs: []error{errDisk, errNetwork}}

	fmt.Println(err)
	fmt.Println("is disk full:", errors.Is(err, errDisk))
	fmt.Println("is network down:", errors.Is(err, errNetwork))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that reads struct field tags via reflection: for each field of a User struct, print its name and its json and validate tag values.",
        "response": '''```go
package main

import (
	"fmt"
	"reflect"
)

type User struct {
	Name  string `json:"name"  validate:"required"`
	Email string `json:"email" validate:"email"`
}

func main() {
	t := reflect.TypeOf(User{})
	for i := 0; i < t.NumField(); i++ {
		f := t.Field(i)
		fmt.Printf("%-6s json=%-7q validate=%q\\n",
			f.Name, f.Tag.Get("json"), f.Tag.Get("validate"))
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a worker pool of 3 workers that process jobs from a channel and also honor a context cancellation via select. Feed 6 jobs, close the channel, and wait for clean shutdown.",
        "response": '''```go
package main

import (
	"context"
	"fmt"
	"sync"
)

func worker(ctx context.Context, jobs <-chan int, wg *sync.WaitGroup) {
	defer wg.Done()
	for {
		select {
		case <-ctx.Done(): // cancellation wins -> stop promptly
			return
		case j, ok := <-jobs:
			if !ok { // channel closed and drained
				return
			}
			_ = j * j // "process" the job
		}
	}
}

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	jobs := make(chan int)
	var wg sync.WaitGroup
	for i := 0; i < 3; i++ {
		wg.Add(1)
		go worker(ctx, jobs, &wg)
	}

	for i := 0; i < 6; i++ {
		jobs <- i
	}
	close(jobs) // tell workers no more jobs are coming
	wg.Wait()
	fmt.Println("all workers finished")
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that parses a date string like '2026-06-27' into year/month/day integers using fmt.Sscanf, checking the number of items scanned. Print the parts.",
        "response": '''```go
package main

import "fmt"

func main() {
	input := "2026-06-27"

	var year, month, day int
	n, err := fmt.Sscanf(input, "%d-%d-%d", &year, &month, &day)
	if err != nil || n != 3 {
		fmt.Printf("parse failed (scanned %d): %v\\n", n, err)
		return
	}
	fmt.Printf("year=%d month=%d day=%d\\n", year, month, day)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that computes the height of a binary tree recursively (number of nodes on the longest root-to-leaf path). Build a small tree and print its height.",
        "response": '''```go
package main

import "fmt"

type node struct {
	left, right *node
}

// height returns the number of levels; an empty tree has height 0.
func height(n *node) int {
	if n == nil {
		return 0
	}
	l, r := height(n.left), height(n.right)
	if l > r {
		return l + 1
	}
	return r + 1
}

func main() {
	tree := &node{
		left:  &node{left: &node{}}, // depth 3 on the left
		right: &node{},
	}
	fmt.Println("height:", height(tree)) // 3
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with two generic helpers: Ptr[T any](v T) *T returning a pointer to a value, and Coalesce[T comparable](vals ...T) T returning the first non-zero value. Demonstrate both.",
        "response": '''```go
package main

import "fmt"

// Ptr returns a pointer to v -- handy for optional struct/API fields where you
// need *string, *int, etc. from a literal.
func Ptr[T any](v T) *T { return &v }

// Coalesce returns the first non-zero argument, or the zero value if all are zero.
func Coalesce[T comparable](vals ...T) T {
	var zero T
	for _, v := range vals {
		if v != zero {
			return v
		}
	}
	return zero
}

func main() {
	p := Ptr(42)
	fmt.Println("*p =", *p)
	fmt.Println(Coalesce("", "", "default", "ignored")) // default
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that builds a comma-separated list of integers into a []byte buffer using strconv.AppendInt (avoiding intermediate string allocations), then prints it as a string.",
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
)

func main() {
	buf := []byte("ids: ")
	for i, id := range []int{10, 20, 30} {
		if i > 0 {
			buf = append(buf, ',')
		}
		// AppendInt writes the decimal digits straight into buf, no temp string.
		buf = strconv.AppendInt(buf, int64(id), 10)
	}
	fmt.Println(string(buf)) // ids: 10,20,30
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; callers can corrupt the struct's private state. Explain and fix:\n\n```go\ntype Config struct {\n\tsettings map[string]string\n}\n\nfunc (c *Config) Settings() map[string]string {\n\treturn c.settings\n}\n```",
        "response": '''**Bug: returning the internal map hands callers a live reference to private state.** Maps are reference types, so `Settings()` doesn't return a copy — it returns the *same* map the `Config` uses internally. Any caller can then do `cfg.Settings()["x"] = "hacked"` (or delete keys) and mutate the `Config`'s state from outside, bypassing all encapsulation and any validation the type might want to enforce. The same trap applies to returning internal slices.

**Fix A — return a copy (callers get a snapshot they can't use to mutate you):**

```go
func (c *Config) Settings() map[string]string {
	return maps.Clone(c.settings) // independent copy
}
```

**Fix B — expose read-only access instead of the whole map:**

```go
func (c *Config) Get(key string) (string, bool) {
	v, ok := c.settings[key]
	return v, ok
}
```

Prefer Fix B when callers only need lookups — it never exposes the container at all and is allocation-free. Use Fix A (`maps.Clone`, or `slices.Clone` for slices) when callers genuinely need the whole collection. The principle: a getter that returns an internal map or slice leaks mutable access to private state; copy on the way out, or expose narrow accessors.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; under load it leaks timers and memory. Explain why and fix:\n\n```go\nfunc poll(ch <-chan int) {\n\tfor {\n\t\tselect {\n\t\tcase v := <-ch:\n\t\t\tprocess(v)\n\t\tcase <-time.After(time.Second):\n\t\t\tfmt.Println(\"idle\")\n\t\t}\n\t}\n}\n```",
        "response": '''**Bug: `time.After` allocates a new timer on every loop iteration, and it isn't garbage-collected until it fires.** Each time the `ch` case is taken, the `time.After(time.Second)` timer created for that iteration is abandoned — but the runtime keeps it alive for its full 1-second duration. In a hot loop receiving many values per second, you accumulate thousands of pending timers, wasting memory and scheduler work until each expires. The `time.After` doc explicitly warns about this for loops.

**Fix — create one timer and `Reset` it each iteration:**

```go
func poll(ch <-chan int) {
	timer := time.NewTimer(time.Second)
	defer timer.Stop()
	for {
		timer.Reset(time.Second) // reuse the same timer
		select {
		case v := <-ch:
			process(v)
		case <-timer.C:
			fmt.Println("idle")
		}
	}
}
```

A single `time.NewTimer` reused via `Reset` avoids per-iteration allocation. (If "idle" means a true periodic tick regardless of activity, a `time.NewTicker` is even simpler.) The rule: `time.After` is fine for a one-shot timeout, but never call it inside a tight or long-running loop — reuse a `Timer`/`Ticker` instead.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; go vet flags it and Wait never blocks correctly. Explain and fix:\n\n```go\nfunc process(items []int, wg sync.WaitGroup) {\n\tfor range items {\n\t\twg.Add(1)\n\t\tgo func() { defer wg.Done() }()\n\t}\n\twg.Wait()\n}\n```",
        "response": '''**Bug: `sync.WaitGroup` is passed by value, so it's copied.** A `WaitGroup` must not be copied after first use — its internal counter and state live in one place, and a copy is an independent, disconnected `WaitGroup`. `go vet` reports *"process passes lock by value: sync.WaitGroup contains sync.noCopy"*. Here the effect is subtle: the copy inside `process` is what `Add`/`Done`/`Wait` operate on, so it may work by luck — but as soon as the caller also holds a `WaitGroup`, or you copy it elsewhere, `Add` and `Done` act on different instances and `Wait` either returns early or blocks forever.

**Fix — take a pointer (WaitGroups are always passed/stored by pointer):**

```go
func process(items []int, wg *sync.WaitGroup) {
	for range items {
		wg.Add(1)
		go func() { defer wg.Done() }()
	}
	wg.Wait()
}
// call: var wg sync.WaitGroup; process(items, &wg)
```

The same "never copy after use" rule applies to `sync.Mutex`, `sync.RWMutex`, `sync.Once`, and any struct embedding them: pass them by pointer and store them by pointer (or keep them as a field accessed through a pointer receiver). The `noCopy` marker exists precisely so `go vet` can catch these copies at build time.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test verifying that a multiError (implementing Unwrap() []error) is detectable via errors.Is for each wrapped sentinel:\n\n```go\ntype multiError struct{ errs []error }\nfunc (m *multiError) Error() string  { return fmt.Sprintf(\"%d errors\", len(m.errs)) }\nfunc (m *multiError) Unwrap() []error { return m.errs }\n```",
        "response": '''```go
var (
	errA = errors.New("error A")
	errB = errors.New("error B")
	errC = errors.New("error C")
)

func TestMultiErrorIs(t *testing.T) {
	err := &multiError{errs: []error{errA, errB}}

	if !errors.Is(err, errA) {
		t.Error("errors.Is(err, errA) = false, want true")
	}
	if !errors.Is(err, errB) {
		t.Error("errors.Is(err, errB) = false, want true")
	}
	// A sentinel that was NOT aggregated must not match.
	if errors.Is(err, errC) {
		t.Error("errors.Is(err, errC) = true, want false")
	}
}
```

This verifies the contract that makes `Unwrap() []error` worthwhile: `errors.Is` traverses *every* branch of the aggregated errors, so each wrapped sentinel (`errA`, `errB`) is detectable, while an unrelated sentinel (`errC`) correctly does not match. Testing the negative case (`errC`) is what proves `Is` isn't just always returning true. This is the standard way to test error aggregation — assert on detectability via `errors.Is`/`errors.As`, never on the concatenated `Error()` string.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a table-driven test for this recursive tree-height function (including the nil/empty tree):\n\n```go\ntype Node struct{ Left, Right *Node }\nfunc Height(n *Node) int {\n\tif n == nil { return 0 }\n\tl, r := Height(n.Left), Height(n.Right)\n\tif l > r { return l + 1 }\n\treturn r + 1\n}\n```",
        "response": '''```go
func TestHeight(t *testing.T) {
	leaf := func() *Node { return &Node{} }

	tests := []struct {
		name string
		tree *Node
		want int
	}{
		{"empty", nil, 0},
		{"single", leaf(), 1},
		{"balanced depth 2", &Node{Left: leaf(), Right: leaf()}, 2},
		{"left-skewed depth 3", &Node{Left: &Node{Left: leaf()}}, 3},
		{"unbalanced takes max", &Node{
			Left:  leaf(),
			Right: &Node{Right: &Node{Right: leaf()}},
		}, 4},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Height(tt.tree); got != tt.want {
				t.Errorf("Height() = %d, want %d", got, tt.want)
			}
		})
	}
}
```

The cases pin the recursion's base case (`nil -> 0`), a single node (`1`), and — most importantly — the `"unbalanced takes max"` case, which fails if someone wrote `l + r` or picked the wrong branch instead of `max(l, r) + 1`. Using a `leaf()` helper keeps the tree literals readable. For recursive functions, always include the empty/base case and at least one asymmetric input, since those expose the two most common bugs: a missing base case and combining sub-results incorrectly.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain Go's philosophy that 'errors are values' and how it differs from exceptions, using this idiom:\n\n```go\nf, err := os.Open(path)\nif err != nil {\n\treturn err\n}\ndefer f.Close()\n```",
        "response": '''In Go, **errors are ordinary values** — an `error` is just an interface (`interface { Error() string }`), returned like any other result. There is no separate exception channel and no `try/catch`. A function that can fail returns an `error` as its last return value, and the caller inspects it explicitly: `if err != nil { ... }`. That's the whole model, and the snippet is its canonical shape — open, check, handle or propagate, then defer cleanup.

How this differs from exceptions:
- **Control flow is visible.** With exceptions, any call *might* unwind the stack invisibly; you can't tell from the call site. In Go, failure is in the function signature (`(T, error)`) and handled right where it happens, so the error path is explicit and local. There's no hidden non-local jump.
- **Errors are data you can program with.** Because they're values, you can store them, compare them (`errors.Is`), extract typed information (`errors.As`), wrap them with context (`fmt.Errorf("...: %w", err)`), aggregate them, or pass them around. An exception is a control event; a Go error is a first-class value.
- **The trade-off is verbosity.** The cost is the repeated `if err != nil` boilerplate — Go deliberately accepts that in exchange for explicitness. The idiom is to handle each error once: add context and return it (let the caller decide), or handle it here. Don't ignore it (`_`), and don't both log *and* return it (that double-reports).

Where `panic`/`recover` fit: they exist, but are **not** Go's error handling. `panic` is for truly exceptional, unrecoverable situations (a violated invariant, programmer bug, or `MustCompile`-style init failure), not for expected failures like a missing file or bad input. The line is: *expected* failures → return an `error`; *impossible/unrecoverable* situations → `panic`. Libraries should almost never let a panic cross their API boundary; convert it to an error first.

So the mental model is: a Go function's signature tells you exactly how it can fail, and you deal with that failure as a value, in line, at the moment it occurs.''',
    },
]
