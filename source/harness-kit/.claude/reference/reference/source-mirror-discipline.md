# Source Mirror 同步纪律

> package-release.sh 发布时 root → source 同步规则。开发源 + 分发源双源管理。

## 同步文件

| 路径 | 方式 |
|------|------|
| `.claude/hooks/*` | `rsync --delete` 全镜像 |
| `.claude/scripts/*` | `rsync --delete` 全镜像 |
| `.claude/references/*` | `rsync --delete` 全镜像 |
| `.claude/kernel.md`, `harness.yaml`, `settings.json`, `index.md` | 直接 cp |
| `anti-patterns.md`, `claude-next.md` | 直接 cp |
| `.cursor/`, `.opencode/`, `.hooks/` | `rsync --delete` |
| `CLAUDE.md` | 直接 cp（字节相同，`@AGENTS.md` 各自指向本目录） |

## 有意不同

- **AGENTS.md** — 开发源=紧凑路由表(74行)，分发源=完整治理文档(1261行)

## 验证

```bash
bash .claude/scripts/audit-hooks.sh --check-source-mirror
```
