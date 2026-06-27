# -*- coding: utf-8 -*-
"""Batch 3 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).
go_generator responses are complete, stdlib-only, compilable programs."""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ----------------
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that limits concurrency to 3 simultaneous goroutines using a buffered channel as a semaphore, computing the square of 0..9 into a results slice without a data race.",
        "response": '''```go
package main

import (
	"fmt"
	"sync"
)

func main() {
	const maxConcurrent = 3
	sem := make(chan struct{}, maxConcurrent)
	results := make([]int, 10)

	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			sem <- struct{}{}        // acquire a slot (blocks if 3 are busy)
			defer func() { <-sem }() // release on return
			results[i] = i * i       // each goroutine writes its own index
		}(i)
	}
	wg.Wait()
	fmt.Println(results)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating the functional options pattern: a server struct with sensible defaults configured via WithHost, WithPort, and WithTLS options passed to a newServer constructor. Print the resulting config.",
        "response": '''```go
package main

import "fmt"

type server struct {
	host string
	port int
	tls  bool
}

// Option mutates a server during construction.
type Option func(*server)

func WithHost(h string) Option { return func(s *server) { s.host = h } }
func WithPort(p int) Option    { return func(s *server) { s.port = p } }
func WithTLS() Option          { return func(s *server) { s.tls = true } }

func newServer(opts ...Option) *server {
	s := &server{host: "localhost", port: 8080} // defaults
	for _, opt := range opts {
		opt(s)
	}
	return s
}

func main() {
	s := newServer(WithHost("example.com"), WithPort(443), WithTLS())
	fmt.Printf("%+v\\n", *s)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program defining a Permission bitmask type using iota (Read, Write, Execute) with a Has method, then combine Read|Write and report which permissions are set.",
        "response": '''```go
package main

import "fmt"

// Permission is a bitmask of access rights.
type Permission uint8

const (
	Read Permission = 1 << iota
	Write
	Execute
)

func (p Permission) Has(flag Permission) bool { return p&flag != 0 }

