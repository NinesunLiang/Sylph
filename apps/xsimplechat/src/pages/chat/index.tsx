import { useEffect, useState } from "react";
import { Rail } from "@/components/shared/Rail";
import { AssistantListPanel } from "@/components/shared/AssistantListPanel";
import { ResizeHandle } from "@/components/shared/ResizeHandle";
import { useChatStore } from "@/store/chat-store";
import { useLayoutStore } from "@/store/layout-store";
import { TopBar } from "./TopBar";
import { WelcomeSection } from "./WelcomeSection";
import { TopicPanel } from "./TopicPanel";
import { Composer } from "./Composer";
import { MessageList } from "./MessageList";
import { AnnouncementModal } from "./AnnouncementModal";
import { LoginModal } from "./LoginModal";
import { ContactModal } from "./ContactModal";
import styles from "./chat.module.scss";

// /chat?session=inbox 会话页（1:1 还原 + 交互 + 二级弹窗 + 侧栏拖拽/开闭）
export function ChatPage() {
  const init = useChatStore((s) => s.init);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const sending = useChatStore((s) => s.sending);

  const leftWidth = useLayoutStore((s) => s.leftPanelWidth);
  const rightWidth = useLayoutStore((s) => s.rightPanelWidth);
  const showLeft = useLayoutStore((s) => s.showLeftPanel);
  const showRight = useLayoutStore((s) => s.showRightPanel);
  const setLeftWidth = useLayoutStore((s) => s.setLeftPanelWidth);
  const setRightWidth = useLayoutStore((s) => s.setRightPanelWidth);
  const toggleLeft = useLayoutStore((s) => s.toggleLeftPanel);
  const toggleRight = useLayoutStore((s) => s.toggleRightPanel);

  const [loginOpen, setLoginOpen] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);

  useEffect(() => {
    void init();
  }, [init]);

  return (
    <div className={styles.page}>
      <Rail />
      {showLeft && (
        <>
          <AssistantListPanel onNewAssistant={() => setLoginOpen(true)} width={leftWidth} />
          <ResizeHandle
            ariaLabel="调整助手列表宽度"
            dataTestId="resize-left"
            onResize={(d) => setLeftWidth(leftWidth + d)}
          />
        </>
      )}
      <div className={styles.workspace}>
        <TopBar
          onToggleLeft={toggleLeft}
          onToggleRight={toggleRight}
          onContact={() => setContactOpen(true)}
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
          {showRight && (
            <>
              <ResizeHandle
                ariaLabel="调整话题面板宽度"
                dataTestId="resize-right"
                onResize={(d) => setRightWidth(rightWidth - d)}
              />
              <TopicPanel width={rightWidth} />
            </>
          )}
        </div>
      </div>
      <AnnouncementModal />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
      <ContactModal open={contactOpen} onClose={() => setContactOpen(false)} />
    </div>
  );
}
