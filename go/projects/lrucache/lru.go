// Package lrucache implements a bounded, in-memory least-recently-used (LRU)
// cache with O(1) Get and Put operations.
//
// The cache is backed by a doubly linked list (container/list) that keeps
// entries ordered by recency of use and a map that provides constant-time
// lookups from key to list element. When the cache exceeds its capacity the
// least-recently-used entry is evicted.
//
// Cache is not safe for concurrent use; callers that share a cache across
// goroutines must provide their own synchronization.
package lrucache

import (
	"container/list"
	"errors"
)

// ErrInvalidCapacity is returned by New when capacity is not positive.
var ErrInvalidCapacity = errors.New("lrucache: capacity must be positive")

// entry is the value stored in each list element. Keeping the key alongside
// the value lets us delete the corresponding map entry in O(1) when an element
// is evicted from the back of the list.
type entry[K comparable, V any] struct {
	key   K
	value V
}

// Cache is a bounded LRU cache mapping keys of type K to values of type V.
// The zero value is not usable; construct a Cache with New.
type Cache[K comparable, V any] struct {
	capacity int
	ll       *list.List          // front = most recently used, back = least
	items    map[K]*list.Element // key -> element holding entry[K, V]
}

// New returns an empty Cache that holds at most capacity entries. It returns
// ErrInvalidCapacity if capacity is less than 1.
func New[K comparable, V any](capacity int) (*Cache[K, V], error) {
	if capacity < 1 {
		return nil, ErrInvalidCapacity
	}
	return &Cache[K, V]{
		capacity: capacity,
		ll:       list.New(),
		items:    make(map[K]*list.Element, capacity),
	}, nil
}

// Len reports the number of entries currently stored in the cache.
func (c *Cache[K, V]) Len() int {
	return c.ll.Len()
}

// Cap reports the maximum number of entries the cache can hold.
func (c *Cache[K, V]) Cap() int {
	return c.capacity
}

// Get returns the value associated with key and marks it as most recently
// used. The second return value reports whether the key was present.
func (c *Cache[K, V]) Get(key K) (V, bool) {
	if el, ok := c.items[key]; ok {
		c.ll.MoveToFront(el)
		return el.Value.(*entry[K, V]).value, true
	}
	var zero V
	return zero, false
}

// Peek returns the value associated with key WITHOUT updating its recency.
// The second return value reports whether the key was present.
func (c *Cache[K, V]) Peek(key K) (V, bool) {
	if el, ok := c.items[key]; ok {
		return el.Value.(*entry[K, V]).value, true
	}
	var zero V
	return zero, false
}

// Contains reports whether key is present without updating its recency.
func (c *Cache[K, V]) Contains(key K) bool {
	_, ok := c.items[key]
	return ok
}

// Put inserts or updates the value for key and marks it as most recently used.
// If inserting a new key causes the cache to exceed its capacity, the
// least-recently-used entry is evicted. Put reports whether an eviction
// occurred.
func (c *Cache[K, V]) Put(key K, value V) (evicted bool) {
	if el, ok := c.items[key]; ok {
		el.Value.(*entry[K, V]).value = value
		c.ll.MoveToFront(el)
		return false
	}

	el := c.ll.PushFront(&entry[K, V]{key: key, value: value})
	c.items[key] = el

	if c.ll.Len() > c.capacity {
		c.removeOldest()
		return true
	}
	return false
}

// Remove deletes key from the cache. It reports whether the key was present.
func (c *Cache[K, V]) Remove(key K) bool {
	if el, ok := c.items[key]; ok {
		c.removeElement(el)
		return true
	}
	return false
}

// removeOldest evicts the least-recently-used entry, if any.
func (c *Cache[K, V]) removeOldest() {
	if el := c.ll.Back(); el != nil {
		c.removeElement(el)
	}
}

// removeElement unlinks el from the list and deletes its map entry.
func (c *Cache[K, V]) removeElement(el *list.Element) {
	c.ll.Remove(el)
	delete(c.items, el.Value.(*entry[K, V]).key)
}
