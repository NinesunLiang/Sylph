// UploadMenu — 回形针上传菜单（gold 真值: states/upload-menu.delta.json）
// ul 114x82 白底 r5 pad4 三层阴影，水平居中于按钮，向上打开间隙 4
// li 104x36 r3 pad 7px 12px，icon 16 + 文本 fs14，间距 8
import { Image, FileUp } from 'lucide-react'
import styles from './index.module.scss'

export default function UploadMenu({ onPick }: { onPick: (kind: 'image' | 'file') => void }) {
  return (
    <ul className={styles.menu} onMouseDown={e => e.stopPropagation()}>
      <li className={styles.item} onClick={() => onPick('image')}><Image size={16} /><span>上传图片</span></li>
      <li className={styles.item} onClick={() => onPick('file')}><FileUp size={16} /><span>上传文件</span></li>
    </ul>
  )
}
