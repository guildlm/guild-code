package configloader

import (
	"fmt"
	"strconv"
	"time"
)

// field is the set of types Load knows how to parse from a string.
type field interface {
	~int | ~bool | ~string | time.Duration
}

// parser turns a raw string into a value of type T, returning an error (already
// wrapping ErrInvalidConfig) when the string is malformed.
type parser[T field] func(key, raw string) (T, error)

// parseField looks up key in src. When absent it returns def; when present it
// delegates to p. This keeps Load free of repetitive lookup/parse plumbing.
func parseField[T field](src map[string]string, key string, def T, p parser[T]) (T, error) {
	raw, ok := src[key]
	if !ok {
		return def, nil
	}
	return p(key, raw)
}

func parseInt(key, raw string) (int, error) {
	n, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("%w: %s=%q is not an integer", ErrInvalidConfig, key, raw)
	}
	return n, nil
}

func parseBool(key, raw string) (bool, error) {
	b, err := strconv.ParseBool(raw)
	if err != nil {
		return false, fmt.Errorf("%w: %s=%q is not a boolean", ErrInvalidConfig, key, raw)
	}
	return b, nil
}

func parseDuration(key, raw string) (time.Duration, error) {
	d, err := time.ParseDuration(raw)
	if err != nil {
		return 0, fmt.Errorf("%w: %s=%q is not a duration", ErrInvalidConfig, key, raw)
	}
	return d, nil
}
