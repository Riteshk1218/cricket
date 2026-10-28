import { Clock, Eye, Heart, MapPin, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage } from '../api/client'
import { useMatchSocket } from '../api/useMatchSocket'
import CelebrationOverlay from '../components/CelebrationOverlay'
import {
  BallDot, BattingTable, BowlingTable, Commentary, FallOfWickets, OversTimeline, Partnerships, RunCharts,
} from '../components/Scorecard'
import { ErrorBox, Spinner, StatusChip, Tabs, TeamBadge } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'
import { trackView } from '../lib/analytics'
import { clockText, fmtDateTime, STAGE_LABEL } from '../lib/format'

function TeamScore({ team, innings, active }) {
  const { t } = useSettings()
  const mine = innings.filter((i) => i.batting_team.id === team.id)
  return (
    <div className={`flex items-center gap-3 ${active ? '' : 'opacity-80'}`}>
      <TeamBadge team={team} size="lg" />
      <div>
        <div className="text-sm font-semibold text-white/80">{team.name}</div>
        {mine.length ? (
          mine.map((i) => (
            <div key={i.id} className={i.is_super_over ? 'text-sm text-amber-200' : 'text-3xl font-black tabular-nums sm:text-4xl'}>
              {i.is_super_over && 'Super over '}{i.total}/{i.wickets}
              <span className="ml-2 text-base font-medium text-white/70">({i.overs})</span>
            </div>
          ))
        ) : (
          <div className="text-lg text-white/60">{t('yetToBat')}</div>
        )}
      </div>
    </div>
  )
}

function LiveHeader({ snap, viewers, status }) {
  const { t } = useSettings()
  const c = snap.current
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30000)
    return () => clearInterval(id)
  }, [])
  const clock = clockText(snap.clock, now)
  return (
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-pitch-700 via-pitch-800 to-slate-900 p-5 text-white shadow-lg sm:p-7">
      <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-white/80">
        <StatusChip status={snap.status} />
        <Link to={`/tournaments/${snap.tournament.id}`} className="font-semibold hover:underline">{snap.tournament.name}</Link>
        <span>· {STAGE_LABEL[snap.stage]} #{snap.match_number}</span>
        {snap.ground && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {snap.ground}</span>}
        <span className="ml-auto flex items-center gap-3">
          {clock && <span className="flex items-center gap-1" title={t('matchClock')}><Clock className="h-3 w-3" /> {clock}</span>}
          {viewers != null && <span className="flex items-center gap-1"><Eye className="h-3 w-3" /> {viewers} {t('viewers')}</span>}
          <span className="flex items-center gap-1" title={t('connection')}>
            {status === 'open' ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3 text-amber-300" />}
            <span className="hidden sm:inline">{status === 'open' ? t('connected') : t('reconnecting')}</span>
          </span>
        </span>
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <TeamScore team={snap.team_a} innings={snap.innings} active={c?.batting_team?.id === snap.team_a.id} />
        <TeamScore team={snap.team_b} innings={snap.innings} active={c?.batting_team?.id === snap.team_b.id} />
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-white/10 pt-4 text-sm">
        {snap.result ? (
          <span className="text-lg font-bold text-gold">{snap.result.summary}</span>
        ) : snap.status === 'paused' ? (
          <span className="font-bold text-amber-300">{t('interrupted')}: {snap.clock.pause_reason}</span>
        ) : snap.status === 'innings_break' ? (
          <span className="font-bold text-amber-200">{t('inningsBreak')}</span>
        ) : c?.equation ? (
          <span className="font-bold text-gold">{c.equation}</span>
        ) : snap.toss ? (
          <span className="text-white/80">{snap.toss.text}</span>
        ) : (
          <span className="text-white/80">{fmtDateTime(snap.scheduled_at)}</span>
        )}
        {c && c.in_progress && (
          <>
            <span>{t('runRate')} <b className="tabular-nums">{c.run_rate.toFixed(2)}</b></span>
            {c.target && <span>{t('target')} <b>{c.target}</b></span>}
            {c.required_run_rate != null && <span>{t('reqRate')} <b className="tabular-nums">{c.required_run_rate.toFixed(2)}</b></span>}
            {c.powerplay?.active && <span className="chip bg-sky-500/30 text-sky-100">{t('powerplay')} {c.powerplay.number}</span>}
            {c.free_hit && <span className="chip animate-pulse bg-gold text-slate-900">{t('freeHit')}</span>}
          </>
        )}
      </div>
    </div>
  )
}

