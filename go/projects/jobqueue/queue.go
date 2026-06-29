package jobqueue

import (
	"errors"
	"sync"
)

// Job is a single unit of work executed by a worker goroutine.
type Job func()

var (
	// ErrClosed is returned by Submit after the queue has been shut down.
	ErrClosed = errors.New("jobqueue: queue is closed")
	// ErrNilJob is returned by Submit when the supplied job is nil.
	ErrNilJob = errors.New("jobqueue: nil job")
)

// Queue is an in-memory job queue served by a fixed-size worker pool.
//
// Submit enqueues work; the workers run it concurrently. Shutdown drains
// the queue and blocks until every accepted job has finished.
type Queue struct {
	jobs chan Job
	wg   sync.WaitGroup

	mu     sync.RWMutex // guards closed and the close of jobs
	closed bool
}

// New starts a Queue with the given number of workers and channel buffer.
//
// workers is clamped to a minimum of 1 and buffer to a minimum of 0, so
// callers never have to special-case degenerate inputs.
func New(workers, buffer int) *Queue {
	if workers < 1 {
		workers = 1
	}
	if buffer < 0 {
		buffer = 0
	}

	q := &Queue{
		jobs: make(chan Job, buffer),
	}

	q.wg.Add(workers)
	for i := 0; i < workers; i++ {
		go q.worker()
	}
	return q
}

// worker pulls jobs until the channel is closed and drained.
func (q *Queue) worker() {
	defer q.wg.Done()
	for job := range q.jobs {
		job()
	}
}

// Submit enqueues job for execution. It blocks while the buffer is full
// and unblocks as soon as a worker is free. It returns ErrNilJob for a nil
// job and ErrClosed once the queue has been shut down.
func (q *Queue) Submit(job Job) error {
	if job == nil {
		return ErrNilJob
	}

	// Hold the read lock across the send. Shutdown closes the channel only
	// under the exclusive write lock, which it cannot acquire while any send
	// is in flight, so a send on a closed channel can never happen here.
	q.mu.RLock()
	defer q.mu.RUnlock()

	if q.closed {
		return ErrClosed
	}
	q.jobs <- job
	return nil
}

// Shutdown stops accepting new work, lets the workers drain every job that
// was already accepted, and blocks until they all return. It is safe to call
// Shutdown more than once and from multiple goroutines.
func (q *Queue) Shutdown() {
	q.mu.Lock()
	if q.closed {
		q.mu.Unlock()
		q.wg.Wait()
		return
	}
	q.closed = true
	close(q.jobs)
	q.mu.Unlock()

	q.wg.Wait()
}
