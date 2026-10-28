import { Radio, Trophy } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { list } from '../api/client'
import { useSocket } from '../api/useMatchSocket'
import MatchCard from '../components/MatchCard'
import { Empty, ErrorBox, Spinner, TeamBadge } from '../components/ui'
import { useSettings } from '../context/SettingsContext'
import { fmtDate } from '../lib/format'

function Section({ title, to, children, icon: Icon }) {
  const { t } = useSettings()
  return (
    <section className="mb-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-bold">{Icon && <Icon className="h-5 w-5 text-pitch-600" />} {title}</h2>
        {to && <Link to={to} className="text-sm font-semibold text-pitch-700 hover:underline dark:text-pitch-400">{t('viewAll')}</Link>}
      </div>
      {children}
    </section>
  )
}

export default function Home() {
  const { t } = useSettings()
  const [data, setData] = useState({ live: [], upcoming: [], completed: [], tournaments: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const dataRef = useRef(data)
  dataRef.current = data

  const load = async () => {
    try {
      const [live, upcoming, completed, tournaments] = await Promise.all([
        api.get('/matches/', { params: { state: 'live', page_size: 12 } }),
        api.get('/matches/', { params: { state: 'upcoming', page_size: 6 } }),
        api.get('/matches/', { params: { state: 'completed', page_size: 6 } }),
        api.get('/tournaments/', { params: { page_size: 6 } }),
      ])
      setData({ live: list(live.data), upcoming: list(upcoming.data), completed: list(completed.data), tournaments: list(tournaments.data) })
      setError(null)
    } catch {
      setError('Could not load matches. Is the backend running on port 8000?')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    load()
  }, [])

  // Live ticker: patch match cards as summaries arrive; reload lists when a match changes state.
  useSocket('/ws/live/?client=web', {
    onMessage: (msg) => {
      if (msg.type !== 'summary') return
      const s = msg.summary
      const inLive = dataRef.current.live.some((m) => m.id === s.id)
      const isLiveNow = ['live', 'innings_break', 'paused'].includes(s.status)
      if (inLive && isLiveNow) setData((d) => ({ ...d, live: d.live.map((m) => (m.id === s.id ? { ...m, ...s } : m)) }))
      else load()
    },
  })

  if (loading) return <Spinner />
  return (
    <div>
      <div className="relative mb-8 overflow-hidden rounded-3xl bg-gradient-to-br from-pitch-700 via-pitch-800 to-slate-900 p-6 text-white sm:p-10">
        <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full border-[18px] border-white/5" />
        <div className="absolute -bottom-24 right-24 h-48 w-48 rounded-full border-[14px] border-white/5" />
        <p className="text-sm font-semibold uppercase tracking-widest text-pitch-200">Local cricket · Ball by ball</p>
        <h1 className="mt-2 max-w-2xl text-3xl font-black sm:text-5xl">Every run, every wicket, live.</h1>
        <p className="mt-3 max-w-xl text-pitch-100">
          {data.live.length} {t('liveMatches').toLowerCase()} · {data.tournaments.length} {t('tournaments').toLowerCase()}
        </p>
      </div>
      <ErrorBox onRetry={load}>{error}</ErrorBox>
      <Section title={t('liveMatches')} to="/matches?state=live" icon={Radio}>
        {data.live.length ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{data.live.map((m) => <MatchCard key={m.id} match={m} />)}</div>
        ) : (
          <Empty icon={Radio}>{t('noMatches')}</Empty>
        )}
      </Section>
      <Section title={t('upcomingMatches')} to="/matches?state=upcoming">
        {data.upcoming.length ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{data.upcoming.map((m) => <MatchCard key={m.id} match={m} />)}</div>
        ) : (
          <Empty>{t('noMatches')}</Empty>
        )}
      </Section>
      <Section title={t('completedMatches')} to="/matches?state=completed">
        {data.completed.length ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{data.completed.map((m) => <MatchCard key={m.id} match={m} />)}</div>
        ) : (
          <Empty>{t('noMatches')}</Empty>
        )}
      </Section>
      <Section title={t('tournaments')} to="/tournaments" icon={Trophy}>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.tournaments.map((tr) => (
            <Link key={tr.id} to={`/tournaments/${tr.id}`} className="card flex items-center gap-3 p-4 hover:border-pitch-300">
              <TeamBadge team={{ name: tr.name, short_name: tr.short_name || tr.name.slice(0, 3), logo: tr.logo, primary_color: '#b45309' }} />
              <div className="min-w-0">
                <div className="truncate font-semibold">{tr.name}</div>
                <div className="text-xs text-slate-500">{tr.match_format} · {tr.location} · {fmtDate(tr.start_date)}</div>
              </div>
              {tr.live_count > 0 && <span className="chip ml-auto bg-red-600 text-white">{tr.live_count} live</span>}
            </Link>
          ))}
        </div>
      </Section>
    </div>
  )
}
