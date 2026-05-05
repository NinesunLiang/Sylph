# Go Version Impact Matrix

| Go Version | Impact | Handling|
|------------|--------|----------|
|< 1.17 | No `t.Setenv()` | Manual set + `t.Cleanup()` restore|
|< 1.18 | No generics, no Fuzz | No generic helpers, no fuzz tests|
|< 1.21 | No `slog` | Use standard `log`|
|< 1.22 | Range var not auto-captured | Parallel tests MUST `tt := tt`|
|≥ 1.22 | Range var auto-captured | No `tt := tt` needed; add comment explaining why |
