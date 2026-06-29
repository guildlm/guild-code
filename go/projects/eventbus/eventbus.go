// Package eventbus provides a small, concurrency-safe, in-process
// topic-based publish/subscribe event bus built on channels and the
// sync package.
//
// A Bus fans each published Event out to every channel that is currently
// subscribed to the Event's topic. Subscriber channels are buffered;
// sends are non-blocking, so a slow subscriber whose buffer is full will
// drop events rather than stall the publisher or other subscribers.
package eventbus

import "sync"

// DefaultBuffer is the per-subscriber channel buffer size used by New.
const DefaultBuffer = 16

// Event is an arbitrary value delivered to the subscribers of a topic.
type Event any

// Bus is a concurrency-safe topic-based publish/subscribe event bus.
//
// The zero value is not usable; create a Bus with New or NewBuffered.
// All methods are safe for concurrent use by multiple goroutines.
type Bus struct {
	mu     sync.RWMutex
	subs   map[string][]chan Event
	buffer int
	closed bool
}

// New returns an empty Bus whose subscriber channels are buffered with
// DefaultBuffer slots.
func New() *Bus {
	return NewBuffered(DefaultBuffer)
}

// NewBuffered returns an empty Bus whose subscriber channels are buffered
// with the given number of slots. A negative size is treated as zero
// (an unbuffered channel).
func NewBuffered(buffer int) *Bus {
	if buffer < 0 {
		buffer = 0
	}
	return &Bus{
		subs:   make(map[string][]chan Event),
		buffer: buffer,
	}
}

// Subscribe registers a new subscriber for the given topic and returns a
// receive-only channel on which the subscriber will receive published
// events. Each call returns an independent channel, so the same topic may
// have many subscribers.
//
// If the Bus is already closed, Subscribe returns an already-closed
// channel so that a range over it terminates immediately.
func (b *Bus) Subscribe(topic string) <-chan Event {
	ch := make(chan Event, b.buffer)

	b.mu.Lock()
	defer b.mu.Unlock()

	if b.closed {
		close(ch)
		return ch
	}
	b.subs[topic] = append(b.subs[topic], ch)
	return ch
}

// Publish delivers event to every current subscriber of topic. Delivery
// is non-blocking: if a subscriber's buffer is full, the event is dropped
// for that subscriber. Publishing to a topic with no subscribers, or to a
// closed Bus, is a no-op.
func (b *Bus) Publish(topic string, event Event) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	if b.closed {
		return
	}
	for _, ch := range b.subs[topic] {
		select {
		case ch <- event:
		default:
		}
	}
}

// Close closes every subscriber channel and marks the Bus as closed.
// After Close returns, Publish is a no-op and Subscribe yields
// already-closed channels. Close is idempotent: calling it more than once
// is safe and has no further effect.
func (b *Bus) Close() {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.closed {
		return
	}
	b.closed = true
	for topic, chans := range b.subs {
		for _, ch := range chans {
			close(ch)
		}
		delete(b.subs, topic)
	}
}
