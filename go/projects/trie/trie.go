// Package trie implements a prefix-search trie (radix-1 / character trie)
// over strings using only the Go standard library.
//
// A Trie supports inserting words, exact-match lookup, prefix existence
// checks, and enumerating all stored words that share a given prefix.
package trie

import "sort"

// node is a single position in the trie. Each node owns a map from the next
// rune to the child node reached by consuming that rune. terminal marks that
// the path from the root to this node spells a word that was inserted.
type node struct {
	children map[rune]*node
	terminal bool
}

func newNode() *node {
	return &node{children: make(map[rune]*node)}
}

// Trie is a mutable collection of words supporting prefix queries.
// The zero value is not ready for use; call New.
type Trie struct {
	root *node
	size int
}

// New returns an empty Trie ready for use.
func New() *Trie {
	return &Trie{root: newNode()}
}

// Len reports the number of distinct words currently stored in the Trie.
func (t *Trie) Len() int {
	return t.size
}

// Insert adds word to the Trie. Inserting the same word twice is a no-op
// after the first insertion. The empty string is a valid word.
func (t *Trie) Insert(word string) {
	cur := t.root
	for _, r := range word {
		next, ok := cur.children[r]
		if !ok {
			next = newNode()
			cur.children[r] = next
		}
		cur = next
	}
	if !cur.terminal {
		cur.terminal = true
		t.size++
	}
}

// find walks the trie consuming every rune of s and returns the node reached,
// or nil if the path does not exist.
func (t *Trie) find(s string) *node {
	cur := t.root
	for _, r := range s {
		next, ok := cur.children[r]
		if !ok {
			return nil
		}
		cur = next
	}
	return cur
}

// Search reports whether word was inserted into the Trie as a complete word.
func (t *Trie) Search(word string) bool {
	n := t.find(word)
	return n != nil && n.terminal
}

// StartsWith reports whether any stored word has prefix as a prefix.
// Every word is a prefix of itself, and the empty prefix matches whenever
// the Trie is non-empty.
func (t *Trie) StartsWith(prefix string) bool {
	n := t.find(prefix)
	if n == nil {
		return false
	}
	return hasWord(n)
}

// hasWord reports whether the subtree rooted at n contains any terminal node.
func hasWord(n *node) bool {
	if n.terminal {
		return true
	}
	for _, c := range n.children {
		if hasWord(c) {
			return true
		}
	}
	return false
}

// WordsWithPrefix returns every stored word that begins with prefix, sorted
// in ascending lexicographic (rune) order. The result is never nil; when no
// word matches it is an empty, non-nil slice.
func (t *Trie) WordsWithPrefix(prefix string) []string {
	out := []string{}
	n := t.find(prefix)
	if n == nil {
		return out
	}
	collect(n, []rune(prefix), &out)
	sort.Strings(out)
	return out
}

// collect appends to out every word formed by a terminal node in the subtree
// rooted at n, where path is the sequence of runes from the root to n.
func collect(n *node, path []rune, out *[]string) {
	if n.terminal {
		*out = append(*out, string(path))
	}
	for r, c := range n.children {
		child := make([]rune, len(path)+1)
		copy(child, path)
		child[len(path)] = r
		collect(c, child, out)
	}
}
