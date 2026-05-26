# 战报交付

拆解完成后输出：

```markdown
# ⚔️ 一人成军拆解完成

共拆分出 N 个正交功能分支：

1. **feat-xxx**：负责...
2. **feat-yyy**：负责...

## 🚀 并发启动指令

请打开 N 个终端，分别运行：

```bash
# 终端 1
/lx-rpe prd/{sub_prd_name}/feat-xxx

# 终端 2
/lx-rpe prd/{sub_prd_name}/feat-yyy
```

底层的 OMA 文件锁已就绪，冲突将自动挂起排队。

─── 方向指引 ───
📍 拆解完成，{N} 个 feature 已就绪。

建议下一步:
  1. /lx-rpe prd/{sub_prd_name}/feat-{name} — 推荐 ✓
  2. 并行启动多个 /lx-rpe — 无依赖的 feature 可同时开发
  3. 自定义操作
```
