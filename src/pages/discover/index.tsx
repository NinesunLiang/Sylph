import { BookOpen, BriefcaseBusiness, Compass, GraduationCap, Grid2X2, Home, Image, Puzzle, Search, Smile, Sparkles, Swords, Wrench } from 'lucide-react'
import { useState } from 'react'
import styles from './index.module.scss'

type Card = { title: string; description: string; category: string; image?: string; href?: string }
type Tab = 'home' | 'assistants' | 'plugins'
type Category = '全部' | '学术' | '职业' | '文案' | '设计' | '教育' | '情感' | '娱乐' | '游戏' | '通用' | '生活' | '商业' | '办公' | '编程' | '翻译'

const assistants: Card[] = [
  { title: '健身专家', description: '知识渊博的健身专家', category: '生活', image: '/assets/card_basketball.webp', href: '/discover/assistant/assistants-health-better' },
  { title: 'Mistaker', description: '通过清晰的解释和语法、发音示例来消除错误。', category: '教育', image: '/assets/card_book.webp' },
  { title: '代码优化/错误修改', description: '精通多种编程语言，优化代码结构，修复错误并提供优雅的解决方案。', category: '编程', image: '/assets/card_robot.webp' },
  { title: '伦理安全分析师', description: '专注于识别和减轻网络和移动平台中的安全漏洞。', category: '编程', image: '/assets/card_detective.webp' },
  { title: '最小化的工件架构师', description: '擅长评估和创建可重用的内容工件', category: '编程', image: '/assets/card_robot.webp' },
  { title: '原则性问题解决者', description: '擅长原则性问题解决和分类。思维链代理', category: '通用', image: '/assets/card_book.webp' },
  { title: 'JSON 提示生成器', description: '专门生成用于任务执行的 JSON 格式提示。', category: '编程', image: '/assets/card_robot.webp' },
  { title: 'C++/Qt', description: '擅长教授 C++/Qt 编程实践', category: '编程', image: '/assets/card_robot.webp' },
  { title: '怼人大师', description: '专业辩论专家，善于快速反驳与幽默应对。', category: '情感' },
  { title: '这很合理', description: '神经病眼中的世界,"这很合理呀"', category: '设计' },
  { title: '美好的短篇星期日信息', description: '星期日信息伴侣，创作鼓舞人心的、基于信仰的信息，以增强社区联系和传播积极性。', category: '情感' },
  { title: 'Flux 提示生成器', description: 'Flux 提示生成助手：专注于为 Flux 模型生成高质量图像输出而创作详细、创', category: '设计' },
]
const directoryCards: Card[] = [
  { title: '这很合理', description: '神经病眼中的世界,"这很合理呀"', category: '设计' },
  { title: 'Flux 提示生成器', description: 'Flux 提示生成助手：专注于为 Flux 模型生成高质量图像输出而创作详细、创意提示的专家。', category: '设计' },
  { title: 'Runway Gen-3 提示生成器', description: '在生成结构化的 Runway Gen-3 提示方面的专家，用于 AI 生成的视频。', category: '设计' },
  { title: '稳定专辑封面提示生成器', description: '专业的平面设计师，专注于为旋律科技音乐专辑创建视觉概念和设计。', category: '设计' },
  { title: 'PPT优化专家v1.0', description: '专业 PPT 汇报材料优化专家', category: '职业' },
  { title: 'UI/UX 设计师', description: '世界级的 UI/UX 设计师，拥有丰富的经验', category: '设计' },
  { title: 'NovelAI 绘图助手', description: '我可以将您描述的场景转化为 NovelAI 的提示', category: '设计' },
  { title: '提示大师 AI', description: '将您的创意概念转化为详细、富有上下文的提示，以激发令人惊叹和逼真的视觉效果', category: '设计' },
]
const plugins: Card[] = [
  { title: 'Arxiv学术', description: '提供Arxiv学术论文搜索', category: '科学教育' },
  { title: 'PubMed学术', description: '提供生物医学和生命科学领域学术论文搜索', category: '科学教育' },
  { title: '思维导图', description: '思维导图生成助手', category: '实用工具' },
]
const categories: { label: Category; icon: typeof Grid2X2 }[] = [
  { label: '全部', icon: Grid2X2 }, { label: '学术', icon: BookOpen }, { label: '职业', icon: BriefcaseBusiness },
  { label: '文案', icon: Wrench }, { label: '设计', icon: Image }, { label: '教育', icon: GraduationCap },
  { label: '情感', icon: Smile }, { label: '娱乐', icon: Swords }, { label: '游戏', icon: Sparkles }, { label: '通用', icon: Compass },
  { label: '生活', icon: Smile }, { label: '商业', icon: BriefcaseBusiness }, { label: '办公', icon: Wrench }, { label: '编程', icon: Puzzle }, { label: '翻译', icon: Sparkles },
]
const categoryPaths: Partial<Record<Category, string>> = { 学术: 'academic', 职业: 'career', 文案: 'copywriting', 设计: 'design', 教育: 'education', 情感: 'emotions', 娱乐: 'entertainment', 游戏: 'games', 通用: 'general' }

