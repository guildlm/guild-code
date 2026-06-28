# -*- coding: utf-8 -*-
"""Batch 21 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Breadth across Go competencies + more EDIT/refactor and thin-role (tester,
reviewer) coverage. go_generator responses are complete, stdlib-only,
compilable programs (compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a Retry(attempts int, backoff "
            "time.Duration, fn func() error) error helper that retries fn up to "
            "attempts times, sleeping backoff between tries, and wraps the last "
            "error. Demonstrate it succeeding on the second try. Standard library only."
        ),
        "response": '''```go
package main

import (
	"errors"
	"fmt"
	"time"
)

// Retry calls fn up to attempts times, sleeping backoff between failures, and
// returns the wrapped last error if every attempt fails.
func Retry(attempts int, backoff time.Duration, fn func() error) error {
	var err error
	for i := 0; i < attempts; i++ {
		if err = fn(); err == nil {
			return nil
		}
		if i < attempts-1 {
			time.Sleep(backoff)
		}
	}
	return fmt.Errorf("after %d attempts: %w", attempts, err)
}

func main() {
	calls := 0
	err := Retry(3, time.Millisecond, func() error {
		calls++
		if calls < 2 {
			return errors.New("transient")
		}
		return nil
	})
	fmt.Println(err, "calls:", calls)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with TopWords(s string, n int) []string "
            "returning the n most frequent whitespace-separated words (lowercased), "
            "ties broken alphabetically. Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"sort"
	"strings"
)

// TopWords returns the n most frequent words in s (case-insensitive), with ties
// broken alphabetically.
func TopWords(s string, n int) []string {
	freq := map[string]int{}
	for _, w := range strings.Fields(strings.ToLower(s)) {
		freq[w]++
	}
	words := make([]string, 0, len(freq))
	for w := range freq {
		words = append(words, w)
	}
	sort.Slice(words, func(i, j int) bool {
		if freq[words[i]] != freq[words[j]] {
			return freq[words[i]] > freq[words[j]]
		}
		return words[i] < words[j]
	})
	if n > len(words) {
		n = len(words)
	}
	return words[:n]
}

func main() {
	fmt.Println(TopWords("a b a c a b", 2))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program that streams a JSON array with "
            "encoding/json's Decoder (token by token, not all at once) and prints "
            "the 'name' field of each object. Standard library only."
        ),
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

type item struct {
	Name string `json:"name"`
}

// decodeStream reads a JSON array element by element so a huge array never has
// to be held in memory at once.
func decodeStream(r *strings.Reader) ([]string, error) {
	dec := json.NewDecoder(r)
	if _, err := dec.Token(); err != nil { // consume the opening '['
		return nil, err
	}
	var names []string
	for dec.More() {
		var it item
		if err := dec.Decode(&it); err != nil {
			return nil, err
		}
		names = append(names, it.Name)
	}
	return names, nil
}

func main() {
	names, err := decodeStream(strings.NewReader(`[{"name":"a"},{"name":"b"}]`))
	fmt.Println(names, err)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic Intersect[T int | string]"
            "(a, b []T) []T returning the sorted, de-duplicated elements present in "
            "both slices. Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// Intersect returns the sorted, de-duplicated elements found in both a and b.
func Intersect[T int | string](a, b []T) []T {
	set := make(map[T]struct{}, len(a))
	for _, x := range a {
		set[x] = struct{}{}
	}
	var out []T
	seen := make(map[T]struct{})
	for _, x := range b {
		if _, ok := set[x]; !ok {
			continue
		}
		if _, dup := seen[x]; dup {
			continue
		}
		seen[x] = struct{}{}
		out = append(out, x)
	}
	sort.Slice(out, func(i, j int) bool { return out[i] < out[j] })
	return out
}

func main() {
	fmt.Println(Intersect([]int{1, 2, 3, 2}, []int{2, 3, 4}))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this program so Average returns an error on empty input instead "
            "of dividing by zero (which yields NaN). Original:\n```go\npackage main\n"
            "import \"fmt\"\nfunc Average(xs []float64) float64 {\n\tvar s float64\n"
            "\tfor _, x := range xs {\n\t\ts += x\n\t}\n\treturn s / float64(len(xs))\n}\n"
            "func main() { fmt.Println(Average([]float64{1, 2, 3})) }\n```"
        ),
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

// ErrEmpty is returned by Average when there is nothing to average.
var ErrEmpty = errors.New("empty input")

// Average returns the mean of xs, or ErrEmpty rather than NaN for empty input.
func Average(xs []float64) (float64, error) {
	if len(xs) == 0 {
		return 0, ErrEmpty
	}
	var s float64
	for _, x := range xs {
		s += x
	}
	return s / float64(len(xs)), nil
}

func main() {
	if avg, err := Average([]float64{1, 2, 3}); err == nil {
		fmt.Println(avg)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this Cache to be safe for concurrent use by multiple goroutines, "
            "keeping the same API. Original:\n```go\npackage main\nimport \"fmt\"\n"
            "type Cache struct{ m map[string]string }\nfunc NewCache() *Cache { return &Cache{m: map[string]string{}} }\n"
            "func (c *Cache) Set(k, v string) { c.m[k] = v }\nfunc (c *Cache) Get(k string) string { return c.m[k] }\n"
            "func main() {\n\tc := NewCache()\n\tc.Set(\"a\", \"1\")\n\tfmt.Println(c.Get(\"a\"))\n}\n```"
        ),
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

// Cache is a concurrency-safe string map. Reads take a shared RLock; writes take
// the exclusive Lock.
type Cache struct {
	mu sync.RWMutex
	m  map[string]string
}

func NewCache() *Cache { return &Cache{m: map[string]string{}} }

func (c *Cache) Set(k, v string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.m[k] = v
}

func (c *Cache) Get(k string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.m[k]
}

func main() {
	c := NewCache()
	c.Set("a", "1")
	fmt.Println(c.Get("a"))
}
```''',
    },

    # ---------------- go_tester (authored; judged) ---------------------------
    {
        "role": "go_tester",
        "instruction": (
            "Write table-driven Go tests (package wordkit) for TopWords, covering "
            "ties broken alphabetically and n larger than the vocabulary.\n```go\n"
            "package wordkit\n// func TopWords(s string, n int) []string\n```"
        ),
        "response": '''```go
package wordkit

import (
	"reflect"
	"testing"
)

func TestTopWords(t *testing.T) {
	tests := []struct {
		name, in string
		n        int
		want     []string
	}{
		{"by frequency", "a b a c a b", 2, []string{"a", "b"}},
		{"tie alphabetical", "x y", 2, []string{"x", "y"}},
		{"n exceeds vocab", "a a b", 5, []string{"a", "b"}},
		{"empty", "", 3, []string{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := TopWords(tt.in, tt.n)
			if len(got) == 0 && len(tt.want) == 0 {
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("TopWords(%q, %d) = %v, want %v", tt.in, tt.n, got, tt.want)
			}
		})
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package retrykit) for Retry: assert it stops early on "
            "the first success, retries on failure, and returns a wrapped error "
            "when all attempts fail.\n```go\npackage retrykit\n"
            "// func Retry(attempts int, backoff time.Duration, fn func() error) error\n```"
        ),
        "response": '''```go
package retrykit

import (
	"errors"
	"testing"
	"time"
)

func TestRetrySucceedsEarly(t *testing.T) {
	calls := 0
	err := Retry(3, time.Millisecond, func() error {
		calls++
		return nil
	})
	if err != nil || calls != 1 {
		t.Fatalf("err=%v calls=%d, want nil/1", err, calls)
	}
}

func TestRetryExhausts(t *testing.T) {
	sentinel := errors.New("boom")
	calls := 0
	err := Retry(3, time.Millisecond, func() error {
		calls++
		return sentinel
	})
	if calls != 3 {
		t.Errorf("calls=%d, want 3", calls)
	}
	if !errors.Is(err, sentinel) {
		t.Errorf("err=%v, want wraps sentinel", err)
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write a Go test (package cache, runnable under -race) proving Cache is "
            "safe under concurrent Set/Get.\n```go\npackage cache\n"
            "// func NewCache() *Cache\n// func (c *Cache) Set(k, v string)\n// func (c *Cache) Get(k string) string\n```"
        ),
        "response": '''```go
package cache

import (
	"strconv"
	"sync"
	"testing"
)

func TestCacheConcurrent(t *testing.T) {
	c := NewCache()
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(2)
		go func(n int) { defer wg.Done(); c.Set(strconv.Itoa(n), "v") }(i)
		go func(n int) { defer wg.Done(); _ = c.Get(strconv.Itoa(n)) }(i)
	}
	wg.Wait()
	if c.Get("1") != "" && c.Get("1") != "v" {
		t.Fatalf("unexpected value %q", c.Get("1"))
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) -------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this loop for a resource issue:\n```go\nfunc poll(ch <-chan int) {\n"
            "\tfor {\n\t\tselect {\n\t\tcase v := <-ch:\n\t\t\tprocess(v)\n"
            "\t\tcase <-time.After(time.Second):\n\t\t\treturn\n\t\t}\n\t}\n}\n```"
        ),
        "response": (
            "**Bug: `time.After` in a loop leaks a timer every iteration.** Each "
            "`select` builds a *new* `time.After` channel+timer; the timer isn't "
            "garbage-collected until it fires (up to a second later), so a hot loop "
            "accumulates thousands of live timers. Worse, the timeout never "
            "represents \"a second of total inactivity\" — it resets every time a "
            "value arrives.\n\n"
            "Create one `time.Timer` and reset it, stopping it on exit:\n\n```go\n"
            "func poll(ch <-chan int) {\n\tt := time.NewTimer(time.Second)\n\tdefer t.Stop()\n"
            "\tfor {\n\t\tselect {\n\t\tcase v := <-ch:\n\t\t\tprocess(v)\n\t\t\tif !t.Stop() {\n"
            "\t\t\t\t<-t.C\n\t\t\t}\n\t\t\tt.Reset(time.Second)\n\t\tcase <-t.C:\n\t\t\treturn\n\t\t}\n\t}\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this for an aliasing bug:\n```go\nfunc addTag(base []string, tag string) []string {\n"
            "\treturn append(base, tag)\n}\nfunc main() {\n\tbase := make([]string, 2, 4)\n"
            "\ta := addTag(base, \"x\")\n\tb := addTag(base, \"y\")\n\tfmt.Println(a[2], b[2])\n}\n```"
        ),
        "response": (
            "**Bug: `a` and `b` share the same backing array, so the second append "
            "overwrites the first.** `base` has length 2 but capacity 4, so both "
            "`append` calls write into index 2 of the *same* array instead of "
            "allocating — `a[2]` and `b[2]` both end up `\"y\"`. This is the classic "
            "shared-capacity aliasing trap.\n\n"
            "Make the helper copy when it must not alias the caller's array, e.g. "
            "with the three-index slice to force a fresh allocation:\n\n```go\n"
            "func addTag(base []string, tag string) []string {\n"
            "\tout := base[:len(base):len(base)] // cap == len -> append allocates\n"
            "\treturn append(out, tag)\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this concurrency code:\n```go\nfunc fanOut(jobs []int) []int {\n"
            "\tresults := make([]int, 0)\n\tvar wg sync.WaitGroup\n\tfor _, j := range jobs {\n"
            "\t\twg.Add(1)\n\t\tgo func(n int) {\n\t\t\tdefer wg.Done()\n"
            "\t\t\tresults = append(results, n*n)\n\t\t}(j)\n\t}\n\twg.Wait()\n\treturn results\n}\n```"
        ),
        "response": (
            "**Bug: concurrent `append` to `results` is a data race.** Multiple "
            "goroutines append to the same slice header without synchronisation; "
            "`append` reads and writes the shared length/backing pointer, so "
            "results are lost or corrupted and `-race` flags it. The output length "
            "is nondeterministic.\n\n"
            "Write into a pre-sized slice by index (no shared mutation), or guard "
            "with a mutex. The index approach is cleanest:\n\n```go\n"
            "func fanOut(jobs []int) []int {\n\tresults := make([]int, len(jobs))\n"
            "\tvar wg sync.WaitGroup\n\tfor i, j := range jobs {\n\t\twg.Add(1)\n"
            "\t\tgo func(idx, n int) {\n\t\t\tdefer wg.Done()\n\t\t\tresults[idx] = n * n\n"
            "\t\t}(i, j)\n\t}\n\twg.Wait()\n\treturn results\n}\n```"
        ),
    },
]
