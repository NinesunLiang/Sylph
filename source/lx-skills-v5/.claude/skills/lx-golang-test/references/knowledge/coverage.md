# §J Coverage Analysis

## Commands

```
bash# Generate coveragego test -coverprofile=coverage.out ./...

# View in terminalgo tool cover -func=coverage.out

# View in browser (HTML)go tool cover -html=coverage.out

# Coverage for specific packagego test -coverprofile=coverage.out -coverpkg=./pkg/... ./pkg/...
```

## Rules

- Focus on meaningful coverage, not 100%
- Cover: business logic, error paths, edge cases
- Skip: generated code, simple getters/setters, main()
- Use `-coverpkg` to include packages tested indirectly
- Track coverage trends, not absolute numbers
