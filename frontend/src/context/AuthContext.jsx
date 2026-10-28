import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api, { getTokens, setTokens } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getTokens())

  const loadMe = useCallback(async () => {
    if (!getTokens()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const { data } = await api.get('/auth/me/')
      setUser(data)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMe()
    const onLogout = () => setUser(null)
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [loadMe])

  const login = async (username, password) => {
    const { data } = await api.post('/auth/login/', { username, password })
    setTokens({ access: data.access, refresh: data.refresh })
    setUser(data.user)
    return data.user
  }

  const register = async (payload) => {
    await api.post('/auth/register/', payload)
    return login(payload.username, payload.password)
  }

  const logout = async () => {
    const tokens = getTokens()
    try {
      if (tokens?.refresh) await api.post('/auth/logout/', { refresh: tokens.refresh })
    } catch {
      /* token may already be expired */
    }
    setTokens(null)
    setUser(null)
  }

  const value = useMemo(() => {
    const role = user?.role
    return {
      user, loading, login, logout, register, reload: loadMe, setUser,
      isSuperAdmin: role === 'super_admin',
      isAdmin: role === 'super_admin' || role === 'tournament_admin',
      isScorer: role === 'scorer' || role === 'super_admin' || role === 'tournament_admin',
    }
  }, [user, loading, loadMe])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
