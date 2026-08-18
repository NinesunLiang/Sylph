import { ChevronDown, Command, MessageSquarePlus, Plus, Search } from "lucide-react";
import { Button, Tooltip } from "antd";
import styles from "./assistant-list-panel.module.scss";

// OpenAI 风格漩涡 logo（真实站当前助手卡使用黑色漩涡图标）
function SwirlIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2.5c-2.2 0-3.8 1.1-4.4 2.9-.9-.5-2-.6-3-.2C3 6 2.3 7.8 2.9 9.6c.5 1.4 1.5 2.4 2.7 2.9-.3.6-.3 1.3 0 2 .6 1.8 2.4 3.1 4.4 2.9.3 1.7 1.4 3 3.3 3.1 2.2.2 4.2-1.3 4.7-3.4.4-1.6-.1-3.2-1.3-4.3.9-1 1.3-2.4 1-3.8-.5-2.1-2.4-3.5-4.7-3.4-1.7 0-3 .9-3.6 2.4-.9-.3-1.9-.2-2.8.3.3-.7.6-1.2 1-1.6 1.4-1.5 3.9-1.7 5.6-.4.8.6 1.4 1.5 1.7 2.5.9-.2 1.9.1 2.7.8.8.8 1.1 1.9.8 3-.3 1-1 1.8-1.9 2.3.3.7.4 1.5.2 2.2-.3 1.1-1 2-1.9 2.5.9.2 1.9-.1 2.6-.8.7-.7 1.1-1.6 1.1-2.6 1.4.1 2.6-.7 3-2 .4-1.2.1-2.6-.8-3.5.7-1.4.7-3-.1-4.4C20 4.6 16.4 2.5 12 2.5zm-4.7 16.6c-1.5-.2-2.6-1.5-2.5-3 .9.5 2 .7 3 .6-.1 1-.5 1.9-1.2 2.4.2 0 .5.1.7 0zm9.3-2.1c-.2.8-.8 1.4-1.6 1.7-.4-1-.6-2.1-.5-3.2.8-.2 1.6-.5 2.3-1.1-.1 1-.3 1.9-.7 2.6h.5z"
        fill="currentColor"
      />
    </svg>
  );
}

interface AssistantListPanelProps {
  onNewAssistant?: () => void;
}

// 左侧助手列表栏（真实站: 320px；XSimple 标题 + 搜索 + 当前助手卡 + 默认列表 + 新建助手）
export function AssistantListPanel({ onNewAssistant }: AssistantListPanelProps) {
  return (
    <aside className={styles.panel} aria-label="助手列表">
      <div className={styles.header}>
        <span className={styles.title}>XSimple</span>
        <Tooltip title="新建会话">
          <Button
            type="text"
            className={styles.newChatBtn}
            aria-label="新建会话"
            icon={<MessageSquarePlus size={18} />}
          />
        </Tooltip>
      </div>

      <div className={styles.search}>
        <Search size={14} className={styles.searchIcon} />
        <input className={styles.searchInput} placeholder="搜索助手..." />
        <span className={styles.kbd}>
          <Command size={11} /> K
        </span>
      </div>

      <div className={styles.currentCard} data-testid="current-assistant">
        <span className={styles.currentIcon}>
          <SwirlIcon />
        </span>
        <span className={styles.currentName}>随便聊聊</span>
      </div>

      <button type="button" className={styles.listHeader} data-testid="list-header">
        <span>默认列表</span>
        <ChevronDown size={14} />
      </button>

      <Button
        className={styles.newAssistant}
        icon={<Plus size={14} />}
        data-testid="new-assistant"
        onClick={onNewAssistant}
      >
        新建助手
      </Button>
    </aside>
  );
}
