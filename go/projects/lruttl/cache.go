// Package lruttl implements a thread-safe, generic LRU cache with per-entry
// time-to-live (TTL) expiry. Eviction is driven by both recency of use and
// elapsed time: the least-recently-used entry is dropped once the cache is at
// capacity, and expired entries are removed lazily when they are read.
package lruttl

import (
	"container/list"
	"sync"
	"time"
)

// entry is the value stored in each list element. It keeps the key alongside
// the value so that evicting from the back of the list can also delete the
// corresponding map index.
type entry[K comparable, V any] struct {
	key       K
	value     V
	expiresAt time.Time // zero means the entry never expires
}

// Cache is a fixed-capacity LRU cache whose entries expire after a TTL.
// The zero value is not usable; construct one with New. A Cache is safe for
// concurrent use by multiple goroutines.
type Cache[K comparable, V any] struct {
	mu       sync.Mutex
	capacity int
	ttl      time.Duration
	ll       *list.List // front = most recently used, back = least
	items    map[K]*list.Element
	now      func() time.Time // injectable clock, defaults to time.Now
}

// New creates a Cache that holds at most capacity entries. Each entry expires
// ttl after it is written; a non-positive ttl disables time-based expiry while
// leaving LRU eviction active. New panics if capacity is not positive.
func New[K comparable, V any](capacity int, ttl time.Duration) *Cache[K, V] {
	if capacity <= 0 {
		panic("lruttl: capacity must be positive")
	}
	return &Cache[K, V]{
		capacity: capacity,
		ttl:      ttl,
		ll:       list.New(),
		items:    make(map[K]*list.Element),
		now:      time.Now,
	}
}

// Put inserts or updates the value for key, marking it most recently used and
// (re)starting its TTL. If inserting a new key exceeds capacity, the
// least-recently-used entry is evicted.
func (c *Cache[K, V]) Put(key K, value V) {
	c.mu.Lock()
	defer c.mu.Unlock()

	var expiresAt time.Time
	if c.ttl > 0 {
		expiresAt = c.now().Add(c.ttl)
	}

	if el, ok := c.items[key]; ok {
		c.ll.MoveToFront(el)
		ent := el.Value.(*entry[K, V])
		ent.value = value
		ent.expiresAt = expiresAt
		return
	}

	el := c.ll.PushFront(&entry[K, V]{key: key, value: value, expiresAt: expiresAt})
	c.items[key] = el

	if c.ll.Len() > c.capacity {
		c.evictOldest()
	}
}

// Get returns the value for key and whether it was present and unexpired.
// A successful read marks the entry most recently used. An expired entry is
// removed and reported as absent (lazy expiry).
func (c *Cache[K, V]) Get(key K) (V, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	el, ok := c.items[key]
	if !ok {
		var zero V
		return zero, false
	}

	ent := el.Value.(*entry[K, V])
	if c.expired(ent) {
		c.removeElement(el)
		var zero V
		return zero, false
	}

	c.ll.MoveToFront(el)
	return ent.value, true
}

// Len reports the number of entries currently retained. It does not account
// for entries that have expired but not yet been read.
func (c *Cache[K, V]) Len() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.ll.Len()
}

// expired reports whether ent has a TTL that has elapsed.
func (c *Cache[K, V]) expired(ent *entry[K, V]) bool {
	return !ent.expiresAt.IsZero() && !c.now().Before(ent.expiresAt)
}

// evictOldest removes the least-recently-used element. The caller must hold mu.
func (c *Cache[K, V]) evictOldest() {
	if el := c.ll.Back(); el != nil {
		c.removeElement(el)
	}
}

// removeElement detaches el from both the list and the map. The caller must
// hold mu.
func (c *Cache[K, V]) removeElement(el *list.Element) {
	c.ll.Remove(el)
	ent := el.Value.(*entry[K, V])
	delete(c.items, ent.key)
}
