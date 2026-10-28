import { Shield } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { list } from '../api/client'
import { Empty, ErrorBox, PageHeader, Spinner, TeamBadge } from '../components/ui'
import { useSettings } from '../context/SettingsContext'
import { useApi } from '../lib/useApi'

export default function Teams() {
  const { t } = useSettings()
  const [q, setQ] = useState('')
  const { data, loading, error } = useApi('/teams/', { params: { page_size: 200, search: q || undefined } })
  return (
    <div>
      <PageHeader title={t('teams')} icon={Shield} actions={<input className="input w-56" placeholder={t('search')} value={q} onChange={(e) => setQ(e.target.value)} aria-label={t('search')} />} />
      <ErrorBox>{error}</ErrorBox>
      {loading ? <Spinner /> : list(data).length ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {list(data).map((team) => (
            <Link key={team.id} to={`/teams/${team.id}`} className="card flex items-center gap-3 p-4 transition hover:-translate-y-0.5 hover:shadow-md">
              <TeamBadge team={team} size="lg" />
              <div className="min-w-0">
                <div className="truncate font-bold">{team.name}</div>
                <div className="text-xs text-slate-500">{team.city} · {team.player_count} players</div>
              </div>
            </Link>
          ))}
        </div>
      ) : <Empty icon={Shield}>No teams found.</Empty>}
    </div>
  )
}
