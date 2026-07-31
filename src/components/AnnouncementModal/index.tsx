import { useEffect } from 'react'
import styles from './index.module.scss'

interface Props { onClose: () => void }

export default function AnnouncementModal({ onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <span className={styles.header_title}>系统公告</span>
          <button className={styles.header_close} onClick={onClose}>×</button>
        </div>
        <div className={styles.body}>
          <div className={styles.section_title}>XSimple AI聚合平台最新公告</div>
          <p className={styles.body_text}>欢迎使用 XSimple AI聚合平台，为您带来全方位的人工智能服务体验！</p>

          <div className={styles.section_emoji_title}>🌟 平台访问方式</div>
          <div className={styles.link_row}>
            <span className={styles.link_label}>🚀 主要网址: </span>
            <a className={styles.link_url} href="https://chat.xsimplechat.com" target="_blank">https://chat.xsimplechat.com</a>
            <span style={{ color: '#999', fontSize: 13 }}>(按 Ctrl + D 收藏本站)</span>
          </div>
          <div className={styles.link_row}>
            <span className={styles.link_label}>🔄 备用网址: </span>
            <a className={styles.link_url} href="https://ai.xsimplechat.com" target="_blank">https://ai.xsimplechat.com</a>
            <span style={{ color: '#999' }}>、</span>
            <a className={styles.link_url} href="https://chat.xsimplechat.com" target="_blank">https://chat.xsimplechat.com</a>
          </div>
          <div className={styles.link_row}>
            <span className={styles.link_label}>💻 桌面客户端: </span>
            <a className={styles.link_url} href="#">⭐ Windows客户端</a>
            <span style={{ color: '#999' }}>、</span>
            <a className={styles.link_url} href="#">⭐ MacOS客户端</a>
          </div>
          <div className={styles.link_row}>
            <span className={styles.link_label}>📱 手机客户端: </span>
            <a className={styles.link_url} href="#">⭐ 安卓客户端</a>
          </div>
          <div className={styles.link_row}>
            <span className={styles.link_label}>📧 客服邮箱: </span>
            <a className={styles.link_url} href="mailto:xsimplechat@gmail.com">xsimplechat@gmail.com</a>
          </div>

          <div className={styles.section_emoji_title}>🚀 模型支持</div>
          <div className={styles.model_list}>
            <div className={styles.model_item}>🔥 Gemini 3 Pro: Google 最新最强模型</div>
            <div className={styles.model_item}>💪 Nano Banana Pro</div>
            <div className={styles.model_item}>👥 GPT-5 &amp; GPT-5.1</div>
            <div className={styles.model_item}>Claude Sonnet 4.5</div>
          </div>

          <div className={styles.section_emoji_title}>⚠️ 注意事项</div>
          <p className={styles.body_text}>如果你是中国大陆用户，请严格遵循《生成式人工智能服务管理暂行办法》及其他相关法规</p>
          <p className={styles.body_text}>对话内容请自行甄别真假，AI生成结果可能存在误差</p>
          <p className={styles.body_text}>免责声明：因用户违反相关法律法规，或因AI误导导致的任何后果，本平台概不负责</p>
          <p className={styles.body_text}>本网站仅限学习使用，已启用敏感信息过滤及风控监测系统</p>
          <p className={styles.body_text} style={{ fontWeight: 700 }}>每人限用一个账号，严禁账号共享、外挂、机器调用或提问敏感问题等行为，一经系统检测违规，将直接封号且费用不予退还</p>
        </div>
        <div className={styles.footer}>
          <button className={styles.btn_cancel} onClick={onClose}>取 消</button>
          <button className={styles.btn_confirm} onClick={onClose}>确 定</button>
        </div>
      </div>
    </div>
  )
}
