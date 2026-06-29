// Package ledger implements a small, concurrency-safe in-memory ledger that
// tracks integer account balances and supports transfers with overdraft
// protection.
//
// Amounts are expressed in the smallest indivisible unit of the currency
// (for example cents) and are therefore represented as int64 to avoid the
// rounding pitfalls of floating-point arithmetic.
package ledger

import (
	"errors"
	"fmt"
	"sort"
	"sync"
)

// ErrInsufficientFunds is the sentinel error returned (wrapped) by Transfer and
// Withdraw when an account does not hold enough funds to cover an operation.
// Callers should test for it with errors.Is.
var ErrInsufficientFunds = errors.New("insufficient funds")

// ErrInvalidAmount is the sentinel error returned (wrapped) when an operation is
// asked to move a non-positive amount.
var ErrInvalidAmount = errors.New("invalid amount")

// ErrSameAccount is returned by Transfer when the source and destination
// accounts are identical, which would otherwise be a meaningless no-op.
var ErrSameAccount = errors.New("source and destination accounts are the same")

// Ledger is a concurrency-safe collection of named account balances. The zero
// value is not usable; obtain a Ledger from NewLedger.
type Ledger struct {
	mu       sync.RWMutex
	balances map[string]int64
}

// NewLedger returns an empty, ready-to-use Ledger.
func NewLedger() *Ledger {
	return &Ledger{balances: make(map[string]int64)}
}

// Balance returns the current balance of the named account. Accounts that have
// never been touched implicitly have a balance of zero.
func (l *Ledger) Balance(account string) int64 {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.balances[account]
}

// Deposit adds amount to the named account, creating the account if necessary.
// The amount must be strictly positive; otherwise a wrapped ErrInvalidAmount is
// returned and no balance is changed.
func (l *Ledger) Deposit(account string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("deposit of %d into %q: %w", amount, account, ErrInvalidAmount)
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	l.balances[account] += amount
	return nil
}

// Withdraw removes amount from the named account. The amount must be strictly
// positive (else wrapped ErrInvalidAmount) and may not exceed the current
// balance (else wrapped ErrInsufficientFunds). On error the balance is
// unchanged.
func (l *Ledger) Withdraw(account string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("withdrawal of %d from %q: %w", amount, account, ErrInvalidAmount)
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.balances[account] < amount {
		return fmt.Errorf("withdrawal of %d from %q (balance %d): %w",
			amount, account, l.balances[account], ErrInsufficientFunds)
	}
	l.balances[account] -= amount
	return nil
}

// Transfer atomically moves amount from the source account to the destination
// account. It enforces overdraft protection: if the source account holds less
// than amount, a wrapped ErrInsufficientFunds is returned and neither balance
// changes.
//
// The amount must be strictly positive (else wrapped ErrInvalidAmount) and the
// two accounts must differ (else wrapped ErrSameAccount).
func (l *Ledger) Transfer(from, to string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("transfer of %d from %q to %q: %w", amount, from, to, ErrInvalidAmount)
	}
	if from == to {
		return fmt.Errorf("transfer from %q to %q: %w", from, to, ErrSameAccount)
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	if l.balances[from] < amount {
		return fmt.Errorf("transfer of %d from %q (balance %d) to %q: %w",
			amount, from, l.balances[from], to, ErrInsufficientFunds)
	}

	l.balances[from] -= amount
	l.balances[to] += amount
	return nil
}

// Total returns the sum of every account balance in the ledger. Because
// Transfer conserves value, Total is invariant across any sequence of
// transfers and changes only via Deposit and Withdraw.
func (l *Ledger) Total() int64 {
	l.mu.RLock()
	defer l.mu.RUnlock()
	var sum int64
	for _, v := range l.balances {
		sum += v
	}
	return sum
}

// Accounts returns the names of every account known to the ledger, sorted
// lexicographically. The returned slice is a copy and may be freely modified by
// the caller.
func (l *Ledger) Accounts() []string {
	l.mu.RLock()
	defer l.mu.RUnlock()
	names := make([]string, 0, len(l.balances))
	for name := range l.balances {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}
