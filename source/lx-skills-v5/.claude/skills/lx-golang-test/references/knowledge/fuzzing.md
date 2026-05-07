# §H Fuzz Testing (Go ≥ 1.18)

## Pattern

```gofu
n
c FuzzParseInput(f *testing.F) { // Seed corpus f.Add("valid input") f.Add("") f.Add("边界值")
 f.Fuzz(func(t *testing.T, input string) { result, err := ParseInput(input) if err != nil { return // invalid input is OK } // Verify invariants on valid output if result.Len() < 0 { t.Errorf("negative length: %d", result.Len()) } })}
```

## Run Commands

```bash
g
o
test -fuzz=FuzzParseInput -fuzztime=30s ./pkg/go test -fuzz=. -fuzztime=1m ./...

```

## When to Use- Input parsing/validation functions- Serialization/deserialization roundtrips- Functions that should never panic

## Rules- Requires Go ≥ 1.18 (check go.mod!)- Seed corpus with known edge cases- Test invariants, not specific outputs- Fuzz targets must not call `t.Parallel()`- Corpus stored in `testdata/fuzz/`
