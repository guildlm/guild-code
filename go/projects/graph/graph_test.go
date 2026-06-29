package graph

import (
	"reflect"
	"testing"
)

// edge is a single directed edge used to build a graph fixture.
type edge struct{ a, b int }

func build(edges []edge) *Graph {
	g := New()
	for _, e := range edges {
		g.AddEdge(e.a, e.b)
	}
	return g
}

func TestShortestPath(t *testing.T) {
	// A diamond plus a long tail:
	//   0 -> 1 -> 3 -> 4
	//   0 -> 2 -> 3
	// and an isolated component 5 -> 6.
	edges := []edge{
		{0, 1}, {0, 2}, {1, 3}, {2, 3}, {3, 4}, {5, 6},
	}

	tests := []struct {
		name     string
		from, to int
		want     []int
		wantOK   bool
	}{
		{"adjacent", 0, 1, []int{0, 1}, true},
		{"two hops via diamond", 0, 3, []int{0, 1, 3}, true},
		{"three hops", 0, 4, []int{0, 1, 3, 4}, true},
		{"same node", 3, 3, []int{3}, true},
		{"unreachable across components", 0, 6, nil, false},
		{"wrong direction", 4, 0, nil, false},
		{"missing source", 99, 0, nil, false},
		{"missing target", 0, 99, nil, false},
		{"isolated edge", 5, 6, []int{5, 6}, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			g := build(edges)
			got, ok := g.ShortestPath(tt.from, tt.to)
			if ok != tt.wantOK {
				t.Fatalf("ShortestPath(%d, %d) ok = %v, want %v", tt.from, tt.to, ok, tt.wantOK)
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("ShortestPath(%d, %d) = %v, want %v", tt.from, tt.to, got, tt.want)
			}
		})
	}
}

// TestShortestPathPicksFewestEdges verifies BFS returns a path with the minimum
// number of edges even when a longer alternative is discovered first.
func TestShortestPathPicksFewestEdges(t *testing.T) {
	// short: 0 -> 1 -> 4 (2 edges); long: 0 -> 2 -> 3 -> 4 (3 edges).
	g := build([]edge{{0, 1}, {1, 4}, {0, 2}, {2, 3}, {3, 4}})

	got, ok := g.ShortestPath(0, 4)
	if !ok {
		t.Fatal("expected a path from 0 to 4")
	}
	want := []int{0, 1, 4}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("ShortestPath(0, 4) = %v, want %v (fewest edges)", got, want)
	}
}

// TestCycleDoesNotLoopForever ensures a cycle does not cause infinite traversal
// and that an unreachable target still terminates with false.
func TestCycleDoesNotLoopForever(t *testing.T) {
	g := build([]edge{{0, 1}, {1, 2}, {2, 0}})

	if got, ok := g.ShortestPath(0, 2); !ok || !reflect.DeepEqual(got, []int{0, 1, 2}) {
		t.Errorf("ShortestPath(0, 2) = %v, %v; want [0 1 2], true", got, ok)
	}
	if got, ok := g.ShortestPath(0, 7); ok || got != nil {
		t.Errorf("ShortestPath(0, 7) = %v, %v; want nil, false", got, ok)
	}
}

// TestSelfLoopNode covers a node with an explicit self-edge.
func TestSelfLoopNode(t *testing.T) {
	g := build([]edge{{1, 1}})

	if got, ok := g.ShortestPath(1, 1); !ok || !reflect.DeepEqual(got, []int{1}) {
		t.Errorf("ShortestPath(1, 1) = %v, %v; want [1], true", got, ok)
	}
}
