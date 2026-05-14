import { useState, useRef } from 'react'
import BatchDropZone      from './BatchDropZone'
import BatchProgress      from './BatchProgress'
import BatchResultsTable  from './BatchResultsTable'

export default function BatchSection() {
  const [jdText,    setJdText]    = useState('')
  const [files,     setFiles]     = useState([])
  const [batchId,   setBatchId]   = useState(null)
  const [batchData, setBatchData] = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')
  const pollRef = useRef(null)

  const handleStartBatch = async () => {
    if (!jdText.trim() || files.length === 0) return
    setLoading(true)
    setError('')
    setBatchData(null)

    const form = new FormData()
    form.append('jd_text', jdText)
    files.forEach(f => form.append('files', f))

    try {
      const res = await fetch('/batch/start', { method: 'POST', body: form })
      if (!res.ok) {
        const e = await res.json()
        throw new Error(e.detail || 'Failed to start batch')
      }
      const data = await res.json()
      setBatchId(data.batch_id)
      startPolling(data.batch_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const startPolling = (id) => {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/batch/status/${id}`)
        if (!res.ok) return
        const data = await res.json()
        setBatchData(data)
        if (data.status === 'completed') clearInterval(pollRef.current)
      } catch (_) {}
    }, 6000)
  }

  const handleClear = () => {
    clearInterval(pollRef.current)
    setFiles([])
    setJdText('')
    setBatchId(null)
    setBatchData(null)
    setError('')
  }

  const isStarting = loading || (batchId && !batchData)
  const isRunning  = batchData?.status === 'processing'
  const isDone     = batchData?.status === 'completed'
  const showForm   = !batchId && !isRunning && !isDone

  return (
    <section className="batch-section">
      <div className="hero">
        <div className="hero-eyebrow">
          <span className="hero-dot" />
          Batch Pipeline · Auto-Score · Auto-Interview
        </div>
        <h2 className="hero-title">
          Bulk Candidate <span className="hero-gradient">Processing</span>
        </h2>
        <p className="hero-sub">
          Upload multiple resumes, auto-score against the JD, filter top candidates (≥ 75), run AI phone interviews, and get a ranked final report — fully automated.
        </p>
      </div>

      {isStarting && !batchData && (
        <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-2)' }}>
          <div className="spinner" style={{ margin: '0 auto 14px' }} />
          <p style={{ fontSize: '0.9rem' }}>Starting batch pipeline…</p>
        </div>
      )}

      {showForm && (
        <>
          <div className="input-grid">
            <div className="input-card">
              <div className="input-card-header">
                <div className="input-card-title">
                  <span className="icon">📋</span>
                  Job Description
                </div>
                <span className="char-count">{jdText.length} chars</span>
              </div>
              <textarea
                className="input-area"
                placeholder={`Paste the job description here...\n\nExample:\nJob Title: Machine Learning Engineer\nRequired Skills: Python, TensorFlow, NLP...\nExperience: 2-4 years...`}
                value={jdText}
                onChange={e => setJdText(e.target.value)}
                spellCheck={false}
              />
            </div>
            <BatchDropZone files={files} onFilesChange={setFiles} disabled={loading} />
          </div>

          <div className="btn-row">
            <button
              className="btn-analyze"
              onClick={handleStartBatch}
              disabled={loading || !jdText.trim() || files.length === 0}
            >
              {loading
                ? <><div className="spinner" /> Starting...</>
                : <>⚡ Run Batch Pipeline</>
              }
            </button>
            <button className="btn-clear" onClick={handleClear} disabled={loading}>
              Clear
            </button>
          </div>

          {error && <div className="error-banner">⚠️ {error}</div>}

          <p className="hint">
            Candidates scoring ≥ 75 will be auto-called for an AI phone interview
          </p>
        </>
      )}

      {isRunning && <BatchProgress batchData={batchData} />}

      {isDone && (
        <>
          <BatchResultsTable candidates={batchData.candidates} />
          <div className="btn-row" style={{ marginTop: 28 }}>
            <button className="btn-clear" onClick={handleClear}>
              Start New Batch
            </button>
          </div>
        </>
      )}
    </section>
  )
}
