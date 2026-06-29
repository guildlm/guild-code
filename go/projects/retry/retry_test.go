package retry

import (
	"context"
	"errors"
	"testing"
	"time"
)

var errBoom = errors.New("boom")

func TestRetry(t *testing.T) {
	tests := []struct {
		name      string
		attempts  int
		failFirst int // number of leading calls that return an error
		wantCalls int
		wantErr   error
	}{
		{name: "success on first try", attempts: 3, failFirst: 0, wantCalls: 1, wantErr: nil},
		{name: "success after retries", attempts: 5, failFirst: 2, wantCalls: 3, wantErr: nil},
		{name: "all attempts fail", attempts: 3, failFirst: 100, wantCalls: 3, wantErr: errBoom},
		{name: "single attempt fails", attempts: 1, failFirst: 100, wantCalls: 1, wantErr: errBoom},
		{name: "zero attempts", attempts: 0, failFirst: 0, wantCalls: 0, wantErr: ErrNoAttempts},
		{name: "negative attempts", attempts: -3, failFirst: 0, wantCalls: 0, wantErr: ErrNoAttempts},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			calls := 0
			err := Retry(context.Background(), tt.attempts, time.Millisecond, func() error {
				calls++
				if calls <= tt.failFirst {
					return errBoom
				}
				return nil
			})
			if calls != tt.wantCalls {
				t.Errorf("call count = %d, want %d", calls, tt.wantCalls)
			}
			if !errors.Is(err, tt.wantErr) {
				t.Errorf("err = %v, want errors.Is(_, %v)", err, tt.wantErr)
			}
		})
	}
}

func TestRetryContextCanceledDuringBackoff(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	calls := 0
	err := Retry(ctx, 5, time.Hour, func() error {
		calls++
		cancel() // cancel while the first backoff wait is in progress
		return errBoom
	})

	if calls != 1 {
		t.Fatalf("call count = %d, want 1 (must not retry after cancel)", calls)
	}
	if !errors.Is(err, context.Canceled) {
		t.Errorf("err = %v, want it to wrap context.Canceled", err)
	}
	if !errors.Is(err, errBoom) {
		t.Errorf("err = %v, want it to wrap the last fn error", err)
	}
}

func TestRetryContextAlreadyDone(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	calls := 0
	err := Retry(ctx, 3, time.Millisecond, func() error {
		calls++
		return nil
	})

	if calls != 0 {
		t.Errorf("call count = %d, want 0 (fn must not run with a done context)", calls)
	}
	if !errors.Is(err, context.Canceled) {
		t.Errorf("err = %v, want context.Canceled", err)
	}
}

func TestRetryBackoffDoubles(t *testing.T) {
	base := 20 * time.Millisecond
	start := time.Now()
	err := Retry(context.Background(), 3, base, func() error {
		return errBoom
	})
	elapsed := time.Since(start)

	if !errors.Is(err, errBoom) {
		t.Fatalf("err = %v, want errBoom", err)
	}
	// Three failing attempts sleep base + 2*base before giving up.
	if min := 3 * base; elapsed < min {
		t.Errorf("elapsed = %v, want >= %v (delays should double)", elapsed, min)
	}
}

func TestDoReturnsValue(t *testing.T) {
	calls := 0
	got, err := Do(context.Background(), 4, time.Millisecond, func() (int, error) {
		calls++
		if calls < 3 {
			return 0, errBoom
		}
		return 42, nil
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != 42 {
		t.Errorf("value = %d, want 42", got)
	}
	if calls != 3 {
		t.Errorf("call count = %d, want 3", calls)
	}
}

func TestDoReturnsZeroOnFailure(t *testing.T) {
	got, err := Do(context.Background(), 2, time.Millisecond, func() (string, error) {
		return "partial", errBoom
	})
	if !errors.Is(err, errBoom) {
		t.Errorf("err = %v, want errBoom", err)
	}
	if got != "" {
		t.Errorf("value = %q, want zero value", got)
	}
}

func TestNextDelay(t *testing.T) {
	tests := []struct {
		name string
		in   time.Duration
		want time.Duration
	}{
		{name: "doubles", in: time.Second, want: 2 * time.Second},
		{name: "zero stays zero", in: 0, want: 0},
		{name: "negative clamps to zero", in: -time.Second, want: 0},
		{name: "saturates near max", in: maxDelay - 1, want: maxDelay},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := nextDelay(tt.in); got != tt.want {
				t.Errorf("nextDelay(%d) = %d, want %d", tt.in, got, tt.want)
			}
		})
	}
}
