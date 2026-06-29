package pool

import "errors"

// ErrEmptyPool is returned by New when no resources are supplied.
var ErrEmptyPool = errors.New("pool: at least one resource is required")

// Pool is a bounded, generic resource pool. It hands out a fixed set of
// pre-created resources of type T and bounds concurrent checkouts to that
// fixed capacity using a buffered channel as a semaphore. Acquire blocks until
// a resource is free; TryAcquire is the non-blocking variant.
//
// The zero value is not usable; create one with New. A Pool is safe for
// concurrent use by multiple goroutines.
type Pool[T any] struct {
	free chan T
}

// New returns a Pool seeded with the given resources. The pool capacity is
// fixed at len(items). It returns ErrEmptyPool if no resources are supplied.
func New[T any](items ...T) (*Pool[T], error) {
	if len(items) == 0 {
		return nil, ErrEmptyPool
	}
	p := &Pool[T]{free: make(chan T, len(items))}
	for _, it := range items {
		p.free <- it
	}
	return p, nil
}

// Acquire checks out a resource, blocking until one is available. Each
// acquired resource must be returned with Release.
func (p *Pool[T]) Acquire() T {
	return <-p.free
}

// TryAcquire checks out a resource without blocking. It returns the resource
// and true if one was available, or the zero value of T and false otherwise.
func (p *Pool[T]) TryAcquire() (T, bool) {
	select {
	case it := <-p.free:
		return it, true
	default:
		var zero T
		return zero, false
	}
}

// Release returns a resource to the pool so it can be acquired again. Only
// resources obtained from Acquire or TryAcquire should be released; releasing
// more resources than the pool's capacity blocks until a slot frees.
func (p *Pool[T]) Release(item T) {
	p.free <- item
}

// Available reports the number of resources currently free for checkout.
func (p *Pool[T]) Available() int {
	return len(p.free)
}

// Cap reports the fixed capacity of the pool.
func (p *Pool[T]) Cap() int {
	return cap(p.free)
}
