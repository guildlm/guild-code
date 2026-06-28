# -*- coding: utf-8 -*-
"""Batch 23 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Algorithms, generics, and classic correctness pitfalls. go_generator responses
are complete, stdlib-only, compilable programs (compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic BinarySearch[T "
            "cmp.Ordered](s []T, target T) int returning the index of target in a "
            "sorted slice, or -1. Standard library only."
        ),
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
)

// BinarySearch returns the index of target in the sorted slice s, or -1.
func BinarySearch[T cmp.Ordered](s []T, target T) int {
	lo, hi := 0, len(s)-1
	for lo <= hi {
		mid := int(uint(lo+hi) >> 1) // avoids overflow
		switch {
		case s[mid] == target:
			return mid
		case s[mid] < target:
			lo = mid + 1
		default:
			hi = mid - 1
		}
	}
	return -1
}

func main() {
	fmt.Println(BinarySearch([]int{1, 3, 5, 7, 9}, 7))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with Merge(a, b []int) []int that merges "
            "two sorted slices into one sorted slice. Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// Merge combines two sorted slices into a single sorted slice.
func Merge(a, b []int) []int {
	out := make([]int, 0, len(a)+len(b))
	i, j := 0, 0
	for i < len(a) && j < len(b) {
		if a[i] <= b[j] {
			out = append(out, a[i])
			i++
		} else {
			out = append(out, b[j])
			j++
		}
	}
	out = append(out, a[i:]...)
	out = append(out, b[j:]...)
	return out
}

func main() {
	fmt.Println(Merge([]int{1, 4, 6}, []int{2, 3, 5}))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic Set[T comparable] type "
            "(Add, Has) backed by a map, and demonstrate it with sorted output. "
            "Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// Set is a generic set backed by a map with empty-struct values.
type Set[T comparable] map[T]struct{}

func (s Set[T]) Add(v T)      { s[v] = struct{}{} }
func (s Set[T]) Has(v T) bool { _, ok := s[v]; return ok }

func main() {
	s := Set[string]{}
	s.Add("b")
	s.Add("a")
	s.Add("a")
	keys := make([]string, 0, len(s))
	for k := range s {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	fmt.Println(keys, s.Has("a"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this program so the collected pointers refer to distinct values "
            "(it currently prints the same value three times on older Go). "
            "Original:\n```go\npackage main\nimport \"fmt\"\nfunc main() {\n"
            "\tvar ptrs []*int\n\tfor _, v := range []int{1, 2, 3} {\n"
            "\t\tptrs = append(ptrs, &v)\n\t}\n\tfor _, p := range ptrs {\n"
            "\t\tfmt.Print(*p, \" \")\n\t}\n\tfmt.Println()\n}\n```"
        ),
        "response": '''```go
package main

import "fmt"

func main() {
	var ptrs []*int
	for _, v := range []int{1, 2, 3} {
		v := v // take the address of a fresh copy per iteration
		ptrs = append(ptrs, &v)
	}
	for _, p := range ptrs {
		fmt.Print(*p, " ")
	}
	fmt.Println()
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with countTicks(every, total time.Duration) "
            "int that counts ticks from a time.Ticker over a window, stopping the "
            "ticker. Demonstrate it. Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

// countTicks counts how many ticks fire from a Ticker over the total window.
func countTicks(every, total time.Duration) int {
	t := time.NewTicker(every)
	defer t.Stop()
	deadline := time.After(total)
	n := 0
	for {
		select {
		case <-t.C:
			n++
		case <-deadline:
			return n
		}
	}
}

func main() {
	fmt.Println(countTicks(time.Millisecond, 5*time.Millisecond) >= 0)
}
```''',
    },

    # ---------------- go_tester (authored; judged) ---------------------------
    {
        "role": "go_tester",
        "instruction": (
            "Write table-driven Go tests (package search) for BinarySearch "
            "covering found, not-found, and empty slice.\n```go\npackage search\n"
            "// func BinarySearch[T cmp.Ordered](s []T, target T) int\n```"
        ),
        "response": '''```go
package search

import "testing"

func TestBinarySearch(t *testing.T) {
	s := []int{1, 3, 5, 7, 9}
	tests := []struct {
		target, want int
	}{
		{1, 0}, {5, 2}, {9, 4}, {4, -1}, {0, -1}, {10, -1},
	}
	for _, tt := range tests {
		if got := BinarySearch(s, tt.target); got != tt.want {
			t.Errorf("BinarySearch(%d) = %d, want %d", tt.target, got, tt.want)
		}
	}
	if got := BinarySearch([]int{}, 1); got != -1 {
		t.Errorf("empty = %d, want -1", got)
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package mergekit) for Merge covering interleaving, an "
            "empty input, and that the result is sorted.\n```go\npackage mergekit\n"
            "// func Merge(a, b []int) []int\n```"
        ),
        "response": '''```go
package mergekit

import (
	"reflect"
	"sort"
	"testing"
)

func TestMerge(t *testing.T) {
	if got := Merge([]int{1, 4, 6}, []int{2, 3, 5}); !reflect.DeepEqual(got, []int{1, 2, 3, 4, 5, 6}) {
		t.Errorf("got %v", got)
	}
	if got := Merge(nil, []int{1, 2}); !reflect.DeepEqual(got, []int{1, 2}) {
		t.Errorf("empty-a got %v", got)
	}
	got := Merge([]int{5, 9}, []int{1, 7})
	if !sort.IntsAreSorted(got) {
		t.Errorf("result not sorted: %v", got)
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) -------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this type for a concurrency bug:\n```go\ntype Counter struct {\n"
            "\tmu sync.Mutex\n\tn  int\n}\nfunc (c Counter) Inc() {\n\tc.mu.Lock()\n"
            "\tc.n++\n\tc.mu.Unlock()\n}\n```"
        ),
        "response": (
            "**Two bugs, both from the value receiver `(c Counter)`.** (1) `Inc` "
            "operates on a *copy* of the Counter, so the caller's `n` is never "
            "incremented — the mutation is lost. (2) Copying a `sync.Mutex` is "
            "illegal: each call duplicates the lock's internal state, so the "
            "mutual exclusion is meaningless and `go vet` reports `Inc passes lock "
            "by value`.\n\n"
            "Use a pointer receiver so the method shares the real struct and its "
            "lock:\n\n```go\nfunc (c *Counter) Inc() {\n\tc.mu.Lock()\n\tc.n++\n"
            "\tc.mu.Unlock()\n}\n```\n\n(Counters held in a struct should always be "
            "passed by pointer for the same reason.)"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this for a correctness assumption:\n```go\nfunc firstKey(m map[string]int) string {\n"
            "\tfor k := range m {\n\t\treturn k\n\t}\n\treturn \"\"\n}\n// used as: id := firstKey(items) // expects the smallest key\n```"
        ),
        "response": (
            "**Bug: it assumes map iteration is ordered, but Go randomises map "
            "range order deliberately.** `firstKey` returns an arbitrary key that "
            "changes run to run, so the caller's expectation of \"the smallest "
            "key\" is wrong and the behaviour is non-deterministic (and untestable).\n\n"
            "If you need the smallest key, compute it explicitly:\n\n```go\n"
            "func smallestKey(m map[string]int) string {\n\tfirst := true\n"
            "\tvar min string\n\tfor k := range m {\n\t\tif first || k < min {\n"
            "\t\t\tmin, first = k, false\n\t\t}\n\t}\n\treturn min\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this for a goroutine leak:\n```go\nfunc first(urls []string) string {\n"
            "\tch := make(chan string)\n\tfor _, u := range urls {\n\t\tgo func(u string) {\n"
            "\t\t\tch <- fetch(u)\n\t\t}(u)\n\t}\n\treturn <-ch\n}\n```"
        ),
        "response": (
            "**Bug: every goroutine except the winner leaks forever.** `first` "
            "reads a single value from the unbuffered `ch` and returns, but the "
            "other `len(urls)-1` goroutines are still blocked trying to send on "
            "`ch` with no receiver — they never exit, leaking goroutines (and "
            "whatever `fetch` holds) for the life of the process.\n\n"
            "Give the channel enough buffer that every sender can complete, or use "
            "a context to cancel the losers:\n\n```go\nfunc first(urls []string) string {\n"
            "\tch := make(chan string, len(urls)) // every goroutine can send and exit\n"
            "\tfor _, u := range urls {\n\t\tgo func(u string) { ch <- fetch(u) }(u)\n\t}\n"
            "\treturn <-ch\n}\n```"
        ),
    },
]
