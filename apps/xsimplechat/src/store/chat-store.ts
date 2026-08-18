import { create } from "zustand";
import { api } from "@/shared/api/api-routing";
import type { Announcement, ChatMessage, ModelInfo } from "@/shared/api/types";

interface ChatState {
  models: ModelInfo[];
  selectedModelId: string;
  announcement: Announcement | null;
  announcementDismissed: boolean;
  messages: ChatMessage[];
  sending: boolean;
  init: () => Promise<void>;
  selectModel: (id: string) => void;
  dismissAnnouncement: () => void;
  sendMessage: (content: string) => Promise<void>;
  resetMessages: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  models: [],
  selectedModelId: "gpt-5.6-luna",
  announcement: null,
  announcementDismissed: false,
  messages: [],
  sending: false,

  init: async () => {
    const [models, announcement] = await Promise.all([api.listModels(), api.getAnnouncement()]);
    set({ models, announcement });
  },

  selectModel: (id) => set({ selectedModelId: id }),

  dismissAnnouncement: () => set({ announcementDismissed: true }),

  sendMessage: async (content) => {
    if (get().sending || !content.trim()) return;
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: content.trim(),
      createdAt: new Date().toISOString(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], sending: true }));
    const reply = await api.sendMessage({
      sessionId: "inbox",
      content: userMsg.content,
      model: get().selectedModelId,
    });
    set((s) => ({ messages: [...s.messages, reply], sending: false }));
  },

  resetMessages: () => set({ messages: [] }),
}));
