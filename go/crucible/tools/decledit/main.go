// decledit applies DECLARATION-LEVEL edits to a Go source file, so a model can change fifty
// characters of a twenty-thousand-character file without retyping the file. go_swe_bench v0
// (2026-09-19) showed the retype form is the wall: 0/17 passes above 16k chars, every pass a small
// file with a small patch. Deterministic, go/ast based, invents nothing.
//
//	decledit -apply   -target pkg/x.go -fragment reply.go   > edited.go
//	decledit -changed -before old.go   -after new.go        > fragment.go   (the gold fragment)
//
// A fragment is Go source (package clause optional) holding top-level declarations. -apply
// replaces every declaration of the target that has the same key (func name, Recv.method, type
// name, var/const name; a const/var group that uses iota is one unit keyed by its first name),
// appends the declarations the target does not have, unions the fragment's imports into the
// target (run goimports afterwards to prune the unused ones), and honours the directive
//
//	// decledit: delete Key
//
// func init() and blank names are always appended. -changed emits the fragment that turns
// -before into -after, which makes the tool testable on every gold patch with no model at all.
// Exit codes: 0 ok · 2 usage · 3 the fragment does not parse (the message is meant as feedback).
package main

import (
	"bytes"
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"regexp"
	"sort"
	"strings"
)

type decl struct {
	key        string
	start, end int    // byte offsets in the source, doc comment included
	doc        string // doc comment text incl. trailing newline, or ""
	body       string // spec text without keyword (GenDecl) / whole func text (FuncDecl)
	tok        string // "const"|"var"|"type" for GenDecl-derived decls, "" for funcs
	grouped    bool   // the decl sits inside a ( ... ) group in its file
	unit       bool   // a whole iota/implicit-repeat group carried as one decl
	appendOnly bool
}

// standalone renders the decl as it would sit at top level on its own.
func (d decl) standalone() string {
	if d.tok == "" || d.unit {
		return d.doc + d.body
	}
	return d.doc + d.tok + " " + d.body
}

func recvName(d *ast.FuncDecl) string {
	t := d.Recv.List[0].Type
	if star, ok := t.(*ast.StarExpr); ok {
		t = star.X
	}
	switch t := t.(type) {
	case *ast.Ident:
		return t.Name
	case *ast.IndexExpr: // generic receiver T[K]
		if id, ok := t.X.(*ast.Ident); ok {
			return id.Name
		}
	case *ast.IndexListExpr: // generic receiver T[K, V]
		if id, ok := t.X.(*ast.Ident); ok {
			return id.Name
		}
	}
	return ""
}

func specKey(s ast.Spec) string {
	switch s := s.(type) {
	case *ast.TypeSpec:
		return s.Name.Name
	case *ast.ValueSpec:
		names := make([]string, len(s.Names))
		for i, n := range s.Names {
			names[i] = n.Name
		}
		return strings.Join(names, ",")
	}
	return ""
}

func specDoc(s ast.Spec) *ast.CommentGroup {
	switch s := s.(type) {
	case *ast.TypeSpec:
		return s.Doc
	case *ast.ValueSpec:
		return s.Doc
	}
	return nil
}

// usesIota reports whether a value group relies on ordering: an explicit iota or an implicit
// repetition (a spec with no type and no values). Such a group only makes sense whole.
func usesIota(d *ast.GenDecl) bool {
	for _, s := range d.Specs {
		v, ok := s.(*ast.ValueSpec)
		if !ok {
			continue
		}
		if len(v.Values) == 0 && v.Type == nil {
			return true
		}
		found := false
		for _, e := range v.Values {
			ast.Inspect(e, func(n ast.Node) bool {
				if id, ok := n.(*ast.Ident); ok && id.Name == "iota" {
					found = true
				}
				return !found
			})
		}
		if found {
			return true
		}
	}
	return false
}

