// Package config loads a key/value configuration file and demonstrates
// idiomatic error wrapping with %w so callers can inspect the cause with
// errors.Is / errors.As.
package config

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
)

// ErrMissingKey is returned when a required key is absent from the config.
var ErrMissingKey = errors.New("missing key")

// Config is a parsed set of string key/value pairs.
type Config map[string]string

// Parse reads "key=value" lines into a Config, skipping blanks and # comments.
// A malformed line is reported with context wrapped around the offending text.
func Parse(text string) (Config, error) {
	cfg := Config{}
	for i, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, value, ok := strings.Cut(line, "=")
		if !ok {
			return nil, fmt.Errorf("line %d: malformed entry %q", i+1, line)
		}
		cfg[strings.TrimSpace(key)] = strings.TrimSpace(value)
	}
	return cfg, nil
}

// Int returns the integer value for key, wrapping ErrMissingKey when absent and
// the strconv error (with context) when the value is not a valid integer.
func (c Config) Int(key string) (int, error) {
	raw, ok := c[key]
	if !ok {
		return 0, fmt.Errorf("config key %q: %w", key, ErrMissingKey)
	}
	n, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("config key %q: %w", key, err)
	}
	return n, nil
}
