// Package pool provides a thread-safe, generic object pool.
//
// A Pool reuses previously returned values to reduce allocation churn.
// When no value is available, the pool creates a new one with the
// factory function supplied to New. All methods are safe for concurrent
// use by multiple goroutines.
package pool

import "sync"

// Pool is a thread-safe pool of reusable values of type T.
//
// The zero value of Pool is not usable; create one with New.
type Pool[T any] struct {
	mu      sync.Mutex
	factory func() T
	items   []T
}

// New returns a Pool that uses factory to create new values when the
// pool is empty. factory must not be nil; New panics otherwise.
func New[T any](factory func() T) *Pool[T] {
	if factory == nil {
		panic("pool: New called with nil factory")
	}
	return &Pool[T]{factory: factory}
}

// Get returns a value from the pool, reusing a previously returned value
// when one is available or creating a new one with the factory otherwise.
func (p *Pool[T]) Get() T {
	p.mu.Lock()
	n := len(p.items)
	if n == 0 {
		p.mu.Unlock()
		return p.factory()
	}
	item := p.items[n-1]
	// Clear the slot so the popped value can be garbage collected if it
	// is never returned, then shrink the slice.
	var zero T
	p.items[n-1] = zero
	p.items = p.items[:n-1]
	p.mu.Unlock()
	return item
}

// Put returns a value to the pool so it can be reused by a later Get.
func (p *Pool[T]) Put(item T) {
	p.mu.Lock()
	p.items = append(p.items, item)
	p.mu.Unlock()
}

// Len reports the number of idle values currently held by the pool.
func (p *Pool[T]) Len() int {
	p.mu.Lock()
	n := len(p.items)
	p.mu.Unlock()
	return n
}
