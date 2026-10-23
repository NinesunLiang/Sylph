// 摄影助手 v2 —— 可选中转服务（零依赖，只用 Node 内置能力）
//
// v2 的定位（2026-09 用户拍板）：自用 App 的主路径是**客户端直连** ——
//   Key 在教练页「模型配置」里输入，只存手机本机，不打进 APK、不进 git。
// 本中转因此是**可选**的：当你不想让自己的 Key 以直连形式跑在手机上的请求里，
// 或将来要把 App 分发给别人用时，开它，Key 只放在服务端。
//
// 它干四件事：
//   1. 持有 API Key（绝不发给客户端）
//   2. 注入提示词 skill（调提示词不用重新发版 App）
//   3. 校验模型输出是否符合契约（不符合就打日志，方便调提示词）
//   4. 限流 + 简单缓存（省钱）
//
// 运行（.env 文件只留在本机，绝不提交，见 .env.example）：
//   cd server && cp .env.example .env   # 填入自己的 DEEPSEEK_API_KEY
//   set -a; source .env; set +a; node server.mjs
//
// 客户端（Flutter）这样配：
//   教练页「模型配置」→ 接口地址填 http://<你的机器IP>:8787/analyze，Key 留空
//   （客户端检测到 http:// 会自动切到中转模式，Key 不需要填）

import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));

// ---------- 配置 ----------
const PORT = Number(process.env.PORT ?? 8787);
const API_KEY = process.env.DEEPSEEK_API_KEY ?? '';
const UPSTREAM =
  process.env.UPSTREAM ?? 'https://api.deepseek.com/chat/completions';
// 模型名放环境变量：以后模型改名不用改代码
// v2 默认 deepseek-v4-flash（和当前 dsh 同款；教练页直连时默认也是它）
const MODEL = process.env.MODEL ?? 'deepseek-v4-flash';

// 限流：每个 IP 每分钟最多 N 次（省钱闸门）
const RATE_LIMIT_PER_MIN = Number(process.env.RATE_LIMIT_PER_MIN ?? 20);
// 请求体上限：DeepSeek 侧 48MiB，这里收紧到 12MiB（客户端本来就压到 ~200KB）
const MAX_BODY_BYTES = Number(process.env.MAX_BODY_BYTES ?? 12 * 1024 * 1024);
// 相同图片 10 分钟内复用结果（同一张图反复点不该重复烧 token）
const CACHE_TTL_MS = Number(process.env.CACHE_TTL_MS ?? 10 * 60 * 1000);

function loadPrompt() {
  const p = process.env.PROMPT_FILE ?? join(HERE, 'prompts', 'composition.md');
  if (existsSync(p)) return readFileSync(p, 'utf8');
  return '你是摄影指导。只输出 JSON，字段：schema_version, composition{rule,confidence,horizon_tilt_deg}, subject{label,current_box,target_box}, camera_move{pan_deg,tilt_deg,dolly_m,zoom,hint}, exposure{ev,reason}, tips[]。坐标用 0-1 归一化。';
}

// ---------- 契约校验（与服务端无关，纯结构检查）----------
// 与 App 的 lib/features/coach/suggestion.dart 保持一致。
// 注意：这里只做「警告级」校验 —— 不合格也照样回给客户端，
// 因为客户端有兜底；但日志里必须能看见，否则调提示词全靠猜。
function validateSuggestion(obj) {
  const problems = [];
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    return ['顶层不是对象'];
  }
  const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
  const isBox = (v) =>
    Array.isArray(v) && v.length === 4 && v.every(isNum);

  if (obj.schema_version !== '1.0') problems.push('schema_version 缺失或不是 1.0');
  if (!obj.composition || typeof obj.composition !== 'object') {
    problems.push('缺 composition');
  }
  if (!obj.subject || typeof obj.subject !== 'object') {
    problems.push('缺 subject');
  } else {
    if (obj.subject.current_box && !isBox(obj.subject.current_box)) {
      problems.push('subject.current_box 不是 4 个数字');
    }
    if (obj.subject.target_box && !isBox(obj.subject.target_box)) {
      problems.push('subject.target_box 不是 4 个数字');
    }
  }
  if (!obj.camera_move || typeof obj.camera_move !== 'object') {
    problems.push('缺 camera_move');
  }
  if (!obj.exposure || typeof obj.exposure !== 'object') {
    problems.push('缺 exposure');
  }
  if (obj.tips !== undefined && !Array.isArray(obj.tips)) {
    problems.push('tips 不是数组');
  }
  return problems;
}

// 从模型文本里抠 JSON（与客户端同名逻辑，服务端也留一份用于校验）
function extractJson(text) {
  const t = String(text ?? '').trim();
  if (!t) return null;
  const tryParse = (s) => {
    try {
      return JSON.parse(s);
    } catch {
      return null;
    }
  };
  const direct = tryParse(t);
  if (direct !== null) return direct;

  for (const m of t.matchAll(/```(?:json)?\s*([\s\S]*?)```/gi)) {
    const inner = m[1]?.trim();
    if (!inner) continue;
    const d = tryParse(inner);
    if (d !== null) return d;
  }

  const start = t.indexOf('{');
  if (start < 0) return null;
  let depth = 0;
  let inStr = false;
  let esc = false;
  for (let i = start; i < t.length; i++) {
    const c = t[i];
    if (inStr) {
      if (esc) esc = false;
      else if (c === '\\') esc = true;
      else if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') inStr = true;
    else if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) return tryParse(t.slice(start, i + 1));
    }
  }
  return null;
}

