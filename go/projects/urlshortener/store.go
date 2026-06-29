package main

import (
	"crypto/rand"
	"errors"
	"sync"
)

// ErrNotFound is returned when a short code has no associated URL.
var ErrNotFound = errors.New("code not found")

const codeAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

// Store is a concurrency-safe in-memory mapping of short codes to URLs.
type Store struct {
	mu       sync.RWMutex
	codes    map[string]string
	codeLen  int
	maxTries int
}

// NewStore returns an empty Store that generates codes of the given length.
func NewStore(codeLen int) *Store {
	if codeLen <= 0 {
		codeLen = 6
	}
	return &Store{
		codes:    make(map[string]string),
		codeLen:  codeLen,
		maxTries: 10,
	}
}

// Put stores url under a freshly generated unique code and returns the code.
func (s *Store) Put(url string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for i := 0; i < s.maxTries; i++ {
		code, err := s.generateCode()
		if err != nil {
			return "", err
		}
		if _, exists := s.codes[code]; exists {
			continue
		}
		s.codes[code] = url
		return code, nil
	}
	return "", errors.New("could not generate a unique code")
}

// Get returns the URL stored under code, or ErrNotFound.
func (s *Store) Get(code string) (string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	url, ok := s.codes[code]
	if !ok {
		return "", ErrNotFound
	}
	return url, nil
}

// Len reports how many codes are currently stored.
func (s *Store) Len() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.codes)
}

// generateCode builds a random base62 code. Callers must hold s.mu.
func (s *Store) generateCode() (string, error) {
	buf := make([]byte, s.codeLen)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	for i := range buf {
		buf[i] = codeAlphabet[int(buf[i])%len(codeAlphabet)]
	}
	return string(buf), nil
}
