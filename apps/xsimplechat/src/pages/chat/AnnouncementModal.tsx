import { useEffect, useMemo, useState } from "react";
import { Modal } from "antd";
import { useChatStore } from "@/store/chat-store";
import styles from "./announcement-modal.module.scss";

// 系统公告弹窗（真实站: ant-modal 家族，页面加载自动弹出，含动画；Esc/遮罩/× 关闭，本会话不再弹出）
export function AnnouncementModal() {
  const { announcement, announcementDismissed, dismissAnnouncement } = useChatStore();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (announcement && !announcementDismissed) {
      const t = setTimeout(() => setOpen(true), 400); // 页面入场后再弹
      return () => clearTimeout(t);
    }
    return undefined;
  }, [announcement, announcementDismissed]);

  const content = useMemo(() => {
    if (!announcement) return null;
    return announcement.content.split("\n").filter(Boolean);
  }, [announcement]);

  return (
    <Modal
      open={open}
      title={announcement?.title ?? "系统公告"}
      centered
      width={420}
      maskClosable
      closable
      footer={null}
      className={styles.announceModal}
      data-testid="announce-modal"
      onCancel={() => {
        setOpen(false);
        dismissAnnouncement();
      }}
      destroyOnClose
    >
      <div className={styles.body} data-testid="announce-body">
        {content?.map((line, i) => (
          <p key={i} className={styles.line}>
            {line}
          </p>
        ))}
      </div>
    </Modal>
  );
}
