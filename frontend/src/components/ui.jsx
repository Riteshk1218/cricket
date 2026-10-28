import { AlertTriangle, Loader2, X } from 'lucide-react'
import { useEffect } from 'react'
import { mediaUrl } from '../api/config'
import { STATUS_LABEL, isLive } from '../lib/format'

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-slate-500" role="status">
      <Loader2 className="h-5 w-5 animate-spin" /> <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorBox({ children, onRetry }) {
  if (!children) return null
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/50 dark:text-red-200" role="alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{children}</div>
      {onRetry && <button className="font-semibold underline" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function Empty({ children, icon: Icon }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-700">
      {Icon && <Icon className="h-8 w-8 text-slate-400" />}
      {children}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions, icon: Icon }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="flex items-center gap-3">
        {Icon && <span className="rounded-xl bg-pitch-100 p-2 text-pitch-700 dark:bg-pitch-900 dark:text-pitch-300"><Icon className="h-6 w-6" /></span>}
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function TeamBadge({ team, size = 'md' }) {
  const sizes = { sm: 'h-7 w-7 text-[10px]', md: 'h-10 w-10 text-xs', lg: 'h-16 w-16 text-base' }
  if (!team) return null
  const logo = mediaUrl(team.logo)
  return logo ? (
    <img src={logo} alt={`${team.name} logo`} className={`${sizes[size]} rounded-full object-cover ring-2 ring-white dark:ring-slate-800`} />
  ) : (
    <span
      aria-hidden="true"
      className={`${sizes[size]} inline-flex shrink-0 items-center justify-center rounded-full font-black text-white ring-2 ring-white dark:ring-slate-800`}
      style={{ background: `linear-gradient(135deg, ${team.primary_color || '#0f766e'}, #0f172a)` }}
    >
      {(team.short_name || team.name || '?').slice(0, 3)}
    </span>
  )
}

export function StatusChip({ status }) {
  if (isLive(status)) {
    const label = status === 'live' ? 'LIVE' : STATUS_LABEL[status].toUpperCase()
    return (
      <span className="chip bg-red-600 text-white">
        <span className="live-dot h-1.5 w-1.5 rounded-full bg-white" /> {label}
      </span>
    )
  }
  const styles = {
    completed: 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    abandoned: 'bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
    scheduled: 'bg-sky-100 text-sky-800 dark:bg-sky-900/50 dark:text-sky-200',
    toss: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  }
  return <span className={`chip ${styles[status] || ''}`}>{STATUS_LABEL[status] || status}</span>
}

export function Modal({ open, onClose, title, children, footer, wide }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/60 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`card max-h-[92vh] w-full overflow-y-auto rounded-b-none sm:rounded-2xl ${wide ? 'sm:max-w-3xl' : 'sm:max-w-lg'}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-bold">{title}</h2>
          <button className="btn-ghost p-1" onClick={onClose} aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        <div className="p-5">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 px-5 py-3 dark:border-slate-800">{footer}</div>}
      </div>
    </div>
  )
}

export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', danger, onConfirm, onCancel, busy, children }) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      footer={
        <>
          <button className="btn-secondary" onClick={onCancel}>Cancel</button>
          <button className={danger ? 'btn-danger' : 'btn-primary'} onClick={onConfirm} disabled={busy}>{confirmLabel}</button>
        </>
      }
    >
      <p className="text-sm text-slate-600 dark:text-slate-300">{message}</p>
      {children}
    </Modal>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="mb-4 flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1 dark:bg-slate-800/70" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
            value === t.value ? 'bg-white text-pitch-700 shadow-sm dark:bg-slate-900 dark:text-pitch-300' : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

export function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  )
}

export function Stat({ label, value, sub, icon: Icon, tone = 'pitch' }) {
  const tones = {
    pitch: 'bg-pitch-100 text-pitch-700 dark:bg-pitch-900/60 dark:text-pitch-300',
    red: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    amber: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    sky: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
    violet: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
  }
  return (
    <div className="card flex items-center gap-3 p-4">
      {Icon && <span className={`rounded-xl p-2.5 ${tones[tone]}`}><Icon className="h-5 w-5" /></span>}
      <div className="min-w-0">
        <div className="text-2xl font-bold tabular-nums">{value ?? '—'}</div>
        <div className="truncate text-xs font-medium text-slate-500 dark:text-slate-400">{label}</div>
        {sub && <div className="text-xs text-slate-400">{sub}</div>}
      </div>
    </div>
  )
}
