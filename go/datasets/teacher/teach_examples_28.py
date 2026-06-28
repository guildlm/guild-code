# -*- coding: utf-8 -*-
"""Batch 28 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Weighted to the thinner go_tester and go_reviewer roles (the next specialists to
train). go_generator responses are complete, stdlib-only, compilable programs
(compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a generic Reduce[T, U any](s []T, "
            "init U, f func(U, T) U) U that folds s into a single value. "
            "Demonstrate summing ints. Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// Reduce folds s left-to-right starting from init.
func Reduce[T, U any](s []T, init U, f func(U, T) U) U {
	acc := init
	for _, v := range s {
		acc = f(acc, v)
	}
	return acc
}

func main() {
	sum := Reduce([]int{1, 2, 3, 4}, 0, func(a, b int) int { return a + b })
	fmt.Println(sum)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a FIFO Queue of ints (Enqueue, "
            "Dequeue returning (int, bool), Len). Demonstrate it. Standard library "
            "only."
        ),
        "response": '''```go
package main

import "fmt"

// Queue is a simple FIFO queue.
type Queue struct{ items []int }

func (q *Queue) Enqueue(v int) { q.items = append(q.items, v) }

func (q *Queue) Dequeue() (int, bool) {
	if len(q.items) == 0 {
		return 0, false
	}
	v := q.items[0]
	q.items = q.items[1:]
	return v, true
}

func (q *Queue) Len() int { return len(q.items) }

func main() {
	var q Queue
	q.Enqueue(1)
	q.Enqueue(2)
	v, _ := q.Dequeue()
	fmt.Println(v, q.Len())
}
```''',
    },

    # ---------------- go_tester (authored; judged) ---------------------------
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package queue) for the FIFO Queue: order is preserved "
            "and Dequeue on empty returns false.\n```go\npackage queue\n"
            "// func (*Queue) Enqueue(int); func (*Queue) Dequeue() (int, bool); func (*Queue) Len() int\n```"
        ),
        "response": '''```go
package queue

import "testing"

func TestQueueFIFO(t *testing.T) {
	var q Queue
	for _, v := range []int{1, 2, 3} {
		q.Enqueue(v)
	}
	for _, want := range []int{1, 2, 3} {
		got, ok := q.Dequeue()
		if !ok || got != want {
			t.Fatalf("Dequeue = %d,%v want %d,true", got, ok, want)
		}
	}
	if _, ok := q.Dequeue(); ok {
		t.Error("empty Dequeue should be false")
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package reducekit) for the generic Reduce: sum and "
            "max via fold, and that init is returned for an empty slice.\n```go\n"
            "package reducekit\n// func Reduce[T, U any](s []T, init U, f func(U, T) U) U\n```"
        ),
        "response": '''```go
package reducekit

import "testing"

func TestReduceSum(t *testing.T) {
	if got := Reduce([]int{1, 2, 3}, 0, func(a, b int) int { return a + b }); got != 6 {
		t.Errorf("sum = %d, want 6", got)
	}
}

func TestReduceEmptyReturnsInit(t *testing.T) {
	if got := Reduce([]int(nil), 42, func(a, b int) int { return a + b }); got != 42 {
		t.Errorf("empty = %d, want 42", got)
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package validate) for ValidateEmail using subtests "
            "for a valid address and several invalid ones.\n```go\npackage validate\n"
            "// func ValidateEmail(s string) error\n```"
        ),
        "response": '''```go
package validate

import "testing"

func TestValidateEmail(t *testing.T) {
	valid := []string{"a@b.co", "user.name@example.com"}
	for _, e := range valid {
		t.Run("valid/"+e, func(t *testing.T) {
			if err := ValidateEmail(e); err != nil {
				t.Errorf("ValidateEmail(%q) = %v, want nil", e, err)
			}
		})
	}
	invalid := []string{"", "no-at", "a@", "@b.co", "a@b"}
	for _, e := range invalid {
		t.Run("invalid/"+e, func(t *testing.T) {
			if err := ValidateEmail(e); err == nil {
				t.Errorf("ValidateEmail(%q) = nil, want error", e)
			}
		})
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) -------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this for a surprising side effect:\n```go\nfunc appendID(ids []int, id int) []int {\n"
            "\treturn append(ids, id)\n}\nfunc main() {\n\tbase := make([]int, 3, 10)\n"
            "\ta := appendID(base, 1)\n\tb := appendID(base, 2)\n\tfmt.Println(a[3], b[3])\n}\n```"
        ),
        "response": (
            "**Bug: `a` and `b` alias the same backing array, so `b`'s append "
            "overwrites `a`'s.** `base` has length 3 but capacity 10, so both "
            "`append` calls write index 3 of the *same* array instead of "
            "allocating — `a[3]` and `b[3]` are both `2`. This is the shared-"
            "capacity aliasing trap.\n\n"
            "Force a fresh allocation with a three-index slice that caps the length:\n\n"
            "```go\nfunc appendID(ids []int, id int) []int {\n"
            "\treturn append(ids[:len(ids):len(ids)], id)\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this type switch:\n```go\nfunc describe(v any) string {\n"
            "\tswitch x := v.(type) {\n\tcase int:\n\t\treturn fmt.Sprintf(\"int %d\", x)\n"
            "\tcase string:\n\t\treturn fmt.Sprintf(\"string %q\", x)\n\t}\n\treturn \"\"\n}\n```"
        ),
        "response": (
            "**Issue: the default case silently returns an empty string, hiding "
            "unhandled types.** Any input that isn't an int or string (a float, a "
            "struct, nil) produces `\"\"`, which a caller can't distinguish from a "
            "genuinely empty result — bugs in the caller go unnoticed.\n\n"
            "Add an explicit default that reports the unhandled type:\n\n```go\n"
            "func describe(v any) string {\n\tswitch x := v.(type) {\n\tcase int:\n"
            "\t\treturn fmt.Sprintf(\"int %d\", x)\n\tcase string:\n"
            "\t\treturn fmt.Sprintf(\"string %q\", x)\n\tdefault:\n"
            "\t\treturn fmt.Sprintf(\"unhandled %T\", v)\n\t}\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this producer/consumer:\n```go\nfunc produce(ch chan int, done chan struct{}) {\n"
            "\tfor i := 0; i < 5; i++ {\n\t\tch <- i\n\t}\n\tclose(ch)\n}\nfunc main() {\n"
            "\tch := make(chan int)\n\tdone := make(chan struct{})\n\tgo produce(ch, done)\n"
            "\tgo produce(ch, done)\n\tfor v := range ch {\n\t\tfmt.Println(v)\n\t}\n}\n```"
        ),
        "response": (
            "**Bug: two goroutines close the same channel, so the second `close(ch)` "
            "panics with `close of closed channel`.** Both `produce` calls run to "
            "completion and each tries to `close(ch)`; whichever runs second crashes "
            "the program. A channel must be closed exactly once, by a single owner.\n\n"
            "Have the producers only send, and let one coordinator close after both "
            "finish:\n\n```go\nvar wg sync.WaitGroup\nwg.Add(2)\nproduce := func() {\n"
            "\tdefer wg.Done()\n\tfor i := 0; i < 5; i++ {\n\t\tch <- i\n\t}\n}\n"
            "go produce()\ngo produce()\ngo func() { wg.Wait(); close(ch) }()\n```"
        ),
    },
]
