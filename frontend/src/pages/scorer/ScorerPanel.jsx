import { ArrowLeftRight, Edit3, ExternalLink, Flag, Pause, Play, RotateCcw, Settings2, UserMinus, UserPlus } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { errorMessage } from '../../api/client'
import { useMatchSocket } from '../../api/useMatchSocket'
import CelebrationOverlay from '../../components/CelebrationOverlay'
import { BallDot } from '../../components/Scorecard'
import { ConfirmDialog, ErrorBox, Field, Modal, Spinner, StatusChip, TeamBadge } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'

const uuid = () =>
  crypto.randomUUID
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
      })

const DISMISSALS = [
  ['bowled', 'Bowled'], ['caught', 'Caught'], ['caught_and_bowled', 'Caught & bowled'], ['lbw', 'LBW'],
  ['run_out', 'Run out'], ['stumped', 'Stumped'], ['hit_wicket', 'Hit wicket'],
  ['obstructing_field', 'Obstructing the field'], ['hit_ball_twice', 'Hit the ball twice'],
]
const ZONES = [
  ['', 'No direction'], ['fine_leg', 'Fine leg'], ['square_leg', 'Square leg'], ['mid_wicket', 'Mid-wicket'],
  ['mid_on', 'Mid-on'], ['straight', 'Straight'], ['mid_off', 'Mid-off'], ['cover', 'Cover'], ['point', 'Point'],
  ['third_man', 'Third man'],
]

function PlayerSelect({ label, players, value, onChange, exclude = [], placeholder = 'Select player' }) {
  return (
    <Field label={label}>
      <select className="input" value={value || ''} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
        <option value="">{placeholder}</option>
        {players.filter((p) => !exclude.includes(p.player_id)).map((p) => (
          <option key={p.player_id} value={p.player_id}>{p.name}</option>
        ))}
      </select>
    </Field>
  )
}

// ---------------------------------------------------------------------------
// Pre-match: playing XI, toss
// ---------------------------------------------------------------------------
function SquadPicker({ snap, team, onSaved, call }) {
  const [players, setPlayers] = useState(null)
  const existing = snap.squads[String(team.id)] || []
  const [selected, setSelected] = useState(existing.map((p) => p.player_id))
  const [captain, setCaptain] = useState(existing.find((p) => p.is_captain)?.player_id || null)
  const [keeper, setKeeper] = useState(existing.find((p) => p.is_wicket_keeper)?.player_id || null)
  const limit = snap.rules.players_per_side

  useEffect(() => {
    Promise.all([
      api.get(`/tournaments/${snap.tournament.id}/registrations/`),
      api.get('/players/', { params: { team: team.id, page_size: 200 } }),
    ]).then(([regs, ps]) => {
      const reg = regs.data.find((r) => r.team === team.id)
      const all = ps.data.results || ps.data
      setPlayers(reg && reg.players.length ? all.filter((p) => reg.players.includes(p.id)) : all)
    })
  }, [snap.tournament.id, team.id])

  const toggle = (id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length < limit ? [...s, id] : s))
  const save = () =>
    call('score/squad', { team: team.id, players: selected.map((id) => ({ player: id, is_captain: id === captain, is_wicket_keeper: id === keeper })) }).then(onSaved)

  if (!players) return <Spinner />
  return (
    <div className="card p-4">
      <h3 className="mb-1 flex items-center gap-2 font-bold"><TeamBadge team={team} size="sm" /> {team.name}</h3>
      <p className="mb-3 text-xs text-slate-500">Select up to {limit} players in batting order. {selected.length}/{limit} selected.</p>
      <div className="grid gap-1 sm:grid-cols-2">
        {players.map((p) => {
          const idx = selected.indexOf(p.id)
          return (
            <div key={p.id} className={`flex items-center gap-2 rounded-lg border px-2 py-1.5 text-sm ${idx >= 0 ? 'border-pitch-400 bg-pitch-50 dark:bg-pitch-900/30' : 'border-slate-200 dark:border-slate-700'}`}>
              <label className="flex flex-1 cursor-pointer items-center gap-2">
                <input type="checkbox" checked={idx >= 0} onChange={() => toggle(p.id)} className="accent-pitch-600" />
                <span className="w-5 text-xs text-slate-500">{idx >= 0 ? idx + 1 : ''}</span>
                <span className="truncate">{p.full_name}</span>
              </label>
              {idx >= 0 && (
                <>
                  <button type="button" className={`chip ${captain === p.id ? 'bg-amber-500 text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => setCaptain(p.id)}>C</button>
                  <button type="button" className={`chip ${keeper === p.id ? 'bg-sky-600 text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => setKeeper(p.id)}>WK</button>
                </>
              )}
            </div>
          )
        })}
      </div>
      <button className="btn-primary mt-3" disabled={selected.length < 2} onClick={save}>Save playing side</button>
    </div>
  )
}

function PreMatch({ snap, call }) {
  const [winner, setWinner] = useState(snap.toss?.winner || '')
  const [decision, setDecision] = useState(snap.toss?.decision || 'bat')
  const squadsReady = [snap.team_a, snap.team_b].every((t) => (snap.squads[String(t.id)] || []).length >= 2)
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <SquadPicker snap={snap} team={snap.team_a} call={call} />
        <SquadPicker snap={snap} team={snap.team_b} call={call} />
      </div>
      <div className="card p-4">
        <h3 className="mb-3 font-bold">Toss</h3>
        {!squadsReady && <p className="mb-2 text-sm text-amber-700">Save both playing sides first.</p>}
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Toss won by">
            <select className="input" value={winner} onChange={(e) => setWinner(Number(e.target.value))}>
              <option value="">Select team</option>
              <option value={snap.team_a.id}>{snap.team_a.name}</option>
              <option value={snap.team_b.id}>{snap.team_b.name}</option>
            </select>
          </Field>
          <Field label="Elected to">
            <select className="input" value={decision} onChange={(e) => setDecision(e.target.value)}>
              <option value="bat">Bat</option>
              <option value="bowl">Bowl</option>
            </select>
          </Field>
          <div className="flex items-end">
            <button className="btn-primary w-full" disabled={!winner || !squadsReady} onClick={() => call('score/toss', { winner, decision })}>Record toss</button>
          </div>
        </div>
        {snap.toss && <p className="mt-2 text-sm text-pitch-700 dark:text-pitch-400">{snap.toss.text}</p>}
      </div>
    </div>
  )
}

