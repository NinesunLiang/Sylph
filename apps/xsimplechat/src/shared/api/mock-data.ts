// ── Mock 数据（真实站捕获 contents.json chat-inbox 块逐字对齐）──
// 事实源: .omc/ui-autopilot/xsimplechat/detail-pages/contents.json
import type { Announcement, Assistant, ModelInfo, Topic } from "./types";

export const mockAssistants: Assistant[] = [
  {
    id: "a1",
    slug: "fitness-expert",
    name: "健身专家",
    description: "知识渊博的健身专家",
    category: "生活",
    icon: "custom",
    emoji: "1f3c0",
  },
  {
    id: "a2",
    slug: "mistaker",
    name: "Mistaker",
    description: "通过清晰的解释和语法、发音示例来消除错误。",
    category: "教育",
    icon: "mistaker",
    emoji: "1f3c0",
  },
  {
    id: "a3",
    slug: "code-review-and-fix",
    name: "代码优化/错误修改",
    description: "精通多种编程语言，优化代码结构，修复错误并提供优雅的解决方案。",
    category: "编程",
    icon: "custom",
    emoji: "1f916",
  },
  {
    id: "a4",
    slug: "cyber-specialist",
    name: "伦理安全分析师",
    description: "专注于识别和减轻网络和移动平台中的安全漏洞。",
    category: "安全",
    icon: "custom",
    emoji: "1f575",
  },
];

export const mockTopics: Topic[] = [
  { id: "t1", title: "默认话题", tag: "临时", temp: true },
];

export const mockModels: ModelInfo[] = [
  { id: "gpt-5.6-luna", name: "GPT-5.6 Luna" },
  { id: "gpt-5.6", name: "GPT-5.6" },
  { id: "claude-opus-4.8", name: "Opus 4.8" },
  { id: "deepseek-v4", name: "DeepSeek V4" },
];

export const mockAnnouncement: Announcement = {
  id: "ann-1",
  title: "系统公告",
  content:
    "欢迎使用 XSimpleChat！\n\n您可以与内置助手随便聊聊，或在「发现」页浏览更多专业助手。发送左侧按钮可将当前会话保存为历史话题，并开启新一轮会话。",
};

export const mockReply = (content: string): string =>
  `已收到你的消息：「${content}」\n（这是 mock 回复——接入真实后端后由模型生成。）`;
