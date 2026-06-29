package ttlcache

import (
	"sync"
	"testing"
	"time"
)

// newTestCache returns a Cache wired to a controllable clock. The returned
// advance func moves the clock forward so expiry can be tested without real
// sleeps.
func newTestCache() (c *Cache, advance func(time.Duration)) {
	var (
		mu  sync.Mutex
		now = time.Unix(0, 0)
	)
	c = New()
	c.now = func() time.Time {
		mu.Lock()
		defer mu.Unlock()
		return now
	}
	advance = func(d time.Duration) {
		mu.Lock()
		defer mu.Unlock()
		now = now.Add(d)
	}
	return c, advance
}

func TestGetSet(t *testing.T) {
	type step struct {
		advance time.Duration // advance the clock before this step
		set     bool          // perform a Set in this step
		key     string
		value   any
		ttl     time.Duration
		get     bool // perform a Get assertion in this step
		wantVal any
		wantOK  bool
	}

	tests := []struct {
		name  string
		steps []step
	}{
		{
			name: "missing key reports not ok",
			steps: []step{
				{get: true, key: "nope", wantVal: nil, wantOK: false},
			},
		},
		{
			name: "set then get before expiry",
			steps: []step{
				{set: true, key: "a", value: 1, ttl: 10 * time.Second},
				{advance: 5 * time.Second},
				{get: true, key: "a", wantVal: 1, wantOK: true},
			},
		},
		{
			name: "entry expires exactly at deadline",
			steps: []step{
				{set: true, key: "a", value: "v", ttl: 10 * time.Second},
				{advance: 10 * time.Second},
				{get: true, key: "a", wantVal: nil, wantOK: false},
			},
		},
		{
			name: "entry alive one tick before deadline",
			steps: []step{
				{set: true, key: "a", value: "v", ttl: 10 * time.Second},
				{advance: 10*time.Second - time.Nanosecond},
				{get: true, key: "a", wantVal: "v", wantOK: true},
			},
		},
		{
			name: "zero ttl never expires",
			steps: []step{
				{set: true, key: "forever", value: 42, ttl: 0},
				{advance: 1000 * time.Hour},
				{get: true, key: "forever", wantVal: 42, wantOK: true},
			},
		},
		{
			name: "negative ttl never expires",
			steps: []step{
				{set: true, key: "forever", value: 42, ttl: -1},
				{advance: 1000 * time.Hour},
				{get: true, key: "forever", wantVal: 42, wantOK: true},
			},
		},
		{
			name: "overwrite refreshes ttl and value",
			steps: []step{
				{set: true, key: "a", value: 1, ttl: 10 * time.Second},
				{advance: 8 * time.Second},
				{set: true, key: "a", value: 2, ttl: 10 * time.Second},
				{advance: 8 * time.Second}, // 16s since first set, 8s since second
				{get: true, key: "a", wantVal: 2, wantOK: true},
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c, advance := newTestCache()
			for i, s := range tt.steps {
				if s.advance != 0 {
					advance(s.advance)
				}
				if s.set {
					c.Set(s.key, s.value, s.ttl)
				}
				if s.get {
					gotVal, gotOK := c.Get(s.key)
					if gotOK != s.wantOK {
						t.Fatalf("step %d Get(%q) ok = %v, want %v", i, s.key, gotOK, s.wantOK)
					}
					if gotVal != s.wantVal {
						t.Errorf("step %d Get(%q) val = %v, want %v", i, s.key, gotVal, s.wantVal)
					}
				}
			}
		})
	}
}

func TestExpiredGetPurges(t *testing.T) {
	c, advance := newTestCache()
	c.Set("a", 1, 5*time.Second)
	if got := c.Len(); got != 1 {
		t.Fatalf("Len before expiry = %d, want 1", got)
	}
	advance(5 * time.Second)

	// Len must not count the expired entry...
	if got := c.Len(); got != 0 {
		t.Errorf("Len after expiry = %d, want 0", got)
	}
	// ...and the failed Get must physically delete it.
	if _, ok := c.Get("a"); ok {
		t.Fatal("Get returned ok for expired key")
	}
	if _, present := c.items["a"]; present {
		t.Error("expired key was not purged from the underlying map")
	}
}

func TestDelete(t *testing.T) {
	c, _ := newTestCache()
	c.Set("a", 1, time.Minute)
	c.Delete("a")
	if _, ok := c.Get("a"); ok {
		t.Error("Get returned ok after Delete")
	}
	c.Delete("a") // deleting absent key must not panic
}

func TestConcurrentAccess(t *testing.T) {
	c := New()
	const workers = 16
	var wg sync.WaitGroup
	wg.Add(workers)
	for w := 0; w < workers; w++ {
		go func(id int) {
			defer wg.Done()
			key := "k"
			for i := 0; i < 1000; i++ {
				c.Set(key, id, time.Millisecond)
				c.Get(key)
				c.Len()
				c.Delete(key)
			}
		}(w)
	}
	wg.Wait()
}
