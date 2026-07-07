# lx-purify 审计速查表

> 各区审计 bash 命令速查，避免 SKILL.md 膨胀。按需加载。

## skills/ — frontmatter 完整性 + 重复段检测

```bash
# frontmatter 完整性
for f in skills/*/SKILL.md; do
  n=$(grep -c '^name:' "$f"); s=$(grep -c '^status:' "$f"); r=$(grep -c '^role:' "$f")
  [ $n -eq 0 ] || [ $s -eq 0 ] || [ $r -eq 0 ] && echo "⚠️ $f"
done
# 重复段检测
grep -c '错误码与超时规范\|可观测性\|降级策略' skills/*/SKILL.md
```

## hooks/ — 三重验证（不改脚本）

```bash
# ① harness.yaml 声明 vs settings.json 注册一致性
python3 -c "import json; ..."  # 提取注册列表
grep -E '^\s+[a-z_]+:' harness.yaml  # 提取声明
# ② 文件孤立检测
for f in hooks/*.sh; do
  refs=$(grep -l "$f" hooks/*.sh | grep -v "$f")
  [ -z "$refs" ] && echo "⚠️ $f — 孤立"
done
# ③ harness 布尔 vs settings 注册矛盾
```

## source/ — 同步检查

```bash
diff -rq .claude/ source/harness-kit/.claude/ | grep -v 'Only in' | grep -v scheduled_tasks
```
排除 `scheduled_tasks.json`（运行时数据）。

## nodes/ — 分层判定

有 frontmatter = 角色节点（注入 prompt），无 = 工具模板。不是 bug。

## Sub-agent 协议

> ⚠️ 教训：展开框架=150K token→sub-agent 死。必须脱水。

1. 生成 purify-compact.md（~800 字节脱水版）
2. 读被审文件→嵌入 content 到 prompt（不让 sub-agent 自己读）
3. prompt ≤3K token：compact框架 + 文件内容 + 判决指令
4. toolsets=`[]`（内容已嵌入）
5. 同时 spawn Oracle + Meta-Oracle（并行）
6. sub-agent 连续失败 2 次→fallback：主 agent 自行做认知隔离审查
