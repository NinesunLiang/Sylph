import { Link, NavLink } from 'react-router-dom'
import styles from './Topbar.module.scss'

export function Topbar() {
  return (
    <header className={styles.topbar}>
      <Link to="/">simpleX</Link>
    </header>
  )
}
