export const fmtDate = (iso, opts = { day: 'numeric', month: 'short', year: 'numeric' }) =>
  iso ? new Date(iso).toLocaleDateString(undefined, opts) : ''
export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '')
export const fmtDateTime = (iso) => (iso ? `${fmtDate(iso, { day: 'numeric', month: 'short' })}, ${fmtTime(iso)}` : '')

export const STATUS_LABEL = {
  scheduled: 'Upcoming', toss: 'Toss done', live: 'Live', innings_break: 'Innings break', paused: 'Interrupted',
  completed: 'Completed', abandoned: 'Abandoned',
}
export const isLive = (s) => ['live', 'innings_break', 'paused'].includes(s)

export const STAGE_LABEL = {
  league: 'League', quarter_final: 'Quarter-final', semi_final: 'Semi-final', final: 'Final', knockout: 'Knockout',
}

export function ballClass(label) {
  if (!label) return 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'
  if (label.includes('W')) return 'bg-ball text-white'
  if (label === '6' || label.startsWith('nb6')) return 'bg-violet-600 text-white'
  if (label === '4' || label.startsWith('nb4')) return 'bg-pitch-600 text-white'
  if (/wd|nb|lb|b|P/.test(label)) return 'bg-amber-200 text-amber-900 dark:bg-amber-500/30 dark:text-amber-200'
  if (label === '0') return 'bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
  return 'bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-200'
}

export const ballText = (label) => (label === '0' ? '•' : label)

export function clockText(clock, now = Date.now()) {
  if (!clock?.started_at) return null
  const end = clock.completed_at ? new Date(clock.completed_at).getTime() : clock.paused_at ? new Date(clock.paused_at).getTime() : now
  const secs = Math.max(0, Math.floor((end - new Date(clock.started_at).getTime()) / 1000) - (clock.paused_seconds || 0))
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  return h ? `${h}h ${m}m` : `${m}m`
}
