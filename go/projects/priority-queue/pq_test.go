package pq

import "testing"

func TestPushPopOrder(t *testing.T) {
	tests := []struct {
		name  string
		input []struct {
			item     string
			priority int
		}
		want []string
	}{
		{
			name: "ascending priorities",
			input: []struct {
				item     string
				priority int
			}{
				{"a", 1}, {"b", 2}, {"c", 3},
			},
			want: []string{"a", "b", "c"},
		},
		{
			name: "out of order insert",
			input: []struct {
				item     string
				priority int
			}{
				{"c", 3}, {"a", 1}, {"b", 2},
			},
			want: []string{"a", "b", "c"},
		},
		{
			name: "negative priorities",
			input: []struct {
				item     string
				priority int
			}{
				{"low", -5}, {"mid", 0}, {"high", 10},
			},
			want: []string{"low", "mid", "high"},
		},
		{
			name: "single element",
			input: []struct {
				item     string
				priority int
			}{
				{"only", 42},
			},
			want: []string{"only"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			q := New[string]()
			for _, in := range tt.input {
				q.Push(in.item, in.priority)
			}
			if got := q.Len(); got != len(tt.want) {
				t.Fatalf("Len() = %d, want %d", got, len(tt.want))
			}
			var got []string
			for q.Len() > 0 {
				v, ok := q.Pop()
				if !ok {
					t.Fatalf("Pop() returned ok=false with Len()=%d", q.Len())
				}
				got = append(got, v)
			}
			if len(got) != len(tt.want) {
				t.Fatalf("popped %d items, want %d", len(got), len(tt.want))
			}
			for i := range tt.want {
				if got[i] != tt.want[i] {
					t.Errorf("position %d = %q, want %q", i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestPopEmpty(t *testing.T) {
	q := New[int]()
	v, ok := q.Pop()
	if ok {
		t.Fatalf("Pop() on empty queue returned ok=true, value=%d", v)
	}
	if v != 0 {
		t.Errorf("Pop() on empty queue returned value=%d, want zero value 0", v)
	}
	if q.Len() != 0 {
		t.Errorf("Len() = %d on empty queue, want 0", q.Len())
	}
}

func TestStableForEqualPriorities(t *testing.T) {
	q := New[string]()
	// All share the same priority; insertion order must be preserved.
	order := []string{"first", "second", "third", "fourth"}
	for _, s := range order {
		q.Push(s, 7)
	}
	for i, want := range order {
		got, ok := q.Pop()
		if !ok {
			t.Fatalf("Pop() #%d returned ok=false", i)
		}
		if got != want {
			t.Errorf("FIFO tie-break: position %d = %q, want %q", i, got, want)
		}
	}
}

func TestInterleavedPushPop(t *testing.T) {
	q := New[int]()
	q.Push(5, 5)
	q.Push(1, 1)
	if v, _ := q.Pop(); v != 1 {
		t.Fatalf("after pushing 1,5 expected pop 1, got %d", v)
	}
	q.Push(3, 3)
	q.Push(2, 2)
	want := []int{2, 3, 5}
	for i, w := range want {
		v, ok := q.Pop()
		if !ok {
			t.Fatalf("Pop() #%d ok=false", i)
		}
		if v != w {
			t.Errorf("interleaved position %d = %d, want %d", i, v, w)
		}
	}
	if q.Len() != 0 {
		t.Errorf("final Len() = %d, want 0", q.Len())
	}
}
