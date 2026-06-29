package ratelimit

import (
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

// fakeClock is a controllable time source for deterministic refill tests.
type fakeClock struct {
	mu sync.Mutex
	t  time.Time
}

func (c *fakeClock) Now() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.t
}

func (c *fakeClock) Advance(d time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.t = c.t.Add(d)
}

func TestNewBucketStartsFull(t *testing.T) {
	tests := []struct {
		name     string
		capacity int
		want     float64
	}{
		{name: "positive", capacity: 5, want: 5},
		{name: "zero", capacity: 0, want: 0},
		{name: "negative clamped", capacity: -3, want: 0},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			b := NewBucket(tt.capacity, 1)
			if got := b.Tokens(); got != tt.want {
				t.Errorf("Tokens() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestAllowConsumesUntilEmpty(t *testing.T) {
	clock := &fakeClock{t: time.Unix(0, 0)}
	b := NewBucket(3, 0) // no refill so the bucket cannot recover
	b.now = clock.Now
	b.last = clock.Now()

	tests := []struct {
		call int
		want bool
	}{
		{call: 1, want: true},
		{call: 2, want: true},
		{call: 3, want: true},
		{call: 4, want: false},
		{call: 5, want: false},
	}
	for _, tt := range tests {
		if got := b.Allow(); got != tt.want {
			t.Errorf("Allow() call %d = %v, want %v", tt.call, got, tt.want)
		}
	}
}

func TestAllowN(t *testing.T) {
	tests := []struct {
		name     string
		capacity int
		n        int
		want     bool
		wantLeft float64
	}{
		{name: "exact", capacity: 5, n: 5, want: true, wantLeft: 0},
		{name: "partial", capacity: 5, n: 2, want: true, wantLeft: 3},
		{name: "too many", capacity: 5, n: 6, want: false, wantLeft: 5},
		{name: "zero consumes nothing", capacity: 5, n: 0, want: true, wantLeft: 5},
		{name: "negative consumes nothing", capacity: 5, n: -1, want: true, wantLeft: 5},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			b := NewBucket(tt.capacity, 0)
			if got := b.AllowN(tt.n); got != tt.want {
				t.Errorf("AllowN(%d) = %v, want %v", tt.n, got, tt.want)
			}
			if got := b.Tokens(); got != tt.wantLeft {
				t.Errorf("Tokens() = %v, want %v", got, tt.wantLeft)
			}
		})
	}
}

func TestRefillOverTime(t *testing.T) {
	clock := &fakeClock{t: time.Unix(0, 0)}
	b := NewBucket(10, 2) // 2 tokens/sec
	b.now = clock.Now
	b.last = clock.Now()

	// Drain the bucket completely.
	if !b.AllowN(10) {
		t.Fatalf("expected to drain full bucket")
	}
	if got := b.Tokens(); got != 0 {
		t.Fatalf("Tokens() after drain = %v, want 0", got)
	}

	tests := []struct {
		advance time.Duration
		want    float64
	}{
		{advance: 500 * time.Millisecond, want: 1}, // 0.5s * 2 = 1
		{advance: 500 * time.Millisecond, want: 2}, // another 1
		{advance: 10 * time.Second, want: 10},      // caps at capacity
	}
	for i, tt := range tests {
		clock.Advance(tt.advance)
		if got := b.Tokens(); got != tt.want {
			t.Errorf("step %d: Tokens() = %v, want %v", i, got, tt.want)
		}
	}
}

func TestRefillDoesNotExceedCapacity(t *testing.T) {
	clock := &fakeClock{t: time.Unix(0, 0)}
	b := NewBucket(4, 100)
	b.now = clock.Now
	b.last = clock.Now()

	clock.Advance(time.Hour)
	if got := b.Tokens(); got != 4 {
		t.Errorf("Tokens() = %v, want 4 (capped at capacity)", got)
	}
}

func TestMiddleware429AfterExhaustion(t *testing.T) {
	clock := &fakeClock{t: time.Unix(0, 0)}
	l := NewLimiter(2, 1)
	l.now = clock.Now

	var hits int
	handler := l.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hits++
		w.WriteHeader(http.StatusOK)
	}))

	tests := []struct {
		call       int
		wantStatus int
	}{
		{call: 1, wantStatus: http.StatusOK},
		{call: 2, wantStatus: http.StatusOK},
		{call: 3, wantStatus: http.StatusTooManyRequests},
		{call: 4, wantStatus: http.StatusTooManyRequests},
	}
	for _, tt := range tests {
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		req.RemoteAddr = "10.0.0.1:1234"
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)
		if rec.Code != tt.wantStatus {
			t.Errorf("call %d: status = %d, want %d", tt.call, rec.Code, tt.wantStatus)
		}
		if tt.wantStatus == http.StatusTooManyRequests {
			if ra := rec.Header().Get("Retry-After"); ra != "1" {
				t.Errorf("call %d: Retry-After = %q, want %q", tt.call, ra, "1")
			}
		}
	}
	if hits != 2 {
		t.Errorf("handler hits = %d, want 2", hits)
	}
}

func TestMiddlewarePerKeyIsolation(t *testing.T) {
	clock := &fakeClock{t: time.Unix(0, 0)}
	l := NewLimiter(1, 0)
	l.now = clock.Now

	handler := l.Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	do := func(addr string) int {
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		req.RemoteAddr = addr
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)
		return rec.Code
	}

	// First client exhausts its single token.
	if got := do("1.1.1.1:1"); got != http.StatusOK {
		t.Errorf("client A first call = %d, want 200", got)
	}
	if got := do("1.1.1.1:2"); got != http.StatusTooManyRequests {
		t.Errorf("client A second call = %d, want 429", got)
	}
	// A different client is unaffected.
	if got := do("2.2.2.2:1"); got != http.StatusOK {
		t.Errorf("client B first call = %d, want 200", got)
	}
}

func TestClientIP(t *testing.T) {
	tests := []struct {
		name       string
		remoteAddr string
		want       string
	}{
		{name: "host port", remoteAddr: "192.168.1.5:54321", want: "192.168.1.5"},
		{name: "no port", remoteAddr: "192.168.1.5", want: "192.168.1.5"},
		{name: "ipv6", remoteAddr: "[::1]:8080", want: "::1"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/", nil)
			req.RemoteAddr = tt.remoteAddr
			if got := ClientIP(req); got != tt.want {
				t.Errorf("ClientIP() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestConcurrentAllowIsRaceFree(t *testing.T) {
	b := NewBucket(1000, 0)
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 10; j++ {
				b.Allow()
			}
		}()
	}
	wg.Wait()
	// 100 * 10 = 1000 tokens consumed exactly.
	if got := b.Tokens(); got != 0 {
		t.Errorf("Tokens() after concurrent drain = %v, want 0", got)
	}
}
