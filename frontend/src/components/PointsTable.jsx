import { Link } from 'react-router-dom'
import { useSettings } from '../context/SettingsContext'
import { TeamBadge } from './ui'

export default function PointsTable({ rows }) {
  const { t } = useSettings()
  const groups = [...new Set(rows.map((r) => r.group))]
  return (
    <div className="space-y-6">
      {groups.map((g) => (
        <div key={g} className="card overflow-x-auto p-4">
          {groups.length > 1 && <h3 className="mb-2 font-bold">Group {g}</h3>}
          <table className="table-basic">
            <thead>
              <tr>
                <th>#</th><th>Team</th><th className="text-right">{t('played')}</th><th className="text-right">{t('won')}</th>
                <th className="text-right">{t('lost')}</th><th className="text-right">{t('tied')}</th><th className="text-right">{t('noResult')}</th>
                <th className="text-right">{t('nrr')}</th><th className="text-right">{t('points')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.filter((r) => r.group === g).map((r) => (
                <tr key={r.team.id}>
                  <td className="font-bold">{r.position}</td>
                  <td><Link to={`/teams/${r.team.id}`} className="flex items-center gap-2 font-semibold hover:underline"><TeamBadge team={r.team} size="sm" /> {r.team.name}</Link></td>
                  <td className="text-right tabular-nums">{r.played}</td>
                  <td className="text-right tabular-nums">{r.won}</td>
                  <td className="text-right tabular-nums">{r.lost}</td>
                  <td className="text-right tabular-nums">{r.tied}</td>
                  <td className="text-right tabular-nums">{r.no_result}</td>
                  <td className={`text-right tabular-nums ${Number(r.net_run_rate) >= 0 ? 'text-pitch-700 dark:text-pitch-400' : 'text-red-600'}`}>{Number(r.net_run_rate) > 0 ? '+' : ''}{Number(r.net_run_rate).toFixed(3)}</td>
                  <td className="text-right font-black tabular-nums">{r.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <p className="text-xs text-slate-500">NRR = (runs scored ÷ overs faced) − (runs conceded ÷ overs bowled). A side bowled out is charged its full quota of overs.</p>
    </div>
  )
}
