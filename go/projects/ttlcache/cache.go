// Package ttlcache provides a small, concurrency-safe key-value cache where
// every entry carries a time-to-live (TTL). Expired entries are purged lazily
// the first time they are read after their deadline has passed.
package ttlcache

import (
	"sync"
	"time"
)

// item is a single stored value together with its expiry deadline. A zero
// expireAt means the entry never expires.
type item struct {
	value    any
	expireAt time.Time
}

// Cache is a concurrency-safe TTL key-value store. The zero value is not
// usable; obtain a Cache with New.
type Cache struct {
	mu    sync.Mutex
	items map[string]item
	// now is the clock used for expiry decisions. It is a field so tests can
	// inject a deterministic clock; production code uses time.Now.
	now func() time.Time
}

// New returns an empty Cache ready for concurrent use.
func New() *Cache {
	return &Cache{
		items: make(map[string]item),
		now:   time.Now,
	}
}

// Set stores value under key, expiring it after ttl. A ttl of zero or less
// stores the entry without an expiry deadline (it lives until overwritten or
// deleted).
func (c *Cache) Set(key string, value any, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()

	it := item{value: value}
	if ttl > 0 {
		it.expireAt = c.now().Add(ttl)
	}
	c.items[key] = it
}

// Get returns the value stored under key and whether it is present and not yet
// expired. An expired entry is deleted as a side effect and reported as absent
// (ok == false).
func (c *Cache) Get(key string) (any, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	it, ok := c.items[key]
	if !ok {
		return nil, false
	}
	if c.expired(it) {
		delete(c.items, key)
		return nil, false
	}
	return it.value, true
}

// Delete removes key from the cache. Deleting an absent key is a no-op.
func (c *Cache) Delete(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	delete(c.items, key)
}

// Len reports the number of entries that are currently present and unexpired.
// Expired-but-not-yet-purged entries are not counted, but Len does not delete
// them; use Get (or a future sweep) to reclaim them.
func (c *Cache) Len() int {
	c.mu.Lock()
	defer c.mu.Unlock()

	n := 0
	for _, it := range c.items {
		if !c.expired(it) {
			n++
		}
	}
	return n
}

// expired reports whether it has passed its expiry deadline. Entries with a
// zero deadline never expire. The caller must hold c.mu.
func (c *Cache) expired(it item) bool {
	return !it.expireAt.IsZero() && !c.now().Before(it.expireAt)
}
