package lrucache

import "container/list"

// Keys returns the cache keys ordered from most-recently-used to
// least-recently-used. The returned slice is a fresh copy; mutating it does
// not affect the cache. Calling Keys does not alter recency.
func (c *Cache[K, V]) Keys() []K {
	keys := make([]K, 0, c.ll.Len())
	for el := c.ll.Front(); el != nil; el = el.Next() {
		keys = append(keys, el.Value.(*entry[K, V]).key)
	}
	return keys
}

// Clear removes all entries from the cache, retaining its capacity.
func (c *Cache[K, V]) Clear() {
	c.ll.Init()
	c.items = make(map[K]*list.Element, c.capacity)
}
