// AdvancedParams — 高级参数面板（gold 真值: states/popover-sliders-horizontal.delta.json，逐字段对齐）
// 触发语义: 输入条 sliders 图标 click（gold delta 无深色气泡 → 该图标无 tooltip，纯点击面板，禁止加 Tip）
// 壳: w400 h136 r8 白底 border 1px rgb(227,227,227) antd 三层影 pad13，相对触发器居中上 4px（gold: x411 y532，触发器中心 611）
// 标题: 高级参数 fs14 fw600 lh22 rgb(8,8,8)（gold: 424,545）
// 表单行: y591 h48（gold: form y575 + pt16）
//   标签列 w115: 创意活跃度 fs14 fw500 lh14 + info 14（gold: 424,596）；参数签 temperature fs12 fw400 rgb(102,102,102)
//     bg rgba(0,0,0,0.06) r3 h20 pad 0 7（gold: 签 x424 y616 w93，内层文本 x431 w79）
//   滑块列 w200 ml-auto（gold: x598 y591）:
//     轨 x+8 y+18 w136 h4 bg rgba(0,0,0,0.03) r3；填充 w68 rgb(170,170,170)（采集时 50%）
//     刻度点 8x8 白 r50%（x-4/64/132 y-2）；当前钮 11x11（x62 y-4）
//     减 x1 y30 14px / 加 x137 y30 14px；值框 right y+11 w40 h27 r3（输入 38x25 r5）
import { Minus, Plus, Info } from 'lucide-react'
import styles from './index.module.scss'

export default function AdvancedParams() {
  return (
    <div className={styles.panel} onMouseDown={e => e.stopPropagation()}>
      <div className={styles.title}>高级参数</div>
      <div className={styles.form}>
        <div className={styles.row}>
          <div className={styles.labelCol}>
            <div className={styles.labelRow}>
              <span className={styles.label}>创意活跃度</span>
              <Info size={14} className={styles.info} />
            </div>
            <small className={styles.tagSmall}>
              <span className={styles.tag}><span className={styles.tagIn}>temperature</span></span>
            </small>
          </div>
          <div className={styles.sliderCol}>
            <div className={styles.track}>
              <div className={styles.fill} />
              <span className={styles.dot} style={{ left: -4 }} />
              <span className={styles.dot} style={{ left: 64 }} />
              <span className={styles.dot} style={{ left: 132 }} />
              <span className={styles.knob} />
            </div>
            <span className={styles.minus}><Minus size={14} /></span>
            <span className={styles.plus}><Plus size={14} /></span>
            <div className={styles.value}><input defaultValue="0.5" readOnly /></div>
          </div>
        </div>
      </div>
    </div>
  )
}
