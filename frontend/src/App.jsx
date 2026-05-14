import { useState, useRef } from 'react'
import Header           from './components/Header'
import InputSection     from './components/InputSection'
import ResultsDashboard from './components/ResultsDashboard'
import BatchSection     from './components/BatchSection'

export default function App() {
  const [mode,        setMode]        = useState('single')  // 'single' | 'batch'
  const [result,      setResult]      = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')
  const [resumeText,  setResumeText]  = useState('')
  const [jdText,      setJdText]      = useState('')
  const [interview,   setInterview]   = useState(null)
  const [callLoading, setCallLoading] = useState(false)
  const [callError,   setCallError]   = useState('')

  // Local voice interview
  const [localStep,  setLocalStep]  = useState('idle')   // 'idle' | 'in-progress' | 'scoring'
  const [localError, setLocalError] = useState('')

  const resultsRef = useRef(null)
  const pollRef    = useRef(null)

  const handleAnalyze = async (rText, jText) => {
    setLoading(true)
    setError('')
    setResult(null)
    setInterview(null)
    setLocalStep('idle')
    setResumeText(rText)
    setJdText(jText)
    try {
      const res = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: rText, jd_text: jText }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis failed')
      }
      const data = await res.json()
      setResult(data)
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    } catch (e) {
      setError(e.message || 'Something went wrong. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const handleStartInterview = async () => {
    if (!result?.phone) return
    setCallLoading(true)
    setCallError('')
    setInterview(null)
    try {
      const res = await fetch('/interview/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone:          result.phone,
          resume_text:    resumeText,
          jd_text:        jdText,
          candidate_name: result.name,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
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

  const handleStartLocal = () => {
    setLocalStep('in-progress')
    setLocalError('')
    setInterview(null)
  }

  const handleLocalComplete = async (conversation) => {
    setLocalStep('scoring')
    try {
      const res = await fetch('/interview/local/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resumeText, jd_text: jdText, conversation }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Scoring failed')
      }
      const scoreResult = await res.json()
      setInterview({
        status:       'completed',
        questions:    conversation.filter(m => m.role === 'interviewer').map(m => m.content),
        transcript:   conversation
          .map(m => `${m.role === 'interviewer' ? 'Interviewer' : 'Candidate'}: ${m.content}`)
          .join('\n\n'),
        score_result: scoreResult,
      })
    } catch (e) {
      setLocalError(e.message)
    } finally {
      setLocalStep('idle')
    }
  }

  const handleLocalCancel = () => {
    setLocalStep('idle')
    setLocalError('')
  }

  const startPolling = (callId) => {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/interview/status/${callId}`)
        if (!res.ok) return
        const data = await res.json()
        setInterview(data)
        if (['completed', 'abandoned', 'failed', 'callback_scheduled'].includes(data.status)) {
          clearInterval(pollRef.current)
        }
      } catch (_) {}
    }, 5000)
  }

  return (
    <div className="app">
      <div className="bg-orbs" aria-hidden="true">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      <Header />

      <div className="mode-toggle">
        <button
          className={`mode-tab${mode === 'single' ? ' mode-tab--active' : ''}`}
          onClick={() => setMode('single')}
        >
          Single Candidate
        </button>
        <button
          className={`mode-tab${mode === 'batch' ? ' mode-tab--active' : ''}`}
          onClick={() => setMode('batch')}
        >
          Batch Pipeline
        </button>
      </div>

      <main className="main">
        {mode === 'single' && (
          <>
            <InputSection onAnalyze={handleAnalyze} loading={loading} error={error} />
            <div ref={resultsRef}>
              {result && (
                <ResultsDashboard
                  data={result}
                  interview={interview}
                  callLoading={callLoading}
                  callError={callError}
                  onStartInterview={handleStartInterview}
                  resumeText={resumeText}
                  jdText={jdText}
                  candidateName={result?.name}
                  localStep={localStep}
                  localError={localError}
                  onStartLocal={handleStartLocal}
                  onLocalComplete={handleLocalComplete}
                  onLocalCancel={handleLocalCancel}
                />
              )}
            </div>
          </>
        )}
        {mode === 'batch' && <BatchSection />}
      </main>
    </div>
  )
}
