package trie

import (
	"reflect"
	"testing"
)

func build(words ...string) *Trie {
	t := New()
	for _, w := range words {
		t.Insert(w)
	}
	return t
}

func TestSearch(t *testing.T) {
	tr := build("app", "apple", "apply", "banana", "")

	tests := []struct {
		name string
		word string
		want bool
	}{
		{"exact word", "app", true},
		{"another exact word", "apple", true},
		{"empty string inserted", "", true},
		{"prefix is not a word", "ap", false},
		{"longer than any word", "applejack", false},
		{"never inserted", "orange", false},
		{"case sensitive", "App", false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := tr.Search(tc.word); got != tc.want {
				t.Errorf("Search(%q) = %v, want %v", tc.word, got, tc.want)
			}
		})
	}
}

func TestStartsWith(t *testing.T) {
	tr := build("app", "apple", "banana")

	tests := []struct {
		name   string
		prefix string
		want   bool
	}{
		{"shared prefix", "ap", true},
		{"full word is a prefix", "app", true},
		{"single matching letter", "b", true},
		{"empty prefix on non-empty trie", "", true},
		{"no such prefix", "cat", false},
		{"diverges partway", "apz", false},
		{"longer than word", "bananas", false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := tr.StartsWith(tc.prefix); got != tc.want {
				t.Errorf("StartsWith(%q) = %v, want %v", tc.prefix, got, tc.want)
			}
		})
	}
}

func TestStartsWithEmptyTrie(t *testing.T) {
	tr := New()
	if tr.StartsWith("") {
		t.Error("StartsWith(\"\") on empty trie = true, want false")
	}
	if tr.StartsWith("a") {
		t.Error("StartsWith(\"a\") on empty trie = true, want false")
	}
}

func TestWordsWithPrefix(t *testing.T) {
	tr := build("app", "apple", "apply", "apt", "banana", "band", "")

	tests := []struct {
		name   string
		prefix string
		want   []string
	}{
		{"common prefix sorted", "ap", []string{"app", "apple", "apply", "apt"}},
		{"deeper prefix", "app", []string{"app", "apple", "apply"}},
		{"single match", "apt", []string{"apt"}},
		{"other branch", "ban", []string{"banana", "band"}},
		{"empty prefix returns all sorted", "", []string{"", "app", "apple", "apply", "apt", "banana", "band"}},
		{"no match is empty non-nil", "zzz", []string{}},
		{"prefix longer than words", "applejack", []string{}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := tr.WordsWithPrefix(tc.prefix)
			if got == nil {
				t.Fatalf("WordsWithPrefix(%q) = nil, want non-nil slice", tc.prefix)
			}
			if !reflect.DeepEqual(got, tc.want) {
				t.Errorf("WordsWithPrefix(%q) = %v, want %v", tc.prefix, got, tc.want)
			}
		})
	}
}

func TestInsertIdempotentAndLen(t *testing.T) {
	tr := New()
	if tr.Len() != 0 {
		t.Fatalf("Len() on new trie = %d, want 0", tr.Len())
	}

	tr.Insert("go")
	tr.Insert("go")
	tr.Insert("gopher")
	if got := tr.Len(); got != 2 {
		t.Errorf("Len() after inserting go,go,gopher = %d, want 2", got)
	}

	tr.Insert("")
	if got := tr.Len(); got != 3 {
		t.Errorf("Len() after inserting empty string = %d, want 3", got)
	}
	if !tr.Search("") {
		t.Error("Search(\"\") after inserting empty string = false, want true")
	}
}

func TestUnicode(t *testing.T) {
	tr := build("naïve", "naïveté", "café", "😀smile")

	if !tr.Search("naïve") {
		t.Error("Search(naïve) = false, want true")
	}
	if !tr.StartsWith("naï") {
		t.Error("StartsWith(naï) = false, want true")
	}
	if got, want := tr.WordsWithPrefix("naï"), []string{"naïve", "naïveté"}; !reflect.DeepEqual(got, want) {
		t.Errorf("WordsWithPrefix(naï) = %v, want %v", got, want)
	}
	if !tr.Search("😀smile") {
		t.Error("Search(😀smile) = false, want true")
	}
	if !tr.StartsWith("😀") {
		t.Error("StartsWith(😀) = false, want true")
	}
}
