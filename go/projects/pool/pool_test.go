package pool

import (
	"sync"
	"testing"
)

func TestNewPanicsOnNilFactory(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("New(nil) did not panic")
		}
	}()
	_ = New[int](nil)
}

func TestGetCreatesWhenEmpty(t *testing.T) {
	calls := 0
	p := New(func() int {
		calls++
		return 42
	})

	tests := []struct {
		name      string
		wantValue int
		wantCalls int
	}{
		{name: "first get creates", wantValue: 42, wantCalls: 1},
		{name: "second get creates again", wantValue: 42, wantCalls: 2},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := p.Get()
			if got != tt.wantValue {
				t.Errorf("Get() = %d, want %d", got, tt.wantValue)
			}
			if calls != tt.wantCalls {
				t.Errorf("factory calls = %d, want %d", calls, tt.wantCalls)
			}
		})
	}
}

func TestPutThenGetReuses(t *testing.T) {
	calls := 0
	p := New(func() *int {
		calls++
		v := 0
		return &v
	})

	a := p.Get() // factory call 1
	if calls != 1 {
		t.Fatalf("after first Get, calls = %d, want 1", calls)
	}
	p.Put(a)
	b := p.Get() // should reuse, no new factory call
	if calls != 1 {
		t.Errorf("after reuse Get, calls = %d, want 1", calls)
	}
	if a != b {
		t.Errorf("Get did not reuse the returned value: got %p, want %p", b, a)
	}
}

func TestLenTracksIdleValues(t *testing.T) {
	p := New(func() int { return 7 })

	tests := []struct {
		name    string
		op      func()
		wantLen int
	}{
		{name: "empty pool", op: func() {}, wantLen: 0},
		{name: "after one put", op: func() { p.Put(1) }, wantLen: 1},
		{name: "after second put", op: func() { p.Put(2) }, wantLen: 2},
		{name: "after one get", op: func() { _ = p.Get() }, wantLen: 1},
		{name: "after draining get", op: func() { _ = p.Get() }, wantLen: 0},
		{name: "get on empty does not go negative", op: func() { _ = p.Get() }, wantLen: 0},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tt.op()
			if got := p.Len(); got != tt.wantLen {
				t.Errorf("Len() = %d, want %d", got, tt.wantLen)
			}
		})
	}
}

func TestGetReusesLIFO(t *testing.T) {
	p := New(func() string { return "new" })
	p.Put("first")
	p.Put("second")

	if got := p.Get(); got != "second" {
		t.Errorf("Get() = %q, want %q (LIFO)", got, "second")
	}
	if got := p.Get(); got != "first" {
		t.Errorf("Get() = %q, want %q (LIFO)", got, "first")
	}
	if got := p.Get(); got != "new" {
		t.Errorf("Get() = %q, want %q (factory after drain)", got, "new")
	}
}

func TestConcurrentUse(t *testing.T) {
	p := New(func() int { return 0 })

	const goroutines = 50
	const iterations = 1000

	var wg sync.WaitGroup
	wg.Add(goroutines)
	for i := 0; i < goroutines; i++ {
		go func() {
			defer wg.Done()
			for j := 0; j < iterations; j++ {
				v := p.Get()
				p.Put(v)
			}
		}()
	}
	wg.Wait()

	// Every Get is balanced by a Put, so the pool must never report a
	// negative or absurd length; it should hold at most one value per
	// goroutine that happened to Put last.
	if got := p.Len(); got < 0 || got > goroutines {
		t.Errorf("Len() after concurrent use = %d, want in [0,%d]", got, goroutines)
	}
}