function nextBatting(snap) {
  const inns = snap.innings
  if (!inns.length) {
    if (!snap.toss) return null
    const tossWinnerBats = snap.toss.decision === 'bat'
    const winner = snap.toss.winner
    return tossWinnerBats ? winner : winner === snap.team_a.id ? snap.team_b.id : snap.team_a.id
  }
  const last = inns[inns.length - 1]
  if (inns.length % 2 === 1) return last.bowling_team.id
  return last.batting_team.id // super over after a tie: the side that batted second bats first
}

function StartInnings({ snap, call }) {
  const batId = nextBatting(snap)
  const bowlId = batId === snap.team_a.id ? snap.team_b.id : snap.team_a.id
  const bat = snap.squads[String(batId)] || []
  const bowl = snap.squads[String(bowlId)] || []
  const [s, setS] = useState(null)
  const [ns, setNs] = useState(null)
  const [b, setB] = useState(null)
  const team = batId === snap.team_a.id ? snap.team_a : snap.team_b
  const superOver = snap.innings.length >= 2
  return (
    <div className="card mx-auto max-w-xl space-y-3 p-5">
      <h3 className="text-lg font-bold">Start {superOver ? 'super over' : `innings ${snap.innings.length + 1}`}: {team.name} batting</h3>
      <PlayerSelect label="Striker" players={bat} value={s} onChange={setS} exclude={[ns]} />
      <PlayerSelect label="Non-striker" players={bat} value={ns} onChange={setNs} exclude={[s]} />
      <PlayerSelect label="Opening bowler" players={bowl} value={b} onChange={setB} />
      <button className="btn-primary w-full" disabled={!s || !b || (!ns && bat.length > 1)} onClick={() => call('score/start-innings', { striker: s, non_striker: ns, bowler: b })}>
        Start innings
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Live scoring dialogs
// ---------------------------------------------------------------------------
function ExtraDialog({ kind, onClose, onSubmit }) {
  const [runs, setRuns] = useState(kind === 'bye' || kind === 'legbye' ? 1 : 0)
  const [nbType, setNbType] = useState('bat')
  const [boundary, setBoundary] = useState(false)
  const titles = { wide: 'Wide', noball: 'No-ball', bye: 'Byes', legbye: 'Leg byes', penalty: 'Penalty runs' }
  const submit = () => {
    if (kind === 'wide') onSubmit({ extra_type: 'wide', extra_runs: runs, boundary: boundary && runs === 4 })
    else if (kind === 'noball') {
      if (nbType === 'bat') onSubmit({ extra_type: 'noball', runs_bat: runs, noball_runs_type: 'bat', boundary: [4, 6].includes(runs) ? boundary || undefined : false })
      else onSubmit({ extra_type: 'noball', noball_runs_type: nbType, extra_runs: runs, boundary: boundary && runs === 4 })
    } else if (kind === 'penalty') onSubmit({ extra_type: 'penalty', penalty_runs: runs || 5 })
    else onSubmit({ extra_type: kind, extra_runs: runs, boundary: boundary && runs === 4 })
  }
  const options = kind === 'penalty' ? [5] : kind === 'noball' && nbType === 'bat' ? [0, 1, 2, 3, 4, 6] : kind === 'bye' || kind === 'legbye' ? [1, 2, 3, 4] : [0, 1, 2, 3, 4]
  return (
    <Modal open onClose={onClose} title={titles[kind]} footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" onClick={submit}>Record</button></>}>
      {kind === 'noball' && (
        <div className="mb-4 flex gap-2">
          {[['bat', 'Off the bat'], ['bye', 'Byes'], ['legbye', 'Leg byes']].map(([v, l]) => (
            <button key={v} className={nbType === v ? 'btn-primary' : 'btn-secondary'} onClick={() => { setNbType(v); setRuns(0) }}>{l}</button>
          ))}
        </div>
      )}
      <p className="label">{kind === 'wide' ? 'Extra runs run (in addition to the wide)' : kind === 'penalty' ? 'Penalty awarded to batting side' : 'Runs'}</p>
      <div className="grid grid-cols-6 gap-2">
        {options.map((r) => (
          <button key={r} className={`h-14 rounded-xl text-xl font-black ${runs === r ? 'bg-pitch-600 text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => setRuns(r)}>{r}</button>
        ))}
      </div>
      {kind !== 'penalty' && [4, 6].includes(runs) && (
        <label className="mt-4 flex items-center gap-2 text-sm font-semibold">
          <input type="checkbox" className="h-5 w-5 accent-pitch-600" checked={boundary} onChange={(e) => setBoundary(e.target.checked)} /> Reached the boundary
        </label>
      )}
    </Modal>
  )
}

function WicketDialog({ snap, onClose, onSubmit }) {
  const c = snap.current
  const fielders = snap.squads[String(c.bowling_team.id)] || []
  const [kind, setKind] = useState('bowled')
  const [out, setOut] = useState(c.striker?.player_id)
  const [fielder, setFielder] = useState(null)
  const [runs, setRuns] = useState(0)
  const [crossed, setCrossed] = useState(false)
  const [delivery, setDelivery] = useState('legal')
  const disallowed = snap.rules.disallowed_dismissals || []
  const needsFielder = ['caught', 'stumped'].includes(kind)
  const allowRuns = ['run_out', 'obstructing_field'].includes(kind)
  const submit = () => {
    const payload = { wicket: { kind, player_out: out, fielder: kind === 'caught_and_bowled' ? null : fielder } }
    if (delivery === 'wide') Object.assign(payload, { extra_type: 'wide', extra_runs: allowRuns ? runs : 0 })
    else if (delivery === 'noball') Object.assign(payload, { extra_type: 'noball', runs_bat: allowRuns ? runs : 0 })
    else payload.runs_bat = allowRuns ? runs : 0
    if (kind === 'run_out') payload.batters_crossed = crossed
    onSubmit(payload)
  }
  return (
    <Modal open onClose={onClose} title="Wicket" footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-danger" disabled={needsFielder && !fielder} onClick={submit}>Record wicket</button></>}>
      <div className="space-y-3">
        <Field label="How out">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {DISMISSALS.filter(([k]) => !disallowed.includes(k)).map(([k, l]) => (
              <button key={k} className={`rounded-xl px-2 py-2 text-sm font-semibold ${kind === k ? 'bg-ball text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => { setKind(k); if (!['run_out', 'obstructing_field'].includes(k)) setOut(c.striker?.player_id) }}>{l}</button>
            ))}
          </div>
        </Field>
        {['run_out', 'obstructing_field'].includes(kind) && (
          <Field label="Batter out">
            <div className="flex gap-2">
              {[c.striker, c.non_striker].filter(Boolean).map((b) => (
                <button key={b.player_id} className={out === b.player_id ? 'btn-primary' : 'btn-secondary'} onClick={() => setOut(b.player_id)}>{b.name}</button>
              ))}
            </div>
          </Field>
        )}
        {(needsFielder || kind === 'run_out') && (
          <PlayerSelect label={kind === 'stumped' ? 'Wicket-keeper' : 'Fielder'} players={fielders} value={fielder} onChange={setFielder} placeholder={kind === 'run_out' ? 'Fielder (optional)' : 'Select fielder'} />
        )}
        {['run_out', 'stumped', 'hit_wicket', 'obstructing_field', 'hit_ball_twice'].includes(kind) && (
          <Field label="Delivery">
            <div className="flex gap-2">
              {[['legal', 'Legal ball'], ['wide', 'Wide'], ['noball', 'No-ball']].map(([v, l]) => (
                <button key={v} className={delivery === v ? 'btn-primary' : 'btn-secondary'} onClick={() => setDelivery(v)}>{l}</button>
              ))}
            </div>
          </Field>
        )}
        {allowRuns && (
          <>
            <Field label="Runs completed before the wicket">
              <div className="flex gap-2">{[0, 1, 2, 3].map((r) => <button key={r} className={`h-11 w-11 rounded-xl font-bold ${runs === r ? 'bg-pitch-600 text-white' : 'bg-slate-100 dark:bg-slate-800'}`} onClick={() => setRuns(r)}>{r}</button>)}</div>
            </Field>
            {kind === 'run_out' && (
              <label className="flex items-center gap-2 text-sm font-semibold">
                <input type="checkbox" className="h-5 w-5 accent-pitch-600" checked={crossed} onChange={(e) => setCrossed(e.target.checked)} /> Batters had crossed on the run being attempted
              </label>
            )}
          </>
        )}
        {c.free_hit && <p className="rounded-lg bg-amber-100 p-2 text-sm text-amber-900">Free hit: only run out, obstructing the field or hitting the ball twice are allowed.</p>}
      </div>
    </Modal>
  )
}

function BatterDialog({ snap, call, onClose }) {
  const c = snap.current
  const inn = snap.innings.find((i) => i.id === c.innings_id)
  const squad = snap.squads[String(c.batting_team.id)] || []
  const outIds = inn.batting.filter((b) => b.is_out).map((b) => b.player_id)
  const busy = [c.striker?.player_id, c.non_striker?.player_id].filter(Boolean)
  const available = squad.filter((p) => !outIds.includes(p.player_id) && !busy.includes(p.player_id))
  const end = !c.striker ? 'striker' : 'non_striker'
  const [player, setPlayer] = useState(available[0]?.player_id || null)
  return (
    <Modal open onClose={onClose} title={`New batter (${end === 'striker' ? 'on strike' : 'non-striker'})`} footer={<button className="btn-primary" disabled={!player} onClick={() => call('score/batter', { player, end }).then(onClose)}>Send in</button>}>
      {available.length ? <PlayerSelect label="Batter" players={available} value={player} onChange={setPlayer} /> : <p className="text-sm">No batters left. End the innings.</p>}
      <p className="mt-2 text-xs text-slate-500">Retired-hurt batters can return and are included in this list.</p>
    </Modal>
  )
}

function BowlerDialog({ snap, call, onClose, midOver }) {
  const c = snap.current
  const inn = snap.innings.find((i) => i.id === c.innings_id)
  const squad = snap.squads[String(c.bowling_team.id)] || []
  const bpo = snap.rules.balls_per_over
  const limit = snap.rules.max_overs_per_bowler
  const lines = Object.fromEntries(inn.bowling.map((b) => [b.player_id, b]))
  const [player, setPlayer] = useState(null)
  const [reason, setReason] = useState('')
  const options = squad.map((p) => {
    const line = lines[p.player_id]
    const balls = line?.balls || 0
    const blocked = (!snap.rules.consecutive_overs_allowed && p.player_id === c.last_over_bowler) || (limit && !c.is_super_over && balls >= limit * bpo) || (midOver && p.player_id === c.bowler?.player_id)
    return { ...p, blocked, figures: line ? `${line.overs}-${line.maidens}-${line.runs}-${line.wickets}` : '' }
  })
  return (
    <Modal open onClose={onClose} title={midOver ? 'Change bowler mid-over' : 'Bowler for the next over'} footer={<button className="btn-primary" disabled={!player || (midOver && !reason)} onClick={() => call('score/bowler', { bowler: player, mid_over: !!midOver, reason }).then(onClose)}>Confirm</button>}>
      <div className="grid gap-2 sm:grid-cols-2">
        {options.map((p) => (
          <button key={p.player_id} disabled={p.blocked} onClick={() => setPlayer(p.player_id)} className={`flex items-center justify-between rounded-xl border px-3 py-2 text-left text-sm disabled:opacity-40 ${player === p.player_id ? 'border-pitch-500 bg-pitch-50 dark:bg-pitch-900/40' : 'border-slate-200 dark:border-slate-700'}`}>
            <span className="font-semibold">{p.name}</span><span className="text-xs tabular-nums text-slate-500">{p.figures}</span>
          </button>
        ))}
      </div>
      {midOver && <Field label="Reason (injury, suspension…)"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>}
      <p className="mt-2 text-xs text-slate-500">Greyed out: bowled the previous over{limit ? ` or reached ${limit} overs` : ''}.</p>
    </Modal>
  )
}

function EditBallDialog({ matchId, snap, call, onClose }) {
  const [rows, setRows] = useState(null)
  const [sel, setSel] = useState(null)
  const [form, setForm] = useState(null)
  const c = snap.current
  useEffect(() => {
    api.get(`/matches/${matchId}/deliveries/`).then((r) => setRows(r.data.filter((d) => d.innings === c.innings_number).slice(-18).reverse()))
  }, [matchId, c.innings_number])
  const pick = (d) => {
    setSel(d)
    const type = d.wides ? 'wide' : d.noballs ? 'noball' : d.byes ? 'bye' : d.legbyes ? 'legbye' : d.is_penalty_only ? 'penalty' : ''
    setForm({
      extra_type: type,
      runs_bat: d.runs_bat,
      extra_runs: type === 'wide' ? d.wides - snap.rules.wide_runs : d.byes || d.legbyes || 0,
      noball_runs_type: d.noballs ? (d.byes ? 'bye' : d.legbyes ? 'legbye' : 'bat') : 'bat',
      boundary: d.is_boundary,
      wicket: d.wicket ? d.wicket.kind : '',
      player_out: d.wicket?.player_out || d.striker,
      fielder: d.wicket?.fielder || null,
      reason: '',
    })
  }
  const save = () => {
    const payload = {
      extra_type: form.extra_type, runs_bat: Number(form.runs_bat), extra_runs: Number(form.extra_runs),
      noball_runs_type: form.noball_runs_type, boundary: form.boundary, reason: form.reason,
      wicket: form.wicket ? { kind: form.wicket, player_out: form.player_out, fielder: form.fielder } : null,
    }
    call(`score/edit/${sel.id}`, payload).then(onClose)
  }
  const fielders = snap.squads[String(c.bowling_team.id)] || []
  const names = Object.fromEntries(Object.values(snap.squads).flat().map((p) => [p.player_id, p.name]))
  const label = (d) => `${d.over_number}.${d.ball_in_over} · ${names[d.bowler] || ''} to ${names[d.striker] || ''}`
  return (
    <Modal open onClose={onClose} wide title={sel ? `Edit ball ${sel.over_number}.${sel.ball_in_over}` : 'Edit a previous ball'} footer={sel && <><button className="btn-secondary" onClick={() => setSel(null)}>Back</button><button className="btn-primary" onClick={save} disabled={!form.reason}>Save correction</button></>}>
      {!rows ? <Spinner /> : !sel ? (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {rows.map((d) => (
            <li key={d.id}><button className="flex w-full items-center justify-between py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => pick(d)}>
              <span>{label(d)}</span>
              <span className="font-bold">{d.wicket ? 'W ' : ''}{d.runs_bat + d.wides + d.noballs + d.byes + d.legbyes + d.penalty_runs} runs</span>
            </button></li>
          ))}
        </ul>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Type">
            <select className="input" value={form.extra_type} onChange={(e) => setForm({ ...form, extra_type: e.target.value })}>
              <option value="">Legal ball</option><option value="wide">Wide</option><option value="noball">No-ball</option>
              <option value="bye">Byes</option><option value="legbye">Leg byes</option>
            </select>
          </Field>
          {['', 'noball'].includes(form.extra_type) && form.noball_runs_type === 'bat' && (
            <Field label="Runs off the bat"><input type="number" min="0" max="7" className="input" value={form.runs_bat} onChange={(e) => setForm({ ...form, runs_bat: e.target.value })} /></Field>
          )}
          {form.extra_type === 'noball' && (
            <Field label="No-ball runs were">
              <select className="input" value={form.noball_runs_type} onChange={(e) => setForm({ ...form, noball_runs_type: e.target.value, runs_bat: 0 })}>
                <option value="bat">Off the bat</option><option value="bye">Byes</option><option value="legbye">Leg byes</option>
              </select>
            </Field>
          )}
          {(['wide', 'bye', 'legbye'].includes(form.extra_type) || (form.extra_type === 'noball' && form.noball_runs_type !== 'bat')) && (
            <Field label="Extra runs"><input type="number" min="0" max="7" className="input" value={form.extra_runs} onChange={(e) => setForm({ ...form, extra_runs: e.target.value })} /></Field>
          )}
          <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" className="h-5 w-5 accent-pitch-600" checked={!!form.boundary} onChange={(e) => setForm({ ...form, boundary: e.target.checked })} /> Boundary</label>
          <Field label="Wicket">
            <select className="input" value={form.wicket} onChange={(e) => setForm({ ...form, wicket: e.target.value })}>
              <option value="">No wicket</option>
              {DISMISSALS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </Field>
          {form.wicket && (
            <>
              <Field label="Batter out">
                <select className="input" value={form.player_out} onChange={(e) => setForm({ ...form, player_out: Number(e.target.value) })}>
                  <option value={sel.striker}>{names[sel.striker]}</option>
                  {sel.non_striker && <option value={sel.non_striker}>{names[sel.non_striker]}</option>}
                </select>
              </Field>
              <PlayerSelect label="Fielder" players={fielders} value={form.fielder} onChange={(v) => setForm({ ...form, fielder: v })} placeholder="None" />
            </>
          )}
          <div className="sm:col-span-2"><Field label="Reason for correction (required)"><input className="input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field></div>
          <p className="text-xs text-slate-500 sm:col-span-2">The innings is replayed after the edit. Corrections that make the scorebook inconsistent (e.g. a batter out who faced later balls) are rejected. Every edit is saved in the correction history.</p>
        </div>
      )}
    </Modal>
  )
}

function FinishDialog({ snap, call, onClose }) {
  const [kind, setKind] = useState('')
  const [winner, setWinner] = useState(null)
  const [pom, setPom] = useState(null)
  const everyone = [...(snap.squads[String(snap.team_a.id)] || []), ...(snap.squads[String(snap.team_b.id)] || [])]
  return (
    <Modal open onClose={onClose} title="Finish match" footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-danger" onClick={() => call('score/finish', { kind, winner, player_of_match: pom }).then(onClose)} disabled={kind === 'awarded' && !winner}>Finish match</button></>}>
      <div className="space-y-3">
        <Field label="Result">
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">Use the scored result {snap.result ? `(${snap.result.summary})` : ''}</option>
            <option value="tie">Tie (no super over)</option>
            <option value="no_result">No result</option>
            <option value="abandoned">Abandoned</option>
            <option value="awarded">Awarded / forfeit</option>
          </select>
        </Field>
        {kind === 'awarded' && (
          <Field label="Awarded to">
            <select className="input" value={winner || ''} onChange={(e) => setWinner(Number(e.target.value))}>
              <option value="">Select team</option><option value={snap.team_a.id}>{snap.team_a.name}</option><option value={snap.team_b.id}>{snap.team_b.name}</option>
            </select>
          </Field>
        )}
        <PlayerSelect label="Player of the match (optional)" players={everyone} value={pom} onChange={setPom} placeholder="None" />
      </div>
    </Modal>
  )
}

function ReviseDialog({ snap, call, onClose }) {
  const c = snap.current
  const inn = snap.innings.find((i) => i.id === c?.innings_id) || snap.innings[snap.innings.length - 1]
  const [overs, setOvers] = useState(inn?.max_overs || snap.rules.overs_per_innings)
  const [target, setTarget] = useState(inn?.target || '')
  const [reason, setReason] = useState('')
  return (
    <Modal open onClose={onClose} title="Revise overs / target (interruption)" footer={<button className="btn-primary" disabled={!reason} onClick={() => call('score/revise', { max_overs: Number(overs), target: inn.number % 2 === 0 && target ? Number(target) : null, reason }).then(onClose)}>Save</button>}>
      <div className="space-y-3">
        <Field label="Overs for this innings"><input type="number" min="1" className="input" value={overs} onChange={(e) => setOvers(e.target.value)} /></Field>
        {inn.number % 2 === 0 && <Field label="Revised target (from the match officials)" hint="No DLS calculation is done automatically."><input type="number" min="1" className="input" value={target} onChange={(e) => setTarget(e.target.value)} /></Field>}
        <Field label="Reason"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Rain delay, bad light…" /></Field>
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------
export default function ScorerPanel() {
  const { id } = useParams()
  const { user } = useAuth()
  const [snap, setSnap] = useState(null)
  const [perm, setPerm] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [dialog, setDialog] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const [zone, setZone] = useState('')
  const [event, setEvent] = useState(null)

  const { status, reset } = useMatchSocket(id, (s, ev) => {
    setSnap(s)
    if (ev?.highlight) setEvent(ev)
  })

  const refresh = useCallback(async () => {
    const r = await api.get(`/matches/${id}/live/`)
    setSnap(r.data)
    reset(r.data.version)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    refresh().catch((e) => setError(errorMessage(e)))
    api.get(`/matches/${id}/permissions_info/`).then((r) => setPerm(r.data)).catch(() => setPerm({ can_score: false }))
  }, [id, refresh, user])

  const call = useCallback(async (path, body = {}) => {
    setBusy(true)
    setError(null)
    try {
      const r = await api.post(`/matches/${id}/${path}/`, body)
      if (r.data?.snapshot) {
        setSnap(r.data.snapshot)
        reset(r.data.snapshot.version)
      }
      if (r.data?.duplicate) setNotice('That ball was already recorded (duplicate tap ignored).')
      return r.data
    } catch (e) {
      if (e.response?.status === 409) {
        setNotice('Another scorer updated this match. The latest score has been loaded — check it before continuing.')
        await refresh()
      } else setError(errorMessage(e))
      throw e
    } finally {
      setBusy(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, refresh])

  const safe = (p) => p.catch(() => {})
  const c = snap?.current
  const ball = (payload) => {
    if (busy) return
    setDialog(null)
    safe(call('score/delivery', { client_event_id: uuid(), expected_sequence: (c?.last_sequence || 0) + 1, shot_zone: zone, ...payload }).then(() => setZone('')))
  }

  // Prompt for the next batter / bowler automatically.
  const needs = useMemo(() => {
    if (!c || !c.in_progress || snap.status !== 'live') return null
    if (c.need_batter) return 'batter'
    if (c.need_bowler) return 'bowler'
    return null
  }, [c, snap?.status])

  if (error && !snap) return <ErrorBox>{error}</ErrorBox>
  if (!snap || !perm) return <Spinner />
  if (!perm.can_score) return <ErrorBox>You are not assigned to score this match.</ErrorBox>

  const live = snap.status === 'live' && c?.in_progress
  const paused = snap.status === 'paused'
  const finished = ['completed', 'abandoned'].includes(snap.status)
  const preMatch = !snap.innings.length && ['scheduled', 'toss'].includes(snap.status)
  const canStartInnings = !finished && !paused && !c?.in_progress && snap.toss && (snap.status === 'toss' || snap.status === 'innings_break')

  return (
    <div className="mx-auto max-w-5xl pb-24">
      <CelebrationOverlay event={event} />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <StatusChip status={snap.status} />
        <h1 className="text-lg font-bold">{snap.team_a.short_name} vs {snap.team_b.short_name}</h1>
        <span className="text-sm text-slate-500">{snap.tournament.name} · {snap.ground}</span>
        <span className={`ml-auto text-xs ${status === 'open' ? 'text-pitch-600' : 'text-amber-600'}`}>{status === 'open' ? '● Live sync' : '○ Reconnecting…'}</span>
        <Link to={`/matches/${id}`} className="btn-ghost px-2 py-1 text-xs" target="_blank"><ExternalLink className="h-4 w-4" /> Public view</Link>
      </div>
      {error && <div className="mb-3"><ErrorBox>{error}</ErrorBox></div>}
      {notice && <div className="mb-3 rounded-xl bg-amber-100 p-3 text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100" role="status">{notice} <button className="ml-2 font-semibold underline" onClick={() => setNotice(null)}>OK</button></div>}

      {preMatch && <PreMatch snap={snap} call={(p, b) => call(p, b).catch(() => {})} />}
      {preMatch && snap.toss && <div className="mt-4"><StartInnings snap={snap} call={(p, b) => safe(call(p, b))} /></div>}
      {!preMatch && canStartInnings && !snap.result && <StartInnings key={snap.innings.length} snap={snap} call={(p, b) => safe(call(p, b))} />}
      {snap.result && <div className="card mb-4 p-4 text-center text-lg font-bold text-pitch-700 dark:text-pitch-400">{snap.result.summary}{snap.result.player_of_match_name && <div className="text-sm font-normal text-slate-500">Player of the match: {snap.result.player_of_match_name}</div>}</div>}
      {paused && (
        <div className="card mb-4 flex flex-wrap items-center gap-3 p-4">
          <Pause className="h-5 w-5 text-amber-600" /> <span className="font-semibold">Match interrupted: {snap.clock.pause_reason}</span>
          <button className="btn-primary ml-auto" disabled={busy} onClick={() => safe(call('score/resume'))}><Play className="h-4 w-4" /> Resume</button>
        </div>
      )}

      {c && !preMatch && (
        <>
          <div className="card mb-3 p-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase text-slate-500">{c.batting_team.name} {c.is_super_over && '· Super over'}</div>
                <div className="text-4xl font-black tabular-nums">{c.score} <span className="text-lg font-semibold text-slate-500">({c.overs}/{snap.innings.find((i) => i.id === c.innings_id)?.max_overs})</span></div>
              </div>
              <div className="text-right text-sm">
                <div>CRR <b>{c.run_rate.toFixed(2)}</b>{c.required_run_rate != null && <> · RRR <b>{c.required_run_rate.toFixed(2)}</b></>}</div>
                {c.equation && <div className="font-semibold text-amber-700 dark:text-amber-400">{c.equation}</div>}
                {c.free_hit && <span className="chip mt-1 animate-pulse bg-gold text-slate-900">FREE HIT</span>}
                {c.powerplay?.active && <span className="chip ml-1 mt-1 bg-sky-100 text-sky-800">Powerplay {c.powerplay.number}</span>}
              </div>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {[c.striker, c.non_striker].map((b, i) => (
                <div key={i} className={`rounded-xl p-2 text-sm ${i === 0 ? 'bg-pitch-50 ring-2 ring-pitch-400 dark:bg-pitch-900/40' : 'bg-slate-50 dark:bg-slate-800'}`}>
                  <div className="text-xs text-slate-500">{i === 0 ? 'Striker' : 'Non-striker'}</div>
                  {b ? <div className="font-bold">{b.name} <span className="tabular-nums">{b.runs}({b.balls})</span></div> : <button className="font-semibold text-pitch-700 underline" onClick={() => setDialog('batter')}>Select batter</button>}
                </div>
              ))}
              <div className="rounded-xl bg-slate-50 p-2 text-sm dark:bg-slate-800">
                <div className="text-xs text-slate-500">Bowler</div>
                {c.bowler ? <div className="font-bold">{c.bowler.name} <span className="tabular-nums">{c.bowler.overs}-{c.bowler.maidens}-{c.bowler.runs}-{c.bowler.wickets}</span></div> : <button className="font-semibold text-pitch-700 underline" onClick={() => setDialog('bowler')}>Select bowler</button>}
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-xs text-slate-500">This over:</span>
              {(c.this_over?.balls || []).map((b, i) => <BallDot key={i} label={b} />)}
              <span className="ml-auto text-xs text-slate-500">Extras {snap.innings.find((i) => i.id === c.innings_id)?.extras.total} · Wkts {c.score.split('/')[1]}</span>
            </div>
          </div>

          {live && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <label htmlFor="zone" className="text-xs font-semibold text-slate-500">Shot direction</label>
                <select id="zone" className="input w-auto py-1.5" value={zone} onChange={(e) => setZone(e.target.value)}>
                  {ZONES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-8" aria-label="Runs">
                {[0, 1, 2, 3].map((r) => (
                  <button key={r} disabled={busy || !!needs} onClick={() => ball({ runs_bat: r, boundary: false })} className="h-16 rounded-2xl bg-white text-2xl font-black shadow-sm ring-1 ring-slate-200 transition active:scale-95 disabled:opacity-40 dark:bg-slate-800 dark:ring-slate-700">{r === 0 ? '•' : r}</button>
                ))}
                <button disabled={busy || !!needs} onClick={() => ball({ runs_bat: 4, boundary: true })} className="h-16 rounded-2xl bg-pitch-600 text-2xl font-black text-white shadow transition active:scale-95 disabled:opacity-40">4</button>
                <button disabled={busy || !!needs} onClick={() => ball({ runs_bat: 6, boundary: true })} className="h-16 rounded-2xl bg-violet-600 text-2xl font-black text-white shadow transition active:scale-95 disabled:opacity-40">6</button>
                <button disabled={busy || !!needs} onClick={() => ball({ runs_bat: 5, boundary: false })} className="h-16 rounded-2xl bg-white text-xl font-black shadow-sm ring-1 ring-slate-200 active:scale-95 disabled:opacity-40 dark:bg-slate-800 dark:ring-slate-700">5</button>
                <button disabled={busy || !!needs} onClick={() => setDialog('wicket')} className="h-16 rounded-2xl bg-ball text-xl font-black text-white shadow active:scale-95 disabled:opacity-40">OUT</button>
              </div>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
                {[['wide', 'Wide'], ['noball', 'No-ball'], ['bye', 'Bye'], ['legbye', 'Leg bye'], ['penalty', 'Penalty']].map(([k, l]) => (
                  <button key={k} disabled={busy || !!needs} onClick={() => (k === 'wide' ? ball({ extra_type: 'wide', extra_runs: 0 }) : setDialog(k))} className="h-12 rounded-xl bg-amber-100 font-bold text-amber-900 active:scale-95 disabled:opacity-40 dark:bg-amber-500/20 dark:text-amber-200">{l}</button>
                ))}
                <button disabled={busy || !!needs} onClick={() => setDialog('wide')} className="h-12 rounded-xl bg-amber-50 text-sm font-semibold text-amber-900 active:scale-95 disabled:opacity-40 dark:bg-amber-500/10 dark:text-amber-200">Wide + runs</button>
              </div>
            </div>
          )}

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <button className="btn-secondary" disabled={busy || !snap.innings.length || paused} onClick={() => setConfirm({ title: 'Undo last ball?', message: 'The last recorded action will be removed and the innings replayed. This is saved in the correction history.', action: () => call('score/undo', { reason: 'Undo by scorer', expected_sequence: snap.innings[snap.innings.length - 1].last_sequence }) })}><RotateCcw className="h-4 w-4" /> Undo</button>
            <button className="btn-secondary" disabled={busy || !c?.in_progress || paused} onClick={() => setDialog('edit')}><Edit3 className="h-4 w-4" /> Edit ball</button>
            <button className="btn-secondary" disabled={busy || !live} onClick={() => setConfirm({ title: 'Swap strike?', message: 'Use this only to correct who is on strike.', action: () => call('score/swap-strike') })}><ArrowLeftRight className="h-4 w-4" /> Swap strike</button>
            <button className="btn-secondary" disabled={busy || !live} onClick={() => setDialog('bowler-mid')}><UserPlus className="h-4 w-4" /> Change bowler</button>
            <button className="btn-secondary" disabled={busy || !live} onClick={() => setDialog('retire')}><UserMinus className="h-4 w-4" /> Retire batter</button>
            {!paused && !finished && <button className="btn-secondary" disabled={busy} onClick={() => setDialog('pause')}><Pause className="h-4 w-4" /> Pause</button>}
            <button className="btn-secondary" disabled={busy || finished} onClick={() => setDialog('revise')}><Settings2 className="h-4 w-4" /> Revise overs</button>
            <button className="btn-secondary" disabled={busy || !live} onClick={() => setConfirm({ title: 'End this innings?', message: 'Use this for a declaration or when no batters are left. The next innings can then be started.', danger: true, action: () => call('score/end-innings', { reason: 'declared' }) })}><Flag className="h-4 w-4" /> End innings</button>
            <button className="btn-danger col-span-2 sm:col-span-4" disabled={busy || (finished && !!snap.result?.player_of_match)} onClick={() => setDialog('finish')}>Finish match / submit result</button>
          </div>
        </>
      )}

      {dialog && ['wide', 'noball', 'bye', 'legbye', 'penalty'].includes(dialog) && <ExtraDialog kind={dialog} onClose={() => setDialog(null)} onSubmit={ball} />}
      {dialog === 'wicket' && <WicketDialog snap={snap} onClose={() => setDialog(null)} onSubmit={ball} />}
      {(dialog === 'batter' || (!dialog && needs === 'batter')) && <BatterDialog snap={snap} call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      {(dialog === 'bowler' || (!dialog && needs === 'bowler')) && <BowlerDialog snap={snap} call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      {dialog === 'bowler-mid' && <BowlerDialog snap={snap} midOver={!!c.this_over?.balls?.length} call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      {dialog === 'edit' && <EditBallDialog matchId={id} snap={snap} call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      {dialog === 'finish' && <FinishDialog snap={snap} call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      {dialog === 'revise' && <ReviseDialog snap={snap} call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      {dialog === 'pause' && <PauseDialog call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      {dialog === 'retire' && <RetireDialog snap={snap} call={(p, b) => call(p, b)} onClose={() => setDialog(null)} />}
      <ConfirmDialog
        open={!!confirm}
        title={confirm?.title}
        message={confirm?.message}
        danger={confirm?.danger}
        busy={busy}
        confirmLabel="Yes, continue"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          const a = confirm.action
          setConfirm(null)
          safe(a())
        }}
      />
    </div>
  )
}

function PauseDialog({ call, onClose }) {
  const [reason, setReason] = useState('Rain')
  return (
    <Modal open onClose={onClose} title="Pause match" footer={<button className="btn-primary" onClick={() => call('score/pause', { reason }).then(onClose).catch(() => {})}>Pause</button>}>
      <Field label="Reason"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
      <p className="mt-2 text-xs text-slate-500">Scoring is locked while paused. Paused time is excluded from the match clock.</p>
    </Modal>
  )
}

function RetireDialog({ snap, call, onClose }) {
  const c = snap.current
  const [player, setPlayer] = useState(c.striker?.player_id)
  const [kind, setKind] = useState('retired_hurt')
  return (
    <Modal open onClose={onClose} title="Retire batter" footer={<button className="btn-danger" onClick={() => call('score/retire', { player, kind }).then(onClose).catch(() => {})}>Confirm</button>}>
      <div className="space-y-3">
        <div className="flex gap-2">
          {[c.striker, c.non_striker].filter(Boolean).map((b) => (
            <button key={b.player_id} className={player === b.player_id ? 'btn-primary' : 'btn-secondary'} onClick={() => setPlayer(b.player_id)}>{b.name}</button>
          ))}
        </div>
        <Field label="Type">
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="retired_hurt">Retired hurt (not out, may return)</option>
            <option value="retired_out">Retired out (counts as a wicket)</option>
          </select>
        </Field>
      </div>
    </Modal>
  )
}
