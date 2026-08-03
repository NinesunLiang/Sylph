import { Archive, ChevronDown, FileText, Grid2X2, Link2, List, MessageSquare, Paperclip, PenLine, Plus, Search, Send, Store, WandSparkles } from 'lucide-react'
import { useState } from 'react'
import styles from './index.module.scss'

type Tab = 'generate' | 'list' | 'template'
const tabs: { id: Tab; label: string }[] = [{ id: 'generate', label: '生成PPT' }, { id: 'list', label: 'PPT列表' }, { id: 'template', label: '自定义模板' }]

function GenerateView() {
  return <div className={styles.generateView}>
    <div className={styles.greeting}>Hi，请问您想怎样创作您的 PPT 呢？</div>
    <div className={styles.creator}>
      <div className={styles.creatorModes}><button className={styles.creatorModeActive}><PenLine size={27} /><strong>AI智能创作</strong></button><button><FileText size={27} /><strong>上传文件生成</strong></button><button><MessageSquare size={27} /><strong>粘贴内容生成</strong></button></div>
      <div className={styles.prompt}><span>试试输入：“快速培养</span><div><button><Paperclip size={22} /></button><button className={styles.create}><Send size={16} />立即创作</button></div></div>
      <div className={styles.options}><button>页数 <b>20–30页</b><ChevronDown size={16} /></button><button>演示场景 <b>智能决策</b><ChevronDown size={16} /></button><button>受众 <b>智能决策</b><ChevronDown size={16} /></button><label>智能搜索 <span className={styles.switch} /></label><button>语言 <b>简体中文</b><ChevronDown size={16} /></button></div>
    </div>
  </div>
}

function ListView() {
  return <div className={styles.listView}><h2><Archive size={28} />我的作品</h2><div className={styles.workActions}><button className={styles.primary}><WandSparkles size={18} />智能生成PPT</button><button>文件夹　导入文件生成PPT</button><button>▤　输入大纲生成PPT</button><button><Store size={18} />创建我的模板</button></div><div className={styles.listTools}><span>共0件作品</span><button><List size={16} /></button><div className={styles.sort}><b>创建时间</b><span>修改时间</span><span>文件名称</span></div><button className={styles.viewIcon}><Grid2X2 size={18} /></button><List size={18} /><label><input placeholder="搜索我的作品" /><Search size={18} /></label></div><div className={styles.noWorks}><Archive size={32} /><span>您尚未拥有任何作品呢 <b>创建一个PPT</b></span></div></div>
}

function TemplateView() {
  return <div className={styles.templateView}><button className={styles.createTemplate}><Plus size={20} />创建我的模板</button><h2><Store size={25} />我的自定义模板</h2><div className={styles.noTemplate}><div className={styles.templateIllustration}>▣</div><span>暂无自定义模板，请先创建</span></div></div>
}

export default function AipptPage() {
  const [activeTab, setActiveTab] = useState<Tab>('generate')
  return <main className={styles.page}><section className={styles.canvas}><nav className={styles.tabs} aria-label="AI PPT 功能">{tabs.map(tab => <button key={tab.id} className={activeTab === tab.id ? styles.active : ''} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}</nav>{activeTab === 'generate' ? <GenerateView /> : activeTab === 'list' ? <ListView /> : <TemplateView />}</section></main>
}
