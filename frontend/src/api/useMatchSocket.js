import { useEffect, useRef, useState } from 'react'
import { WS_ROOT } from './config'

/**
 * Live WebSocket feed with automatic reconnect (exponential backoff) and heartbeats.
 * onUpdate(snapshot, event) is called for every newer snapshot.
 */
export function useSocket(path, { onMessage, enabled = true } = {}) {
  const [status, setStatus] = useState('connecting')
  const handler = useRef(onMessage)
  handler.current = onMessage

  useEffect(() => {
    if (!enabled || !path) return undefined
    let ws
    let retry = 0
    let closed = false
    let timer
    let ping

    const connect = () => {
      setStatus(retry ? 'reconnecting' : 'connecting')
      ws = new WebSocket(`${WS_ROOT}${path}`)
      ws.onopen = () => {
        retry = 0
        setStatus('open')
        ping = setInterval(() => ws.readyState === 1 && ws.send(JSON.stringify({ type: 'ping' })), 25000)
      }
      ws.onmessage = (e) => {
        try {
          handler.current?.(JSON.parse(e.data))
        } catch {
          /* ignore malformed frames */
        }
      }
      ws.onclose = () => {
        clearInterval(ping)
        if (closed) return
        setStatus('reconnecting')
        retry += 1
        timer = setTimeout(connect, Math.min(15000, 500 * 2 ** retry))
      }
      ws.onerror = () => ws.close()
    }
    connect()
    const onVisible = () => {
      if (document.visibilityState === 'visible' && ws?.readyState === 1) ws.send(JSON.stringify({ type: 'resync' }))
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      closed = true
      clearTimeout(timer)
      clearInterval(ping)
      document.removeEventListener('visibilitychange', onVisible)
      ws?.close()
    }
  }, [path, enabled])

  return status
}

export function useMatchSocket(matchId, onUpdate) {
  const [viewers, setViewers] = useState(null)
  const version = useRef(-1)
  const status = useSocket(matchId ? `/ws/matches/${matchId}/?client=web` : null, {
    onMessage: (msg) => {
      if (msg.type === 'snapshot' || msg.type === 'update') {
        if (msg.snapshot.version >= version.current) {
          const isNew = msg.type === 'update' && msg.snapshot.version > version.current
          version.current = msg.snapshot.version
          onUpdate(msg.snapshot, isNew ? msg.event : null)
        }
        if (msg.viewers != null) setViewers(msg.viewers)
      } else if (msg.type === 'viewers') setViewers(msg.count)
    },
  })
  const reset = (v) => (version.current = v)
  return { status, viewers, reset }
}
