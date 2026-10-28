import { ClipboardList, Plus, Trash2, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage, list } from '../../api/client'
import { ConfirmDialog, ErrorBox, Field, Modal, PageHeader, Spinner, StatusChip, Tabs, TeamBadge } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { fmtDateTime, STAGE_LABEL } from '../../lib/format'
import { useApi } from '../../lib/useApi'
import { TournamentForm } from './AdminTournaments'

const DISMISSAL_KEYS = ['lbw', 'caught', 'stumped', 'hit_wicket', 'run_out', 'bowled', 'retired_out', 'timed_out']

function RulesEditor({ tournament, onSaved }) {
  const [rules, setRules] = useState(tournament.rules)
  const [points, setPoints] = useState({ points_win: tournament.points_win, points_tie: tournament.points_tie, points_no_result: tournament.points_no_result, points_loss: tournament.points_loss })
  const [msg, setMsg] = useState(null)
  const [error, setError] = useState(null)
  const num = (k) => (e) => setRules({ ...rules, [k]: e.target.value === '' ? null : Number(e.target.value) })
  const bool = (k) => (e) => setRules({ ...rules, [k]: e.target.checked })
  const save = async () => {
    try {
      const r = await api.patch(`/tournaments/${tournament.id}/`, { rules, ...points })
      setMsg('Rules saved. They apply to matches created from now on; existing scheduled matches keep their copy.')
      setError(null)
      onSaved(r.data)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  return (
    <div className="card space-y-4 p-4">
      <ErrorBox>{error}</ErrorBox>
      {msg && <p className="text-sm text-pitch-700">{msg}</p>}
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <Field label="Overs per innings"><input type="number" className="input" value={rules.overs_per_innings} onChange={num('overs_per_innings')} /></Field>
        <Field label="Balls per over"><input type="number" className="input" value={rules.balls_per_over} onChange={num('balls_per_over')} /></Field>
        <Field label="Players per side"><input type="number" className="input" value={rules.players_per_side} onChange={num('players_per_side')} /></Field>
        <Field label="Max overs per bowler" hint="Empty = no limit"><input type="number" className="input" value={rules.max_overs_per_bowler ?? ''} onChange={num('max_overs_per_bowler')} /></Field>
        <Field label="Wide penalty runs"><input type="number" className="input" value={rules.wide_runs} onChange={num('wide_runs')} /></Field>
        <Field label="No-ball penalty runs"><input type="number" className="input" value={rules.noball_runs} onChange={num('noball_runs')} /></Field>
        <Field label="Super over: overs"><input type="number" className="input" value={rules.super_over_overs} onChange={num('super_over_overs')} /></Field>
        <Field label="Super over: wickets"><input type="number" className="input" value={rules.super_over_wickets} onChange={num('super_over_wickets')} /></Field>
        <Field label="Powerplays" hint="e.g. 1-6, 15-16">
          <input className="input" defaultValue={(rules.powerplays || []).map((p) => p.join('-')).join(', ')} onBlur={(e) => setRules({ ...rules, powerplays: e.target.value.split(',').map((x) => x.trim().split('-').map(Number)).filter((p) => p.length === 2 && p.every(Number.isFinite)) })} />
        </Field>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {[
          ['free_hit_on_noball', 'Free hit after a no-ball'], ['free_hit_on_wide', 'Free hit after a wide'], ['super_over_on_tie', 'Super over if tied'],
          ['caught_new_batter_on_strike', 'New batter on strike after a catch'], ['last_man_stands', 'Last man stands (bat alone)'], ['consecutive_overs_allowed', 'Allow consecutive overs by one bowler'],
        ].map(([k, l]) => (
          <label key={k} className="flex items-center gap-2 text-sm"><input type="checkbox" className="h-4 w-4 accent-pitch-600" checked={!!rules[k]} onChange={bool(k)} /> {l}</label>
        ))}
      </div>
      <Field label="Dismissals not allowed (local rules)">
        <div className="flex flex-wrap gap-2">
          {DISMISSAL_KEYS.map((d) => {
            const on = (rules.disallowed_dismissals || []).includes(d)
            return (
              <button key={d} type="button" className={`chip px-3 py-1 ${on ? 'bg-red-600 text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => setRules({ ...rules, disallowed_dismissals: on ? rules.disallowed_dismissals.filter((x) => x !== d) : [...(rules.disallowed_dismissals || []), d] })}>
                {d.replace(/_/g, ' ')}
              </button>
            )
          })}
        </div>
      </Field>
      <div className="grid gap-3 sm:grid-cols-4">
        {[['points_win', 'Points for win'], ['points_tie', 'Points for tie'], ['points_no_result', 'Points for no result'], ['points_loss', 'Points for loss']].map(([k, l]) => (
          <Field key={k} label={l}><input type="number" min="0" className="input" value={points[k]} onChange={(e) => setPoints({ ...points, [k]: Number(e.target.value) })} /></Field>
        ))}
      </div>
      <button className="btn-primary" onClick={save}>Save rules</button>
    </div>
  )
}

function GroundsAdmins({ tournament, onSaved }) {
  const { isSuperAdmin } = useAuth()
  const grounds = useApi('/grounds/')
  const admins = useApi(isSuperAdmin ? '/users/' : null, { params: { role: 'tournament_admin', page_size: 200 } })
  const [sel, setSel] = useState(tournament.grounds)
  const [adm, setAdm] = useState(tournament.admins)
  const [error, setError] = useState(null)
  const save = async () => {
    try {
      const body = { grounds: sel }
      if (isSuperAdmin) body.admins = adm
      onSaved((await api.patch(`/tournaments/${tournament.id}/`, body)).data)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const toggle = (arr, setArr, id) => setArr(arr.includes(id) ? arr.filter((x) => x !== id) : [...arr, id])
  return (
    <div className="card space-y-4 p-4">
      <ErrorBox>{error}</ErrorBox>
      <div>
        <h3 className="label">Venues used by this tournament</h3>
        <div className="flex flex-wrap gap-2">
          {(grounds.data || []).map((g) => (
            <button key={g.id} className={`chip px-3 py-1.5 ${sel.includes(g.id) ? 'bg-pitch-600 text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => toggle(sel, setSel, g.id)}>{g.name}{g.city && `, ${g.city}`}</button>
          ))}
        </div>
        <p className="mt-1 text-xs text-slate-500">Add new grounds under Admin → Grounds. Fixtures rotate through the selected grounds.</p>
      </div>
      {isSuperAdmin && (
        <div>
          <h3 className="label">Tournament admins</h3>
          <div className="flex flex-wrap gap-2">
            {list(admins.data).map((u) => (
              <button key={u.id} className={`chip px-3 py-1.5 ${adm.includes(u.id) ? 'bg-pitch-600 text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => toggle(adm, setAdm, u.id)}>{u.display_name || u.username}</button>
            ))}
          </div>
        </div>
      )}
      <button className="btn-primary" onClick={save}>Save</button>
    </div>
  )
}

function Registrations({ tournament }) {
  const regs = useApi(`/tournaments/${tournament.id}/registrations/`)
  const teams = useApi('/teams/', { params: { page_size: 500 } })
  const [team, setTeam] = useState('')
  const [group, setGroup] = useState('A')
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)
  const add = async () => {
    try {
      await api.post(`/tournaments/${tournament.id}/registrations/`, { team, group })
      setTeam('')
      regs.reload()
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const remove = async (r) => {
    try {
      await api.delete(`/registrations/${r.id}/`)
      regs.reload()
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const registered = (regs.data || []).map((r) => r.team)
  return (
    <div className="space-y-4">
      <ErrorBox>{error}</ErrorBox>
      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="min-w-56 flex-1">
          <Field label="Register team">
            <select className="input" value={team} onChange={(e) => setTeam(e.target.value)}>
              <option value="">Select team</option>
              {list(teams.data).filter((t) => !registered.includes(t.id)).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </Field>
        </div>
        <div className="w-28"><Field label="Group"><input className="input" value={group} onChange={(e) => setGroup(e.target.value.toUpperCase())} maxLength={10} /></Field></div>
        <button className="btn-primary" disabled={!team} onClick={add}><Plus className="h-4 w-4" /> Register</button>
        <Link to="/admin/teams" className="btn-secondary">Create a team</Link>
      </div>
      {regs.loading ? <Spinner /> : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(regs.data || []).map((r) => (
            <div key={r.id} className="card flex items-center gap-3 p-3">
              <TeamBadge team={r.team_detail} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">{r.team_detail.name}</div>
                <div className="text-xs text-slate-500">Group {r.group} · squad of {r.players.length}</div>
              </div>
              <button className="btn-ghost px-2 py-1 text-xs" onClick={() => setEditing(r)}>Squad</button>
              <button className="btn-ghost p-1 text-red-600" onClick={() => remove(r)} aria-label="Remove"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      )}
      {editing && <SquadEditor reg={editing} onClose={() => { setEditing(null); regs.reload() }} />}
    </div>
  )
}

function SquadEditor({ reg, onClose }) {
  const players = useApi('/players/', { params: { team: reg.team, page_size: 200 } })
  const [sel, setSel] = useState(reg.players)
  const [group, setGroup] = useState(reg.group)
  const [error, setError] = useState(null)
  const save = async () => {
    try {
      await api.patch(`/registrations/${reg.id}/`, { players: sel, group, team: reg.team })
      onClose()
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  return (
    <Modal open onClose={onClose} title={`${reg.team_detail.name}: tournament squad`} footer={<button className="btn-primary" onClick={save}>Save squad</button>}>
      <ErrorBox>{error}</ErrorBox>
      <Field label="Group"><input className="input mb-3" value={group} onChange={(e) => setGroup(e.target.value.toUpperCase())} /></Field>
      {players.loading ? <Spinner /> : (
        <div className="grid gap-1 sm:grid-cols-2">
          {list(players.data).map((p) => (
            <label key={p.id} className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm hover:bg-slate-50 dark:hover:bg-slate-800">
              <input type="checkbox" className="accent-pitch-600" checked={sel.includes(p.id)} onChange={() => setSel(sel.includes(p.id) ? sel.filter((x) => x !== p.id) : [...sel, p.id])} /> {p.full_name}
            </label>
          ))}
        </div>
      )}
    </Modal>
  )
}

function MatchForm({ tournament, initial, onClose }) {
  const regs = useApi(`/tournaments/${tournament.id}/registrations/`)
  const grounds = useApi('/grounds/')
  const toLocal = (iso) => (iso ? new Date(new Date(iso).getTime() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16) : '')
  const [form, setForm] = useState(initial ? {
    team_a: initial.team_a.id, team_b: initial.team_b.id, ground: initial.ground_id || '', scheduled_at: toLocal(initial.scheduled_at), stage: initial.stage, overs: initial.rules.overs_per_innings,
  } : { team_a: '', team_b: '', ground: '', scheduled_at: toLocal(new Date().toISOString()), stage: 'league', overs: tournament.rules.overs_per_innings })
  const [error, setError] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const save = async () => {
    try {
      const body = {
        tournament: tournament.id, team_a: Number(form.team_a), team_b: Number(form.team_b), ground: form.ground || null,
        scheduled_at: new Date(form.scheduled_at).toISOString(), stage: form.stage,
      }
      if (!initial || initial.status === 'scheduled') body.rules = { overs_per_innings: Number(form.overs) }
      if (initial) await api.patch(`/matches/${initial.id}/`, body)
      else await api.post('/matches/', body)
      onClose(true)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const teams = (regs.data || []).map((r) => r.team_detail)
  return (
    <Modal open onClose={() => onClose(false)} title={initial ? 'Edit match' : 'New match'} footer={<button className="btn-primary" onClick={save}>Save</button>}>
      <ErrorBox>{error}</ErrorBox>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Team A"><select className="input" value={form.team_a} onChange={set('team_a')} disabled={initial && initial.status !== 'scheduled'}><option value="">Select</option>{teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
        <Field label="Team B"><select className="input" value={form.team_b} onChange={set('team_b')} disabled={initial && initial.status !== 'scheduled'}><option value="">Select</option>{teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
        <Field label="Ground"><select className="input" value={form.ground} onChange={set('ground')}><option value="">—</option>{(grounds.data || []).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></Field>
        <Field label="Date & time"><input type="datetime-local" className="input" value={form.scheduled_at} onChange={set('scheduled_at')} /></Field>
        <Field label="Stage"><select className="input" value={form.stage} onChange={set('stage')}>{Object.entries(STAGE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
        <Field label="Overs (this match)"><input type="number" min="1" className="input" value={form.overs} onChange={set('overs')} disabled={initial && initial.status !== 'scheduled'} /></Field>
      </div>
    </Modal>
  )
}

function ScorerAssign({ match, onClose }) {
  const scorers = useApi('/users/', { params: { role: 'scorer', page_size: 200 } })
  const current = useApi(`/matches/${match.id}/scorers/`)
  const [error, setError] = useState(null)
  const assign = async (scorer, active = true) => {
    try {
      await api.post(`/matches/${match.id}/scorers/`, { scorer, is_active: active })
      current.reload()
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const assigned = (current.data || []).filter((a) => a.is_active).map((a) => a.scorer)
  return (
    <Modal open onClose={onClose} title={`Scorers: ${match.team_a.short_name} vs ${match.team_b.short_name}`}>
      <ErrorBox>{error}</ErrorBox>
      {scorers.loading ? <Spinner /> : (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {list(scorers.data).map((u) => (
            <li key={u.id} className="flex items-center justify-between py-2 text-sm">
              <span>{u.display_name || u.username} <span className="text-xs text-slate-500">@{u.username}</span></span>
              {assigned.includes(u.id) ? <button className="btn-secondary py-1" onClick={() => assign(u.id, false)}>Remove</button> : <button className="btn-primary py-1" onClick={() => assign(u.id)}>Assign</button>}
            </li>
          ))}
          {!list(scorers.data).length && <li className="py-2 text-slate-500">No scorer accounts yet. A Super Admin can create them under Users.</li>}
        </ul>
      )}
      <p className="mt-3 text-xs text-slate-500">Each match has its own scorers. Tournament admins can also score their own matches.</p>
    </Modal>
  )
}

function Fixtures({ tournament }) {
  const matches = useApi('/matches/', { params: { tournament: tournament.id, page_size: 500, ordering: 'scheduled_at' } })
  const [gen, setGen] = useState(false)
  const [opts, setOpts] = useState({ start_date: tournament.start_date, matches_per_day: 4, first_start: '09:00', slot_hours: 3, double_round: false, replace: false })
  const [error, setError] = useState(null)
  const [msg, setMsg] = useState(null)
  const [edit, setEdit] = useState(null)
  const [assign, setAssign] = useState(null)
  const [del, setDel] = useState(null)
  const run = async (fn, ok) => {
    try {
      setError(null)
      const r = await fn()
      setMsg(ok(r.data))
      matches.reload()
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  return (
    <div className="space-y-4">
      <ErrorBox>{error}</ErrorBox>
      {msg && <p className="rounded-xl bg-pitch-50 p-3 text-sm text-pitch-800 dark:bg-pitch-900/40 dark:text-pitch-200">{msg}</p>}
      <div className="flex flex-wrap gap-2">
        {tournament.kind === 'league' && <button className="btn-primary" onClick={() => setGen(true)}><Wand2 className="h-4 w-4" /> Generate league fixtures</button>}
        <button className="btn-secondary" onClick={() => run(() => api.post(`/tournaments/${tournament.id}/generate_knockouts/`, {}), (d) => `Created ${d.created.length} knockout match(es).`)}>
          <Wand2 className="h-4 w-4" /> {tournament.kind === 'knockout' ? 'Generate next knockout round' : 'Generate semi-finals / final'}
        </button>
        <button className="btn-secondary" onClick={() => setEdit({})}><Plus className="h-4 w-4" /> Add match</button>
      </div>
      {matches.loading ? <Spinner /> : (
        <div className="card overflow-x-auto">
          <table className="table-basic">
            <thead><tr><th>#</th><th>Match</th><th>Stage</th><th>When / where</th><th>Status</th><th /></tr></thead>
            <tbody>
              {list(matches.data).map((m) => (
                <tr key={m.id}>
                  <td>{m.match_number}</td>
                  <td className="font-semibold"><Link to={`/matches/${m.id}`} className="hover:underline">{m.team_a.short_name} vs {m.team_b.short_name}</Link>{m.result && <div className="text-xs font-normal text-slate-500">{m.result}</div>}</td>
                  <td>{STAGE_LABEL[m.stage]}{m.group && ` ${m.group}`}</td>
                  <td className="text-xs">{fmtDateTime(m.scheduled_at)}<br />{m.ground}</td>
                  <td><StatusChip status={m.status} /></td>
                  <td className="whitespace-nowrap text-right">
                    <button className="btn-ghost px-2 py-1 text-xs" onClick={() => setAssign(m)}>Scorers</button>
                    <button className="btn-ghost px-2 py-1 text-xs" onClick={() => setEdit(m)}>Edit</button>
                    <Link className="btn-ghost px-2 py-1 text-xs" to={`/scorer/matches/${m.id}`}><ClipboardList className="h-3 w-3" /> Score</Link>
                    {m.status === 'scheduled' && <button className="btn-ghost p-1 text-red-600" onClick={() => setDel(m)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={gen} onClose={() => setGen(false)} title="Generate round-robin fixtures" footer={<button className="btn-primary" onClick={() => { setGen(false); run(() => api.post(`/tournaments/${tournament.id}/generate_fixtures/`, opts), (d) => `Created ${d.created} league matches.`) }}>Generate</button>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Start date"><input type="date" className="input" value={opts.start_date} onChange={(e) => setOpts({ ...opts, start_date: e.target.value })} /></Field>
          <Field label="Matches per day"><input type="number" min="1" className="input" value={opts.matches_per_day} onChange={(e) => setOpts({ ...opts, matches_per_day: Number(e.target.value) })} /></Field>
          <Field label="First match time"><input type="time" className="input" value={opts.first_start} onChange={(e) => setOpts({ ...opts, first_start: e.target.value })} /></Field>
          <Field label="Hours between slots"><input type="number" min="1" className="input" value={opts.slot_hours} onChange={(e) => setOpts({ ...opts, slot_hours: Number(e.target.value) })} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={opts.double_round} onChange={(e) => setOpts({ ...opts, double_round: e.target.checked })} /> Double round robin</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={opts.replace} onChange={(e) => setOpts({ ...opts, replace: e.target.checked })} /> Replace existing (only if none started)</label>
        </div>
        <p className="mt-3 text-xs text-slate-500">Teams in the same group play each other. Simultaneous slots use different grounds.</p>
      </Modal>
      {edit && <MatchForm tournament={tournament} initial={edit.id ? edit : null} onClose={(saved) => { setEdit(null); if (saved) matches.reload() }} />}
      {assign && <ScorerAssign match={assign} onClose={() => setAssign(null)} />}
      <ConfirmDialog open={!!del} danger title="Delete match?" message="This removes the scheduled match. This cannot be undone." confirmLabel="Delete" onCancel={() => setDel(null)} onConfirm={() => { const m = del; setDel(null); run(() => api.delete(`/matches/${m.id}/`), () => 'Match deleted.') }} />
    </div>
  )
}

export default function AdminTournamentManage() {
  const { id } = useParams()
  const { data, setData, loading, error } = useApi(`/tournaments/${id}/`)
  const [tab, setTab] = useState('fixtures')
  if (loading) return <Spinner />
  if (error) return <ErrorBox>{error}</ErrorBox>
  return (
    <div>
      <PageHeader title={data.name} subtitle={`${data.match_format} · ${data.ball_type} · ${data.kind}`} actions={<Link to={`/tournaments/${id}`} className="btn-secondary">Public page</Link>} />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: 'fixtures', label: 'Fixtures & scorers' }, { value: 'teams', label: 'Teams & squads' }, { value: 'rules', label: 'Playing rules' },
        { value: 'venues', label: 'Venues & admins' }, { value: 'details', label: 'Details' },
      ]} />
      {tab === 'fixtures' && <Fixtures tournament={data} />}
      {tab === 'teams' && <Registrations tournament={data} />}
      {tab === 'rules' && <RulesEditor tournament={data} onSaved={setData} />}
      {tab === 'venues' && <GroundsAdmins tournament={data} onSaved={setData} />}
      {tab === 'details' && <div className="card p-4"><TournamentForm initial={{ ...data, overs: '' }} onSaved={setData} /></div>}
    </div>
  )
}
