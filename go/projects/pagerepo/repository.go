// Package pagerepo provides a concurrency-safe, in-memory repository of
// records with filtered, sorted, and paginated querying.
package pagerepo

import (
	"sort"
	"sync"
)

// Repository is a concurrency-safe, in-memory collection of records of type R.
// The zero value is not ready for use; call New.
type Repository[R any] struct {
	mu    sync.RWMutex
	items []R
}

// New returns an empty Repository ready for use.
func New[R any]() *Repository[R] {
	return &Repository[R]{}
}

// Add appends a record to the repository. It is safe for concurrent use.
func (r *Repository[R]) Add(item R) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.items = append(r.items, item)
}

// Len reports the number of records currently stored.
func (r *Repository[R]) Len() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.items)
}

// Query returns a single page of records.
//
// The records are first filtered with filter (a nil filter keeps every
// record), then ordered with sortLess (a nil sortLess preserves insertion
// order), and finally the page-th page of the given size is returned.
//
// Pages are 1-based: page 1 is the first page. A page or size that is out of
// range, or a page that lies beyond the available data, yields a non-nil,
// empty slice. The returned slice is a fresh copy and never aliases the
// repository's internal storage.
func (r *Repository[R]) Query(filter func(R) bool, sortLess func(a, b R) bool, page, size int) []R {
	if page < 1 || size < 1 {
		return []R{}
	}

	r.mu.RLock()
	matched := make([]R, 0, len(r.items))
	for _, item := range r.items {
		if filter == nil || filter(item) {
			matched = append(matched, item)
		}
	}
	r.mu.RUnlock()

	if sortLess != nil {
		sort.SliceStable(matched, func(i, j int) bool {
			return sortLess(matched[i], matched[j])
		})
	}

	start := (page - 1) * size
	if start >= len(matched) {
		return []R{}
	}
	end := start + size
	if end > len(matched) {
		end = len(matched)
	}

	out := make([]R, end-start)
	copy(out, matched[start:end])
	return out
}
