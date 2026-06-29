// Package ringbuffer provides a fixed-capacity ring (circular) buffer.
//
// When the buffer is full, pushing a new element overwrites the oldest
// element, keeping only the most recent `capacity` items.
package ringbuffer

import "errors"

// ErrEmpty is returned by Pop when the buffer contains no elements.
var ErrEmpty = errors.New("ringbuffer: buffer is empty")

// RingBuffer is a fixed-capacity FIFO buffer. The zero value is not usable;
// construct one with New.
type RingBuffer[T any] struct {
	buf   []T
	head  int // index of the oldest element
	count int // number of elements currently stored
}

// New returns a RingBuffer that can hold up to capacity elements.
// It panics if capacity is not positive, since a non-positive capacity
// cannot store anything and almost always indicates a programming error.
func New[T any](capacity int) *RingBuffer[T] {
	if capacity <= 0 {
		panic("ringbuffer: capacity must be positive")
	}
	return &RingBuffer[T]{buf: make([]T, capacity)}
}

// Cap returns the maximum number of elements the buffer can hold.
func (r *RingBuffer[T]) Cap() int { return len(r.buf) }

// Len returns the number of elements currently stored.
func (r *RingBuffer[T]) Len() int { return r.count }

// Push appends v to the buffer. If the buffer is full, the oldest element
// is overwritten and discarded.
func (r *RingBuffer[T]) Push(v T) {
	tail := (r.head + r.count) % len(r.buf)
	r.buf[tail] = v
	if r.count == len(r.buf) {
		// Full: overwrite oldest, advance head.
		r.head = (r.head + 1) % len(r.buf)
	} else {
		r.count++
	}
}

// Pop removes and returns the oldest element. It returns ErrEmpty if the
// buffer is empty.
func (r *RingBuffer[T]) Pop() (T, error) {
	var zero T
	if r.count == 0 {
		return zero, ErrEmpty
	}
	v := r.buf[r.head]
	r.buf[r.head] = zero // release reference for GC
	r.head = (r.head + 1) % len(r.buf)
	r.count--
	return v, nil
}

// ToSlice returns the buffer's elements in logical order, from oldest to
// newest. The returned slice is a fresh copy and does not alias internal
// storage.
func (r *RingBuffer[T]) ToSlice() []T {
	out := make([]T, r.count)
	for i := 0; i < r.count; i++ {
		out[i] = r.buf[(r.head+i)%len(r.buf)]
	}
	return out
}
