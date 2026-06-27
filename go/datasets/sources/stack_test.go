// Package stack provides a tiny generic LIFO stack and a table-driven test that
// exercises its push/pop/peek behaviour, including the empty-stack edge case.
package stack

import "testing"

// Stack is a last-in, first-out collection of T.
type Stack[T any] struct {
	items []T
}

// Push appends v to the top of the stack.
func (s *Stack[T]) Push(v T) { s.items = append(s.items, v) }

// Pop removes and returns the top element; ok is false when the stack is empty.
func (s *Stack[T]) Pop() (v T, ok bool) {
	if len(s.items) == 0 {
		return v, false
	}
	last := len(s.items) - 1
	v = s.items[last]
	s.items = s.items[:last]
	return v, true
}

// Len reports the number of elements on the stack.
func (s *Stack[T]) Len() int { return len(s.items) }

func TestStack(t *testing.T) {
	tests := []struct {
		name    string
		pushes  []int
		pops    int
		wantTop int
		wantOK  bool
	}{
		{name: "single", pushes: []int{42}, pops: 1, wantTop: 42, wantOK: true},
		{name: "lifo order", pushes: []int{1, 2, 3}, pops: 1, wantTop: 3, wantOK: true},
		{name: "empty pop", pushes: nil, pops: 1, wantTop: 0, wantOK: false},
		{name: "over pop", pushes: []int{7}, pops: 2, wantTop: 0, wantOK: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var s Stack[int]
			for _, v := range tt.pushes {
				s.Push(v)
			}
			var got int
			var ok bool
			for i := 0; i < tt.pops; i++ {
				got, ok = s.Pop()
			}
			if ok != tt.wantOK {
				t.Fatalf("ok = %v, want %v", ok, tt.wantOK)
			}
			if ok && got != tt.wantTop {
				t.Errorf("top = %d, want %d", got, tt.wantTop)
			}
		})
	}
}
