# §K CI/CD Integration

## GitHub Actions Example

```yam
l
- name: Test run: go test -race -coverprofile=coverage.out ./...
- name: Check coverage run: | COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}') echo "Coverage: $COVERAGE"
```

## Common CI Commands

```bash
# Full test suite with race detectiongo test -race -count=1 ./...

# Short mode (skip slow tests)go test -short ./...

# With timeoutgo test -timeout 5m ./...

# Verbose for CI logsgo test -v -race ./...
```

## Rules- Always enable `-race` in CI- Use `-count=1` to disable test caching in CI- Set explicit `-timeout` to prevent hung tests- Separate unit tests (fast) from integration tests (build tags)- Cache Go modules in CI (`actions/cache` or `actions/setup-go`)
