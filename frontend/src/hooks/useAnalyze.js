import { useState, useRef } from 'react'
import { apiAnalyze, safeJson } from '../api/client'

export function useAnalyze({ onAutoSaveJd } = {}) {
  const [result,     setResult]     = useState(null)
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')
  const [resumeText, setResumeText] = useState('')
  const [jdText,     setJdText]     = useState('')
  const abortRef = useRef(null)

  const handleAnalyze = async (rText, jText) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    const timer = setTimeout(() => ctrl.abort(), 90000)
    setLoading(true)
    setError('')
    setResult(null)
    setResumeText(rText)
    setJdText(jText)
    onAutoSaveJd?.(jText)
    try {
      const res = await apiAnalyze(rText, jText, ctrl.signal)
      if (!res.ok) {
        const err = await safeJson(res)
        throw new Error(err.detail || 'Analysis failed')
      }
      const data = await res.json()
      setResult(data)
    } catch (e) {
      if (e.name !== 'AbortError')
        setError(e.message || 'Something went wrong. Is the backend running?')
    } finally {
      clearTimeout(timer)
      setLoading(false)
    }
  }

  const clearAnalyze = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
    setError('')
    setResult(null)
    setResumeText('')
    setJdText('')
  }

  return { result, setResult, loading, error, resumeText, jdText, handleAnalyze, clearAnalyze }
}
