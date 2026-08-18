# Prototype — XSimpleChat chat inbox

- 产品名: xsimplechat
- 原型 URL: https://xsimplechat.com/chat?session=inbox
- kind: interactive（真实可交互站点；会话页 = 三栏聊天工作台）
- 捕获资产（只读复用）: `.omc/ui-autopilot/xsimplechat/`
  - interactions/inventory.json（6 元素 / 2 OVERLAY）
  - detail-pages/contents.json（chat-inbox 29 DOM 文本节点 + 坐标/字号）
  - detail-pages/chat-inbox.png（1440x900 目标页截图）
  - gold/chat.png（2880x1800 金样）
  - cdp-real-states.json（22 元素四态矩阵）
- 还原范围: /chat?session=inbox 单页（静态 + 交互 + 二级弹窗），复杂组件用 antd
- 输入成熟度: prototype=present, prd=absent, api_doc=pending → api_contract_status: inferred
