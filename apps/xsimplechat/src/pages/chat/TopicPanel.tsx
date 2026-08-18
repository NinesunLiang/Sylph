import { useEffect, useState } from "react";
import { MoreHorizontal, Search, X } from "lucide-react";
import { Tooltip } from "antd";
import { api } from "@/shared/api/api-routing";
import type { Topic } from "@/shared/api/types";
import styles from "./topic-panel.module.scss";

// 右侧话题面板（真实站: 280px；话题标题 + 说明卡 + 默认话题·临时 + Artifacts 空态）
export function TopicPanel() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [showGuide, setShowGuide] = useState(true);

  useEffect(() => {
    void api.getTopics("inbox").then(setTopics);
  }, []);

  return (
    <aside className={styles.panel} aria-label="话题" data-testid="topic-panel">
      <div className={styles.header}>
        <span className={styles.title}>话题</span>
        <div className={styles.headerActions}>
          <Tooltip title="搜索话题">
            <button type="button" className={styles.iconBtn} aria-label="搜索话题">
              <Search size={15} />
            </button>
          </Tooltip>
          <Tooltip title="更多">
            <button type="button" className={styles.iconBtn} aria-label="更多话题操作">
              <MoreHorizontal size={15} />
            </button>
          </Tooltip>
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
            <X size={13} />
          </button>
          <div className={styles.guideArt} aria-hidden>
            <svg width="160" height="106" viewBox="0 0 160 106" fill="none">
              {/* 主卡片 */}
              <rect x="6" y="4" width="106" height="98" rx="8" fill="#fafafa" stroke="#eeeeee" />
              {/* 顶栏线 + 圆点 */}
              <rect x="72" y="12" width="34" height="6" rx="3" fill="#e5e5e5" />
              <circle cx="118" cy="15" r="4" fill="#5ac8b8" />
              {/* 列表行 */}
              <circle cx="20" cy="38" r="4" fill="#ffd166" />
              <rect x="32" y="35" width="48" height="5" rx="2.5" fill="#e5e5e5" />
              <rect x="32" y="44" width="32" height="5" rx="2.5" fill="#efefef" />
              <circle cx="20" cy="84" r="4" fill="#ffd166" />
              <rect x="32" y="81" width="52" height="5" rx="2.5" fill="#e5e5e5" />
              <rect x="32" y="90" width="36" height="5" rx="2.5" fill="#efefef" />
              {/* 叠加小卡（星标） */}
              <rect x="90" y="40" width="64" height="38" rx="7" fill="#ffffff" stroke="#dddddd" />
              <path d="M99 59l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" fill="#c9c9c9" />
              <rect x="114" y="52" width="34" height="5" rx="2.5" fill="#dddddd" />
              <rect x="114" y="62" width="22" height="5" rx="2.5" fill="#e8e8e8" />
              {/* 虚线连接 */}
              <path d="M114 20l22 12M114 96l22-12" stroke="#dddddd" strokeWidth="1.5" strokeDasharray="3 3" />
            </svg>
          </div>
          <div className={styles.guideTitleRow}>
            <h3 className={styles.guideTitle}>话题列表</h3>
            <span className={styles.guideEmptyTag}>当前知识列表为空</span>
          </div>
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

      <div className={styles.artifactsEmpty} data-empty>
        当前 Artifacts 列表为空，请在会话中按需使用插件后再查看
      </div>
    </aside>
  );
}