func decls(fset *token.FileSet, f *ast.File, src []byte) []decl {
	off := func(p token.Pos) int { return fset.Position(p).Offset }
	var out []decl
	for _, d := range f.Decls {
		switch d := d.(type) {
		case *ast.FuncDecl:
			k := d.Name.Name
			if d.Recv != nil {
				k = recvName(d) + "." + k
			}
			start, doc := off(d.Pos()), ""
			if d.Doc != nil {
				doc = string(src[off(d.Doc.Pos()):start])
				start = off(d.Doc.Pos())
			}
			out = append(out, decl{key: k, start: start, end: off(d.End()), doc: doc,
				body: string(src[off(d.Pos()):off(d.End())]), appendOnly: k == "init" || k == "_"})
		case *ast.GenDecl:
			if d.Tok == token.IMPORT {
				continue
			}
			tok := d.Tok.String()
			if d.Lparen.IsValid() && usesIota(d) { // one unit
				start, doc := off(d.Pos()), ""
				if d.Doc != nil {
					doc = string(src[off(d.Doc.Pos()):start])
					start = off(d.Doc.Pos())
				}
				out = append(out, decl{key: "group:" + specKey(d.Specs[0]), start: start, end: off(d.End()), doc: doc,
					body: string(src[off(d.Pos()):off(d.End())]), tok: tok, unit: true})
				continue
			}
			for _, s := range d.Specs {
				start, doc := off(s.Pos()), ""
				if sd := specDoc(s); sd != nil {
					doc = string(src[off(sd.Pos()):start])
					start = off(sd.Pos())
				}
				dd := decl{key: specKey(s), start: start, end: off(s.End()), doc: doc,
					body: string(src[off(s.Pos()):off(s.End())]), tok: tok, grouped: d.Lparen.IsValid()}
				if !dd.grouped && d.Doc != nil { // the doc sits before the keyword on a standalone decl
					dd.doc = string(src[off(d.Doc.Pos()):off(d.Pos())])
					dd.start = off(d.Doc.Pos())
				}
				if !dd.grouped {
					dd.start = min(dd.start, off(d.Pos()))
					dd.end = off(d.End())
					if strings.Contains(dd.key, "_") && dd.key == "_" {
						dd.appendOnly = true
					}
				}
				out = append(out, dd)
			}
		}
	}
	return out
}

var (
	pkgRE    = regexp.MustCompile(`(?m)^package\s+\w+`)
	deleteRE = regexp.MustCompile(`(?m)^//\s*decledit:\s*delete\s+(\S+)`)
)

func parse(fset *token.FileSet, name string, src []byte) (*ast.File, error) {
	return parser.ParseFile(fset, name, src, parser.ParseComments)
}

func importsOf(f *ast.File) map[string]string { // path -> alias ("" if none)
	m := map[string]string{}
	for _, im := range f.Imports {
		alias := ""
		if im.Name != nil {
			alias = im.Name.Name
		}
		m[strings.Trim(im.Path.Value, `"`)] = alias
	}
	return m
}

type edit struct {
	start, end int
	text       string
}

