import { LayoutDashboard, MapPin, ScrollText, Shield, Trophy, Users } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function AdminLayout() {
  const { isSuperAdmin } = useAuth()
  const links = [
    { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/admin/tournaments', label: 'Tournaments', icon: Trophy },
    { to: '/admin/teams', label: 'Teams & players', icon: Shield },
    { to: '/admin/grounds', label: 'Grounds', icon: MapPin },
  ]
  if (isSuperAdmin) {
    links.push({ to: '/admin/users', label: 'Users & scorers', icon: Users })
    links.push({ to: '/admin/audit', label: 'Audit log', icon: ScrollText })
  }
  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      <aside className="lg:sticky lg:top-20 lg:self-start">
        <nav className="flex gap-1 overflow-x-auto lg:flex-col" aria-label="Admin">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `flex items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2 text-sm font-semibold ${isActive ? 'bg-pitch-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`
              }
            >
              <l.icon className="h-4 w-4" /> {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  )
}
