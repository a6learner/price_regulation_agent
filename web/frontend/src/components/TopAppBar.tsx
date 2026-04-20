import { Link, useLocation } from 'react-router-dom'
import type { Role } from '../types'
import { ROLE_LABELS } from '../types'

interface Props {
  role?: Role
}

export default function TopAppBar({ role }: Props) {
  const location = useLocation()

  return (
    <header className="sticky top-0 z-40 flex items-center justify-between w-full px-6 py-3 bg-surface-container-lowest shadow-ambient">
      <div className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <span className="material-symbols-outlined icon-fill text-primary text-2xl">account_balance</span>
          <span className="font-headline font-bold text-xl text-primary tracking-tight">Jurisconsult AI</span>
        </Link>
        {role && (
          <span className="bg-surface-container-high text-on-surface-variant px-2 py-1 rounded text-xs font-medium">
            {ROLE_LABELS[role]}
          </span>
        )}
      </div>

      <nav className="flex items-center gap-1">
        <Link
          to={`/chat${role ? `?role=${role}` : ''}`}
          className={`px-3 py-2 rounded-lg text-sm font-medium no-underline transition-colors ${
            location.pathname === '/chat'
              ? 'bg-primary-fixed text-primary'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined text-[18px] align-middle mr-1">chat</span>
          对话分析
        </Link>
        <Link
          to="/knowledge"
          className={`px-3 py-2 rounded-lg text-sm font-medium no-underline transition-colors ${
            location.pathname === '/knowledge'
              ? 'bg-primary-fixed text-primary'
              : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
        >
          <span className="material-symbols-outlined text-[18px] align-middle mr-1">library_books</span>
          知识库
        </Link>
      </nav>
    </header>
  )
}
