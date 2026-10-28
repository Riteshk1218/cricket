import { MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'
import { fmtDateTime, STAGE_LABEL } from '../lib/format'
import { StatusChip, TeamBadge } from './ui'

function ScoreLine({ match, team }) {
  const scores = match.scores?.[String(team.id)] || []
  const batting = match.batting_team_id === team.id
  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex min-w-0 items-center gap-2">
        <TeamBadge team={team} size="sm" />
        <span className={`truncate font-semibold ${batting ? 'text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-300'}`}>{team.name}</span>
        {batting && <span className="h-2 w-2 shrink-0 rounded-full bg-pitch-500" aria-label="batting" />}
      </div>
      <div className="shrink-0 text-right tabular-nums">
        {scores.map((s) => (
          <span key={s.innings} className={`ml-2 ${s.is_super_over ? 'text-xs text-amber-600' : 'font-bold'}`}>
            {s.is_super_over && 'SO '}{s.runs}/{s.wickets}
            <span className="ml-1 text-xs font-normal text-slate-500">({s.overs})</span>
          </span>
        ))}
      </div>
    </div>
  )
}

export default function MatchCard({ match }) {
  return (
    <Link
      to={`/matches/${match.id}`}
      className="card group block p-4 transition hover:-translate-y-0.5 hover:border-pitch-300 hover:shadow-md dark:hover:border-pitch-700"
    >
      <div className="mb-3 flex items-center justify-between gap-2 text-xs text-slate-500">
        <span className="truncate font-medium">
          {match.tournament?.name} · {STAGE_LABEL[match.stage] || match.stage} #{match.match_number}
        </span>
        <StatusChip status={match.status} />
      </div>
      <div className="space-y-2">
        <ScoreLine match={match} team={match.team_a} />
        <ScoreLine match={match} team={match.team_b} />
      </div>
      <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-100 pt-2 text-xs dark:border-slate-800">
        {match.result ? (
          <span className="font-semibold text-pitch-700 dark:text-pitch-400">{match.result}</span>
        ) : match.target ? (
          <span className="font-semibold text-amber-700 dark:text-amber-400">Target {match.target}</span>
        ) : (
          <span className="text-slate-500">{fmtDateTime(match.scheduled_at)}</span>
        )}
        {match.ground && (
          <span className="flex items-center gap-1 truncate text-slate-500"><MapPin className="h-3 w-3" /> {match.ground}</span>
        )}
      </div>
    </Link>
  )
}
