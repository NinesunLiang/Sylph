import { useEffect, useState } from "react";
import { Rail } from "@/components/shared/Rail";
import { AssistantListPanel } from "@/components/shared/AssistantListPanel";
import { useChatStore } from "@/store/chat-store";
import { TopBar } from "./TopBar";
import { WelcomeSection } from "./WelcomeSection";
import { TopicPanel } from "./TopicPanel";
import { Composer } from "./Composer";
import { MessageList } from "./MessageList";
import { AnnouncementModal } from "./AnnouncementModal";
import { LoginModal } from "./LoginModal";
import styles from "./chat.module.scss";

// /chat?session=inbox 会话页（1:1 还原 + 交互 + 二级弹窗）
export function ChatPage() {
  const init = useChatStore((s) => s.init);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const sending = useChatStore((s) => s.sending);

  const [loginOpen, setLoginOpen] = useState(false);
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);

  useEffect(() => {
    void init();
  }, [init]);

  return (
    <div className={styles.page}>
      <Rail />
      {showLeftPanel && <AssistantListPanel onNewAssistant={() => setLoginOpen(true)} />}
      <div className={styles.workspace}>
        <TopBar
          onToggleLeft={() => setShowLeftPanel((v) => !v)}
          onToggleRight={() => setShowRightPanel((v) => !v)}
        />
        <div className={styles.workspaceBody}>
          <main className={styles.main}>
            <div className={styles.content}>
              <WelcomeSection />
              <div style={{ flex: 1 }} />
              <MessageList />
              <Composer disabled={sending} onSend={(c) => void sendMessage(c)} />
            </div>
          </main>
          {showRightPanel && <TopicPanel />}
        </div>
      </div>
      <AnnouncementModal />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}
