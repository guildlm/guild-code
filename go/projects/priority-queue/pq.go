// Package pq provides a generic min-heap priority queue built on
// container/heap. The lowest-priority item is always dequeued first.
//
// The heap.Interface boilerplate is kept unexported so callers only deal
// with a small, type-safe API: Push, Pop and Len.
package pq

import "container/heap"

// PriorityQueue is a min-heap of items of type T. Items with the smallest
// priority value are returned first by Pop. Ties are broken in favor of the
// item that was pushed earlier (FIFO among equal priorities).
//
// The zero value is not ready for use; create a queue with New.
type PriorityQueue[T any] struct {
	h *minHeap[T]
}

// New returns an empty PriorityQueue ready for use.
func New[T any]() *PriorityQueue[T] {
	h := &minHeap[T]{}
	heap.Init(h)
	return &PriorityQueue[T]{h: h}
}

// Len reports the number of items currently in the queue.
func (pq *PriorityQueue[T]) Len() int {
	return pq.h.Len()
}

// Push adds item to the queue with the given priority. Lower priority values
// are dequeued before higher ones.
func (pq *PriorityQueue[T]) Push(item T, priority int) {
	heap.Push(pq.h, entry[T]{value: item, priority: priority, seq: pq.h.counter})
	pq.h.counter++
}

// Pop removes and returns the lowest-priority item. The boolean result is
// false if the queue is empty, in which case the zero value of T is returned.
func (pq *PriorityQueue[T]) Pop() (T, bool) {
	if pq.h.Len() == 0 {
		var zero T
		return zero, false
	}
	e := heap.Pop(pq.h).(entry[T])
	return e.value, true
}

// entry is one stored element. seq preserves insertion order so that items
// sharing a priority are returned FIFO.
type entry[T any] struct {
	value    T
	priority int
	seq      uint64
}

// minHeap implements heap.Interface for a slice of entry[T]. It is unexported
// so the boilerplate never leaks into the public API.
type minHeap[T any] struct {
	items   []entry[T]
	counter uint64
}

func (h *minHeap[T]) Len() int { return len(h.items) }

func (h *minHeap[T]) Less(i, j int) bool {
	if h.items[i].priority != h.items[j].priority {
		return h.items[i].priority < h.items[j].priority
	}
	return h.items[i].seq < h.items[j].seq
}

func (h *minHeap[T]) Swap(i, j int) {
	h.items[i], h.items[j] = h.items[j], h.items[i]
}

func (h *minHeap[T]) Push(x any) {
	h.items = append(h.items, x.(entry[T]))
}

func (h *minHeap[T]) Pop() any {
	old := h.items
	n := len(old)
	e := old[n-1]
	old[n-1] = entry[T]{} // avoid retaining a reference for the GC
	h.items = old[:n-1]
	return e
}
