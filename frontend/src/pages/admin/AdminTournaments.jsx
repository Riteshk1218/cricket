import { Plus, Trophy } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api, { errorMessage, list } from '../../api/client'
import { Empty, ErrorBox, Field, Modal, PageHeader, Spinner } from '../../components/ui'
import { fmtDate } from '../../lib/format'
import { useApi } from '../../lib/useApi'

export function TournamentForm({ initial, onSaved, onCancel }) {
  const today = new Date().toISOString().slice(0, 10)
  const [form, setForm] = useState(
    initial || { name: '', short_name: '', location: '', start_date: today, end_date: today, kind: 'league', match_format: 'T20', ball_type: 'leather', overs: '', playoff_teams: 4, description: '' },
  )
  const [logo, setLogo] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const payload = { ...form }
      if (!payload.overs) delete payload.overs
      delete payload.rules
      delete payload.grounds
      delete payload.admins
      delete payload.logo
      const r = initial ? await api.patch(`/tournaments/${initial.id}/`, payload) : await api.post('/tournaments/', payload)
      if (logo) {
        const fd = new FormData()
        fd.append('logo', logo)
        await api.patch(`/tournaments/${r.data.id}/`, fd)
      }
      onSaved(r.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2"><ErrorBox>{error}</ErrorBox></div>
      <Field label="Name"><input className="input" required value={form.name} onChange={set('name')} /></Field>
      <Field label="Short name"><input className="input" value={form.short_name} onChange={set('short_name')} maxLength={20} /></Field>
      <Field label="Location"><input className="input" value={form.location} onChange={set('location')} /></Field>
      <Field label="Logo"><input type="file" accept="image/*" className="input" onChange={(e) => setLogo(e.target.files[0])} /></Field>
      <Field label="Start date"><input type="date" className="input" required value={form.start_date} onChange={set('start_date')} /></Field>
      <Field label="End date"><input type="date" className="input" required value={form.end_date} onChange={set('end_date')} /></Field>
      <Field label="Format">
        <select className="input" value={form.match_format} onChange={set('match_format')}>
          <option value="T10">T10 (10 overs)</option><option value="T20">T20 (20 overs)</option><option value="ODI">One Day (50 overs)</option><option value="CUSTOM">Custom overs</option>
        </select>
      </Field>
      {form.match_format === 'CUSTOM' && <Field label="Overs per innings"><input type="number" min="1" max="100" className="input" value={form.overs} onChange={set('overs')} required /></Field>}
      <Field label="Ball / format type" hint="Tennis ball and box cricket presets disable LBW; box cricket uses 8-a-side and last man stands. Adjust in Rules after saving.">
        <select className="input" value={form.ball_type} onChange={set('ball_type')}>
          <option value="leather">Leather ball</option><option value="tennis">Tennis ball</option><option value="box">Box cricket</option>
        </select>
      </Field>
      <Field label="Tournament type">
        <select className="input" value={form.kind} onChange={set('kind')}>
          <option value="league">League (round robin + playoffs)</option><option value="knockout">Knockout</option>
        </select>
      </Field>
      {form.kind === 'league' && (
        <Field label="Playoffs">
          <select className="input" value={form.playoff_teams} onChange={set('playoff_teams')}>
            <option value={4}>Semi-finals + final (top 4)</option><option value={2}>Final only (top 2)</option><option value={0}>No playoffs</option>
          </select>
        </Field>
      )}
      <div className="sm:col-span-2"><Field label="Description"><textarea className="input" rows={2} value={form.description} onChange={set('description')} /></Field></div>
      <div className="flex justify-end gap-2 sm:col-span-2">
        {onCancel && <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>}
        <button className="btn-primary" disabled={busy}>{initial ? 'Save' : 'Create tournament'}</button>
      </div>
    </form>
  )
}

export default function AdminTournaments() {
  const { data, loading, error, reload } = useApi('/tournaments/', { params: { managed: 1, page_size: 200 } })
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()
  return (
    <div>
      <PageHeader title="Tournaments" icon={Trophy} actions={<button className="btn-primary" onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New tournament</button>} />
      <ErrorBox onRetry={reload}>{error}</ErrorBox>
      {loading ? <Spinner /> : list(data).length ? (
        <div className="card overflow-x-auto">
          <table className="table-basic">
            <thead><tr><th>Name</th><th>Format</th><th>Dates</th><th>Teams</th><th>Matches</th><th>Status</th></tr></thead>
            <tbody>
              {list(data).map((t) => (
                <tr key={t.id}>
                  <td><Link className="font-semibold text-pitch-700 hover:underline dark:text-pitch-400" to={`/admin/tournaments/${t.id}`}>{t.name}</Link></td>
                  <td>{t.match_format} · {t.ball_type}</td>
                  <td>{fmtDate(t.start_date)} – {fmtDate(t.end_date)}</td>
                  <td>{t.team_count}</td><td>{t.match_count}</td><td className="capitalize">{t.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Empty icon={Trophy}>You do not manage any tournaments yet.</Empty>}
      <Modal open={creating} onClose={() => setCreating(false)} title="New tournament" wide>
        <TournamentForm onCancel={() => setCreating(false)} onSaved={(t) => navigate(`/admin/tournaments/${t.id}`)} />
      </Modal>
    </div>
  )
}
