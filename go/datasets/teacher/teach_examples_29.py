# -*- coding: utf-8 -*-
"""Batch 29 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Heavily weighted to go_tester — the ONE role where targeted SFT measurably beats
the base (go_test_bench: 8/13 vs 6/13). These examples drill the discipline that
catches bugs: cover boundaries, empties, error paths, and edge cases, not just
the happy path. go_generator responses are complete, stdlib-only, compilable
programs (compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with Clamp(v, lo, hi int) int constraining "
            "v to [lo, hi]. Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// Clamp constrains v to the inclusive range [lo, hi].
func Clamp(v, lo, hi int) int {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func main() {
	fmt.Println(Clamp(12, 0, 10), Clamp(-1, 0, 10), Clamp(5, 0, 10))
}
```''',
    },

    # ---------------- go_tester — thorough, edge-covering tests --------------
    {
        "role": "go_tester",
        "instruction": (
            "Write thorough Go tests (package mathx) for Clamp(v, lo, hi int) int. "
            "Cover the boundaries precisely.\n```go\npackage mathx\n// func Clamp(v, lo, hi int) int\n```"
        ),
        "response": '''```go
package mathx

import "testing"

func TestClamp(t *testing.T) {
	tests := []struct {
		name          string
		v, lo, hi, want int
	}{
		{"below range", -5, 0, 10, 0},
		{"above range", 99, 0, 10, 10},
		{"in range", 5, 0, 10, 5},
		{"equals lo (boundary)", 0, 0, 10, 0},
		{"equals hi (boundary)", 10, 0, 10, 10},
		{"lo == hi", 7, 3, 3, 3},
		{"negative range", -7, -10, -1, -7},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Clamp(tt.v, tt.lo, tt.hi); got != tt.want {
				t.Errorf("Clamp(%d,%d,%d) = %d, want %d", tt.v, tt.lo, tt.hi, got, tt.want)
			}
		})
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write thorough Go tests (package strkit) for Reverse(s string) string "
            "(rune-safe). Cover empty, single, ASCII, multi-byte, and the "
            "reverse-twice identity.\n```go\npackage strkit\n// func Reverse(s string) string\n```"
        ),
        "response": '''```go
package strkit

import "testing"

func TestReverse(t *testing.T) {
	cases := map[string]string{
		"":       "",
		"a":      "a",
		"abc":    "cba",
		"héllo":  "olléh",
		"世界":     "界世",
		"ab世":    "世ba",
	}
	for in, want := range cases {
		if got := Reverse(in); got != want {
			t.Errorf("Reverse(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestReverseTwiceIsIdentity(t *testing.T) {
	for _, s := range []string{"", "x", "héllo 世界", "12345"} {
		if got := Reverse(Reverse(s)); got != s {
			t.Errorf("Reverse(Reverse(%q)) = %q", s, got)
		}
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write thorough Go tests (package sortx) for IsSorted(xs []int) bool "
            "(non-decreasing). Cover empty, single, sorted, unsorted, and equal "
            "elements.\n```go\npackage sortx\n// func IsSorted(xs []int) bool\n```"
        ),
        "response": '''```go
package sortx

import "testing"

func TestIsSorted(t *testing.T) {
	tests := []struct {
		name string
		xs   []int
		want bool
	}{
		{"empty", nil, true},
		{"single", []int{5}, true},
		{"sorted", []int{1, 2, 3, 4}, true},
		{"equal elements", []int{2, 2, 2}, true},
		{"descending", []int{3, 2, 1}, false},
		{"one dip", []int{1, 2, 1, 3}, false},
		{"last out of order", []int{1, 2, 3, 0}, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := IsSorted(tt.xs); got != tt.want {
				t.Errorf("IsSorted(%v) = %v, want %v", tt.xs, got, tt.want)
			}
		})
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write thorough Go tests (package vowels) for CountVowels(s string) int "
            "(ASCII vowels, case-insensitive). Cover none, all, mixed case, empty, "
            "and that non-vowels including unicode are excluded.\n```go\npackage vowels\n"
            "// func CountVowels(s string) int\n```"
        ),
        "response": '''```go
package vowels

import "testing"

func TestCountVowels(t *testing.T) {
	tests := []struct {
		in   string
		want int
	}{
		{"", 0},
		{"xyz", 0},
		{"aeiou", 5},
		{"AEIOU", 5},
		{"Hello World", 3},
		{"rhythm", 0},
		{"héllo", 1}, // é is not an ASCII vowel, so only the 'o' counts
	}
	for _, tt := range tests {
		if got := CountVowels(tt.in); got != tt.want {
			t.Errorf("CountVowels(%q) = %d, want %d", tt.in, got, tt.want)
		}
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write thorough Go tests (package divkit) for Divide(a, b int) (int, error) "
            "which returns ErrDivByZero on b==0. Cover exact division, truncation, "
            "negatives, and the error path with errors.Is.\n```go\npackage divkit\n"
            "// var ErrDivByZero = errors.New(...)\n// func Divide(a, b int) (int, error)\n```"
        ),
        "response": '''```go
package divkit

import (
	"errors"
	"testing"
)

func TestDivide(t *testing.T) {
	ok := []struct {
		a, b, want int
	}{
		{6, 3, 2},
		{7, 2, 3},   // truncates toward zero
		{-6, 3, -2},
		{0, 5, 0},
	}
	for _, c := range ok {
		got, err := Divide(c.a, c.b)
		if err != nil || got != c.want {
			t.Errorf("Divide(%d,%d) = %d,%v want %d,nil", c.a, c.b, got, err, c.want)
		}
	}
	if _, err := Divide(1, 0); !errors.Is(err, ErrDivByZero) {
		t.Error("Divide by zero should wrap ErrDivByZero")
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write thorough Go tests (package stack) for a generic Stack[int] "
            "(Push, Pop returning (int, bool), Len). Cover LIFO order, pop-empty, "
            "and length tracking.\n```go\npackage stack\n// type Stack[T any]; Push, Pop() (T, bool), Len() int\n```"
        ),
        "response": '''```go
package stack

import "testing"

func TestStackLIFO(t *testing.T) {
	var s Stack[int]
	if _, ok := s.Pop(); ok {
		t.Fatal("Pop on empty should be false")
	}
	if s.Len() != 0 {
		t.Fatalf("empty len = %d", s.Len())
	}
	for _, v := range []int{1, 2, 3} {
		s.Push(v)
	}
	if s.Len() != 3 {
		t.Fatalf("len after pushes = %d", s.Len())
	}
	for _, want := range []int{3, 2, 1} { // LIFO
		got, ok := s.Pop()
		if !ok || got != want {
			t.Fatalf("Pop = %d,%v want %d,true", got, ok, want)
		}
	}
	if _, ok := s.Pop(); ok {
		t.Fatal("Pop after draining should be false")
	}
}
```''',
    },
]
