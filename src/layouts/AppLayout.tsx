import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  MessageSquare, SquareParking, Languages, FolderClosed, Compass, Gem,
  Activity, BookOpenText, MessageCircleQuestion, MessageSquarePlus,
  Search, ChevronDown, ChevronLeft, ChevronRight, Plus, Ellipsis, X, MessageSquareDashed,
  PanelLeftClose, Import, Share2, PanelRightClose, AlignJustify,
} from 'lucide-react'
import { useState, useCallback, useRef } from 'react'
import AnnouncementModal from '@/components/AnnouncementModal'
import HelpDialog from '@/components/HelpDialog'
import AppLauncher from '@/components/AppLauncher'
import Tip from '@/components/Tip'
import styles from './AppLayout.module.scss'

// 图标顺序与原型 DOM 提取一致（proto-styles.json: lucide-* class 真值）
// tip = gold states/tooltip-*.delta.json 悬浮提示真值（空串 = gold 无提示证据，不编造）
// launcher = gold popover-folder-closed.delta.json 真值：点击进应用启动屏
type NavItem = { to: string; icon: typeof MessageSquare; tip: string; place?: 'right' | 'top'; launcher?: boolean }
const iconNav: NavItem[] = [
  { to: '/chat', icon: MessageSquare, tip: '会话' },
  { to: '/aippt', icon: SquareParking, tip: 'AI PPT' },
  { to: '#', icon: Languages, tip: '翻译' },
  { to: '#', icon: FolderClosed, tip: '', launcher: true },
  { to: '/discover', icon: Compass, tip: '发现' },
  { to: '#', icon: Gem, tip: '会员' },
]
const iconNavBottom: NavItem[] = [
  { to: '#', icon: Activity, tip: '' },
  { to: '#', icon: BookOpenText, tip: '' },
  { to: '#', icon: MessageCircleQuestion, tip: '联系客服', place: 'top' }, // gold: 气泡在图标上、视口左缘钳位 x0（Tip 运行时自动钳位）
]

const assistants = [{ id: '1', name: '随便聊聊' }]

function DragHandle({ onDrag, onToggle, collapsed, dir }: { onDrag: (dx: number) => void; onToggle: () => void; collapsed: boolean; dir: 'left' | 'right' }) {
  const dragging = useRef(false)
  const lastX = useRef(0)
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault(); dragging.current = true; lastX.current = e.clientX
    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return
      const dx = ev.clientX - lastX.current; lastX.current = ev.clientX; onDrag(dx)
    }
    const onUp = () => {
      dragging.current = false
      window.removeEventListener('mousemove', onMove)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp, { once: true })
  }, [onDrag])
  // 折叠钮（原型真值：分隔线中点胶囊钮，展开时 chevron 指向聊天区=折叠方向）
  const Icon = dir === 'left' ? (collapsed ? ChevronLeft : ChevronRight) : (collapsed ? ChevronRight : ChevronLeft)
  return (
    <div className={styles.drag_handle} onMouseDown={onMouseDown}>
      <button className={styles.drag_handle_toggle} onMouseDown={e => e.stopPropagation()} onClick={onToggle}><Icon size={14} /></button>
    </div>
  )
}

