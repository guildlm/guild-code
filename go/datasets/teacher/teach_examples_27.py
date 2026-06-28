# -*- coding: utf-8 -*-
"""Batch 27 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Targeted at the base model's measured weak spots on go_dev_bench — rune-safe
string handling, generics with ordered/comparable constraints, and JSON struct
tags — taught through DIFFERENT functions than the benchmark (no teaching to the
test). go_generator responses are complete, stdlib-only, compilable programs
(compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator — rune-safe string handling ---------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with ReverseWords(s string) string that "
            "reverses the order of whitespace-separated words (not the characters). "
            "Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"strings"
)

// ReverseWords reverses the order of words, leaving each word intact.
func ReverseWords(s string) string {
	w := strings.Fields(s)
	for i, j := 0, len(w)-1; i < j; i, j = i+1, j-1 {
		w[i], w[j] = w[j], w[i]
	}
	return strings.Join(w, " ")
}

func main() {
	fmt.Println(ReverseWords("the quick brown fox"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this program: IsMirror reverses by bytes, so multi-byte runes "
            "break it. Make it compare rune-by-rune. Original:\n```go\npackage main\n"
            "import \"fmt\"\nfunc IsMirror(s string) bool {\n\tb := []byte(s)\n"
            "\tfor i, j := 0, len(b)-1; i < j; i, j = i+1, j-1 {\n\t\tif b[i] != b[j] {\n"
            "\t\t\treturn false\n\t\t}\n\t}\n\treturn true\n}\nfunc main() { fmt.Println(IsMirror(\"abccba\")) }\n```"
        ),
        "response": '''```go
package main

import "fmt"

// IsMirror reports whether s reads the same forwards and backwards by RUNE, so
// multi-byte characters are compared as whole code points, not bytes.
func IsMirror(s string) bool {
	r := []rune(s)
	for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
		if r[i] != r[j] {
			return false
		}
	}
	return true
}

func main() {
	fmt.Println(IsMirror("abccba"), IsMirror("世界界世"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with RuneLen(s string) int returning the "
            "number of Unicode code points (not bytes) in s, and demonstrate the "
            "difference on a multi-byte string. Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"unicode/utf8"
)

// RuneLen counts code points; len(s) would count bytes instead.
func RuneLen(s string) int {
	return utf8.RuneCountInString(s)
}

func main() {
	s := "héllo 世界"
	fmt.Println("runes:", RuneLen(s), "bytes:", len(s))
}
```''',
    },

    # ---------------- go_generator — generics (ordered / comparable) ---------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic Min[T cmp.Ordered](xs ...T) "
            "(T, bool) returning the minimum and false when empty. Demonstrate it. "
            "Standard library only."
        ),
        "response": '''```go
package main

import (
	"cmp"
	"fmt"
)

// Min returns the smallest of xs; ok is false when xs is empty.
func Min[T cmp.Ordered](xs ...T) (T, bool) {
	var m T
	if len(xs) == 0 {
		return m, false
	}
	m = xs[0]
	for _, v := range xs[1:] {
		if v < m {
			m = v
		}
	}
	return m, true
}

func main() {
	fmt.Println(Min(3, 1, 2))
	fmt.Println(Min[int]())
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic Contains[T comparable](s "
            "[]T, target T) bool. Demonstrate with strings. Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// Contains reports whether target is present in s.
func Contains[T comparable](s []T, target T) bool {
	for _, v := range s {
		if v == target {
			return true
		}
	}
	return false
}

func main() {
	fmt.Println(Contains([]string{"a", "b", "c"}, "b"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic MaxBy[T any](s []T, key "
            "func(T) int) (T, bool) returning the element with the largest key. "
            "Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// MaxBy returns the element of s whose key is largest; ok is false when empty.
func MaxBy[T any](s []T, key func(T) int) (T, bool) {
	var best T
	if len(s) == 0 {
		return best, false
	}
	best = s[0]
	bk := key(best)
	for _, v := range s[1:] {
		if k := key(v); k > bk {
			best, bk = v, k
		}
	}
	return best, true
}

func main() {
	words := []string{"a", "ccc", "bb"}
	longest, _ := MaxBy(words, func(w string) int { return len(w) })
	fmt.Println(longest)
}
```''',
    },

    # ---------------- go_generator — JSON struct tags / (un)marshal ----------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program defining a Config struct with json tags "
            "(host string `host`, port int `port`, tls bool `tls,omitempty`) and "
            "marshal a value, printing compact JSON. Standard library only."
        ),
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
)

// Config marshals with explicit json field names; tls is omitted when false.
type Config struct {
	Host string `json:"host"`
	Port int    `json:"port"`
	TLS  bool   `json:"tls,omitempty"`
}

func main() {
	b, err := json.Marshal(Config{Host: "localhost", Port: 8080})
	if err != nil {
		fmt.Println(err)
		return
	}
	fmt.Println(string(b))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program that unmarshals a JSON object string into "
            "a struct with json tags and prints a field, handling the decode error. "
            "Standard library only."
        ),
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
)

type User struct {
	Name  string `json:"name"`
	Admin bool   `json:"admin"`
}

func main() {
	var u User
	if err := json.Unmarshal([]byte(`{"name":"ana","admin":true}`), &u); err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(u.Name, u.Admin)
}
```''',
    },

    # ---------------- go_tester --------------------------------------------- #
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package minkit) for the generic Min: the minimum of a "
            "few ints and false for empty.\n```go\npackage minkit\n"
            "// func Min[T cmp.Ordered](xs ...T) (T, bool)\n```"
        ),
        "response": '''```go
package minkit

import "testing"

func TestMin(t *testing.T) {
	if m, ok := Min(3, 1, 2); !ok || m != 1 {
		t.Errorf("Min(3,1,2) = %d,%v want 1,true", m, ok)
	}
	if _, ok := Min[int](); ok {
		t.Error("empty Min should be false")
	}
}
```''',
    },

    # ---------------- go_reviewer ------------------------------------------- #
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this for a Unicode bug:\n```go\nfunc firstChar(s string) string {\n"
            "\treturn string(s[0])\n}\n```"
        ),
        "response": (
            "**Bug: `s[0]` indexes a BYTE, not a rune, so it mangles multi-byte "
            "characters.** For `firstChar(\"héllo\")` the first character is fine, "
            "but for `firstChar(\"世界\")` `s[0]` is just the first byte of a 3-byte "
            "rune, and `string(s[0])` produces the replacement character `ï¿½`, not "
            "`世`. Indexing a string always yields bytes.\n\n"
            "Decode the first rune instead:\n\n```go\nimport \"unicode/utf8\"\n\n"
            "func firstChar(s string) string {\n\tr, _ := utf8.DecodeRuneInString(s)\n"
            "\tif r == utf8.RuneError {\n\t\treturn \"\"\n\t}\n\treturn string(r)\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review why this JSON comes out empty:\n```go\ntype point struct {\n"
            "\tx int\n\ty int\n}\nfunc main() {\n\tb, _ := json.Marshal(point{1, 2})\n"
            "\tfmt.Println(string(b)) // prints {}\n}\n```"
        ),
        "response": (
            "**Bug: the struct fields are unexported (lowercase), so encoding/json "
            "can't see them and marshals `{}`.** `json.Marshal` uses reflection and "
            "only serializes EXPORTED (capitalized) fields; `x` and `y` are package-"
            "private, so they're skipped entirely.\n\n"
            "Export the fields and tag them for the wire name you want:\n\n```go\n"
            "type point struct {\n\tX int `json:\"x\"`\n\tY int `json:\"y\"`\n}\n```\n\n"
            "Now `json.Marshal(point{1, 2})` yields `{\"x\":1,\"y\":2}`."
        ),
    },
]
