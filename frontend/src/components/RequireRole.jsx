import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './ui'

/** Client-side guard for convenience only; every API call is authorised again by the backend. */
export default function RequireRole({ roles, children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (roles && !roles.includes(user.role)) {
    return <div className="card p-6 text-center"><h1 className="text-xl font-bold">Not allowed</h1><p className="text-sm text-slate-500">Your account ({user.role.replace('_', ' ')}) cannot open this page.</p></div>
  }
  return children
}
