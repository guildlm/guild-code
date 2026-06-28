# -*- coding: utf-8 -*-
"""Batch 26 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Generics + small data structures, weighted toward the thinner go_tester and
go_reviewer roles. go_generator responses are complete, stdlib-only, compilable
programs (compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic Filter[T any](s []T, keep "
            "func(T) bool) []T returning the elements for which keep is true. "
            "Demonstrate it. Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// Filter returns the elements of s for which keep returns true.
func Filter[T any](s []T, keep func(T) bool) []T {
	var out []T
	for _, v := range s {
		if keep(v) {
			out = append(out, v)
		}
	}
	return out
}

func main() {
	evens := Filter([]int{1, 2, 3, 4, 5, 6}, func(n int) bool { return n%2 == 0 })
	fmt.Println(evens)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a fixed-size Ring buffer of ints "
            "(NewRing(size), Push overwriting the oldest, Len). Demonstrate "
            "overwrite. Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// Ring is a fixed-capacity circular buffer; Push overwrites the oldest element.
type Ring struct {
	buf  []int
	head int
	n    int
}

func NewRing(size int) *Ring { return &Ring{buf: make([]int, size)} }

func (r *Ring) Push(v int) {
	r.buf[r.head] = v
	r.head = (r.head + 1) % len(r.buf)
	if r.n < len(r.buf) {
		r.n++
	}
}

func (r *Ring) Len() int { return r.n }

func main() {
	r := NewRing(3)
	for i := 1; i <= 5; i++ {
		r.Push(i)
	}
	fmt.Println("len:", r.Len()) // capped at 3
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this Sum to work for any numeric slice (ints and floats) using a "
            "type constraint. Original:\n```go\npackage main\nimport \"fmt\"\n"
            "func Sum(xs []int) int {\n\ts := 0\n\tfor _, x := range xs {\n\t\ts += x\n"
            "\t}\n\treturn s\n}\nfunc main() { fmt.Println(Sum([]int{1, 2, 3})) }\n```"
        ),
        "response": '''```go
package main

import "fmt"

// Number is satisfied by the built-in numeric kinds (and named types over them).
type Number interface {
	~int | ~int64 | ~float64
}

// Sum adds the elements of any numeric slice.
func Sum[T Number](xs []T) T {
	var s T
	for _, x := range xs {
		s += x
	}
	return s
}

func main() {
	fmt.Println(Sum([]int{1, 2, 3}), Sum([]float64{1.5, 2.5}))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with getInt(key string, def int) int that "
            "reads an integer from an environment variable, falling back to def "
            "when unset or unparseable. Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"os"
	"strconv"
)

// getInt reads an int from the environment, returning def if the variable is
// unset or not a valid integer.
func getInt(key string, def int) int {
	if v, ok := os.LookupEnv(key); ok {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func main() {
	fmt.Println(getInt("GUILDLM_UNSET_PORT", 8080))
}
```''',
    },

    # ---------------- go_tester (authored; judged) ---------------------------
    {
        "role": "go_tester",
        "instruction": (
            "Write table-driven Go tests (package slicekit) for Filter covering "
            "keeping some, keeping none, and an empty input.\n```go\npackage slicekit\n"
            "// func Filter[T any](s []T, keep func(T) bool) []T\n```"
        ),
        "response": '''```go
package slicekit

import (
	"reflect"
	"testing"
)

func TestFilter(t *testing.T) {
	in := []int{1, 2, 3, 4, 5, 6}
	if got := Filter(in, func(n int) bool { return n%2 == 0 }); !reflect.DeepEqual(got, []int{2, 4, 6}) {
		t.Errorf("evens = %v", got)
	}
	if got := Filter(in, func(int) bool { return false }); len(got) != 0 {
		t.Errorf("keep-none = %v, want empty", got)
	}
	if got := Filter([]int(nil), func(int) bool { return true }); len(got) != 0 {
		t.Errorf("empty input = %v", got)
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package ring) for the Ring buffer: Len caps at the "
            "size after more pushes than capacity.\n```go\npackage ring\n"
            "// func NewRing(size int) *Ring\n// func (*Ring) Push(int)\n// func (*Ring) Len() int\n```"
        ),
        "response": '''```go
package ring

import "testing"

func TestRingLenCaps(t *testing.T) {
	r := NewRing(3)
	if r.Len() != 0 {
		t.Fatalf("empty len = %d", r.Len())
	}
	r.Push(1)
	r.Push(2)
	if r.Len() != 2 {
		t.Errorf("after 2 pushes len = %d, want 2", r.Len())
	}
	for i := 0; i < 5; i++ {
		r.Push(i)
	}
	if r.Len() != 3 {
		t.Errorf("len = %d, want capped at 3", r.Len())
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package numkit) for the generic Sum, asserting it sums "
            "ints and floats and returns the zero value for an empty slice.\n```go\n"
            "package numkit\n// func Sum[T Number](xs []T) T\n```"
        ),
        "response": '''```go
package numkit

import "testing"

func TestSumInts(t *testing.T) {
	if got := Sum([]int{1, 2, 3, 4}); got != 10 {
		t.Errorf("ints = %d, want 10", got)
	}
	if got := Sum([]int(nil)); got != 0 {
		t.Errorf("empty = %d, want 0", got)
	}
}

func TestSumFloats(t *testing.T) {
	if got := Sum([]float64{1.5, 2.5}); got != 4.0 {
		t.Errorf("floats = %v, want 4.0", got)
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write a Go test (package config) for getInt using t.Setenv: the value "
            "is read when set, and the default is used when unset or invalid.\n```go\n"
            "package config\n// func getInt(key string, def int) int\n```"
        ),
        "response": '''```go
package config

import "testing"

func TestGetInt(t *testing.T) {
	t.Setenv("X_PORT", "9090")
	if got := getInt("X_PORT", 8080); got != 9090 {
		t.Errorf("set = %d, want 9090", got)
	}
	t.Setenv("X_PORT", "not-a-number")
	if got := getInt("X_PORT", 8080); got != 8080 {
		t.Errorf("invalid = %d, want default 8080", got)
	}
	if got := getInt("X_UNSET", 1234); got != 1234 {
		t.Errorf("unset = %d, want default 1234", got)
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) -------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this concurrency code:\n```go\nfunc run(tasks []func()) {\n"
            "\tvar wg sync.WaitGroup\n\tfor _, t := range tasks {\n\t\tgo func(f func()) {\n"
            "\t\t\twg.Add(1)\n\t\t\tdefer wg.Done()\n\t\t\tf()\n\t\t}(t)\n\t}\n\twg.Wait()\n}\n```"
        ),
        "response": (
            "**Bug: `wg.Add(1)` runs inside the goroutine, so `wg.Wait` can return "
            "before the tasks are even counted.** The loop launches goroutines and "
            "immediately calls `wg.Wait()`; if `Wait` runs before a goroutine has "
            "executed its `wg.Add(1)`, the counter is still 0 and `Wait` returns "
            "early — the tasks run (or don't) unsynchronised, a classic race that "
            "`-race` flags.\n\n"
            "Call `Add` before launching the goroutine, while still on the main "
            "goroutine:\n\n```go\nfunc run(tasks []func()) {\n\tvar wg sync.WaitGroup\n"
            "\twg.Add(len(tasks))\n\tfor _, t := range tasks {\n\t\tgo func(f func()) {\n"
            "\t\t\tdefer wg.Done()\n\t\t\tf()\n\t\t}(t)\n\t}\n\twg.Wait()\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this accessor:\n```go\ntype Buffer struct{ data []byte }\n"
            "func (b *Buffer) Bytes() []byte {\n\treturn b.data\n}\n```"
        ),
        "response": (
            "**Bug: returning the internal slice lets callers mutate the Buffer's "
            "private state.** `Bytes()` hands out the same backing array as "
            "`b.data`, so a caller can do `buf.Bytes()[0] = 'x'` and silently "
            "corrupt the Buffer — the encapsulation is an illusion. (The standard "
            "library's `bytes.Buffer.Bytes` documents this sharp edge precisely "
            "because it is surprising.)\n\n"
            "If callers must not mutate it, return a copy:\n\n```go\n"
            "func (b *Buffer) Bytes() []byte {\n\tout := make([]byte, len(b.data))\n"
            "\tcopy(out, b.data)\n\treturn out\n}\n```\n\nOtherwise, document loudly "
            "that the returned slice aliases internal storage and is valid only "
            "until the next mutation."
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this channel usage:\n```go\nfunc merge(a, b <-chan int) <-chan int {\n"
            "\tout := make(chan int)\n\tgo func() { for v := range a { out <- v } }()\n"
            "\tgo func() { for v := range b { out <- v } }()\n\treturn out\n}\n```"
        ),
        "response": (
            "**Bug: `out` is never closed, so a `range` over the merged channel "
            "blocks forever.** Both source goroutines finish when `a` and `b` "
            "close, but nothing closes `out`, so a consumer doing `for v := range "
            "merge(a, b)` hangs after the last value — and the two goroutines, if "
            "the consumer stops reading, leak.\n\n"
            "Use a `sync.WaitGroup` to close `out` exactly once after both "
            "producers are done:\n\n```go\nfunc merge(a, b <-chan int) <-chan int {\n"
            "\tout := make(chan int)\n\tvar wg sync.WaitGroup\n\twg.Add(2)\n"
            "\tpipe := func(c <-chan int) { defer wg.Done(); for v := range c { out <- v } }\n"
            "\tgo pipe(a)\n\tgo pipe(b)\n\tgo func() { wg.Wait(); close(out) }()\n\treturn out\n}\n```"
        ),
    },
]
