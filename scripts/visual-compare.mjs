// Visual comparison using Kimi K3 (via Moonshot Anthropic-compatible API)
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW';
const K3_CONFIG = JSON.parse(readFileSync(resolve(ROOT, '.claude/settings_k3.json'), 'utf8'));
const API_KEY = K3_CONFIG.env.ANTHROPIC_AUTH_TOKEN;
const BASE_URL = K3_CONFIG.env.ANTHROPIC_BASE_URL;

const PROTO_IMG = resolve(ROOT, '.omc/ui-autopilot/home_page/measurements/proto-full-loaded.png');
const IMPL_IMG = resolve(ROOT, '.omc/ui-autopilot/home_page/measurements/impl-full.png');

// Encode images to base64
function b64(path) {
  return readFileSync(path).toString('base64');
}

const PROTO = b64(PROTO_IMG);
const IMPL = b64(IMPL_IMG);

const requestBody = {
  model: 'kimi-k3',
  max_tokens: 4096,
  messages: [{
    role: 'user',
    content: [
      {
        type: 'text',
        text: `你是一个专业的UI视觉对比专家。比较以下两张截图：

第一张是原型（xsimplechat.com，一个AI聊天应用），第二张是本地实现。

请详细列出：
1. 当前实现的布局结构（侧边栏、主内容区、聊天输入区）
2. 与原型相比的视觉差异（具体到色值差异、布局差异、元素差异）
3. 修复优先级排序（从最高到最低）
4. 具体的CSS/Tailwind调整建议

输出格式：
## 总体评估
## 差异清单（按优先级）
## 具体修复建议`,
      },
      {
        type: 'image',
        source: {
          type: 'base64',
          media_type: 'image/png',
          data: PROTO,
        },
      },
      {
        type: 'image',
        source: {
          type: 'base64',
          media_type: 'image/png',
          data: IMPL,
        },
      },
    ],
  }],
};

const response = await fetch(`${BASE_URL}/v1/messages`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': API_KEY,
    'anthropic-version': '2023-06-01',
  },
  body: JSON.stringify(requestBody),
});

if (!response.ok) {
  const err = await response.text();
  console.error(`Kimi K3 API error (${response.status}): ${err}`);
  process.exit(1);
}

const result = await response.json();
const text = result.content?.[0]?.text || '(no text response)';
console.log(text);
