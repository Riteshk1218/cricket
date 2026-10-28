import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { ErrorBox, Field } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useSettings } from '../context/SettingsContext'

function landing(user) {
  if (user.role === 'super_admin' || user.role === 'tournament_admin') return '/admin'
  if (user.role === 'scorer') return '/scorer'
  return '/'
}

export function Login() {
  const { login } = useAuth()
  const { t } = useSettings()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = await login(form.username, form.password)
      navigate(location.state?.from || landing(user), { replace: true })
    } catch (err) {
      setError(err.response?.status === 401 ? 'Wrong username or password.' : errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="mx-auto max-w-sm">
      <form onSubmit={submit} className="card space-y-4 p-6">
        <h1 className="text-2xl font-bold">{t('login')}</h1>
        <ErrorBox>{error}</ErrorBox>
        <Field label="Username"><input className="input" autoComplete="username" required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field>
        <Field label="Password"><input className="input" type="password" autoComplete="current-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
        <button className="btn-primary w-full" disabled={busy}>{busy ? '…' : t('login')}</button>
        <p className="text-center text-sm text-slate-500">New here? <Link to="/register" className="font-semibold text-pitch-700 hover:underline dark:text-pitch-400">{t('register')}</Link></p>
      </form>
    </div>
  )
}

export function Register() {
  const { register } = useAuth()
  const { t, lang } = useSettings()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '', display_name: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await register({ ...form, preferred_language: lang })
      navigate('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  return (
    <div className="mx-auto max-w-sm">
      <form onSubmit={submit} className="card space-y-4 p-6">
        <h1 className="text-2xl font-bold">{t('register')}</h1>
        <p className="text-sm text-slate-500">Viewer accounts can follow teams and matches. Admins create scorer accounts.</p>
        <ErrorBox>{error}</ErrorBox>
        <Field label="Username"><input className="input" required value={form.username} onChange={set('username')} /></Field>
        <Field label="Display name"><input className="input" value={form.display_name} onChange={set('display_name')} /></Field>
        <Field label="Email"><input className="input" type="email" required value={form.email} onChange={set('email')} /></Field>
        <Field label="Password" hint="At least 8 characters, not only numbers."><input className="input" type="password" minLength={8} required value={form.password} onChange={set('password')} autoComplete="new-password" /></Field>
        <button className="btn-primary w-full" disabled={busy}>{t('register')}</button>
      </form>
    </div>
  )
}
