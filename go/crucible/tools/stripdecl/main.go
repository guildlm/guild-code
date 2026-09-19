// stripdecl removes from a Go TEST file every top-level declaration whose name is already
// declared in the IMPLEMENTATION file it will be compiled with. It is a deterministic repair
// for the single most common self-written-test defect measured on 2026-09-19: the test writer
// re-implements the function under test inside the test file ("redeclared in this block"),
// which makes an otherwise reasonable test uncompilable. Nothing is invented: only names that
// collide are dropped, and only in the test file. Test functions (TestXxx) are never dropped.
//
//	go run ./tools/stripdecl -impl impl.go -test impl_test.go   > repaired_test.go
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
	"strings"
)

func declaredNames(f *ast.File) map[string]bool {
	names := map[string]bool{}
	for _, d := range f.Decls {
		switch d := d.(type) {
		case *ast.FuncDecl:
			if d.Recv == nil {
				names[d.Name.Name] = true
			} else {
				// methods collide by (receiver type, name); record as T.m
				names[recvName(d)+"."+d.Name.Name] = true
			}
		case *ast.GenDecl:
			for _, s := range d.Specs {
				switch s := s.(type) {
				case *ast.TypeSpec:
					names[s.Name.Name] = true
				case *ast.ValueSpec:
					for _, n := range s.Names {
						names[n.Name] = true
					}
				}
			}
		}
	}
	return names
}

func recvName(d *ast.FuncDecl) string {
	t := d.Recv.List[0].Type
	if star, ok := t.(*ast.StarExpr); ok {
		t = star.X
	}
	if id, ok := t.(*ast.Ident); ok {
		return id.Name
	}
	if idx, ok := t.(*ast.IndexExpr); ok { // generic receiver T[K]
		if id, ok := idx.X.(*ast.Ident); ok {
			return id.Name
		}
	}
	return ""
}

func main() {
	impl := flag.String("impl", "", "implementation file")
	test := flag.String("test", "", "test file to repair")
	flag.Parse()
	if *impl == "" || *test == "" {
		fmt.Fprintln(os.Stderr, "usage: stripdecl -impl impl.go -test impl_test.go")
		os.Exit(2)
	}
	fset := token.NewFileSet()
	implAST, err := parser.ParseFile(fset, *impl, nil, 0)
	if err != nil {
		fmt.Fprintln(os.Stderr, "impl does not parse; nothing stripped:", err)
		src, _ := os.ReadFile(*test)
		os.Stdout.Write(src)
		return
	}
	taken := declaredNames(implAST)
	testAST, err := parser.ParseFile(fset, *test, nil, parser.ParseComments)
	if err != nil {
		fmt.Fprintln(os.Stderr, "test does not parse; nothing stripped:", err)
		src, _ := os.ReadFile(*test)
		os.Stdout.Write(src)
		return
	}
	kept := testAST.Decls[:0]
	dropped := 0
	for _, d := range testAST.Decls {
		drop := false
		switch d := d.(type) {
		case *ast.FuncDecl:
			if strings.HasPrefix(d.Name.Name, "Test") || strings.HasPrefix(d.Name.Name, "Benchmark") || strings.HasPrefix(d.Name.Name, "Example") {
				break
			}
			if d.Recv == nil {
				drop = taken[d.Name.Name]
			} else {
				drop = taken[recvName(d)+"."+d.Name.Name] || taken[recvName(d)] // method of a type the impl owns
			}
		case *ast.GenDecl:
			if d.Tok == token.IMPORT {
				break
			}
			var specs []ast.Spec
			for _, s := range d.Specs {
				keep := true
				switch s := s.(type) {
				case *ast.TypeSpec:
					keep = !taken[s.Name.Name]
				case *ast.ValueSpec:
					for _, n := range s.Names {
						if taken[n.Name] {
							keep = false
						}
					}
				}
				if keep {
					specs = append(specs, s)
				} else {
					dropped++
				}
			}
			if len(specs) == 0 {
				drop = true
				dropped-- // counted below
			} else {
				d.Specs = specs
			}
		}
		if drop {
			dropped++
			continue
		}
		kept = append(kept, d)
	}
	testAST.Decls = kept
	var buf bytes.Buffer
	if err := format.Node(&buf, fset, testAST); err != nil {
		fmt.Fprintln(os.Stderr, "format failed; nothing stripped:", err)
		src, _ := os.ReadFile(*test)
		os.Stdout.Write(src)
		return
	}
	fmt.Fprintf(os.Stderr, "stripdecl: dropped %d colliding declaration(s)\n", dropped)
	os.Stdout.Write(buf.Bytes())
}
