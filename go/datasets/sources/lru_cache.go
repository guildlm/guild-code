// Package lru implements a small fixed-capacity LRU cache.
//
// It pairs a map for O(1) lookups with a container/list doubly linked list to
// track recency, evicting the least-recently-used entry when full.
package lru

import "container/list"

type entry struct {
	key   string
	value int
}

// Cache is a non-concurrent LRU cache mapping string keys to int values.
type Cache struct {
	capacity int
	ll       *list.List
	items    map[string]*list.Element
}

// New returns a Cache holding at most capacity entries (minimum 1).
func New(capacity int) *Cache {
	if capacity < 1 {
		capacity = 1
	}
	return &Cache{
		capacity: capacity,
		ll:       list.New(),
		items:    make(map[string]*list.Element, capacity),
	}
}

// Get returns the value for key and marks it most-recently-used.
func (c *Cache) Get(key string) (int, bool) {
	el, ok := c.items[key]
	if !ok {
		return 0, false
	}
	c.ll.MoveToFront(el)
	return el.Value.(*entry).value, true
}

// Put inserts or updates key, evicting the least-recently-used entry if needed.
func (c *Cache) Put(key string, value int) {
	if el, ok := c.items[key]; ok {
		el.Value.(*entry).value = value
		c.ll.MoveToFront(el)
		return
	}
	c.items[key] = c.ll.PushFront(&entry{key: key, value: value})
	if c.ll.Len() > c.capacity {
		oldest := c.ll.Back()
		if oldest != nil {
			c.ll.Remove(oldest)
			delete(c.items, oldest.Value.(*entry).key)
		}
	}
}
