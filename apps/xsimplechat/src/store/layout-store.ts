import { create } from "zustand";
import { persist } from "zustand/middleware";

interface LayoutState {
  leftPanelWidth: number; // 左列表栏宽度
  rightPanelWidth: number; // 右话题面板宽度
  showLeftPanel: boolean;
  showRightPanel: boolean;
  setLeftPanelWidth: (w: number) => void;
  setRightPanelWidth: (w: number) => void;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
}

export const LEFT_MIN = 240;
export const LEFT_MAX = 420;
export const RIGHT_MIN = 240;
export const RIGHT_MAX = 420;

// 侧栏宽度/开闭（持久化到 localStorage，刷新保留）
export const useLayoutStore = create<LayoutState>()(
  persist(
    (set) => ({
      leftPanelWidth: 320,
      rightPanelWidth: 280,
      showLeftPanel: true,
      showRightPanel: true,
      setLeftPanelWidth: (w) =>
        set({ leftPanelWidth: Math.min(LEFT_MAX, Math.max(LEFT_MIN, w)) }),
      setRightPanelWidth: (w) =>
        set({ rightPanelWidth: Math.min(RIGHT_MAX, Math.max(RIGHT_MIN, w)) }),
      toggleLeftPanel: () => set((s) => ({ showLeftPanel: !s.showLeftPanel })),
      toggleRightPanel: () => set((s) => ({ showRightPanel: !s.showRightPanel })),
    }),
    { name: "xsimplechat-layout" },
  ),
);
