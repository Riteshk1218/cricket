import { Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { list } from '../api/client'
import { mediaUrl } from '../api/config'
import { Empty, ErrorBox, PageHeader, Spinner } from '../components/ui'
import { useSettings } from '../context/SettingsContext'
import { useApi } from '../lib/useApi'

export function PlayerAvatar({ player, size = 'h-12 w-12' }) {
  const photo = mediaUrl(player.photo)
  const initials = player.full_name.split(' ').map((x) => x[0]).slice(0, 2).join('')
  return photo ? <img src={photo} alt={player.full_name} className={`${size} rounded-full object-cover`} /> : (
    <span className={`${size} inline-flex items-center justify-center rounded-full bg-gradient-to-br from-pitch-500 to-pitch-800 font-bold text-white`} aria-hidden="true">{initials}</span>
  )
}

export default function Players() {
  const { t } = useSettings()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error } = useApi('/players/', { params: { search: q || undefined, page, page_size: 48 } })
  return (
    <div>
      <PageHeader title={t('players')} icon={Users} actions={<input className="input w-56" placeholder={t('search')} value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} aria-label={t('search')} />} />
      <ErrorBox>{error}</ErrorBox>
      {loading ? <Spinner /> : list(data).length ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {list(data).map((p) => (
              <Link key={p.id} to={`/players/${p.id}`} className="card flex items-center gap-3 p-3 hover:border-pitch-300">
                <PlayerAvatar player={p} />
                <div className="min-w-0">
                  <div className="truncate font-semibold">{p.full_name}</div>
                  <div className="truncate text-xs capitalize text-slate-500">{p.role.replace('_', ' ')} · {p.team_name || 'Free agent'}</div>
                </div>
              </Link>
            ))}
          </div>
          <div className="mt-4 flex justify-center gap-2">
            <button className="btn-secondary" disabled={!data.previous} onClick={() => setPage(page - 1)}>Previous</button>
            <button className="btn-secondary" disabled={!data.next} onClick={() => setPage(page + 1)}>Next</button>
          </div>
        </>
      ) : <Empty icon={Users}>No players found.</Empty>}
    </div>
  )
}
