# Go Security Scan Rules (15 items)

Execute ALL rules against changed files. Parallel execution allowed.

## 🔴 Critical (6 rules)

| # | Scan Item | rg Command|
|---|-----------|------------|
|S01 | Hardcoded key/token | `rg -i '(api[_-]?key\|secret\|token)\s*=\s*"[^"]{10,}"'`|
|S02 | Hardcoded password | `rg -i 'password\s*=\s*"[^"]{3,}"'`|
|S03 | Key pattern (prefix) | `rg '(sk-\|pk-\|sk_live\|pk_live\|eyJ)[a-zA-Z0-9+/]{20,}'`|
|S04 | SQL injection (fmt.Sprintf) | `rg 'fmt\.Sprintf\s*\(.*"(SELECT\|INSERT\|UPDATE\|DELETE)'`|
|S05 | SQL injection (string concat) | `rg '"(SELECT\|INSERT\|UPDATE\|DELETE).*"\s*\+'`|
|S06 | Command injection | `rg 'exec\.Command\s*\(.*\+'` |

## 🟠 High (2 rules)

| # | Scan Item | rg Command|
|---|-----------|------------|
|S07 | Path traversal | `rg 'filepath\.(Join\|Clean)\s*\([^)]*r\.(URL\|FormValue\|Header)'`|
|S08 | Sensitive data in logs | `rg -i '(log\|logx\|logc)\.(Print\|Printf\|Println\|Fatal\|Error\|Info\|Infof\|Infow\|Debug\|Debugf\|Slow\|Slowf\|Severe\|Severef).*\b(password\|token\|secret\|key\|cvv)\b'` |

## 🟡 Medium (4 rules)

| # | Scan Item | rg Command|
|---|-----------|------------|
|S09 | Missing input validation | `rg 'r\.(URL\.Query()\|FormValue\|PostFormValue)\(' \| rg -v '(validate\|sanitize\|bind\|Bind\|Parse\|ShouldBind)'`|
|S10 | Error message leak | `rg 'http\.Error\s*\(.*err\.(Error\|String)\(\)'`|
|S11 | Missing authz (sensitive ops) | `rg 'func.*Handler.*\b(Delete\|Remove\|Admin\|Drop)\b' \| rg -v '(auth\|authorize\|checkPermission\|middleware\|Auth\|JWT)'`|
|S12 | SSRF risk | `rg 'http\.Get\s*\(.*r\.(URL\|FormValue\|Header)'` |

## 🟢 Low (3 rules)

| # | Scan Item | rg Command|
|---|-----------|------------|
|S13 | Sensitive comments | `rg -i '//.*\b(password\|secret\|key\|token\|todo.*auth)\b'`|
|S14 | Missing timeout | `rg 'http\.DefaultClient\b'`|
|S15 | Goroutine leak risk | `rg 'go func\(' \| rg -v '(defer\|context\|cancel\|wg\.\|Done\(\)\|WithTimeout\|WithCancel)'` |
