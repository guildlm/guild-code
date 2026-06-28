# -*- coding: utf-8 -*-
"""Batch 20 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Weighted to the thin specialists (go_tester, go_reviewer) and to EDIT/refactor
tasks for go_generator — the "düzenleyebilsin" capability: given existing code +
a change request, emit the full corrected program. go_generator responses are
complete, stdlib-only, compilable programs (compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator — EDIT / refactor (compile-verified) -------
    {
        "role": "go_generator",
        "instruction": (
            "Edit this Go program so Divide returns an error instead of panicking "
            "on division by zero, wrapping a sentinel ErrDivideByZero, and main "
            "prints the error path. Original:\n"
            "```go\npackage main\nimport \"fmt\"\nfunc Divide(a, b int) int { return a / b }\n"
            "func main() { fmt.Println(Divide(10, 2)) }\n```"
        ),
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

// ErrDivideByZero is returned by Divide when the divisor is zero.
var ErrDivideByZero = errors.New("divide by zero")

// Divide returns a/b, or ErrDivideByZero instead of panicking when b == 0.
func Divide(a, b int) (int, error) {
	if b == 0 {
		return 0, ErrDivideByZero
	}
	return a / b, nil
}

func main() {
	if q, err := Divide(10, 2); err == nil {
		fmt.Println("10/2 =", q)
	}
	if _, err := Divide(1, 0); err != nil {
		fmt.Println("error:", err)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Refactor this pre-Go-1.22 program: each goroutine captures the loop "
            "variable, so results are wrong. Make it correct on any Go version, "
            "keeping the concurrency. Original:\n"
            "```go\npackage main\nimport (\n\t\"fmt\"\n\t\"sync\"\n)\nfunc main() {\n"
            "\txs := []int{1, 2, 3, 4}\n\tout := make([]int, len(xs))\n\tvar wg sync.WaitGroup\n"
            "\tfor i, x := range xs {\n\t\twg.Add(1)\n\t\tgo func() { defer wg.Done(); out[i] = x * x }()\n"
            "\t}\n\twg.Wait()\n\tfmt.Println(out)\n}\n```"
        ),
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

// squareAll returns the squares of xs computed concurrently. Passing i and x as
// arguments gives each goroutine its own copy, so the result is correct even on
// Go versions before 1.22 (where the range variable was shared).
func squareAll(xs []int) []int {
	out := make([]int, len(xs))
	var wg sync.WaitGroup
	for i, x := range xs {
		wg.Add(1)
		go func(idx, val int) {
			defer wg.Done()
			out[idx] = val * val
		}(i, x)
	}
	wg.Wait()
	return out
}

func main() {
	fmt.Println(squareAll([]int{1, 2, 3, 4}))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this Go function to respect cancellation: add a context.Context "
            "parameter so the caller can time it out, and demonstrate a timeout in "
            "main. Original:\n```go\npackage main\nimport (\n\t\"fmt\"\n\t\"time\"\n)\n"
            "func fetch(d time.Duration) string {\n\ttime.Sleep(d)\n\treturn \"ok\"\n}\n"
            "func main() { fmt.Println(fetch(time.Millisecond)) }\n```"
        ),
        "response": '''```go
package main

import (
	"context"
	"errors"
	"fmt"
	"time"
)

// fetch now selects on ctx.Done so a caller can cancel or time it out.
func fetch(ctx context.Context, d time.Duration) (string, error) {
	select {
	case <-time.After(d):
		return "ok", nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()
	if _, err := fetch(ctx, 50*time.Millisecond); errors.Is(err, context.DeadlineExceeded) {
		fmt.Println("timed out as expected")
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this program to fix the nil-map panic and make Set safe to call "
            "on a zero-value Registry. Original:\n```go\npackage main\nimport \"fmt\"\n"
            "type Registry struct{ m map[string]int }\nfunc (r *Registry) Set(k string, v int) { r.m[k] = v }\n"
            "func main() {\n\tvar r Registry\n\tr.Set(\"a\", 1)\n\tfmt.Println(r.m[\"a\"])\n}\n```"
        ),
        "response": '''```go
package main

import "fmt"

type Registry struct{ m map[string]int }

// Set lazily initialises the map so a zero-value Registry is usable without a
// constructor — writing to a nil map panics, so we allocate on first use.
func (r *Registry) Set(k string, v int) {
	if r.m == nil {
		r.m = make(map[string]int)
	}
	r.m[k] = v
}

func main() {
	var r Registry
	r.Set("a", 1)
	fmt.Println(r.m["a"])
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic Stack[T any] (Push, Pop "
            "returning (T, bool)), demonstrating it with ints in main. Standard "
            "library only."
        ),
        "response": '''```go
package main

import "fmt"

// Stack is a simple LIFO stack of any element type.
type Stack[T any] struct{ items []T }

// Push appends v to the top of the stack.
func (s *Stack[T]) Push(v T) { s.items = append(s.items, v) }

// Pop removes and returns the top element; ok is false when the stack is empty.
func (s *Stack[T]) Pop() (T, bool) {
	var zero T
	if len(s.items) == 0 {
		return zero, false
	}
	v := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return v, true
}

func main() {
	var s Stack[int]
	s.Push(1)
	s.Push(2)
	if v, ok := s.Pop(); ok {
		fmt.Println("popped:", v)
	}
}
```''',
    },

    # ---------------- go_tester (authored; judged, not isolated-compiled) -----
    {
        "role": "go_tester",
        "instruction": (
            "Write thorough table-driven Go tests for this function (package "
            "strkit). Cover ASCII, unicode, and the empty string.\n```go\n"
            "package strkit\nfunc Reverse(s string) string {\n\tr := []rune(s)\n"
            "\tfor i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n\t\tr[i], r[j] = r[j], r[i]\n"
            "\t}\n\treturn string(r)\n}\n```"
        ),
        "response": '''```go
package strkit

import "testing"

func TestReverse(t *testing.T) {
	tests := []struct {
		name, in, want string
	}{
		{"empty", "", ""},
		{"single", "x", "x"},
		{"ascii", "hello", "olleh"},
		{"unicode", "héllo", "olléh"},
		{"cjk", "世界", "界世"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Reverse(tt.in); got != tt.want {
				t.Errorf("Reverse(%q) = %q, want %q", tt.in, got, tt.want)
			}
		})
	}
}

func TestReverseTwiceIsIdentity(t *testing.T) {
	for _, s := range []string{"", "abc", "héllo 世界"} {
		if got := Reverse(Reverse(s)); got != s {
			t.Errorf("Reverse(Reverse(%q)) = %q, want %q", s, got, s)
		}
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write httptest-based Go tests (package api) for this handler, covering "
            "the 200 and 404 paths.\n```go\npackage api\nimport (\n\t\"net/http\"\n)\n"
            "func Health(w http.ResponseWriter, r *http.Request) {\n\tif r.URL.Path != \"/health\" {\n"
            "\t\thttp.NotFound(w, r)\n\t\treturn\n\t}\n\tw.WriteHeader(http.StatusOK)\n"
            "\tw.Write([]byte(\"ok\"))\n}\n```"
        ),
        "response": '''```go
package api

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealth(t *testing.T) {
	tests := []struct {
		name, path string
		wantCode   int
		wantBody   string
	}{
		{"ok", "/health", http.StatusOK, "ok"},
		{"not found", "/nope", http.StatusNotFound, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, tt.path, nil)
			rec := httptest.NewRecorder()
			Health(rec, req)
			if rec.Code != tt.wantCode {
				t.Fatalf("code = %d, want %d", rec.Code, tt.wantCode)
			}
			if tt.wantBody != "" {
				body, _ := io.ReadAll(rec.Result().Body)
				if string(body) != tt.wantBody {
					t.Errorf("body = %q, want %q", body, tt.wantBody)
				}
			}
		})
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package mathx) for ParsePort that assert both the "
            "happy path and that out-of-range / non-numeric inputs wrap "
            "ErrBadPort, using errors.Is.\n```go\npackage mathx\n// var ErrBadPort = errors.New(\"bad port\")\n"
            "// func ParsePort(s string) (int, error)\n```"
        ),
        "response": '''```go
package mathx

import (
	"errors"
	"testing"
)

func TestParsePortValid(t *testing.T) {
	for _, s := range []string{"1", "8080", "65535"} {
		if _, err := ParsePort(s); err != nil {
			t.Errorf("ParsePort(%q) unexpected error: %v", s, err)
		}
	}
}

func TestParsePortInvalidWrapsSentinel(t *testing.T) {
	for _, s := range []string{"0", "65536", "-1", "abc", ""} {
		if _, err := ParsePort(s); !errors.Is(err, ErrBadPort) {
			t.Errorf("ParsePort(%q) error = %v, want wraps ErrBadPort", s, err)
		}
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write a concurrency test (package counter, runnable under -race) that "
            "proves Counter.Inc is safe under 100 concurrent goroutines.\n```go\n"
            "package counter\n// func NewCounter() *Counter\n// func (c *Counter) Inc(key string)\n"
            "// func (c *Counter) Get(key string) int\n```"
        ),
        "response": '''```go
package counter

import (
	"sync"
	"testing"
)

func TestCounterConcurrentInc(t *testing.T) {
	c := NewCounter()
	const n = 100
	var wg sync.WaitGroup
	wg.Add(n)
	for i := 0; i < n; i++ {
		go func() {
			defer wg.Done()
			c.Inc("k")
		}()
	}
	wg.Wait()
	if got := c.Get("k"); got != n {
		t.Errorf("Get(k) = %d, want %d", got, n)
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) --------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this Go code for a real bug:\n```go\nfunc Sum(nums []int) int {\n"
            "\tvar total int\n\tfor i := 1; i <= len(nums); i++ {\n\t\ttotal += nums[i]\n"
            "\t}\n\treturn total\n}\n```"
        ),
        "response": (
            "**Bug: off-by-one that indexes out of bounds.** The loop runs `i` from "
            "`1` to `len(nums)` inclusive. Two problems: it skips `nums[0]`, and on "
            "the last iteration `i == len(nums)` indexes one past the end, so "
            "`nums[i]` panics with `index out of range`.\n\n"
            "Use a `range` loop, which visits every element by value and can never "
            "go out of bounds:\n\n```go\nfunc Sum(nums []int) int {\n\ttotal := 0\n"
            "\tfor _, n := range nums {\n\t\ttotal += n\n\t}\n\treturn total\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this error handling:\n```go\nvar ErrNotFound = errors.New(\"not found\")\n"
            "func Lookup(id int) error {\n\treturn fmt.Errorf(\"lookup %d: %w\", id, ErrNotFound)\n}\n"
            "func handle(id int) {\n\tif err := Lookup(id); err == ErrNotFound {\n"
            "\t\tfmt.Println(\"404\")\n\t}\n}\n```"
        ),
        "response": (
            "**Bug: `err == ErrNotFound` never matches a wrapped error.** `Lookup` "
            "wraps the sentinel with `%w`, so the returned error is a `*fmt.wrapError` "
            "whose identity differs from `ErrNotFound`. The `==` comparison is "
            "therefore always false and the 404 branch is dead code.\n\n"
            "Compare with `errors.Is`, which unwraps the chain:\n\n```go\n"
            "if errors.Is(err, ErrNotFound) {\n\tfmt.Println(\"404\")\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this loop that opens files:\n```go\nfunc total(paths []string) (int64, error) {\n"
            "\tvar n int64\n\tfor _, p := range paths {\n\t\tf, err := os.Open(p)\n"
            "\t\tif err != nil {\n\t\t\treturn 0, err\n\t\t}\n\t\tdefer f.Close()\n"
            "\t\tfi, _ := f.Stat()\n\t\tn += fi.Size()\n\t}\n\treturn n, nil\n}\n```"
        ),
        "response": (
            "**Bug: `defer f.Close()` inside the loop accumulates open handles.** "
            "Deferred calls run when the *function* returns, not at the end of each "
            "iteration, so every file stays open until `total` finishes — over many "
            "paths this exhausts the file-descriptor limit. The ignored error from "
            "`f.Stat()` is a second, smaller problem.\n\n"
            "Close each file before the next iteration by scoping the work into a "
            "helper (or an inline closure) so the `defer` fires per file:\n\n```go\n"
            "func size(p string) (int64, error) {\n\tf, err := os.Open(p)\n\tif err != nil {\n"
            "\t\treturn 0, err\n\t}\n\tdefer f.Close()\n\tfi, err := f.Stat()\n\tif err != nil {\n"
            "\t\treturn 0, err\n\t}\n\treturn fi.Size(), nil\n}\n```\n\nThen sum the per-file "
            "sizes in `total`."
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this slice usage for a hidden aliasing bug:\n```go\nfunc topTwo(xs []int) []int {\n"
            "\tsort.Sort(sort.Reverse(sort.IntSlice(xs)))\n\treturn xs[:2]\n}\n```"
        ),
        "response": (
            "**Two real bugs.** (1) `sort.Sort` mutates the caller's slice in place, "
            "so `topTwo` has the surprising side effect of reordering the argument — "
            "callers that still need the original order are silently broken. (2) "
            "`xs[:2]` panics if `len(xs) < 2`, and the returned slice still aliases "
            "the caller's backing array, so later writes to either affect both.\n\n"
            "Work on a copy and guard the length:\n\n```go\nfunc topTwo(xs []int) []int {\n"
            "\tcp := append([]int(nil), xs...)\n\tsort.Sort(sort.Reverse(sort.IntSlice(cp)))\n"
            "\tn := 2\n\tif len(cp) < n {\n\t\tn = len(cp)\n\t}\n\treturn cp[:n]\n}\n```"
        ),
    },
]
