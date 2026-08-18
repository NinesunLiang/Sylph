import { useEffect, useState } from "react";
import { MoreHorizontal, Search, X } from "lucide-react";
import { Dropdown, Tooltip } from "antd";
import { api } from "@/shared/api/api-routing";
import type { Topic } from "@/shared/api/types";
import styles from "./topic-panel.module.scss";

interface TopicPanelProps {
  width?: number;
}

// 右侧话题面板（真实站: 280px；话题标题 + 说明卡 + 默认话题·临时 + Artifacts 空态）
export function TopicPanel({ width = 280 }: TopicPanelProps) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [showGuide, setShowGuide] = useState(true);

  useEffect(() => {
    void api.getTopics("inbox").then(setTopics);
  }, []);

  return (
    <aside className={styles.panel} aria-label="话题" data-testid="topic-panel" style={{ flexBasis: width }}>
      <div className={styles.header}>
        <span className={styles.title}>话题</span>
        <div className={styles.headerActions}>
          <Tooltip title="搜索话题">
            <button type="button" className={styles.iconBtn} aria-label="搜索话题">
              <Search size={15} />
            </button>
          </Tooltip>
          <Dropdown
            menu={{
              items: [
                { key: "rename", label: "重命名话题" },
                { key: "export", label: "导出话题" },
                { key: "clear", label: "清空会话" },
              ],
            }}
            trigger={["click"]}
            placement="bottomRight"
          >
            <Tooltip title="更多">
              <button type="button" className={styles.iconBtn} aria-label="更多话题操作" data-testid="topic-more">
                <MoreHorizontal size={15} />
              </button>
            </Tooltip>
          </Dropdown>
        </div>
      </div>

      {showGuide && (
        <div className={styles.guideCard} data-testid="topic-guide">
          <button
            type="button"
            className={styles.guideClose}
            aria-label="关闭说明"
            onClick={() => setShowGuide(false)}
          >
            <X size={15} strokeWidth={2.2} />
          </button>
          <div className={styles.guideArt} aria-hidden>
            <svg width="160" height="76" viewBox="0 0 160 76" fill="none">
              {/* 主卡片 */}
              <rect x="52" y="2" width="106" height="68" rx="8" fill="#fafafa" stroke="#eeeeee" />
              {/* 顶栏线 + 圆点 */}
              <rect x="118" y="10" width="34" height="6" rx="3" fill="#e5e5e5" />
              <circle cx="164" cy="13" r="4" fill="#5ac8b8" />
              {/* 列表行 */}
              <circle cx="66" cy="24" r="4" fill="#ffd166" />
              <rect x="78" y="21" width="48" height="5" rx="2.5" fill="#e5e5e5" />
              <rect x="78" y="30" width="32" height="5" rx="2.5" fill="#efefef" />
              <circle cx="66" cy="60" r="4" fill="#ffd166" />
              <rect x="78" y="57" width="52" height="5" rx="2.5" fill="#e5e5e5" />
              <rect x="78" y="66" width="36" height="5" rx="2.5" fill="#efefef" />
              {/* 叠加小卡（星标） */}
              <rect x="122" y="22" width="64" height="38" rx="7" fill="#ffffff" stroke="#dddddd" />
              <path d="M131 41l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" fill="#c9c9c9" />
              <rect x="146" y="34" width="34" height="5" rx="2.5" fill="#dddddd" />
              <rect x="146" y="44" width="22" height="5" rx="2.5" fill="#e8e8e8" />
              {/* 虚线连接 */}
              <path d="M156 12l22 8M158 72l22-8" stroke="#dddddd" strokeWidth="1.5" strokeDasharray="3 3" />
            </svg>
          </div>
          <h3 className={styles.guideTitle}>话题列表</h3>
          <p className={styles.guideText}>点击发送左侧按钮可将当前会话保存为历史话题，并开启新一轮会话</p>
        </div>
      )}

      <div className={styles.topicList} data-testid="topic-list">
        {topics.map((t) => (
          <div key={t.id} className={styles.topicItem} data-item={t.id}>
            <span className={styles.topicIcon}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <rect x="4" y="4" width="16" height="16" rx="4" stroke="currentColor" strokeWidth="1.6" strokeDasharray="3 2" />
              </svg>
            </span>
            <span className={styles.topicTitle}>{t.title}</span>
            {t.tag && <span className={styles.topicTag}>{t.tag}</span>}
          </div>
        ))}
      </div>

    </aside>
  );
}
