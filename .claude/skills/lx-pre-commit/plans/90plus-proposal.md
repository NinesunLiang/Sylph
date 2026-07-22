# lx-pre-commit 修复方案（目标 90+）

## 现状
v2.1.0 | Sonnet-5: ~59/100
P0: 无可执行实现 / 测试策略缺失

## 修复项

### 1. 新增预提交脚本 lx-pre-commit.sh
轻量 bash 脚本，不自建框架，4种项目类型自动检测+执行。
```bash
# 检测项目类型
if [ -f go.mod ]; then
  go build ./... && go test ./... -count=1 -timeout 120s && gofmt -l .
elif [ -f package.json ]; then
  npm run build && npm test -- --bail && npx eslint .
elif [ -f pyproject.toml ]; then
  python -m py_compile **/*.py && pytest --tb=short -x && ruff check .
fi
```

### 2. 可配置超时
SKILL.md 增加超时说明：
| 类型 | 默认超时 | 说明 |
|------|---------|------|
| 编译 | 120s | go build / npm build |
| 测试 | 120s | 单元测试快照 |
| Lint | 60s | 基本格式检查 |

### 3. 失败行为定义
| 结果 | 行为 |
|------|------|
| 编译失败 | ❌ 阻断提交，输出错误 |
| 测试失败 | ❌ 阻断提交，输出失败测试名 |
| Lint 失败 | ⚠️ 不阻断，输出警告 |
| 超时 | ⚠️ 提示手动执行 |

### 4. 测试场景
5个场景：Go项目 / Node项目 / Python项目 / 编译失败 / 测试失败

### 5. 变更日志
CHANGELOG.md 追溯 v2.0.0→v2.1.0

## 不改变的设计
- "不接入治理管线" 保持不变
- 纯指令触发 /lx-pre-commit 不变
- 每次一个任务的轻量定位不变
