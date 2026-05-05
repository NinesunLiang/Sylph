# Mock Strategy Quick Reference

| Dependency Type | Recommended Strategy|
|----------------|---------------------|
|Interface | Handwritten Mock struct (simple) / gomock (complex interaction)|
|HTTP external | `httptest.NewServer()` / handwritten `RoundTripper`|
|Database | Interface abstraction + Mock / `sqlmock`|
|Filesystem | `t.TempDir()` + real files / `io/fs.FS` interface|
|Time | Inject `clock` interface / parameterized time (no `time.Sleep`)|
|Env vars | `t.Setenv()` (Go ≥ 1.17) / manual + `t.Cleanup()`|
|Random | Inject `rand.Source` / fixed seed |
