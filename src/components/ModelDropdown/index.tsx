// ModelDropdown — 模型选择下拉（gold 真值: states/model-dropdown.delta.json）
// 容器 434x620 白底 r5 pad4 三层 antd 阴影，向上打开，左对齐 pill，间隙 6
// 行 h36 r3 pad 7px 12px，选中行 bg rgba(0,0,0,0.03)；组头 fs14 #999
import { Eye, ToyBrick, Atom, Globe } from 'lucide-react'
import { MODELS_BASIC, MODELS_ENHANCED, CAP_STYLE } from './models'
import type { ModelRow } from './models'
// gold: 组头 = 20px 旋涡 svg（currentColor 继承 #999）+ gap4 + 文本；🔥 为文本 emoji 非图片
import swirlRaw from '/assets/models/gpt.svg?raw'
import styles from './index.module.scss'

const CAP_ICON: Record<string, typeof Eye> = { eye: Eye, 'toy-brick': ToyBrick, atom: Atom, globe: Globe }

function Row({ m, selected, onPick }: { m: ModelRow; selected: boolean; onPick: (n: string) => void }) {
  return (
    <li className={`${styles.row} ${selected ? styles['row--selected'] : ''}`} onClick={() => onPick(m.name)}>
      <span className={styles.row_logo} style={{ background: m.logoBg }}>
        <img src={m.logo} alt="" width={m.logoInner} height={m.logoInner} />
      </span>
      <span className={styles.row_name}>{m.name}</span>
      {m.flame && <img className={styles.row_flame} src="/assets/models/flame.webp" alt="🔥" />}
      <span className={styles.row_right}>
        {m.caps.map(c => {
          const Icon = CAP_ICON[c]
          const [color, bg] = CAP_STYLE[c]
          return Icon ? <span key={c} className={styles.row_cap} style={{ color, background: bg }}><Icon size={14} /></span> : null
        })}
        <span className={styles.row_tag}>{m.tag}</span>
      </span>
    </li>
  )
}

export default function ModelDropdown({ current, onPick, onClose }: {
  current: string; onPick: (n: string) => void; onClose: () => void
}) {
  return (
    <ul className={styles.menu} onMouseDown={e => e.stopPropagation()}>
      <li className={styles.group}><div className={styles.group_in}><span className={styles.group_swirl} dangerouslySetInnerHTML={{ __html: swirlRaw }} />基础模型</div></li>
      {MODELS_BASIC.map(m => <Row key={m.name} m={m} selected={m.name === current} onPick={onPick} />)}
      <li className={styles.group}><div className={styles.group_in}><span className={styles.group_swirl} dangerouslySetInnerHTML={{ __html: swirlRaw }} />增强模型🔥</div></li>
      {MODELS_ENHANCED.map(m => <Row key={m.name} m={m} selected={m.name === current} onPick={onPick} />)}
    </ul>
  )
}
