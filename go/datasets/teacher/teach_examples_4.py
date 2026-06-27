# -*- coding: utf-8 -*-
"""Batch 4 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses time.NewTicker to do periodic work every 10ms and stops after ~35ms using time.After, printing how many ticks occurred. Stop the ticker to avoid a leak.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	ticker := time.NewTicker(10 * time.Millisecond)
	defer ticker.Stop() // release the ticker's resources

	done := time.After(35 * time.Millisecond)
	ticks := 0
	for {
		select {
		case <-ticker.C:
			ticks++
		case <-done:
			fmt.Println("ticks:", ticks)
			return
		}
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that decodes a stream of concatenated JSON objects (no enclosing array) using json.Decoder and dec.More(), summing an integer field across all objects. Print the total.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

type event struct {
	Type string `json:"type"`
	N    int    `json:"n"`
}

func main() {
	stream := `{"type":"a","n":1}{"type":"b","n":2}{"type":"c","n":3}`
	dec := json.NewDecoder(strings.NewReader(stream))

	total := 0
	for dec.More() {
		var e event
		if err := dec.Decode(&e); err != nil {
			fmt.Println("decode error:", err)
			return
		}
		total += e.N
	}
	fmt.Println("total n:", total)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that sorts a slice of Person{Name, Age} by ascending age by implementing sort.Interface, and prints the sorted people.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

type Person struct {
	Name string
	Age  int
}

// byAge implements sort.Interface to order people by ascending age.
type byAge []Person

func (a byAge) Len() int           { return len(a) }
func (a byAge) Less(i, j int) bool { return a[i].Age < a[j].Age }
func (a byAge) Swap(i, j int)      { a[i], a[j] = a[j], a[i] }

func main() {
	people := []Person{{"Ada", 36}, {"Tim", 15}, {"Ken", 42}}
	sort.Sort(byAge(people))
	for _, p := range people {
		fmt.Printf("%s (%d)\\n", p.Name, p.Age)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses a compiled regular expression to extract all email addresses (with user, domain, and TLD capture groups) from a string, printing each match's parts.",
        "response": '''```go
package main

import (
	"fmt"
	"regexp"
)

func main() {
	// MustCompile panics at startup on a bad pattern, which is what you want for
	// a constant regex.
	re := regexp.MustCompile(`(\\w+)@(\\w+)\\.(\\w+)`)
	input := "contact ada@example.com or tim@test.org for details"

	for _, m := range re.FindAllStringSubmatch(input, -1) {
		fmt.Printf("full=%s user=%s domain=%s tld=%s\\n", m[0], m[1], m[2], m[3])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a transpose function that transposes a rectangular [][]int matrix and prints the result for a 2x3 matrix.",
        "response": '''```go
package main

import "fmt"

// transpose returns the transpose of a rectangular matrix (rows<->cols).
func transpose(m [][]int) [][]int {
	if len(m) == 0 {
		return nil
	}
	rows, cols := len(m), len(m[0])
	out := make([][]int, cols)
	for i := range out {
		out[i] = make([]int, rows)
		for j := 0; j < rows; j++ {
			out[i][j] = m[j][i]
		}
	}
	return out
}

func main() {
	m := [][]int{
		{1, 2, 3},
		{4, 5, 6},
	}
	fmt.Println(transpose(m)) // [[1 4] [2 5] [3 6]]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing a singly linked list with a push (prepend) method and a method that returns its values as a slice. Push 1, 2, 3 and print the slice.",
        "response": '''```go
package main

import "fmt"

type node struct {
	val  int
	next *node
}

type list struct {
	head *node
}

// push prepends v to the list (O(1)).
func (l *list) push(v int) {
	l.head = &node{val: v, next: l.head}
}

// values walks the list head-to-tail and returns the elements.
func (l *list) values() []int {
	var out []int
	for n := l.head; n != nil; n = n.next {
		out = append(out, n.val)
	}
	return out
}

func main() {
	var l list
	l.push(1)
	l.push(2)
	l.push(3)
	fmt.Println(l.values()) // [3 2 1]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that increments a shared counter from 50 goroutines (200 increments each) using sync/atomic's atomic.Int64, and prints the final value (10000).",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

func main() {
	var counter atomic.Int64
	var wg sync.WaitGroup

	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 200; j++ {
				counter.Add(1)
			}
		}()
	}
	wg.Wait()
	fmt.Println("total:", counter.Load())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating a channel pipeline: a generator stage emits numbers, a square stage maps them, and main ranges over the final channel. Each stage closes its output channel. Print the squares of 2, 3, 4.",
        "response": '''```go
package main

import "fmt"

func gen(nums ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for _, n := range nums {
			out <- n
		}
	}()
	return out
}

func square(in <-chan int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for n := range in {
			out <- n * n
		}
	}()
	return out
}

func main() {
	for v := range square(gen(2, 3, 4)) {
		fmt.Println(v)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that groups words by their first letter into a map[byte][]string and prints each group in sorted key order.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

func main() {
	words := []string{"apple", "banana", "avocado", "cherry", "blueberry"}

	groups := map[byte][]string{}
	for _, w := range words {
		groups[w[0]] = append(groups[w[0]], w)
	}

	keys := make([]byte, 0, len(groups))
	for k := range groups {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool { return keys[i] < keys[j] })

	for _, k := range keys {
		fmt.Printf("%c: %v\\n", k, groups[k])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a sentinel error ErrNotFound that a lookup function wraps with %w, then have main use errors.Is to detect it and print a friendly message.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

// ErrNotFound is a sentinel callers can test for with errors.Is.
var ErrNotFound = errors.New("not found")

func lookup(id int) error {
	if id == 0 {
		return fmt.Errorf("lookup id %d: %w", id, ErrNotFound)
	}
	return nil
}

func main() {
	err := lookup(0)
	if errors.Is(err, ErrNotFound) {
		fmt.Println("handled: the resource is missing")
	}
	fmt.Println("full error:", err)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with generic Filter[T any] and Reduce[T, A any] functions. Use them to keep the even numbers from a slice and sum them, printing both.",
        "response": '''```go
package main

import "fmt"

// Filter returns the elements of s for which keep reports true.
func Filter[T any](s []T, keep func(T) bool) []T {
	var out []T
	for _, v := range s {
		if keep(v) {
			out = append(out, v)
		}
	}
	return out
}

// Reduce folds s into a single accumulator starting from init.
func Reduce[T, A any](s []T, init A, f func(A, T) A) A {
	acc := init
	for _, v := range s {
		acc = f(acc, v)
	}
	return acc
}

func main() {
	nums := []int{1, 2, 3, 4, 5, 6}
	evens := Filter(nums, func(n int) bool { return n%2 == 0 })
	sum := Reduce(evens, 0, func(a, n int) int { return a + n })
	fmt.Println("evens:", evens, "sum:", sum)
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go error-handling code; the retry branch never fires even on a timeout. Explain and fix:\n\n```go\nvar ErrTimeout = errors.New(\"timeout\")\n\nfunc shouldRetry(err error) bool {\n\treturn err == ErrTimeout\n}\n\n// callers do: shouldRetry(fmt.Errorf(\"call api: %w\", ErrTimeout))\n```",
        "response": '''**Bug: `==` doesn't see through wrapping.** Callers wrap the cause with `fmt.Errorf("...: %w", ErrTimeout)`, producing a *new* error value whose identity differs from `ErrTimeout`. `err == ErrTimeout` compares interface identity, so it's false for the wrapped error, and `shouldRetry` returns false even though a timeout really occurred.

**Fix — use `errors.Is`, which unwraps the chain:**

```go
func shouldRetry(err error) bool {
	return errors.Is(err, ErrTimeout)
}
```

`errors.Is` walks the `%w` chain (calling `Unwrap` repeatedly) and returns true if any layer equals `ErrTimeout`. As a rule: compare sentinel errors with `errors.Is`, extract typed errors with `errors.As`, and reserve `==` for errors you know are never wrapped (like `io.EOF` returned directly).''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; `go vet` complains and the counter never increases. Explain both problems and fix:\n\n```go\ntype Counter struct {\n\tmu sync.Mutex\n\tn  int\n}\n\nfunc (c Counter) Inc() {\n\tc.mu.Lock()\n\tc.n++\n\tc.mu.Unlock()\n}\n```",
        "response": '''Two linked problems, both caused by the **value receiver** `func (c Counter) Inc()`:

1. **The increment is lost.** A value receiver copies the whole `Counter`, so `c.n++` mutates the copy; the caller's counter is unchanged.
2. **The mutex is copied (`go vet` error: "Inc passes lock by value").** Copying a `sync.Mutex` is a bug — the copy has its own independent lock state, so it provides no mutual exclusion and can deadlock or race. A `sync.Mutex` must never be copied after first use.

**Fix — use a pointer receiver:**

```go
func (c *Counter) Inc() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.n++
}
```

The pointer receiver operates on the original (so the increment persists) and locks the original's mutex (so concurrent `Inc` calls are actually serialized). As a corollary, always pass `*Counter` around, never `Counter` by value, once it contains a mutex.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; percentage(1, 4) returns 0 instead of 25. Explain and fix:\n\n```go\nfunc percentage(part, total int) float64 {\n\treturn float64(part / total * 100)\n}\n```",
        "response": '''**Bug: integer arithmetic happens before the float conversion.** Inside the parentheses, `part`, `total`, and `100` are all `int`, so `part / total` is *integer* division. For `percentage(1, 4)`, `1 / 4 == 0`, then `0 * 100 == 0`, and only then is the `0` converted to `float64`. The `float64(...)` cast is applied to an already-truncated integer result.

**Fix — convert to float64 *before* dividing:**

```go
func percentage(part, total int) float64 {
	if total == 0 {
		return 0 // avoid division by zero
	}
	return float64(part) / float64(total) * 100
}
```

Now the division is floating-point (`1.0 / 4.0 == 0.25`), giving `25`. I also guarded `total == 0`, which would otherwise panic for integers or yield `+Inf`/`NaN` once it's floating point. General rule: convert operands to the wider type *before* the operation, not after.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go concurrency code; sometimes it prints nothing and Wait returns early. Explain the race and fix:\n\n```go\nfunc process(items []int) {\n\tvar wg sync.WaitGroup\n\tfor _, n := range items {\n\t\tgo func(n int) {\n\t\t\twg.Add(1)\n\t\t\tdefer wg.Done()\n\t\t\tfmt.Println(n)\n\t\t}(n)\n\t}\n\twg.Wait()\n}\n```",
        "response": '''**Bug: `wg.Add(1)` is called *inside* the goroutine.** There's a race between the goroutines running `wg.Add(1)` and the main goroutine reaching `wg.Wait()`. If `Wait()` runs before any goroutine has had a chance to `Add`, the counter is still 0, so `Wait` returns immediately and `process` exits — the goroutines may never run (or run after the function returned). This is exactly the misuse the `sync.WaitGroup` docs warn against.

**Fix — call `Add` before launching the goroutine, from the parent:**

```go
func process(items []int) {
	var wg sync.WaitGroup
	for _, n := range items {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			fmt.Println(n)
		}(n)
	}
	wg.Wait()
}
```

The rule from the `WaitGroup` documentation: calls with a positive delta to `Add` must *happen before* the corresponding `Wait`. Adding in the parent before `go` guarantees the counter reflects every goroutine before `Wait` can observe it.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write table-driven tests with parallel subtests (t.Parallel) for this pure function:\n\n```go\n// Clamp returns v constrained to the inclusive range [lo, hi].\nfunc Clamp(v, lo, hi int) int {\n\tif v < lo {\n\t\treturn lo\n\t}\n\tif v > hi {\n\t\treturn hi\n\t}\n\treturn v\n}\n```",
        "response": '''```go
func TestClamp(t *testing.T) {
	tests := []struct {
		name           string
		v, lo, hi, want int
	}{
		{"within range", 5, 0, 10, 5},
		{"below lo", -3, 0, 10, 0},
		{"above hi", 42, 0, 10, 10},
		{"equal lo", 0, 0, 10, 0},
		{"equal hi", 10, 0, 10, 10},
		{"negative range", -5, -10, -1, -5},
	}

	for _, tt := range tests {
		tt := tt // capture range variable for the closure
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			if got := Clamp(tt.v, tt.lo, tt.hi); got != tt.want {
				t.Errorf("Clamp(%d, %d, %d) = %d, want %d",
					tt.v, tt.lo, tt.hi, got, tt.want)
			}
		})
	}
}
```

Each case runs as its own subtest and calls `t.Parallel()`, so the cases execute concurrently — fine here because `Clamp` is pure and the cases share no state. The `tt := tt` line shadows the loop variable so every parallel closure captures its own case (essential on Go versions before 1.22, and harmless after). The cases pin both boundaries and a negative range to catch off-by-one or sign mistakes.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test that verifies error wrapping for this function using errors.Is:\n\n```go\nvar ErrInsufficientFunds = errors.New(\"insufficient funds\")\n\nfunc Withdraw(balance, amount int) (int, error) {\n\tif amount > balance {\n\t\treturn balance, fmt.Errorf(\"withdraw %d from %d: %w\", amount, balance, ErrInsufficientFunds)\n\t}\n\treturn balance - amount, nil\n}\n```",
        "response": '''```go
func TestWithdraw(t *testing.T) {
	t.Run("success", func(t *testing.T) {
		got, err := Withdraw(100, 30)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != 70 {
			t.Errorf("balance = %d, want 70", got)
		}
	})

	t.Run("insufficient funds", func(t *testing.T) {
		got, err := Withdraw(50, 80)
		if !errors.Is(err, ErrInsufficientFunds) {
			t.Fatalf("err = %v, want wrapped ErrInsufficientFunds", err)
		}
		if got != 50 {
			t.Errorf("balance = %d, want unchanged 50", got)
		}
	})
}
```

The success case checks the happy path. The failure case asserts the contract that matters to callers: the returned error must wrap `ErrInsufficientFunds` so they can branch on it with `errors.Is` — testing the *behavior* (the sentinel is detectable through the wrap) rather than the exact error string, which is brittle. It also verifies the balance is returned unchanged on a rejected withdrawal.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain the difference between buffered and unbuffered channels in Go, using this snippet to illustrate when a send blocks:\n\n```go\nunbuffered := make(chan int)\nbuffered := make(chan int, 2)\n```",
        "response": '''The second argument to `make` is the channel's **buffer capacity**, and it changes when a *send* (`ch <- v`) blocks.

**Unbuffered (`make(chan int)`, capacity 0).** A send blocks until another goroutine is ready to receive, and a receive blocks until another goroutine sends. The send and receive happen at the same instant — the channel is a synchronization point, a "handoff." Sending on an unbuffered channel guarantees the receiver has actually taken the value before the sender proceeds.

**Buffered (`make(chan int, 2)`, capacity 2).** A send succeeds immediately as long as there's free space in the buffer; only when the buffer is full does a send block (until a receiver frees a slot). A receive blocks only when the buffer is empty. So `buffered <- 1` and `buffered <- 2` both return right away without any receiver, but a third send would block until something is received.

Practical implications:
- Use **unbuffered** channels when you need a guarantee that the other side has received the value (tight synchronization / handoff).
- Use a **buffered** channel to decouple producer and consumer speeds, or as a counting semaphore (`make(chan struct{}, N)` limits concurrency to N).
- Both block on **receive** when there's nothing to read; the buffer only affects how tolerant *sends* are.
- Closing matters for both: receiving from a closed channel returns the zero value with `ok == false`; sending on a closed channel panics.''',
    },
]
