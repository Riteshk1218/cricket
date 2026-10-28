import { BarChart3 } from 'lucide-react'
import { useState } from 'react'
import { list } from '../api/client'
import Leaderboards from '../components/Leaderboards'
import { PageHeader } from '../components/ui'
import { useSettings } from '../context/SettingsContext'
import { useApi } from '../lib/useApi'

export default function Stats() {
  const { t } = useSettings()
  const [tournament, setTournament] = useState('')
  const tours = useApi('/tournaments/', { params: { page_size: 100 } })
  return (
    <div>
      <PageHeader
        title={t('leaderboards')}
        icon={BarChart3}
        actions={
          <select className="input w-64" value={tournament} onChange={(e) => setTournament(e.target.value)} aria-label="Tournament">
            <option value="">{t('allTournaments')}</option>
            {list(tours.data).map((tr) => <option key={tr.id} value={tr.id}>{tr.name}</option>)}
          </select>
        }
      />
      <Leaderboards key={tournament} tournament={tournament || undefined} />
    </div>
  )
}
