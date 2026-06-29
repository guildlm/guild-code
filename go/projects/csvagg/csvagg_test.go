package csvagg

import (
	"errors"
	"reflect"
	"strings"
	"testing"
)

func TestGroupSum(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		keyCol  string
		valCol  string
		want    map[string]int
		wantErr bool
	}{
		{
			name:   "basic aggregation",
			input:  "region,amount\nwest,10\neast,5\nwest,7\n",
			keyCol: "region",
			valCol: "amount",
			want:   map[string]int{"west": 17, "east": 5},
		},
		{
			name:   "single group",
			input:  "k,v\na,1\na,2\na,3\n",
			keyCol: "k",
			valCol: "v",
			want:   map[string]int{"a": 6},
		},
		{
			name:   "header only yields empty map",
			input:  "region,amount\n",
			keyCol: "region",
			valCol: "amount",
			want:   map[string]int{},
		},
		{
			name:   "negative values",
			input:  "k,v\nx,5\nx,-3\ny,-10\n",
			keyCol: "k",
			valCol: "v",
			want:   map[string]int{"x": 2, "y": -10},
		},
		{
			name:   "whitespace around values is trimmed",
			input:  "k,v\na, 4 \na,\t6\n",
			keyCol: "k",
			valCol: "v",
			want:   map[string]int{"a": 10},
		},
		{
			name:   "empty string key is a valid group",
			input:  "k,v\n,3\n,4\n",
			keyCol: "k",
			valCol: "v",
			want:   map[string]int{"": 7},
		},
		{
			name:    "missing key column",
			input:   "k,v\na,1\n",
			keyCol:  "nope",
			valCol:  "v",
			wantErr: true,
		},
		{
			name:    "missing value column",
			input:   "k,v\na,1\n",
			keyCol:  "k",
			valCol:  "nope",
			wantErr: true,
		},
		{
			name:    "non-integer value",
			input:   "k,v\na,oops\n",
			keyCol:  "k",
			valCol:  "v",
			wantErr: true,
		},
		{
			name:    "empty input has no header",
			input:   "",
			keyCol:  "k",
			valCol:  "v",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := GroupSum(strings.NewReader(tt.input), tt.keyCol, tt.valCol)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error, got nil (result=%v)", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("GroupSum() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestParseEmptyIsError(t *testing.T) {
	_, err := Parse(strings.NewReader(""))
	if err == nil {
		t.Fatal("expected error parsing empty input, got nil")
	}
}

func TestGroupSumShortRow(t *testing.T) {
	// A ragged row that is too short to contain valCol. encoding/csv normally
	// rejects ragged rows, so use FieldsPerRecord-disabled parsing via Table
	// constructed directly.
	tbl := &Table{
		Header: []string{"k", "v"},
		Rows:   [][]string{{"onlykey"}},
	}
	_, err := tbl.GroupSum("k", "v")
	if err == nil {
		t.Fatal("expected error for short row, got nil")
	}
	if !strings.Contains(err.Error(), "fields") {
		t.Errorf("error %q does not mention field count", err.Error())
	}
}

func TestColumnIndexError(t *testing.T) {
	tbl := &Table{Header: []string{"a", "b"}}
	_, err := tbl.columnIndex("missing")
	if err == nil {
		t.Fatal("expected error for missing column")
	}
	var _ error = err // ensure it satisfies error
	if errors.Unwrap(err) != nil {
		// columnIndex errors are not wrapped; this is informational only.
		t.Logf("unexpected wrapped error: %v", err)
	}
}
