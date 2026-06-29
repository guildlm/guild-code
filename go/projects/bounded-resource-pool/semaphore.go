// Package pool provides a semaphore-based bounded resource pool built on the
// standard library "channel as semaphore" idiom.
package pool

// Semaphore is a counting semaphore that bounds the number of concurrent
// holders to a fixed capacity. A buffered channel of tokens is used as the
// underlying primitive: acquiring sends a token, releasing receives one.
//
// The zero value is not usable; create one with NewSemaphore. A Semaphore is
// safe for concurrent use by multiple goroutines.
type Semaphore struct {
	tokens chan struct{}
}

// NewSemaphore returns a Semaphore that permits at most capacity concurrent
// holders. It panics if capacity is not positive.
func NewSemaphore(capacity int) *Semaphore {
	if capacity <= 0 {
		panic("pool: semaphore capacity must be positive")
	}
	return &Semaphore{tokens: make(chan struct{}, capacity)}
}

// Acquire takes one slot, blocking until a slot is available. Each successful
// Acquire must be balanced by exactly one Release.
func (s *Semaphore) Acquire() {
	s.tokens <- struct{}{}
}

// TryAcquire attempts to take one slot without blocking. It reports whether a
// slot was taken; a true result must be balanced by exactly one Release.
func (s *Semaphore) TryAcquire() bool {
	select {
	case s.tokens <- struct{}{}:
		return true
	default:
		return false
	}
}

// Release returns one previously acquired slot. Calling Release without a
// matching Acquire blocks until another goroutine acquires a slot, so callers
// must pair every Release with a successful Acquire or TryAcquire.
func (s *Semaphore) Release() {
	<-s.tokens
}

// Len reports the number of slots currently held.
func (s *Semaphore) Len() int {
	return len(s.tokens)
}

// Cap reports the total capacity of the semaphore.
func (s *Semaphore) Cap() int {
	return cap(s.tokens)
}
