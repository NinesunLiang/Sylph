import { useState } from "react";
import {
  ChevronDown,
  Eraser,
  FileStack,
  Inbox,
  LayoutGrid,
  Maximize2,
  Mic,
  Paperclip,
  SlidersHorizontal,
} from "lucide-react";
import { Dropdown, Tooltip } from "antd";
import { CheckOutlined } from "@ant-design/icons";
import { SwirlIcon } from "@/components/shared/SwirlIcon";
import { useChatStore } from "@/store/chat-store";
import styles from "./composer.module.scss";

interface ComposerProps {
  disabled?: boolean;
  onSend?: (content: string) => void;
}

// 底部输入区（真实站: 模型胶囊 + 工具图标 + 输入框 + 发送按钮）
export function Composer({ disabled = false, onSend }: ComposerProps) {
  const [value, setValue] = useState("");
  const models = useChatStore((s) => s.models);
  const selectedModelId = useChatStore((s) => s.selectedModelId);
  const selectModel = useChatStore((s) => s.selectModel);

  const selectedModel = models.find((m) => m.id === selectedModelId) ?? {
    id: "gpt-5.6-luna",
    name: "GPT-5.6 Luna",
  };

  const handleSend = () => {
    if (disabled || !value.trim()) return;
    onSend?.(value.trim());
    setValue("");
  };

  const modelMenu = {
    items: models.map((m) => ({
      key: m.id,
      label: m.name,
      icon: m.id === selectedModelId ? <CheckOutlined /> : undefined,
    })),
    onClick: ({ key }: { key: string }) => selectModel(key),
  };

  return (
    <footer className={styles.composer} data-testid="composer">
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <Dropdown menu={modelMenu} trigger={["click"]} placement="topLeft" data-testid="model-dropdown">
            <button type="button" className={styles.modelPill} data-testid="model-selector">
              <span className={styles.modelDot}>
                <SwirlIcon size={11} />
              </span>
              <span className={styles.modelName}>{selectedModel.name}</span>
            </button>
          </Dropdown>
          <Tooltip title="添加附件">
            <button type="button" className={styles.toolBtn} aria-label="添加附件">
              <Paperclip size={16} />
            </button>
          </Tooltip>
          <Tooltip title="资料">
            <button type="button" className={styles.toolBtn} aria-label="资料">
              <FileStack size={16} />
            </button>
          </Tooltip>
          <Tooltip title="调节">
            <button type="button" className={styles.toolBtn} aria-label="调节">
              <SlidersHorizontal size={16} />
            </button>
          </Tooltip>
          <Tooltip title="语音输入">
            <button type="button" className={styles.toolBtn} aria-label="语音输入">
              <Mic size={16} />
            </button>
          </Tooltip>
          <Tooltip title="工具">
            <button type="button" className={styles.toolBtn} aria-label="工具">
              <LayoutGrid size={16} />
            </button>
          </Tooltip>
        </div>
        <div className={styles.toolbarRight}>
          <Tooltip title="清空">
            <button
              type="button"
              className={styles.toolBtn}
              aria-label="清空"
              data-testid="clear-messages"
              onClick={() => {
                setValue("");
                useChatStore.getState().resetMessages();
              }}
            >
              <Eraser size={16} />
            </button>
          </Tooltip>
          <Tooltip title="展开">
            <button type="button" className={styles.toolBtn} aria-label="展开">
              <Maximize2 size={16} />
            </button>
          </Tooltip>
        </div>
      </div>

      <textarea
        className={styles.input}
        placeholder="输入聊天内容..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.metaKey && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        rows={2}
        data-testid="chat-input"
      />

      <div className={styles.actions}>
        <span className={styles.hint}>↵ 发送 / ⌘ ↵ 换行</span>
        <div className={styles.actionBtns}>
          <Dropdown
            menu={{
              items: [
                { key: "panel", label: "会话面板" },
                { key: "knowledge", label: "知识库" },
                { key: "artifacts", label: "Artifacts" },
              ],
            }}
            trigger={["click"]}
            placement="topRight"
          >
            <Tooltip title="会话面板">
              <button type="button" className={styles.trayBtn} aria-label="会话面板" data-testid="tray-menu">
                <Inbox size={17} strokeWidth={2.2} />
              </button>
            </Tooltip>
          </Dropdown>
          <div className={styles.sendGroup} data-testid="send-group">
            <button
              type="button"
              className={styles.sendBtn}
              disabled={disabled}
              onClick={handleSend}
              data-testid="send-button"
            >
              <span>发送</span>
            </button>
            <Dropdown
              menu={{
                items: [
                  { key: "send", label: "发送" },
                  { key: "regenerate", label: "重新生成" },
                  { key: "continue", label: "继续生成" },
                ],
              }}
              trigger={["click"]}
              placement="topRight"
            >
              <button type="button" className={styles.sendArrow} aria-label="发送选项" data-testid="send-arrow">
                <ChevronDown size={14} />
              </button>
            </Dropdown>
          </div>
        </div>
      </div>
    </footer>
  );
}
