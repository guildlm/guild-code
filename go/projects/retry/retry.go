// Package retry provides helpers to retry an operation with exponential
// backoff while honouring context cancellation.
package retry

import (
	"context"
	"errors"
	"time"
)

// ErrNoAttempts is returned when Retry or Do is called with attempts <= 0.
var ErrNoAttempts = errors.New("retry: attempts must be greater than zero")

// Retry calls fn up to attempts times, sleeping between failed attempts for an
// exponentially increasing delay (base, 2*base, 4*base, ...). It returns nil as
// soon as fn succeeds, or the last error from fn once attempts are exhausted.
//
// Retry honours ctx: if ctx is done before an attempt, or while waiting between
// attempts, Retry stops early and returns the joined value of the last fn error
// (if any) and ctx.Err(). If attempts <= 0, Retry returns ErrNoAttempts without
// calling fn.
func Retry(ctx context.Context, attempts int, base time.Duration, fn func() error) error {
	_, err := Do(ctx, attempts, base, func() (struct{}, error) {
		return struct{}{}, fn()
	})
	return err
}

// Do is the value-returning form of Retry. It calls fn up to attempts times and
// returns the first successful value. On failure it returns the zero value of T
// together with the error, following the same backoff and cancellation rules as
// Retry.
func Do[T any](ctx context.Context, attempts int, base time.Duration, fn func() (T, error)) (T, error) {
	var zero T
	if attempts <= 0 {
		return zero, ErrNoAttempts
	}

	var lastErr error
	delay := base
	for i := 0; i < attempts; i++ {
		// Stop before attempting if the context is already done.
		if err := ctx.Err(); err != nil {
			return zero, errors.Join(lastErr, err)
		}

		val, err := fn()
		if err == nil {
			return val, nil
		}
		lastErr = err

		// Do not sleep after the final attempt.
		if i == attempts-1 {
			break
		}

		// Wait for the backoff delay or context cancellation.
		timer := time.NewTimer(delay)
		select {
		case <-ctx.Done():
			timer.Stop()
			return zero, errors.Join(lastErr, ctx.Err())
		case <-timer.C:
		}
		delay = nextDelay(delay)
	}
	return zero, lastErr
}
