# -*- coding: utf-8 -*-
"""Batch 22 of teacher-authored Go SFT examples (Claude Opus 4.8 as teacher).

Focus: stdlib HTTP / backend patterns — http.ServeMux 1.22 method+pattern
routing, middleware, JSON request handling, graceful shutdown — deliberately
teaching the standard library router (no third-party mux) so the specialist
stops reaching for gorilla/mux. go_generator responses are complete,
stdlib-only, compilable programs (compile-verified by teach_build).
"""

EXAMPLES = [
    # ---------------- go_generator (compile-verified) ------------------------
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program that builds an http.ServeMux using Go "
            "1.22 method+pattern routing (GET /items/{id} with r.PathValue), and "
            "exercises it via httptest, printing the status and body. Standard "
            "library only — do not use any third-party router."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
)

// newMux wires routes with the standard library's method+pattern router
// (Go 1.22+), so no third-party mux is needed.
func newMux() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /items/{id}", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "item %s", r.PathValue("id"))
	})
	return mux
}

func main() {
	srv := httptest.NewServer(newMux())
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/items/42")
	if err != nil {
		fmt.Println(err)
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	fmt.Println(resp.StatusCode, string(body))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program demonstrating HTTP middleware: a "
            "func(http.Handler) http.Handler that sets a response header, wrapping "
            "a handler, exercised with httptest. Standard library only."
        ),
        "response": '''```go
package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
)

// withHeader is middleware: it sets a header, then delegates to next.
func withHeader(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-App", "guildlm")
		next.ServeHTTP(w, r)
	})
}

func main() {
	h := withHeader(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	fmt.Println(rec.Code, rec.Header().Get("X-App"))
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a JSON POST handler that decodes "
            "{\"name\":...}, returns 400 with a JSON error on invalid/empty input "
            "and 201 with the echoed name otherwise; exercise both paths via "
            "httptest. Standard library only."
        ),
        "response": '''```go
package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
)

type createReq struct {
	Name string `json:"name"`
}

func create(w http.ResponseWriter, r *http.Request) {
	var req createReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || strings.TrimSpace(req.Name) == "" {
		w.Header().Set("Content-Type", "application/json")
		http.Error(w, `{"error":"invalid"}`, http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(map[string]string{"name": req.Name})
}

func main() {
	for _, body := range []string{`{"name":"x"}`, `{"name":""}`} {
		rec := httptest.NewRecorder()
		create(rec, httptest.NewRequest(http.MethodPost, "/", strings.NewReader(body)))
		fmt.Println(rec.Code)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Write a complete Go program with a Status int enum (Pending, Active, "
            "Closed) that implements fmt.Stringer and a ParseStatus(string) "
            "(Status, bool). Demonstrate both. Standard library only."
        ),
        "response": '''```go
package main

import "fmt"

// Status is a small enum with a String and a parser.
type Status int

const (
	Pending Status = iota
	Active
	Closed
)

func (s Status) String() string {
	switch s {
	case Pending:
		return "pending"
	case Active:
		return "active"
	case Closed:
		return "closed"
	default:
		return "unknown"
	}
}

func ParseStatus(s string) (Status, bool) {
	switch s {
	case "pending":
		return Pending, true
	case "active":
		return Active, true
	case "closed":
		return Closed, true
	}
	return 0, false
}

func main() {
	if st, ok := ParseStatus("active"); ok {
		fmt.Println(st)
	}
}
```''',
    },
    {
        "role": "go_generator",
        "instruction": (
            "Edit this handler so it stops ignoring the JSON decode error: return "
            "400 on a malformed body or empty Name, otherwise echo the name. "
            "Original:\n```go\npackage main\nimport (\n\t\"encoding/json\"\n\t\"fmt\"\n"
            "\t\"net/http\"\n)\nfunc create(w http.ResponseWriter, r *http.Request) {\n"
            "\tvar req struct{ Name string `json:\"name\"` }\n\tjson.NewDecoder(r.Body).Decode(&req)\n"
            "\tfmt.Fprintln(w, req.Name)\n}\nfunc main() {}\n```"
        ),
        "response": '''```go
package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
)

func create(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Name string `json:"name"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || strings.TrimSpace(req.Name) == "" {
		http.Error(w, "invalid request", http.StatusBadRequest)
		return
	}
	_, _ = w.Write([]byte(req.Name))
}

func main() {
	// Exercise both paths so the program is self-contained.
	for _, b := range []string{`{"name":"x"}`, `not json`} {
		create(httptest.NewRecorder(), httptest.NewRequest(http.MethodPost, "/", strings.NewReader(b)))
	}
}
```''',
    },

    # ---------------- go_tester (authored; judged) ---------------------------
    {
        "role": "go_tester",
        "instruction": (
            "Write httptest-based Go tests (package api) for the create handler, "
            "asserting 201 for a valid body and 400 for an empty name.\n```go\n"
            "package api\n// func create(w http.ResponseWriter, r *http.Request)\n```"
        ),
        "response": '''```go
package api

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestCreate(t *testing.T) {
	tests := []struct {
		name, body string
		wantCode   int
	}{
		{"valid", `{"name":"x"}`, http.StatusCreated},
		{"empty name", `{"name":""}`, http.StatusBadRequest},
		{"malformed", `{`, http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := httptest.NewRecorder()
			req := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(tt.body))
			create(rec, req)
			if rec.Code != tt.wantCode {
				t.Errorf("code = %d, want %d", rec.Code, tt.wantCode)
			}
		})
	}
}
```''',
    },
    {
        "role": "go_tester",
        "instruction": (
            "Write Go tests (package statuskit) for ParseStatus and the Stringer: "
            "a round-trip for each valid value and a false for an unknown "
            "string.\n```go\npackage statuskit\n// type Status int; func (Status) String() string\n"
            "// func ParseStatus(string) (Status, bool)\n```"
        ),
        "response": '''```go
package statuskit

import "testing"

func TestParseStatusRoundTrip(t *testing.T) {
	for _, name := range []string{"pending", "active", "closed"} {
		st, ok := ParseStatus(name)
		if !ok {
			t.Fatalf("ParseStatus(%q) ok=false", name)
		}
		if st.String() != name {
			t.Errorf("String() = %q, want %q", st.String(), name)
		}
	}
	if _, ok := ParseStatus("bogus"); ok {
		t.Error("ParseStatus(bogus) should be false")
	}
}
```''',
    },

    # ---------------- go_reviewer (authored; judged) -------------------------
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this HTTP client code for a leak:\n```go\nfunc fetch(url string) (int, error) {\n"
            "\tresp, err := http.Get(url)\n\tif err != nil {\n\t\treturn 0, err\n\t}\n"
            "\treturn resp.StatusCode, nil\n}\n```"
        ),
        "response": (
            "**Bug: the response body is never closed, leaking connections.** "
            "`http.Get` returns a `resp` whose `Body` must always be closed, even "
            "if you only read the status code — otherwise the underlying TCP "
            "connection can't be reused or released, and under load the process "
            "exhausts file descriptors / sockets.\n\n"
            "Close it with `defer`, right after the error check:\n\n```go\n"
            "func fetch(url string) (int, error) {\n\tresp, err := http.Get(url)\n"
            "\tif err != nil {\n\t\treturn 0, err\n\t}\n\tdefer resp.Body.Close()\n"
            "\treturn resp.StatusCode, nil\n}\n```\n\nIf you don't need the body, "
            "still drain it (`io.Copy(io.Discard, resp.Body)`) before closing to "
            "let keep-alive reuse the connection."
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this handler's status-code handling:\n```go\nfunc h(w http.ResponseWriter, r *http.Request) {\n"
            "\tw.Write([]byte(\"created\"))\n\tw.WriteHeader(http.StatusCreated)\n}\n```"
        ),
        "response": (
            "**Bug: `WriteHeader` is called after `Write`, so it has no effect "
            "and Go logs `http: superfluous response.WriteHeader call`.** The "
            "first `Write` implicitly sends a `200 OK` header; the later "
            "`WriteHeader(201)` is ignored, so the client always sees 200, not the "
            "intended 201.\n\n"
            "Set the status code *before* writing the body:\n\n```go\n"
            "func h(w http.ResponseWriter, r *http.Request) {\n"
            "\tw.WriteHeader(http.StatusCreated)\n\t_, _ = w.Write([]byte(\"created\"))\n}\n```"
        ),
    },
    {
        "role": "go_reviewer",
        "instruction": (
            "Review this JSON decoding for a robustness issue in an HTTP server:\n"
            "```go\nfunc handler(w http.ResponseWriter, r *http.Request) {\n"
            "\tbody, _ := io.ReadAll(r.Body)\n\tvar v map[string]any\n"
            "\tjson.Unmarshal(body, &v)\n\tprocess(v)\n}\n```"
        ),
        "response": (
            "**Several real problems.** (1) Both errors are ignored: a read "
            "failure or malformed JSON silently yields a nil/partial map that "
            "`process` then operates on. (2) `io.ReadAll(r.Body)` is unbounded — a "
            "malicious client can stream gigabytes and OOM the server. (3) Unknown "
            "fields pass silently.\n\n"
            "Bound the body and decode with error handling:\n\n```go\n"
            "func handler(w http.ResponseWriter, r *http.Request) {\n"
            "\tr.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MiB cap\n"
            "\tdec := json.NewDecoder(r.Body)\n\tdec.DisallowUnknownFields()\n"
            "\tvar v map[string]any\n\tif err := dec.Decode(&v); err != nil {\n"
            "\t\thttp.Error(w, \"bad request\", http.StatusBadRequest)\n\t\treturn\n\t}\n"
            "\tprocess(v)\n}\n```"
        ),
    },
]
