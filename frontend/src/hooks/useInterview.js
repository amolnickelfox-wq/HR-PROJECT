import { useState, useRef } from 'react'
import { apiStartInterview, apiRecallInterview, safeJson } from '../api/client'

export function useInterview() {
  const [interview,   setInterview]   = useState(null)
  const [callLoading, setCallLoading] = useState(false)
  const [callError,   setCallError]   = useState('')
  const esRef = useRef(null)

  const startPolling = (callId) => {
    if (esRef.current) esRef.current.close()

    const es = new EventSource(`/interview/stream/${callId}`)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.status === 'not_found') { es.close(); esRef.current = null; return }
        setInterview(data)
        if (['completed', 'abandoned', 'failed', 'callback_scheduled'].includes(data.status)) {
          es.close()
          esRef.current = null
        }
      } catch (_) {}
    }

    es.onerror = () => { es.close(); esRef.current = null }
  }

  const handleStartInterview = async (payload) => {
    setCallLoading(true)
    setCallError('')
    setInterview(null)
    try {
      const res = await apiStartInterview(payload)
      if (!res.ok) {
        const err = await safeJson(res)
        throw new Error(err.detail || 'Failed to start interview')
      }
      const data = await res.json()
      setInterview({ ...data })
      startPolling(data.call_id)
    } catch (e) {
      setCallError(e.message || 'Failed to initiate call.')
    } finally {
      setCallLoading(false)
    }
  }

  const handleRecall = async (interviewId) =>
    apiRecallInterview(interviewId)

  const clearInterview = () => {
    if (esRef.current) { esRef.current.close(); esRef.current = null }
    setInterview(null)
    setCallError('')
  }

  return {
    interview, setInterview, callLoading, callError,
    handleStartInterview, handleRecall, clearInterview, startPolling,
  }
}
