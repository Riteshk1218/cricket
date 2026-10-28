import { useEffect, useState } from 'react'
import { useSettings } from '../context/SettingsContext'
import { playEffect } from '../lib/sound'

const COLORS = ['#f2b01e', '#22997b', '#c81e1e', '#3b82f6', '#a855f7', '#ffffff']

function particles(n, spread) {
  return Array.from({ length: n }, (_, i) => {
    const angle = (i / n) * Math.PI * 2
    const dist = spread * (0.6 + Math.random() * 0.6)
    return { id: i, dx: `${Math.cos(angle) * dist}px`, dy: `${Math.sin(angle) * dist}px`, color: COLORS[i % COLORS.length], size: 6 + Math.random() * 8 }
  })
}

/**
 * Non-blocking FOUR / SIX / WICKET overlay. pointer-events are disabled so it never
 * interrupts scoring, and it only animates transform/opacity.
 */
export default function CelebrationOverlay({ event }) {
  const { animations, sound, volume, t, lang } = useSettings()
  const [shown, setShown] = useState(null)

  useEffect(() => {
    if (!event?.highlight) return undefined
    if (sound) playEffect(event.highlight, volume)
    if (!animations) return undefined
    setShown({ ...event, key: Date.now(), parts: particles(event.highlight === 'six' ? 28 : 16, event.highlight === 'six' ? 220 : 150) })
    const timer = setTimeout(() => setShown(null), 2300)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event?.delivery_id, event?.highlight])

  if (!shown) return null
  const kind = shown.highlight
  const label = kind === 'four' ? t('four') : kind === 'six' ? t('six') : t('wicket')
  return (
    <div key={shown.key} className="pointer-events-none fixed inset-0 z-[60] flex items-center justify-center" aria-live="assertive">
      <span className="sr-only">{label}</span>
      {kind !== 'wicket' &&
        shown.parts.map((p) => (
          <span
            key={p.id}
            className="burst absolute rounded-full"
            style={{ '--dx': p.dx, '--dy': p.dy, width: p.size, height: p.size, background: p.color }}
          />
        ))}
      {kind === 'wicket' && (
        <>
          <span className="bail absolute h-2 w-10 rounded bg-amber-300" style={{ '--dx': '-120px', '--rot': '-200deg' }} />
          <span className="bail absolute h-2 w-10 rounded bg-amber-300" style={{ '--dx': '120px', '--rot': '220deg' }} />
        </>
      )}
      <div
        className={`${kind === 'wicket' ? 'wicket-text bg-ball' : kind === 'six' ? 'celebrate-text bg-gradient-to-br from-violet-600 to-fuchsia-500' : 'celebrate-text bg-gradient-to-br from-pitch-500 to-emerald-700'} rounded-3xl px-10 py-6 text-center shadow-2xl ring-4 ring-white/40`}
      >
        <div className="text-6xl font-black tracking-tight text-white drop-shadow sm:text-8xl">{label}</div>
        {shown.batter && <div className="mt-1 text-sm font-semibold text-white/90">{kind === 'wicket' ? (shown.text?.[lang] || shown.text?.en || '').split(/[.।]/)[0] : shown.batter}</div>}
      </div>
    </div>
  )
}
