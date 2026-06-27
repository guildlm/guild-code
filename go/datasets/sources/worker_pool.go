// Package pool implements a bounded worker pool over channels.
//
// It demonstrates idiomatic Go concurrency: a fixed number of worker goroutines
// draining a jobs channel, a WaitGroup to await completion, and a results
// channel closed exactly once all work is done.
package pool

import "sync"

// Job is a unit of work: it maps an input integer to an output integer.
type Job func(int) int

// Run fans `inputs` out across `workers` goroutines applying `job` to each, and
// returns the collected results. Order of results is not guaranteed.
func Run(workers int, inputs []int, job Job) []int {
	if workers < 1 {
		workers = 1
	}

	jobs := make(chan int)
	results := make(chan int)

	var wg sync.WaitGroup
	wg.Add(workers)
	for i := 0; i < workers; i++ {
		go func() {
			defer wg.Done()
			for n := range jobs {
				results <- job(n)
			}
		}()
	}

	go func() {
		for _, n := range inputs {
			jobs <- n
		}
		close(jobs)
	}()

	go func() {
		wg.Wait()
		close(results)
	}()

	out := make([]int, 0, len(inputs))
	for r := range results {
		out = append(out, r)
	}
	return out
}
