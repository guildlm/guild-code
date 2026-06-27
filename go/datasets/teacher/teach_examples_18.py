# -*- coding: utf-8 -*-
"""Batch 18 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that computes the SHA-256 hash of a string and prints it as a hex string using crypto/sha256 and encoding/hex.",
        "response": '''```go
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

func main() {
	data := []byte("GuildLM")

	sum := sha256.Sum256(data) // returns a [32]byte array
	fmt.Println("sha256:", hex.EncodeToString(sum[:]))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that upper-cases every word in a string using regexp.ReplaceAllStringFunc with a word-matching pattern. Print the result.",
        "response": '''```go
package main

import (
	"fmt"
	"regexp"
	"strings"
)

func main() {
	re := regexp.MustCompile(`\\b\\w+\\b`) // match whole words

	// ReplaceAllStringFunc transforms each match with the given function.
	out := re.ReplaceAllStringFunc("hello world go", strings.ToUpper)
	fmt.Println(out) // HELLO WORLD GO
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a custom type CSV ([]string) that implements json.Unmarshaler to decode a comma-separated JSON string into a slice. Decode a struct containing it and print the slice.",
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

type CSV []string

// UnmarshalJSON decodes a JSON string "a,b,c" into a []string.
func (c *CSV) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err != nil {
		return err
	}
	*c = strings.Split(s, ",")
	return nil
}

func main() {
	var post struct {
		Tags CSV `json:"tags"`
	}
	if err := json.Unmarshal([]byte(`{"tags":"go,backend,fast"}`), &post); err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(post.Tags, "count:", len(post.Tags)) // [go backend fast] count: 3
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that checks at runtime whether an io.Writer also implements io.Closer using a type assertion, demonstrating both a closer and a non-closer.",
        "response": '''```go
package main

import (
	"bytes"
	"fmt"
	"io"
)

func describe(name string, w io.Writer) {
	// Comma-ok assertion: does this concrete writer also satisfy io.Closer?
	if _, ok := w.(io.Closer); ok {
		fmt.Printf("%s is also a Closer\\n", name)
	} else {
		fmt.Printf("%s is NOT a Closer\\n", name)
	}
}

// nopCloser is a writer that also implements Close.
type nopCloser struct{ io.Writer }

func (nopCloser) Close() error { return nil }

func main() {
	var buf bytes.Buffer
	describe("bytes.Buffer", &buf)              // not a Closer
	describe("nopCloser", nopCloser{Writer: &buf}) // is a Closer
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that rounds and truncates a time.Duration to the nearest minute using Duration.Round and Duration.Truncate, printing all three values.",
        "response": '''```go
package main

import (
	"fmt"
	"time"
)

func main() {
	d := 1*time.Hour + 23*time.Minute + 45*time.Second

	fmt.Println("original: ", d)                    // 1h23m45s
	fmt.Println("truncated:", d.Truncate(time.Minute)) // 1h23m0s (rounds toward zero)
	fmt.Println("rounded:  ", d.Round(time.Minute))    // 1h24m0s (nearest)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a Flags bitmask type (iota) demonstrating set (|=), toggle (^=), and clear (&^=) operations, then report which flags are set.",
        "response": '''```go
package main

import "fmt"

type Flags uint8

const (
	FlagA Flags = 1 << iota
	FlagB
	FlagC
)

func main() {
	var f Flags
	f |= FlagA | FlagC // set A and C
	f ^= FlagC         // toggle C (now off)
	f &^= FlagA        // clear A with AND-NOT
	f |= FlagB         // set B

	fmt.Printf("A=%t B=%t C=%t\\n", f&FlagA != 0, f&FlagB != 0, f&FlagC != 0)
	// A=false B=true C=false
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with generic Filter and Map functions, composing them to take the even numbers of a slice and square them. Print the result.",
        "response": '''```go
package main

import "fmt"

func Filter[T any](s []T, keep func(T) bool) []T {
	var out []T
	for _, v := range s {
		if keep(v) {
			out = append(out, v)
		}
	}
	return out
}

func Map[T, U any](s []T, f func(T) U) []U {
	out := make([]U, len(s))
	for i, v := range s {
		out[i] = f(v)
	}
	return out
}

func main() {
	nums := []int{1, 2, 3, 4, 5, 6}
	evens := Filter(nums, func(n int) bool { return n%2 == 0 })
	squares := Map(evens, func(n int) int { return n * n })
	fmt.Println(squares) // [4 16 36]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with withTimeout(d time.Duration, fn func() int) (int, error) that runs fn in a goroutine and returns its result, or a timeout error if it takes too long. Show a fast success and a slow timeout. Avoid leaking the goroutine.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
	"time"
)

// withTimeout runs fn and returns its result, or an error if d elapses first.
func withTimeout(d time.Duration, fn func() int) (int, error) {
	// Buffered so the goroutine can always send and exit, even after a timeout.
	resultCh := make(chan int, 1)
	go func() { resultCh <- fn() }()

	select {
	case r := <-resultCh:
		return r, nil
	case <-time.After(d):
		return 0, errors.New("operation timed out")
	}
}

func main() {
	r, err := withTimeout(50*time.Millisecond, func() int {
		time.Sleep(10 * time.Millisecond)
		return 42
	})
	fmt.Println("fast:", r, err)

	_, err = withTimeout(10*time.Millisecond, func() int {
		time.Sleep(50 * time.Millisecond)
		return 1
	})
	fmt.Println("slow:", err)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with an insert(s []int, x int) []int function that inserts x into a sorted slice at the correct position using sort.SearchInts, keeping it sorted. Print the result.",
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

// insert places x into the sorted slice s, preserving order.
func insert(s []int, x int) []int {
	i := sort.SearchInts(s, x) // first index where s[i] >= x
	s = append(s, 0)           // grow by one
	copy(s[i+1:], s[i:])       // shift the tail right
	s[i] = x
	return s
}

func main() {
	s := []int{1, 3, 5, 7}
	s = insert(s, 4)
	fmt.Println(s) // [1 3 4 5 7]
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program where 10 goroutines race to claim a one-time slot via atomic CompareAndSwap (0 -> 1); exactly one should win. Count and print the winners.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

func main() {
	var slot atomic.Int32
	winners := make(chan int, 10)

	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			// Only the first goroutine to swap 0->1 succeeds; the rest see 1.
			if slot.CompareAndSwap(0, 1) {
				winners <- id
			}
		}(i)
	}
	wg.Wait()
	close(winners)

	count := 0
	for range winners {
		count++
	}
	fmt.Println("winners:", count) // exactly 1
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code from a security standpoint; comparing the token this way is unsafe. Explain and fix:\n\n```go\nfunc validToken(provided, expected string) bool {\n\treturn provided == expected\n}\n```",
        "response": '''**Security bug: comparing secrets with `==` is vulnerable to a timing attack.** Go's string `==` (like `bytes.Equal`) short-circuits at the first differing byte. The time it takes therefore depends on *how many leading bytes match*, which leaks information: an attacker who can measure response times can recover the secret one byte at a time by observing which guesses take fractionally longer. For tokens, API keys, HMACs, and password hashes, you must compare in **constant time** — independent of the data.

**Fix — use `crypto/subtle.ConstantTimeCompare`:**

```go
import "crypto/subtle"

func validToken(provided, expected string) bool {
	// Returns 1 only if the byte slices are equal, in time independent of content.
	return subtle.ConstantTimeCompare([]byte(provided), []byte(expected)) == 1
}
```

`ConstantTimeCompare` examines every byte regardless of where a mismatch occurs, so the comparison time doesn't reveal how much matched. Notes: it returns `1`/`0` (compare `== 1`), and it *does* reveal length differences (it returns 0 immediately if lengths differ), so for variable-length secrets compare fixed-length hashes — e.g. HMAC both sides and compare the digests. The general rule: any equality check on a secret value must be constant-time. (`==` is perfectly fine for non-secret data, where timing leaks nothing useful.)''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code for performance; it's slow when called in a loop. Explain and fix:\n\n```go\nfunc isNumeric(s string) bool {\n\tre := regexp.MustCompile(`^\\d+$`)\n\treturn re.MatchString(s)\n}\n```",
        "response": '''**Performance bug: the regular expression is recompiled on every call.** `regexp.MustCompile` parses the pattern and builds the matching automaton — that work is relatively expensive, and here it's repeated for *every* invocation of `isNumeric`. In a hot path or a loop over many strings, the compilation dominates the runtime and allocates each time.

**Fix — compile the regex once, as a package-level variable:**

```go
var numericRe = regexp.MustCompile(`^\\d+$`)

func isNumeric(s string) bool {
	return numericRe.MatchString(s)
}
```

A compiled `*regexp.Regexp` is **safe for concurrent use** by multiple goroutines, so a single package-level instance can be shared freely. Compiling at package init (via `MustCompile`, which panics on a bad pattern — appropriate for a constant regex known at build time) means the cost is paid exactly once at startup. The general rule: anything expensive to build but immutable and reusable — compiled regexes, `text/template`/`html/template`, database prepared statements, `time.Location` — should be created once and reused, never rebuilt per call.

(Aside: for a simple `^\\d+$` check you don't even need a regex — a loop checking `unicode.IsDigit`/`c < '0' || c > '9'`, or `strconv.Atoi`, is faster still. But when you do use a regex, compile it once.)''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code that models money; explain why float64 is the wrong choice and what to use instead:\n\n```go\ntype Order struct {\n\tTotal float64 // dollars\n}\n\nfunc (o Order) WithTax(rate float64) float64 {\n\treturn o.Total + o.Total*rate\n}\n```",
        "response": '''**Bug: representing money as `float64` causes rounding errors.** Binary floating point can't exactly represent most decimal fractions (`0.1`, `0.20`, `19.99`), so values drift: sums don't add up to the cent, `0.1 + 0.2 != 0.3`, and repeated arithmetic (tax, discounts, currency conversion) accumulates error. For money this is unacceptable — totals fail to reconcile, and you can lose or invent fractions of a cent.

**Fix A — store the smallest currency unit as an integer (cents):**

```go
type Order struct {
	TotalCents int64 // exact: $19.99 -> 1999
}

func (o Order) WithTaxCents(ratePerMille int64) int64 {
	// rate expressed in per-mille (e.g. 75 = 7.5%); round half-up.
	tax := (o.TotalCents*ratePerMille + 500) / 1000
	return o.TotalCents + tax
}
```

Integer cents are exact for addition/subtraction and let you control rounding explicitly at the point it's needed (here, round-half-up on the tax). Format for display by dividing by 100.

**Fix B — use a decimal library** (e.g. `github.com/shopspring/decimal`) when you need arbitrary-precision decimal arithmetic, variable scale, or many currencies:

```go
total := decimal.NewFromString("19.99")
withTax := total.Mul(decimal.NewFromFloat(1.075))
```

Prefer integer minor units (Fix A) for simple, single-currency money — it's allocation-free and fast. Reach for a decimal type (Fix B) for complex financial math. The rule: **never use `float64` for currency or any value where exact decimal arithmetic matters**; floats are for measurements and approximations, not money.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go test for this timeout wrapper, covering both the fast-success and the timeout paths:\n\n```go\nfunc WithTimeout(d time.Duration, fn func() int) (int, error) { /* ... */ }\n```",
        "response": '''```go
func TestWithTimeout(t *testing.T) {
	t.Run("returns result when fast", func(t *testing.T) {
		got, err := WithTimeout(50*time.Millisecond, func() int {
			return 42 // returns immediately
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != 42 {
			t.Errorf("got %d, want 42", got)
		}
	})

	t.Run("errors when slow", func(t *testing.T) {
		_, err := WithTimeout(10*time.Millisecond, func() int {
			time.Sleep(100 * time.Millisecond) // exceeds the timeout
			return 1
		})
		if err == nil {
			t.Fatal("expected a timeout error, got nil")
		}
	})
}
```

The first subtest verifies the happy path returns the function's value with no error. The second forces the work to outlast the deadline and asserts a (non-nil) error comes back. Two practical notes for timing-dependent tests: use a comfortable margin between the fast function's duration and the timeout (and vice-versa) so the test isn't flaky on a busy CI machine; and the implementation must use a **buffered** result channel so the slow goroutine can still send and exit after the timeout — otherwise the test would leak a goroutine on every "slow" run (worth checking with `goleak` if you want to be strict).''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test for a custom json.Unmarshaler that decodes a comma-separated string into a slice:\n\n```go\ntype CSV []string\nfunc (c *CSV) UnmarshalJSON(data []byte) error { /* splits a JSON string on \",\" */ }\n```",
        "response": '''```go
func TestCSVUnmarshalJSON(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    CSV
		wantErr bool
	}{
		{"multiple", `{"tags":"go,backend,fast"}`, CSV{"go", "backend", "fast"}, false},
		{"single", `{"tags":"solo"}`, CSV{"solo"}, false},
		{"empty string", `{"tags":""}`, CSV{""}, false},
		{"wrong type", `{"tags":123}`, nil, true}, // not a JSON string
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var post struct {
				Tags CSV `json:"tags"`
			}
			err := json.Unmarshal([]byte(tt.input), &post)
			if (err != nil) != tt.wantErr {
				t.Fatalf("err = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && !slices.Equal(post.Tags, tt.want) {
				t.Errorf("Tags = %v, want %v", post.Tags, tt.want)
			}
		})
	}
}
```

The cases cover the normal multi-value split, a single value (no separator), and the empty string (which `strings.Split` returns as `[""]` — a deliberately pinned edge so a future "trim empties" change is a conscious decision, not an accident). The "wrong type" case feeds a JSON number where a string is expected and asserts that the custom `UnmarshalJSON` propagates the error from the inner `json.Unmarshal(data, &s)` rather than silently succeeding. Testing a custom unmarshaler end-to-end through `json.Unmarshal` (not by calling the method directly) verifies it's actually wired into the decoder.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain Go generics: type parameters, constraints, and inference, using this snippet:\n\n```go\nfunc Max[T cmp.Ordered](a, b T) T {\n\tif a > b {\n\t\treturn a\n\t}\n\treturn b\n}\n```",
        "response": '''Generics (Go 1.18+) let you write functions and types that work over a *set* of types while keeping full compile-time type safety. `Max` is parameterized so it works for `int`, `float64`, `string`, etc. — without `any`, without runtime type assertions, and without writing one copy per type.

The pieces:

**Type parameters** — the `[T cmp.Ordered]` after the name declares a type parameter `T`. Inside the function, `T` is a real type: `a` and `b` are both `T`, and the return is `T`. At each call site the compiler substitutes a concrete type for `T`.

**Constraints** — `T` isn't "any type"; it's constrained by `cmp.Ordered`. A constraint is an *interface used as a type set* that says what operations `T` must support. `cmp.Ordered` is the set of all types whose values support the ordering operators `< <= > >=` (the integer, float, and string kinds). That's exactly why `a > b` compiles — the constraint promises every permitted `T` supports `>`. Common constraints:
- `any` — no restriction (the type set is all types); you can store, pass, and compare-to-nil, but not use type-specific operators.
- `comparable` — types that support `==`/`!=` (so they can be map keys); required for things like a generic `Set[T comparable]`.
- `cmp.Ordered` — the ordered types (for `<`, sorting, min/max).
- **Custom unions with `~`** — you can define your own: `interface { ~int | ~int64 | ~float64 }`. The `~` means "any type whose *underlying* type is this," so a `type Celsius float64` still satisfies `~float64`. A constraint may also list required *methods* (e.g. `interface { String() string }`), meaning "any type with this method."

**Type inference** — you rarely write the type argument explicitly. The compiler infers `T` from the ordinary arguments: in `Max(3, 5)` it sees two `int`s and infers `T = int`; `Max("a", "b")` infers `string`. You *can* be explicit — `Max[float64](1, 2)` — when inference can't figure it out (e.g. the type parameter only appears in the return type).

**Why use generics vs alternatives:** compared to writing `MaxInt`, `MaxFloat`, ... you get one implementation; compared to `any` + type switches, you keep static type checking, avoid boxing/allocation, and can't pass mismatched types (`Max(1, "x")` won't compile). The guideline: reach for generics when an algorithm or container is genuinely the same across many types and the types are related by a clear constraint (ordering, comparability, a shared method). When behavior should *differ* per type, an ordinary **interface with methods** is still the right tool — generics are for parametric uniformity, interfaces for polymorphic behavior.''',
    },
]
