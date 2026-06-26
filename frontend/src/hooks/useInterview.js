import { useState, useRef } from 'react'
import { apiStartInterview, apiRecallInterview, apiInterviewStatus, safeJson } from '../api/client'

const TERMINAL = ['completed', 'abandoned', 'failed', 'declined']

export function useInterview() {
  const [interview,   setInterview]   = useState(null)
  const [callLoading, setCallLoading] = useState(false)
  const [callError,   setCallError]   = useState('')
  const esRef       = useRef(null)
  const slowPollRef = useRef(null)

  const _stopAll = () => {
    if (esRef.current)       { esRef.current.close(); esRef.current = null }
    if (slowPollRef.current) { clearInterval(slowPollRef.current); slowPollRef.current = null }
  }

  const startPolling = (callId) => {
    _stopAll()

    const es = new EventSource(`/interview/stream/${callId}`)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.status === 'not_found') { _stopAll(); return }
        setInterview(data)

        if (TERMINAL.includes(data.status)) {
          _stopAll()
        } else if (data.status === 'callback_scheduled') {
          // Close SSE — callback will fire later; switch to slow poll to detect when it does
          es.close(); esRef.current = null
          slowPollRef.current = setInterval(async () => {
            try {
              const r = await apiInterviewStatus(callId)
              const d = await safeJson(r)
              if (!d.status || d.status === 'callback_scheduled') return
              // Status changed — callback fired
              clearInterval(slowPollRef.current); slowPollRef.current = null
              setInterview(d)
              if (!TERMINAL.includes(d.status)) {
                startPolling(callId) // reconnect SSE for the new call attempt
              }
            } catch (_) {}
          }, 10_000)
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
    _stopAll()
    setInterview(null)
    setCallError('')
  }

  return {
    interview, setInterview, callLoading, callError,
    handleStartInterview, handleRecall, clearInterview, startPolling,
  }
}
