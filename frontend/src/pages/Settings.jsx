import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api/client'
import { ErrorBox, Field, PageHeader } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'
import { LANGS } from '../i18n/strings'
import { playEffect } from '../lib/sound'

export function SettingsPage() {
  const s = useSettings()
  const { t } = s
  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title={t('settings')} />
      <div className="card space-y-5 p-6">
        <Field label={t('language')}>
          <select className="input" value={s.lang} onChange={(e) => s.setLang(e.target.value)}>
            {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </Field>
        <Field label={t('theme')}>
          <div className="flex gap-2">
            {['light', 'dark'].map((th) => (
              <button key={th} className={s.theme === th ? 'btn-primary' : 'btn-secondary'} onClick={() => s.setTheme(th)}>{t(th)}</button>
            ))}
          </div>
        </Field>
        <label className="flex items-center justify-between gap-3">
          <span className="font-semibold">{t('animations')}</span>
          <input type="checkbox" className="h-5 w-5 accent-pitch-600" checked={s.animations} onChange={(e) => s.setAnimations(e.target.checked)} />
        </label>
        <label className="flex items-center justify-between gap-3">
          <span className="font-semibold">{t('sound')}</span>
          <input type="checkbox" className="h-5 w-5 accent-pitch-600" checked={s.sound} onChange={(e) => s.setSound(e.target.checked)} />
        </label>
        <Field label={`${t('volume')} (${Math.round(s.volume * 100)}%)`}>
          <input type="range" min="0" max="1" step="0.05" value={s.volume} onChange={(e) => s.setVolume(Number(e.target.value))} className="w-full accent-pitch-600" disabled={!s.sound} />
        </Field>
        <div className="flex flex-wrap gap-2">
          {['four', 'six', 'wicket'].map((k) => (
            <button key={k} className="btn-secondary" onClick={() => playEffect(k, s.volume)} disabled={!s.sound}>▶ {t(k)}</button>
          ))}
        </div>
        <p className="text-xs text-slate-500">Sounds are generated in your browser (original, no audio files). Animations respect the “reduce motion” setting of your device.</p>
      </div>
    </div>
  )
}

export function Profile() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState({ display_name: user.display_name, email: user.email, phone: user.phone, preferred_language: user.preferred_language })
  const [msg, setMsg] = useState(null)
  const [error, setError] = useState(null)
  const save = async (e) => {
    e.preventDefault()
    try {
      const { data } = await api.patch('/auth/me/', form)
      setUser(data)
      setMsg('Saved.')
      setError(null)
    } catch (err) {
      setError(errorMessage(err))
    }
  }
  const [favs, setFavs] = useState(null)
  useEffect(() => {
    api.get('/favorites/').then((r) => setFavs(r.data)).catch(() => setFavs([]))
  }, [])
  return (
    <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-2">
      <form onSubmit={save} className="card space-y-4 p-6">
        <h1 className="text-xl font-bold">{user.username} <span className="chip ml-1 bg-pitch-100 capitalize text-pitch-800 dark:bg-pitch-900 dark:text-pitch-200">{user.role.replace('_', ' ')}</span></h1>
        <ErrorBox>{error}</ErrorBox>
        {msg && <p className="text-sm text-pitch-700">{msg}</p>}
        <Field label="Display name"><input className="input" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} /></Field>
        <Field label="Email"><input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        <Field label="Phone"><input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
        <Field label="Language">
          <select className="input" value={form.preferred_language} onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}>
            {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </Field>
        <button className="btn-primary">Save</button>
      </form>
      <div className="card p-6">
        <h2 className="mb-3 text-lg font-bold">Following</h2>
        <ul className="space-y-2 text-sm">
          {(favs || []).map((f) => (
            <li key={f.id} className="flex items-center justify-between gap-2">
              {f.team && <Link className="hover:underline" to={`/teams/${f.team}`}>Team: {f.team_name}</Link>}
              {f.match && <Link className="hover:underline" to={`/matches/${f.match}`}>Match: {f.match_title}</Link>}
              {f.tournament && <Link className="hover:underline" to={`/tournaments/${f.tournament}`}>Tournament: {f.tournament_name}</Link>}
              <button className="btn-ghost px-2 py-1 text-xs" onClick={async () => { await api.delete(`/favorites/${f.id}/`); setFavs(favs.filter((x) => x.id !== f.id)) }}>Remove</button>
            </li>
          ))}
          {favs && !favs.length && <li className="text-slate-500">Follow teams and matches from their pages.</li>}
        </ul>
      </div>
    </div>
  )
}
