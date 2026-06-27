# -*- coding: utf-8 -*-
"""Batch 5 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses select with a default case to receive from a channel without blocking, showing both the 'value ready' and 'nothing ready' outcomes.",
        "response": '''```go
package main

import "fmt"

func main() {
	ch := make(chan int, 1)
	ch <- 42

	// A value is buffered, so the receive case is chosen.
	select {
	case v := <-ch:
		fmt.Println("received:", v)
	default:
		fmt.Println("no value ready")
	}

	// Now the channel is empty, so default fires instead of blocking.
	select {
	case v := <-ch:
		fmt.Println("received:", v)
	default:
		fmt.Println("no value ready")
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing a concurrency-safe cache with sync.RWMutex, allowing many concurrent readers but exclusive writers. Demonstrate set and get (including a miss).",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

type cache struct {
	mu sync.RWMutex
	m  map[string]int
}

func newCache() *cache { return &cache{m: make(map[string]int)} }

func (c *cache) get(k string) (int, bool) {
	c.mu.RLock() // many readers may hold this at once
	defer c.mu.RUnlock()
	v, ok := c.m[k]
	return v, ok
}

func (c *cache) set(k string, v int) {
	c.mu.Lock() // writers get exclusive access
	defer c.mu.Unlock()
	c.m[k] = v
}

func main() {
	c := newCache()
	c.set("a", 1)
	if v, ok := c.get("a"); ok {
		fmt.Println("a =", v)
	}
	if _, ok := c.get("b"); !ok {
		fmt.Println("b missing")
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic Sum function constrained to a custom Number interface (covering int, int64, float64 and their derived types), and use it on both an []int and a []float64.",
        "response": '''```go
package main

import "fmt"

// Number admits the built-in numeric kinds and any type whose underlying type
// is one of them (the ~ operator).
type Number interface {
	~int | ~int64 | ~float64
}

func Sum[T Number](nums []T) T {
	var total T
	for _, n := range nums {
		total += n
	}
	return total
}

func main() {
	fmt.Println(Sum([]int{1, 2, 3}))
	fmt.Println(Sum([]float64{1.5, 2.5, 3.0}))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that parses a timestamp with time.Parse using Go's reference layout, adds 90 minutes, and prints the original, the later time, and the duration between them.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	// Go's reference time is Mon Jan 2 15:04:05 MST 2006.
	const layout = "2006-01-02 15:04"

	t, err := time.Parse(layout, "2026-06-27 14:30")
	if err != nil {
		fmt.Println("parse error:", err)
		return
	}

	later := t.Add(90 * time.Minute)
	fmt.Println("start:", t.Format(layout))
	fmt.Println("later:", later.Format(layout))
	fmt.Println("diff: ", later.Sub(t))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that reads input line by line from an in-memory reader using bufio.Scanner, numbering each line, and checks scanner.Err() afterwards.",
        "response": '''```go
package main

import (
	"bufio"
	"fmt"
	"strings"
)

func main() {
	input := "first\\nsecond\\nthird\\n"
	scanner := bufio.NewScanner(strings.NewReader(input))

	count := 0
	for scanner.Scan() {
		count++
		fmt.Printf("%d: %s\\n", count, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		fmt.Println("scan error:", err)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating closures over state: a counter() function that returns a function yielding 1, 2, 3,… on each call, and show that two counters keep independent state.",
        "response": '''```go
package main

import "fmt"

// counter returns a closure that increments and returns its own private n.
func counter() func() int {
	n := 0
	return func() int {
		n++
		return n
	}
}

func main() {
	next := counter()
	fmt.Println(next(), next(), next()) // 1 2 3

	other := counter() // independent captured state
	fmt.Println(other()) // 1
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that demonstrates deferred calls running in LIFO order, by deferring a print of i for i = 1..3 inside a loop and printing markers before and after.",
        "response": '''```go
package main

import "fmt"

func main() {
	fmt.Println("start")
	for i := 1; i <= 3; i++ {
		defer fmt.Println("deferred:", i)
	}
	fmt.Println("end")
	// Deferred calls are pushed onto a stack and run in reverse (LIFO) order
	// as the function returns: 3, then 2, then 1.
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a variadic minMax(nums ...int) (min, max int) function that returns the smallest and largest of its arguments, and print the result for a few numbers.",
        "response": '''```go
package main

import "fmt"

// minMax returns the smallest and largest of nums (0, 0 if none are given).
func minMax(nums ...int) (lo, hi int) {
	if len(nums) == 0 {
		return 0, 0
	}
	lo, hi = nums[0], nums[0]
	for _, n := range nums[1:] {
		if n < lo {
			lo = n
		}
		if n > hi {
			hi = n
		}
	}
	return lo, hi
}

func main() {
	lo, hi := minMax(3, 7, 1, 9, 4)
	fmt.Printf("min=%d max=%d\\n", lo, hi)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that builds and iterates a slice of anonymous structs holding a name and age, printing each entry.",
        "response": '''```go
package main

import "fmt"

func main() {
	people := []struct {
		Name string
		Age  int
	}{
		{"Ada", 36},
		{"Tim", 15},
		{"Ken", 42},
	}

	for _, p := range people {
		fmt.Printf("%s is %d\\n", p.Name, p.Age)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with parseInts(line string) ([]int, error) that splits a whitespace-separated string into ints, wrapping any conversion error with the offending token. Demonstrate it on a valid line.",
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
	"strings"
)

// parseInts converts a whitespace-separated string of integers into a slice,
// reporting which token failed if any.
func parseInts(line string) ([]int, error) {
	fields := strings.Fields(line)
	nums := make([]int, 0, len(fields))
	for _, f := range fields {
		n, err := strconv.Atoi(f)
		if err != nil {
			return nil, fmt.Errorf("parse %q: %w", f, err)
		}
		nums = append(nums, n)
	}
	return nums, nil
}

func main() {
	nums, err := parseInts("10 20 30 40")
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(nums)
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; the equality check fails unexpectedly. Explain and fix:\n\n```go\nfunc main() {\n\tx := 0.1 + 0.2\n\tif x == 0.3 {\n\t\tfmt.Println(\"equal\")\n\t} else {\n\t\tfmt.Println(\"not equal\")\n\t}\n}\n```",
        "response": '''**Bug: exact `==` comparison of floating-point results.** `0.1`, `0.2`, and `0.3` cannot be represented exactly in IEEE-754 binary floating point, so `0.1 + 0.2` is actually `0.30000000000000004`, which is not bit-for-bit equal to the literal `0.3`. The program prints `not equal`. This isn't a Go quirk — it's true of floats in essentially every language.

**Fix — compare within a small tolerance (epsilon):**

```go
import "math"

func main() {
	x := 0.1 + 0.2
	const eps = 1e-9
	if math.Abs(x-0.3) < eps {
		fmt.Println("equal")
	} else {
		fmt.Println("not equal")
	}
}
```

Choose `eps` relative to the magnitude and precision you care about (for values far from 1.0, a relative tolerance `math.Abs(x-y) <= eps*math.Max(math.Abs(x), math.Abs(y))` is better). Only use exact `==` on floats for special sentinels like `0` that you assigned yourself, or when you specifically need to test for exact representable values.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go function; it always returns an empty Config even when useFile is true. Explain the shadowing bug and fix:\n\n```go\nfunc loadConfig(useFile bool) (*Config, error) {\n\tcfg := &Config{}\n\tif useFile {\n\t\tcfg, err := readFile()\n\t\tif err != nil {\n\t\t\treturn nil, err\n\t\t}\n\t\t_ = cfg\n\t}\n\treturn cfg, nil\n}\n```",
        "response": '''**Bug: variable shadowing with `:=`.** Inside the `if` block, `cfg, err := readFile()` uses `:=`, which declares **new** `cfg` and `err` variables scoped to that block — it does *not* assign to the outer `cfg`. The loaded config is bound to the inner `cfg` (and then discarded by `_ = cfg`), while the function returns the outer, still-empty `&Config{}`.

**Fix — assign to the existing `cfg` with `=`, declaring only `err`:**

```go
func loadConfig(useFile bool) (*Config, error) {
	cfg := &Config{}
	if useFile {
		var err error
		cfg, err = readFile() // = assigns the outer cfg
		if err != nil {
			return nil, err
		}
	}
	return cfg, nil
}
```

Now `cfg` refers to the same variable throughout. This class of bug is exactly what `go vet`'s shadow analysis and linters like `govet`/`golangci-lint` (shadow check) are designed to catch — turning them on in CI prevents it.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it crashes with 'all goroutines are asleep - deadlock'. Explain why and show two fixes:\n\n```go\nfunc main() {\n\tch := make(chan int)\n\tch <- 1\n\tfmt.Println(<-ch)\n}\n```",
        "response": '''**Bug: blocking send on an unbuffered channel with no concurrent receiver.** `ch` is unbuffered, so `ch <- 1` blocks until *another* goroutine receives. But `main` is the only goroutine, and the matching `<-ch` is on the very next line — it can never run because execution is stuck on the send. The runtime detects that every goroutine is blocked and aborts: `fatal error: all goroutines are asleep - deadlock!`.

**Fix A — give the channel a buffer** so the send completes without a waiting receiver:

```go
func main() {
	ch := make(chan int, 1)
	ch <- 1
	fmt.Println(<-ch)
}
```

**Fix B — send and receive in different goroutines** (the right shape when you actually want a handoff):

```go
func main() {
	ch := make(chan int)
	go func() { ch <- 1 }() // send concurrently
	fmt.Println(<-ch)       // main receives
}
```

Use the buffer when the channel is just a one-slot mailbox; use separate goroutines when the send and receive are genuinely concurrent work.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go testable example (ExampleXxx with an // Output: comment) for this function so it doubles as documentation and a test:\n\n```go\n// Reverse returns s with its runes in reverse order.\nfunc Reverse(s string) string {\n\tr := []rune(s)\n\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tr[i], r[j] = r[j], r[i]\n\t}\n\treturn string(r)\n}\n```",
        "response": '''```go
func ExampleReverse() {
	fmt.Println(Reverse("hello"))
	fmt.Println(Reverse("世界"))
	// Output:
	// olleh
	// 界世
}
```

A function named `ExampleReverse` in a `_test.go` file is a **testable example**: `go test` runs it and compares everything it prints to stdout against the text in the `// Output:` comment, failing if they differ. So this single block serves three purposes at once — it's executed as a test, it appears in `go doc` / pkg.go.dev as usage documentation, and it guarantees the docs never drift from the real behavior. The second line (`世界` → `界世`) also documents that the reversal is rune-correct for multi-byte input. For output whose order isn't deterministic, use `// Unordered output:` instead.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a table-driven test for this generic stack's Push/Pop behavior, including the empty-pop error:\n\n```go\ntype Stack[T any] struct{ items []T }\nfunc (s *Stack[T]) Push(v T)      { s.items = append(s.items, v) }\nfunc (s *Stack[T]) Pop() (T, bool) { var z T; if len(s.items)==0 { return z, false }; i:=len(s.items)-1; v:=s.items[i]; s.items=s.items[:i]; return v, true }\n```",
        "response": '''```go
func TestStack(t *testing.T) {
	var s Stack[int]

	// Pop on empty returns the zero value and false.
	if v, ok := s.Pop(); ok || v != 0 {
		t.Fatalf("empty Pop() = (%d, %v), want (0, false)", v, ok)
	}

	// LIFO order: push 1,2,3 -> pop 3,2,1.
	for _, v := range []int{1, 2, 3} {
		s.Push(v)
	}
	want := []int{3, 2, 1}
	for i, w := range want {
		got, ok := s.Pop()
		if !ok {
			t.Fatalf("Pop() #%d: ok=false, want a value", i)
		}
		if got != w {
			t.Errorf("Pop() #%d = %d, want %d", i, got, w)
		}
	}

	// Stack is empty again.
	if _, ok := s.Pop(); ok {
		t.Errorf("Pop() after draining: ok=true, want false")
	}
}
```

The test exercises the full lifecycle: popping an empty stack (zero value + `false`), the LIFO ordering after a sequence of pushes, and a final empty-pop to confirm the stack drains correctly. Driving `Pop` against the expected `[3,2,1]` order is what actually verifies "last in, first out".''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain how Go slices grow when you append to them, and why append's return value must be reassigned, using this snippet:\n\n```go\ns := make([]int, 0, 2)\ns = append(s, 1, 2)\ns = append(s, 3)\n```",
        "response": '''A slice is a three-word header: a pointer to a backing array, a `len` (elements in use), and a `cap` (slots available in that array before it must grow).

Walking the snippet:
- `make([]int, 0, 2)` allocates a backing array of size 2 and returns a slice with `len 0, cap 2`.
- `append(s, 1, 2)` has room (`len 0` + 2 ≤ `cap 2`), so it writes into the existing array and returns a header with `len 2, cap 2`. No allocation.
- `append(s, 3)` needs `len 3 > cap 2`, so `append` **allocates a new, larger backing array**, copies the existing two elements into it, writes `3`, and returns a slice pointing at the *new* array. The growth strategy is roughly geometric (commonly doubling for small slices, ~1.25× for large ones), which makes a sequence of appends amortized O(1) per element.

**Why you must write `s = append(...)`:** when `append` grows, the returned slice points to a different array with a different `cap` than the one you passed in. If you discarded the return value, `s` would still reference the old, full array and you'd lose the appended element (and writes via the old header wouldn't be visible through the new one). Because the header is passed by value, `append` *cannot* update your variable for you — it returns the updated header and you must assign it back. This is also why a function that appends to a slice argument must return the slice (or take a `*[]T`) for the caller to see growth.''',
    },
]
