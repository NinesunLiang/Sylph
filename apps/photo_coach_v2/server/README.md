# 中转服务（v2 里是可选组件）

**v2 的定位**：自用 App 的主路径是**客户端直连** —— Key 在教练页「模型配置」
里输入，只存手机本机（SharedPreferences），不打进 APK、不进 git。
本中转是**可选**的：不想让自己的 Key 直连跑在请求里，或将来把 App 分发给别人
用时才开它。Key 只存在服务端时，它仍然有价值（提示词热更 + 限流 + 缓存）。

零依赖（只用 Node 内置能力），Node ≥ 18 就能跑。

## 跑起来

```bash
cd apps/photo_coach_v2/server
node --test                                  # 先跑契约测试
cp .env.example .env                         # 填 DEEPSEEK_API_KEY（.env 已被 gitignore）
set -a; source .env; set +a; node server.mjs # 启动
```

看健康状态：

```bash
curl -s http://localhost:8787/health
# {"ok":true,"model":"deepseek-v4-flash","hasKey":true,...}
```

## 客户端怎么接

教练页 →「模型配置」→ **接口地址**填 `http://<你的机器IP>:8787/analyze`，
**API Key 留空**。客户端检测到 `http://`（局域网/中转）会自动切到
`ProxyMode.server`，**手机端不需要 Key**。

> 不填任何内容 = 直连官方接口（默认）；Key 填在「API Key」框里，只存本机。

> 真机连本机服务：手机和电脑要在同一个 Wi-Fi，用电脑的局域网 IP
> （`ipconfig getifaddr en0`）。Android 模拟器用 `10.0.2.2`。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `PORT` | `8787` | 监听端口 |
| `DEEPSEEK_API_KEY` | 无（必填） | Key 只存在服务端 |
| `UPSTREAM` | `https://api.deepseek.com/chat/completions` | 上游地址 |
| `MODEL` | `deepseek-v4-flash` | 模型名。**改这里，不用改 App** |
| `PROMPT_FILE` | `./prompts/composition.md` | 提示词文件。**改这里，不用改 App** |
| `RATE_LIMIT_PER_MIN` | `20` | 每 IP 每分钟次数（省钱闸门） |
| `MAX_BODY_BYTES` | `12 MiB` | 请求体上限 |
| `CACHE_TTL_MS` | `600000` | 相同图片结果复用时长（10 分钟） |
| `ALLOW_CLIENT_MODEL` | `0` | 设 1 才允许客户端指定模型（一般别开） |

## 两个接口

### `GET /health`

返回模型名、是否配了 Key、上游地址、提示词长度。

### `POST /analyze`

请求体（和 OpenAI Chat Completions 一样）：

```json
{
  "model": "deepseek-flash",
  "messages": [
    { "role": "user", "content": [
      { "type": "text", "text": "这是用户提供的参考图" },
      { "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,..." } }
    ]}
  ]
}
```

响应：原样透传上游的 OpenAI 兼容格式，客户端从
`choices[0].message.content` 里取文本、再抠 JSON。

**注意**：客户端传上来的 `system` 消息会被**丢弃并替换**成
`prompts/composition.md`。这样调提示词不用重新发版 App。

## 它替客户端挡了什么

| 保护 | 行为 |
|---|---|
| Key 泄露 | Key 只在服务端；发 `Bearer` 只在上游方向 |
| 被刷 | 每 IP 每分钟 20 次，超了返 429 |
| 重复烧 token | 相同请求体 10 分钟内直接返回缓存（响应头 `x-photocoach-cache: hit`） |
| 大包攻击 | 请求体超过 12 MiB 返 413 |
| 契约漂移 | 用 `validateSuggestion` 校验模型输出，不合格打 `[contract]` 警告日志 |

## 还没做（别以为有了）

- ⬜ 鉴权：现在**任何能访问到的人都可用**。上线前必须加客户端鉴权
  （简单版：一个共享 token；正经版：登录体系）
- ⬜ 持久化：限流和缓存都在内存，重启即清
- ⬜ HTTPS：现在是裸 HTTP，只适合内网/开发
- ⬜ 可观测：只有 console 日志，没有指标和告警
- ⬜ 提示词 A/B：没有版本管理和灰度

## 契约两边要保持一致

| 位置 | 文件 |
|---|---|
| 客户端解析 | `lib/features/coach/suggestion.dart` |
| 服务端校验 | `server/server.mjs` 的 `validateSuggestion` |
| 提示词 | `server/prompts/composition.md` |
| 内置提示词兜底 | `lib/features/coach/prompt.dart` |

改任意一处，四处都要对一遍。客户端的
`test/llm_and_compressor_test.dart` 里有「提示词字段名必须能被解析器认」的
测试，就是防这个漂移的。
