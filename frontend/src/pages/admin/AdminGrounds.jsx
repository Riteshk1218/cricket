import { MapPin, Plus } from 'lucide-react'
import { useState } from 'react'
import api, { errorMessage } from '../../api/client'
import { ErrorBox, Field, PageHeader, Spinner } from '../../components/ui'
import { useApi } from '../../lib/useApi'

export default function AdminGrounds() {
  const { data, loading, reload } = useApi('/grounds/')
  const [form, setForm] = useState({ name: '', city: '', address: '', capacity: '' })
  const [error, setError] = useState(null)
  const add = async (e) => {
    e.preventDefault()
    try {
      await api.post('/grounds/', { ...form, capacity: form.capacity || null })
      setForm({ name: '', city: '', address: '', capacity: '' })
      setError(null)
      reload()
    } catch (err) {
      setError(errorMessage(err))
    }
  }
  return (
    <div>
      <PageHeader title="Grounds" icon={MapPin} />
      <form onSubmit={add} className="card mb-4 grid gap-3 p-4 sm:grid-cols-5">
        <div className="sm:col-span-5"><ErrorBox>{error}</ErrorBox></div>
        <Field label="Name"><input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="City"><input className="input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></Field>
        <Field label="Address"><input className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
        <Field label="Capacity"><input type="number" className="input" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} /></Field>
        <div className="flex items-end"><button className="btn-primary w-full"><Plus className="h-4 w-4" /> Add ground</button></div>
      </form>
      {loading ? <Spinner /> : (
        <div className="card overflow-x-auto">
          <table className="table-basic">
            <thead><tr><th>Name</th><th>City</th><th>Address</th><th>Capacity</th></tr></thead>
            <tbody>{(data || []).map((g) => <tr key={g.id}><td className="font-semibold">{g.name}</td><td>{g.city}</td><td>{g.address}</td><td>{g.capacity}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </div>
  )
}
