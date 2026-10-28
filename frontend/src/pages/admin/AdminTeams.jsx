import { Plus, Shield, Trash2 } from 'lucide-react'
import { useState } from 'react'
import api, { errorMessage, list } from '../../api/client'
import { ConfirmDialog, ErrorBox, Field, Modal, PageHeader, Spinner, TeamBadge } from '../../components/ui'
import { useApi } from '../../lib/useApi'

async function saveWithFile(url, method, body, fileField, file) {
  const r = await api[method](url, body)
  if (file) {
    const fd = new FormData()
    fd.append(fileField, file)
    return api.patch(`${url.endsWith('/') && method === 'post' ? `${url}${r.data.id}/` : url}`, fd)
  }
  return r
}

function TeamForm({ initial, onClose }) {
  const [form, setForm] = useState(initial || { name: '', short_name: '', primary_color: '#0f766e', city: '' })
  const [logo, setLogo] = useState(null)
  const [error, setError] = useState(null)
  const save = async () => {
    try {
      const { name, short_name, primary_color, city } = form
      if (initial) await saveWithFile(`/teams/${initial.id}/`, 'patch', { name, short_name, primary_color, city }, 'logo', logo)
      else await saveWithFile('/teams/', 'post', { name, short_name, primary_color, city }, 'logo', logo)
      onClose(true)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  return (
    <Modal open onClose={() => onClose(false)} title={initial ? 'Edit team' : 'New team'} footer={<button className="btn-primary" onClick={save}>Save</button>}>
      <ErrorBox>{error}</ErrorBox>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name"><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="Short name (max 6)"><input className="input" maxLength={6} value={form.short_name} onChange={(e) => setForm({ ...form, short_name: e.target.value.toUpperCase() })} /></Field>
        <Field label="City"><input className="input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></Field>
        <Field label="Team colour"><input type="color" className="input h-10 p-1" value={form.primary_color} onChange={(e) => setForm({ ...form, primary_color: e.target.value })} /></Field>
        <div className="sm:col-span-2"><Field label="Logo (PNG/JPG, your own artwork)"><input type="file" accept="image/*" className="input" onChange={(e) => setLogo(e.target.files[0])} /></Field></div>
      </div>
    </Modal>
  )
}

function PlayerForm({ team, initial, onClose }) {
  const [form, setForm] = useState(initial || { full_name: '', short_name: '', role: 'batter', batting_style: 'right', bowling_style: '', jersey_number: '' })
  const [photo, setPhoto] = useState(null)
  const [error, setError] = useState(null)
  const save = async () => {
    try {
      const body = { full_name: form.full_name, short_name: form.short_name, role: form.role, batting_style: form.batting_style, bowling_style: form.bowling_style, jersey_number: form.jersey_number || null, team: team.id }
      if (initial) await saveWithFile(`/players/${initial.id}/`, 'patch', body, 'photo', photo)
      else await saveWithFile('/players/', 'post', body, 'photo', photo)
      onClose(true)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  return (
    <Modal open onClose={() => onClose(false)} title={initial ? 'Edit player' : `New player for ${team.name}`} footer={<button className="btn-primary" onClick={save}>Save</button>}>
      <ErrorBox>{error}</ErrorBox>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Full name"><input className="input" value={form.full_name} onChange={set('full_name')} /></Field>
        <Field label="Scorecard name" hint="Optional, e.g. R Patil"><input className="input" value={form.short_name} onChange={set('short_name')} /></Field>
        <Field label="Role"><select className="input" value={form.role} onChange={set('role')}><option value="batter">Batter</option><option value="bowler">Bowler</option><option value="all_rounder">All-rounder</option><option value="wicket_keeper">Wicket-keeper</option></select></Field>
        <Field label="Batting"><select className="input" value={form.batting_style} onChange={set('batting_style')}><option value="right">Right-hand</option><option value="left">Left-hand</option></select></Field>
        <Field label="Bowling style"><input className="input" value={form.bowling_style} onChange={set('bowling_style')} placeholder="Right-arm medium" /></Field>
        <Field label="Jersey number"><input type="number" className="input" value={form.jersey_number ?? ''} onChange={set('jersey_number')} /></Field>
        <div className="sm:col-span-2"><Field label="Photo"><input type="file" accept="image/*" className="input" onChange={(e) => setPhoto(e.target.files[0])} /></Field></div>
      </div>
    </Modal>
  )
}

export default function AdminTeams() {
  const teams = useApi('/teams/', { params: { page_size: 500 } })
  const [team, setTeam] = useState(null)
  const players = useApi(team ? '/players/' : null, { params: { team: team?.id, page_size: 200 } })
  const [teamForm, setTeamForm] = useState(null)
  const [playerForm, setPlayerForm] = useState(null)
  const [del, setDel] = useState(null)
  const [error, setError] = useState(null)
  return (
    <div>
      <PageHeader title="Teams & players" icon={Shield} actions={<button className="btn-primary" onClick={() => setTeamForm({})}><Plus className="h-4 w-4" /> New team</button>} />
      <ErrorBox>{error}</ErrorBox>
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className="card max-h-[70vh] overflow-y-auto p-2">
          {teams.loading ? <Spinner /> : list(teams.data).map((t) => (
            <button key={t.id} onClick={() => setTeam(t)} className={`flex w-full items-center gap-2 rounded-xl p-2 text-left text-sm ${team?.id === t.id ? 'bg-pitch-50 dark:bg-pitch-900/40' : 'hover:bg-slate-50 dark:hover:bg-slate-800'}`}>
              <TeamBadge team={t} size="sm" /> <span className="flex-1 truncate font-semibold">{t.name}</span> <span className="text-xs text-slate-500">{t.player_count}</span>
            </button>
          ))}
        </div>
        <div className="card p-4">
          {!team ? <p className="text-sm text-slate-500">Select a team to manage its players.</p> : (
            <>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <TeamBadge team={team} />
                <h2 className="text-lg font-bold">{team.name}</h2>
                <button className="btn-secondary ml-auto py-1" onClick={() => setTeamForm(team)}>Edit team</button>
                <button className="btn-primary py-1" onClick={() => setPlayerForm({})}><Plus className="h-4 w-4" /> Add player</button>
              </div>
              {players.loading ? <Spinner /> : (
                <table className="table-basic">
                  <thead><tr><th>#</th><th>Name</th><th>Role</th><th>Bat</th><th>Bowl</th><th /></tr></thead>
                  <tbody>
                    {list(players.data).map((p) => (
                      <tr key={p.id}>
                        <td>{p.jersey_number}</td><td className="font-semibold">{p.full_name}</td><td className="capitalize">{p.role.replace('_', ' ')}</td>
                        <td className="capitalize">{p.batting_style}</td><td>{p.bowling_style}</td>
                        <td className="whitespace-nowrap text-right">
                          <button className="btn-ghost px-2 py-1 text-xs" onClick={() => setPlayerForm(p)}>Edit</button>
                          <button className="btn-ghost p-1 text-red-600" onClick={() => setDel(p)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </div>
      </div>
      {teamForm && <TeamForm initial={teamForm.id ? teamForm : null} onClose={(ok) => { setTeamForm(null); if (ok) teams.reload() }} />}
      {playerForm && <PlayerForm team={team} initial={playerForm.id ? playerForm : null} onClose={(ok) => { setPlayerForm(null); if (ok) { players.reload(); teams.reload() } }} />}
      <ConfirmDialog open={!!del} danger title="Delete player?" message="Players who have already played matches cannot be deleted (their scoring history is protected)." confirmLabel="Delete"
        onCancel={() => setDel(null)}
        onConfirm={async () => { const p = del; setDel(null); try { await api.delete(`/players/${p.id}/`); players.reload() } catch (e) { setError(e.response?.status === 500 ? 'This player has match history and cannot be deleted.' : errorMessage(e)) } }} />
    </div>
  )
}