function CardGrid({ cards, directory = false }: { cards: Card[]; directory?: boolean }) {
  return <div className={`${styles.grid} ${directory ? styles.directoryGrid : ''}`}>{cards.map(card => <article className={`${styles.card} ${card.image ? '' : styles.cardCompact}`} key={card.title}>
    {card.image && <div className={styles.cardTop}><span className={styles.cardIcon}><img src={card.image} alt="" /></span></div>}
    <div className={styles.cardBody}><a href={card.href ?? '#'}><h3>{card.title}</h3><p>{card.description}</p></a><span className={styles.tag}>{card.category}</span></div>
  </article>)}</div>
}
function AssistantDirectory({ category, onCategory }: { category: Category; onCategory: (category: Category) => void }) {
  const filtered = category === '全部' ? directoryCards : directoryCards.filter(card => card.category === category)
  return <div className={styles.directory}><aside className={styles.categoryNav} aria-label="助手分类"><ul className={styles.categoryList}>{categories.map(({ label, icon: Icon }) => <li key={label}><a href="#" className={`${styles.categoryItem} ${category === label ? styles.categoryActive : ''}`} onClick={event => { event.preventDefault(); onCategory(label) }}><Icon size={18} /><span>{label}</span></a></li>)}</ul></aside><section className={styles.directoryMain}><header className={styles.directoryHeader}><h2>{category === '全部' ? '最近更新' : category}</h2></header><CardGrid cards={filtered} directory /></section></div>
}
function PluginDirectory() {
  return <section className={styles.pluginDirectory}><header className={styles.directoryHeader}><h2>插件</h2></header><CardGrid cards={plugins} directory /></section>
}
export default function DiscoverPage() {
  const [tab, setTab] = useState<Tab>('home'); const [category, setCategory] = useState<Category>('全部')
  const selectTab = (next: Tab) => { setTab(next); if (next !== 'assistants') setCategory('全部'); window.history.pushState({}, '', next === 'assistants' ? '/discover/assistants' : next === 'plugins' ? '/discover/plugins' : '/discover') }
  const selectCategory = (next: Category) => { setCategory(next); window.history.pushState({}, '', categoryPaths[next] ? `/discover/assistants/${categoryPaths[next]}` : '/discover/assistants') }
  return <main className={styles.page}><header className={styles.header}><h1 className={styles.brand}>XSimple</h1><span className={styles.title}>发现</span><label className={styles.search}><Search size={16} /><input placeholder="搜索名称介绍或关键词..." aria-label="搜索" /><span className={styles.searchHint}>⌘ K</span></label></header><nav className={styles.tabs} aria-label="发现分类"><button className={`${styles.tab} ${tab === 'home' ? styles.tabActive : ''}`} onClick={() => selectTab('home')}><Home size={24} />首页</button><button className={`${styles.tab} ${tab === 'assistants' ? styles.tabActive : ''}`} onClick={() => selectTab('assistants')}><Sparkles size={24} />助手</button><button className={`${styles.tab} ${tab === 'plugins' ? styles.tabActive : ''}`} onClick={() => selectTab('plugins')}><Puzzle size={24} />插件</button></nav>{tab === 'assistants' ? <AssistantDirectory category={category} onCategory={selectCategory} /> : tab === 'plugins' ? <PluginDirectory /> : <div className={styles.content}><section className={styles.section}><header className={styles.sectionHeader}><h2>推荐助手</h2><button className={styles.more}>发现更多</button></header><CardGrid cards={assistants} /></section><section className={styles.section}><header className={styles.sectionHeader}><h2>推荐插件</h2><button className={styles.more}>发现更多</button></header><CardGrid cards={plugins} /></section></div>}</main>
}
