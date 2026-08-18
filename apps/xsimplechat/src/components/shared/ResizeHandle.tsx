import { useCallback, useRef } from "react";
import styles from "./resize-handle.module.scss";

interface ResizeHandleProps {
  onResize: (delta: number) => void;
  ariaLabel: string;
  dataTestId?: string;
}

// 水平拖拽分隔条（侧栏调宽；mousemove 实时上报增量，宿主用 getState 读最新宽度避免闭包竞态）
export function ResizeHandle({ onResize, ariaLabel, dataTestId }: ResizeHandleProps) {
  const lastX = useRef(0);
  const dragging = useRef(false);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      lastX.current = e.clientX;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      const onMove = (ev: MouseEvent) => {
        if (!dragging.current) return;
        const delta = ev.clientX - lastX.current;
        lastX.current = ev.clientX;
        if (delta !== 0) onResize(delta);
      };
      const onUp = () => {
        if (!dragging.current) return;
        dragging.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [onResize],
  );

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={ariaLabel}
      className={styles.handle}
      data-testid={dataTestId}
      onMouseDown={onMouseDown}
    />
  );
}
