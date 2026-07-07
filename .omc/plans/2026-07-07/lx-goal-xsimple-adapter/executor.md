# lx-goal 执行报告

## 目标
把本地的 Claude Code 终端请求打包给 xsimplechat GPT-5.5 回答；正确解析返回数据包（含 SSE）；完成 chat 转 coding 模式的代理

## 执行摘要
适配器已完成并运行在 `http://127.0.0.1:8765`。CDP 背景监控自动维护 session 有效性（cookies 每 30s 刷新，auth 在用户发消息时自动捕获 HS256 token）。非流式和流式均返回 OpenAI 兼容格式。

## 已完成
1. **CDP 方案一（后台监控）** — 适配器启动时自动连接 Chrome 9222，监听 `Network.requestWillBeSentExtraInfo` 捕获 HS256 x-ai-chat-auth，每 30s 轮询 `document.cookie` 刷新 cookies
2. **SSE 解析** — xsimplechat 使用自定义 SSE 格式 `event: text / data: "chunk"`，已正确解析为 OpenAI 标准 `data: {"choices":[{"delta":{"content":"..."}}]}`
3. **模型映射** — gpt-5.5 / opus-4.8 / sonnet-4.8 / deepseek-r1
4. **HS256 过滤** — 排除 CDP 误抓 Clerk RS256 token，通过 path 过滤 + alg 签名头双重校验

## 已验证
- 非流式：`"Hello"` ✅
- 流式 SSE chunk：`"Hi."` ✅
- CDP 自动刷新：auth_refreshes=1, cookie_refreshes=22 ✅

## ⚠️ 未实现
### 请求代理走 CDP（方案三）
通过 CDP `Fetch.enable` 代理所有请求到浏览器，让浏览器处理 auth 注入。当前不必要（方案一已满足持久运行），但可做增强。

## 使用方式
```bash
# 启动
cd ~/Desktop/lock && python3 -u adapter_server.py

# 测试
curl http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"hi"}],"stream":false}'

# Claude Code 使用
# 在 settings.json 配 LLM provider 指向 http://127.0.0.1:8765/v1
```

## 依赖
- Chrome 启动参数：`--remote-debugging-port=9222 --user-data-dir=$HOME/.chrome-debug-profile`
- xsimplechat 页面保持打开登录态
- 发消息时 CDP 自动捕获新 HS256 token
