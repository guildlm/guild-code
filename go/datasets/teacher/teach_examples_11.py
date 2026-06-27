# -*- coding: utf-8 -*-
"""Batch 11 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program implementing quicksort that returns a new sorted slice (three-way partition around a pivot). Sort and print a sample slice.",
        "response": '''```go
package main

import "fmt"

// quicksort returns a sorted copy of s using a simple three-way partition.
func quicksort(s []int) []int {
	if len(s) <= 1 {
		return s
	}
	pivot := s[len(s)/2]
	var less, equal, greater []int
	for _, v := range s {
		switch {
		case v < pivot:
			less = append(less, v)
		case v > pivot:
			greater = append(greater, v)
		default:
			equal = append(equal, v)
		}
	}
	result := append(quicksort(less), equal...)
	return append(result, quicksort(greater)...)
}

func main() {
	fmt.Println(quicksort([]int{5, 2, 9, 1, 5, 6})) // [1 2 5 5 6 9]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program solving two-sum in one pass with a map: return the indices of the two numbers adding up to a target. Print the result for a sample.",
        "response": '''```go
package main

import "fmt"

// twoSum returns the indices of the first pair summing to target, plus ok.
func twoSum(nums []int, target int) (int, int, bool) {
	seen := make(map[int]int) // value -> index seen so far
	for i, n := range nums {
		if j, ok := seen[target-n]; ok {
			return j, i, true
		}
		seen[n] = i
	}
	return 0, 0, false
}

func main() {
	i, j, ok := twoSum([]int{2, 7, 11, 15}, 9)
	fmt.Println(i, j, ok) // 0 1 true
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with maxWindowSum(nums []int, k int) int that finds the maximum sum of any contiguous window of size k using the sliding-window technique (O(n)). Print the result.",
        "response": '''```go
package main

import "fmt"

// maxWindowSum returns the largest sum of any contiguous window of size k.
func maxWindowSum(nums []int, k int) int {
	if k <= 0 || k > len(nums) {
		return 0
	}
	sum := 0
	for i := 0; i < k; i++ {
		sum += nums[i]
	}
	best := sum
	for i := k; i < len(nums); i++ {
		sum += nums[i] - nums[i-k] // add the entering element, drop the leaving one
		if sum > best {
			best = sum
		}
	}
	return best
}

func main() {
	fmt.Println(maxWindowSum([]int{1, 4, 2, 10, 2, 3, 1, 0, 20}, 3)) // 21 (window 1,0,20)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that HTML-escapes a string by replacing <, >, and & using a single strings.NewReplacer (more efficient than chained ReplaceAll). Print the escaped output.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

func main() {
	// NewReplacer scans the input once, applying all replacements together.
	escaper := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
	)
	out := escaper.Replace("a < b && c > d")
	fmt.Println(out) // a &lt; b &amp;&amp; c &gt; d
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that builds a time.Time, adds 6 months with AddDate, and prints both dates, whether the end is after the start, and the number of days between them.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	start := time.Date(2026, time.January, 1, 0, 0, 0, 0, time.UTC)
	end := start.AddDate(0, 6, 0) // years, months, days

	fmt.Println("start:", start.Format("2006-01-02"))
	fmt.Println("end:  ", end.Format("2006-01-02"))
	fmt.Println("end after start:", end.After(start))
	fmt.Println("days between:    ", int(end.Sub(start).Hours()/24))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program showing context deadline propagation: a child context derived with a shorter timeout than its parent, demonstrating the child fires first. Print the child's error.",
        "response": '''```go
package main

import (
	"context"
	"fmt"
	"time"
)

func main() {
	// Parent allows 100ms.
	parent, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	// Child can only tighten the deadline, never loosen it.
	child, cancel2 := context.WithTimeout(parent, 30*time.Millisecond)
	defer cancel2()

	<-child.Done() // blocks until the 30ms child deadline elapses
	fmt.Println("child done:", child.Err()) // context deadline exceeded
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program using JSON struct tags with omitempty (and a pointer to a nested struct) so that zero-valued optional fields are omitted from the output. Marshal a sparse and a full value.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
)

type Address struct {
	City string `json:"city,omitempty"`
	Zip  string `json:"zip,omitempty"`
}

type User struct {
	Name    string   `json:"name"`
	Email   string   `json:"email,omitempty"`
	Address *Address `json:"address,omitempty"` // pointer so nil is omitted
}

func main() {
	sparse := User{Name: "Ada"}
	b, _ := json.Marshal(sparse)
	fmt.Println(string(b)) // {"name":"Ada"}

	full := User{Name: "Tim", Email: "tim@x.io", Address: &Address{City: "Berlin"}}
	b2, _ := json.Marshal(full)
	fmt.Println(string(b2))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that groups a list of words into anagram buckets, keyed by the sorted letters. Print a few buckets deterministically.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
	"strings"
)

// sortedKey returns the runes of s sorted, so anagrams share the same key.
func sortedKey(s string) string {
	r := []rune(s)
	sort.Slice(r, func(i, j int) bool { return r[i] < r[j] })
	return string(r)
}

func groupAnagrams(words []string) map[string][]string {
	groups := map[string][]string{}
	for _, w := range words {
		k := sortedKey(strings.ToLower(w))
		groups[k] = append(groups[k], w)
	}
	return groups
}

func main() {
	g := groupAnagrams([]string{"eat", "tea", "tan", "ate", "nat", "bat"})
	for _, k := range []string{"aet", "ant", "abt"} { // fixed order for stable output
		fmt.Printf("%s: %v\\n", k, g[k])
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses io.MultiWriter to write a log line to both standard output and an in-memory buffer at once, then print the captured copy.",
        "response": '''```go
package main

import (
	"bytes"
	"fmt"
	"io"
	"os"
)

func main() {
	var buf bytes.Buffer

	// One Write fans out to every underlying writer.
	w := io.MultiWriter(os.Stdout, &buf)
	fmt.Fprintln(w, "logged everywhere")

	fmt.Print("captured copy: ", buf.String())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining a Color{R,G,B uint8} type that implements fmt.Stringer to render as a hex code, so fmt prints it nicely. Print a color via Println and %v.",
        "response": '''```go
package main

import "fmt"

type Color struct {
	R, G, B uint8
}

// String makes Color satisfy fmt.Stringer; fmt's %v/%s and Println use it.
func (c Color) String() string {
	return fmt.Sprintf("#%02X%02X%02X", c.R, c.G, c.B)
}

func main() {
	c := Color{R: 255, G: 128, B: 0}
	fmt.Println(c)             // #FF8000
	fmt.Printf("color: %v\\n", c) // color: #FF8000
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; callers that append to the result silently corrupt the input. Explain the shared-capacity bug and fix:\n\n```go\nfunc firstThree(s []int) []int {\n\treturn s[:3]\n}\n// caller: head := firstThree(data); head = append(head, 99) // overwrites data[3]\n```",
        "response": '''**Bug: the returned sub-slice shares the input's backing array *and* its spare capacity.** `s[:3]` has `len 3` but `cap` equal to `cap(s)` (often the full length). So when the caller does `append(head, 99)` and there's room (`len < cap`), `append` writes into the shared array at index 3 — which is `data[3]`. The caller mutates the original through what looked like an independent slice.

**Fix A — a full slice expression that caps the capacity:**

```go
func firstThree(s []int) []int {
	return s[:3:3] // len 3, cap 3 -> any append must allocate a new array
}
```

**Fix B — return an independent copy:**

```go
func firstThree(s []int) []int {
	return slices.Clone(s[:3])
}
```

With `s[:3:3]`, `cap(head) == 3`, so the caller's first `append` is forced to allocate and copy, leaving `data` untouched. Use the three-index slice when you want to hand out a read-prefix cheaply but safely; use `slices.Clone` when the caller may keep and mutate the result long-term. This "leaking spare capacity" bug is subtle precisely because it only triggers when there *is* spare capacity.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; after the channel is closed it spins forever printing zeros. Explain and fix:\n\n```go\nfunc consume(ch chan int) {\n\tfor {\n\t\tv := <-ch\n\t\tfmt.Println(v)\n\t}\n}\n```",
        "response": '''**Bug: a plain receive on a closed channel never blocks — it returns the zero value immediately, forever.** Once the channel is closed, `v := <-ch` keeps yielding `0` (the zero value for `int`) on every iteration, so the loop spins at full speed printing zeros and never terminates. The single-value receive form can't tell "a real 0 was sent" from "the channel is closed."

**Fix A — range over the channel (the idiomatic consumer loop):**

```go
func consume(ch chan int) {
	for v := range ch {
		fmt.Println(v)
	}
}
```

`for range ch` receives until the channel is closed *and* drained, then exits the loop cleanly.

**Fix B — use the comma-ok receive** when you need to do something on close:

```go
func consume(ch chan int) {
	for {
		v, ok := <-ch
		if !ok {
			return // channel closed and drained
		}
		fmt.Println(v)
	}
}
```

The two-value receive returns `ok == false` once the channel is closed and empty. Prefer `range` for "process everything until closed"; use comma-ok when you must distinguish closure explicitly or select among multiple channels.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; stored rows mysteriously change after the caller reuses its buffer. Explain the aliasing bug and fix:\n\n```go\ntype Store struct{ rows [][]int }\n\nfunc (s *Store) Add(row []int) {\n\ts.rows = append(s.rows, row)\n}\n\n// caller:\n// buf := make([]int, 3)\n// for i := 0; i < 2; i++ { fill(buf); store.Add(buf) }\n```",
        "response": '''**Bug: `Add` stores the caller's slice header, not a copy — so every stored row points at the *same* backing array.** The caller reuses one `buf` across iterations; each `store.Add(buf)` appends a slice that shares `buf`'s underlying array. When the caller refills `buf` for the next iteration, it overwrites the data behind the previously stored row too. After the loop, all stored rows reflect the *last* contents of `buf`.

**Fix — defensively copy the slice on the way in:**

```go
func (s *Store) Add(row []int) {
	s.rows = append(s.rows, slices.Clone(row)) // own an independent copy
}
```

`slices.Clone` (or `dst := make([]int, len(row)); copy(dst, row)`) gives the store its own array, decoupled from whatever the caller does to `row` afterward. The general principle: a slice argument is a *view* into the caller's memory; if you retain it beyond the call, copy it — otherwise you've created hidden aliasing where two owners mutate the same array. (The same applies to maps stored by reference.)''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a property-style Go test for a sort function, asserting the output is sorted and is a permutation of the input:\n\n```go\n// QuickSort returns a sorted copy of s.\nfunc QuickSort(s []int) []int { /* ... */ }\n```",
        "response": '''```go
func TestQuickSort(t *testing.T) {
	tests := [][]int{
		{},
		{1},
		{2, 1},
		{5, 2, 9, 1, 5, 6},
		{3, 3, 3},
		{-2, 4, -1, 0},
	}

	for _, in := range tests {
		got := QuickSort(in)

		// Property 1: the result is sorted ascending.
		if !sort.IntsAreSorted(got) {
			t.Errorf("QuickSort(%v) = %v, not sorted", in, got)
		}

		// Property 2: it's a permutation of the input (same multiset).
		wantCounts := map[int]int{}
		for _, v := range in {
			wantCounts[v]++
		}
		gotCounts := map[int]int{}
		for _, v := range got {
			gotCounts[v]++
		}
		if !maps.Equal(wantCounts, gotCounts) {
			t.Errorf("QuickSort(%v) = %v, not a permutation of input", in, got)
		}
	}
}
```

Rather than hard-coding each expected output, this checks the two *properties* that define a correct sort: the result is ordered (`sort.IntsAreSorted`), and it contains exactly the same elements with the same multiplicities as the input (compared as a multiset via `maps.Equal` on element counts). Property checks like these catch bugs that example-based tests miss — e.g. a sort that drops or duplicates elements but still returns something ordered. The cases include empty, single, already-trivial, duplicates, and negatives.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test verifying that a type's String() method (fmt.Stringer) produces the expected text, for:\n\n```go\ntype Color struct{ R, G, B uint8 }\nfunc (c Color) String() string { return fmt.Sprintf(\"#%02X%02X%02X\", c.R, c.G, c.B) }\n```",
        "response": '''```go
func TestColorString(t *testing.T) {
	tests := []struct {
		name string
		c    Color
		want string
	}{
		{"orange", Color{255, 128, 0}, "#FF8000"},
		{"black", Color{0, 0, 0}, "#000000"},
		{"white", Color{255, 255, 255}, "#FFFFFF"},
		{"needs padding", Color{1, 2, 3}, "#010203"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.c.String(); got != tt.want {
				t.Errorf("Color%v.String() = %q, want %q", tt.c, got, tt.want)
			}
			// Also confirm fmt uses Stringer (so %v matches String()).
			if got := fmt.Sprintf("%v", tt.c); got != tt.want {
				t.Errorf("%%v of Color%v = %q, want %q", tt.c, got, tt.want)
			}
		})
	}
}
```

The "needs padding" and "black" cases are the important ones: they verify the `%02X` zero-padding, which is exactly where a hex formatter is most likely to be wrong (e.g. rendering `Color{1,2,3}` as `#123` instead of `#010203`). The second assertion checks that the type genuinely satisfies `fmt.Stringer`, so `%v`/`Println` route through `String()` — if someone accidentally gave it a pointer receiver, a `Color` value would stop formatting via `String` and this catches it.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain Go's directional channel types and why functions often take them, using this snippet:\n\n```go\nfunc produce(out chan<- int) { out <- 1; close(out) }\nfunc consume(in <-chan int)  { for v := range in { _ = v } }\n```",
        "response": '''Channels can be typed by **direction**, restricting a reference to send-only or receive-only:

- `chan int` — bidirectional: you can send (`ch <- v`) and receive (`<-ch`).
- `chan<- int` — **send-only**: the arrow points *into* the channel. You may send and `close`, but not receive.
- `<-chan int` — **receive-only**: the arrow points *out*. You may receive, but not send or close.

In the snippet, `produce` takes `chan<- int`: inside it you can only put values in (and close), which matches a producer's role. `consume` takes `<-chan int`: it can only take values out, matching a consumer. The underlying channel is the same; the parameter types are *views* that narrow what each function is allowed to do.

Why this is worth doing:
- **Compile-time safety / intent.** The signature documents the data flow ("this function only produces / only consumes") and the compiler enforces it. A consumer that accidentally tries to `close(in)` or send on it won't compile — preventing a whole class of bugs, since closing a channel from the receiving side or double-closing causes panics.
- **Encapsulation of the close contract.** The rule "only the sender closes" is *enforced* when the consumer only has a `<-chan`: it physically cannot close. This makes pipelines safer to compose.
- **Conversions are one-way and implicit.** A bidirectional `chan int` converts automatically to `chan<- int` or `<-chan int` when passed to such a parameter (that's why `produce(out)`/`consume(out)` just work). You cannot convert a directional channel back to bidirectional.

A common idiom: a generator function creates a bidirectional channel internally but **returns** it as `<-chan int`, so callers can only read from it — the function retains exclusive send/close rights. Directional types cost nothing at runtime; they're purely a compile-time guarantee that encodes the pipeline's data-flow contract.''',
    },
]
