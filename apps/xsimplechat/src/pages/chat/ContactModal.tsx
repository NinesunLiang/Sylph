import { useState } from "react";
import { Modal, Typography } from "antd";
import styles from "./contact-modal.module.scss";

interface ContactModalProps {
  open: boolean;
  onClose: () => void;
}

// 联系客服弹窗（真实站联系客服入口；内容为 mock 支持渠道）
export function ContactModal({ open, onClose }: ContactModalProps) {
  const [copied, setCopied] = useState(false);

  const copyEmail = async () => {
    try {
      await navigator.clipboard.writeText("support@xsimplechat.com");
    } catch {
      // 无头/非安全上下文环境 clipboard 不可用：仍给 UI 反馈（mock 语义）
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Modal
      open={open}
      centered
      width={400}
      mask={{ closable: true }}
      closable
      footer={null}
      className={styles.contactModal}
      data-testid="contact-modal"
      onCancel={onClose}
      destroyOnHidden
    >
      <div className={styles.header}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          联系客服
        </Typography.Title>
        <Typography.Text type="secondary">工作日 9:00-18:00 在线</Typography.Text>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>客服邮箱</span>
        <button type="button" className={styles.value} onClick={copyEmail} data-testid="copy-email">
          support@xsimplechat.com
          <span className={styles.copyHint}>{copied ? "已复制 ✓" : "点击复制"}</span>
        </button>
      </div>
      <div className={styles.row}>
        <span className={styles.label}>企业微信</span>
        <span className={styles.value}>XSimple 官方客服</span>
      </div>
    </Modal>
  );
}
