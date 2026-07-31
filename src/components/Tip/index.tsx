// Tip — 悬浮提示组件类（gold 真值: states/tooltip-*.delta.json）
// 一类组件而非个例：任何 icon/按钮包一层即获得与原型一致的悬停气泡
// 行为真值: mount-on-hover —— gold 悬停才挂载气泡节点；
//           常挂 opacity-0 会在 capture-states 的 before 集中出现 → delta=0 无法闭环（§十三 定律）
// 结构真值: 无快捷键时文本直挂气泡（gold 文本节点 ownText 父级 = 气泡壳，x = 壳 x）；
//           有快捷键时文本在内层 span（gold tooltip-将当前会话保存为话题：内层 div x = 壳 x + pad8）
// 定位真值: bottom=topbar/输入条（图标下 4px 居中）top=底部条（图标上 4px）right=侧边栏（图标右 4px 垂直居中）
// 钳位真值（视口碰撞律）: gold 气泡永不溢出视口——右侧贴边（tooltip-会话设置 x=vw-w）、
//           左侧贴边（tooltip-联系客服 x=0）；挂载后实测 rect 自动钳位，非手工坐标
// 快捷键真值: keys —— kbd fs12 #999 bg rgba(153,153,153,0.15) r5 pad0 8 lh22，键间距 4
import { useState, useRef, useEffect } from 'react'

export default function Tip({ text, children, className = '', onClick, place, keys }: {
  text: string
  children: React.ReactNode
  className?: string
  onClick?: () => void
  place?: 'bottom' | 'top' | 'right'
  keys?: string[]
}) {
  const [show, setShow] = useState(false)
  const [clamp, setClamp] = useState(0)
  const tipRef = useRef<HTMLSpanElement>(null)
  // 视口碰撞自动钳位（gold 真值：气泡恒在视口内，贴边 0 间距）
  useEffect(() => {
    if (!show || !tipRef.current) return
    const r = tipRef.current.getBoundingClientRect()
    let dx = 0
    if (r.left < 0) dx = -r.left
    else if (r.right > window.innerWidth) dx = window.innerWidth - r.right
    setClamp(prev => prev === dx ? prev : dx)
  }, [show])
  const placeCls = place && place !== 'bottom' ? ` tip--${place}` : ''
  return (
    <span
      className={`has-tip ${className}`}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => { setShow(false); setClamp(0) }}
      onClick={onClick}
    >
      {children}
      {show && (
        <span ref={tipRef} className={`tip${placeCls}`} style={clamp ? { marginLeft: clamp } : undefined}>
          {keys ? <span className="tip_text">{text}</span> : text}
          {keys && <span className="tip_keys">{keys.map((k, i) => <kbd key={i}><span>{k}</span></kbd>)}</span>}
        </span>
      )}
    </span>
  )
}
