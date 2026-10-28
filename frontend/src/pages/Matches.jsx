import { useSearchParams } from 'react-router-dom'
import { list } from '../api/client'
import MatchCard from '../components/MatchCard'
import { Empty, ErrorBox, PageHeader, Spinner, Tabs } from '../components/ui'
import { useSettings } from '../context/SettingsContext'
import { useApi } from '../lib/useApi'

export default function Matches() {
  const { t } = useSettings()
  const [params, setParams] = useSearchParams()
  const state = params.get('state') || 'live'
  const tournament = params.get('tournament') || undefined
  const { data, loading, error, reload } = useApi('/matches/', { params: { state, tournament, page_size: 100 } })
  return (
    <div>
      <PageHeader title={t('matches')} />
      <Tabs
        value={state}
        onChange={(v) => setParams({ state: v })}
        tabs={[{ value: 'live', label: t('live') }, { value: 'upcoming', label: t('upcoming') }, { value: 'completed', label: t('completed') }]}
      />
      <ErrorBox onRetry={reload}>{error}</ErrorBox>
      {loading ? <Spinner /> : list(data).length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{list(data).map((m) => <MatchCard key={m.id} match={m} />)}</div>
      ) : <Empty>{t('noMatches')}</Empty>}
    </div>
  )
}
