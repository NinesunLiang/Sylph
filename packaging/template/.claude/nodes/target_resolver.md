# Node: target_resolver

# node: target_resolver
# input:
# - user_args: string (optional) — \$ARGUMENTS 用户传入参数
# - git_diff_cmd: string (optional, default: "git diff HEAD --name-only --diff-filter=AM")
# - include_patterns: array of string (optional, default: ["*"])
# - exclude_patterns: array of string (optional, default: ["node_modules/", "dist/", "vendor/"])
# output:
# - scan_target: scan_target.yaml — 解析后的目标定义
# triggers:
# - on_success: target_resolved
# - on_empty: no_target_found

> 从 \$ARGUMENTS 或 git diff 解析扫描/审查/验证目标
> 复用: code-review, security-review, browser-verify, pre-commit, pre-push, perf-analysis, web-perf, react-review, style-guide, golang-test

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| user_args | string | 否 | — | 用户传入的目标（文件/目录/URL/函数名） |
| include_patterns | string[] | 否 | `["*"]` | 保留的文件模式 |
| exclude_patterns | string[] | 否 | `["node_modules/", "dist/", "vendor/"]` | 排除的路径模式 |

## 输出契约

输出 `scan_target` schema（`schemas/atomic/scan_target.yaml`）：
```yaml
target_type: file | dir | commit | url | function | component
target_path: string # 解析后的路径/URL
scope: staged | uncommitted | committed | directory | single_file | url
exclude_patterns: string[]
derived_from: arguments | git_diff | user_prompt | auto_detected
```

## 流程

1. 若 `user_args` 非空 → 解析类型（file/dir/commit/url/function/component）
2. 若 `user_args` 为空 → 执行 `git diff --name-only --diff-filter=AM`
3. 按 `include_patterns` / `exclude_patterns` 过滤
4. 过滤后为空 → 触发 `on_empty: no_target_found`
5. 输出 `scan_target` schema
