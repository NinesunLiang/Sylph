// HelpDialog — 帮助与支持弹窗（gold 真值: states/help-dialog[-notice].delta.json）
// 遮罩 rgba(0,0,0,0.44)；弹窗 720x618 居中 白 r8；头 56 pad16 标题 fs16 fw600 居中 + 右上 X
// 左 tabs（icon16+文本 fs14）+ 右内容（fs15 #333, h1 24/h2 20 fw600, 链接 rgb(24,144,255)）
import { useState } from 'react'
import { X, MessageCircle, Bell } from 'lucide-react'
import styles from './index.module.scss'

const A = ({ children, href = '#' }: { children: React.ReactNode; href?: string }) =>
  <a className={styles.link} href={href} onClick={e => e.preventDefault()}>{children}</a>

function ContactTab() {
  return (
    <>
      <h1>欢迎使用 XSimple 一体化 AI 超级平台！</h1>
      <h2>客服联系方式</h2>
      <ul>
        <li>📧 <strong>客服邮箱</strong>: <A>xsimplechat@gmail.com</A>
          <ul>
            <li>请详细说明问题</li>
            <li>不允许讨论违规内容</li>
          </ul>
        </li>
      </ul>
      <h2>平台访问方式</h2>
      <ul>
        {/* gold: 此列表为 li>p 结构（行距 39 = 27 + p.mb6 + li.mb6），与其余列表行距 33 区分 */}
        <li><p>🚀 <strong>主要网址</strong>: <A>https://chat.xsimplechat.com</A> (按 Ctrl + D 收藏本站)</p></li>
        <li><p>🔄 <strong>备用网址</strong>: <A>https://ai.xsimplechat.com</A>、<A>https://chat.xsimplechat.com</A></p></li>
      </ul>
      <h2>⚠️ 注意事项</h2>
      <ul>
        {/* gold: 注意事项五项同为 li>p 结构（两行项 pitch66=54+12，单行项 pitch39=27+12） */}
        <li><p>如果你是中国大陆用户，请严格遵循《生成式人工智能服务管理暂行办法》及其他相关法规</p></li>
        <li><p>对话内容请自行甄别真假，AI生成结果可能存在误差</p></li>
        <li><p>免责声明：因用户违反相关法律法规，或因AI误导导致的任何后果，本平台概不负责</p></li>
        <li><p>本网站仅限学习使用，已启用敏感信息过滤及风控监测系统</p></li>
        <li><p><strong>每人限用一个账号，严禁账号共享、外挂、机器调用或提问敏感问题等行为，一经系统检测违规，将直接封号且费用不予退还</strong></p></li>
      </ul>
    </>
  )
}

function NoticeTab() {
  return (
    <>
      <h1>XSimple AI聚合平台最新公告</h1>
      <p>欢迎使用 XSimple AI聚合平台，为您带来全方位的人工智能服务体验！</p>
      <h2>🌟 平台访问方式</h2>
      <ul>
        <li>🚀 <strong>主要网址</strong>: <A>https://chat.xsimplechat.com</A> (按 Ctrl + D 收藏本站)</li>
        <li>🔄 <strong>备用网址</strong>: <A>https://ai.xsimplechat.com</A>、<A>https://chat.xsimplechat.com</A></li>
        <li>💻 <strong>桌面客户端</strong>: 🌟<A>Windows客户端</A>、🌟<A>MacOS客户端</A></li>
        <li>📱 <strong>手机客户端</strong>: 🌟<A>安卓客户端</A></li>
        <li>📧 <strong>客服邮箱</strong>: <A>xsimplechat@gmail.com</A></li>
      </ul>
      <h2>🚀 模型支持</h2>
      <ul>
        <li>🔥 <strong>Gemini 3 Pro</strong>: Google 最新最强模型</li>
        <li>🔥 <strong>Nano Banana Pro</strong>: Google 最新画图模型</li>
        <li>💪 <strong>GPT-5 & GPT-5.1</strong>：ChatGPT 最新旗舰模型</li>
        <li>🧑‍💻 <strong>Claude Sonnet 4.5</strong>：Anthropic最新模型</li>
        <li>🔥 <strong>GPT-4o 画图功能</strong>: 创新的图像生成能力</li>
        <li>更多模型请进入系统查看</li>
        <li>🧠 <strong>支持全球顶流模型</strong>: 支持ChatGPT 、 Gemini 、 Claude 、 Grok 、 DeepSeek 等全球顶流模型厂商顶流模型~</li>
      </ul>
      <h2>🌟 使用说明</h2>
      <ul>
        <li><strong>1、普通模型</strong>: 性价比最高，响应速度快，适合日常使用</li>
        <li><strong>2、增强模型</strong>:
          <ul>
            <li><strong>主力模型</strong>: 综合性最全面，覆盖多种场景</li>
            <li><strong>推理模型</strong>: 在复杂问题和深度分析上表现优异</li>
          </ul>
        </li>
      </ul>
      <h2>⚠️ 注意事项</h2>
      <ul>
        <li>如果你是中国大陆用户，请严格遵循《生成式人工智能服务管理暂行办法》及其他相关法规</li>
        <li>对话内容请自行甄别真假，AI生成结果可能存在误差</li>
        <li>免责声明：因用户违反相关法律法规，或因AI误导导致的任何后果，本平台概不负责</li>
        <li>本网站仅限学习使用，已启用敏感信息过滤及风控监测系统</li>
        <li><strong>每人限用一个账号，严禁账号共享、外挂、机器调用或提问敏感问题等行为，一经系统检测违规，将直接封号且费用不予退还</strong></li>
      </ul>
    </>
  )
}

export default function HelpDialog({ onClose, initialTab = 'contact' }: {
  onClose: () => void; initialTab?: 'contact' | 'notice'
}) {
  const [tab, setTab] = useState(initialTab)
  return (
    <div className={styles.mask} onClick={onClose}>
      <div className={styles.dialog} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <span className={styles.title}>帮助与支持</span>
          <button className={styles.close} onClick={onClose}><X size={20} /></button>
        </div>
        <div className={styles.body}>
          <div className={styles.tabs}>
            <button className={`${styles.tab} ${tab === 'contact' ? styles['tab--active'] : ''}`} onClick={() => setTab('contact')}>
              <MessageCircle size={16} /><span>联系客服</span>
            </button>
            <button className={`${styles.tab} ${tab === 'notice' ? styles['tab--active'] : ''}`} onClick={() => setTab('notice')}>
              <Bell size={16} /><span>系统公告</span>
            </button>
          </div>
          <div className={styles.content}>
            {/* gold: pane 顶距按 tab 分真值——联系客服 200-194=6 / 系统公告 218-194=24 */}
            <div className={tab === 'contact' ? styles.pane_contact : styles.pane_notice}>
              {tab === 'contact' ? <ContactTab /> : <NoticeTab />}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
