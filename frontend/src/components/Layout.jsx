import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Link2, PieChart, Lightbulb,
  ListOrdered, TrendingUp, Globe,
} from 'lucide-react'
import clsx from 'clsx'
import { useLang } from '../LangContext'

export default function Layout() {
  const { t, lang, setLang } = useLang()

  const NAV = [
    { to: '/dashboard',       label: t('nav_dashboard'),    icon: LayoutDashboard },
    { to: '/connect',         label: t('nav_connect'),       icon: Link2 },
    { to: '/expenses',        label: t('nav_expenses'),      icon: PieChart },
    { to: '/recommendations', label: t('nav_advice'),        icon: Lightbulb },
    { to: '/transactions',    label: t('nav_transactions'),  icon: ListOrdered },
  ]

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 bg-slate-900 text-white flex flex-col">
        <div className="px-6 py-5 flex items-center gap-2 border-b border-slate-700">
          <TrendingUp className="text-sky-400" size={22} />
          <span className="font-bold text-lg tracking-tight">myFinance</span>
        </div>

        <nav className="flex-1 py-4 space-y-1 px-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-sky-500 text-white'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-slate-700 space-y-3">
          {/* Language toggle */}
          <button
            onClick={() => setLang(lang === 'en' ? 'he' : 'en')}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition text-sm font-medium"
          >
            <Globe size={16} />
            {lang === 'en' ? 'עברית' : 'English'}
          </button>
          <p className="text-xs text-slate-500 px-1">{t('nav_tagline')}</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
