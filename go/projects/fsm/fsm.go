// Package fsm provides a small, generic finite state machine.
//
// A Machine is parameterized over a state type S and an event type E (both
// comparable). Allowed transitions are registered with Permit, the current
// state is read with Current, and events are applied with Fire. Firing an event
// that is not permitted from the current state leaves the state unchanged and
// returns an error wrapping the sentinel ErrInvalidTransition.
//
// A Machine is intended for sequential use by a single goroutine. It performs
// no internal locking and is not safe for concurrent use without external
// synchronization.
package fsm

import (
	"errors"
	"fmt"
)

// ErrInvalidTransition is the sentinel returned (wrapped) by Fire when an event
// is not permitted from the machine's current state. Callers can detect it with
// errors.Is.
var ErrInvalidTransition = errors.New("fsm: invalid transition")

// key uniquely identifies a (state, event) pair used to look up a transition.
type key[S, E comparable] struct {
	from  S
	event E
}

// Machine is a finite state machine over state type S and event type E.
//
// The zero Machine is not usable; construct one with New.
type Machine[S, E comparable] struct {
	current     S
	transitions map[key[S, E]]S
}

// New creates a Machine in the given initial state with no transitions
// registered. Use Permit to register the allowed transitions.
func New[S, E comparable](initial S) *Machine[S, E] {
	return &Machine[S, E]{
		current:     initial,
		transitions: make(map[key[S, E]]S),
	}
}

// Permit registers that applying event e while in state from advances the
// machine to state to. Permit returns the receiver so calls can be chained.
//
// Registering the same (from, e) pair again overwrites the previous
// destination.
func (m *Machine[S, E]) Permit(from S, e E, to S) *Machine[S, E] {
	m.transitions[key[S, E]{from: from, event: e}] = to
	return m
}

// Current returns the machine's current state.
func (m *Machine[S, E]) Current() S {
	return m.current
}

// Can reports whether event e is permitted from the current state.
func (m *Machine[S, E]) Can(e E) bool {
	_, ok := m.transitions[key[S, E]{from: m.current, event: e}]
	return ok
}

// Fire applies event e to the machine. If e is permitted from the current
// state, the machine advances to the destination state and Fire returns nil.
// Otherwise the state is left unchanged and Fire returns an error wrapping
// ErrInvalidTransition.
func (m *Machine[S, E]) Fire(e E) error {
	to, ok := m.transitions[key[S, E]{from: m.current, event: e}]
	if !ok {
		return fmt.Errorf("%w: event %v from state %v", ErrInvalidTransition, e, m.current)
	}
	m.current = to
	return nil
}
