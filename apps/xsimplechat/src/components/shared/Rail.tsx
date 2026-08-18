import { useNavigate } from "react-router-dom";
import {
  Activity,
  BookOpen,
  CircleHelp,
  Compass,
  Folder,
  Gem,
  Languages,
  MessageSquare,
} from "lucide-react";
import type { ComponentType } from "react";
import { Tooltip } from "antd";
import { paths } from "@/router/paths";
import styles from "./rail.module.scss";

const ICON_SIZE = 22;

// 助手入口图标（真实站: 圆角方框内字母 P）
function PIcon() {
  return (
    <svg width="21" height="21" viewBox="0 0 21 21" fill="none" aria-hidden>
      <rect x="1" y="1" width="19" height="19" rx="5" stroke="currentColor" strokeWidth="1.5" />
      <text x="10.5" y="14.5" textAnchor="middle" fontSize="11" fontWeight="600" fill="currentColor">
        P
      </text>
    </svg>
  );
}

const topItems = [
  { key: "chat", icon: MessageSquare, label: "会话", active: true, to: paths.chat() },
  { key: "assistants", icon: PIcon, label: "助手", active: false, to: paths.discover },
  { key: "translation", icon: Languages, label: "翻译", active: false, to: paths.translation },
  { key: "files", icon: Folder, label: "文件", active: false, to: paths.files },
  { key: "discover", icon: Compass, label: "探索", active: false, to: paths.discover },
  { key: "member", icon: Gem, label: "会员", active: false, to: paths.member },
];

const bottomItems = [
  { key: "activity", icon: Activity, label: "活动" },
  { key: "docs", icon: BookOpen, label: "文档" },
  { key: "help", icon: CircleHelp, label: "帮助" },
];

// 左侧窄导航栏（真实站: 64px，顶部 XS logo + 图标列，底部工具图标）
export function Rail() {
  const navigate = useNavigate();

  const renderItem = (
    item: {
      key: string;
      icon: ComponentType<{ size?: number; strokeWidth?: number }>;
      label: string;
      active?: boolean;
      to?: string;
    },
  ) => (
    <Tooltip title={item.label} placement="right" key={item.key}>
      <button
        type="button"
        className={`${styles.item} ${item.active ? styles.itemActive : ""}`}
        aria-label={item.label}
        data-testid={`rail-${item.key}`}
        onClick={() => {
          if (item.to) navigate(item.to);
        }}
      >
        <item.icon size={ICON_SIZE} strokeWidth={1.5} />
      </button>
    </Tooltip>
  );

  return (
    <nav className={styles.rail} aria-label="主导航">
      <div className={styles.logo} aria-label="XSimple logo">
        <img src="/logo/rail-logo.png" alt="" width={32} height={32} />
      </div>
      <div className={styles.top}>{topItems.map(renderItem)}</div>
      <div className={styles.bottom}>{bottomItems.map(renderItem)}</div>
    </nav>
  );
}
