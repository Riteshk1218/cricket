import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../api/client'

/** GET a URL and keep {data, loading, error, reload}. Pass null to skip. */
export function useApi(url, { params, initial = null } = {}) {
  const [data, setData] = useState(initial)
  const [loading, setLoading] = useState(!!url)
  const [error, setError] = useState(null)
  const key = url ? `${url}?${JSON.stringify(params || {})}` : null

  const reload = useCallback(async () => {
    if (!url) return
    setLoading(true)
    try {
      const res = await api.get(url, { params })
      setData(res.data)
      setError(null)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => {
    reload()
  }, [reload])

  return { data, setData, loading, error, reload }
}
