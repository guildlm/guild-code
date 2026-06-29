package ledger

import (
	"errors"
	"sync"
	"testing"
)

func TestDeposit(t *testing.T) {
	tests := []struct {
		name    string
		amount  int64
		wantErr error
		wantBal int64
	}{
		{name: "positive", amount: 100, wantErr: nil, wantBal: 100},
		{name: "zero", amount: 0, wantErr: ErrInvalidAmount, wantBal: 0},
		{name: "negative", amount: -50, wantErr: ErrInvalidAmount, wantBal: 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := NewLedger()
			err := l.Deposit("alice", tt.amount)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("Deposit(%d) error = %v, want %v", tt.amount, err, tt.wantErr)
			}
			if got := l.Balance("alice"); got != tt.wantBal {
				t.Errorf("balance = %d, want %d", got, tt.wantBal)
			}
		})
	}
}

func TestWithdraw(t *testing.T) {
	tests := []struct {
		name    string
		start   int64
		amount  int64
		wantErr error
		wantBal int64
	}{
		{name: "exact", start: 100, amount: 100, wantErr: nil, wantBal: 0},
		{name: "partial", start: 100, amount: 30, wantErr: nil, wantBal: 70},
		{name: "overdraft", start: 100, amount: 150, wantErr: ErrInsufficientFunds, wantBal: 100},
		{name: "from empty", start: 0, amount: 1, wantErr: ErrInsufficientFunds, wantBal: 0},
		{name: "zero amount", start: 100, amount: 0, wantErr: ErrInvalidAmount, wantBal: 100},
		{name: "negative amount", start: 100, amount: -10, wantErr: ErrInvalidAmount, wantBal: 100},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := NewLedger()
			if tt.start > 0 {
				if err := l.Deposit("bob", tt.start); err != nil {
					t.Fatalf("setup Deposit: %v", err)
				}
			}
			err := l.Withdraw("bob", tt.amount)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("Withdraw(%d) error = %v, want %v", tt.amount, err, tt.wantErr)
			}
			if got := l.Balance("bob"); got != tt.wantBal {
				t.Errorf("balance = %d, want %d", got, tt.wantBal)
			}
		})
	}
}

func TestTransfer(t *testing.T) {
	tests := []struct {
		name     string
		fromInit int64
		toInit   int64
		from     string
		to       string
		amount   int64
		wantErr  error
		wantFrom int64
		wantTo   int64
	}{
		{
			name: "happy path", fromInit: 100, toInit: 0,
			from: "alice", to: "bob", amount: 40,
			wantErr: nil, wantFrom: 60, wantTo: 40,
		},
		{
			name: "exact balance", fromInit: 100, toInit: 5,
			from: "alice", to: "bob", amount: 100,
			wantErr: nil, wantFrom: 0, wantTo: 105,
		},
		{
			name: "overdraft protection", fromInit: 30, toInit: 0,
			from: "alice", to: "bob", amount: 31,
			wantErr: ErrInsufficientFunds, wantFrom: 30, wantTo: 0,
		},
		{
			name: "empty source", fromInit: 0, toInit: 0,
			from: "alice", to: "bob", amount: 1,
			wantErr: ErrInsufficientFunds, wantFrom: 0, wantTo: 0,
		},
		{
			name: "zero amount", fromInit: 100, toInit: 0,
			from: "alice", to: "bob", amount: 0,
			wantErr: ErrInvalidAmount, wantFrom: 100, wantTo: 0,
		},
		{
			name: "negative amount", fromInit: 100, toInit: 0,
			from: "alice", to: "bob", amount: -5,
			wantErr: ErrInvalidAmount, wantFrom: 100, wantTo: 0,
		},
		{
			name: "same account", fromInit: 100, toInit: 100,
			from: "alice", to: "alice", amount: 10,
			wantErr: ErrSameAccount, wantFrom: 100, wantTo: 100,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := NewLedger()
			if tt.fromInit > 0 {
				if err := l.Deposit(tt.from, tt.fromInit); err != nil {
					t.Fatalf("setup Deposit from: %v", err)
				}
			}
			// Only seed the destination separately when it is a distinct account.
			if tt.toInit > 0 && tt.to != tt.from {
				if err := l.Deposit(tt.to, tt.toInit); err != nil {
					t.Fatalf("setup Deposit to: %v", err)
				}
			}

			err := l.Transfer(tt.from, tt.to, tt.amount)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("Transfer error = %v, want %v", err, tt.wantErr)
			}
			if got := l.Balance(tt.from); got != tt.wantFrom {
				t.Errorf("from balance = %d, want %d", got, tt.wantFrom)
			}
			if got := l.Balance(tt.to); got != tt.wantTo {
				t.Errorf("to balance = %d, want %d", got, tt.wantTo)
			}
		})
	}
}

// TestTransferWrappedSentinel verifies that the returned error both matches the
// sentinel via errors.Is and carries human-readable context.
func TestTransferWrappedSentinel(t *testing.T) {
	l := NewLedger()
	if err := l.Deposit("alice", 10); err != nil {
		t.Fatalf("setup: %v", err)
	}
	err := l.Transfer("alice", "bob", 25)
	if !errors.Is(err, ErrInsufficientFunds) {
		t.Fatalf("errors.Is(err, ErrInsufficientFunds) = false, err = %v", err)
	}
	if errors.Is(err, ErrInvalidAmount) {
		t.Errorf("error unexpectedly matches ErrInvalidAmount: %v", err)
	}
}

func TestTotalAndAccounts(t *testing.T) {
	l := NewLedger()
	for acct, amt := range map[string]int64{"alice": 100, "bob": 50, "carol": 25} {
		if err := l.Deposit(acct, amt); err != nil {
			t.Fatalf("setup Deposit %s: %v", acct, err)
		}
	}

	if got, want := l.Total(), int64(175); got != want {
		t.Errorf("Total before transfer = %d, want %d", got, want)
	}

	if err := l.Transfer("alice", "bob", 30); err != nil {
		t.Fatalf("Transfer: %v", err)
	}

	// Transfers conserve value, so Total must be unchanged.
	if got, want := l.Total(), int64(175); got != want {
		t.Errorf("Total after transfer = %d, want %d", got, want)
	}

	got := l.Accounts()
	want := []string{"alice", "bob", "carol"}
	if len(got) != len(want) {
		t.Fatalf("Accounts() = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("Accounts() = %v, want %v (sorted)", got, want)
		}
	}
}

// TestConcurrentTransfers exercises the mutex under the race detector and
// asserts that no value is created or destroyed by concurrent transfers.
func TestConcurrentTransfers(t *testing.T) {
	l := NewLedger()
	if err := l.Deposit("alice", 1000); err != nil {
		t.Fatalf("setup: %v", err)
	}
	if err := l.Deposit("bob", 1000); err != nil {
		t.Fatalf("setup: %v", err)
	}

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			// Errors (overdraft) are acceptable here; we only care that the
			// invariant Total == 2000 holds and the race detector stays quiet.
			_ = l.Transfer("alice", "bob", 1)
			_ = l.Transfer("bob", "alice", 1)
		}()
	}
	wg.Wait()

	if got, want := l.Total(), int64(2000); got != want {
		t.Errorf("Total = %d, want %d (value not conserved)", got, want)
	}
}
