package pool

import (
	"sync"
	"testing"
	"time"
)

func TestNew(t *testing.T) {
	tests := []struct {
		name    string
		items   []string
		wantErr bool
		wantCap int
	}{
		{name: "no items", items: nil, wantErr: true},
		{name: "single item", items: []string{"a"}, wantCap: 1},
		{name: "several items", items: []string{"a", "b", "c"}, wantCap: 3},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			p, err := New(tt.items...)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("New(%v) error = nil, want error", tt.items)
				}
				if p != nil {
					t.Fatalf("New(%v) pool = %v, want nil", tt.items, p)
				}
				return
			}
			if err != nil {
				t.Fatalf("New(%v) unexpected error: %v", tt.items, err)
			}
			if got := p.Cap(); got != tt.wantCap {
				t.Errorf("Cap() = %d, want %d", got, tt.wantCap)
			}
			if got := p.Available(); got != tt.wantCap {
				t.Errorf("Available() = %d, want %d", got, tt.wantCap)
			}
		})
	}
}

func TestTryAcquireExhaustion(t *testing.T) {
	p, err := New(1, 2)
	if err != nil {
		t.Fatalf("New: %v", err)
	}

	// Drain the pool; every checkout should succeed.
	for i := 0; i < p.Cap(); i++ {
		if _, ok := p.TryAcquire(); !ok {
			t.Fatalf("TryAcquire #%d = false, want true while pool has free slots", i)
		}
	}
	if got := p.Available(); got != 0 {
		t.Errorf("Available() after draining = %d, want 0", got)
	}

	// Empty pool: non-blocking acquire must fail and yield the zero value.
	got, ok := p.TryAcquire()
	if ok {
		t.Errorf("TryAcquire() on empty pool = (%d, true), want (_, false)", got)
	}
	if got != 0 {
		t.Errorf("TryAcquire() zero value = %d, want 0", got)
	}

	// Returning a resource makes a slot available again.
	p.Release(42)
	if got := p.Available(); got != 1 {
		t.Fatalf("Available() after Release = %d, want 1", got)
	}
	if v, ok := p.TryAcquire(); !ok || v != 42 {
		t.Errorf("TryAcquire() after Release = (%d, %v), want (42, true)", v, ok)
	}
}

func TestAcquireReleaseRoundTrip(t *testing.T) {
	p, err := New("x", "y")
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	a := p.Acquire()
	b := p.Acquire()
	if a == b {
		t.Fatalf("Acquire returned the same resource twice: %q", a)
	}
	if got := p.Available(); got != 0 {
		t.Errorf("Available() = %d, want 0", got)
	}
	p.Release(a)
	p.Release(b)
	if got := p.Available(); got != p.Cap() {
		t.Errorf("Available() after releasing all = %d, want %d", got, p.Cap())
	}
}

func TestAcquireBlocksUntilRelease(t *testing.T) {
	p, err := New(7)
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	first := p.Acquire() // pool now empty

	acquired := make(chan int, 1)
	go func() {
		acquired <- p.Acquire() // must block until the Release below
	}()

	select {
	case v := <-acquired:
		t.Fatalf("Acquire returned %d while pool was empty; expected it to block", v)
	case <-time.After(50 * time.Millisecond):
		// Still blocked, as required.
	}

	p.Release(first)

	select {
	case v := <-acquired:
		if v != 7 {
			t.Errorf("blocked Acquire returned %d, want 7", v)
		}
	case <-time.After(time.Second):
		t.Fatal("Acquire did not unblock after Release")
	}
}

func TestSemaphore(t *testing.T) {
	tests := []struct {
		name     string
		capacity int
	}{
		{name: "capacity one", capacity: 1},
		{name: "capacity three", capacity: 3},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := NewSemaphore(tt.capacity)
			if got := s.Cap(); got != tt.capacity {
				t.Fatalf("Cap() = %d, want %d", got, tt.capacity)
			}
			// Fill every slot.
			for i := 0; i < tt.capacity; i++ {
				if !s.TryAcquire() {
					t.Fatalf("TryAcquire #%d = false, want true", i)
				}
				if got := s.Len(); got != i+1 {
					t.Errorf("Len() = %d, want %d", got, i+1)
				}
			}
			// Full: further non-blocking acquires must fail.
			if s.TryAcquire() {
				t.Errorf("TryAcquire() on full semaphore = true, want false")
			}
			// Release frees exactly one slot.
			s.Release()
			if got := s.Len(); got != tt.capacity-1 {
				t.Errorf("Len() after Release = %d, want %d", got, tt.capacity-1)
			}
			if !s.TryAcquire() {
				t.Errorf("TryAcquire() after Release = false, want true")
			}
		})
	}
}

func TestNewSemaphorePanicsOnNonPositive(t *testing.T) {
	tests := []struct {
		name     string
		capacity int
	}{
		{name: "zero", capacity: 0},
		{name: "negative", capacity: -3},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			defer func() {
				if recover() == nil {
					t.Errorf("NewSemaphore(%d) did not panic", tt.capacity)
				}
			}()
			NewSemaphore(tt.capacity)
		})
	}
}

func TestSemaphoreBoundsConcurrency(t *testing.T) {
	const capacity = 4
	const workers = 64
	s := NewSemaphore(capacity)

	var mu sync.Mutex
	var inFlight, maxInFlight int

	var wg sync.WaitGroup
	wg.Add(workers)
	for i := 0; i < workers; i++ {
		go func() {
			defer wg.Done()
			s.Acquire()
			defer s.Release()

			mu.Lock()
			inFlight++
			if inFlight > maxInFlight {
				maxInFlight = inFlight
			}
			mu.Unlock()

			mu.Lock()
			inFlight--
			mu.Unlock()
		}()
	}
	wg.Wait()

	if maxInFlight > capacity {
		t.Errorf("max concurrent holders = %d, want <= %d", maxInFlight, capacity)
	}
	if got := s.Len(); got != 0 {
		t.Errorf("Len() after all released = %d, want 0", got)
	}
}
