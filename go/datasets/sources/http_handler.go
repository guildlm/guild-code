// Package httpapi contains a small, self-contained HTTP handler example.
//
// It exposes a /health endpoint and a /greet endpoint that echoes a name from
// the query string, demonstrating idiomatic request handling, status codes and
// JSON encoding with the standard library only.
package httpapi

import (
	"encoding/json"
	"net/http"
)

// greeting is the JSON payload returned by the /greet endpoint.
type greeting struct {
	Message string `json:"message"`
}

// NewMux wires the handlers onto a fresh ServeMux and returns it.
func NewMux() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", handleHealth)
	mux.HandleFunc("/greet", handleGreet)
	return mux
}

// handleHealth always reports the service is up.
func handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}

// handleGreet greets the caller, defaulting to "world" when no name is given.
func handleGreet(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	name := r.URL.Query().Get("name")
	if name == "" {
		name = "world"
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(greeting{Message: "hello, " + name})
}
