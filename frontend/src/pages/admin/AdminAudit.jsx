import { ScrollText } from 'lucide-react'
import { useState } from 'react'
import { list } from '../../api/client'
import { ErrorBox, PageHeader, Spinner } from '../../components/ui'
import { fmtDateTime } from '../../lib/format'
import { useApi } from '../../lib/useApi'

export default function AdminAudit() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const { data, loading, error } = useApi('/audit/', { params: { page, search: q || undefined } })
  return (
    <div>
      <PageHeader title="Audit log" subtitle="Every admin and scoring action, newest first" icon={ScrollText} actions={<input className="input w-56" placeholder="Filter by action" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />} />
      <ErrorBox>{error}</ErrorBox>
      {loading ? <Spinner /> : (
        <>
          <div className="card overflow-x-auto">
            <table className="table-basic">
              <thead><tr><th>When</th><th>User</th><th>Action</th><th>Object</th><th>Match</th><th>Details</th></tr></thead>
              <tbody>
                {list(data).map((a) => (
                  <tr key={a.id}>
                    <td className="whitespace-nowrap text-xs">{fmtDateTime(a.created_at)}</td><td>{a.user_name || '—'}</td>
                    <td className="font-mono text-xs">{a.action}</td><td className="text-xs">{a.object_type} #{a.object_id}</td><td>{a.match}</td>
                    <td className="max-w-xs truncate font-mono text-xs text-slate-500" title={JSON.stringify(a.data)}>{JSON.stringify(a.data)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex justify-center gap-2">
            <button className="btn-secondary" disabled={!data?.previous} onClick={() => setPage(page - 1)}>Previous</button>
            <button className="btn-secondary" disabled={!data?.next} onClick={() => setPage(page + 1)}>Next</button>
          </div>
        </>
      )}
    </div>
  )
}
