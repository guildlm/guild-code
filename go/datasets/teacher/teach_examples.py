# -*- coding: utf-8 -*-
"""Batch 1 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses a bounded worker pool of 4 goroutines to compute the square of the integers 1..9 concurrently, then prints the sum of the squares. Use channels and sync.WaitGroup; do not leak goroutines.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

// job carries an input value into the pool.
type job struct{ n int }

// worker squares each job's value and sends it to results until jobs is closed.
func worker(wg *sync.WaitGroup, jobs <-chan job, results chan<- int) {
	defer wg.Done()
	for j := range jobs {
		results <- j.n * j.n
	}
}

func main() {
	const workers = 4
	jobs := make(chan job)
	results := make(chan int)

	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go worker(&wg, jobs, results)
	}

	// Feed jobs, then close so workers drain and exit.
	go func() {
		for n := 1; n <= 9; n++ {
			jobs <- job{n: n}
		}
		close(jobs)
	}()

	// Close results once every worker has returned.
	go func() {
		wg.Wait()
		close(results)
	}()

	sum := 0
	for sq := range results {
		sum += sq
	}
	fmt.Println("sum of squares:", sum)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that defines a generic Map[T, U any](s []T, f func(T) U) []U function and uses it to turn a slice of ints into a slice of their string representations, printing the result.",
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
)

// Map applies f to every element of s and returns a new slice of the results.
func Map[T, U any](s []T, f func(T) U) []U {
	out := make([]U, len(s))
	for i, v := range s {
		out[i] = f(v)
	}
	return out
}

func main() {
	nums := []int{1, 2, 3, 4}
	strs := Map(nums, func(n int) string { return strconv.Itoa(n) })
	fmt.Printf("%q\\n", strs)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that runs a slow operation with a 50ms timeout using context.WithTimeout. If the operation (which sleeps 200ms) does not finish in time, print the context error; otherwise print its result.",
        "response": '''```go
package main

import (
	"context"
	"fmt"
	"time"
)

// slowOp simulates work that takes 200ms and respects cancellation.
func slowOp(ctx context.Context) (string, error) {
	select {
	case <-time.After(200 * time.Millisecond):
		return "done", nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	res, err := slowOp(ctx)
	if err != nil {
		fmt.Println("operation failed:", err)
		return
	}
	fmt.Println("operation result:", res)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a custom error type NotFoundError that wraps an underlying error, and demonstrate using errors.Is and errors.As to inspect it. Print whether the error is a NotFoundError and the key it carries.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

// NotFoundError reports that a keyed lookup failed.
type NotFoundError struct {
	Key string
	Err error
}

func (e *NotFoundError) Error() string {
	return fmt.Sprintf("key %q not found: %v", e.Key, e.Err)
}

func (e *NotFoundError) Unwrap() error { return e.Err }

var errStore = errors.New("store miss")

func lookup(key string) error {
	return &NotFoundError{Key: key, Err: errStore}
}

func main() {
	err := lookup("user:42")

	fmt.Println("is store miss:", errors.Is(err, errStore))

	var nfe *NotFoundError
	if errors.As(err, &nfe) {
		fmt.Println("missing key:", nfe.Key)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing a concurrency-safe counter using sync.Mutex. Spawn 100 goroutines that each increment the counter 100 times, wait for them, and print the final value (which must be 10000).",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

// counter is safe for concurrent use by multiple goroutines.
type counter struct {
	mu sync.Mutex
	n  int
}

func (c *counter) inc() {
	c.mu.Lock()
	c.n++
	c.mu.Unlock()
}

func (c *counter) value() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.n
}

func main() {
	var c counter
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 100; j++ {
				c.inc()
			}
		}()
	}
	wg.Wait()
	fmt.Println("final:", c.value())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that decodes a JSON array of users (each with a name and age) from a string, filters out anyone under 18, and prints the names of the remaining adults. Use encoding/json with struct tags.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
)

type user struct {
	Name string `json:"name"`
	Age  int    `json:"age"`
}

func main() {
	const data = `[
		{"name": "Ada", "age": 36},
		{"name": "Tim", "age": 15},
		{"name": "Ken", "age": 42}
	]`

	var users []user
	if err := json.Unmarshal([]byte(data), &users); err != nil {
		fmt.Println("decode error:", err)
		return
	}

	for _, u := range users {
		if u.Age >= 18 {
			fmt.Println(u.Name)
		}
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with an HTTP middleware that logs the method and path of each request and recovers from panics, returning 500. Wire it around a handler that panics on /boom and returns 'ok' otherwise, then exercise it with httptest (no real network).",
        "response": '''```go
package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/httptest"
)

// withMiddleware logs each request and converts panics into 500 responses.
func withMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s", r.Method, r.URL.Path)
		defer func() {
			if rec := recover(); rec != nil {
				log.Printf("recovered: %v", rec)
				http.Error(w, "internal error", http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func app() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/boom", func(http.ResponseWriter, *http.Request) {
		panic("kaboom")
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprint(w, "ok")
	})
	return withMiddleware(mux)
}

func main() {
	h := app()
	for _, path := range []string{"/", "/boom"} {
		rec := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodGet, path, nil)
		h.ServeHTTP(rec, req)
		fmt.Printf("%s -> %d\\n", path, rec.Code)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating a fan-in pattern: two producer goroutines each emit three integers on their own channel, a merge function fans them into a single channel, and main prints the count of received values.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

func producer(values ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for _, v := range values {
			out <- v
		}
	}()
	return out
}

// merge fans multiple input channels into one, closing it when all inputs drain.
func merge(chans ...<-chan int) <-chan int {
	out := make(chan int)
	var wg sync.WaitGroup
	for _, ch := range chans {
		wg.Add(1)
		go func(c <-chan int) {
			defer wg.Done()
			for v := range c {
				out <- v
			}
		}(ch)
	}
	go func() {
		wg.Wait()
		close(out)
	}()
	return out
}

func main() {
	a := producer(1, 2, 3)
	b := producer(4, 5, 6)

	count := 0
	for range merge(a, b) {
		count++
	}
	fmt.Println("received:", count)
}
```''',
    },

    # ---------------- go_reviewer (kept as authored) ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code and identify the bug, explain why it happens, and show the corrected version:\n\n```go\nfunc startWorkers(tasks []string) {\n\tvar wg sync.WaitGroup\n\tfor _, t := range tasks {\n\t\twg.Add(1)\n\t\tgo func() {\n\t\t\tdefer wg.Done()\n\t\t\tfmt.Println(t)\n\t\t}()\n\t}\n\twg.Wait()\n}\n```",
        "response": '''**Bug: loop-variable capture.** Each goroutine closes over the single loop variable `t`, not a per-iteration copy. By the time the goroutines run, the loop has usually finished, so they all observe the *last* value of `t` (and you'll see duplicated/last-only output rather than every task).

Note: in Go 1.22+ the loop variable is per-iteration, so this specific snippet is safe there — but relying on that is fragile and breaks on older toolchains and in linters. Make the intent explicit.

**Fix — pass the value as an argument (works on every Go version):**

```go
func startWorkers(tasks []string) {
	var wg sync.WaitGroup
	for _, t := range tasks {
		wg.Add(1)
		go func(task string) {
			defer wg.Done()
			fmt.Println(task)
		}(t)
	}
	wg.Wait()
}
```

Passing `t` as the `task` argument binds the current value at call time, so each goroutine prints its own task. (Equivalently, you could write `t := t` inside the loop before the goroutine.)''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go function for correctness and idiom issues, and show a corrected version:\n\n```go\nfunc CountWords(r io.Reader) map[string]int {\n\tcounts := map[string]int{}\n\tscanner := bufio.NewScanner(r)\n\tscanner.Split(bufio.ScanWords)\n\tfor scanner.Scan() {\n\t\tcounts[scanner.Text()]++\n\t}\n\treturn counts\n}\n```",
        "response": '''The logic is correct and the map is initialized properly (so the `counts[word]++` writes are safe). The real issue is **a swallowed error**: `bufio.Scanner` stops silently on read errors, and the caller has no way to know the count is partial.

**Idiomatic fix — return the scanner error:**

```go
func CountWords(r io.Reader) (map[string]int, error) {
	counts := make(map[string]int)
	scanner := bufio.NewScanner(r)
	scanner.Split(bufio.ScanWords)
	for scanner.Scan() {
		counts[scanner.Text()]++
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("count words: %w", err)
	}
	return counts, nil
}
```

Key points:
- Return `(map[string]int, error)` and check `scanner.Err()` after the loop — that's the documented way to detect read failures.
- Wrap with `%w` so callers can `errors.Is`/`errors.As` the underlying cause.
- `make(map[string]int)` and `map[string]int{}` are equivalent; either is fine.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code for a concurrency problem and show how to fix it:\n\n```go\nfunc sumAll(nums []int) int {\n\ttotal := 0\n\tvar wg sync.WaitGroup\n\tfor _, n := range nums {\n\t\twg.Add(1)\n\t\tgo func(v int) {\n\t\t\tdefer wg.Done()\n\t\t\ttotal += v\n\t\t}(v)\n\t}\n\twg.Wait()\n\treturn total\n}\n```",
        "response": '''**Data race.** Multiple goroutines read-modify-write the shared `total` without synchronization, so `total += v` is not atomic. Results are non-deterministic and `go test -race` will flag it. (The snippet also references `v` in the `go func(...)(v)` call but ranges over `n` — it wouldn't compile as written; the value should come from the range.)

**Fix A — sync/atomic (simple accumulator):**

```go
func sumAll(nums []int) int {
	var total int64
	var wg sync.WaitGroup
	for _, n := range nums {
		wg.Add(1)
		go func(v int) {
			defer wg.Done()
			atomic.AddInt64(&total, int64(v))
		}(n)
	}
	wg.Wait()
	return int(total)
}
```

**Better — don't spawn a goroutine per element at all.** For a simple sum the concurrency is pure overhead; a plain loop is faster and race-free:

```go
func sumAll(nums []int) int {
	total := 0
	for _, n := range nums {
		total += n
	}
	return total
}
```

Reach for goroutines only when the per-item work is expensive enough to dwarf the scheduling and synchronization cost.''',
    },

    # ---------------- go_tester (kept as authored) ----------------
    {
        "role": "go_tester",
        "instruction": "Given this function, write a thorough table-driven test using subtests:\n\n```go\n// IsValidUsername reports whether s is 3-16 chars of [a-z0-9_].\nfunc IsValidUsername(s string) bool {\n\tif len(s) < 3 || len(s) > 16 {\n\t\treturn false\n\t}\n\tfor _, r := range s {\n\t\tif !(r >= 'a' && r <= 'z' || r >= '0' && r <= '9' || r == '_') {\n\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\n```",
        "response": '''```go
func TestIsValidUsername(t *testing.T) {
	tests := []struct {
		name string
		in   string
		want bool
	}{
		{"typical", "alice_99", true},
		{"min length", "abc", true},
		{"max length", "abcdefghij012345", true},
		{"too short", "ab", false},
		{"too long", "abcdefghij0123456", false},
		{"empty", "", false},
		{"uppercase rejected", "Alice", false},
		{"space rejected", "alice 1", false},
		{"hyphen rejected", "al-ice", false},
		{"unicode rejected", "alicé", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := IsValidUsername(tt.in); got != tt.want {
				t.Errorf("IsValidUsername(%q) = %v, want %v", tt.in, got, tt.want)
			}
		})
	}
}
```

The cases deliberately cover the boundaries (length 2/3 and 16/17), the allowed character classes, and rejections for uppercase, spaces, punctuation, and multi-byte runes — the last is important because ranging over a string yields runes, so an accented character is a single iteration that must fail the class check.''',
    },

    # ---------------- go_explainer (kept as authored) ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain what this Go code does and how the select statement behaves:\n\n```go\nfunc first(a, b <-chan int) int {\n\tselect {\n\tcase v := <-a:\n\t\treturn v\n\tcase v := <-b:\n\t\treturn v\n\t}\n}\n```",
        "response": '''This function returns the first integer that becomes available from either of two receive-only channels, `a` or `b`.

How it works:
- `select` blocks until **at least one** of its communication cases can proceed — here, until a value can be received from `a` or from `b`.
- Whichever channel delivers a value first has its case chosen; the received value is bound to `v` and returned immediately. The other case is abandoned (no value is taken from the other channel).
- If **both** channels are ready at the same moment, `select` picks one of the ready cases **at random** (uniformly), which prevents starvation between the two sources.
- Because there is no `default` case, the `select` is blocking: if neither channel is ready, the goroutine parks until one is.

A practical caveat: the value not chosen stays in its channel, and this function never reads it. If a caller relies on draining both channels, this "take the first" pattern would leave the loser's value (and potentially its sender goroutine) pending — usually you'd combine it with a `context` or timeout case to avoid blocking forever.''',
    },
]
