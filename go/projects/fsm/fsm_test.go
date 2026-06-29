package fsm

import (
	"errors"
	"testing"
)

// state and event types used by the tests. Strings keep the tables readable.
type state string

type event string

const (
	stateIdle    state = "idle"
	stateRunning state = "running"
	statePaused  state = "paused"
	stateDone    state = "done"
)

const (
	eventStart  event = "start"
	eventPause  event = "pause"
	eventResume event = "resume"
	eventStop   event = "stop"
	eventReset  event = "reset"
)

// newTrafficMachine builds a small machine reused across tests.
func newTrafficMachine() *Machine[state, event] {
	m := New[state, event](stateIdle)
	m.Permit(stateIdle, eventStart, stateRunning).
		Permit(stateRunning, eventPause, statePaused).
		Permit(statePaused, eventResume, stateRunning).
		Permit(stateRunning, eventStop, stateDone).
		Permit(statePaused, eventStop, stateDone).
		Permit(stateDone, eventReset, stateIdle)
	return m
}

func TestNewStartsInInitialState(t *testing.T) {
	m := New[state, event](stateIdle)
	if got := m.Current(); got != stateIdle {
		t.Fatalf("Current() = %q, want %q", got, stateIdle)
	}
}

func TestFireSequence(t *testing.T) {
	tests := []struct {
		name    string
		events  []event
		want    state // expected Current after the (last successful) sequence
		wantErr bool  // whether the final Fire should error
	}{
		{
			name:   "single valid transition",
			events: []event{eventStart},
			want:   stateRunning,
		},
		{
			name:   "full happy path to done",
			events: []event{eventStart, eventPause, eventResume, eventStop},
			want:   stateDone,
		},
		{
			name:   "cycle back to idle via reset",
			events: []event{eventStart, eventStop, eventReset},
			want:   stateIdle,
		},
		{
			name:    "illegal first event leaves state unchanged",
			events:  []event{eventPause},
			want:    stateIdle,
			wantErr: true,
		},
		{
			name:    "illegal event mid-sequence",
			events:  []event{eventStart, eventResume},
			want:    stateRunning,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := newTrafficMachine()
			var lastErr error
			for _, e := range tt.events {
				lastErr = m.Fire(e)
			}
			if tt.wantErr && lastErr == nil {
				t.Fatalf("final Fire: got nil error, want non-nil")
			}
			if !tt.wantErr && lastErr != nil {
				t.Fatalf("final Fire: unexpected error: %v", lastErr)
			}
			if got := m.Current(); got != tt.want {
				t.Errorf("Current() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestFireInvalidWrapsSentinel(t *testing.T) {
	m := newTrafficMachine()
	err := m.Fire(eventStop) // not permitted from idle
	if err == nil {
		t.Fatal("Fire(eventStop) from idle: got nil error, want error")
	}
	if !errors.Is(err, ErrInvalidTransition) {
		t.Errorf("error %v does not wrap ErrInvalidTransition", err)
	}
	if got := m.Current(); got != stateIdle {
		t.Errorf("state changed after rejected event: Current() = %q, want %q", got, stateIdle)
	}
}

func TestFireDoesNotMutateOnRejection(t *testing.T) {
	// A rejected event must not corrupt state to a zero value or any other
	// state. This guards against assigning the lookup result before checking ok.
	m := New[state, event](stateRunning)
	m.Permit(stateRunning, eventStop, stateDone)

	if err := m.Fire(eventStart); err == nil { // eventStart undefined from running
		t.Fatal("Fire(eventStart): got nil error, want error")
	}
	if got := m.Current(); got != stateRunning {
		t.Fatalf("after rejected event Current() = %q, want %q", got, stateRunning)
	}
	// The machine must still accept the originally-valid event afterward.
	if err := m.Fire(eventStop); err != nil {
		t.Fatalf("Fire(eventStop) after rejection: unexpected error: %v", err)
	}
	if got := m.Current(); got != stateDone {
		t.Errorf("Current() = %q, want %q", got, stateDone)
	}
}

func TestCan(t *testing.T) {
	m := newTrafficMachine()
	tests := []struct {
		name string
		e    event
		want bool
	}{
		{"permitted from idle", eventStart, true},
		{"not permitted from idle", eventPause, false},
		{"unknown event", event("nope"), false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := m.Can(tt.e); got != tt.want {
				t.Errorf("Can(%q) = %v, want %v", tt.e, got, tt.want)
			}
		})
	}
	// Can must not mutate state.
	if got := m.Current(); got != stateIdle {
		t.Errorf("Can changed state: Current() = %q, want %q", got, stateIdle)
	}
}

func TestSelfLoopTransition(t *testing.T) {
	// A transition whose destination equals its source is a valid edge case.
	m := New[state, event](stateRunning)
	m.Permit(stateRunning, eventResume, stateRunning)
	if err := m.Fire(eventResume); err != nil {
		t.Fatalf("self-loop Fire: unexpected error: %v", err)
	}
	if got := m.Current(); got != stateRunning {
		t.Errorf("Current() = %q, want %q", got, stateRunning)
	}
}

func TestPermitOverwritesDestination(t *testing.T) {
	m := New[state, event](stateIdle)
	m.Permit(stateIdle, eventStart, stateRunning)
	m.Permit(stateIdle, eventStart, statePaused) // overwrite
	if err := m.Fire(eventStart); err != nil {
		t.Fatalf("Fire(eventStart): unexpected error: %v", err)
	}
	if got := m.Current(); got != statePaused {
		t.Errorf("Current() = %q, want %q (overwrite should win)", got, statePaused)
	}
}

func TestIntStateAndEventTypes(t *testing.T) {
	// Exercise the generics with non-string comparable types.
	const (
		off = iota
		on
	)
	type signal int
	const toggle signal = 1

	m := New[int, signal](off)
	m.Permit(off, toggle, on).Permit(on, toggle, off)

	if err := m.Fire(toggle); err != nil {
		t.Fatalf("Fire(toggle): unexpected error: %v", err)
	}
	if got := m.Current(); got != on {
		t.Fatalf("Current() = %d, want %d", got, on)
	}
	if err := m.Fire(toggle); err != nil {
		t.Fatalf("Fire(toggle): unexpected error: %v", err)
	}
	if got := m.Current(); got != off {
		t.Errorf("Current() = %d, want %d", got, off)
	}
}
