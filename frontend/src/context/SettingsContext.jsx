import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { STRINGS } from '../i18n/strings'

const SettingsContext = createContext(null)

function load(key, fallback) {
  try {
    const v = localStorage.getItem(key)
    return v === null ? fallback : JSON.parse(v)
  } catch {
    return fallback
  }
}

function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* ignore */
  }
}

export function SettingsProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    } catch {
      return 'light'
    }
  })
  const [lang, setLang] = useState(() => load('cricket.lang', 'en'))
  const [sound, setSound] = useState(() => load('cricket.sound', true))
  const [volume, setVolume] = useState(() => load('cricket.volume', 0.6))
  const [animations, setAnimations] = useState(() => load('cricket.animations', true))

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try {
      localStorage.setItem('theme', theme)
    } catch {
      /* ignore */
    }
  }, [theme])
  useEffect(() => {
    save('cricket.lang', lang)
    document.documentElement.lang = lang
  }, [lang])
  useEffect(() => save('cricket.sound', sound), [sound])
  useEffect(() => save('cricket.volume', volume), [volume])
  useEffect(() => save('cricket.animations', animations), [animations])

  const t = useCallback((key) => STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key, [lang])

  const value = useMemo(
    () => ({ theme, setTheme, lang, setLang, sound, setSound, volume, setVolume, animations, setAnimations, t }),
    [theme, lang, sound, volume, animations, t],
  )
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export const useSettings = () => useContext(SettingsContext)
