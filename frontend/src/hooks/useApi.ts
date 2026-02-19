import { useCallback, useState } from 'react'
import api from '../lib/api'

interface UseApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
}

export function useApi<T>() {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    error: null,
    loading: false,
  })

  const request = useCallback(async (method: string, url: string, body?: unknown) => {
    setState({ data: null, error: null, loading: true })
    try {
      const res = await api.request({ method, url, data: body })
      setState({ data: res.data, error: null, loading: false })
      return res.data as T
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message || 'Request failed'
      setState({ data: null, error: message, loading: false })
      throw err
    }
  }, [])

  return { ...state, request }
}
