package retry

import (
	"math"
	"time"
)

// maxDelay is the largest representable backoff delay. It is used to clamp the
// doubling so the delay never overflows into a negative duration.
const maxDelay = time.Duration(math.MaxInt64)

// nextDelay doubles d, saturating at maxDelay and never returning a value below
// zero. A non-positive d (e.g. a zero base) yields immediate retries.
func nextDelay(d time.Duration) time.Duration {
	if d <= 0 {
		return 0
	}
	if d > maxDelay/2 {
		return maxDelay
	}
	return d * 2
}
