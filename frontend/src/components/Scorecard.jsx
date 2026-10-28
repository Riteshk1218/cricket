import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useSettings } from '../context/SettingsContext'
import { ballClass, ballText } from '../lib/format'

export function BallDot({ label, size = 'md' }) {
  const s = size === 'lg' ? 'h-11 min-w-11 text-base' : 'h-8 min-w-8 text-xs'
  return (
    <span className={`ball-in inline-flex items-center justify-center rounded-full px-1.5 font-bold ${s} ${ballClass(label)}`}>
      {ballText(label)}
    </span>
  )
}

export function BattingTable({ innings }) {
  const { t } = useSettings()
  return (
    <div className="overflow-x-auto">
      <table className="table-basic">
        <thead>
          <tr>
            <th>{t('batter')}</th>
            <th className="hidden sm:table-cell" />
            <th className="text-right">{t('runs')}</th>
            <th className="text-right">{t('ballsShort')}</th>
            <th className="text-right">{t('fours')}</th>
            <th className="text-right">{t('sixes')}</th>
            <th className="text-right">{t('strikeRate')}</th>
          </tr>
        </thead>
        <tbody>
          {innings.batting.map((b) => (
            <tr key={b.player_id}>
              <td className="font-semibold">
                <Link to={`/players/${b.player_id}`} className="hover:underline">{b.name}</Link>
                <div className="text-xs font-normal text-slate-500 sm:hidden">{b.dismissal_text}</div>
              </td>
              <td className="hidden text-xs text-slate-500 sm:table-cell">{b.dismissal_text}</td>
              <td className="text-right font-bold tabular-nums">{b.runs}</td>
              <td className="text-right tabular-nums">{b.balls}</td>
              <td className="text-right tabular-nums">{b.fours}</td>
              <td className="text-right tabular-nums">{b.sixes}</td>
              <td className="text-right tabular-nums">{b.strike_rate.toFixed(1)}</td>
            </tr>
          ))}
          <tr>
            <td colSpan={7} className="text-sm">
              <span className="font-semibold">{t('extras')}</span> {innings.extras.total}{' '}
              <span className="text-xs text-slate-500">
                (wd {innings.extras.wides}, nb {innings.extras.noballs}, b {innings.extras.byes}, lb {innings.extras.legbyes}
                {innings.extras.penalty ? `, pen ${innings.extras.penalty}` : ''})
              </span>
            </td>
          </tr>
          <tr>
            <td colSpan={7} className="font-bold">
              {t('total')} {innings.total}/{innings.wickets} <span className="font-normal text-slate-500">({innings.overs} ov, RR {innings.run_rate.toFixed(2)})</span>
            </td>
          </tr>
        </tbody>
      </table>
      {innings.yet_to_bat?.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          <span className="font-semibold">{t('yetToBat')}:</span> {innings.yet_to_bat.map((p) => p.name).join(', ')}
        </p>
      )}
    </div>
  )
}

