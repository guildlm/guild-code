package ratelimit

import (
	"math"
	"net"
	"net/http"
	"strconv"
	"sync"
	"time"
)

// KeyFunc derives a rate-limit key from a request, for example the client IP.
type KeyFunc func(*http.Request) string

// ClientIP returns the host portion of r.RemoteAddr, falling back to the raw
// RemoteAddr when it cannot be split.
func ClientIP(r *http.Request) string {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

// Limiter maintains one token bucket per key and provides HTTP middleware.
// It is safe for concurrent use.
type Limiter struct {
	mu      sync.Mutex
	buckets map[string]*Bucket

	capacity   int
	refillRate float64
	keyFunc    KeyFunc

	// now is shared with every bucket so tests can inject a clock.
	now func() time.Time
}

// NewLimiter returns a Limiter whose per-key buckets hold up to capacity tokens
// and refill at refillRate tokens per second. By default keys are client IPs.
func NewLimiter(capacity int, refillRate float64) *Limiter {
	return &Limiter{
		buckets:    make(map[string]*Bucket),
		capacity:   capacity,
		refillRate: refillRate,
		keyFunc:    ClientIP,
		now:        time.Now,
	}
}

// WithKeyFunc sets the function used to derive a bucket key from a request and
// returns the Limiter for chaining. A nil keyFunc is ignored.
func (l *Limiter) WithKeyFunc(keyFunc KeyFunc) *Limiter {
	if keyFunc != nil {
		l.mu.Lock()
		l.keyFunc = keyFunc
		l.mu.Unlock()
	}
	return l
}

// bucket returns the bucket for key, creating it on first use.
func (l *Limiter) bucket(key string) *Bucket {
	l.mu.Lock()
	defer l.mu.Unlock()
	b, ok := l.buckets[key]
	if !ok {
		b = NewBucket(l.capacity, l.refillRate)
		b.now = l.now
		b.last = l.now()
		l.buckets[key] = b
	}
	return b
}

// Allow reports whether the request may proceed, consuming a token if so.
func (l *Limiter) Allow(r *http.Request) bool {
	l.mu.Lock()
	keyFunc := l.keyFunc
	l.mu.Unlock()
	return l.bucket(keyFunc(r)).Allow()
}

// retryAfterSeconds returns how many whole seconds a caller should wait before
// retrying, derived from the refill rate. It is at least 1 when a positive rate
// is configured.
func (l *Limiter) retryAfterSeconds() int {
	if l.refillRate <= 0 {
		return 1
	}
	return int(math.Ceil(1 / l.refillRate))
}

// Middleware wraps next, responding with 429 Too Many Requests when the caller
// has exhausted its bucket.
func (l *Limiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !l.Allow(r) {
			w.Header().Set("Retry-After", strconv.Itoa(l.retryAfterSeconds()))
			http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
			return
		}
		next.ServeHTTP(w, r)
	})
}
