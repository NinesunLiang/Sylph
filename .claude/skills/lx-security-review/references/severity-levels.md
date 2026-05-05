# Severity Levels

| Level | Definition | Examples | Gate|
|-------|-----------|----------|------|
|🔴 Critical | Directly exploitable, data leak/system compromise | Hardcoded secrets, SQL injection (string concat), command injection | Block + fix|
|🟠 High | Auth bypass, sensitive data exposure | Hardcoded token, password in logs, missing auth check, path traversal | Block + fix|
|🟡 Medium | Weakens security posture, aids attack | No input validation, error leaks internals, missing authz, SSRF risk | Block + fix|
|🟢 Low | Best practice gap, low risk | Sensitive comments, missing rate limit, missing timeout | Warn, allow |
