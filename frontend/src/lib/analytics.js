import axios from 'axios'
import { API_URL } from '../api/config'

// A random ID kept in this browser only. The server hashes it with a daily salt
// and never stores IPs, so visits are counted without tracking people.
function visitorId() {
  try {
    let id = localStorage.getItem('cricket.visitor')
    if (!id) {
      id = crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)
      localStorage.setItem('cricket.visitor', id)
    }
    return id
  } catch {
    return 'anonymous'
  }
}

export function trackView(path, matchId) {
  axios
    .post(`${API_URL}/analytics/track/`, { path, visitor_id: visitorId(), client: 'web', match: matchId || null })
    .catch(() => {})
}
