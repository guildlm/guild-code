# -*- coding: utf-8 -*-
"""Batch 25 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Idiomatic Go API patterns (functional options, small state machine),
constructor-validation edits, and more reviewer pitfalls. go_generator responses
are complete, stdlib-only, compilable programs (compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program demonstrating the functional options "
            "pattern: a Server configured by WithPort and WithTLS options through "
            "NewServer(opts ...Option). Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

type Server struct {
	port int
	tls  bool
}

// Option configures a Server; this is the functional options pattern.
type Option func(*Server)

func WithPort(p int) Option { return func(s *Server) { s.port = p } }
func WithTLS() Option       { return func(s *Server) { s.tls = true } }

// NewServer applies sensible defaults, then each option in order.
func NewServer(opts ...Option) *Server {
	s := &Server{port: 8080}
	for _, opt := range opts {
		opt(s)
	}
	return s
}

func main() {
	s := NewServer(WithPort(9090), WithTLS())
	fmt.Println(s.port, s.tls)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a small state machine: a State enum "
            "(Idle, Running, Done) and next(State) (State, bool) returning the next "
            "state and whether the transition was valid. Drive it from Idle to Done. "
            "Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

type State int

const (
	Idle State = iota
	Running
	Done
)

// next advances the state machine; ok is false when there is no transition.
func next(s State) (State, bool) {
	switch s {
	case Idle:
		return Running, true
	case Running:
		return Done, true
	default:
		return s, false
	}
}

func main() {
	s := Idle
	for {
		ns, ok := next(s)
		if !ok {
			break
		}
		s = ns
	}
	fmt.Println("final state:", s)
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this constructor to validate its input: return an error wrapping "
            "ErrInvalidUser when the name is blank or age is outside 0..150. "
            "Original:\n```go\npackage main\nimport \"fmt\"\ntype User struct {\n"
            "\tName string\n\tAge  int\n}\nfunc NewUser(name string, age int) *User {\n"
            "\treturn &User{name, age}\n}\nfunc main() { fmt.Println(NewUser(\"a\", 30)) }\n```"
        ),
        "response": '''```go
package main

import (
	"errors"
	"fmt"
	"strings"
)

type User struct {
	Name string
	Age  int
}

// ErrInvalidUser is returned when NewUser is given invalid input.
var ErrInvalidUser = errors.New("invalid user")

// NewUser validates its arguments before constructing the User.
func NewUser(name string, age int) (*User, error) {
	if strings.TrimSpace(name) == "" || age < 0 || age > 150 {
		return nil, fmt.Errorf("name=%q age=%d: %w", name, age, ErrInvalidUser)
	}
	return &User{Name: name, Age: age}, nil
}

func main() {
	if u, err := NewUser("a", 30); err == nil {
		fmt.Println(u)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with Clamp[T int | float64](v, lo, hi T) T "
            "that constrains v to the [lo, hi] range. Demonstrate it. Standard "
            "library only."
        ),
        "response": '''```go
package main

import "fmt"

// Clamp constrains v to the inclusive range [lo, hi].
func Clamp[T int | float64](v, lo, hi T) T {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func main() {
	fmt.Println(Clamp(12, 0, 10), Clamp(-3, 0, 10), Clamp(5, 0, 10))
}
```''',
    },

    # ---------------- go_tester (authored; judged) ---------------------------
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package srv) for the functional options NewServer: "
            "defaults when no options are passed, and the values set by WithPort "
            "and WithTLS.\n```go\npackage srv\n// func NewServer(opts ...Option) *Server\n"
            "// func WithPort(int) Option; func WithTLS() Option\n```"
        ),
        "response": '''```go
package srv

import "testing"

func TestNewServerDefaults(t *testing.T) {
	s := NewServer()
	if s.port != 8080 || s.tls {
		t.Errorf("defaults = {port:%d tls:%v}, want {8080 false}", s.port, s.tls)
	}
}

func TestNewServerOptions(t *testing.T) {
	s := NewServer(WithPort(9090), WithTLS())
	if s.port != 9090 || !s.tls {
		t.Errorf("configured = {port:%d tls:%v}, want {9090 true}", s.port, s.tls)
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package users) for NewUser: a valid user, and that "
            "blank name or out-of-range age wraps ErrInvalidUser (errors.Is).\n"
            "```go\npackage users\n// var ErrInvalidUser = errors.New(...)\n"
            "// func NewUser(name string, age int) (*User, error)\n```"
        ),
        "response": '''```go
package users

import (
	"errors"
	"testing"
)

func TestNewUserValid(t *testing.T) {
	u, err := NewUser("ann", 30)
	if err != nil || u == nil || u.Name != "ann" {
		t.Fatalf("got %v, %v", u, err)
	}
}

func TestNewUserInvalid(t *testing.T) {
	cases := []struct {
		name string
		age  int
	}{
		{"", 30}, {"  ", 30}, {"ann", -1}, {"ann", 200},
	}
	for _, c := range cases {
		if _, err := NewUser(c.name, c.age); !errors.Is(err, ErrInvalidUser) {
			t.Errorf("NewUser(%q,%d) err=%v, want ErrInvalidUser", c.name, c.age, err)
		}
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) -------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this comparison of computed values:\n```go\nfunc equal(a, b float64) bool {\n"
            "\treturn a == b\n}\n// used as: equal(0.1+0.2, 0.3)\n```"
        ),
        "response": (
            "**Bug: exact `==` on floats fails for computed values due to rounding.** "
            "`0.1 + 0.2` is `0.30000000000000004` in IEEE-754, so `equal(0.1+0.2, "
            "0.3)` returns false even though the values are mathematically equal. "
            "Direct float equality is only safe for values you know are bit-identical.\n\n"
            "Compare within a tolerance (epsilon):\n\n```go\nimport \"math\"\n\n"
            "func equal(a, b float64) bool {\n\tconst eps = 1e-9\n\treturn math.Abs(a-b) <= eps\n}\n```\n\n"
            "For values of very different magnitudes, scale the epsilon relative to "
            "the operands."
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this parser:\n```go\nfunc toInt(s string) int {\n"
            "\tn, _ := strconv.Atoi(s)\n\treturn n\n}\n```"
        ),
        "response": (
            "**Bug: the `strconv.Atoi` error is discarded, so invalid input silently "
            "becomes 0.** A caller can't distinguish `toInt(\"0\")` from "
            "`toInt(\"garbage\")` — both return 0 — which hides malformed data and "
            "leads to wrong downstream logic.\n\n"
            "Propagate the error so the caller decides:\n\n```go\n"
            "func toInt(s string) (int, error) {\n\tn, err := strconv.Atoi(s)\n"
            "\tif err != nil {\n\t\treturn 0, fmt.Errorf(\"toInt(%q): %w\", s, err)\n\t}\n"
            "\treturn n, nil\n}\n```\n\nIf a default truly is acceptable, make it "
            "explicit (e.g. a `toIntOr(s string, def int) int`) so the intent is clear."
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this HTTP handler's use of context:\n```go\nfunc handler(w http.ResponseWriter, r *http.Request) {\n"
            "\trows, err := db.QueryContext(context.Background(), \"SELECT ...\")\n\t_ = rows\n\t_ = err\n}\n```"
        ),
        "response": (
            "**Bug: it ignores the request's context, breaking cancellation and "
            "timeouts.** Using `context.Background()` instead of `r.Context()` means "
            "the database query keeps running even after the client disconnects or "
            "the request deadline passes — wasting a connection and DB work, and "
            "defeating any server timeout. It also drops request-scoped values "
            "(trace IDs, deadlines).\n\n"
            "Pass the request context so the query is cancelled with the request:\n\n```go\n"
            "func handler(w http.ResponseWriter, r *http.Request) {\n"
            "\trows, err := db.QueryContext(r.Context(), \"SELECT ...\")\n"
            "\t// ... handle rows, err\n}\n```"
        ),
    },
]
