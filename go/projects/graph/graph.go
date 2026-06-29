// Package graph implements a directed graph with a BFS shortest-path search.
package graph

// Graph is a directed graph whose nodes are identified by int keys. Edges are
// stored as an adjacency list.
type Graph struct {
	adj map[int][]int
}

// New returns an empty Graph ready for use.
func New() *Graph {
	return &Graph{adj: make(map[int][]int)}
}

// AddNode ensures that node n exists in the graph, even if it has no edges.
func (g *Graph) AddNode(n int) {
	if _, ok := g.adj[n]; !ok {
		g.adj[n] = nil
	}
}

// AddEdge adds a directed edge from a to b. Both endpoints are registered as
// nodes. Parallel edges are not deduplicated, which does not affect the
// shortest-path result.
func (g *Graph) AddEdge(a, b int) {
	g.AddNode(b)
	g.adj[a] = append(g.adj[a], b)
}

// ShortestPath returns the shortest path, by number of edges, from node from to
// node to using breadth-first search. The returned slice includes both
// endpoints. The boolean result is false when no path exists; in that case the
// returned slice is nil.
//
// A path from a node to itself is always the single-element path [from].
func (g *Graph) ShortestPath(from, to int) ([]int, bool) {
	if _, ok := g.adj[from]; !ok {
		return nil, false
	}
	if from == to {
		return []int{from}, true
	}

	prev := map[int]int{from: from}
	queue := []int{from}

	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]

		for _, next := range g.adj[cur] {
			if _, seen := prev[next]; seen {
				continue
			}
			prev[next] = cur
			if next == to {
				return buildPath(prev, from, to), true
			}
			queue = append(queue, next)
		}
	}

	return nil, false
}

// buildPath reconstructs the path from from to to by walking the prev map
// backwards and then reversing the result.
func buildPath(prev map[int]int, from, to int) []int {
	path := []int{to}
	for cur := to; cur != from; {
		cur = prev[cur]
		path = append(path, cur)
	}

	for i, j := 0, len(path)-1; i < j; i, j = i+1, j-1 {
		path[i], path[j] = path[j], path[i]
	}
	return path
}
