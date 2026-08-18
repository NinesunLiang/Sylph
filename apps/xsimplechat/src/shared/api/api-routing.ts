// ── api 路由层（全 mock；接入真实后端时仅替换本文件）──
// api_contract_status: inferred — 契约逐条登记 .omc/night/2026-08-18/assumptions.yaml
import { mockAnnouncement, mockAssistants, mockModels, mockReply, mockTopics } from "./mock-data";
import type { Announcement, Assistant, ChatMessage, ModelInfo, SendMessagePayload, Topic } from "./types";

const LATENCY = 120;

const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

export const api = {
  async listAssistants(): Promise<Assistant[]> {
    await delay(LATENCY);
    return mockAssistants;
  },

  async getTopics(sessionId: string): Promise<Topic[]> {
    await delay(LATENCY);
    void sessionId;
    return mockTopics;
  },

  async listModels(): Promise<ModelInfo[]> {
    await delay(LATENCY);
    return mockModels;
  },

  async getAnnouncement(): Promise<Announcement | null> {
    await delay(200);
    return mockAnnouncement;
  },

  async sendMessage(payload: SendMessagePayload): Promise<ChatMessage> {
    await delay(600); // 模拟生成耗时（触发 double_submit 防抖语义）
    return {
      id: `m-${Date.now()}`,
      role: "assistant",
      content: mockReply(payload.content),
      createdAt: new Date().toISOString(),
    };
  },
};
