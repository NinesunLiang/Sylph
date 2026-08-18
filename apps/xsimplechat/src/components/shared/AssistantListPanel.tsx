import { ChevronDown, Command, MessageSquarePlus, Plus, Search } from "lucide-react";
import { Button, Tooltip } from "antd";
import styles from "./assistant-list-panel.module.scss";

interface AssistantListPanelProps {
  onNewAssistant?: () => void;
  width?: number;
}

// 左侧助手列表栏（真实站: 320px；XSimple 标题 + 搜索 + 当前助手卡 + 默认列表 + 新建助手）
export function AssistantListPanel({ onNewAssistant, width = 320 }: AssistantListPanelProps) {
  return (
    <aside className={styles.panel} aria-label="助手列表" style={{ flexBasis: width }}>
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
          <img src="/logo/swirl-logo.png" alt="" width={20} height={20} />
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