func main() {
	p := Read | Write
	fmt.Println("read:", p.Has(Read))
	fmt.Println("write:", p.Has(Write))
	fmt.Println("execute:", p.Has(Execute))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that returns all prime numbers up to n using the Sieve of Eratosthenes, and prints the primes up to 30.",
        "response": '''```go
package main

import "fmt"

// primes returns all prime numbers <= n using the Sieve of Eratosthenes.
func primes(n int) []int {
	if n < 2 {
		return nil
	}
	composite := make([]bool, n+1)
	var result []int
	for i := 2; i <= n; i++ {
		if composite[i] {
			continue
		}
		result = append(result, i)
		for j := i * i; j <= n; j += i {
			composite[j] = true
		}
	}
	return result
}

func main() {
	fmt.Println(primes(30))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that validates a name and age, collecting multiple validation failures into a single error with errors.Join, and prints the combined error.",
        "response": '''```go
package main

import (
	"errors"
	"fmt"
)

// validate accumulates every problem and joins them into one error.
func validate(name string, age int) error {
	var errs []error
	if name == "" {
		errs = append(errs, errors.New("name is required"))
	}
	if age < 0 {
		errs = append(errs, errors.New("age must be non-negative"))
	}
	if age > 150 {
		errs = append(errs, errors.New("age is implausibly large"))
	}
	return errors.Join(errs...) // returns nil if errs is empty
}

func main() {
	if err := validate("", -5); err != nil {
		fmt.Println("validation failed:")
		fmt.Println(err)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that uses the standard library slices package (Go 1.21+) to sort a slice of ints and query it: print the sorted slice, whether it contains 8, the index of 9, and the maximum.",
        "response": '''```go
package main

import (
	"fmt"
	"slices"
)

func main() {
	nums := []int{5, 2, 8, 1, 9, 2}

	slices.Sort(nums)
	fmt.Println("sorted:    ", nums)
	fmt.Println("contains 8:", slices.Contains(nums, 8))
	fmt.Println("index of 9:", slices.Index(nums, 9))
	fmt.Println("max:       ", slices.Max(nums))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with a reverse(s string) string function that reverses a string by runes so multi-byte (Unicode) characters are preserved. Demonstrate it on a string containing accented and CJK characters.",
        "response": '''```go
package main

import "fmt"

// reverse reverses s by runes, keeping multi-byte characters intact. Reversing
// by bytes would corrupt any character that is more than one byte in UTF-8.
func reverse(s string) string {
	r := []rune(s)
	for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
		r[i], r[j] = r[j], r[i]
	}
	return string(r)
}

func main() {
	fmt.Println(reverse("héllo, 世界"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that starts three workers which run until a context is cancelled, cancels them after a short delay, and has each worker print why it stopped. Use context.WithCancel and select.",
        "response": '''```go
package main

import (
	"context"
	"fmt"
	"sync"
	"time"
)

func worker(ctx context.Context, id int, wg *sync.WaitGroup) {
	defer wg.Done()
	for {
		select {
		case <-ctx.Done():
			fmt.Printf("worker %d stopping: %v\\n", id, ctx.Err())
			return
		case <-time.After(10 * time.Millisecond):
			// perform one unit of work, then loop
		}
	}
}

func main() {
	ctx, cancel := context.WithCancel(context.Background())

	var wg sync.WaitGroup
	for i := 1; i <= 3; i++ {
		wg.Add(1)
		go worker(ctx, i, &wg)
	}

	time.Sleep(25 * time.Millisecond)
	cancel()  // signal every worker at once
	wg.Wait() // wait for them to observe cancellation and exit
	fmt.Println("all workers stopped")
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program demonstrating struct embedding: an Animal with a Describe method embedded into a Dog, showing method promotion and field access. Print the promoted method's output.",
        "response": '''```go
package main

import "fmt"

type Animal struct {
	Name string
}

func (a Animal) Describe() string { return "I am " + a.Name }

// Dog embeds Animal, so Animal's fields and methods are promoted onto Dog.
type Dog struct {
	Animal
	Breed string
}

func main() {
	d := Dog{Animal: Animal{Name: "Rex"}, Breed: "Labrador"}
	fmt.Println(d.Describe())     // promoted method
	fmt.Println(d.Name, d.Breed)  // promoted field + own field
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program with gcd (Euclidean algorithm) and lcm functions for ints, and print gcd(12,18) and lcm(4,6).",
        "response": '''```go
package main

import "fmt"

// gcd returns the greatest common divisor using the iterative Euclidean algorithm.
func gcd(a, b int) int {
	for b != 0 {
		a, b = b, a%b
	}
	return a
}

// lcm returns the least common multiple. Dividing before multiplying avoids
// overflowing for large inputs.
func lcm(a, b int) int {
	if a == 0 || b == 0 {
		return 0
	}
	return a / gcd(a, b) * b
}

func main() {
	fmt.Println("gcd(12, 18) =", gcd(12, 18))
	fmt.Println("lcm(4, 6)   =", lcm(4, 6))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": "Write a complete Go program that efficiently builds a comma-separated string from a slice using strings.Builder (pre-sizing where possible), and prints the result.",
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

// joinCSV concatenates words with commas using a single growing buffer instead
// of repeated string concatenation (which would allocate on every step).
func joinCSV(words []string) string {
	var b strings.Builder
	for i, w := range words {
		if i > 0 {
			b.WriteByte(',')
		}
		b.WriteString(w)
	}
	return b.String()
}

func main() {
	fmt.Println(joinCSV([]string{"alpha", "beta", "gamma"}))
}
```''',
    },

    # ---------------- go_reviewer ----------------
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code; it panics at runtime. Explain why and fix it:\n\n```go\nfunc tally(words []string) map[string]int {\n\tvar counts map[string]int\n\tfor _, w := range words {\n\t\tcounts[w]++\n\t}\n\treturn counts\n}\n```",
        "response": '''**Bug: writing to a nil map panics.** `var counts map[string]int` declares the map variable but leaves it nil — no underlying hash table is allocated. *Reading* a nil map is fine (returns the zero value), but `counts[w]++` is a write, which panics with `assignment to entry in nil map`.

**Fix — initialize the map with `make` (or a literal):**

```go
func tally(words []string) map[string]int {
	counts := make(map[string]int)
	for _, w := range words {
		counts[w]++
	}
	return counts
}
```

`make(map[string]int)` (or `map[string]int{}`) allocates the table so writes succeed. This is the single most common nil-map mistake: a freshly `var`-declared map is read-safe but not write-safe.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code for performance and correctness, and show an idiomatic rewrite:\n\n```go\nfunc concat(items []string) string {\n\tresult := \"\"\n\tfor _, s := range items {\n\t\tresult += s + \",\"\n\t}\n\treturn result\n}\n```",
        "response": '''Two problems:

1. **Quadratic performance.** Strings are immutable, so `result += ...` allocates a brand-new string and copies everything on every iteration — O(n²) total for n items. For large slices this is the real bottleneck.
2. **Trailing comma.** The result ends with a stray `,` (e.g. `a,b,c,`).

**Idiomatic fix.** For a plain separator, just use `strings.Join`:

```go
func concat(items []string) string {
	return strings.Join(items, ",")
}
```

If you need custom per-item logic, use a `strings.Builder` (single growing buffer, amortized O(n)):

```go
func concat(items []string) string {
	var b strings.Builder
	for i, s := range items {
		if i > 0 {
			b.WriteByte(',')
		}
		b.WriteString(s)
	}
	return b.String()
}
```

Both run in linear time and produce no trailing comma. Reach for `strings.Join` first; drop to `Builder` only when the elements need transforming.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code for a goroutine leak and fix it:\n\n```go\nfunc firstResult(urls []string) string {\n\tch := make(chan string)\n\tfor _, u := range urls {\n\t\tgo func(u string) {\n\t\t\tch <- fetch(u)\n\t\t}(u)\n\t}\n\treturn <-ch\n}\n```",
        "response": '''**Bug: goroutine leak.** The channel is unbuffered and `main` only receives once (`<-ch`). The first goroutine to send succeeds; every other goroutine blocks **forever** on `ch <- fetch(u)` because no one will ever receive their value. Those goroutines (and whatever resources `fetch` holds) leak for the lifetime of the process.

**Fix A — buffer the channel so every send can complete:**

```go
func firstResult(urls []string) string {
	ch := make(chan string, len(urls)) // every goroutine can send without blocking
	for _, u := range urls {
		go func(u string) { ch <- fetch(u) }(u)
	}
	return <-ch
}
```

The extra results sit in the buffer and are garbage-collected with the channel once `firstResult` returns.

**Fix B — cancel the losers with context** (better if `fetch` is expensive and should stop early):

```go
func firstResult(ctx context.Context, urls []string) string {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel() // tell stragglers to stop
	ch := make(chan string, len(urls))
	for _, u := range urls {
		go func(u string) { ch <- fetchCtx(ctx, u) }(u)
	}
	return <-ch
}
```

Buffering stops the leak; context cancellation also stops the wasted work.''',
    },
    {
        "role": "go_reviewer",
        "instruction": "Review this Go code that writes a file; a reviewer flags a silent failure mode. Explain and fix:\n\n```go\nfunc writeConfig(path string, data []byte) error {\n\tf, err := os.Create(path)\n\tif err != nil {\n\t\treturn err\n\t}\n\tdefer f.Close()\n\t_, err = f.Write(data)\n\treturn err\n}\n```",
        "response": '''**Issue: the error from `defer f.Close()` is discarded.** For a file you are *writing*, `Close` is not just bookkeeping — it can flush buffered data and surface real errors (a full disk, an I/O failure). With `defer f.Close()` that error is dropped, so `writeConfig` can report success while the file is actually truncated or corrupt.

**Fix — capture the close error via a named return, without masking a write error:**

```go
func writeConfig(path string, data []byte) (err error) {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer func() {
		if cerr := f.Close(); cerr != nil && err == nil {
			err = cerr // only surface Close's error if Write succeeded
		}
	}()

	if _, err = f.Write(data); err != nil {
		return err
	}
	return nil
}
```

The deferred closure reports `Close`'s error only when there wasn't already a write error (so the original, more relevant failure isn't masked). For durability-critical writes you'd also `f.Sync()` before closing, and ideally write to a temp file then `os.Rename` for atomic replacement.''',
    },

    # ---------------- go_tester ----------------
    {
        "role": "go_tester",
        "instruction": "Write a Go benchmark and a correctness test for this function:\n\n```go\n// Fib returns the nth Fibonacci number iteratively.\nfunc Fib(n int) int {\n\ta, b := 0, 1\n\tfor i := 0; i < n; i++ {\n\t\ta, b = b, a+b\n\t}\n\treturn a\n}\n```",
        "response": '''```go
func TestFib(t *testing.T) {
	tests := []struct {
		n    int
		want int
	}{
		{0, 0}, {1, 1}, {2, 1}, {3, 2}, {4, 3}, {5, 5}, {10, 55},
	}
	for _, tt := range tests {
		if got := Fib(tt.n); got != tt.want {
			t.Errorf("Fib(%d) = %d, want %d", tt.n, got, tt.want)
		}
	}
}

func BenchmarkFib(b *testing.B) {
	for i := 0; i < b.N; i++ {
		Fib(30)
	}
}
```

The test pins the base cases (`Fib(0)=0`, `Fib(1)=1`) and a few known values so any off-by-one in the loop is caught. The benchmark calls `Fib(30)` `b.N` times — the framework chooses `b.N` to run long enough for a stable ns/op measurement. Run it with `go test -bench=Fib -benchmem`; because `Fib` allocates nothing, you'd expect `0 B/op`.''',
    },
    {
        "role": "go_tester",
        "instruction": "Write a Go test (using t.TempDir) for this function that writes lines to a file:\n\n```go\n// WriteLines writes each line followed by a newline to path.\nfunc WriteLines(path string, lines []string) error {\n\tf, err := os.Create(path)\n\tif err != nil {\n\t\treturn err\n\t}\n\tdefer f.Close()\n\tfor _, l := range lines {\n\t\tif _, err := fmt.Fprintln(f, l); err != nil {\n\t\t\treturn err\n\t\t}\n\t}\n\treturn nil\n}\n```",
        "response": '''```go
func TestWriteLines(t *testing.T) {
	dir := t.TempDir() // auto-removed when the test finishes
	path := filepath.Join(dir, "out.txt")

	lines := []string{"alpha", "beta", "gamma"}
	if err := WriteLines(path, lines); err != nil {
		t.Fatalf("WriteLines: %v", err)
	}

	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	want := "alpha\\nbeta\\ngamma\\n"
	if string(got) != want {
		t.Errorf("file = %q, want %q", got, want)
	}
}
```

`t.TempDir()` gives a unique directory that the testing framework deletes automatically, so the test leaves nothing behind and can run in parallel with others. We write known lines, read the file back, and assert the exact bytes — including the trailing newline after the last line, which `fmt.Fprintln` adds and is easy to get wrong.''',
    },

    # ---------------- go_explainer ----------------
    {
        "role": "go_explainer",
        "instruction": "Explain the difference between value and pointer receivers in this Go code and why only one of the increments persists:\n\n```go\ntype Counter struct{ n int }\n\nfunc (c Counter) IncVal()  { c.n++ }\nfunc (c *Counter) IncPtr() { c.n++ }\n\nfunc main() {\n\tc := Counter{}\n\tc.IncVal()\n\tc.IncPtr()\n\tfmt.Println(c.n)\n}\n```",
        "response": '''This prints `1`, because only `IncPtr` mutates the original `Counter`.

- **Value receiver** `func (c Counter) IncVal()` operates on a **copy** of the `Counter`. Inside the method, `c.n++` increments the copy's field; when the method returns, the copy is discarded and the caller's `c` is untouched. So `IncVal` has no lasting effect.
- **Pointer receiver** `func (c *Counter) IncPtr()` receives the **address** of the caller's `Counter`. `c.n++` dereferences that pointer and increments the original field, so the change persists.
- In `main`, `c` is an addressable variable, so `c.IncPtr()` is shorthand that Go rewrites as `(&c).IncPtr()` automatically — that's why you don't have to write the `&` yourself.

Practical guidance:
- Use a **pointer receiver** when the method must modify the receiver, or when the struct is large and you want to avoid copying it.
- Be **consistent**: if any method needs a pointer receiver, give them all pointer receivers so the method set is uniform.
- This also affects interface satisfaction: methods with pointer receivers are only in the method set of `*Counter`, not `Counter`, so you'd need a `*Counter` to satisfy an interface that requires `IncPtr`.''',
    },
]
