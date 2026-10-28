import { useEffect } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import RequireRole from './components/RequireRole'
import { trackView } from './lib/analytics'
import AdminAudit from './pages/admin/AdminAudit'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminGrounds from './pages/admin/AdminGrounds'
import AdminLayout from './pages/admin/AdminLayout'
import AdminTeams from './pages/admin/AdminTeams'
import AdminTournamentManage from './pages/admin/AdminTournamentManage'
import AdminTournaments from './pages/admin/AdminTournaments'
import AdminUsers from './pages/admin/AdminUsers'
import { Login, Register } from './pages/Auth'
import Home from './pages/Home'
import MatchDetail from './pages/MatchDetail'
import Matches from './pages/Matches'
import PlayerDetail from './pages/PlayerDetail'
import Players from './pages/Players'
import ScorerHome from './pages/scorer/ScorerHome'
import ScorerPanel from './pages/scorer/ScorerPanel'
import { Profile, SettingsPage } from './pages/Settings'
import Stats from './pages/Stats'
import TeamDetail from './pages/TeamDetail'
import Teams from './pages/Teams'
import TournamentDetail from './pages/TournamentDetail'
import Tournaments from './pages/Tournaments'

const ADMIN = ['super_admin', 'tournament_admin']
const SCORING = ['super_admin', 'tournament_admin', 'scorer']

function PageViews() {
  const { pathname } = useLocation()
  useEffect(() => {
    // Match pages report their own view (with the match id).
    if (!/^\/matches\/\d+/.test(pathname)) trackView(pathname)
  }, [pathname])
  return null
}

export default function App() {
  return (
    <>
      <PageViews />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="matches" element={<Matches />} />
          <Route path="matches/:id" element={<MatchDetail />} />
          <Route path="tournaments" element={<Tournaments />} />
          <Route path="tournaments/:id" element={<TournamentDetail />} />
          <Route path="teams" element={<Teams />} />
          <Route path="teams/:id" element={<TeamDetail />} />
          <Route path="players" element={<Players />} />
          <Route path="players/:id" element={<PlayerDetail />} />
          <Route path="stats" element={<Stats />} />
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Register />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="profile" element={<RequireRole><Profile /></RequireRole>} />
          <Route path="scorer" element={<RequireRole roles={SCORING}><ScorerHome /></RequireRole>} />
          <Route path="scorer/matches/:id" element={<RequireRole roles={SCORING}><ScorerPanel /></RequireRole>} />
          <Route path="admin" element={<RequireRole roles={ADMIN}><AdminLayout /></RequireRole>}>
            <Route index element={<AdminDashboard />} />
            <Route path="tournaments" element={<AdminTournaments />} />
            <Route path="tournaments/:id" element={<AdminTournamentManage />} />
            <Route path="teams" element={<AdminTeams />} />
            <Route path="grounds" element={<AdminGrounds />} />
            <Route path="users" element={<RequireRole roles={['super_admin']}><AdminUsers /></RequireRole>} />
            <Route path="audit" element={<RequireRole roles={['super_admin']}><AdminAudit /></RequireRole>} />
          </Route>
          <Route path="*" element={<div className="py-20 text-center"><h1 className="text-3xl font-bold">Page not found</h1><Link to="/" className="mt-4 inline-block text-pitch-700 underline">Go home</Link></div>} />
        </Route>
      </Routes>
    </>
  )
}
