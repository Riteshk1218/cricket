import { Heart } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { list } from '../api/client'
import MatchCard from '../components/MatchCard'
import { ErrorBox, Spinner, Stat, TeamBadge } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'
import { useApi } from '../lib/useApi'

export default function TeamDetail() {
  const { id } = useParams()
  const { t } = useSettings()
  const { user } = useAuth()
  const team = useApi(`/teams/${id}/`)
  const players = useApi(`/teams/${id}/players/`)
  const stats = useApi(`/stats/teams/${id}/`)
  const matches = useApi('/matches/', { params: { team: id, page_size: 12, ordering: '-scheduled_at' } })
  const [fav, setFav] = useState(null)
  useEffect(() => {
    if (user) api.get('/favorites/').then((r) => setFav(r.data.find((f) => f.team === Number(id)) || false)).catch(() => {})
  }, [user, id])
  const toggle = async () => {
    if (fav) {
      await api.delete(`/favorites/${fav.id}/`)
      setFav(false)
    } else setFav((await api.post('/favorites/', { team: Number(id) })).data)
  }
  if (team.loading) return <Spinner />
  if (team.error) return <ErrorBox>{team.error}</ErrorBox>
  const s = stats.data
  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-3xl p-6 text-white" style={{ background: `linear-gradient(135deg, ${team.data.primary_color}, #0f172a)` }}>
        <TeamBadge team={team.data} size="lg" />
        <div className="flex-1">
          <h1 className="text-3xl font-black">{team.data.name}</h1>
          <p className="text-white/80">{team.data.city}</p>
        </div>
        {user && fav !== null && (
          <button className="btn bg-white/15 text-white hover:bg-white/25" onClick={toggle} aria-pressed={!!fav}>
            <Heart className={`h-4 w-4 ${fav ? 'fill-current' : ''}`} /> {fav ? t('following') : t('follow')}
          </button>
        )}
      </div>
      {s && (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat label="Played" value={s.played} /><Stat label="Won" value={s.won} tone="sky" /><Stat label="Lost" value={s.lost} tone="red" />
          <Stat label="Tied / NR" value={`${s.tied} / ${s.no_result}`} tone="amber" />
          <Stat label="Highest total" value={s.highest_total ? `${s.highest_total.runs}/${s.highest_total.wickets}` : '—'} tone="violet" />
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card p-4">
          <h2 className="mb-3 font-bold">{t('players')}</h2>
          {players.loading ? <Spinner /> : (
            <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
              {(players.data || []).map((p) => (
                <li key={p.id} className="flex items-center justify-between py-2">
                  <Link to={`/players/${p.id}`} className="font-semibold hover:underline">{p.jersey_number ? `#${p.jersey_number} ` : ''}{p.full_name}</Link>
                  <span className="text-xs capitalize text-slate-500">{p.role.replace('_', ' ')}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="lg:col-span-2">
          <h2 className="mb-3 font-bold">{t('matches')}</h2>
          <div className="grid gap-4 sm:grid-cols-2">{list(matches.data).map((m) => <MatchCard key={m.id} match={m} />)}</div>
        </div>
      </div>
    </div>
  )
}
