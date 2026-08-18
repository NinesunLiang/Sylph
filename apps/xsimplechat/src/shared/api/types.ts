// ── API 契约类型（api_contract_status: inferred，见 .omc/night/2026-08-18/assumptions.yaml）──

export interface Assistant {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  icon: string; // emoji 或图标 key（1:1 还原真实站 emoji 图标）
}

export interface Topic {
  id: string;
  title: string;
  tag?: string; // 如 "临时"
  temp?: boolean;
}

export interface ModelInfo {
  id: string;
  name: string;
  badge?: string;
}

export interface Announcement {
  id: string;
  title: string;
  content: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

export interface SendMessagePayload {
  sessionId: string;
  content: string;
  model: string;
}