function LivePanel({ snap }) {
  const { t } = useSettings()
  const c = snap.current
  if (!c) return <p className="text-sm text-slate-500">{snap.toss ? snap.toss.text : 'The match has not started yet.'}</p>
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="card p-4 lg:col-span-2">
        <table className="table-basic">
          <thead>
            <tr><th>{t('batter')}</th><th className="text-right">{t('runs')}</th><th className="text-right">{t('ballsShort')}</th><th className="text-right">{t('fours')}</th><th className="text-right">{t('sixes')}</th><th className="text-right">{t('strikeRate')}</th></tr>
          </thead>
          <tbody>
            {[c.striker, c.non_striker].filter(Boolean).map((b, i) => (
              <tr key={b.player_id}>
                <td className="font-semibold">{b.name}{i === 0 && c.in_progress ? ' *' : ''}</td>
                <td className="text-right font-bold tabular-nums">{b.runs}</td>
                <td className="text-right tabular-nums">{b.balls}</td>
                <td className="text-right tabular-nums">{b.fours}</td>
                <td className="text-right tabular-nums">{b.sixes}</td>
                <td className="text-right tabular-nums">{Number(b.strike_rate).toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {c.bowler && (
          <table className="table-basic mt-3">
            <thead><tr><th>{t('bowler')}</th><th className="text-right">{t('oversShort')}</th><th className="text-right">{t('maidens')}</th><th className="text-right">{t('runs')}</th><th className="text-right">{t('wicketsShort')}</th><th className="text-right">{t('economy')}</th></tr></thead>
            <tbody>
              <tr>
                <td className="font-semibold">{c.bowler.name}</td>
                <td className="text-right tabular-nums">{c.bowler.overs}</td>
                <td className="text-right tabular-nums">{c.bowler.maidens}</td>
                <td className="text-right tabular-nums">{c.bowler.runs}</td>
                <td className="text-right font-bold tabular-nums">{c.bowler.wickets}</td>
                <td className="text-right tabular-nums">{Number(c.bowler.economy).toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
        )}
        <div className="mt-4">
          <h4 className="label">{t('recent')}</h4>
          <div className="flex flex-wrap gap-1.5">{c.recent_balls.map((b, i) => <BallDot key={i} label={b} />)}</div>
        </div>
      </div>
      <div className="card space-y-4 p-4">
        {c.this_over && (
          <div>
            <h4 className="label">{t('thisOver')} ({c.this_over.number})</h4>
            <div className="flex flex-wrap gap-1.5">{c.this_over.balls.map((b, i) => <BallDot key={i} label={b} size="lg" />)}</div>
          </div>
        )}
        {c.partnership && (
          <div>
            <h4 className="label">{t('partnership')}</h4>
            <p className="text-2xl font-bold tabular-nums">{c.partnership.runs} <span className="text-base font-normal text-slate-500">({c.partnership.balls})</span></p>
            <p className="text-xs text-slate-500">{c.partnership.batters.join(' & ')}</p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-xl bg-slate-100 p-2 dark:bg-slate-800"><div className="text-xs text-slate-500">{t('overs')}</div><b>{c.overs}</b></div>
          <div className="rounded-xl bg-slate-100 p-2 dark:bg-slate-800"><div className="text-xs text-slate-500">{t('runRate')}</div><b>{c.run_rate.toFixed(2)}</b></div>
          {c.target && <div className="rounded-xl bg-slate-100 p-2 dark:bg-slate-800"><div className="text-xs text-slate-500">{t('target')}</div><b>{c.target}</b></div>}
          {c.required_run_rate != null && <div className="rounded-xl bg-slate-100 p-2 dark:bg-slate-800"><div className="text-xs text-slate-500">{t('reqRate')}</div><b>{c.required_run_rate.toFixed(2)}</b></div>}
        </div>
      </div>
      <div className="card p-4 lg:col-span-3">
        <h3 className="mb-3 font-bold">{t('commentary')}</h3>
        <Commentary entries={snap.commentary} limit={12} />
      </div>
    </div>
  )
}

function FullCommentary({ matchId, version }) {
  const [entries, setEntries] = useState(null)
  useEffect(() => {
    api.get(`/matches/${matchId}/commentary/`).then((r) => setEntries(r.data)).catch(() => setEntries([]))
  }, [matchId, version])
  if (!entries) return <Spinner />
  return <div className="card p-4"><Commentary entries={entries} /></div>
}

function Squads({ snap }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {[snap.team_a, snap.team_b].map((team) => (
        <div key={team.id} className="card p-4">
          <h3 className="mb-2 flex items-center gap-2 font-bold"><TeamBadge team={team} size="sm" /> {team.name}</h3>
          <ol className="space-y-1 text-sm">
            {(snap.squads[String(team.id)] || []).map((p) => (
              <li key={p.player_id}>
                <Link to={`/players/${p.player_id}`} className="hover:underline">{p.batting_order}. {p.name}</Link>
                {p.is_captain && <span className="ml-1 text-xs font-bold text-amber-600">(c)</span>}
                {p.is_wicket_keeper && <span className="ml-1 text-xs font-bold text-sky-600">(wk)</span>}
              </li>
            ))}
            {!(snap.squads[String(team.id)] || []).length && <li className="text-slate-500">Playing XI not announced yet.</li>}
          </ol>
        </div>
      ))}
    </div>
  )
}

export default function MatchDetail() {
  const { id } = useParams()
  const { t } = useSettings()
  const { user } = useAuth()
  const [snap, setSnap] = useState(null)
  const [error, setError] = useState(null)
  const [event, setEvent] = useState(null)
  const [tab, setTab] = useState('live')
  const [favorite, setFavorite] = useState(null)

  const { status, viewers, reset } = useMatchSocket(id, (s, ev) => {
    setSnap(s)
    if (ev?.highlight) setEvent(ev)
  })

  useEffect(() => {
    trackView(`/matches/${id}`, Number(id))
    api.get(`/matches/${id}/live/`).then((r) => {
      setSnap((cur) => (cur && cur.version >= r.data.version ? cur : r.data))
      reset(r.data.version)
    }).catch((e) => setError(errorMessage(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (!user) return
    api.get('/favorites/').then((r) => setFavorite(r.data.find((f) => f.match === Number(id)) || false)).catch(() => {})
  }, [user, id])

  const toggleFollow = async () => {
    if (favorite) {
      await api.delete(`/favorites/${favorite.id}/`)
      setFavorite(false)
    } else {
      const r = await api.post('/favorites/', { match: Number(id) })
      setFavorite(r.data)
    }
  }

  if (error) return <ErrorBox>{error}</ErrorBox>
  if (!snap) return <Spinner />
  const tabs = [
    { value: 'live', label: t('overview') },
    { value: 'scorecard', label: t('scorecard') },
    { value: 'commentary', label: t('commentary') },
    { value: 'overs', label: t('overs') },
    { value: 'charts', label: 'Charts' },
    { value: 'squads', label: t('squads') },
  ]
  return (
    <div>
      <CelebrationOverlay event={event} />
      <LiveHeader snap={snap} viewers={viewers} status={status} />
      <div className="mt-4 flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1"><Tabs tabs={tabs} value={tab} onChange={setTab} /></div>
        {user && favorite !== null && (
          <button className={`mb-4 ${favorite ? 'btn-primary' : 'btn-secondary'}`} onClick={toggleFollow} aria-pressed={!!favorite}>
            <Heart className={`h-4 w-4 ${favorite ? 'fill-current' : ''}`} /> <span className="hidden sm:inline">{favorite ? t('following') : t('follow')}</span>
          </button>
        )}
      </div>
      {tab === 'live' && <LivePanel snap={snap} />}
      {tab === 'scorecard' && (
        <div className="space-y-6">
          {snap.innings.length === 0 && <p className="text-sm text-slate-500">No innings yet.</p>}
          {snap.innings.map((inn) => (
            <div key={inn.id} className="card space-y-4 p-4">
              <h3 className="flex items-center gap-2 text-lg font-bold">
                <TeamBadge team={inn.batting_team} size="sm" /> {inn.batting_team.name}
                {inn.is_super_over && <span className="chip bg-amber-100 text-amber-800">Super over</span>}
                <span className="ml-auto tabular-nums">{inn.total}/{inn.wickets} <span className="text-sm font-normal text-slate-500">({inn.overs})</span></span>
              </h3>
              <BattingTable innings={inn} />
              <BowlingTable innings={inn} />
              <FallOfWickets innings={inn} />
              <Partnerships innings={inn} />
            </div>
          ))}
          {snap.toss && <p className="text-sm text-slate-500">{t('toss')}: {snap.toss.text}</p>}
        </div>
      )}
      {tab === 'commentary' && <FullCommentary matchId={id} version={snap.version} />}
      {tab === 'overs' && (
        <div className="space-y-6">
          {snap.innings.map((inn) => (
            <div key={inn.id} className="card p-4">
              <h3 className="mb-3 font-bold">{inn.batting_team.name}</h3>
              <OversTimeline innings={inn} />
            </div>
          ))}
        </div>
      )}
      {tab === 'charts' && <RunCharts innings={snap.innings} />}
      {tab === 'squads' && <Squads snap={snap} />}
    </div>
  )
}
