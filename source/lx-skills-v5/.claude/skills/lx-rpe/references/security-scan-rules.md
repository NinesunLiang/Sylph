# 安全扫描规则（lx-rpe Step 4 加载）

## Go 项目

### 必检项（🔴 阻断）

- SQL 注入：拼接 SQL 字符串（使用参数化查询）
- 硬编码密钥：源码含 password/secret/key + 字面量值
- 命令注入：exec.Command 含用户输入
- 路径穿越：文件路径含用户输入未过滤

### 建议项（🟡 警告）

- govulncheck 发现依赖漏洞
- 不安全随机数（math/rand 用于安全场景）
- 无超时的 HTTP 客户端

### 工具链

```
bash# 主扫描lx-security-review

# 降级1：govulncheckgovulncheck ./...

# 降级2：静态模式扫描grep -rn "password\s*=" --include="*.go"grep -rn "exec\.Command" --include="*.go"
```

## 前端项目

### 必检项（🔴 阻断）

- XSS：dangerouslySetInnerHTML + 用户输入
- 硬编码 API Key/Secret（源码中）
- eval() / new Function() 含动态内容

### 工具链

```
bashnpm
audit --productionnpx eslint --rule '{"no-eval": "error"}'

```
