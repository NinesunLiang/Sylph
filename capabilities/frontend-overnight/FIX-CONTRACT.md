# FIX CONTRACT — AI 修复契约（违反 = 历史上三次白屏的根因）

## 唯一输入

`.omc/ui-autopilot/<task>/measurements/latest/fix-list.json`

修复动作只允许响应 fix-list 里的条目。禁止修复"自己看出来"但不在列表里的问题
（列表来自 gold 真值，肉眼判断来自截图，后者已被证明不可靠）。

## 允许的修复形式

每一项修复必须能写成四元组：

```
{ file: "src/pages/console/index.module.scss",
  selector: ".card_title",
  property: "font-weight",
  value: "700" }        ← 来自 proto-styles.json 真值
```

- 用 Edit 工具精确修改该 class 的该属性
- 结构修复（缺元素/图标/图片）按 zone 映射表改对应 TSX
- 图标名、图片 URL 以 proto-styles.json 的 lucide class / img src 为准

## 禁止事项（铁律）

1. ❌ 任何形式的**全局查找替换**修 CSS（sed、批量 replace_all 短值）
   — `8px→50%` 曾把 border-radius 打到全站、白屏三次
2. ❌ 视觉模型（Kimi 等）输出的色值/尺寸**直接落盘**
   — 模型输出只能生成"假设"，必须经 extract-styles 真值验证
3. ❌ 修改 gold/ 下任何文件（真值只能由 gold-refresh.sh 刷新）
4. ❌ 一轮修复跨 3 个以上 zone（聚焦，便于回滚归因）
5. ❌ 跳过 gate 直接进入下一轮

## 闭环

```
measure → 读 fix-list → 修 1-2 个 zone → gate --rollback → measure 复测
                                              ↑红灯自动回滚
```

每轮结束必须在 `measurements/iterations.log` 追加一行：
`iter | score(before→after) | zones touched | gate 结果`
