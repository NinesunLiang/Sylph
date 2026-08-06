import { ArrowLeft, BotMessageSquare, ChevronDown, ChevronRight, Share2 } from 'lucide-react'
import styles from './index.module.scss'

const steps = [
  '阐述你对问题的完整理解',
  '阐述这个问题背后涉及的知识，可以出自学科、书籍、训练体系或实践经验。',
  '引用具体的专业机构、训练体系、知名教练的思路来提供多角度的回答',
]
const requirements = [
  '如果你觉得提问者希望得到的是具体行动建议，请先全方面分析情况，再给建议。',
  '如果用户问的不是健身相关的问题，直接回复“我只是个健身教练，不想回答这个问题”',
  '回答风格要带专业、严谨，需要罗列信息时用表格呈现，信息尽可能全面，多用数字来量化',
  '请使用提问者所用的语言来回答',
]
const related = [
  ['人生教练', '擅长引导思考，帮助探索人生意义的专家教练', '脑'],
  ['Joi', '私人旅行助手，擅长规划行程与推荐住宿活动', '地'],
  ['智慧导师', '一个绝对客观，专注事实，不在乎用户，但是衷心爱着用户的智者', '智'],
  ['健身领域大神', '追寻希腊古典美', '健'],
  ['健身AI教练', '专注于个性化计划、肌肉目标、姿势指导、进度跟踪、激励和虚拟现实训练的AI锻炼助手', '健'],
]

export default function AssistantDetailPage() {
  return <main className={styles.page}>
    <div className={styles.topline}><a href="/discover"><ArrowLeft size={16} />返回发现</a></div>
    <div className={styles.heading}>
      <div className={styles.identity}><img src="/assets/card_basketball.webp" alt="" /><div><h1>健身专家</h1><div className={styles.meta}><span>助手</span><span>生活</span></div></div></div>
      <div className={styles.breadcrumb}><span>助手</span><ChevronRight size={14} /><span>生活</span></div>
    </div>
    <p className={styles.description}>知识渊博的健身专家</p>
    <div className={styles.keywords}><span>健身</span><span>咨询</span><span>生活问题</span><span>建议</span></div>
    <div className={styles.content}>
      <article className={styles.detail}>
        <section className={styles.settings}>
          <header><BotMessageSquare size={20} /><h2>助手设定</h2></header>
          <div className={styles.settingsBody}>
            <p>你是一个精通训练学、生物力学、生理学、营养学知识的人体运动科学专家，善于全面地解决用户的健身问题。你需要基于提问，进行完整地分析，要考虑到各方面的影响，不能直接下结论。</p>
            <section><h2>回答的步骤</h2><ol>{steps.map(step => <li key={step}>{step}</li>)}</ol></section>
            <section><h2>回答的要求：</h2><ul>{requirements.map(item => <li key={item}>{item}</li>)}</ul></section>
          </div>
        </section>
      </article>
      <aside className={styles.aside}>
        <div className={styles.actions}><button className={styles.start}>添加助手并会话</button><button className={styles.dropdown}><ChevronDown size={18} /></button><button className={styles.share}><Share2 size={18} /></button></div>
        <div className={styles.relatedHeader}><h2>相关推荐</h2><button>更多 <ChevronRight size={14} /></button></div>
        <div className={styles.related}>{related.map(([title, text, avatar]) => <a href="#" key={title} className={styles.relatedCard}><span className={styles.relatedAvatar}>{avatar}</span><div><h3>{title}</h3><p>{text}</p></div></a>)}</div>
      </aside>
    </div>
  </main>
}
