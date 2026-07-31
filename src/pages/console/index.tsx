import { useState, useRef, useEffect } from 'react'
import {
  Paperclip, LibraryBig, SlidersHorizontal, Mic, Blocks, Eraser, Maximize2,
  GalleryVerticalEnd, ChevronDown, ChevronUp, CornerDownLeft, Command, RefreshCw,
} from 'lucide-react'
import ModelDropdown from '@/components/ModelDropdown'
import UploadMenu from '@/components/UploadMenu'
import AdvancedParams from '@/components/AdvancedParams'
import Tip from '@/components/Tip'
import styles from './index.module.scss'

interface Message { role: 'user' | 'assistant'; content: string }

// 卡片图标与原型一致（proto-styles.json: fluent-emoji-3d webp 真值）
const cards = [
  { name: '健身专家', icon: '/assets/card_basketball.webp', desc: '知识渊博的健身专家' },
  { name: 'Mistaker', icon: '/assets/card_book.webp', desc: '通过清晰的解释和语法、发音示例来消除错误。' },
  { name: '代码优化/错误修改', icon: '/assets/card_robot.webp', desc: '精通多种编程语言，优化代码结构，修复错误并提供优雅的解决方案。' },
  { name: '伦理安全分析师', icon: '/assets/card_detective.webp', desc: '专注于识别和减轻网络和移动平台中的安全漏洞。' },
]

export default function ConsolePage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [showChat, setShowChat] = useState(false)
  const [model, setModel] = useState('GPT-5.6 Luna')
  const [showModels, setShowModels] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [showParams, setShowParams] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const hour = new Date().getHours()
  const greet = hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好'

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  // 二级 UI 统一外点关闭（菜单 stopPropagation 防自相残杀）
  useEffect(() => {
    if (!showModels && !showUpload && !showParams) return
    const close = () => { setShowModels(false); setShowUpload(false); setShowParams(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [showModels, showUpload, showParams])

  const send = () => {
    if (!input.trim()) return
    setShowChat(true)
    setMessages(prev => [...prev, { role: 'user', content: input.trim() }])
    setInput('')
    setTimeout(() => setMessages(prev => [...prev, { role: 'assistant', content: '收到，我在帮你处理。' }]), 1000)
  }

  return (
    <div className={styles.console}>
      {!showChat ? (
        <div className={styles.greeting}>
          <div className={styles.greeting_row}>
            <img className={styles.greeting_wave} src="/assets/wave.webp" alt="👋" />
            <h2 className={styles.greeting_text}>{greet}</h2>
          </div>
          <p className={styles.greeting_desc}>我是您的私人智能助理 XSimple ，请问现在能帮您做什么？<br />如果需要获得更加专业或定制的助手，可以点击 <code className={styles.greeting_plus}>+</code> 创建自定义助手</p>
          <div className={styles.greeting_label_row}>
            <span className={styles.greeting_label}>新增助手推荐：</span>
            <RefreshCw size={14} className={styles.greeting_refresh} />
          </div>
          <div className={styles.grid}>
            {cards.map((c, i) => (
              <a key={i} className={styles.card} onClick={() => setInput(`使用${c.name}`)}>
                <img className={styles.card_icon} src={c.icon} alt="" />
                <div className={styles.card_right}>
                  <div className={styles.card_title}>{c.name}</div>
                  <div className={styles.card_desc}>{c.desc}</div>
                </div>
              </a>
            ))}
          </div>
        </div>
      ) : (
        <div className={styles.msgs}>
          {messages.map((m, i) => (
            <div key={i} className={styles.msg}>
              <div className={styles.msg_avatar + ' ' + (m.role === 'assistant' ? styles.msg_avatar_ai : styles.msg_avatar_user)}>
                {m.role === 'assistant' ? 'X' : 'U'}
              </div>
              <div className={styles.msg_bubble}>{m.content}</div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      )}

      {/* 输入区（gold 真值：顶部折叠胶囊 → 工具行 → 输入框 → 右对齐底部簇） */}
      <div className={styles.input_area}>
        <button className={styles.input_collapse}><ChevronUp size={14} /></button>
        <div className={styles.input_box}>
          <div className={styles.input_toolbar}>
            <span className={styles.input_model} onClick={() => { setShowModels(v => !v); setShowUpload(false); setShowParams(false) }}>
              <img src="/assets/inbox_avatar.svg" alt="" /><span>{model}</span>
              {showModels && <ModelDropdown current={model} onPick={n => { setModel(n); setShowModels(false) }} onClose={() => setShowModels(false)} />}
            </span>
            {/* 工具栏悬浮提示（gold 真值: 用户截图 + states/tooltip-* —— 一类组件统一 Tip） */}
            <Tip text="上传" className={styles.input_tool} onClick={() => { setShowUpload(v => !v); setShowModels(false); setShowParams(false) }}>
              <Paperclip size={20} />
              {showUpload && <UploadMenu onPick={() => setShowUpload(false)} />}
            </Tip>
            <Tip text="知识库" className={styles.input_tool}><LibraryBig size={20} /></Tip>
            {/* gold: popover-sliders-horizontal —— 点击开高级参数面板（delta 无气泡 → 无 tooltip） */}
            <span className={styles.input_tool} onClick={() => { setShowParams(v => !v); setShowModels(false); setShowUpload(false) }}>
              <SlidersHorizontal size={20} />
              {showParams && <AdvancedParams />}
            </span>
            <Tip text="语音输入" className={styles.input_tool}><Mic size={22} /></Tip>
            <Tip text="扩展插件" className={styles.input_tool}><Blocks size={20} /></Tip>
            <span className={styles.input_tool_spacer} />
            <Tip text="清空当前会话消息" className={styles.input_tool}><Eraser size={20} /></Tip>
            <span className={styles.input_tool}><Maximize2 size={20} /></span>
          </div>
          <textarea className={styles.input} placeholder="输入聊天内容..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
        </div>
        <div className={styles.input_bottom}>
          <span className={styles.input_hint}>
            <CornerDownLeft size={12} /><span>发送</span><span>/</span><Command size={12} /><CornerDownLeft size={12} /><span>换行</span>
          </span>
          <div className={styles.input_right}>
            {/* gold: tooltip-将当前会话保存为话题 + kbd ⌘N（气泡在图标上方） */}
            <Tip text="将当前会话保存为话题" place="top" keys={['⌘', 'N']} className={styles.input_attach}><GalleryVerticalEnd size={16} /></Tip>
            <button className={styles.input_btn} onClick={send} disabled={!input.trim()}><span>发 送</span></button>
            <button className={styles.input_arrow}><ChevronDown size={16} /></button>
          </div>
        </div>
      </div>
    </div>
  )
}
