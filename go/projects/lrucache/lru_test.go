package lrucache

import (
	"errors"
	"reflect"
	"testing"
)

func TestNewInvalidCapacity(t *testing.T) {
	tests := []struct {
		name     string
		capacity int
		wantErr  bool
	}{
		{name: "zero capacity", capacity: 0, wantErr: true},
		{name: "negative capacity", capacity: -3, wantErr: true},
		{name: "capacity one", capacity: 1, wantErr: false},
		{name: "capacity many", capacity: 128, wantErr: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c, err := New[string, int](tt.capacity)
			if tt.wantErr {
				if !errors.Is(err, ErrInvalidCapacity) {
					t.Fatalf("New(%d) error = %v, want ErrInvalidCapacity", tt.capacity, err)
				}
				if c != nil {
					t.Errorf("New(%d) cache = %v, want nil", tt.capacity, c)
				}
				return
			}
			if err != nil {
				t.Fatalf("New(%d) unexpected error: %v", tt.capacity, err)
			}
			if got := c.Cap(); got != tt.capacity {
				t.Errorf("Cap() = %d, want %d", got, tt.capacity)
			}
			if got := c.Len(); got != 0 {
				t.Errorf("Len() = %d, want 0", got)
			}
		})
	}
}

func mustNew[K comparable, V any](t *testing.T, capacity int) *Cache[K, V] {
	t.Helper()
	c, err := New[K, V](capacity)
	if err != nil {
		t.Fatalf("New(%d): %v", capacity, err)
	}
	return c
}

func TestPutGet(t *testing.T) {
	c := mustNew[string, int](t, 2)

	if v, ok := c.Get("missing"); ok {
		t.Errorf("Get(missing) = (%d, true), want miss", v)
	}

	if evicted := c.Put("a", 1); evicted {
		t.Errorf("Put(a) evicted on empty cache")
	}
	if v, ok := c.Get("a"); !ok || v != 1 {
		t.Errorf("Get(a) = (%d, %v), want (1, true)", v, ok)
	}

	// Updating an existing key must not change Len and must not evict.
	if evicted := c.Put("a", 11); evicted {
		t.Errorf("Put(a) update evicted")
	}
	if v, ok := c.Get("a"); !ok || v != 11 {
		t.Errorf("Get(a) after update = (%d, %v), want (11, true)", v, ok)
	}
	if got := c.Len(); got != 1 {
		t.Errorf("Len() = %d, want 1", got)
	}
}

func TestEvictionOrder(t *testing.T) {
	c := mustNew[string, int](t, 2)
	c.Put("a", 1)
	c.Put("b", 2)

	// Access "a" so "b" becomes the least-recently-used.
	if _, ok := c.Get("a"); !ok {
		t.Fatalf("Get(a) miss")
	}

	// Inserting "c" must evict "b".
	if evicted := c.Put("c", 3); !evicted {
		t.Errorf("Put(c) evicted = false, want true")
	}
	if c.Contains("b") {
		t.Errorf("expected b to be evicted")
	}
	if !c.Contains("a") || !c.Contains("c") {
		t.Errorf("expected a and c to remain: keys=%v", c.Keys())
	}
	if got := c.Len(); got != 2 {
		t.Errorf("Len() = %d, want 2", got)
	}
}

func TestPutUpdateRefreshesRecency(t *testing.T) {
	c := mustNew[string, int](t, 2)
	c.Put("a", 1)
	c.Put("b", 2)

	// Re-Put "a" to refresh recency; "b" is now least recently used.
	c.Put("a", 10)
	c.Put("c", 3) // should evict "b"

	if c.Contains("b") {
		t.Errorf("expected b evicted after refreshing a")
	}
	if v, ok := c.Peek("a"); !ok || v != 10 {
		t.Errorf("Peek(a) = (%d, %v), want (10, true)", v, ok)
	}
}

func TestPeekDoesNotChangeRecency(t *testing.T) {
	c := mustNew[string, int](t, 2)
	c.Put("a", 1)
	c.Put("b", 2)

	// Peek "a" — must NOT promote it. "a" remains LRU.
	if v, ok := c.Peek("a"); !ok || v != 1 {
		t.Fatalf("Peek(a) = (%d, %v), want (1, true)", v, ok)
	}
	c.Put("c", 3) // should evict the still-LRU "a"

	if c.Contains("a") {
		t.Errorf("expected a evicted; Peek must not refresh recency")
	}
	if !c.Contains("b") || !c.Contains("c") {
		t.Errorf("keys = %v, want b and c", c.Keys())
	}
}

func TestRemove(t *testing.T) {
	c := mustNew[string, int](t, 3)
	c.Put("a", 1)
	c.Put("b", 2)

	if ok := c.Remove("missing"); ok {
		t.Errorf("Remove(missing) = true, want false")
	}
	if ok := c.Remove("a"); !ok {
		t.Errorf("Remove(a) = false, want true")
	}
	if c.Contains("a") {
		t.Errorf("a still present after Remove")
	}
	if got := c.Len(); got != 1 {
		t.Errorf("Len() = %d, want 1", got)
	}

	// After removal there is room; inserting must not evict.
	if evicted := c.Put("c", 3); evicted {
		t.Errorf("Put(c) evicted after Remove freed space")
	}
}

func TestKeysOrder(t *testing.T) {
	c := mustNew[int, int](t, 3)
	c.Put(1, 1)
	c.Put(2, 2)
	c.Put(3, 3)
	c.Get(1) // promote 1 to MRU

	// MRU -> LRU should be: 1, 3, 2.
	want := []int{1, 3, 2}
	if got := c.Keys(); !reflect.DeepEqual(got, want) {
		t.Errorf("Keys() = %v, want %v", got, want)
	}
}

func TestClear(t *testing.T) {
	c := mustNew[string, int](t, 2)
	c.Put("a", 1)
	c.Put("b", 2)
	c.Clear()

	if got := c.Len(); got != 0 {
		t.Errorf("Len() after Clear = %d, want 0", got)
	}
	if c.Contains("a") || c.Contains("b") {
		t.Errorf("entries remain after Clear: %v", c.Keys())
	}
	// Cache must remain usable after Clear.
	if evicted := c.Put("x", 9); evicted {
		t.Errorf("Put after Clear evicted unexpectedly")
	}
	if v, ok := c.Get("x"); !ok || v != 9 {
		t.Errorf("Get(x) after Clear = (%d, %v), want (9, true)", v, ok)
	}
}

func TestCapacityOneRepeatedEviction(t *testing.T) {
	c := mustNew[int, int](t, 1)
	for i := 0; i < 100; i++ {
		c.Put(i, i*i)
		if got := c.Len(); got != 1 {
			t.Fatalf("Len() = %d at i=%d, want 1", got, i)
		}
		if v, ok := c.Peek(i); !ok || v != i*i {
			t.Fatalf("Peek(%d) = (%d, %v), want (%d, true)", i, v, ok, i*i)
		}
		if i > 0 && c.Contains(i-1) {
			t.Fatalf("key %d not evicted at capacity 1", i-1)
		}
	}
}
