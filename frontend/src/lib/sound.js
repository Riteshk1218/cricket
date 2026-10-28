// Original sound effects synthesised with the Web Audio API (no audio files, no licensing issues).
let ctx

function audio() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext
    if (!AC) return null
    ctx = new AC()
  }
  if (ctx.state === 'suspended') ctx.resume()
  return ctx
}

function tone(ac, { freq, start = 0, dur = 0.2, type = 'sine', gain = 0.3, slide }) {
  const t = ac.currentTime + start
  const osc = ac.createOscillator()
  const g = ac.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, t)
  if (slide) osc.frequency.exponentialRampToValueAtTime(slide, t + dur)
  g.gain.setValueAtTime(0.0001, t)
  g.gain.exponentialRampToValueAtTime(gain, t + 0.02)
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur)
  osc.connect(g).connect(ac.destination)
  osc.start(t)
  osc.stop(t + dur + 0.05)
}

function noise(ac, { start = 0, dur = 0.3, gain = 0.2 }) {
  const t = ac.currentTime + start
  const buffer = ac.createBuffer(1, ac.sampleRate * dur, ac.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < data.length; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / data.length)
  const src = ac.createBufferSource()
  const g = ac.createGain()
  const f = ac.createBiquadFilter()
  f.type = 'bandpass'
  f.frequency.value = 1800
  src.buffer = buffer
  g.gain.value = gain
  src.connect(f).connect(g).connect(ac.destination)
  src.start(t)
}

export function playEffect(kind, volume = 0.7) {
  const ac = audio()
  if (!ac || volume <= 0) return
  const v = Math.max(0, Math.min(1, volume))
  if (kind === 'four') {
    tone(ac, { freq: 523, dur: 0.15, type: 'triangle', gain: 0.35 * v })
    tone(ac, { freq: 659, start: 0.12, dur: 0.15, type: 'triangle', gain: 0.35 * v })
    tone(ac, { freq: 784, start: 0.24, dur: 0.35, type: 'triangle', gain: 0.4 * v })
  } else if (kind === 'six') {
    ;[523, 659, 784, 1047].forEach((f, i) => tone(ac, { freq: f, start: i * 0.1, dur: 0.3, type: 'square', gain: 0.18 * v }))
    tone(ac, { freq: 1047, start: 0.45, dur: 0.6, type: 'triangle', gain: 0.35 * v })
    noise(ac, { start: 0.4, dur: 0.8, gain: 0.12 * v })
  } else if (kind === 'wicket') {
    noise(ac, { dur: 0.15, gain: 0.35 * v })
    tone(ac, { freq: 440, start: 0.1, dur: 0.5, type: 'sawtooth', gain: 0.2 * v, slide: 110 })
  }
}
