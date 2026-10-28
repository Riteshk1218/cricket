import { Calendar, MapPin, Trophy } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { list } from '../api/client'
import Leaderboards from '../components/Leaderboards'
import MatchCard from '../components/MatchCard'
import PointsTable from '../components/PointsTable'
import { Empty, ErrorBox, Spinner, Tabs, TeamBadge } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'
import { fmtDate } from '../lib/format'
import { useApi } from '../lib/useApi'

export default function TournamentDetail() {
  const { id } = useParams()
  const { t } = useSettings()
  const { isAdmin } = useAuth()
  const [tab, setTab] = useState('fixtures')
  const tour = useApi(`/tournaments/${id}/`)
  const matches = useApi('/matches/', { params: { tournament: id, page_size: 500, ordering: 'scheduled_at' } })
  const table = useApi(tab === 'points' ? `/tournaments/${id}/points_table/` : null)
  const regs = useApi(tab === 'teams' ? `/tournaments/${id}/registrations/` : null)

  if (tour.loading) return <Spinner />
  if (tour.error) return <ErrorBox>{tour.error}</ErrorBox>
  const tr = tour.data
  const all = list(matches.data)
  return (
    <div>
      <div className="mb-6 overflow-hidden rounded-3xl bg-gradient-to-br from-amber-600 via-orange-700 to-slate-900 p-6 text-white">
        <div className="flex flex-wrap items-center gap-4">
          <TeamBadge team={{ name: tr.name, short_name: tr.short_name || tr.name.slice(0, 3), logo: tr.logo, primary_color: '#78350f' }} size="lg" />
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-black sm:text-3xl">{tr.name}</h1>
            <p className="mt-1 flex flex-wrap gap-x-4 text-sm text-white/80">
              <span className="flex items-center gap-1"><MapPin className="h-4 w-4" /> {tr.location}</span>
              <span className="flex items-center gap-1"><Calendar className="h-4 w-4" /> {fmtDate(tr.start_date)} – {fmtDate(tr.end_date)}</span>
              <span>{tr.match_format} · {tr.rules.overs_per_innings} overs · {tr.ball_type} ball · {tr.rules.players_per_side}-a-side</span>
            </p>
          </div>
          {isAdmin && <Link to={`/admin/tournaments/${tr.id}`} className="btn bg-white/15 text-white hover:bg-white/25">Manage</Link>}
        </div>
        {tr.winner_name && (
          <div className="mt-4 flex items-center gap-2 rounded-xl bg-white/10 p-3 font-semibold">
            <Trophy className="h-5 w-5 text-gold" /> {t('winner')}: {tr.winner_name}{tr.runner_up_name && <span className="font-normal text-white/70"> · {t('runnerUp')}: {tr.runner_up_name}</span>}
          </div>
        )}
      </div>
      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { value: 'fixtures', label: t('fixtures') }, { value: 'points', label: t('pointsTable') },
          { value: 'stats', label: t('leaderboards') }, { value: 'teams', label: t('teams') }, { value: 'rules', label: 'Rules' },
        ]}
      />
      {tab === 'fixtures' && (matches.loading ? <Spinner /> : all.length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{all.map((m) => <MatchCard key={m.id} match={m} />)}</div>
      ) : <Empty>No fixtures yet.</Empty>)}
      {tab === 'points' && (table.loading ? <Spinner /> : <PointsTable rows={table.data || []} />)}
      {tab === 'stats' && <Leaderboards tournament={id} />}
      {tab === 'teams' && (regs.loading ? <Spinner /> : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {(regs.data || []).map((r) => (
            <Link key={r.id} to={`/teams/${r.team}`} className="card flex items-center gap-3 p-4 hover:border-pitch-300">
              <TeamBadge team={r.team_detail} />
              <div>
                <div className="font-semibold">{r.team_detail.name}</div>
                <div className="text-xs text-slate-500">Group {r.group} · {r.players.length} players</div>
              </div>
            </Link>
          ))}
        </div>
      ))}
      {tab === 'rules' && (
        <div className="card p-4">
          <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {[
              ['Overs per innings', tr.rules.overs_per_innings], ['Balls per over', tr.rules.balls_per_over],
              ['Players per side', tr.rules.players_per_side], ['Max overs per bowler', tr.rules.max_overs_per_bowler ?? 'No limit'],
              ['Wide runs', tr.rules.wide_runs], ['No-ball runs', tr.rules.noball_runs],
              ['Free hit after no-ball', tr.rules.free_hit_on_noball ? 'Yes' : 'No'], ['Free hit after wide', tr.rules.free_hit_on_wide ? 'Yes' : 'No'],
              ['Powerplays', (tr.rules.powerplays || []).map((p) => `${p[0]}-${p[1]}`).join(', ') || 'None'],
              ['Super over on tie', tr.rules.super_over_on_tie ? 'Yes' : 'No'], ['Last man stands', tr.rules.last_man_stands ? 'Yes' : 'No'],
              ['Not allowed', (tr.rules.disallowed_dismissals || []).join(', ') || '—'],
              ['Points (W/T/NR/L)', `${tr.points_win}/${tr.points_tie}/${tr.points_no_result}/${tr.points_loss}`],
            ].map(([k, v]) => (
              <div key={k} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800"><dt className="text-xs text-slate-500">{k}</dt><dd className="font-semibold">{String(v)}</dd></div>
            ))}
          </dl>
        </div>
      )}
    </div>
  )
}
