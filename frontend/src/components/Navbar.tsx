// components/Navbar.tsx
import Link from 'next/link'
import { datasetConfig } from '@/lib/config'

export default function Navbar() {
  const { title, subtitle } = datasetConfig
  return (
    <nav className="navbar bg-primary text-white shadow-lg">
      <div className="container">
        <div className="navbar-brand">
          <span className="navbar-brand-text">{title}</span>
        </div>
        {subtitle && (
          <div className="navbar-nav">
            <Link href="#" className="nav-link">
              {subtitle}
            </Link>
          </div>
        )}
      </div>
    </nav>
  )
}