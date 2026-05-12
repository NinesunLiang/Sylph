# AC Template Example (lx-task-spec Q3 Reference)

## Three-Part AC Format

```
AC-{N} [{Type}]: {Description}
Verification: {Specific command or steps}
Success: {Expected output/state}
Failure: {Failure behavior}
```

## Example

```
AC-1 [Function]: Login endpoint returns 200
Verification: curl -X POST /api/login -d '{"phone":"138xx","code":"1234"}'
Success: HTTP 200 + {"token": "..."}
Failure: HTTP 4xx / 5xx

AC-2 [Test]: Unit tests pass
Verification: go test ./pkg/user/... -v
Success: --- PASS (all test names)
Failure: --- FAIL or compilation error

AC-3 [Boundary]: Empty phone number returns 400
Verification: curl -X POST /api/login -d '{}'
Success: HTTP 400 + {"error": "phone required"}
Failure: HTTP 500 or empty response
```
