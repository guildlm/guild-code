package configloader

import (
	"errors"
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	cfg, err := Load(nil)
	if err != nil {
		t.Fatalf("Load(nil) returned error: %v", err)
	}
	want := Config{
		Host:     "localhost",
		Port:     8080,
		Debug:    false,
		Timeout:  30 * time.Second,
		MaxConns: 100,
	}
	if cfg != want {
		t.Errorf("Load(nil) = %+v, want %+v", cfg, want)
	}
}

func TestLoadValid(t *testing.T) {
	tests := []struct {
		name string
		src  map[string]string
		want Config
	}{
		{
			name: "all overridden",
			src: map[string]string{
				"HOST":      "0.0.0.0",
				"PORT":      "9000",
				"DEBUG":     "true",
				"TIMEOUT":   "5s",
				"MAX_CONNS": "250",
			},
			want: Config{
				Host:     "0.0.0.0",
				Port:     9000,
				Debug:    true,
				Timeout:  5 * time.Second,
				MaxConns: 250,
			},
		},
		{
			name: "partial override keeps defaults",
			src:  map[string]string{"PORT": "1"},
			want: Config{
				Host:     "localhost",
				Port:     1,
				Debug:    false,
				Timeout:  30 * time.Second,
				MaxConns: 100,
			},
		},
		{
			name: "boundary port 65535",
			src:  map[string]string{"PORT": "65535"},
			want: Config{
				Host:     "localhost",
				Port:     65535,
				Debug:    false,
				Timeout:  30 * time.Second,
				MaxConns: 100,
			},
		},
		{
			name: "bool shorthand and duration with units",
			src:  map[string]string{"DEBUG": "1", "TIMEOUT": "1m30s"},
			want: Config{
				Host:     "localhost",
				Port:     8080,
				Debug:    true,
				Timeout:  90 * time.Second,
				MaxConns: 100,
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Load(tt.src)
			if err != nil {
				t.Fatalf("Load(%v) unexpected error: %v", tt.src, err)
			}
			if got != tt.want {
				t.Errorf("Load(%v) = %+v, want %+v", tt.src, got, tt.want)
			}
		})
	}
}

func TestLoadInvalid(t *testing.T) {
	tests := []struct {
		name string
		src  map[string]string
	}{
		{"empty host", map[string]string{"HOST": ""}},
		{"non-integer port", map[string]string{"PORT": "abc"}},
		{"port zero out of range", map[string]string{"PORT": "0"}},
		{"port too large", map[string]string{"PORT": "70000"}},
		{"negative port", map[string]string{"PORT": "-1"}},
		{"bad bool", map[string]string{"DEBUG": "yesplease"}},
		{"bad duration", map[string]string{"TIMEOUT": "30"}},
		{"zero duration", map[string]string{"TIMEOUT": "0s"}},
		{"negative duration", map[string]string{"TIMEOUT": "-5s"}},
		{"non-integer maxconns", map[string]string{"MAX_CONNS": "lots"}},
		{"zero maxconns", map[string]string{"MAX_CONNS": "0"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Load(tt.src)
			if err == nil {
				t.Fatalf("Load(%v) = %+v, want error", tt.src, got)
			}
			if !errors.Is(err, ErrInvalidConfig) {
				t.Errorf("Load(%v) error %v does not wrap ErrInvalidConfig", tt.src, err)
			}
			if got != (Config{}) {
				t.Errorf("Load(%v) returned non-zero Config on error: %+v", tt.src, got)
			}
		})
	}
}
