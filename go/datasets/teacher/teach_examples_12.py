# -*- coding: utf-8 -*-
"""Batch 12 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that splits 'name=value' style strings using strings.Cut, handling both the found and not-found cases.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

func main() {
	// Cut splits around the FIRST occurrence of sep; ok reports if it was found.
	if key, val, ok := strings.Cut("name=GuildLM", "="); ok {
		fmt.Printf("key=%q val=%q\\n", key, val)
	}
	if _, _, ok := strings.Cut("no-separator", "="); !ok {
		fmt.Println("no separator found")
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that inserts and deletes elements in a slice using the slices.Insert and slices.Delete helpers (Go 1.21+). Print the slice after each operation.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	s := []int{1, 2, 5}

	s = slices.Insert(s, 2, 3, 4) // insert 3,4 starting at index 2
	fmt.Println("after insert:", s) // [1 2 3 4 5]

	s = slices.Delete(s, 1, 3) // delete the half-open range [1,3)
	fmt.Println("after delete:", s) // [1 4 5]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that copies a map with maps.Clone (Go 1.21+) and shows that mutating the copy does not affect the original. Print both lengths.",
        "response": '''```go
package main

import (
	"fmt"
	"maps"
)

func main() {
	orig := map[string]int{"a": 1, "b": 2}

	cp := maps.Clone(orig) // shallow copy of the map
	cp["c"] = 3            // affects only the copy

	fmt.Println("orig len:", len(orig)) // 2
	fmt.Println("copy len:", len(cp))   // 3
	fmt.Println("orig has c:", func() bool { _, ok := orig["c"]; return ok }())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating common math package functions: Sqrt, Floor, Ceil, Round, and Pow. Print each result.",
        "response": '''```go
package main

import (
	"fmt"
	"math"
)

func main() {
	fmt.Printf("sqrt(2)    = %.4f\\n", math.Sqrt(2))
	fmt.Printf("floor(2.7) = %.0f\\n", math.Floor(2.7))
	fmt.Printf("ceil(2.1)  = %.0f\\n", math.Ceil(2.1))
	fmt.Printf("round(2.5) = %.0f\\n", math.Round(2.5))
	fmt.Printf("pow(2, 8)  = %.0f\\n", math.Pow(2, 8))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with isPowerOfTwo(n int) bool that uses the n & (n-1) bit trick, and test it on several numbers.",
        "response": '''```go
package main

import "fmt"

// isPowerOfTwo reports whether n is a positive power of two. A power of two has
// exactly one set bit, so n & (n-1) clears it to zero.
func isPowerOfTwo(n int) bool {
	return n > 0 && n&(n-1) == 0
}

func main() {
	for _, n := range []int{1, 2, 3, 4, 16, 18, 64} {
		fmt.Printf("%2d -> %t\\n", n, isPowerOfTwo(n))
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with safeIndex(s []int, i int) (int, error) that returns s[i] but converts an out-of-range panic into an error using defer/recover and a named return. Show a valid and an invalid access.",
        "response": '''```go
package main

import "fmt"

// safeIndex returns s[i], converting an out-of-range panic into an error.
func safeIndex(s []int, i int) (val int, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("safeIndex(%d): %v", i, r)
		}
	}()
	return s[i], nil
}

func main() {
	s := []int{10, 20, 30}
	if v, err := safeIndex(s, 1); err == nil {
		fmt.Println("ok:", v)
	}
	if _, err := safeIndex(s, 9); err != nil {
		fmt.Println("recovered:", err)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that parses a human-readable duration string like '1h30m15s' with time.ParseDuration and prints it back plus its value in total seconds.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	d, err := time.ParseDuration("1h30m15s")
	if err != nil {
		fmt.Println("parse error:", err)
		return
	}
	fmt.Println("duration:     ", d)
	fmt.Printf("total seconds: %.0f\\n", d.Seconds())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining an Animal interface with a Sound method, implemented by Dog and Cat, and iterate a []Animal printing each sound (polymorphic dispatch).",
        "response": '''```go
package main

import "fmt"

type Animal interface {
	Sound() string
}

type Dog struct{}

func (Dog) Sound() string { return "Woof" }

type Cat struct{}

func (Cat) Sound() string { return "Meow" }

func main() {
	animals := []Animal{Dog{}, Cat{}, Dog{}}
	for _, a := range animals {
		fmt.Println(a.Sound()) // dynamic dispatch to the concrete type's method
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that stably sorts a slice of {name, price} products by ascending price using slices.SortStableFunc with cmp.Compare, so equal prices keep input order. Print the result.",
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
	"slices"
)

type product struct {
	name  string
	price int
}

func main() {
	products := []product{
		{"pen", 3}, {"book", 3}, {"lamp", 12}, {"cup", 5},
	}

	// Stable: pen and book (both 3) keep their original relative order.
	slices.SortStableFunc(products, func(a, b product) int {
		return cmp.Compare(a.price, b.price)
	})

	for _, p := range products {
		fmt.Printf("%s:%d ", p.name, p.price)
	}
	fmt.Println() // pen:3 book:3 cup:5 lamp:12
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses json.RawMessage to defer decoding a polymorphic payload: first decode an envelope with a type tag, then decode the payload based on that tag. Print the decoded point.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
)

type envelope struct {
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload"` // kept raw until we know the type
}

func main() {
	data := `{"type":"point","payload":{"x":1,"y":2}}`

	var env envelope
	if err := json.Unmarshal([]byte(data), &env); err != nil {
		fmt.Println("error:", err)
		return
	}

	switch env.Type {
	case "point":
		var p struct{ X, Y int }
		if err := json.Unmarshal(env.Payload, &p); err != nil {
			fmt.Println("payload error:", err)
			return
		}
		fmt.Printf("point: %+v\\n", p)
	default:
		fmt.Println("unknown type:", env.Type)
	}
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; average([]int{1,2}) returns 1 instead of 1.5, and it can divide by zero. Explain and fix:\n\n```go\nfunc average(nums []int) float64 {\n\tsum := 0\n\tfor _, n := range nums {\n\t\tsum += n\n\t}\n\treturn float64(sum / len(nums))\n}\n```",
        "response": '''**Two bugs:**

1. **Integer division before conversion.** `sum / len(nums)` divides two `int`s, truncating the fractional part, and *then* converts to `float64`. For `{1, 2}`, `3 / 2 == 1`, so you get `1.0` instead of `1.5`. The `float64(...)` is applied too late.
2. **Division by zero.** For an empty slice, `len(nums) == 0`, and `sum / 0` panics (integer divide by zero).

**Fix — guard the empty case and convert before dividing:**

```go
func average(nums []int) float64 {
	if len(nums) == 0 {
		return 0 // or return an error, depending on the contract
	}
	sum := 0
	for _, n := range nums {
		sum += n
	}
	return float64(sum) / float64(len(nums))
}
```

Converting both operands to `float64` makes the division floating-point (`3.0 / 2.0 == 1.5`). The empty-slice guard avoids the panic — returning `0` is one choice; returning `(float64, error)` is better if "no data" is meaningfully different from "average is zero". General rule for averages/percentages/ratios: convert to float *before* the division, and always consider the zero-denominator case.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it panics with a nil pointer dereference when the request fails. Explain the ordering bug and fix:\n\n```go\nfunc get(url string) ([]byte, error) {\n\tresp, err := http.Get(url)\n\tdefer resp.Body.Close()\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\treturn io.ReadAll(resp.Body)\n}\n```",
        "response": '''**Bug: `defer resp.Body.Close()` runs before the error check.** When `http.Get` fails, it returns `resp == nil` and a non-nil `err`. But the `defer resp.Body.Close()` line has already been registered with that nil `resp`. The function then returns the error — and as it returns, the deferred call executes `nil.Body.Close()`, panicking with a nil pointer dereference. The error path crashes instead of returning cleanly.

**Fix — check the error first, then defer the close:**

```go
func get(url string) ([]byte, error) {
	resp, err := http.Get(url)
	if err != nil {
		return nil, err // resp is nil here; nothing to close
	}
	defer resp.Body.Close() // only reached when resp is valid

	return io.ReadAll(resp.Body)
}
```

The ordering rule for any function that returns a `(resource, error)` pair: **validate `err` before touching or deferring cleanup on the resource.** On the error path the resource is typically nil/zero, so deferring a method call on it is unsafe. Only after you've confirmed `err == nil` is the resource guaranteed valid.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it usually prints nothing. Explain why the goroutines don't run and fix it:\n\n```go\nfunc main() {\n\tfor i := 0; i < 5; i++ {\n\t\tgo func(i int) {\n\t\t\tfmt.Println(i)\n\t\t}(i)\n\t}\n}\n```",
        "response": '''**Bug: nothing waits for the goroutines, so `main` exits before they run.** `go func(...)` schedules each goroutine and returns immediately. The `for` loop finishes almost instantly, `main` returns, and **when `main` returns the whole program exits** — the runtime does not wait for outstanding goroutines. They're killed before the scheduler ever gives them a chance to print. (You might occasionally see partial output, which makes it a flaky bug.)

**Fix — wait for completion with a `sync.WaitGroup`:**

```go
func main() {
	var wg sync.WaitGroup
	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			fmt.Println(i)
		}(i)
	}
	wg.Wait() // block until all five goroutines finish
}
```

`wg.Add(1)` before each launch, `defer wg.Done()` inside, and `wg.Wait()` after the loop guarantees `main` doesn't return until every goroutine has run. The underlying principle: goroutines have no implicit lifetime tie to the function that started them — you must explicitly synchronize on their completion (WaitGroup, channel, or errgroup) whenever you need their work to actually happen before proceeding.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a table-driven test (including the empty-input edge case) for this function:\n\n```go\n// Average returns the mean of nums, or 0 for an empty slice.\nfunc Average(nums []int) float64 {\n\tif len(nums) == 0 {\n\t\treturn 0\n\t}\n\tsum := 0\n\tfor _, n := range nums {\n\t\tsum += n\n\t}\n\treturn float64(sum) / float64(len(nums))\n}\n```",
        "response": '''```go
func TestAverage(t *testing.T) {
	tests := []struct {
		name string
		in   []int
		want float64
	}{
		{"empty", nil, 0},
		{"single", []int{5}, 5},
		{"two -> fractional", []int{1, 2}, 1.5},
		{"with negatives", []int{-2, 0, 2}, 0},
		{"larger set", []int{10, 20, 30, 40}, 25},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := Average(tt.in)
			if math.Abs(got-tt.want) > 1e-9 {
				t.Errorf("Average(%v) = %v, want %v", tt.in, got, tt.want)
			}
		})
	}
}
```

Two deliberate choices. The `"two -> fractional"` case (`1.5`) is the one that would catch the classic integer-division bug — an implementation doing `sum/len` then converting would return `1.0` and fail here. And the result is compared with an epsilon (`math.Abs(got-want) > 1e-9`) rather than `==`, because `Average` returns a `float64` and exact float equality is unreliable. The empty case pins the documented "return 0" contract.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test verifying polymorphic dispatch for this interface and its implementations:\n\n```go\ntype Animal interface{ Sound() string }\ntype Dog struct{}\nfunc (Dog) Sound() string { return \"Woof\" }\ntype Cat struct{}\nfunc (Cat) Sound() string { return \"Meow\" }\n```",
        "response": '''```go
func TestAnimalSound(t *testing.T) {
	tests := []struct {
		name   string
		animal Animal
		want   string
	}{
		{"dog", Dog{}, "Woof"},
		{"cat", Cat{}, "Meow"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.animal.Sound(); got != tt.want {
				t.Errorf("%T.Sound() = %q, want %q", tt.animal, got, tt.want)
			}
		})
	}
}

// Compile-time assertions that the types satisfy the interface.
var (
	_ Animal = Dog{}
	_ Animal = Cat{}
)
```

The table stores each concrete type as an `Animal` interface value and checks that calling `Sound()` dispatches to the right implementation — that's the behavior the interface promises. The `var _ Animal = Dog{}` lines are a common idiom: they assert *at compile time* that `Dog` and `Cat` still satisfy `Animal`, so if someone changes a method signature the build breaks immediately rather than only failing where the value is used. Using `%T` in the error message prints the concrete type, which makes a failure easy to pinpoint.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain the empty interface (`any` / `interface{}`) in Go — what it means, how you get values back out, and when to prefer generics — using this snippet:\n\n```go\nfunc describe(v any) {\n\tfmt.Printf(\"%v is a %T\\n\", v, v)\n}\n```",
        "response": '''`any` is an alias for `interface{}`, the **empty interface** — an interface with zero methods. Since every type has at least zero methods, **every value satisfies `any`**, so a parameter of type `any` can hold a value of *any* type. That's what lets `describe` accept an `int`, a `string`, a struct, anything.

How values are stored and retrieved:
- An `any` value is a two-word box: it records the **dynamic type** and a pointer to the **value**. `fmt`'s `%T` reads that dynamic type, `%v` formats the value — which is how `describe` can report both.
- To *use* the underlying value as its concrete type, you must extract it with a **type assertion** (`s, ok := v.(string)`) or a **type switch** (`switch x := v.(type) { case int: ... }`). You can't call type-specific methods or operators on an `any` directly — the compiler only knows it's "some type."

When to prefer **generics** instead (Go 1.18+):
- Reach for `any` only when you genuinely don't know or don't care about the type — heterogeneous containers, `fmt`-style formatting, decoding arbitrary JSON (`map[string]any`), plugin boundaries.
- Prefer **generics** (`func Max[T cmp.Ordered](...)`, `[]T`) whenever the types are related or you need type safety. Generics keep the concrete type through the call, so you get compile-time checking, no boxing/allocation overhead, and no runtime type assertions. `any` throws that information away and pushes the check to runtime, where a wrong assertion panics.

Rule of thumb: `any` says "I'll inspect the type at runtime"; a generic type parameter says "I'll preserve the type at compile time." If you find yourself immediately type-asserting an `any` parameter back to a known set of types, that's usually a sign a generic (or a real interface with methods) is the better design.''',
    },
]
