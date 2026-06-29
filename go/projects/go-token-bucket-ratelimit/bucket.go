// Package ratelimit provides a concurrency-safe token-bucket rate limiter
// and an HTTP middleware that responds with 429 Too Many Requests when a
// caller exceeds its configured rate.
package ratelimit

import (
	"sync"
	"time"
)

// Bucket is a token-bucket rate limiter. Tokens accrue at refillRate per
// second up to capacity. A request consumes tokens; when none are available
// the request is denied. Bucket is safe for concurrent use.
type Bucket struct {
	mu         sync.Mutex
	capacity   float64
	tokens     float64
	refillRate float64 // tokens added per second
	last       time.Time

	// now returns the current time. It is a field so tests can inject a
	// deterministic clock; it defaults to time.Now.
	now func() time.Time
}

// NewBucket returns a Bucket that holds up to capacity tokens and refills at
// refillRate tokens per second. The bucket starts full. capacity is clamped to
// a minimum of 0 and refillRate to a minimum of 0.
func NewBucket(capacity int, refillRate float64) *Bucket {
	cap := float64(capacity)
	if cap < 0 {
		cap = 0
	}
	if refillRate < 0 {
		refillRate = 0
	}
	return &Bucket{
		capacity:   cap,
		tokens:     cap,
		refillRate: refillRate,
		last:       time.Now(),
		now:        time.Now,
	}
}

// refill adds tokens accrued since the last update. The caller must hold mu.
func (b *Bucket) refill() {
	now := b.now()
	elapsed := now.Sub(b.last).Seconds()
	if elapsed <= 0 {
		return
	}
	b.tokens += elapsed * b.refillRate
	if b.tokens > b.capacity {
		b.tokens = b.capacity
	}
	b.last = now
}

// Allow reports whether a single token is available, consuming it if so.
func (b *Bucket) Allow() bool {
	return b.AllowN(1)
}

// AllowN reports whether n tokens are available, consuming them if so.
// A non-positive n is always allowed and consumes nothing.
func (b *Bucket) AllowN(n int) bool {
	if n <= 0 {
		return true
	}
	need := float64(n)

	b.mu.Lock()
	defer b.mu.Unlock()

	b.refill()
	if b.tokens >= need {
		b.tokens -= need
		return true
	}
	return false
}

// Tokens returns the number of tokens currently available after accounting for
// refill. It is primarily useful for tests and introspection.
func (b *Bucket) Tokens() float64 {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.refill()
	return b.tokens
}
