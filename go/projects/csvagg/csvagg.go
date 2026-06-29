// Package csvagg parses CSV data and aggregates integer values grouped by a
// key column. It relies only on the Go standard library.
package csvagg

import (
	"encoding/csv"
	"fmt"
	"io"
	"strconv"
	"strings"
)

// Table holds parsed CSV data: a header row and the data rows beneath it.
type Table struct {
	Header []string
	Rows   [][]string
}

// Parse reads CSV data from r, treating the first record as the header.
// It returns an error if the data is malformed or if no header is present.
func Parse(r io.Reader) (*Table, error) {
	reader := csv.NewReader(r)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("csvagg: read: %w", err)
	}
	if len(records) == 0 {
		return nil, fmt.Errorf("csvagg: empty input: no header row")
	}
	return &Table{
		Header: records[0],
		Rows:   records[1:],
	}, nil
}

// columnIndex returns the zero-based position of name within the header.
// Matching is exact and case-sensitive.
func (t *Table) columnIndex(name string) (int, error) {
	for i, h := range t.Header {
		if h == name {
			return i, nil
		}
	}
	return 0, fmt.Errorf("csvagg: column %q not found in header %v", name, t.Header)
}

// GroupSum groups the table rows by the value in keyCol and sums the integer
// values found in valCol for each group. The result maps each distinct key to
// its accumulated sum.
//
// An error is returned if either column name is missing, if a row is too short
// to contain the requested columns, or if a value cell is not a valid integer.
func (t *Table) GroupSum(keyCol, valCol string) (map[string]int, error) {
	keyIdx, err := t.columnIndex(keyCol)
	if err != nil {
		return nil, err
	}
	valIdx, err := t.columnIndex(valCol)
	if err != nil {
		return nil, err
	}

	sums := make(map[string]int)
	for rowNum, row := range t.Rows {
		if keyIdx >= len(row) || valIdx >= len(row) {
			return nil, fmt.Errorf("csvagg: row %d has %d fields, need at least %d",
				rowNum+1, len(row), max(keyIdx, valIdx)+1)
		}
		key := row[keyIdx]
		raw := strings.TrimSpace(row[valIdx])
		v, err := strconv.Atoi(raw)
		if err != nil {
			return nil, fmt.Errorf("csvagg: row %d: value %q in column %q is not an integer: %w",
				rowNum+1, row[valIdx], valCol, err)
		}
		sums[key] += v
	}
	return sums, nil
}

// GroupSum is a convenience wrapper that parses r and aggregates in one call.
func GroupSum(r io.Reader, keyCol, valCol string) (map[string]int, error) {
	t, err := Parse(r)
	if err != nil {
		return nil, err
	}
	return t.GroupSum(keyCol, valCol)
}