export default function AppLayout() {
  const loc = useLocation()
  const isConsole = loc.pathname === '/' || loc.pathname === '/chat'
  const isAssistantDetail = loc.pathname === '/discover/assistant/assistants-health-better' || loc.pathname === '/discoverassistant/assistants-health-better'
  const isDiscoverShell = !isConsole
  const [showAnnouncement, setShowAnnouncement] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showLauncher, setShowLauncher] = useState(false)
  const [showTopicCard, setShowTopicCard] = useState(true)
  const [leftW, setLeftW] = useState(321)
  const [rightW, setRightW] = useState(281)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const _onClose = useCallback(() => setShowAnnouncement(false), [])
  // 面板拖拽 min/max 约束（近似值：proto 默认 321/281 [内部自检，非行业标准]，观测到的 proto 会话最窄 ≈209）
  const _onLeftDrag = useCallback((dx: number) => setLeftW(w => Math.max(260, Math.min(420, w + dx))), [])
  const _onRightDrag = useCallback((dx: number) => setRightW(w => Math.max(200, Math.min(400, w - dx))), [])

  return (
    <div className={styles.app_layout} style={{ height: '100vh', display: 'flex' }}>
      {/* Col 1: Icon sidebar */}
      <aside className={styles.app_layout_sidebar}>
        <img className={styles.app_layout_sidebar_logo} src="/assets/logo.png" alt="XSimple" />
        <nav className={styles.app_layout_sidebar_nav}>
          {iconNav.map((item, i) => {
            const click = item.launcher ? () => setShowLauncher(true) : undefined
            const inner = <item.icon size={24} />
            const body = item.tip
              ? <Tip text={item.tip} place="right" className={styles.app_layout_sidebar_tip} onClick={click}>{inner}</Tip>
              : inner
            return item.to === '#' ? (
              <button key={i} className={styles.app_layout_sidebar_icon} onClick={click}>{body}</button>
            ) : (
              <NavLink key={i} to={item.to} end className={({ isActive }) =>
                `${styles.app_layout_sidebar_icon} ${isActive ? styles['app_layout_sidebar_icon--active'] : ''}`
              }>{body}</NavLink>
            )
          })}
        </nav>
        <nav className={styles.app_layout_sidebar_nav_bottom}>
          {iconNavBottom.map((item, i) => (
            <button key={i} className={styles.app_layout_sidebar_icon}>
              {item.tip
                ? <Tip text={item.tip} place={item.place ?? 'right'} className={styles.app_layout_sidebar_tip}><item.icon size={20} /></Tip>
                : <item.icon size={20} />}
            </button>
          ))}
        </nav>
      </aside>

      {/* Col 2: Assistant panel（可拖拽 260-420，胶囊钮折叠） */}
      {isConsole && (
        <>
          {/* gold: popover-chevron-right —— 折叠不卸载 DOM（宽 0 + overflow hidden，afterCount≈beforeCount 真值），
              key 切换强制重挂载（gold delta=168 为面板重挂载证据） */}
          <aside
            key={String(leftCollapsed)}
            className={styles.app_layout_assistants}
            style={{ width: leftCollapsed ? 0 : leftW, overflow: 'hidden', flexShrink: 0 }}
          >
            <div style={{ width: leftW, flexShrink: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div className={styles.app_layout_assistants_header}>
              <span>XSimple</span>
              <Tip text="新建助手" className={styles.app_layout_assistants_header_new_wrap}>
                <MessageSquarePlus size={20} className={styles.app_layout_assistants_header_new} />
              </Tip>
            </div>
            <div className={styles.app_layout_assistants_search}>
              <div className={styles.app_layout_assistants_search_box}>
                <Search size={14} />
                <input placeholder="搜索助手..." />
                <span className={styles.app_layout_assistants_search_hint}><span>{'⌘  K'}</span></span>
              </div>
            </div>
            <div className={styles.app_layout_assistants_list}>
              {assistants.map(a => (
                <div key={a.id} className={`${styles.app_layout_assistants_item} ${styles['app_layout_assistants_item--active']}`}>
                  <img className={styles.app_layout_assistants_item_avatar} src="/assets/inbox_avatar.svg" alt="" />
                  <div><div className={styles.app_layout_assistants_item_name}>{a.name}</div></div>
                </div>
              ))}
              <div className={styles.app_layout_assistants_group}>
                <span>默认列表</span>
                <ChevronDown size={16} />
              </div>
              <button className={styles.app_layout_assistants_new}><Plus size={14} /><span>新建助手</span></button>
            </div>
            </div>
          </aside>
          <DragHandle onDrag={_onLeftDrag} onToggle={() => setLeftCollapsed(c => !c)} collapsed={leftCollapsed} dir="left" />
        </>
      )}

      {/* Col 3+4: 主列（topbar 全宽横跨聊天+右面板，原型真值：联系客服位于右面板上方） */}
      <div className={styles.app_layout_main}>
        {isConsole && (
          <div className={styles.app_layout_topbar}>
            <div className={styles.app_layout_topbar_left}>
              <PanelLeftClose size={20} className={styles.app_layout_topbar_collapse} />
              <img className={styles.app_layout_topbar_logo} src="/assets/inbox_avatar.svg" alt="AI" />
              <span className={styles.app_layout_topbar_name}>随便聊聊</span>
              <span className={styles.app_layout_topbar_badge}><span className={styles.app_layout_topbar_badge_inner}><img className={styles.app_layout_topbar_badge_avatar} src="/assets/inbox_avatar.svg" alt="" />GPT-5.6 Luna</span></span>
            </div>
            <div className={styles.app_layout_topbar_right}>
              <button className={styles.app_layout_topbar_kefu} onClick={() => setShowHelp(true)}><MessageCircleQuestion size={20} />联系客服</button>
              <button className={styles.app_layout_topbar_install}><Import size={20} />安装到桌面</button>
              <Tip text="分享" className={styles.app_layout_topbar_icon}><Share2 size={20} /></Tip>
              <Tip text="角色与记录" className={styles.app_layout_topbar_icon} onClick={() => setRightCollapsed(c => !c)}><PanelRightClose size={20} /></Tip>
              <Tip text="会话设置" className={styles.app_layout_topbar_icon}><AlignJustify size={20} /></Tip>
            </div>
          </div>
        )}
        {isDiscoverShell && (
          <div className={styles.app_layout_discover_topbar}>
            <strong>XSimple</strong><span className={styles.app_layout_discover_slash}>/</span><span>{loc.pathname === '/aippt' ? 'AI PPT' : '发现'}</span>
            <label><Search size={18} /><input placeholder="搜索名称介绍或关键词..." /><kbd>⌘ K</kbd></label>
          </div>
        )}
        {false && (
          <div className={styles.app_layout_topbar}>
            <div className={styles.app_layout_topbar_left}>
              <PanelLeftClose size={20} className={styles.app_layout_topbar_collapse} />
              <img className={styles.app_layout_topbar_logo} src="/assets/inbox_avatar.svg" alt="AI" />
              <span className={styles.app_layout_topbar_name}>随便聊聊</span>
              <span className={styles.app_layout_topbar_badge}><span className={styles.app_layout_topbar_badge_inner}><img className={styles.app_layout_topbar_badge_avatar} src="/assets/inbox_avatar.svg" alt="" />GPT-5.6 Luna</span></span>
            </div>
            <div className={styles.app_layout_topbar_right}>
              <button className={styles.app_layout_topbar_kefu} onClick={() => setShowHelp(true)}><MessageCircleQuestion size={20} />联系客服</button>
              <button className={styles.app_layout_topbar_install}><Import size={20} />安装到桌面</button>
              {/* topbar 图标悬浮提示（gold: tooltip-分享/角色与记录/会话设置）；PanelRightClose 点击折叠右面板 */}
              <Tip text="分享" className={styles.app_layout_topbar_icon}><Share2 size={20} /></Tip>
              <Tip text="角色与记录" className={styles.app_layout_topbar_icon} onClick={() => setRightCollapsed(c => !c)}><PanelRightClose size={20} /></Tip>
              <Tip text="会话设置" className={styles.app_layout_topbar_icon}><AlignJustify size={20} /></Tip>
            </div>
          </div>
        )}
        <div className={styles.app_layout_content}>
          <div className={styles.app_layout_chat}><Outlet /></div>
          {isConsole && (
            <>
              <DragHandle onDrag={_onRightDrag} onToggle={() => setRightCollapsed(c => !c)} collapsed={rightCollapsed} dir="right" />
              {!rightCollapsed && (
              <aside className={styles.app_layout_right} style={{ width: rightW }}>
            <div className={styles.app_layout_right_header}>
              <span className={styles.app_layout_right_header_title}>话题</span>
              <div className={styles.app_layout_right_header_actions}>
                <Search size={14} />
                <Ellipsis size={14} />
              </div>
            </div>
            <div className={styles.app_layout_right_content}>
              {showTopicCard && (
                <div className={styles.app_layout_right_card}>
                  <div className={styles.app_layout_right_card_illus}>
                    <img src="/assets/empty_topic.webp" alt="" />
                    <button className={styles.app_layout_right_card_close} onClick={() => setShowTopicCard(false)}><X size={16} /></button>
                  </div>
                  <div className={styles.app_layout_right_card_body}>
                    <div className={styles.app_layout_right_section_title}>话题列表</div>
                    <div className={styles.app_layout_right_empty}>点击发送左侧按钮可将当前会话保存为历史话题，并开启新一轮会话</div>
                  </div>
                </div>
              )}
              <div className={styles.app_layout_right_topic}>
                <MessageSquareDashed size={14} />
                <span className={styles.app_layout_right_topic_name}>默认话题</span>
                <span className={styles.app_layout_right_topic_badge}><span>临时</span></span>
              </div>
            </div>
              </aside>
              )}
            </>
          )}
        </div>
      </div>

      {showAnnouncement && <AnnouncementModal onClose={_onClose} />}
      {showHelp && <HelpDialog onClose={() => setShowHelp(false)} />}
      {showLauncher && <AppLauncher onClose={() => setShowLauncher(false)} />}
    </div>
  )
}
