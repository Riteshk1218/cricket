import axios from 'axios'
import { API_URL } from './config'

const TOKEN_KEY = 'cricket.tokens'

export function getTokens() {
  try {
    return JSON.parse(localStorage.getItem(TOKEN_KEY)) || null
  } catch {
    return null
  }
}

export function setTokens(tokens) {
  try {
    if (tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens))
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable (private mode) */
  }
}

const api = axios.create({ baseURL: API_URL, timeout: 15000 })

api.interceptors.request.use((config) => {
  const tokens = getTokens()
  if (tokens?.access) config.headers.Authorization = `Bearer ${tokens.access}`
  return config
})

let refreshing = null

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    const tokens = getTokens()
    if (error.response?.status === 401 && tokens?.refresh && !original._retry && !original.url.includes('/auth/')) {
      original._retry = true
      try {
        refreshing = refreshing || axios.post(`${API_URL}/auth/refresh/`, { refresh: tokens.refresh })
        const { data } = await refreshing
        setTokens({ access: data.access, refresh: data.refresh || tokens.refresh })
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (e) {
        setTokens(null)
        window.dispatchEvent(new Event('auth:logout'))
        throw e
      } finally {
        refreshing = null
      }
    }
    throw error
  },
)

/** Human-readable message from an API error. */
export function errorMessage(err) {
  const data = err?.response?.data
  if (!err?.response) return 'Cannot reach the server. Check that the backend is running and you are on the same network.'
  if (typeof data === 'string') return data.slice(0, 200)
  if (data?.detail) return data.detail
  if (data && typeof data === 'object') {
    return Object.entries(data)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : typeof v === 'object' ? JSON.stringify(v) : v}`)
      .join(' · ')
  }
  return err.message || 'Something went wrong'
}

/** Unwrap paginated or plain list responses. */
export const list = (data) => (Array.isArray(data) ? data : data?.results || [])

export default api
