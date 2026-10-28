// The backend runs on port 8000 of the same machine that serves the website.
// Using window.location.hostname means the site works on localhost and when a
// phone opens http://<laptop-LAN-IP>:5173 over Wi-Fi.
const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
const proto = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http'

export const API_ROOT = (import.meta.env.VITE_API_URL || `${proto}://${host}:8000`).replace(/\/$/, '')
export const API_URL = `${API_ROOT}/api`
export const WS_ROOT = (import.meta.env.VITE_WS_URL || API_ROOT.replace(/^http/, 'ws')).replace(/\/$/, '')

export function mediaUrl(path) {
  if (!path) return null
  return path.startsWith('http') ? path : `${API_ROOT}${path}`
}
