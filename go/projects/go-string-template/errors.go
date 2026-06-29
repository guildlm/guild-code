package template

import (
	"errors"
	"fmt"
)

// ErrUnclosed is returned (wrapped in a *PlaceholderError) when a placeholder is
// opened with "{{" but never closed with a matching "}}".
var ErrUnclosed = errors.New("template: unclosed placeholder")

// ErrUnknownKey is returned (wrapped in a *PlaceholderError) when a placeholder
// names a key that is not present in the supplied variables.
var ErrUnknownKey = errors.New("template: unknown placeholder key")

// PlaceholderError describes a problem with a single placeholder, including the
// byte offset at which the offending "{{" begins. It wraps one of the sentinel
// errors above, so callers can match with errors.Is.
type PlaceholderError struct {
	Key string // the placeholder key; empty for an unclosed placeholder
	Pos int    // byte offset of the "{{" that triggered the error
	Err error  // sentinel cause: ErrUnclosed or ErrUnknownKey
}

func (e *PlaceholderError) Error() string {
	if errors.Is(e.Err, ErrUnclosed) {
		return fmt.Sprintf("%v at position %d", e.Err, e.Pos)
	}
	return fmt.Sprintf("%v %q at position %d", e.Err, e.Key, e.Pos)
}

// Unwrap exposes the sentinel cause for errors.Is / errors.As.
func (e *PlaceholderError) Unwrap() error { return e.Err }
