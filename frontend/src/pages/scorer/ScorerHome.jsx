import { ClipboardList } from 'lucide-react'
import { Link } from 'react-router-dom'
import { list } from '../../api/client'
import { Empty, ErrorBox, PageHeader, Spinner, StatusChip, TeamBadge } from '../../components/ui'
import { fmtDateTime } from '../../lib/format'
import { useApi } from '../../lib/useApi'

export default function ScorerHome() {
  const { data, loading, error, reload } = useApi('/matches/', { params: { assigned: 1, page_size: 200, ordering: 'scheduled_at' } })
  const matches = list(data)
  const groups = [
    ['Live now', matches.filter((m) => ['live', 'innings_break', 'paused', 'toss'].includes(m.status))],
    ['Upcoming', matches.filter((m) => m.status === 'scheduled')],
    ['Finished', matches.filter((m) => ['completed', 'abandoned'].includes(m.status))],
  ]
  return (
    <div>
      <PageHeader title="My scoring matches" subtitle="Matches you are assigned to score" icon={ClipboardList} />
      <ErrorBox onRetry={reload}>{error}</ErrorBox>
      {loading ? <Spinner /> : !matches.length ? (
        <Empty icon={ClipboardList}>No matches are assigned to you yet. Ask a tournament admin to assign you.</Empty>
      ) : (
        groups.map(([title, items]) => items.length > 0 && (
          <section key={title} className="mb-8">
            <h2 className="mb-3 text-lg font-bold">{title}</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {items.map((m) => (
                <Link key={m.id} to={`/scorer/matches/${m.id}`} className="card flex items-center gap-3 p-4 transition hover:border-pitch-400">
                  <TeamBadge team={m.team_a} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-bold">{m.team_a.short_name} vs {m.team_b.short_name}</div>
                    <div className="truncate text-xs text-slate-500">{m.tournament.name} · {m.ground} · {fmtDateTime(m.scheduled_at)}</div>
                    {m.result && <div className="text-xs font-semibold text-pitch-700">{m.result}</div>}
                  </div>
                  <TeamBadge team={m.team_b} />
                  <StatusChip status={m.status} />
                </Link>
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  )
}
