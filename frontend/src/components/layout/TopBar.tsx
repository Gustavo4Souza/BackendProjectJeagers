import { AlertBadge } from './AlertBadge'
import { useAuth } from '../../context/AuthContext'

interface TopBarProps {
  alertCount: number
}

const NAV_LINKS = ['Painel', 'Histórico', 'Alertas', 'Config'] as const

export function TopBar({ alertCount }: TopBarProps) {
  const { user, logout } = useAuth()
  const userName = user?.sub ?? 'Admin'

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-0 flex items-center justify-between sticky top-0 z-10 h-14">
      {/* Logo */}
      <span className="text-lg font-bold text-gray-900 tracking-tight select-none flex-shrink-0">
        EH <span style={{ color: '#1D9E75' }}>Brewing</span>
      </span>

      {/* Nav links — decorativas na V1 exceto Painel */}
      <nav className="hidden sm:flex items-center gap-1">
        {NAV_LINKS.map((link) => (
          <span
            key={link}
            className={`text-sm px-3 py-1.5 rounded-md font-medium cursor-default select-none ${
              link === 'Painel' ? 'text-gray-900 bg-gray-100' : 'text-gray-400'
            }`}
          >
            {link}
          </span>
        ))}
      </nav>

      {/* Right side: bell + user + logout */}
      <div className="flex items-center gap-4">
        {/* Bell icon with badge */}
        <div className="relative">
          <svg
            className={`w-5 h-5 ${alertCount > 0 ? 'text-red-500' : 'text-gray-400'}`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-2.83-2h5.66A3 3 0 0110 18z" />
          </svg>
          <AlertBadge count={alertCount} />
        </div>

        {/* User avatar + name */}
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
            style={{ backgroundColor: '#1D9E75' }}
          >
            {userName.charAt(0).toUpperCase()}
          </div>
          <span className="hidden sm:block text-sm text-gray-600 font-medium">{userName}</span>
        </div>

        {/* Logout button */}
        <button
          onClick={logout}
          className="hidden sm:flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          title="Sair"
          aria-label="Sair"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Sair
        </button>
      </div>
    </header>
  )
}
