package jobqueue

import (
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// TestNewClampsArguments verifies that degenerate worker/buffer counts are
// normalised so the queue is always usable.
func TestNewClampsArguments(t *testing.T) {
	tests := []struct {
		name    string
		workers int
		buffer  int
	}{
		{"zero workers", 0, 0},
		{"negative workers", -5, 0},
		{"negative buffer", 1, -3},
		{"normal", 4, 8},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			q := New(tt.workers, tt.buffer)

			var ran atomic.Bool
			done := make(chan struct{})
			if err := q.Submit(func() { ran.Store(true); close(done) }); err != nil {
				t.Fatalf("Submit returned error: %v", err)
			}

			select {
			case <-done:
			case <-time.After(2 * time.Second):
				t.Fatal("job was never executed; queue not usable")
			}
			q.Shutdown()

			if !ran.Load() {
				t.Error("expected job to have run")
			}
		})
	}
}

// TestSubmitRunsAllJobs checks that every submitted job runs exactly once
// across the worker pool, even when there are more jobs than workers.
func TestSubmitRunsAllJobs(t *testing.T) {
	tests := []struct {
		name    string
		workers int
		buffer  int
		jobs    int
	}{
		{"single worker", 1, 0, 100},
		{"more workers than jobs", 16, 4, 5},
		{"buffered", 4, 32, 500},
		{"unbuffered", 8, 0, 200},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			q := New(tt.workers, tt.buffer)

			var counter int64
			for i := 0; i < tt.jobs; i++ {
				if err := q.Submit(func() { atomic.AddInt64(&counter, 1) }); err != nil {
					t.Fatalf("Submit %d returned error: %v", i, err)
				}
			}

			// Shutdown must drain: all accepted jobs run before it returns.
			q.Shutdown()

			if got := atomic.LoadInt64(&counter); got != int64(tt.jobs) {
				t.Errorf("ran %d jobs, want %d", got, tt.jobs)
			}
		})
	}
}

// TestSubmitErrors covers the documented error returns of Submit.
func TestSubmitErrors(t *testing.T) {
	t.Run("nil job", func(t *testing.T) {
		q := New(2, 2)
		defer q.Shutdown()
		if err := q.Submit(nil); err != ErrNilJob {
			t.Errorf("Submit(nil) = %v, want %v", err, ErrNilJob)
		}
	})

	t.Run("after shutdown", func(t *testing.T) {
		q := New(2, 2)
		q.Shutdown()
		if err := q.Submit(func() {}); err != ErrClosed {
			t.Errorf("Submit after Shutdown = %v, want %v", err, ErrClosed)
		}
	})
}

// TestShutdownIsIdempotent verifies Shutdown may be called repeatedly and
// concurrently without panicking or blocking forever.
func TestShutdownIsIdempotent(t *testing.T) {
	q := New(3, 4)

	var counter int64
	for i := 0; i < 50; i++ {
		if err := q.Submit(func() { atomic.AddInt64(&counter, 1) }); err != nil {
			t.Fatalf("Submit returned error: %v", err)
		}
	}

	var wg sync.WaitGroup
	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			q.Shutdown()
		}()
	}

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("concurrent Shutdown calls deadlocked")
	}

	if got := atomic.LoadInt64(&counter); got != 50 {
		t.Errorf("drained %d jobs, want 50", got)
	}
}

// TestConcurrentSubmitAndShutdown stresses the lock that protects the channel
// close: many producers submit while another goroutine shuts the queue down.
// Submit must either succeed or return ErrClosed, never panic.
func TestConcurrentSubmitAndShutdown(t *testing.T) {
	q := New(4, 16)

	var accepted, rejected int64
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 100; j++ {
				switch err := q.Submit(func() {}); err {
				case nil:
					atomic.AddInt64(&accepted, 1)
				case ErrClosed:
					atomic.AddInt64(&rejected, 1)
				default:
					t.Errorf("unexpected Submit error: %v", err)
					return
				}
			}
		}()
	}

	time.Sleep(1 * time.Millisecond)
	q.Shutdown()
	wg.Wait()

	if total := accepted + rejected; total != 800 {
		t.Errorf("accounted for %d submits, want 800", total)
	}
}
