# lx-pre-commit 测试场景

## 场景1: Go项目
```bash
cd /tmp/test-go
go mod init test
echo 'package main; func main() { println("hello") }' > main.go
lx-pre-commit
# 预期: go build ✅ → test(无测试跳过) → gofmt ✅
```

## 场景2: Node项目
```bash
cd /tmp/test-node
npm init -y
echo 'console.log("hello")' > index.js
lx-pre-commit
# 预期: npm build(无脚本→警告) → test(无→警告) → eslint ✅
```

## 场景3: Python项目
```bash
cd /tmp/test-py
echo -e '[project]\nname="test"\nversion="0.1.0"' > pyproject.toml
echo 'print("hello")' > main.py
lx-pre-commit
# 预期: py_compile ✅ → test(无→跳过) → ruff ✅
```

## 场景4: 空仓库
```bash
cd /tmp/test-empty
lx-pre-commit
# 预期: 未知项目类型 → 跳过 → exit 0
```

## 场景5: 编译失败
```bash
cd /tmp/test-fail
echo 'package main; func main() { bad syntax }' > main.go
lx-pre-commit
# 预期: go build ❌ → 阻断 → exit 1
```

## 场景6: 测试失败
```bash
cd /tmp/test-test-fail
go mod init test
echo 'package main; func main() {}' > main.go
echo 'package main; import "testing"; func TestFail(t *testing.T) { t.Error("fail") }' > main_test.go
lx-pre-commit
# 预期: build ✅ → test ❌(1 failure) → 阻断 → exit 1
```

## 场景7: 多语言项目
```bash
cd /tmp/test-multi
go mod init test
npm init -y
lx-pre-commit
# 预期: 检测到 go(优先级高) → 走Go路径
```

## 场景8: 无脚本(应有优雅降级)
```bash
cd /tmp/test-no-script
lx-pre-commit
# 预期: 未知项目类型 → skip → exit 0
```