// ---------- 限流 + 缓存（内存版，重启即清）----------
const hits = new Map(); // ip -> {count, windowStart}
const cache = new Map(); // hash -> {body, at}

function rateLimited(ip) {
  const now = Date.now();
  const rec = hits.get(ip);
  if (!rec || now - rec.windowStart > 60_000) {
    hits.set(ip, { count: 1, windowStart: now });
    return false;
  }
  rec.count++;
  return rec.count > RATE_LIMIT_PER_MIN;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error(`请求体超过 ${MAX_BODY_BYTES} 字节`));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

function json(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
  });
  res.end(body);
}

// ---------- 主逻辑 ----------
async function handleAnalyze(req, res, ip) {
  if (!API_KEY) {
    return json(res, 500, {
      error: 'server_not_configured',
      message: '服务端没配 DEEPSEEK_API_KEY',
    });
  }
  if (rateLimited(ip)) {
    return json(res, 429, {
      error: 'rate_limited',
      message: `每分钟最多 ${RATE_LIMIT_PER_MIN} 次`,
    });
  }

  let raw;
  try {
    raw = await readBody(req);
  } catch (e) {
    return json(res, 413, { error: 'body_too_large', message: String(e.message) });
  }

  let incoming;
  try {
    incoming = JSON.parse(raw);
  } catch {
    return json(res, 400, { error: 'bad_json', message: '请求体不是合法 JSON' });
  }

  const cacheKey = createHash('sha256').update(raw).digest('hex');
  const cached = cache.get(cacheKey);
  if (cached && Date.now() - cached.at < CACHE_TTL_MS) {
    res.setHeader('x-photocoach-cache', 'hit');
    return json(res, 200, cached.body);
  }

  // 客户端传来的 messages 里可能带自己的 system，这里强制换成服务端提示词
  const messages = Array.isArray(incoming.messages) ? incoming.messages : [];
  const userMessages = messages.filter((m) => m?.role !== 'system');

  const upstreamBody = {
    model: incoming.model && process.env.ALLOW_CLIENT_MODEL === '1'
      ? incoming.model
      : MODEL,
    messages: [{ role: 'system', content: loadPrompt() }, ...userMessages],
    response_format: { type: 'json_object' },
    stream: false,
  };

  let upstreamRes;
  try {
    upstreamRes = await fetch(UPSTREAM, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${API_KEY}`,
      },
      body: JSON.stringify(upstreamBody),
    });
  } catch (e) {
    return json(res, 502, { error: 'upstream_unreachable', message: String(e) });
  }

  const text = await upstreamRes.text();
  if (!upstreamRes.ok) {
    return json(res, 502, {
      error: 'upstream_error',
      status: upstreamRes.status,
      message: text.slice(0, 500),
    });
  }

  // 校验模型输出，把问题打日志（方便调提示词），但不拦回客户端
  let parsed = null;
  try {
    const envelope = JSON.parse(text);
    const content = envelope?.choices?.[0]?.message?.content ?? '';
    parsed = extractJson(content);
    const problems = validateSuggestion(parsed);
    if (problems.length) {
      console.warn('[contract] 模型输出不合契约:', problems.join('; '));
    } else {
      console.log('[contract] ok');
    }
  } catch (e) {
    console.warn('[contract] 解析响应失败:', String(e));
  }

  const out = JSON.parse(text);
  cache.set(cacheKey, { body: out, at: Date.now() });
  if (cache.size > 500) {
    // 简单清理，别让内存无限涨
    const oldest = [...cache.entries()].sort((a, b) => a[1].at - b[1].at)[0];
    if (oldest) cache.delete(oldest[0]);
  }
  json(res, 200, out);
}

export const app = createServer(async (req, res) => {
  const ip = req.socket.remoteAddress ?? 'unknown';
  const url = new URL(req.url ?? '/', 'http://localhost');

  if (req.method === 'GET' && url.pathname === '/health') {
    return json(res, 200, {
      ok: true,
      model: MODEL,
      hasKey: Boolean(API_KEY),
      upstream: UPSTREAM,
      promptChars: loadPrompt().length,
    });
  }

  if (req.method === 'POST' && url.pathname === '/analyze') {
    try {
      return await handleAnalyze(req, res, ip);
    } catch (e) {
      console.error('[fatal]', e);
      return json(res, 500, { error: 'internal', message: String(e) });
    }
  }

  json(res, 404, { error: 'not_found', message: '只有 GET /health 和 POST /analyze' });
});

// 只有直接 `node server.mjs` 才监听端口。
// 被 import 时（比如测试）不监听 —— 否则测试进程不会退出。
const isMain =
  process.argv[1] && import.meta.url === `file://${process.argv[1]}`;

if (isMain) {
  app.listen(PORT, () => {
    console.log(`摄影助手中转已启动: http://localhost:${PORT}`);
    console.log(`  GET  /health   健康检查`);
    console.log(`  POST /analyze  分析图片`);
    console.log(`  模型: ${MODEL}`);
    console.log(`  Key:  ${API_KEY ? '已配置' : '⚠️ 未配置（DEEPSEEK_API_KEY）'}`);
  });
}

export { validateSuggestion, extractJson };
