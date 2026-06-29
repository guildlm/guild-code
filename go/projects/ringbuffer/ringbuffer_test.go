package ringbuffer

import (
	"errors"
	"reflect"
	"testing"
)

func TestNewPanicsOnNonPositiveCapacity(t *testing.T) {
	for _, capacity := range []int{0, -1, -5} {
		func() {
			defer func() {
				if recover() == nil {
					t.Errorf("New(%d): expected panic, got none", capacity)
				}
			}()
			New[int](capacity)
		}()
	}
}

func TestPopEmpty(t *testing.T) {
	r := New[int](3)
	v, err := r.Pop()
	if !errors.Is(err, ErrEmpty) {
		t.Fatalf("Pop on empty: err = %v, want ErrEmpty", err)
	}
	if v != 0 {
		t.Errorf("Pop on empty: value = %d, want zero", v)
	}
}

func TestPushPopFIFO(t *testing.T) {
	r := New[int](3)
	r.Push(1)
	r.Push(2)
	r.Push(3)
	if got := r.Len(); got != 3 {
		t.Fatalf("Len = %d, want 3", got)
	}
	for _, want := range []int{1, 2, 3} {
		got, err := r.Pop()
		if err != nil {
			t.Fatalf("Pop: unexpected error %v", err)
		}
		if got != want {
			t.Errorf("Pop = %d, want %d", got, want)
		}
	}
	if got := r.Len(); got != 0 {
		t.Errorf("Len after draining = %d, want 0", got)
	}
}

func TestPushOverwritesOldest(t *testing.T) {
	r := New[int](3)
	r.Push(1)
	r.Push(2)
	r.Push(3)
	r.Push(4) // overwrites 1
	r.Push(5) // overwrites 2
	if got, want := r.Len(), 3; got != want {
		t.Fatalf("Len = %d, want %d", got, want)
	}
	if got, want := r.ToSlice(), []int{3, 4, 5}; !reflect.DeepEqual(got, want) {
		t.Fatalf("ToSlice = %v, want %v", got, want)
	}
}

func TestToSliceLogicalOrderAfterWrap(t *testing.T) {
	r := New[int](4)
	r.Push(10)
	r.Push(20)
	r.Push(30)
	// Pop two so head advances, then push to force wrap-around.
	if _, err := r.Pop(); err != nil { // removes 10
		t.Fatal(err)
	}
	if _, err := r.Pop(); err != nil { // removes 20
		t.Fatal(err)
	}
	r.Push(40)
	r.Push(50)
	r.Push(60) // wraps in underlying array
	if got, want := r.ToSlice(), []int{30, 40, 50, 60}; !reflect.DeepEqual(got, want) {
		t.Fatalf("ToSlice after wrap = %v, want %v", got, want)
	}
}

func TestToSliceEmptyAndCopy(t *testing.T) {
	r := New[int](3)
	if got := r.ToSlice(); len(got) != 0 {
		t.Fatalf("ToSlice on empty: got %v, want empty", got)
	}
	r.Push(7)
	r.Push(8)
	s := r.ToSlice()
	s[0] = 999 // mutating the returned slice must not affect the buffer
	if got, want := r.ToSlice(), []int{7, 8}; !reflect.DeepEqual(got, want) {
		t.Fatalf("ToSlice not a copy: got %v, want %v", got, want)
	}
}

func TestCapAndSingleCapacity(t *testing.T) {
	r := New[int](1)
	if got := r.Cap(); got != 1 {
		t.Fatalf("Cap = %d, want 1", got)
	}
	r.Push(1)
	r.Push(2) // overwrites 1
	if got, want := r.ToSlice(), []int{2}; !reflect.DeepEqual(got, want) {
		t.Fatalf("ToSlice = %v, want %v", got, want)
	}
	v, err := r.Pop()
	if err != nil || v != 2 {
		t.Fatalf("Pop = (%d, %v), want (2, nil)", v, err)
	}
}

func TestInterleavedPushPop(t *testing.T) {
	r := New[int](2)
	r.Push(1)
	r.Push(2)
	if _, err := r.Pop(); err != nil { // remove 1
		t.Fatal(err)
	}
	r.Push(3) // buffer: 2,3
	r.Push(4) // overwrites 2 -> 3,4
	if got, want := r.ToSlice(), []int{3, 4}; !reflect.DeepEqual(got, want) {
		t.Fatalf("ToSlice = %v, want %v", got, want)
	}
}

// Sanity check that the type really is generic over non-int element types.
func TestGenericStrings(t *testing.T) {
	r := New[string](2)
	r.Push("a")
	r.Push("b")
	r.Push("c") // overwrites "a"
	if got, want := r.ToSlice(), []string{"b", "c"}; !reflect.DeepEqual(got, want) {
		t.Fatalf("ToSlice = %v, want %v", got, want)
	}
}
