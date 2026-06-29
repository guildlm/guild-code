package pagerepo

import (
	"reflect"
	"sync"
	"testing"
)

type person struct {
	Name string
	Age  int
}

func byAgeAsc(a, b person) bool { return a.Age < b.Age }

func names(ps []person) []string {
	out := make([]string, len(ps))
	for i, p := range ps {
		out[i] = p.Name
	}
	return out
}

func sampleRepo() *Repository[person] {
	r := New[person]()
	r.Add(person{"Carol", 30})
	r.Add(person{"Alice", 25})
	r.Add(person{"Dave", 40})
	r.Add(person{"Bob", 25})
	r.Add(person{"Eve", 35})
	return r
}

func TestQuery(t *testing.T) {
	tests := []struct {
		name     string
		filter   func(person) bool
		sortLess func(a, b person) bool
		page     int
		size     int
		want     []string
	}{
		{
			name:     "first page sorted by age",
			sortLess: byAgeAsc,
			page:     1,
			size:     2,
			want:     []string{"Alice", "Bob"}, // both 25, stable: Alice added first
		},
		{
			name:     "second page sorted by age",
			sortLess: byAgeAsc,
			page:     2,
			size:     2,
			want:     []string{"Carol", "Eve"},
		},
		{
			name:     "last partial page",
			sortLess: byAgeAsc,
			page:     3,
			size:     2,
			want:     []string{"Dave"},
		},
		{
			name:     "page beyond data returns empty",
			sortLess: byAgeAsc,
			page:     4,
			size:     2,
			want:     []string{},
		},
		{
			name: "nil filter and nil sort preserves insertion order",
			page: 1,
			size: 3,
			want: []string{"Carol", "Alice", "Dave"},
		},
		{
			name:     "filter then sort",
			filter:   func(p person) bool { return p.Age >= 30 },
			sortLess: byAgeAsc,
			page:     1,
			size:     10,
			want:     []string{"Carol", "Eve", "Dave"},
		},
		{
			name:     "filter matches nothing",
			filter:   func(p person) bool { return p.Age > 100 },
			sortLess: byAgeAsc,
			page:     1,
			size:     10,
			want:     []string{},
		},
		{
			name:     "size larger than result returns all",
			sortLess: byAgeAsc,
			page:     1,
			size:     100,
			want:     []string{"Alice", "Bob", "Carol", "Eve", "Dave"},
		},
		{
			name:     "zero page is out of range",
			sortLess: byAgeAsc,
			page:     0,
			size:     2,
			want:     []string{},
		},
		{
			name:     "negative page is out of range",
			sortLess: byAgeAsc,
			page:     -1,
			size:     2,
			want:     []string{},
		},
		{
			name:     "zero size is out of range",
			sortLess: byAgeAsc,
			page:     1,
			size:     0,
			want:     []string{},
		},
		{
			name:     "negative size is out of range",
			sortLess: byAgeAsc,
			page:     1,
			size:     -5,
			want:     []string{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := sampleRepo()
			got := names(r.Query(tt.filter, tt.sortLess, tt.page, tt.size))
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("Query() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestQueryNeverReturnsNil(t *testing.T) {
	r := New[person]()
	got := r.Query(nil, nil, 1, 10)
	if got == nil {
		t.Fatal("Query() returned nil; want non-nil empty slice")
	}
	if len(got) != 0 {
		t.Errorf("Query() len = %d, want 0", len(got))
	}
}

func TestQueryReturnsCopy(t *testing.T) {
	r := New[person]()
	r.Add(person{"Alice", 25})
	r.Add(person{"Bob", 30})

	got := r.Query(nil, byAgeAsc, 1, 10)
	if len(got) != 2 {
		t.Fatalf("Query() len = %d, want 2", len(got))
	}
	// Mutating the returned slice must not affect the repository.
	got[0].Name = "MUTATED"

	again := r.Query(nil, byAgeAsc, 1, 10)
	if again[0].Name != "Alice" {
		t.Errorf("repository data mutated through returned slice: got %q", again[0].Name)
	}
}

func TestLen(t *testing.T) {
	r := New[person]()
	if got := r.Len(); got != 0 {
		t.Fatalf("Len() = %d, want 0", got)
	}
	r.Add(person{"Alice", 25})
	r.Add(person{"Bob", 30})
	if got := r.Len(); got != 2 {
		t.Errorf("Len() = %d, want 2", got)
	}
}

func TestConcurrentAddAndQuery(t *testing.T) {
	r := New[int]()
	var wg sync.WaitGroup
	const writers = 8
	const perWriter = 250

	for w := 0; w < writers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < perWriter; i++ {
				r.Add(i)
			}
		}()
	}
	for g := 0; g < 4; g++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < perWriter; i++ {
				_ = r.Query(func(v int) bool { return v%2 == 0 }, func(a, b int) bool { return a < b }, 1, 10)
			}
		}()
	}
	wg.Wait()

	if got := r.Len(); got != writers*perWriter {
		t.Errorf("Len() = %d, want %d", got, writers*perWriter)
	}
}
