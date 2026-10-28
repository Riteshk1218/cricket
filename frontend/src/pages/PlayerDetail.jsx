import { Link, useParams } from 'react-router-dom'
import { list } from '../api/client'
import { ErrorBox, Spinner, Stat } from '../components/ui'
import { useSettings } from '../context/SettingsContext'
import { useApi } from '../lib/useApi'
import { PlayerAvatar } from './Players'

const v = (x) => (x === null || x === undefined ? '—' : x)

export default function PlayerDetail() {
  const { id } = useParams()
  const { t } = useSettings()
  const { data, loading, error } = useApi(`/stats/players/${id}/`)
  const tours = useApi('/tournaments/', { params: { page_size: 100 } })
  if (loading) return <Spinner />
  if (error) return <ErrorBox>{error}</ErrorBox>
  const { player, stats, recent } = data
  const bat = stats.batting
  const bowl = stats.bowling
  const fld = stats.fielding
  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <PlayerAvatar player={player} size="h-20 w-20 text-2xl" />
        <div>
          <h1 className="text-3xl font-black">{player.full_name}</h1>
          <p className="text-sm capitalize text-slate-500">
            {player.role.replace('_', ' ')} · {player.batting_style}-hand bat{player.bowling_style && ` · ${player.bowling_style}`}
            {player.team && <> · <Link className="font-semibold text-pitch-700 hover:underline dark:text-pitch-400" to={`/teams/${player.team}`}>{player.team_name}</Link></>}
          </p>
        </div>
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label={t('matches')} value={stats.matches} /><Stat label="Runs" value={bat.runs} tone="sky" />
        <Stat label={t('wickets')} value={bowl.wickets} tone="red" /><Stat label={t('catches')} value={fld.catches} tone="amber" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card overflow-x-auto p-4">
          <h2 className="mb-3 font-bold">{t('batting')}</h2>
          <table className="table-basic">
            <thead><tr>{['M', 'Inns', 'NO', 'Runs', 'Balls', 'HS', 'Avg', 'SR', '50s', '100s', '4s', '6s'].map((h) => <th key={h} className="text-right">{h}</th>)}</tr></thead>
            <tbody><tr>{[stats.matches, bat.innings, bat.not_outs, bat.runs, bat.balls, bat.highest, v(bat.average), bat.strike_rate, bat.fifties, bat.hundreds, bat.fours, bat.sixes].map((x, i) => <td key={i} className="text-right tabular-nums">{x}</td>)}</tr></tbody>
          </table>
        </div>
        <div className="card overflow-x-auto p-4">
          <h2 className="mb-3 font-bold">{t('bowling')}</h2>
          <table className="table-basic">
            <thead><tr>{['Inns', 'Overs', 'Mdns', 'Runs', 'Wkts', 'Best', 'Avg', 'Econ', 'SR'].map((h) => <th key={h} className="text-right">{h}</th>)}</tr></thead>
            <tbody><tr>{[bowl.innings, bowl.overs, bowl.maidens, bowl.runs, bowl.wickets, bowl.best, v(bowl.average), v(bowl.economy), v(bowl.strike_rate)].map((x, i) => <td key={i} className="text-right tabular-nums">{x}</td>)}</tr></tbody>
          </table>
        </div>
        <div className="card p-4">
          <h2 className="mb-3 font-bold">{t('fielding')}</h2>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div><div className="text-2xl font-bold">{fld.catches}</div><div className="text-xs text-slate-500">{t('catches')}</div></div>
            <div><div className="text-2xl font-bold">{fld.run_outs}</div><div className="text-xs text-slate-500">{t('runOuts')}</div></div>
            <div><div className="text-2xl font-bold">{fld.stumpings}</div><div className="text-xs text-slate-500">{t('stumpings')}</div></div>
          </div>
        </div>
        <div className="card p-4">
          <h2 className="mb-3 font-bold">{t('recent')}</h2>
          <ul className="divide-y divide-slate-100 text-sm dark:divide-slate-800">
            {recent.map((r) => (
              <li key={`${r.match_id}-${r.innings}`} className="flex justify-between gap-2 py-2">
                <Link to={`/matches/${r.match_id}`} className="truncate hover:underline">{r.match} <span className="text-xs text-slate-500">{r.date}</span></Link>
                <span className="shrink-0 tabular-nums">{r.balls ? `${r.runs} (${r.balls})` : ''}{r.bowled_balls ? ` · ${r.wickets} wkt` : ''}</span>
              </li>
            ))}
            {!recent.length && <li className="py-2 text-slate-500">No innings yet.</li>}
          </ul>
        </div>
      </div>
      {list(tours.data).length > 0 && <p className="mt-4 text-xs text-slate-500">Career figures across all tournaments. Super overs excluded.</p>}
    </div>
  )
}
