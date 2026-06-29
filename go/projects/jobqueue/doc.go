// Package jobqueue provides a small in-memory job queue backed by a
// fixed-size pool of worker goroutines.
//
// A Queue is created with New, which starts the requested number of
// workers. Work is submitted with Submit and runs concurrently across
// the pool. Shutdown stops accepting new work, drains every job that
// was already buffered, waits for the workers to finish, and returns.
//
// The zero value of Queue is not usable; always construct one with New.
// A Queue is safe for concurrent use by multiple goroutines.
package jobqueue
