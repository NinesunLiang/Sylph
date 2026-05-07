# §D Test Helpers & Cleanup

## Pattern

```gofu
n
c newTestServer(t *testing.T) *httptest.Server { t.Helper() srv := httptest.NewServer(handler) t.Cleanup(func() { srv.Close() }) return srv}
func mustParseJSON(t *testing.T, data string) map[string]any { t.Helper() var result map[string]any if err := json.Unmarshal([]byte(data), \&result); err != nil { t.Fatalf("invalid JSON: %v", err) } return result}
```

## Rules- ALL helpers MUST call `t.Helper()` first line- ALL resources MUST register `t.Cleanup()`- Use `t.TempDir()` for temp files (auto-cleaned)- Use `t.Setenv()` for env vars (Go ≥ 1.17)- Never recreate helpers that already exist in the project- Helpers should `t.Fatal()` on setup failure, not return error