export function BowlingTable({ innings }) {
  const { t } = useSettings()
  return (
    <div className="overflow-x-auto">
      <table className="table-basic">
        <thead>
          <tr>
            <th>{t('bowler')}</th>
            <th className="text-right">{t('oversShort')}</th>
            <th className="text-right">{t('maidens')}</th>
            <th className="text-right">{t('runs')}</th>
            <th className="text-right">{t('wicketsShort')}</th>
            <th className="text-right">{t('economy')}</th>
            <th className="hidden text-right sm:table-cell">wd</th>
            <th className="hidden text-right sm:table-cell">nb</th>
          </tr>
        </thead>
        <tbody>
          {innings.bowling.map((b) => (
            <tr key={b.player_id}>
              <td className="font-semibold"><Link to={`/players/${b.player_id}`} className="hover:underline">{b.name}</Link></td>
              <td className="text-right tabular-nums">{b.overs}</td>
              <td className="text-right tabular-nums">{b.maidens}</td>
              <td className="text-right tabular-nums">{b.runs}</td>
              <td className="text-right font-bold tabular-nums">{b.wickets}</td>
              <td className="text-right tabular-nums">{b.economy.toFixed(2)}</td>
              <td className="hidden text-right tabular-nums sm:table-cell">{b.wides}</td>
              <td className="hidden text-right tabular-nums sm:table-cell">{b.noballs}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function FallOfWickets({ innings }) {
  const { t } = useSettings()
  if (!innings.fall_of_wickets.length) return null
  return (
    <div>
      <h4 className="label">{t('fallOfWickets')}</h4>
      <div className="flex flex-wrap gap-2 text-sm">
        {innings.fall_of_wickets.map((f) => (
          <span key={f.wicket} className="rounded-lg bg-slate-100 px-2 py-1 dark:bg-slate-800">
            <b>{f.score}-{f.wicket}</b> <span className="text-slate-500">({f.player}, {f.overs})</span>
          </span>
        ))}
      </div>
    </div>
  )
}

export function Partnerships({ innings }) {
  const { t } = useSettings()
  if (!innings.partnerships.length) return null
  const max = Math.max(...innings.partnerships.map((p) => p.runs), 1)
  return (
    <div>
      <h4 className="label">{t('partnerships')}</h4>
      <div className="space-y-2">
        {innings.partnerships.map((p, i) => (
          <div key={i} className="text-sm">
            <div className="flex justify-between gap-2">
              <span className="truncate">{p.batters.join(' & ')}</span>
              <span className="shrink-0 font-semibold tabular-nums">{p.runs} ({p.balls}){p.unbeaten ? '*' : ''}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
              <div className="h-1.5 rounded-full bg-pitch-500" style={{ width: `${(p.runs / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function OversTimeline({ innings }) {
  const overs = innings.overs_detail.slice().reverse()
  return (
    <div className="space-y-2">
      {overs.map((o) => (
        <div key={o.number} className="flex flex-wrap items-center gap-2 border-b border-slate-100 pb-2 text-sm dark:border-slate-800">
          <span className="w-14 shrink-0 font-semibold">Ov {o.number}</span>
          <span className="w-32 shrink-0 truncate text-xs text-slate-500">{o.bowler}</span>
          <div className="flex flex-1 flex-wrap gap-1">{o.balls.map((b, i) => <BallDot key={i} label={b} />)}</div>
          <span className="shrink-0 text-xs font-semibold tabular-nums">{o.runs} runs{o.score_at_end && ` · ${o.score_at_end}`}</span>
        </div>
      ))}
    </div>
  )
}

const palette = ['#16a34a', '#2563eb', '#d97706', '#9333ea']

export function RunCharts({ innings }) {
  const main = innings.filter((i) => !i.is_super_over)
  if (!main.length || !main.some((i) => i.overs_detail.length)) return null
  const maxOvers = Math.max(...main.map((i) => i.overs_detail.length))
  const rows = Array.from({ length: maxOvers }, (_, idx) => {
    const row = { over: idx + 1 }
    main.forEach((inn, k) => {
      const o = inn.overs_detail[idx]
      if (o) {
        row[`r${k}`] = o.runs
        row[`c${k}`] = inn.overs_detail.slice(0, idx + 1).reduce((s, x) => s + x.runs, 0)
      }
    })
    return row
  })
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-4">
        <h4 className="label">Runs per over</h4>
        <div className="h-56">
          <ResponsiveContainer>
            <BarChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="over" fontSize={11} />
              <YAxis fontSize={11} allowDecimals={false} />
              <Tooltip />
              <Legend />
              {main.map((inn, k) => <Bar key={k} dataKey={`r${k}`} name={inn.batting_team.short_name} fill={palette[k]} radius={[3, 3, 0, 0]} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="card p-4">
        <h4 className="label">Worm (cumulative runs)</h4>
        <div className="h-56">
          <ResponsiveContainer>
            <LineChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="over" fontSize={11} />
              <YAxis fontSize={11} allowDecimals={false} />
              <Tooltip />
              <Legend />
              {main.map((inn, k) => <Line key={k} dataKey={`c${k}`} name={inn.batting_team.short_name} stroke={palette[k]} strokeWidth={2} dot={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export function Commentary({ entries, limit }) {
  const { lang } = useSettings()
  const list = limit ? entries.slice(0, limit) : entries
  if (!list.length) return <p className="text-sm text-slate-500">Commentary will appear when the first ball is bowled.</p>
  return (
    <ol className="space-y-2" aria-live="polite">
      {list.map((c, i) =>
        c.type === 'ball' ? (
          <li key={`${c.innings || ''}-${c.delivery_id}`} className={`flex gap-3 rounded-xl p-2 ${c.highlight ? 'bg-slate-50 dark:bg-slate-800/60' : ''}`}>
            <div className="flex w-12 shrink-0 flex-col items-center gap-1">
              <span className="text-xs font-semibold text-slate-500 tabular-nums">{c.over}</span>
              <BallDot label={c.label} />
            </div>
            <div className="text-sm">
              <p className={c.highlight === 'wicket' ? 'font-bold text-red-700 dark:text-red-400' : c.highlight ? 'font-bold' : ''}>{c.text[lang] || c.text.en}</p>
              <p className="text-xs text-slate-500">{c.bowler} to {c.batter} · {c.score}{c.is_free_hit ? ' · Free hit' : ''}{c.note ? ` · ${c.note}` : ''}</p>
            </div>
          </li>
        ) : (
          <li key={`${c.type}-${c.innings || ''}-${c.sequence}-${i}`} className="rounded-xl bg-pitch-50 px-3 py-2 text-sm font-semibold text-pitch-800 dark:bg-pitch-900/40 dark:text-pitch-200">
            {c.text[lang] || c.text.en}
          </li>
        ),
      )}
    </ol>
  )
}
