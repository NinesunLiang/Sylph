import { useState } from "react";
import { Button, Form, Input, Modal, Typography } from "antd";
import { EyeInvisibleOutlined, EyeTwoTone } from "@ant-design/icons";
import styles from "./login-modal.module.scss";

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
}

// 登录弹窗（真实站: Clerk cl-modal——"登录到 XSimpleChat / 欢迎回来！"，含密码可见切换）
export function LoginModal({ open, onClose }: LoginModalProps) {
  const [loading, setLoading] = useState(false);

  const handleOk = async () => {
    setLoading(true);
    // 全 mock：模拟登录成功
    await new Promise((r) => setTimeout(r, 600));
    setLoading(false);
    onClose();
  };

  return (
    <Modal
      open={open}
      centered
      width={400}
      maskClosable
      closable
      footer={null}
      className={styles.loginModal}
      data-testid="login-modal"
      onCancel={onClose}
      destroyOnClose
    >
      <div className={styles.header}>
        <div className={styles.logo}>X</div>
        <Typography.Title level={4} className={styles.title}>
          登录到 XSimpleChat
        </Typography.Title>
        <Typography.Text type="secondary">欢迎回来！</Typography.Text>
      </div>
      <Form layout="vertical" className={styles.form} requiredMark={false}>
        <Form.Item label="邮箱地址" name="email" rules={[{ required: true, message: "请输入邮箱地址" }]}>
          <Input placeholder="you@example.com" size="large" data-testid="login-email" />
        </Form.Item>
        <Form.Item label="密码" name="password" rules={[{ required: true, message: "请输入密码" }]}>
          <Input.Password
            placeholder="••••••••"
            size="large"
            iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
            data-testid="login-password"
          />
        </Form.Item>
        <Button
          type="primary"
          block
          size="large"
          loading={loading}
          onClick={handleOk}
          data-testid="login-submit"
        >
          继续
        </Button>
      </Form>
    </Modal>
  );
}
