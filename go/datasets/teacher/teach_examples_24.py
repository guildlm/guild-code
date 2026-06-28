# -*- coding: utf-8 -*-
"""Batch 24 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Encoding/IO/sorting + efficiency edits + more reviewer pitfalls. go_generator
responses are complete, stdlib-only, compilable programs (compile-verified by
teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program that parses CSV text with encoding/csv "
            "and prints the records. Standard library only."
        ),
        "response": '''```go
package main

import (
	"encoding/csv"
	"fmt"
	"strings"
)

// parseCSV reads all CSV records from text.
func parseCSV(text string) ([][]string, error) {
	return csv.NewReader(strings.NewReader(text)).ReadAll()
}

func main() {
	rows, err := parseCSV("name,age\\nann,30\\nbob,25\\n")
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	for _, row := range rows {
		fmt.Println(row)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with RoundTrip(s string) (string, error) "
            "that base64-encodes then decodes s (proving it is lossless). Standard "
            "library only."
        ),
        "response": '''```go
package main

import (
	"encoding/base64"
	"fmt"
)

// RoundTrip encodes s to base64 and back, returning the decoded result.
func RoundTrip(s string) (string, error) {
	enc := base64.StdEncoding.EncodeToString([]byte(s))
	dec, err := base64.StdEncoding.DecodeString(enc)
	if err != nil {
		return "", err
	}
	return string(dec), nil
}

func main() {
	got, err := RoundTrip("hello, 世界")
	fmt.Println(got, err)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program that sorts a []Person by Age ascending, "
            "then Name ascending as a tiebreak, using sort.Slice. Standard library "
            "only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"sort"
)

type Person struct {
	Name string
	Age  int
}

// SortPeople orders people by age, breaking ties by name.
func SortPeople(ps []Person) {
	sort.Slice(ps, func(i, j int) bool {
		if ps[i].Age != ps[j].Age {
			return ps[i].Age < ps[j].Age
		}
		return ps[i].Name < ps[j].Name
	})
}

func main() {
	ps := []Person{{"Bob", 30}, {"Ann", 30}, {"Cy", 25}}
	SortPeople(ps)
	fmt.Println(ps)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with RLE(s string) string returning a "
            "run-length encoding like \"a3b2c1\". Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"strconv"
	"strings"
)

// RLE returns the run-length encoding of s, e.g. "aaabbc" -> "a3b2c1".
func RLE(s string) string {
	if s == "" {
		return ""
	}
	runes := []rune(s)
	var b strings.Builder
	count := 1
	for i := 1; i <= len(runes); i++ {
		if i < len(runes) && runes[i] == runes[i-1] {
			count++
			continue
		}
		b.WriteRune(runes[i-1])
		b.WriteString(strconv.Itoa(count))
		count = 1
	}
	return b.String()
}

func main() {
	fmt.Println(RLE("aaabbc"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this function to avoid quadratic string concatenation; build the "
            "result efficiently. Original:\n```go\npackage main\nimport \"fmt\"\n"
            "func Join(words []string) string {\n\ts := \"\"\n\tfor i, w := range words {\n"
            "\t\tif i > 0 {\n\t\t\ts += \",\"\n\t\t}\n\t\ts += w\n\t}\n\treturn s\n}\n"
            "func main() { fmt.Println(Join([]string{\"a\", \"b\", \"c\"})) }\n```"
        ),
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

// Join concatenates words with commas using a strings.Builder, which grows one
// buffer instead of allocating a new string on every `+=` (quadratic) step.
func Join(words []string) string {
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
	fmt.Println(Join([]string{"a", "b", "c"}))
}
```''',
    },

    # ---------------- go_tester (authored; judged) ---------------------------
    {
        "role": "go_tester",
        "instruction": (
            "Write table-driven Go tests (package rle) for RLE covering the empty "
            "string, a single rune, and runs.\n```go\npackage rle\n// func RLE(s string) string\n```"
        ),
        "response": '''```go
package rle

import "testing"

func TestRLE(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{"", ""},
		{"a", "a1"},
		{"aaabbc", "a3b2c1"},
		{"xxxx", "x4"},
	}
	for _, tt := range tests {
		if got := RLE(tt.in); got != tt.want {
			t.Errorf("RLE(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write a Go test (package people) asserting SortPeople orders by age "
            "then name.\n```go\npackage people\n// type Person struct { Name string; Age int }\n"
            "// func SortPeople(ps []Person)\n```"
        ),
        "response": '''```go
package people

import (
	"reflect"
	"testing"
)

func TestSortPeople(t *testing.T) {
	ps := []Person{{"Bob", 30}, {"Ann", 30}, {"Cy", 25}}
	SortPeople(ps)
	want := []Person{{"Cy", 25}, {"Ann", 30}, {"Bob", 30}}
	if !reflect.DeepEqual(ps, want) {
		t.Errorf("got %v, want %v", ps, want)
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) -------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this for a panic risk:\n```go\nfunc length(v any) int {\n"
            "\treturn len(v.(string))\n}\n```"
        ),
        "response": (
            "**Bug: the unchecked type assertion panics for any non-string input.** "
            "`v.(string)` aborts with `interface conversion: interface {} is int, "
            "not string` the moment a caller passes anything but a string — a "
            "library function should not crash the program on bad input.\n\n"
            "Use the comma-ok form and handle the mismatch:\n\n```go\n"
            "func length(v any) (int, bool) {\n\ts, ok := v.(string)\n\tif !ok {\n"
            "\t\treturn 0, false\n\t}\n\treturn len(s), true\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this error handling:\n```go\nfunc load() error {\n\tf, err := os.Open(\"f\")\n"
            "\tif err != nil {\n\t\treturn err\n\t}\n\tdefer f.Close()\n"
            "\tif data, err := io.ReadAll(f); err == nil {\n\t\tprocess(data)\n\t}\n"
            "\treturn err\n}\n```"
        ),
        "response": (
            "**Bug: the inner `err` shadows the outer one, so a read failure is "
            "swallowed.** The `if data, err := io.ReadAll(f); ...` declares a NEW "
            "`err` scoped to the `if`. When the read fails, `process` is correctly "
            "skipped, but the function then returns the *outer* `err`, which is "
            "still `nil` from the successful `os.Open` — the caller is told "
            "everything succeeded.\n\n"
            "Don't shadow; assign and check the read error explicitly:\n\n```go\n"
            "data, err := io.ReadAll(f)\nif err != nil {\n\treturn err\n}\n"
            "process(data)\nreturn nil\n```\n\n(`go vet -vettool=shadow` flags this "
            "class of bug.)"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this average for correctness:\n```go\nfunc avg(a, b int) int {\n"
            "\treturn (a + b) / 2\n}\n```"
        ),
        "response": (
            "**Two issues.** (1) `a + b` can overflow for large operands (e.g. two "
            "values near `math.MaxInt`), producing a wrong or negative result "
            "before the division. (2) Integer division truncates toward zero, so "
            "`avg(1, 2)` is `1`, not `1.5` — fine if truncation is intended, but it "
            "should be deliberate.\n\n"
            "Compute the midpoint without overflow:\n\n```go\n"
            "func avg(a, b int) int {\n\treturn a + (b-a)/2\n}\n```\n\n"
            "If a fractional mean is wanted, return `float64(a+b) / 2` from a "
            "`float64`-returning function instead."
        ),
    },
]
