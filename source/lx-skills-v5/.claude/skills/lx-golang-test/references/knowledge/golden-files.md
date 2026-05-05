# §E Golden File Tests

## Pattern

```
gofunc TestOutput(t *testing.T) { got := generateOutput(input)
 golden := filepath.Join("testdata", t.Name()+".golden") if *update { os.WriteFile(golden, got, 0644) } want, err := os.ReadFile(golden) if err != nil { t.Fatalf("read golden: %v", err) } if diff := cmp.Diff(string(want), string(got)); diff != "" { t.Errorf("mismatch (-want +got):\n%s", diff) }}
var update = flag.Bool("update", false, "update golden files")
```

## When to Use

- Complex output (JSON, HTML, config files)
- Output too large for inline assertions
- Need visual diff on failure

## Rules

- Golden files in `testdata/` directory
- Update flag: `-update` to regenerate
- Use `cmp.Diff` for readable diffs
- Commit golden files to version control
