# 前端编码规范（lx-rpe Step 2/3 前端项目加载）

## 架构约束
- Pages → Components → Hooks → Services 分层- Controller/Route 禁止直接操作 DB，通过 Service/Repository 层- 禁止 any，unknown 仅在边界使用且必须类型收敛

## React 规范
- 禁止 useEffect 无限循环（deps 数组必须完整）- 禁止组件内定义组件（闭包组件每次渲染重建）- Props 接口必须显式定义（禁止 any/object）- 禁止过深 prop drilling（超过3层用 Context 或状态管理）

## TypeScript
- strict mode 必须开启- 禁止类型断言（as）替代正确类型声明- API 响应必须有完整类型定义

## 性能
- 列表渲染必须有 key（禁止用 index）- 大列表用虚拟滚动（>100 条）- 图片必须有 width/height 防 CLS

## 反模式（禁止）
- 直接修改 state（必须不可变更新）- 在渲染函数中定义常量/函数- 滥用 useEffect（能用派生计算的不用 effect）
