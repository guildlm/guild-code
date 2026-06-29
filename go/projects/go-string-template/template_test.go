package template

import (
	"errors"
	"testing"
)

func TestRender(t *testing.T) {
	tests := []struct {
		name string
		tmpl string
		vars map[string]string
		want string
	}{
		{
			name: "empty template",
			tmpl: "",
			vars: nil,
			want: "",
		},
		{
			name: "no placeholders",
			tmpl: "hello world",
			vars: map[string]string{"unused": "x"},
			want: "hello world",
		},
		{
			name: "single placeholder",
			tmpl: "hello {{name}}",
			vars: map[string]string{"name": "Ada"},
			want: "hello Ada",
		},
		{
			name: "inner whitespace trimmed",
			tmpl: "hi {{  name  }}!",
			vars: map[string]string{"name": "Ada"},
			want: "hi Ada!",
		},
		{
			name: "adjacent placeholders",
			tmpl: "{{a}}{{b}}",
			vars: map[string]string{"a": "1", "b": "2"},
			want: "12",
		},
		{
			name: "repeated key",
			tmpl: "{{x}}-{{x}}",
			vars: map[string]string{"x": "z"},
			want: "z-z",
		},
		{
			name: "empty value is allowed",
			tmpl: "[{{blank}}]",
			vars: map[string]string{"blank": ""},
			want: "[]",
		},
		{
			name: "value containing braces is not re-expanded",
			tmpl: "{{a}}",
			vars: map[string]string{"a": "{{b}}"},
			want: "{{b}}",
		},
		{
			name: "single brace is literal text",
			tmpl: "a { b } c",
			vars: nil,
			want: "a { b } c",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Render(tt.tmpl, tt.vars)
			if err != nil {
				t.Fatalf("Render(%q) unexpected error: %v", tt.tmpl, err)
			}
			if got != tt.want {
				t.Errorf("Render(%q) = %q, want %q", tt.tmpl, got, tt.want)
			}
		})
	}
}

func TestRenderErrors(t *testing.T) {
	tests := []struct {
		name    string
		tmpl    string
		vars    map[string]string
		wantErr error
		wantKey string
		wantPos int
	}{
		{
			name:    "unknown key",
			tmpl:    "hello {{name}}",
			vars:    map[string]string{"other": "x"},
			wantErr: ErrUnknownKey,
			wantKey: "name",
			wantPos: 6,
		},
		{
			name:    "unknown key reports trimmed name",
			tmpl:    "{{ missing }}",
			vars:    nil,
			wantErr: ErrUnknownKey,
			wantKey: "missing",
			wantPos: 0,
		},
		{
			name:    "empty placeholder is an unknown key",
			tmpl:    "x{{}}y",
			vars:    map[string]string{"name": "Ada"},
			wantErr: ErrUnknownKey,
			wantKey: "",
			wantPos: 1,
		},
		{
			name:    "unclosed placeholder",
			tmpl:    "hello {{name",
			vars:    map[string]string{"name": "Ada"},
			wantErr: ErrUnclosed,
			wantPos: 6,
		},
		{
			name:    "open delim at very end",
			tmpl:    "done{{",
			vars:    nil,
			wantErr: ErrUnclosed,
			wantPos: 4,
		},
		{
			name:    "second placeholder unclosed",
			tmpl:    "{{a}} and {{b",
			vars:    map[string]string{"a": "1"},
			wantErr: ErrUnclosed,
			wantPos: 10,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := Render(tt.tmpl, tt.vars)
			if err == nil {
				t.Fatalf("Render(%q) = nil error, want %v", tt.tmpl, tt.wantErr)
			}
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("Render(%q) error = %v, want errors.Is %v", tt.tmpl, err, tt.wantErr)
			}

			var pe *PlaceholderError
			if !errors.As(err, &pe) {
				t.Fatalf("Render(%q) error %v is not a *PlaceholderError", tt.tmpl, err)
			}
			if pe.Pos != tt.wantPos {
				t.Errorf("Render(%q) error Pos = %d, want %d", tt.tmpl, pe.Pos, tt.wantPos)
			}
			if errors.Is(tt.wantErr, ErrUnknownKey) && pe.Key != tt.wantKey {
				t.Errorf("Render(%q) error Key = %q, want %q", tt.tmpl, pe.Key, tt.wantKey)
			}
		})
	}
}
