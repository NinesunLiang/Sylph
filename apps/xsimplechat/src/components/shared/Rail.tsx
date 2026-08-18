import { useNavigate } from "react-router-dom";
import {
  Activity,
  BookOpen,
  CircleHelp,
  Compass,
  Folder,
  Gem,
  Languages,
  MessageCircle,
  SquarePen,
} from "lucide-react";
import { Tooltip } from "antd";
import { paths } from "@/router/paths";
import styles from "./rail.module.scss";

const ICON_SIZE = 20;

const topItems = [
  { key: "chat", icon: MessageCircle, label: "会话", active: true, to: paths.chat() },
  { key: "assistants", icon: SquarePen, label: "助手", active: false, to: paths.discover },
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
    item: { key: string; icon: typeof MessageCircle; label: string; active?: boolean; to?: string },
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
        <item.icon size={ICON_SIZE} strokeWidth={1.8} />
      </button>
    </Tooltip>
  );

  return (
    <nav className={styles.rail} aria-label="主导航">
      <div className={styles.logo} aria-label="XSimple logo">
        <span className={styles.logoX}>X</span>
      </div>
      <div className={styles.top}>{topItems.map(renderItem)}</div>
      <div className={styles.bottom}>{bottomItems.map(renderItem)}</div>
    </nav>
  );
}
