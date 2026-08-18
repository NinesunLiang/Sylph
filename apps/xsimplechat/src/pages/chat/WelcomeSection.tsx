import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "@/shared/api/api-routing";
import type { Assistant } from "@/shared/api/types";
import styles from "./welcome.module.scss";

// Mistaker 用粉红闭合书图标（真实站实测：粉红书 + 深紫红底边）
function MistakerIcon() {
  return (
    <span className={styles.mistakerIcon} aria-hidden>
      <svg width="30" height="30" viewBox="0 0 32 32" fill="none">
        <defs>
          <linearGradient id="mistaker-book" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#ff8fc0" />
            <stop offset="1" stopColor="#ec4899" />
          </linearGradient>
        </defs>
        <rect x="5" y="3" width="22" height="23" rx="4" fill="url(#mistaker-book)" stroke="#d63384" strokeWidth="1.5" />
        <rect x="5" y="21" width="22" height="4" rx="1.5" fill="#be185d" />
        <rect x="5" y="25.5" width="22" height="3" rx="1.5" fill="#f9a8d4" />
      </svg>
    </span>
  );
}

// 代码优化/错误修改：紫头机器人（真实站实测：黄横条+粉天线杆+深蓝面罩+青蓝眼）
function RobotIcon() {
  return (
    <span className={styles.mistakerIcon} aria-hidden>
      <svg width="30" height="34" viewBox="0 0 30 34" fill="none">
        <defs>
          <linearGradient id="robot-head" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#e6d2f4" />
            <stop offset="1" stopColor="#c2a6e6" />
          </linearGradient>
        </defs>
        <rect x="6.5" y="2" width="10" height="3" rx="1.5" fill="#f59e0b" />
        <rect x="26.5" y="2.5" width="1.5" height="15" rx="0.75" fill="#f472b6" />
        <circle cx="27.2" cy="1.5" r="1.8" fill="#f472b6" />
        <rect x="1" y="2.5" width="1.5" height="15" rx="0.75" fill="#f472b6" />
        <circle cx="1.8" cy="1.5" r="1.8" fill="#f472b6" />
        <rect x="4" y="5" width="23" height="24" rx="6.5" fill="url(#robot-head)" />
        <rect x="4.5" y="9" width="22" height="8" rx="4" fill="#312e81" />
        <rect x="5.2" y="10.4" width="3" height="5.2" rx="1.5" fill="#22d3ee" />
        <rect x="16" y="10.4" width="3" height="5.2" rx="1.5" fill="#22d3ee" />
        <rect x="8" y="22.5" width="7.6" height="2.8" rx="1.4" fill="#4c1d95" />
      </svg>
    </span>
  );
}

function AssistantIcon({ assistant }: { assistant: Assistant }) {
  if (assistant.slug === "mistaker") {
    return <MistakerIcon />;
  }
  if (assistant.slug === "code-review-and-fix") {
    return <RobotIcon />;
  }

  // 健身专家/其余用 Twemoji（真实站 Twemoji 渲染）
  return (
    <span className={styles.cardIcon} aria-hidden>
      <img src={`/emoji/${assistant.emoji}.svg`} alt="" width={30} height={30} />
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
          <img src="/emoji/1f44b.svg" alt="" width={34} height={34} />
        </span>
        <h2 className={styles.greetingTitle}>晚上好</h2>
      </div>
      <p className={styles.desc} data-testid="welcome-desc-1">我是您的私人智能助理 XSimple，请问现在能帮您做什么？</p>
      <p className={styles.desc}>
        如果需要获得更加专业或定制的助手，可以点击 <span className={styles.plus}>＋</span>{" "}
        创建自定义助手
      </p>

      <div className={styles.recommendRow} data-testid="recommend-row">
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
