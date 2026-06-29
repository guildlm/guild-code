// Package configloader loads typed configuration from a string map (such as
// environment variables), applying defaults and validation. Invalid input is
// reported by wrapping the sentinel error ErrInvalidConfig.
package configloader

import (
	"errors"
	"fmt"
	"time"
)

// ErrInvalidConfig is the sentinel wrapped by every error returned from Load
// when the input map cannot be turned into a valid Config. Callers may test for
// it with errors.Is.
var ErrInvalidConfig = errors.New("invalid config")

// Config is the fully parsed and validated configuration.
type Config struct {
	// Host is the bind address. Defaults to "localhost".
	Host string
	// Port is the TCP port to listen on. Must be in [1, 65535]. Defaults to 8080.
	Port int
	// Debug toggles verbose logging. Defaults to false.
	Debug bool
	// Timeout bounds a single request. Must be > 0. Defaults to 30s.
	Timeout time.Duration
	// MaxConns caps concurrent connections. Must be > 0. Defaults to 100.
	MaxConns int
}

// Load parses src into a Config. Missing keys fall back to documented defaults;
// present-but-malformed or out-of-range values produce an error that wraps
// ErrInvalidConfig. A nil map is treated as empty and yields the all-default
// Config.
func Load(src map[string]string) (Config, error) {
	cfg := Config{
		Host:     "localhost",
		Port:     8080,
		Debug:    false,
		Timeout:  30 * time.Second,
		MaxConns: 100,
	}

	if v, ok := src["HOST"]; ok {
		if v == "" {
			return Config{}, fmt.Errorf("%w: HOST must not be empty", ErrInvalidConfig)
		}
		cfg.Host = v
	}

	port, err := parseField(src, "PORT", cfg.Port, parseInt)
	if err != nil {
		return Config{}, err
	}
	cfg.Port = port

	debug, err := parseField(src, "DEBUG", cfg.Debug, parseBool)
	if err != nil {
		return Config{}, err
	}
	cfg.Debug = debug

	timeout, err := parseField(src, "TIMEOUT", cfg.Timeout, parseDuration)
	if err != nil {
		return Config{}, err
	}
	cfg.Timeout = timeout

	maxConns, err := parseField(src, "MAX_CONNS", cfg.MaxConns, parseInt)
	if err != nil {
		return Config{}, err
	}
	cfg.MaxConns = maxConns

	if err := cfg.validate(); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

// validate enforces the cross-field and range invariants of a Config.
func (c Config) validate() error {
	if c.Port < 1 || c.Port > 65535 {
		return fmt.Errorf("%w: PORT %d out of range [1, 65535]", ErrInvalidConfig, c.Port)
	}
	if c.Timeout <= 0 {
		return fmt.Errorf("%w: TIMEOUT must be positive, got %s", ErrInvalidConfig, c.Timeout)
	}
	if c.MaxConns < 1 {
		return fmt.Errorf("%w: MAX_CONNS must be positive, got %d", ErrInvalidConfig, c.MaxConns)
	}
	return nil
}
