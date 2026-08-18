import type { ThemeConfig } from "antd";

// antd ConfigProvider 主题：把 antd 组件收敛到真实站色板
// 事实源: cdp-real-states.json（#0072f5/#222/#f8f8f8）+ tokens/_colors.scss
export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: "#0072f5",
    colorInfo: "#0072f5",
    colorText: "#222222",
    colorTextSecondary: "#999999",
    colorTextTertiary: "#666666",
    colorBgLayout: "#f8f8f8",
    colorBgContainer: "#ffffff",
    colorBorder: "#e9e9e9",
    colorBorderSecondary: "#e9e9e9",
    borderRadius: 8,
    borderRadiusLG: 12,
    fontSize: 14,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    controlHeight: 36,
  },
  components: {
    Button: {
      primaryColor: "#ffffff",
      primaryShadow: "none",
      defaultShadow: "none",
      fontWeight: 400,
      borderRadius: 8,
    },
    Modal: {
      borderRadiusLG: 16,
    },
    Tooltip: {
      colorBgSpotlight: "rgba(17, 17, 17, 0.9)",
    },
    Dropdown: {
      borderRadiusLG: 12,
    },
  },
};
