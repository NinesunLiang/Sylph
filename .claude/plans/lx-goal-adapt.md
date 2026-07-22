# lx-goal Base适应性方案（送审）

## Boss裁定
lx-goal 是最重要的skill，Base和Enhance都要有。

## Base适应性改造
当前lx-goal的问题：
1. 引用已归档的lx-race(1处) + 已移除的lx-stepwise(1处) ❌
2. 6处SubAgent引用（Base不做SubAgent）❌
3. "无人值守自主执行"定位 → Base应该改为"stepwise有人值守执行"

## 改造方案
1. 删除 lx-race/lx-stepwise 引用
2. 删除 SubAgent 调度段落
3. 改为 stepwise 模式：每步完成后等人类确认再下一步
4. 保留核心：目标澄清→计划→执行→验证→归档
5. 完整自主版保留在Enhance

## 审阅问题
1. Base版的lx-goal应该保留什么能力？
2. 适应性改造是否充分？
3. 还有没有其他需要调整的点？
