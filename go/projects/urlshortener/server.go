package main

import (
	"encoding/json"
	"net/http"
	"net/url"
	"strings"
)

// shortenRequest is the JSON body accepted by POST /shorten.
type shortenRequest struct {
	URL string `json:"url"`
}

// shortenResponse is the JSON body returned by POST /shorten.
type shortenResponse struct {
	Code string `json:"code"`
}

// errorResponse is the JSON body returned for any error.
type errorResponse struct {
	Error string `json:"error"`
}

// Server wires HTTP handlers to a Store.
type Server struct {
	store *Store
}

// NewServer returns a Server backed by the given Store.
func NewServer(store *Store) *Server {
	return &Server{store: store}
}

// Handler returns the http.Handler exposing the shortener routes.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /shorten", s.handleShorten)
	mux.HandleFunc("GET /{code}", s.handleRedirect)
	return mux
}

func (s *Server) handleShorten(w http.ResponseWriter, r *http.Request) {
	var req shortenRequest
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}

	target := strings.TrimSpace(req.URL)
	if !validURL(target) {
		writeError(w, http.StatusBadRequest, "url must be an absolute http(s) URL")
		return
	}

	code, err := s.store.Put(target)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "could not store url")
		return
	}

	writeJSON(w, http.StatusCreated, shortenResponse{Code: code})
}

func (s *Server) handleRedirect(w http.ResponseWriter, r *http.Request) {
	code := r.PathValue("code")
	target, err := s.store.Get(code)
	if err != nil {
		writeError(w, http.StatusNotFound, "unknown code")
		return
	}
	http.Redirect(w, r, target, http.StatusFound)
}

// validURL reports whether raw is an absolute http or https URL with a host.
func validURL(raw string) bool {
	if raw == "" {
		return false
	}
	u, err := url.Parse(raw)
	if err != nil {
		return false
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return false
	}
	return u.Host != ""
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}
