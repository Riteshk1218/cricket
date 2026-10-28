import { Link } from 'react-router-dom'
import { useSettings } from '../context/SettingsContext'
import { useApi } from '../lib/useApi'
import { ErrorBox, Spinner } from './ui'

const BOARDS = [
  ['most_runs', 'mostRuns'], ['most_wickets', 'mostWickets'], ['highest_strike_rate', 'highestSR'],
  ['best_economy', 'bestEconomy'], ['most_sixes', 'mostSixes'], ['most_fours', 'mostFours'],
  ['highest_scores', 'highestScores'], ['most_catches', 'mostCatches'],
]

export default function Leaderboards({ tournament }) {
  const { t } = useSettings()
  const { data, loading, error } = useApi('/stats/leaderboards/', { params: tournament ? { tournament } : {} })
  if (loading) return <Spinner />
  if (error) return <ErrorBox>{error}</ErrorBox>
  return (
    <div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {BOARDS.map(([key, label]) => (
          <div key={key} className="card p-4">
            <h3 className="mb-2 font-bold">{t(label)}</h3>
            {data[key].length ? (
              <ol className="space-y-1.5 text-sm">
                {data[key].map((r, i) => (
                  <li key={r.player_id} className="flex items-center gap-2">
                    <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${i === 0 ? 'bg-gold text-slate-900' : 'bg-slate-100 dark:bg-slate-800'}`}>{i + 1}</span>
                    <Link to={`/players/${r.player_id}`} className="min-w-0 flex-1 truncate hover:underline">{r.name} <span className="text-xs text-slate-500">{r.team}</span></Link>
                    <span className="font-bold tabular-nums">{r.value}</span>
                  </li>
                ))}
              </ol>
            ) : <p className="text-sm text-slate-500">—</p>}
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Strike rate needs at least {data.criteria.min_balls_strike_rate} balls faced; economy needs {data.criteria.min_balls_economy} balls bowled. Super overs are excluded.
      </p>
    </div>
  )
}
