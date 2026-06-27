# -*- coding: utf-8 -*-
"""Batch 9 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic Reverse[T any](s []T) that reverses a slice in place, and demonstrate it on a slice of ints.",
        "response": '''```go
package main

import "fmt"

// Reverse reverses s in place using the two-pointer swap.
func Reverse[T any](s []T) {
	for i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {
		s[i], s[j] = s[j], s[i]
	}
}

func main() {
	s := []int{1, 2, 3, 4, 5}
	Reverse(s)
	fmt.Println(s) // [5 4 3 2 1]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that prints an aligned price table using fmt printf width/precision verbs (left-aligned names, right-aligned 2-decimal prices), with a separator line via strings.Repeat.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

func main() {
	names := []string{"apple", "banana", "cherry"}
	prices := map[string]float64{"apple": 1.5, "banana": 0.75, "cherry": 3.2}

	for _, n := range names {
		// %-10s left-aligns in a 10-wide field; %6.2f right-aligns to 2 decimals.
		fmt.Printf("%-10s $%6.2f\\n", n, prices[n])
	}
	fmt.Println(strings.Repeat("-", 18))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that reuses bytes.Buffer objects via a sync.Pool to avoid repeated allocation, with a render function that gets a buffer, uses it, resets it, and returns it to the pool.",
        "response": '''```go
package main

import (
	"bytes"
	"fmt"
	"sync"
)

// bufPool recycles buffers so hot paths don't allocate a new one each call.
var bufPool = sync.Pool{
	New: func() any { return new(bytes.Buffer) },
}

func render(msg string) string {
	buf := bufPool.Get().(*bytes.Buffer)
	defer func() {
		buf.Reset()      // clear before returning so the next user starts clean
		bufPool.Put(buf)
	}()

	buf.WriteByte('[')
	buf.WriteString(msg)
	buf.WriteByte(']')
	return buf.String()
}

func main() {
	fmt.Println(render("hello"))
	fmt.Println(render("world"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a fan-out worker pool: a single job stream is consumed by 3 workers that double each value and emit results; main sums the results. Use channels and sync.WaitGroup and close channels correctly.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	jobs := make(chan int)
	results := make(chan int)

	var wg sync.WaitGroup
	for w := 0; w < 3; w++ { // fan out across 3 workers
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := range jobs {
				results <- j * 2
			}
		}()
	}

	go func() {
		for i := 1; i <= 6; i++ {
			jobs <- i
		}
		close(jobs) // workers drain and exit
	}()

	go func() {
		wg.Wait()
		close(results) // close results once all workers are done
	}()

	sum := 0
	for r := range results {
		sum += r
	}
	fmt.Println("sum of doubled:", sum) // 2*(1+2+3+4+5+6) = 42
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a recursive power(base, exp int) int using fast exponentiation (exponentiation by squaring), and print 2^10 and 3^4.",
        "response": '''```go
package main

import "fmt"

// power computes base^exp for exp >= 0 in O(log exp) multiplications.
func power(base, exp int) int {
	if exp == 0 {
		return 1
	}
	half := power(base, exp/2)
	if exp%2 == 0 {
		return half * half
	}
	return base * half * half
}

func main() {
	fmt.Println(power(2, 10)) // 1024
	fmt.Println(power(3, 4))  // 81
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a mostFrequent(nums []int) (int, int) function that returns the most common element and its count in one pass, and print the result for a sample slice.",
        "response": '''```go
package main

import "fmt"

// mostFrequent returns the element that appears most often and how many times.
// On ties it keeps the first element to reach the maximum count.
func mostFrequent(nums []int) (value, count int) {
	counts := make(map[int]int, len(nums))
	for _, n := range nums {
		counts[n]++
		if counts[n] > count {
			value, count = n, counts[n]
		}
	}
	return value, count
}

func main() {
	v, c := mostFrequent([]int{1, 3, 3, 2, 3, 1})
	fmt.Printf("%d appears %d times\\n", v, c)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a getEnv(key, def string) string helper that reads an environment variable, falling back to a default when it is unset or empty (using os.LookupEnv). Print a port with a default.",
        "response": '''```go
package main

import (
	"fmt"
	"os"
)

// getEnv returns the value of the environment variable key, or def when the
// variable is unset or empty. LookupEnv distinguishes "unset" from "empty".
func getEnv(key, def string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return def
}

func main() {
	port := getEnv("PORT", "8080")
	fmt.Println("listening on port", port)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that unmarshals arbitrary JSON into a map[string]any and reads back a string, a number (as float64), and an array (as []any), printing each.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
)

func main() {
	data := `{"name":"go","version":1.21,"stable":true,"tags":["fast","simple"]}`

	var m map[string]any
	if err := json.Unmarshal([]byte(data), &m); err != nil {
		fmt.Println("error:", err)
		return
	}

	// Into interface{}: JSON numbers become float64, arrays become []any.
	fmt.Println("name:   ", m["name"])
	fmt.Println("version:", m["version"])
	if tags, ok := m["tags"].([]any); ok {
		fmt.Println("tags:   ", len(tags), "items")
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic MaxOf[T cmp.Ordered](first T, rest ...T) T that returns the largest of its arguments, and use it on ints and strings.",
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
)

// MaxOf returns the largest of first and rest. Requiring at least `first`
// guarantees there is always a value to return (no empty-input ambiguity).
func MaxOf[T cmp.Ordered](first T, rest ...T) T {
	best := first
	for _, v := range rest {
		if v > best {
			best = v
		}
	}
	return best
}

func main() {
	fmt.Println(MaxOf(3, 7, 2, 9, 4))            // 9
	fmt.Println(MaxOf("apple", "pear", "fig"))    // pear
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that compares slices for element-wise equality using slices.Equal and checks membership with slices.Contains, printing the results.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	a := []int{1, 2, 3}
	b := []int{1, 2, 3}
	c := []int{1, 2, 4}

	// slices.Equal compares length + each element (you cannot use == on slices).
	fmt.Println("a equal b:", slices.Equal(a, b)) // true
	fmt.Println("a equal c:", slices.Equal(a, c)) // false
	fmt.Println("b has 2:  ", slices.Contains(b, 2))
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it has a data race and sometimes returns fewer elements than expected. Explain and fix:\n\n```go\nfunc squares(n int) []int {\n\tvar out []int\n\tvar wg sync.WaitGroup\n\tfor i := 0; i < n; i++ {\n\t\twg.Add(1)\n\t\tgo func(i int) {\n\t\t\tdefer wg.Done()\n\t\t\tout = append(out, i*i)\n\t\t}(i)\n\t}\n\twg.Wait()\n\treturn out\n}\n```",
        "response": '''**Bug: concurrent `append` to a shared slice is a data race.** Every goroutine reads and writes the same `out` header (and its backing array) with no synchronization. `go test -race` flags it, and concurrent appends can interleave so that two goroutines write the same slot or one's growth clobbers another's — you lose elements and get non-deterministic results.

**Fix A — write into pre-sized, disjoint slots (no lock needed):**

```go
func squares(n int) []int {
	out := make([]int, n)
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			out[i] = i * i // each goroutine owns index i
		}(i)
	}
	wg.Wait()
	return out
}
```

**Fix B — guard the append with a mutex** (when the count isn't known up front):

```go
var mu sync.Mutex
// inside the goroutine:
mu.Lock()
out = append(out, i*i)
mu.Unlock()
```

Prefer Fix A: assigning to a distinct, pre-allocated index needs no lock at all and preserves order. Use the mutex only when results arrive in unknown quantity. For "many results from many goroutines," a buffered channel collected by one goroutine is another clean, race-free pattern.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go error handling; it's brittle. Explain and fix:\n\n```go\nfunc isNotFound(err error) bool {\n\treturn err != nil && err.Error() == \"not found\"\n}\n```",
        "response": '''**Problem: matching errors by their string message.** Comparing `err.Error()` to a literal breaks the moment anything changes the text — and lots of things do. Wrapping with `fmt.Errorf("lookup user %d: %w", id, ErrNotFound)` prepends context, so `err.Error()` becomes `"lookup user 7: not found"` and the exact comparison fails. Rewording the sentinel, translating it, or adding punctuation all silently break callers too.

**Fix — define a sentinel error and test with `errors.Is`:**

```go
var ErrNotFound = errors.New("not found")

func isNotFound(err error) bool {
	return errors.Is(err, ErrNotFound)
}
```

`errors.Is` walks the `%w` wrap chain and compares error *identity*, not text, so it keeps working no matter how much context callers wrap around `ErrNotFound`. For errors that carry data, define a type and use `errors.As`. The string returned by `Error()` is for humans/logs — never branch program logic on it.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go HTTP handler; the status code isn't what the author intended and the server logs a warning. Explain and fix:\n\n```go\nfunc createHandler(w http.ResponseWriter, r *http.Request) {\n\tw.Write([]byte(`{\"created\":true}`))\n\tw.WriteHeader(http.StatusCreated)\n}\n```",
        "response": '''**Bug: `WriteHeader` is called after `Write`.** The first call to `w.Write` implicitly sends the response header with status `200 OK` (and flushes it). The subsequent `w.WriteHeader(http.StatusCreated)` then has no effect — the header is already on the wire — and `net/http` logs `http: superfluous response.WriteHeader call`. So the client receives `200`, not the intended `201 Created`.

**Fix — set headers and status *before* writing the body:**

```go
func createHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated) // status first
	w.Write([]byte(`{"created":true}`))
}
```

The required order is always: (1) set any response headers via `w.Header().Set(...)`, (2) call `w.WriteHeader(status)` once, (3) `w.Write(body)`. Once the body starts, the status and headers are fixed. If you skip `WriteHeader`, the first `Write` defaults the status to `200`.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test that runs concurrent increments and is meaningful under `go test -race`, for this counter:\n\n```go\ntype Counter struct {\n\tmu sync.Mutex\n\tn  int\n}\nfunc (c *Counter) Inc() { c.mu.Lock(); c.n++; c.mu.Unlock() }\nfunc (c *Counter) Value() int { c.mu.Lock(); defer c.mu.Unlock(); return c.n }\n```",
        "response": '''```go
func TestCounterConcurrent(t *testing.T) {
	var c Counter

	const goroutines, perG = 50, 200
	var wg sync.WaitGroup
	for i := 0; i < goroutines; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < perG; j++ {
				c.Inc()
			}
		}()
	}
	wg.Wait()

	if want := goroutines * perG; c.Value() != want {
		t.Errorf("Value() = %d, want %d", c.Value(), want)
	}
}
```

This test does two things. First, the final-value assertion (`50*200 = 10000`) fails if increments are lost to a race — proving the locking actually serializes the writes. Second, and just as important, run it with `go test -race`: the detector instruments `Inc`/`Value` and flags any unsynchronized access, so if someone later removes the mutex the test fails loudly even if the count happens to come out right. Concurrency tests should always be run under `-race` in CI, since a correct-looking result doesn't prove the code is race-free.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a table-driven test that compares the returned slice with the expected slice using slices.Equal, for this function:\n\n```go\n// Evens returns the even numbers from nums, in order.\nfunc Evens(nums []int) []int {\n\tvar out []int\n\tfor _, n := range nums {\n\t\tif n%2 == 0 {\n\t\t\tout = append(out, n)\n\t\t}\n\t}\n\treturn out\n}\n```",
        "response": '''```go
func TestEvens(t *testing.T) {
	tests := []struct {
		name string
		in   []int
		want []int
	}{
		{"mixed", []int{1, 2, 3, 4, 5, 6}, []int{2, 4, 6}},
		{"all odd", []int{1, 3, 5}, nil},
		{"all even", []int{2, 4}, []int{2, 4}},
		{"empty", nil, nil},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Evens(tt.in)
			if !slices.Equal(got, tt.want) {
				t.Errorf("Evens(%v) = %v, want %v", tt.in, got, tt.want)
			}
		})
	}
}
```

`slices.Equal` is the right comparison for slice results — you can't use `==` on slices, and it correctly treats a `nil` slice and an empty slice as equal (both length 0), which matters because `Evens` returns `nil` when nothing matches. The "all odd" and "empty" cases pin that nil-result behavior; the others cover ordering and the all-match path. (For slices of non-comparable elements you'd use `slices.EqualFunc` or `reflect.DeepEqual` instead.)''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain the difference between arrays and slices in Go, using this snippet to show why one copies and the other shares:\n\n```go\narr := [3]int{1, 2, 3}\nsl := []int{1, 2, 3}\nmodify(arr)  // func modify(a [3]int) / func modify(s []int)\nmodify(sl)\n```",
        "response": '''The core difference: **an array is a fixed-size value; a slice is a small header that *references* an underlying array.** This changes copy semantics, length flexibility, and how they behave as function arguments.

**Arrays (`[3]int`)**
- The size is part of the type: `[3]int` and `[4]int` are different, incompatible types. The length is fixed at compile time.
- An array is a *value*. Assigning it or passing it to a function **copies all its elements**. So `func modify(a [3]int)` receives a full copy — mutating `a` inside does **not** affect the caller's `arr`.

**Slices (`[]int`)**
- A slice has no size in its type; its length is dynamic and can grow with `append`.
- A slice is a 3-word header — `{pointer, len, cap}` — that points at a backing array. Copying the *header* (e.g. passing it to `func modify(s []int)`) is cheap and **shares the same backing array**. So mutating `s[i]` inside the function **is** visible to the caller (though appending may reallocate and detach — which is why `append` results must be reassigned).

Practical guidance:
- Use **slices** for almost everything — collections you build up, pass around, and resize. They're the idiomatic Go container.
- Use **arrays** rarely and deliberately: fixed-size data where value semantics help (e.g. a `[32]byte` hash, a small lookup table, or map keys that must be comparable — arrays are comparable with `==`, slices are not).
- Remember the argument-passing consequence: an array parameter is a defensive copy (caller is safe but you pay the copy cost); a slice parameter shares storage (cheap, but the callee can mutate the caller's data).''',
    },
]
