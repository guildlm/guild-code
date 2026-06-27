# -*- coding: utf-8 -*-
"""Batch 6 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining a Shape interface with an Area method, implemented by Rectangle and Circle, and a function that sums the areas of a slice of Shapes. Print the total.",
        "response": '''```go
package main

import (
	"fmt"
	"math"
)

type Shape interface {
	Area() float64
}

type Rectangle struct{ W, H float64 }

func (r Rectangle) Area() float64 { return r.W * r.H }

type Circle struct{ R float64 }

func (c Circle) Area() float64 { return math.Pi * c.R * c.R }

// totalArea works on any Shape, no matter the concrete type.
func totalArea(shapes []Shape) float64 {
	var sum float64
	for _, s := range shapes {
		sum += s.Area()
	}
	return sum
}

func main() {
	shapes := []Shape{Rectangle{W: 3, H: 4}, Circle{R: 5}}
	fmt.Printf("total area: %.2f\\n", totalArea(shapes))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a describe(v any) string function that uses a type switch to report the dynamic type and a detail for int, string, bool, nil, and a default case. Run it over a mixed slice.",
        "response": '''```go
package main

import "fmt"

func describe(v any) string {
	switch x := v.(type) {
	case int:
		return fmt.Sprintf("int: %d", x)
	case string:
		return fmt.Sprintf("string of length %d", len(x))
	case bool:
		return fmt.Sprintf("bool: %t", x)
	case nil:
		return "nil"
	default:
		return fmt.Sprintf("unhandled type %T", x)
	}
}

func main() {
	for _, v := range []any{42, "hello", true, 3.14, nil} {
		fmt.Println(describe(v))
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program where 5 goroutines do work (one fails), each writing its error into a per-index slot, then combine the results with errors.Join and report.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
	"sync"
)

func work(id int) error {
	if id == 3 {
		return fmt.Errorf("worker %d failed", id)
	}
	return nil
}

func main() {
	const n = 5
	errs := make([]error, n)

	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			errs[i] = work(i) // each goroutine owns its own slot
		}(i)
	}
	wg.Wait()

	if err := errors.Join(errs...); err != nil { // nil entries are ignored
		fmt.Println("some work failed:", err)
	} else {
		fmt.Println("all ok")
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a custom JSON encoding: a Tags type ([]string) that marshals as a single comma-separated string via MarshalJSON. Marshal a struct containing it and print the JSON.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

type Tags []string

// MarshalJSON renders the tags as one comma-separated string instead of an array.
func (t Tags) MarshalJSON() ([]byte, error) {
	return json.Marshal(strings.Join(t, ","))
}

type Post struct {
	Title string `json:"title"`
	Tags  Tags   `json:"tags"`
}

func main() {
	p := Post{Title: "Go", Tags: Tags{"lang", "backend"}}
	b, err := json.Marshal(p)
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(string(b))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that sorts a slice of Person{Name, Age} by age ascending and, for equal ages, by name, using slices.SortFunc with cmp.Compare. Print the sorted people.",
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
	"slices"
)

type Person struct {
	Name string
	Age  int
}

func main() {
	people := []Person{
		{"Bob", 30}, {"Alice", 30}, {"Carol", 25},
	}

	slices.SortFunc(people, func(a, b Person) int {
		if c := cmp.Compare(a.Age, b.Age); c != 0 {
			return c // primary key: age
		}
		return cmp.Compare(a.Name, b.Name) // tie-break: name
	})

	for _, p := range people {
		fmt.Printf("%s (%d)\\n", p.Name, p.Age)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that runs functions in goroutines but recovers from any panic inside each goroutine, so one panicking goroutine does not crash the whole program. Show a panicking and a normal goroutine, then confirm main survives.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

// safeRun executes fn, turning a panic into a logged message instead of a crash.
func safeRun(fn func(), wg *sync.WaitGroup) {
	defer wg.Done()
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("recovered in goroutine:", r)
		}
	}()
	fn()
}

func main() {
	var wg sync.WaitGroup
	wg.Add(2)
	go safeRun(func() { panic("boom") }, &wg)
	go safeRun(func() { fmt.Println("normal work done") }, &wg)
	wg.Wait()
	fmt.Println("main still alive")
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that counts the number of set bits (population count) of several unsigned integers using math/bits.OnesCount, printing each.",
        "response": '''```go
package main

import (
	"fmt"
	"math/bits"
)

func main() {
	for _, n := range []uint{0, 1, 7, 255, 1024} {
		fmt.Printf("%d (binary %b) has %d set bits\\n", n, n, bits.OnesCount(n))
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that waits for a result from a goroutine but gives up after a 50ms timeout using select with time.After. The goroutine produces its result after 20ms, so the success path should win.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	result := make(chan string, 1) // buffered so the goroutine never leaks
	go func() {
		time.Sleep(20 * time.Millisecond)
		result <- "done"
	}()

	select {
	case r := <-result:
		fmt.Println("got:", r)
	case <-time.After(50 * time.Millisecond):
		fmt.Println("timed out")
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a generic Keys[K comparable, V any](m map[K]V) []K helper that returns a map's keys, then print the sorted keys of a map[string]int.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// Keys returns the keys of m in unspecified order.
func Keys[K comparable, V any](m map[K]V) []K {
	keys := make([]K, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	return keys
}

func main() {
	m := map[string]int{"banana": 2, "apple": 1, "cherry": 3}
	keys := Keys(m)
	sort.Strings(keys) // map iteration order is random; sort for stable output
	fmt.Println(keys)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that constructs a time.Duration from hours, minutes, and seconds, then prints it in Go's default form plus its value in hours and in total minutes.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	d := 2*time.Hour + 35*time.Minute + 12*time.Second

	fmt.Println("duration:     ", d)            // 2h35m12s
	fmt.Printf("hours:         %.2f\\n", d.Hours())
	fmt.Printf("total minutes: %.0f\\n", d.Minutes())
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; the returned pointers don't behave as expected (older Go versions). Explain the range-variable pitfall and give a version-safe fix:\n\n```go\nfunc pointers(items []int) []*int {\n\tvar out []*int\n\tfor _, v := range items {\n\t\tout = append(out, &v)\n\t}\n\treturn out\n}\n```",
        "response": '''**Pitfall: taking the address of the range variable.** Before Go 1.22, the loop variable `v` is a *single* variable reused across iterations, so `&v` is the same address every time. After the loop, that variable holds the last element — so every pointer in `out` points to it, and dereferencing them all yields the final value, not each element.

Go 1.22+ changed `for` to create a fresh `v` per iteration, so this specific code is correct there — but relying on the toolchain version is fragile, and `go vet`/linters still flag the pattern.

**Version-safe fixes:**

```go
// 1. Shadow with a per-iteration copy:
for _, v := range items {
	v := v
	out = append(out, &v)
}

// 2. Or point into the slice's own storage (no copy):
for i := range items {
	out = append(out, &items[i])
}
```

Option 1 gives each pointer its own variable; option 2 points at the backing array element directly (valid as long as `items` isn't later reallocated). Both produce distinct, correct pointers on every Go version.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it panics on some inputs. Explain and fix using a safe type assertion:\n\n```go\nfunc lengths(vals []any) []int {\n\tvar out []int\n\tfor _, v := range vals {\n\t\ts := v.(string)\n\t\tout = append(out, len(s))\n\t}\n\treturn out\n}\n```",
        "response": '''**Bug: a single-result type assertion panics on a mismatch.** `s := v.(string)` asserts that `v` holds a `string`; if any element is, say, an `int`, this panics with `interface conversion: interface {} is int, not string`. One bad element crashes the whole function.

**Fix — use the two-result ("comma, ok") form** and decide what to do on a miss:

```go
func lengths(vals []any) []int {
	out := make([]int, 0, len(vals))
	for _, v := range vals {
		if s, ok := v.(string); ok {
			out = append(out, len(s))
		}
		// non-strings are skipped (or handle/collect an error if you prefer)
	}
	return out
}
```

The comma-ok form returns `(zeroValue, false)` instead of panicking, so you can skip, default, or report the unexpected type. Reserve the single-result assertion for cases where a non-match is genuinely a programming error you *want* to crash on.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it's flaky and sometimes prints 'finished' before the work is done. Explain why and fix it properly:\n\n```go\nfunc main() {\n\tgo doWork()\n\ttime.Sleep(time.Second)\n\tfmt.Println(\"finished\")\n}\n```",
        "response": '''**Anti-pattern: using `time.Sleep` to synchronize with a goroutine.** The sleep is a guess, not a guarantee. If `doWork` takes longer than a second (slow machine, more data), `main` prints "finished" and exits while the work is still running — and when `main` returns, the program terminates, killing the goroutine mid-flight. If it takes less than a second, you waste the remaining time. Either way it's a race.

**Fix — wait for an actual completion signal.** With a `sync.WaitGroup`:

```go
func main() {
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		doWork()
	}()
	wg.Wait() // blocks until doWork actually finishes
	fmt.Println("finished")
}
```

Or, if `doWork` produces a value, signal via a channel and receive it. The principle: synchronize on a real event (`WaitGroup`, channel, `errgroup`), never on wall-clock time. `time.Sleep` in tests and `main` is the most common source of flaky, timing-dependent bugs.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test that uses a t.Helper() assertion helper to keep failure line numbers pointing at the caller, testing this function:\n\n```go\n// Abs returns the absolute value of x.\nfunc Abs(x int) int {\n\tif x < 0 {\n\t\treturn -x\n\t}\n\treturn x\n}\n```",
        "response": '''```go
func assertEqual(t *testing.T, got, want int) {
	t.Helper() // report failures at the caller's line, not inside this helper
	if got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}

func TestAbs(t *testing.T) {
	assertEqual(t, Abs(5), 5)
	assertEqual(t, Abs(-5), 5)
	assertEqual(t, Abs(0), 0)
	assertEqual(t, Abs(-1), 1)
}
```

Calling `t.Helper()` at the top of `assertEqual` marks it as a test helper, so when an assertion fails the reported file:line points at the `assertEqual(...)` call inside `TestAbs` rather than at the `t.Errorf` line inside the helper. That makes failures immediately traceable to the specific case. The cases cover the negative branch, the positive branch, and the `0` boundary.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go benchmark that does one-time setup before the measured loop, using b.ResetTimer, for this function:\n\n```go\n// SumSlice returns the sum of the slice.\nfunc SumSlice(s []int) int {\n\ttotal := 0\n\tfor _, v := range s {\n\t\ttotal += v\n\t}\n\treturn total\n}\n```",
        "response": '''```go
func BenchmarkSumSlice(b *testing.B) {
	// Expensive setup that should NOT count toward the measurement.
	data := make([]int, 10000)
	for i := range data {
		data[i] = i
	}

	b.ResetTimer() // zero the clock so only the loop below is timed

	for i := 0; i < b.N; i++ {
		_ = SumSlice(data)
	}
}
```

`b.ResetTimer()` discards the time (and allocations) spent building `data`, so the reported ns/op reflects only `SumSlice` itself rather than the setup. Assign the result to `_` (or a package-level sink) so the compiler can't optimize the call away. Run with `go test -bench=SumSlice -benchmem`; if you need to exclude per-iteration setup too, use `b.StopTimer()`/`b.StartTimer()` around it inside the loop.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain how interfaces and implicit satisfaction work in this Go code, and why Rectangle doesn't need to declare that it implements Stringer:\n\n```go\ntype Stringer interface{ String() string }\n\ntype Rectangle struct{ W, H int }\n\nfunc (r Rectangle) String() string {\n\treturn fmt.Sprintf(\"%dx%d\", r.W, r.H)\n}\n\nfunc printIt(s Stringer) { fmt.Println(s.String()) }\n```",
        "response": '''Go interfaces are satisfied **implicitly** (structural, "duck typing"): a type implements an interface simply by having the required methods — there is no `implements` keyword and no explicit declaration.

In this code:
- `Stringer` requires one method: `String() string`.
- `Rectangle` defines `func (r Rectangle) String() string`. That's the whole requirement, so `Rectangle` automatically satisfies `Stringer`. You can pass a `Rectangle` to `printIt(s Stringer)` and it just works.
- Nothing links `Rectangle` to `Stringer` in source — the compiler checks method sets at the point of *use* (the assignment/argument-passing), and if they match, it's allowed.

Why this matters:
- **Decoupling:** `Rectangle` doesn't import or know about `Stringer`. You can define an interface in your own package that an existing third-party type satisfies, without modifying that type. This is the opposite of nominal systems (Java/C#) where a class must declare the interfaces it implements.
- **Small interfaces:** because satisfaction is automatic, Go favors tiny interfaces (often one method, like `io.Reader`, `io.Writer`, `fmt.Stringer`) that many types incidentally satisfy.
- **Method sets and pointers:** if `String` had a pointer receiver `(*Rectangle)`, then only `*Rectangle` — not `Rectangle` — would satisfy `Stringer`, because value method sets exclude pointer-receiver methods. Here the value receiver means both `Rectangle` and `*Rectangle` satisfy it.

A common idiom to *assert* (at compile time) that a type satisfies an interface is `var _ Stringer = Rectangle{}` — if it ever stops satisfying, the build breaks.''',
    },
]