func apply(targetPath, fragmentPath string) int {
	tsrc, err := os.ReadFile(targetPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	fsrc, err := os.ReadFile(fragmentPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	fset := token.NewFileSet()
	tf, err := parse(fset, targetPath, tsrc)
	if err != nil {
		fmt.Fprintln(os.Stderr, "target does not parse:", err)
		return 2
	}
	if !pkgRE.Match(fsrc) {
		fsrc = append([]byte("package "+tf.Name.Name+"\n\n"), fsrc...)
	}
	ff, err := parse(fset, "fragment.go", fsrc)
	if err != nil {
		fmt.Fprintln(os.Stderr, "fragment does not parse:", err)
		return 3
	}
	tds, fds := decls(fset, tf, tsrc), decls(fset, ff, fsrc)
	find := func(key string) *decl {
		for i := range tds {
			if tds[i].key == key {
				return &tds[i]
			}
		}
		if strings.HasPrefix(key, "group:") { // a unit group matches a target group holding its first name
			first := strings.TrimPrefix(key, "group:")
			for i := range tds {
				if tds[i].unit && strings.Contains(","+strings.Join(groupNames(tds[i].body), ",")+",", ","+first+",") {
					return &tds[i]
				}
			}
		}
		return nil
	}
	var edits []edit
	var appends []string
	used := map[int]bool{}
	for _, fd := range fds {
		t := fd.appendOnly
		var td *decl
		if !t {
			td = find(fd.key)
		}
		if td == nil || used[td.start] {
			appends = append(appends, fd.standalone())
			continue
		}
		used[td.start] = true
		text := fd.standalone()
		if td.grouped && !fd.unit && fd.tok != "" { // spec text only, inside the target's group
			text = fd.doc + fd.body
		}
		edits = append(edits, edit{td.start, td.end, text})
	}
	for _, m := range deleteRE.FindAllSubmatch(fsrc, -1) {
		if td := find(string(m[1])); td != nil && !used[td.start] {
			used[td.start] = true
			end := td.end
			for end < len(tsrc) && (tsrc[end] == '\n' || tsrc[end] == '\r') {
				end++
			}
			edits = append(edits, edit{td.start, end, ""})
		}
	}
	// imports the fragment brings and the target lacks: inserted after the target's last import
	// (or the package clause); goimports afterwards merges and prunes.
	have := importsOf(tf)
	var add []string
	for path, alias := range importsOf(ff) {
		if _, ok := have[path]; !ok {
			if alias != "" {
				add = append(add, alias+" \""+path+"\"")
			} else {
				add = append(add, "\""+path+"\"")
			}
		}
	}
	if len(add) > 0 {
		sort.Strings(add)
		at := fset.Position(tf.Name.End()).Offset
		for _, d := range tf.Decls {
			if g, ok := d.(*ast.GenDecl); ok && g.Tok == token.IMPORT {
				at = fset.Position(g.End()).Offset
			}
		}
		edits = append(edits, edit{at, at, "\n\nimport (\n\t" + strings.Join(add, "\n\t") + "\n)\n"})
	}
	sort.Slice(edits, func(i, j int) bool { return edits[i].start > edits[j].start })
	out := append([]byte(nil), tsrc...)
	for _, e := range edits {
		out = append(out[:e.start], append([]byte(e.text), out[e.end:]...)...)
	}
	if len(appends) > 0 {
		out = append(bytes.TrimRight(out, "\n"), []byte("\n\n"+strings.Join(appends, "\n\n")+"\n")...)
	}
	if formatted, err := format.Source(out); err == nil {
		out = formatted
	} else {
		fmt.Fprintln(os.Stderr, "result does not format (written unformatted):", err)
	}
	os.Stdout.Write(out)
	return 0
}

func groupNames(body string) []string {
	var names []string
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, "g.go", "package p\n"+body, 0)
	if err != nil {
		return names
	}
	for _, d := range f.Decls {
		if g, ok := d.(*ast.GenDecl); ok {
			for _, s := range g.Specs {
				names = append(names, strings.Split(specKey(s), ",")...)
			}
		}
	}
	return names
}

func changed(beforePath, afterPath string) int {
	bsrc, err := os.ReadFile(beforePath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	asrc, err := os.ReadFile(afterPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	fset := token.NewFileSet()
	bf, err := parse(fset, beforePath, bsrc)
	if err != nil {
		fmt.Fprintln(os.Stderr, "before does not parse:", err)
		return 2
	}
	af, err := parse(fset, afterPath, asrc)
	if err != nil {
		fmt.Fprintln(os.Stderr, "after does not parse:", err)
		return 2
	}
	bds, ads := decls(fset, bf, bsrc), decls(fset, af, asrc)
	before := map[string]string{}
	for _, d := range bds {
		before[d.key] = strings.TrimSpace(d.standalone())
	}
	var b strings.Builder
	fmt.Fprintf(&b, "package %s\n\n", af.Name.Name)
	if len(af.Imports) > 0 {
		b.WriteString("import (\n")
		for _, im := range af.Imports {
			if im.Name != nil {
				fmt.Fprintf(&b, "\t%s %s\n", im.Name.Name, im.Path.Value)
			} else {
				fmt.Fprintf(&b, "\t%s\n", im.Path.Value)
			}
		}
		b.WriteString(")\n\n")
	}
	seen := map[string]bool{}
	for _, d := range ads {
		seen[d.key] = true
		if old, ok := before[d.key]; ok && old == strings.TrimSpace(d.standalone()) && !d.appendOnly {
			continue
		}
		b.WriteString(d.standalone())
		b.WriteString("\n\n")
	}
	for _, d := range bds {
		if !seen[d.key] && !d.appendOnly {
			fmt.Fprintf(&b, "// decledit: delete %s\n", d.key)
		}
	}
	os.Stdout.WriteString(b.String())
	return 0
}

func main() {
	doApply := flag.Bool("apply", false, "apply -fragment to -target, print the result")
	doChanged := flag.Bool("changed", false, "print the fragment that turns -before into -after")
	target := flag.String("target", "", "")
	fragment := flag.String("fragment", "", "")
	before := flag.String("before", "", "")
	after := flag.String("after", "", "")
	flag.Parse()
	switch {
	case *doApply && *target != "" && *fragment != "":
		os.Exit(apply(*target, *fragment))
	case *doChanged && *before != "" && *after != "":
		os.Exit(changed(*before, *after))
	}
	fmt.Fprintln(os.Stderr, "usage: decledit -apply -target f.go -fragment frag.go | decledit -changed -before a.go -after b.go")
	os.Exit(2)
}
