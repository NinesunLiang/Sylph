
## Format

| Scenario | Input | Expected Output | Priority |
|----------|-------|-----------------|----------|
| Normal path | Valid input | Success response | P0 |
| Boundary | Edge input | Boundary behavior | P1 |
| Error path | Invalid input | Error response | P1 |
| Concurrency | Concurrent requests | Consistency | P2 |

## Example

| Scenario | Input | Expected | Priority |
|----------|-------|----------|----------|
| Normal login | Registered phone + correct code | 200 + token | P0 |
| Expired code | Registered phone + expired code | 400 "code expired" | P1 |
| Phone not found | Unregistered phone | 400 "user not found" | P1 |
| Rate limiting | >5 requests within 1s | 429 "too many requests" | P2 |
