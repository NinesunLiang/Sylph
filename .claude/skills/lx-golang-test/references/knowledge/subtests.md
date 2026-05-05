# §C Subtests & Parallel

## Pattern

```gofu
n
c
TestGroup(t *testing.T) { t.Run("subgroup", func(t *testing.T) { t.Run("case1", func(t *testing.T) { t.Parallel() // test logic }) t.Run("case2", func(t *testing.T) { t.Parallel() // test logic }) })}

```

## When to Use- Logically grouped test scenarios- Independent tests that can run in parallel- Shared setup with `t.Cleanup()`

## Rules- `t.Parallel()` only for truly independent tests- Never parallel if tests share mutable state- Go < 1.22: capture range var with `tt := tt`- Use `t.Cleanup()` for teardown, not `defer` in subtests
