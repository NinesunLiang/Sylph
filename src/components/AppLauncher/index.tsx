// AppLauncher — 应用启动屏（gold 真值: states/popover-folder-closed.delta.json）
// 侧边栏点击应用图标（知识库等）→ 全屏启动页：logo48 + XSimple fs32 fw900 + 进度条 + 应用启动中...
// 真值明细: logo (654,372) 48x48 / h1 x726 y372 fs32 fw900 / 进度轨 (665,444) 180x8 r100 bg0.06
//           进度填充 45x8 rgb(34,34,34)（采集时为加载中 25%）/ 文本 x723 y466 fs14 #999 + 旋转 svg16
import styles from './index.module.scss'

export default function AppLauncher({ onClose }: { onClose: () => void }) {
  return (
    <div className={styles.launcher} onClick={onClose}>
      <div className={styles.brand}>
        <img className={styles.logo} src="/assets/logo.png" alt="XSimple" />
        {/* gold: 标题容器 div w143 pad-left 12（h1 x726 = 容器 x714 + 12，右缘与容器齐平） */}
        <div className={styles.title}><h1 className={styles.name}>XSimple</h1></div>
      </div>
      <div className={styles.track}><div className={styles.fill} /></div>
      <div className={styles.status}>
        <svg className={styles.spin} width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2a6 6 0 1 1-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <span>应用启动中...</span>
      </div>
    </div>
  )
}
