package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer() http.Handler {
	return NewServer(NewStore(6)).Handler()
}

func TestShorten(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantCode   bool
	}{
		{
			name:       "valid http url",
			body:       `{"url":"http://example.com/page"}`,
			wantStatus: http.StatusCreated,
			wantCode:   true,
		},
		{
			name:       "valid https url",
			body:       `{"url":"https://example.com"}`,
			wantStatus: http.StatusCreated,
			wantCode:   true,
		},
		{
			name:       "empty url",
			body:       `{"url":""}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "whitespace url",
			body:       `{"url":"   "}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "missing scheme",
			body:       `{"url":"example.com"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "unsupported scheme",
			body:       `{"url":"ftp://example.com"}`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "malformed json",
			body:       `{"url":`,
			wantStatus: http.StatusBadRequest,
		},
		{
			name:       "unknown field",
			body:       `{"link":"http://example.com"}`,
			wantStatus: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestServer()
			req := httptest.NewRequest(http.MethodPost, "/shorten", strings.NewReader(tt.body))
			rec := httptest.NewRecorder()
			h.ServeHTTP(rec, req)

			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d (body=%q)", rec.Code, tt.wantStatus, rec.Body.String())
			}
			if !tt.wantCode {
				return
			}
			var resp shortenResponse
			if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
				t.Fatalf("decode response: %v", err)
			}
			if len(resp.Code) != 6 {
				t.Errorf("code = %q, want length 6", resp.Code)
			}
		})
	}
}

func TestRedirect(t *testing.T) {
	h := newTestServer()

	// Create a short code first.
	post := httptest.NewRequest(http.MethodPost, "/shorten", strings.NewReader(`{"url":"https://example.com/target"}`))
	postRec := httptest.NewRecorder()
	h.ServeHTTP(postRec, post)
	if postRec.Code != http.StatusCreated {
		t.Fatalf("setup shorten failed: status %d", postRec.Code)
	}
	var resp shortenResponse
	if err := json.Unmarshal(postRec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode setup response: %v", err)
	}

	tests := []struct {
		name         string
		code         string
		wantStatus   int
		wantLocation string
	}{
		{
			name:         "known code redirects",
			code:         resp.Code,
			wantStatus:   http.StatusFound,
			wantLocation: "https://example.com/target",
		},
		{
			name:       "unknown code is 404",
			code:       "zzzzzz",
			wantStatus: http.StatusNotFound,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/"+tt.code, nil)
			rec := httptest.NewRecorder()
			h.ServeHTTP(rec, req)

			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d", rec.Code, tt.wantStatus)
			}
			if tt.wantLocation != "" {
				if loc := rec.Header().Get("Location"); loc != tt.wantLocation {
					t.Errorf("Location = %q, want %q", loc, tt.wantLocation)
				}
			}
		})
	}
}

func TestStorePutGet(t *testing.T) {
	s := NewStore(6)
	code, err := s.Put("https://example.com")
	if err != nil {
		t.Fatalf("Put: %v", err)
	}
	if len(code) != 6 {
		t.Errorf("code length = %d, want 6", len(code))
	}
	got, err := s.Get(code)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != "https://example.com" {
		t.Errorf("Get = %q, want %q", got, "https://example.com")
	}
	if _, err := s.Get("missing"); err != ErrNotFound {
		t.Errorf("Get(missing) err = %v, want ErrNotFound", err)
	}
	if s.Len() != 1 {
		t.Errorf("Len = %d, want 1", s.Len())
	}
}

func TestMethodNotAllowed(t *testing.T) {
	h := newTestServer()
	req := httptest.NewRequest(http.MethodDelete, "/shorten", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusMethodNotAllowed)
	}
}
