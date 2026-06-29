// Package template implements a tiny string-substitution engine. It expands
// "{{key}}" placeholders in a template using a caller-supplied set of variables
// and reports unclosed or unknown placeholders as errors.
package template

import "strings"

const (
	openDelim  = "{{"
	closeDelim = "}}"
)

// Render expands every {{key}} placeholder in tmpl using vars. Whitespace
// directly inside the braces is ignored, so "{{ key }}" and "{{key}}" name the
// same key. It returns an error if a placeholder is left unclosed or names a key
// that is absent from vars; the error wraps ErrUnclosed or ErrUnknownKey.
func Render(tmpl string, vars map[string]string) (string, error) {
	return render(tmpl, func(key string) (string, bool) {
		v, ok := vars[key]
		return v, ok
	}, func(v string) string { return v })
}

// render is the generic engine shared by the exported helpers. lookup reports
// the value for a key and whether the key is known; format turns a found value
// into its replacement text.
func render[V any](tmpl string, lookup func(string) (V, bool), format func(V) string) (string, error) {
	var b strings.Builder
	b.Grow(len(tmpl))

	for i := 0; i < len(tmpl); {
		rel := strings.Index(tmpl[i:], openDelim)
		if rel < 0 {
			b.WriteString(tmpl[i:])
			break
		}
		start := i + rel
		b.WriteString(tmpl[i:start])

		body := start + len(openDelim)
		end := strings.Index(tmpl[body:], closeDelim)
		if end < 0 {
			return "", &PlaceholderError{Pos: start, Err: ErrUnclosed}
		}

		key := strings.TrimSpace(tmpl[body : body+end])
		val, ok := lookup(key)
		if !ok {
			return "", &PlaceholderError{Key: key, Pos: start, Err: ErrUnknownKey}
		}
		b.WriteString(format(val))

		i = body + end + len(closeDelim)
	}
	return b.String(), nil
}
