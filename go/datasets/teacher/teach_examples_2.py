# -*- coding: utf-8 -*-
"""Batch 2 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic BinarySearch[T cmp.Ordered](s []T, target T) (int, bool) that returns the index and whether target was found in the sorted slice. Demonstrate it on a sorted []int for a present and an absent value.",
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
)

// BinarySearch returns the index of target in the sorted slice s and whether it
// was found. On a miss it returns the index where target could be inserted.
func BinarySearch[T cmp.Ordered](s []T, target T) (int, bool) {
	lo, hi := 0, len(s)
	for lo < hi {
		mid := int(uint(lo+hi) >> 1)
		switch {
		case s[mid] < target:
			lo = mid + 1
		case s[mid] > target:
			hi = mid
		default:
			return mid, true
		}
	}
	return lo, false
}

func main() {
	s := []int{1, 3, 5, 7, 9, 11}
	for _, t := range []int{7, 8} {
		if i, ok := BinarySearch(s, t); ok {
			fmt.Printf("%d found at index %d\\n", t, i)
		} else {
			fmt.Printf("%d not found (insert at %d)\\n", t, i)
		}
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining a generic Stack[T any] with Push, Pop (returning an error when empty), and Len. Demonstrate pushing and popping strings and handling the empty-pop error.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

// Stack is a simple generic LIFO stack.
type Stack[T any] struct {
	items []T
}

func (s *Stack[T]) Push(v T) { s.items = append(s.items, v) }

func (s *Stack[T]) Pop() (T, error) {
	var zero T
	if len(s.items) == 0 {
		return zero, errors.New("pop from empty stack")
	}
	last := len(s.items) - 1
	v := s.items[last]
	s.items = s.items[:last]
	return v, nil
}

func (s *Stack[T]) Len() int { return len(s.items) }

func main() {
	var st Stack[string]
	st.Push("a")
	st.Push("b")
	for st.Len() > 0 {
		v, _ := st.Pop()
		fmt.Println(v)
	}
	if _, err := st.Pop(); err != nil {
		fmt.Println("error:", err)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that lazily initializes a config exactly once using sync.Once, even when accessed concurrently from many goroutines. Print a marker from inside the once-body to prove it runs a single time.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

type config struct{ Env string }

var (
	once sync.Once
	cfg  *config
)

// loadConfig returns the singleton config, initializing it on first use only.
func loadConfig() *config {
	once.Do(func() {
		cfg = &config{Env: "production"}
		fmt.Println("config loaded once")
	})
	return cfg
}

func main() {
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_ = loadConfig()
		}()
	}
	wg.Wait()
	fmt.Println("env:", loadConfig().Env)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that fetches 5 resources concurrently (simulated; even ids fail), collecting each result and error into per-index slices so there is no data race, then prints successes and failures.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

// fetch simulates a network fetch; even ids fail.
func fetch(id int) (string, error) {
	if id%2 == 0 {
		return "", fmt.Errorf("resource %d unavailable", id)
	}
	return fmt.Sprintf("data-%d", id), nil
}

func main() {
	ids := []int{1, 2, 3, 4, 5}
	results := make([]string, len(ids))
	errs := make([]error, len(ids))

	var wg sync.WaitGroup
	for i, id := range ids {
		wg.Add(1)
		// Each goroutine writes only its own index -> no shared mutation.
		go func(i, id int) {
			defer wg.Done()
			results[i], errs[i] = fetch(id)
		}(i, id)
	}
	wg.Wait()

	for i, id := range ids {
		if errs[i] != nil {
			fmt.Printf("id %d: error: %v\\n", id, errs[i])
			continue
		}
		fmt.Printf("id %d: %s\\n", id, results[i])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing a min-heap priority queue of ints using container/heap. Push a few values, then pop them and print them in ascending order.",
        "response": '''```go
package main

import (
	"container/heap"
	"fmt"
)

// minHeap implements heap.Interface as a min-heap of ints.
type minHeap []int

func (h minHeap) Len() int           { return len(h) }
func (h minHeap) Less(i, j int) bool { return h[i] < h[j] }
func (h minHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *minHeap) Push(x any) { *h = append(*h, x.(int)) }

func (h *minHeap) Pop() any {
	old := *h
	n := len(old)
	v := old[n-1]
	*h = old[:n-1]
	return v
}

func main() {
	h := &minHeap{5, 2, 8, 1}
	heap.Init(h)
	heap.Push(h, 3)
	for h.Len() > 0 {
		fmt.Print(heap.Pop(h), " ")
	}
	fmt.Println()
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that computes Fibonacci numbers using a memoized recursive closure backed by a map, printing F(0) through F(10).",
        "response": '''```go
package main

import "fmt"

func main() {
	memo := map[int]int{0: 0, 1: 1}

	var fib func(n int) int
	fib = func(n int) int {
		if v, ok := memo[n]; ok {
			return v
		}
		v := fib(n-1) + fib(n-2)
		memo[n] = v
		return v
	}

	for i := 0; i <= 10; i++ {
		fmt.Print(fib(i), " ")
	}
	fmt.Println()
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining a generic Set[T comparable] backed by a map[T]struct{} with Add and Has methods. Use it to collect the unique words from a slice and print them sorted.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// Set is a generic set backed by a map; struct{} values use no memory.
type Set[T comparable] map[T]struct{}

func (s Set[T]) Add(v T)      { s[v] = struct{}{} }
func (s Set[T]) Has(v T) bool { _, ok := s[v]; return ok }

func main() {
	s := make(Set[string])
	for _, w := range []string{"go", "rust", "go", "c", "rust"} {
		s.Add(w)
	}

	keys := make([]string, 0, len(s))
	for k := range s {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	fmt.Println("unique:", keys)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a retry helper retry(attempts int, base time.Duration, fn func() error) error that retries with exponential backoff and wraps the final error. Demonstrate it succeeding on the third attempt.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
	"time"
)

// retry calls fn up to attempts times, sleeping base*2^i between tries.
func retry(attempts int, base time.Duration, fn func() error) error {
	var err error
	for i := 0; i < attempts; i++ {
		if err = fn(); err == nil {
			return nil
		}
		if i < attempts-1 {
			time.Sleep(base * time.Duration(1<<i))
		}
	}
	return fmt.Errorf("after %d attempts: %w", attempts, err)
}

func main() {
	calls := 0
	err := retry(3, time.Millisecond, func() error {
		calls++
		if calls < 3 {
			return errors.New("transient failure")
		}
		return nil
	})
	fmt.Printf("calls=%d err=%v\\n", calls, err)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that counts word frequencies in a string (case-insensitive) and prints the words sorted by descending count, breaking ties alphabetically.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
	"strings"
)

func main() {
	text := "the quick brown fox the lazy dog the fox"

	counts := map[string]int{}
	for _, w := range strings.Fields(text) {
		counts[strings.ToLower(w)]++
	}

	type pair struct {
		word  string
		count int
	}
	pairs := make([]pair, 0, len(counts))
	for w, c := range counts {
		pairs = append(pairs, pair{w, c})
	}
	sort.Slice(pairs, func(i, j int) bool {
		if pairs[i].count != pairs[j].count {
			return pairs[i].count > pairs[j].count
		}
		return pairs[i].word < pairs[j].word
	})

	for _, p := range pairs {
		fmt.Printf("%s: %d\\n", p.word, p.count)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that performs a breadth-first traversal of a directed graph represented as map[int][]int, returning the visitation order from a start node. Print the order from node 1.",
        "response": '''```go
package main

import "fmt"

// bfs returns the nodes reachable from start in breadth-first order.
func bfs(graph map[int][]int, start int) []int {
	visited := map[int]bool{start: true}
	queue := []int{start}
	var order []int

	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		order = append(order, node)
		for _, next := range graph[node] {
			if !visited[next] {
				visited[next] = true
				queue = append(queue, next)
			}
		}
	}
	return order
}

func main() {
	graph := map[int][]int{
		1: {2, 3},
		2: {4},
		3: {4, 5},
		4: {6},
		5: {6},
	}
	fmt.Println(bfs(graph, 1))
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code and explain the resource problem, then show the fix:\n\n```go\nfunc processAll(paths []string) error {\n\tfor _, p := range paths {\n\t\tf, err := os.Open(p)\n\t\tif err != nil {\n\t\t\treturn err\n\t\t}\n\t\tdefer f.Close()\n\t\tdata, _ := io.ReadAll(f)\n\t\tfmt.Println(len(data))\n\t}\n\treturn nil\n}\n```",
        "response": '''**Bug: `defer` accumulates until the *function* returns, not each loop iteration.** Every opened file stays open for the whole loop, so processing many paths leaks file descriptors and can hit the OS open-file limit (`too many open files`). The ignored error from `io.ReadAll` is a secondary issue.

**Fix — give each file its own scope so it closes promptly:**

```go
func processAll(paths []string) error {
	for _, p := range paths {
		if err := processOne(p); err != nil {
			return err
		}
	}
	return nil
}

func processOne(p string) error {
	f, err := os.Open(p)
	if err != nil {
		return err
	}
	defer f.Close() // runs when processOne returns -> once per file

	data, err := io.ReadAll(f)
	if err != nil {
		return fmt.Errorf("read %s: %w", p, err)
	}
	fmt.Println(len(data))
	return nil
}
```

Extracting the body into `processOne` makes `defer f.Close()` fire at the end of *each* file, and it also lets you handle (and wrap) the read error instead of discarding it.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; the caller is surprised that err != nil even on success. Explain why and fix it:\n\n```go\ntype ValidationError struct{ msg string }\n\nfunc (e *ValidationError) Error() string { return e.msg }\n\nfunc validate(n int) error {\n\tvar e *ValidationError\n\tif n < 0 {\n\t\te = &ValidationError{msg: \"negative\"}\n\t}\n\treturn e\n}\n```",
        "response": '''**Bug: the typed-nil interface trap.** `validate` returns `e`, a `*ValidationError`. When `n >= 0`, `e` is a nil *pointer* — but returning it as an `error` produces an interface value whose **type** is `*ValidationError` and whose **value** is nil. An interface is only equal to `nil` when *both* its type and value are nil, so `validate(5) != nil` is true and callers see a phantom error.

**Fix — return `nil` explicitly, never a typed nil pointer:**

```go
func validate(n int) error {
	if n < 0 {
		return &ValidationError{msg: "negative"}
	}
	return nil
}
```

Rule of thumb: don't declare a concrete error pointer and return it across an `error` interface boundary. Return the literal `nil` on the success path, or only build the concrete value when you actually have an error.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go HTTP client helper for a leak and fix it:\n\n```go\nfunc get(url string) ([]byte, error) {\n\tresp, err := http.Get(url)\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\treturn io.ReadAll(resp.Body)\n}\n```",
        "response": '''**Bug: `resp.Body` is never closed**, so the underlying TCP connection can't be reused or released — under load this leaks connections and file descriptors. You should also check the read error and, often, the status code.

**Fix:**

```go
func get(url string) ([]byte, error) {
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close() // always, after the error check

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get %s: status %d", url, resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	return body, nil
}
```

Key points: `defer resp.Body.Close()` goes immediately *after* confirming `err == nil` (when `err != nil`, `resp` may be nil and dereferencing it would panic). Closing the body lets `net/http` reuse the keep-alive connection.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Given this function, write a thorough table-driven test that covers both valid inputs and error cases:\n\n```go\n// ParseRatio parses strings like \"3/4\" into a float64.\nfunc ParseRatio(s string) (float64, error) {\n\tparts := strings.SplitN(s, \"/\", 2)\n\tif len(parts) != 2 {\n\t\treturn 0, fmt.Errorf(\"bad ratio %q\", s)\n\t}\n\tnum, err := strconv.Atoi(parts[0])\n\tif err != nil {\n\t\treturn 0, err\n\t}\n\tden, err := strconv.Atoi(parts[1])\n\tif err != nil {\n\t\treturn 0, err\n\t}\n\tif den == 0 {\n\t\treturn 0, errors.New(\"division by zero\")\n\t}\n\treturn float64(num) / float64(den), nil\n}\n```",
        "response": '''```go
func TestParseRatio(t *testing.T) {
	tests := []struct {
		name    string
		in      string
		want    float64
		wantErr bool
	}{
		{"simple", "3/4", 0.75, false},
		{"whole", "6/2", 3, false},
		{"negative numerator", "-1/2", -0.5, false},
		{"missing slash", "34", 0, true},
		{"non-numeric numerator", "a/2", 0, true},
		{"non-numeric denominator", "3/b", 0, true},
		{"division by zero", "3/0", 0, true},
		{"empty", "", 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseRatio(tt.in)
			if (err != nil) != tt.wantErr {
				t.Fatalf("ParseRatio(%q) err = %v, wantErr %v", tt.in, err, tt.wantErr)
			}
			if !tt.wantErr && got != tt.want {
				t.Errorf("ParseRatio(%q) = %v, want %v", tt.in, got, tt.want)
			}
		})
	}
}
```

The cases separate the two axes — whether an error is expected (`wantErr`) and, only on the success path, the numeric result. Error inputs cover each failure branch in the function: missing `/`, a non-numeric numerator, a non-numeric denominator, and an explicit zero denominator. Using `t.Fatalf` for the error-mismatch check avoids a misleading second failure when `err` is unexpectedly non-nil.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a test using net/http/httptest for this handler, asserting the status code and JSON body:\n\n```go\nfunc PingHandler(w http.ResponseWriter, r *http.Request) {\n\tw.Header().Set(\"Content-Type\", \"application/json\")\n\tjson.NewEncoder(w).Encode(map[string]bool{\"pong\": true})\n}\n```",
        "response": '''```go
func TestPingHandler(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/ping", nil)
	rec := httptest.NewRecorder()

	PingHandler(rec, req)

	res := rec.Result()
	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.StatusCode, http.StatusOK)
	}
	if ct := res.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}

	var body map[string]bool
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if !body["pong"] {
		t.Errorf("body = %v, want pong=true", body)
	}
}
```

`httptest.NewRecorder` captures everything the handler writes without binding a real port, so the test is fast and hermetic. We assert all three contracts of the handler: the 200 status, the `application/json` content type, and the decoded JSON payload. Remember to close `res.Body` even for an in-memory recorder result.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain how defer, panic, and recover interact in this Go code, and what it prints:\n\n```go\nfunc safeDivide(a, b int) (result int, err error) {\n\tdefer func() {\n\t\tif r := recover(); r != nil {\n\t\t\terr = fmt.Errorf(\"recovered: %v\", r)\n\t\t}\n\t}()\n\treturn a / b, nil\n}\n```",
        "response": '''This function divides `a` by `b` but turns the runtime panic from a divide-by-zero into a normal `error` return instead of crashing the program.

The mechanics, step by step:
- The `defer`red function is registered as soon as `safeDivide` starts, and it runs no matter how the function exits — normal return *or* panic.
- If `b != 0`, `a / b` succeeds, the function returns normally, then the deferred closure runs: `recover()` returns `nil` (no panic in progress), so the `if` body is skipped and the original return values stand. You get `(a/b, nil)`.
- If `b == 0`, `a / b` triggers a runtime panic. Normal execution stops and Go begins unwinding, running deferred functions. Here `recover()` returns the panic value (a runtime error), which is non-nil, so the closure assigns to `err`.
- The crucial detail is the **named return values** `(result int, err error)`. Because they're named, the deferred closure can assign to `err` *after* the panic, and that assignment becomes the function's actual return value. With unnamed returns there'd be no way to set the result during recovery.

So `safeDivide(10, 2)` returns `(5, nil)`, and `safeDivide(10, 0)` returns `(0, "recovered: runtime error: integer divide by zero")`. Idiomatically, `recover` should only be used like this — at a well-defined boundary to convert a panic into an error — not as general control flow.''',
    },
    {
        "role": "go_explainer",
        "instruction": "Explain why this Go code can unexpectedly modify the original slice, and how append's backing-array sharing causes it:\n\n```go\nfunc main() {\n\ta := []int{1, 2, 3, 4, 5}\n\tb := a[:3]\n\tb = append(b, 99)\n\tfmt.Println(a)\n}\n```",
        "response": '''This prints `[1 2 3 99 5]` — appending to `b` silently overwrote `a[3]`. The reason is how slices and `append` share a backing array.

- A slice is a small header: a pointer to a backing array, a length, and a capacity. `a` has length 5 and capacity 5, pointing at the array `[1 2 3 4 5]`.
- `b := a[:3]` creates a *new header* with length 3 but the **same backing array pointer**, and its capacity extends to the end of that array — so `cap(b) == 5`, not 3.
- `append(b, 99)` checks `len(b) < cap(b)` (3 < 5), so there's room without allocating. It writes `99` into the next slot of the **shared** array — index 3 — which is also `a[3]`. That's why `a` changes to `[1 2 3 99 5]`.

If `cap(b)` had been exactly 3, `append` would have allocated a fresh array and copied, leaving `a` untouched — which is why this bug is intermittent and surprising.

**How to avoid it:** force `append` to copy by capping the slice with a three-index slice, `b := a[:3:3]` (length 3, capacity 3), or copy explicitly with `b := slices.Clone(a[:3])`. Either makes `b` independent so appends never reach back into `a`.''',
    },
]
