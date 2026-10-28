import { BarChart3, ClipboardList, Home, LayoutDashboard, LogIn, LogOut, Menu, Moon, Settings, Shield, Sun, Trophy, Users, Volume2, VolumeX, X } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'
import { LANGS } from '../i18n/strings'

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 font-black tracking-tight">
      <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-full bg-ball shadow-inner">
        <span className="absolute inset-y-1 left-1/2 w-px -translate-x-1/2 border-l border-dashed border-white/80" />
      </span>
      <span className="text-lg">Cric<span className="text-pitch-600 dark:text-pitch-400">Live</span></span>
    </Link>
  )
}

export default function Layout() {
  const { user, logout, isAdmin, isScorer } = useAuth()
  const { theme, setTheme, lang, setLang, sound, setSound, t } = useSettings()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const links = [
    { to: '/', label: t('home'), icon: Home, end: true },
    { to: '/matches', label: t('matches'), icon: ClipboardList },
    { to: '/tournaments', label: t('tournaments'), icon: Trophy },
    { to: '/teams', label: t('teams'), icon: Shield },
    { to: '/players', label: t('players'), icon: Users },
    { to: '/stats', label: t('stats'), icon: BarChart3 },
  ]
  if (isScorer) links.push({ to: '/scorer', label: t('scorer'), icon: ClipboardList })
  if (isAdmin) links.push({ to: '/admin', label: t('admin'), icon: LayoutDashboard })

  const navClass = ({ isActive }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition ${
      isActive ? 'bg-pitch-50 text-pitch-700 dark:bg-pitch-900/50 dark:text-pitch-300' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
    }`

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:p-2">Skip to content</a>
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/85 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
          <Logo />
          <nav className="ml-4 hidden flex-1 items-center gap-1 lg:flex" aria-label="Main">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} className={navClass}>{l.label}</NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <select aria-label={t('language')} value={lang} onChange={(e) => setLang(e.target.value)} className="input hidden w-auto py-1.5 sm:block">
              {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
            <button className="btn-ghost p-2" onClick={() => setSound(!sound)} aria-label={sound ? t('mute') : t('unmute')} title={sound ? t('mute') : t('unmute')}>
              {sound ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
            </button>
            <button className="btn-ghost p-2" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={t('theme')}>
              {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            {user ? (
              <>
                <Link to="/profile" className="btn-ghost hidden px-2 sm:inline-flex">{user.display_name || user.username}</Link>
                <button className="btn-ghost hidden p-2 sm:inline-flex" onClick={async () => { await logout(); navigate('/') }} aria-label={t('logout')} title={t('logout')}>
                  <LogOut className="h-5 w-5" />
                </button>
              </>
            ) : (
              <Link to="/login" className="btn-primary hidden py-1.5 sm:inline-flex"><LogIn className="h-4 w-4" /> {t('login')}</Link>
            )}
            <button className="btn-ghost p-2 lg:hidden" onClick={() => setOpen(!open)} aria-label="Menu" aria-expanded={open}>
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
        {open && (
          <nav className="border-t border-slate-200 px-4 py-3 lg:hidden dark:border-slate-800" aria-label="Mobile">
            <div className="grid grid-cols-2 gap-1">
              {links.map((l) => (
                <NavLink key={l.to} to={l.to} end={l.end} className={navClass} onClick={() => setOpen(false)}>
                  <l.icon className="h-4 w-4" /> {l.label}
                </NavLink>
              ))}
              <NavLink to="/settings" className={navClass} onClick={() => setOpen(false)}><Settings className="h-4 w-4" /> {t('settings')}</NavLink>
              {user ? (
                <button className="flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-600 dark:text-slate-300" onClick={async () => { await logout(); setOpen(false); navigate('/') }}>
                  <LogOut className="h-4 w-4" /> {t('logout')}
                </button>
              ) : (
                <NavLink to="/login" className={navClass} onClick={() => setOpen(false)}><LogIn className="h-4 w-4" /> {t('login')}</NavLink>
              )}
            </div>
            <select aria-label={t('language')} value={lang} onChange={(e) => setLang(e.target.value)} className="input mt-3">
              {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </nav>
        )}
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-500 dark:border-slate-800">
        CricLive · Local cricket scoring · <Link to="/settings" className="underline">{t('settings')}</Link>
      </footer>
    </div>
  )
}
