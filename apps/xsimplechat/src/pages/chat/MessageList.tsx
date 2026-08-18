import { useChatStore } from "@/store/chat-store";
import styles from "./message-list.module.scss";

// 会话消息列表（发送后渲染用户/助手气泡；空态不渲染）
export function MessageList() {
  const messages = useChatStore((s) => s.messages);
  const sending = useChatStore((s) => s.sending);

  if (messages.length === 0 && !sending) return null;

  return (
    <div className={styles.list} data-testid="message-list">
      {messages.map((m) => (
        <div
          key={m.id}
          className={`${styles.row} ${m.role === "user" ? styles.rowUser : styles.rowAssistant}`}
          data-item={m.id}
          data-testid={`message-${m.role}`}
        >
          <div className={m.role === "user" ? styles.bubbleUser : styles.bubbleAssistant}>
            {m.content}
          </div>
        </div>
      ))}
      {sending && (
        <div className={`${styles.row} ${styles.rowAssistant}`} data-testid="message-typing">
          <div className={styles.bubbleAssistant}>正在输入…</div>
        </div>
      )}
    </div>
  );
}
