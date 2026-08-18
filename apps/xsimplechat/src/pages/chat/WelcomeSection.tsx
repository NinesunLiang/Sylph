import { useEffect, useState } from "react";
import { BookOpen, RefreshCw } from "lucide-react";
import { api } from "@/shared/api/api-routing";
import type { Assistant } from "@/shared/api/types";
import styles from "./welcome.module.scss";

// Mistaker 用红紫渐变书本图标（真实站为渐变图形；其余助手用 emoji，1:1 还原）
function AssistantIcon({ assistant }: { assistant: Assistant }) {
  if (assistant.slug === "mistaker") {
    return (
      <span className={styles.mistakerIcon} aria-hidden>
        <BookOpen size={26} strokeWidth={1.6} />
      </span>
    );
  }
  return (
    <span className={styles.cardIcon} aria-hidden>
      {assistant.icon}
    </span>
  );
}

// 中央欢迎区（真实站: 👋 晚上好 + 两行说明 + 新增助手推荐 + 4 助手卡 2x2）
export function WelcomeSection() {
  const [assistants, setAssistants] = useState<Assistant[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const list = await api.listAssistants();
    setAssistants(list);
    setLoading(false);
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <section className={styles.welcome} aria-busy={loading} data-testid="welcome-section">
      <div className={styles.greeting}>
        <span className={styles.wave} aria-hidden>
          <svg className={styles.waveLines} width="34" height="40" viewBox="0 0 34 40" fill="none">
            <path d="M4 6c6 2 10 5 11 10" stroke="#9cc8ff" strokeWidth="2" strokeLinecap="round" />
            <path d="M1 13c6 2 9 5 10 9" stroke="#9cc8ff" strokeWidth="2" strokeLinecap="round" />
            <path d="M5 19c5 1 8 4 9 7" stroke="#9cc8ff" strokeWidth="2" strokeLinecap="round" />
            <path d="M1 28c5 1 8 3 9 6" stroke="#9cc8ff" strokeWidth="2" strokeLinecap="round" />
            <path d="M4 34c4 1 7 2 8 4" stroke="#9cc8ff" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span className={styles.waveEmoji}>👋</span>
        </span>
        <h2 className={styles.greetingTitle}>晚上好</h2>
      </div>
      <p className={styles.desc}>我是您的私人智能助理 XSimple，请问现在能帮您做什么？</p>
      <p className={styles.desc}>
        如果需要获得更加专业或定制的助手，可以点击 <span className={styles.plus}>＋</span>{" "}
        创建自定义助手
      </p>

      <div className={styles.recommendRow}>
        <span className={styles.recommendLabel}>新增助手推荐：</span>
        <button
          type="button"
          className={styles.refresh}
          aria-label="刷新推荐"
          data-testid="refresh-recommend"
          onClick={() => void load()}
        >
          <RefreshCw size={14} />
        </button>
      </div>

      <div className={styles.grid} data-testid="assistant-grid">
        {assistants.map((a) => (
          <article
            key={a.id}
            className={styles.card}
            data-item={a.id}
            data-testid={`assistant-card-${a.slug}`}
          >
            <AssistantIcon assistant={a} />
            <div className={styles.cardBody}>
              <h3 className={styles.cardTitle}>{a.name}</h3>
              <p className={styles.cardDesc}>{a.description}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
