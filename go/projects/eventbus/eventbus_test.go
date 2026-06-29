package eventbus

import (
	"sync"
	"testing"
	"time"
)

// recv receives one value from ch, reporting whether a value arrived
// before the timeout and whether the channel was closed.
func recv(t *testing.T, ch <-chan Event) (ev Event, ok, timedOut bool) {
	t.Helper()
	select {
	case ev, ok = <-ch:
		return ev, ok, false
	case <-time.After(time.Second):
		return nil, false, true
	}
}

func TestPublishRouting(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		topics  []string // topics to subscribe one channel to each
		publish map[string][]Event
		// want maps a subscriber index to the events it should receive.
		want map[int][]Event
	}{
		{
			name:    "single subscriber single event",
			topics:  []string{"a"},
			publish: map[string][]Event{"a": {1}},
			want:    map[int][]Event{0: {1}},
		},
		{
			name:    "fan out to two subscribers same topic",
			topics:  []string{"a", "a"},
			publish: map[string][]Event{"a": {"x"}},
			want:    map[int][]Event{0: {"x"}, 1: {"x"}},
		},
		{
			name:    "topic isolation",
			topics:  []string{"a", "b"},
			publish: map[string][]Event{"a": {1}, "b": {2}},
			want:    map[int][]Event{0: {1}, 1: {2}},
		},
		{
			name:    "multiple events preserve order",
			topics:  []string{"a"},
			publish: map[string][]Event{"a": {1, 2, 3}},
			want:    map[int][]Event{0: {1, 2, 3}},
		},
		{
			name:    "publish to topic without subscribers is dropped",
			topics:  []string{"a"},
			publish: map[string][]Event{"a": {1}, "ghost": {99}},
			want:    map[int][]Event{0: {1}},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			b := New()
			defer b.Close()

			subs := make([]<-chan Event, len(tt.topics))
			for i, topic := range tt.topics {
				subs[i] = b.Subscribe(topic)
			}

			for topic, events := range tt.publish {
				for _, e := range events {
					b.Publish(topic, e)
				}
			}

			for i, want := range tt.want {
				for j, wantEv := range want {
					gotEv, ok, timedOut := recv(t, subs[i])
					if timedOut {
						t.Fatalf("subscriber %d: timed out waiting for event %d (want %v)", i, j, wantEv)
					}
					if !ok {
						t.Fatalf("subscriber %d: channel closed before event %d (want %v)", i, j, wantEv)
					}
					if gotEv != wantEv {
						t.Errorf("subscriber %d event %d = %v, want %v", i, j, gotEv, wantEv)
					}
				}
			}
		})
	}
}

func TestCloseClosesAllSubscribers(t *testing.T) {
	t.Parallel()

	b := New()
	a1 := b.Subscribe("a")
	a2 := b.Subscribe("a")
	c1 := b.Subscribe("b")

	b.Close()

	for i, ch := range []<-chan Event{a1, a2, c1} {
		if _, ok, timedOut := recv(t, ch); timedOut {
			t.Fatalf("subscriber %d: Close did not close the channel", i)
		} else if ok {
			t.Errorf("subscriber %d: received a value, want closed channel", i)
		}
	}
}

func TestCloseIsIdempotent(t *testing.T) {
	t.Parallel()

	b := New()
	b.Subscribe("a")

	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("second Close panicked: %v", r)
		}
	}()
	b.Close()
	b.Close()
}

func TestPublishAfterCloseIsNoop(t *testing.T) {
	t.Parallel()

	b := New()
	b.Subscribe("a")
	b.Close()

	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("Publish after Close panicked: %v", r)
		}
	}()
	b.Publish("a", 1) // must not panic on a closed channel
}

func TestSubscribeAfterCloseReturnsClosedChannel(t *testing.T) {
	t.Parallel()

	b := New()
	b.Close()

	ch := b.Subscribe("a")
	if _, ok, timedOut := recv(t, ch); timedOut {
		t.Fatal("Subscribe after Close returned an open, empty channel")
	} else if ok {
		t.Error("Subscribe after Close returned a channel that yielded a value")
	}
}

func TestFullBufferDropsWithoutBlocking(t *testing.T) {
	t.Parallel()

	b := NewBuffered(2)
	ch := b.Subscribe("a")

	// Publish more than the buffer can hold; excess must be dropped and
	// Publish must never block.
	done := make(chan struct{})
	go func() {
		for i := 0; i < 10; i++ {
			b.Publish("a", i)
		}
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("Publish blocked when subscriber buffer was full")
	}

	// Exactly buffer-many events should be queued.
	got := 0
	for {
		select {
		case <-ch:
			got++
		default:
			if got != 2 {
				t.Errorf("buffered events = %d, want 2", got)
			}
			return
		}
	}
}

func TestConcurrentPublishSubscribeClose(t *testing.T) {
	t.Parallel()

	b := New()
	var wg sync.WaitGroup

	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			ch := b.Subscribe("topic")
			for ev := range ch { // drains until Close
				_ = ev
			}
		}()
	}

	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			for j := 0; j < 100; j++ {
				b.Publish("topic", n*100+j)
			}
		}(i)
	}

	time.Sleep(10 * time.Millisecond)
	b.Close()
	wg.Wait()
}
