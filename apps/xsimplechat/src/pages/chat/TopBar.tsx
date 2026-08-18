import { Bot, Download, Headset, Menu, PanelLeftClose, PanelRight, Share2 } from "lucide-react";
import { Tooltip } from "antd";
import styles from "./topbar.module.scss";

interface TopBarProps {
  onToggleLeft?: () => void;
  onToggleRight?: () => void;
}

// 顶部工具栏（真实站: 高 48，跨中间+右面板；左=会话名+模型标签，右=联系客服/安装到桌面/分享/面板/菜单）
export function TopBar({ onToggleLeft, onToggleRight }: TopBarProps) {
  return (
    <header className={styles.bar}>
      <div className={styles.left}>
        <Tooltip title="收起侧栏">
          <button
            type="button"
            className={styles.iconBtn}
            aria-label="收起侧栏"
            data-testid="collapse-sidebar"
            onClick={onToggleLeft}
          >
            <PanelLeftClose size={18} />
          </button>
        </Tooltip>
        <span className={styles.logo}>
          <Bot size={19} strokeWidth={2} />
        </span>
        <span className={styles.title}>随便聊聊</span>
        <span className={styles.modelBadge} data-testid="model-badge">
          <span className={styles.modelDot} />
          GPT-5.6 Luna
        </span>
      </div>

      <div className={styles.right}>
        <button type="button" className={styles.supportBtn} data-testid="contact-support">
          <Headset size={16} />
          联系客服
        </button>
        <button type="button" className={styles.textBtn}>
          <Download size={16} />
          安装到桌面
        </button>
        <Tooltip title="分享">
          <button type="button" className={styles.iconBtn} aria-label="分享">
            <Share2 size={17} />
          </button>
        </Tooltip>
        <Tooltip title="切换面板">
          <button
            type="button"
            className={styles.iconBtn}
            aria-label="切换面板"
            data-testid="toggle-right-panel"
            onClick={onToggleRight}
          >
            <PanelRight size={17} />
          </button>
        </Tooltip>
        <Tooltip title="更多">
          <button type="button" className={styles.iconBtn} aria-label="更多">
            <Menu size={17} />
          </button>
        </Tooltip>
      </div>
    </header>
  );
}
