import { Calendar, MapPin, Trophy } from 'lucide-react'
import { Link } from 'react-router-dom'
import { list } from '../api/client'
import { Empty, ErrorBox, PageHeader, Spinner, TeamBadge } from '../components/ui'
import { useSettings } from '../context/SettingsContext'
import { fmtDate } from '../lib/format'
import { useApi } from '../lib/useApi'

export default function Tournaments() {
  const { t } = useSettings()
  const { data, loading, error, reload } = useApi('/tournaments/', { params: { page_size: 100 } })
  return (
    <div>
      <PageHeader title={t('tournaments')} icon={Trophy} />
      <ErrorBox onRetry={reload}>{error}</ErrorBox>
      {loading ? <Spinner /> : list(data).length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {list(data).map((tr) => (
            <Link key={tr.id} to={`/tournaments/${tr.id}`} className="card overflow-hidden transition hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-center gap-3 bg-gradient-to-r from-amber-600 to-orange-700 p-4 text-white">
                <TeamBadge team={{ name: tr.name, short_name: tr.short_name || tr.name.slice(0, 3), logo: tr.logo, primary_color: '#78350f' }} size="lg" />
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-bold">{tr.name}</h2>
                  <p className="text-xs text-white/80">{tr.match_format} · {tr.ball_type} ball · {tr.kind}</p>
                </div>
              </div>
              <div className="space-y-1 p-4 text-sm text-slate-600 dark:text-slate-300">
                <p className="flex items-center gap-2"><MapPin className="h-4 w-4" /> {tr.location || '—'}</p>
                <p className="flex items-center gap-2"><Calendar className="h-4 w-4" /> {fmtDate(tr.start_date)} – {fmtDate(tr.end_date)}</p>
                <p>{tr.team_count} teams · {tr.match_count} matches {tr.live_count > 0 && <span className="chip ml-1 bg-red-600 text-white">{tr.live_count} live</span>}</p>
                {tr.winner_name && <p className="font-semibold text-amber-700 dark:text-amber-400">🏆 {t('winner')}: {tr.winner_name}</p>}
              </div>
            </Link>
          ))}
        </div>
      ) : <Empty icon={Trophy}>No tournaments yet.</Empty>}
    </div>
  )
}
