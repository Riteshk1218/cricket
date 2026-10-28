import { Plus, Users } from 'lucide-react'
import { useState } from 'react'
import api, { errorMessage, list } from '../../api/client'
import { ErrorBox, Field, Modal, PageHeader, Spinner } from '../../components/ui'
import { useApi } from '../../lib/useApi'

const ROLES = [['super_admin', 'Super Admin'], ['tournament_admin', 'Tournament Admin'], ['scorer', 'Scorer'], ['viewer', 'Viewer']]

function UserForm({ initial, onClose }) {
  const [form, setForm] = useState(initial || { username: '', email: '', display_name: '', role: 'scorer', password: '', is_active: true })
  const [error, setError] = useState(null)
  const save = async () => {
    try {
      const body = { ...form }
      if (!body.password) delete body.password
      delete body.avatar
      if (initial) await api.patch(`/users/${initial.id}/`, body)
      else await api.post('/users/', body)
      onClose(true)
    } catch (e) {
      setError(errorMessage(e))
    }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  return (
    <Modal open onClose={() => onClose(false)} title={initial ? `Edit ${initial.username}` : 'New user'} footer={<button className="btn-primary" onClick={save}>Save</button>}>
      <ErrorBox>{error}</ErrorBox>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Username"><input className="input" value={form.username} onChange={set('username')} disabled={!!initial} /></Field>
        <Field label="Display name"><input className="input" value={form.display_name} onChange={set('display_name')} /></Field>
        <Field label="Email"><input type="email" className="input" value={form.email} onChange={set('email')} /></Field>
        <Field label="Role"><select className="input" value={form.role} onChange={set('role')}>{ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Field>
        <Field label={initial ? 'New password (optional)' : 'Password'}><input type="password" className="input" value={form.password || ''} onChange={set('password')} autoComplete="new-password" /></Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Active</label>
      </div>
    </Modal>
  )
}

export default function AdminUsers() {
  const [role, setRole] = useState('')
  const [q, setQ] = useState('')
  const { data, loading, error, reload } = useApi('/users/', { params: { role: role || undefined, search: q || undefined, page_size: 200 } })
  const [edit, setEdit] = useState(null)
  return (
    <div>
      <PageHeader title="Users & scorers" icon={Users} actions={<button className="btn-primary" onClick={() => setEdit({})}><Plus className="h-4 w-4" /> New user</button>} />
      <div className="mb-3 flex flex-wrap gap-2">
        <select className="input w-48" value={role} onChange={(e) => setRole(e.target.value)}><option value="">All roles</option>{ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        <input className="input w-56" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <ErrorBox onRetry={reload}>{error}</ErrorBox>
      {loading ? <Spinner /> : (
        <div className="card overflow-x-auto">
          <table className="table-basic">
            <thead><tr><th>Username</th><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th /></tr></thead>
            <tbody>
              {list(data).map((u) => (
                <tr key={u.id}>
                  <td className="font-semibold">{u.username}</td><td>{u.display_name}</td><td>{u.email}</td>
                  <td>{ROLES.find((r) => r[0] === u.role)?.[1]}</td><td>{u.is_active ? 'Active' : 'Disabled'}</td>
                  <td className="text-right"><button className="btn-ghost px-2 py-1 text-xs" onClick={() => setEdit(u)}>Edit</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {edit && <UserForm initial={edit.id ? edit : null} onClose={(ok) => { setEdit(null); if (ok) reload() }} />}
    </div>
  )
}
