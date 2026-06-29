package lruttl

import (
	"testing"
	"time"
)

// fakeClock is a manually-advanced clock for deterministic TTL tests.
type fakeClock struct{ t time.Time }

func (f *fakeClock) Now() time.Time          { return f.t }
func (f *fakeClock) Advance(d time.Duration) { f.t = f.t.Add(d) }

// newWithClock builds a Cache wired to fc so tests control time precisely.
func newWithClock[K comparable, V any](capacity int, ttl time.Duration, fc *fakeClock) *Cache[K, V] {
	c := New[K, V](capacity, ttl)
	c.now = fc.Now
	return c
}

func TestPutGet(t *testing.T) {
	c := New[string, int](2, time.Minute)
	c.Put("a", 1)

	got, ok := c.Get("a")
	if !ok || got != 1 {
		t.Fatalf("Get(a) = (%d, %v), want (1, true)", got, ok)
	}

	if _, ok := c.Get("missing"); ok {
		t.Errorf("Get(missing) = true, want false")
	}
}

func TestPutUpdatesValueAndKeepsLen(t *testing.T) {
	c := New[string, int](2, time.Minute)
	c.Put("a", 1)
	c.Put("a", 2)

	if got := c.Len(); got != 1 {
		t.Errorf("Len() = %d, want 1 after overwrite", got)
	}
	if got, ok := c.Get("a"); !ok || got != 2 {
		t.Errorf("Get(a) = (%d, %v), want (2, true)", got, ok)
	}
}

func TestLRUEviction(t *testing.T) {
	c := New[string, int](2, time.Minute)
	c.Put("a", 1)
	c.Put("b", 2)
	c.Put("c", 3) // evicts "a", the least recently used

	tests := []struct {
		key     string
		wantOK  bool
		wantVal int
	}{
		{"a", false, 0},
		{"b", true, 2},
		{"c", true, 3},
	}
	for _, tt := range tests {
		got, ok := c.Get(tt.key)
		if ok != tt.wantOK || got != tt.wantVal {
			t.Errorf("Get(%q) = (%d, %v), want (%d, %v)", tt.key, got, ok, tt.wantVal, tt.wantOK)
		}
	}
}

func TestGetRefreshesRecency(t *testing.T) {
	c := New[string, int](2, time.Minute)
	c.Put("a", 1)
	c.Put("b", 2)

	// Touch "a" so "b" becomes least recently used.
	if _, ok := c.Get("a"); !ok {
		t.Fatalf("Get(a) = false, want true")
	}

	c.Put("c", 3) // should evict "b", not "a"

	if _, ok := c.Get("b"); ok {
		t.Errorf("expected b to be evicted")
	}
	if _, ok := c.Get("a"); !ok {
		t.Errorf("expected a to survive eviction")
	}
}

func TestLazyExpiry(t *testing.T) {
	fc := &fakeClock{t: time.Unix(0, 0)}
	c := newWithClock[string, int](4, 10*time.Second, fc)

	c.Put("a", 1)

	fc.Advance(5 * time.Second)
	if got, ok := c.Get("a"); !ok || got != 1 {
		t.Fatalf("Get(a) before expiry = (%d, %v), want (1, true)", got, ok)
	}

	fc.Advance(10 * time.Second) // now past the 10s TTL from insertion
	if _, ok := c.Get("a"); ok {
		t.Errorf("Get(a) after expiry = true, want false")
	}

	// Lazy expiry removed it from the underlying store.
	if got := c.Len(); got != 0 {
		t.Errorf("Len() after expired read = %d, want 0", got)
	}
}

func TestExpiryBoundaryIsInclusive(t *testing.T) {
	fc := &fakeClock{t: time.Unix(0, 0)}
	c := newWithClock[string, int](2, time.Second, fc)
	c.Put("a", 1)

	fc.Advance(time.Second) // exactly at expiry instant
	if _, ok := c.Get("a"); ok {
		t.Errorf("entry should be expired at exactly its TTL boundary")
	}
}

func TestPutRefreshesTTL(t *testing.T) {
	fc := &fakeClock{t: time.Unix(0, 0)}
	c := newWithClock[string, int](2, 10*time.Second, fc)

	c.Put("a", 1)
	fc.Advance(8 * time.Second)
	c.Put("a", 2) // re-arms TTL to t=18s

	fc.Advance(5 * time.Second) // t=13s, still alive
	if got, ok := c.Get("a"); !ok || got != 2 {
		t.Errorf("Get(a) = (%d, %v), want (2, true) after TTL refresh", got, ok)
	}
}

func TestZeroTTLNeverExpires(t *testing.T) {
	fc := &fakeClock{t: time.Unix(0, 0)}
	c := newWithClock[string, int](2, 0, fc)

	c.Put("a", 1)
	fc.Advance(1000 * time.Hour)
	if got, ok := c.Get("a"); !ok || got != 1 {
		t.Errorf("Get(a) = (%d, %v), want (1, true) with TTL disabled", got, ok)
	}
}

func TestNewPanicsOnNonPositiveCapacity(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Errorf("New with capacity 0 did not panic")
		}
	}()
	_ = New[string, int](0, time.Minute)
}
