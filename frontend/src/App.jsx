import { useState, useRef, useEffect } from 'react'
import Sidebar           from './components/Sidebar'
import InputSection      from './components/InputSection'
import ResultsDashboard  from './components/ResultsDashboard'
import BatchProgress     from './components/BatchProgress'
import BatchResultsTable from './components/BatchResultsTable'

const PAGE_TITLES = {
  dashboard:      'Dashboard',
  single:         'Single Candidate',
  batch:          'Batch Pipeline',
  'active-calls': 'Active Calls',
  callbacks:      'Scheduled Callbacks',
  rankings:       'Rankings',
}

export default function App() {
  // ── navigation ──
  const [activePage, setActivePage] = useState('dashboard')

  // ── single-candidate state ──
  const [result,      setResult]      = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')
  const [resumeText,  setResumeText]  = useState('')
  const [jdText,      setJdText]      = useState('')
  const [interview,   setInterview]   = useState(null)
  const [callLoading, setCallLoading] = useState(false)
  const [callError,   setCallError]   = useState('')

  // ── batch state ──
  const [batchFiles,   setBatchFiles]   = useState([])
  const [batchId,      setBatchId]      = useState(null)
  const [batchData,    setBatchData]    = useState(null)
  const [batchLoading, setBatchLoading] = useState(false)
  const [batchError,   setBatchError]   = useState('')

  const resultsRef   = useRef(null)
  const pollRef      = useRef(null)
  const batchPollRef = useRef(null)

  // ── all-time stats (localStorage) ──
  const [allTime, setAllTime] = useState(() => {
    try {
      const s = localStorage.getItem('recruitai_stats')
      return s ? JSON.parse(s) : { total: 0, qualified: 0, done: 0, batches: [] }
    } catch {
      return { total: 0, qualified: 0, done: 0, batches: [] }
    }
  })
  const prevResultRef    = useRef(null)
  const prevIvStatusRef  = useRef(null)

  // ── job openings (localStorage) ──
  const [openings, setOpenings] = useState(() => {
    try {
      const s = localStorage.getItem('recruitai_openings')
      return s ? JSON.parse(s) : []
    } catch { return [] }
  })
  const [activeOpeningId, setActiveOpeningId] = useState(null)
  const [defaultJd,       setDefaultJd]       = useState('')
  const [showOpeningForm, setShowOpeningForm]  = useState(false)
  const [newOpeningTitle, setNewOpeningTitle]  = useState('')
  const [newOpeningJd,    setNewOpeningJd]     = useState('')

  const addAllTime = (delta) => {
    setAllTime(prev => {
      const next = {
        total:     (prev.total     || 0) + (delta.total     || 0),
        qualified: (prev.qualified || 0) + (delta.qualified || 0),
        done:      (prev.done      || 0) + (delta.done      || 0),
        batches:   delta.batchId
          ? [...(prev.batches || []), delta.batchId]
          : (prev.batches || []),
      }
      try { localStorage.setItem('recruitai_stats', JSON.stringify(next)) } catch {}
      return next
    })
  }

  const resetAllTime = () => {
    const blank = { total: 0, qualified: 0, done: 0, batches: [] }
    setAllTime(blank)
    try { localStorage.setItem('recruitai_stats', JSON.stringify(blank)) } catch {}
  }

  const saveOpenings = (arr) => {
    try { localStorage.setItem('recruitai_openings', JSON.stringify(arr)) } catch {}
  }

  const createOpening = () => {
    if (!newOpeningTitle.trim()) return
    const o = {
      id: Date.now().toString(),
      title: newOpeningTitle.trim(),
      jd: newOpeningJd.trim(),
      createdAt: new Date().toISOString().slice(0, 10),
      stats: { total: 0, qualified: 0, done: 0 },
      batchIds: [],
    }
    const next = [...openings, o]
    setOpenings(next); saveOpenings(next)
    setNewOpeningTitle(''); setNewOpeningJd(''); setShowOpeningForm(false)
  }

  const deleteOpening = (id) => {
    const next = openings.filter(o => o.id !== id)
    setOpenings(next); saveOpenings(next)
    if (activeOpeningId === id) setActiveOpeningId(null)
  }

  const updateOpeningStat = (id, delta) => {
    setOpenings(prev => {
      const next = prev.map(o => {
        if (o.id !== id) return o
        return {
          ...o,
          stats: {
            total:     (o.stats.total     || 0) + (delta.total     || 0),
            qualified: (o.stats.qualified || 0) + (delta.qualified || 0),
            done:      (o.stats.done      || 0) + (delta.done      || 0),
          },
          batchIds: delta.batchId
            ? [...(o.batchIds || []), delta.batchId]
            : (o.batchIds || []),
        }
      })
      saveOpenings(next)
      return next
    })
  }

  // Track single-candidate analysis
  useEffect(() => {
    if (result && result !== prevResultRef.current) {
      const score = parseInt(result.match_score) || 0
      const delta = { total: 1, qualified: score >= 75 ? 1 : 0 }
      addAllTime(delta)
      if (activeOpeningId) updateOpeningStat(activeOpeningId, delta)
    }
    prevResultRef.current = result
  }, [result])

  // Track single interview completion
  useEffect(() => {
    if (interview?.status === 'completed' && prevIvStatusRef.current !== 'completed') {
      addAllTime({ done: 1 })
      if (activeOpeningId) updateOpeningStat(activeOpeningId, { done: 1 })
    }
    prevIvStatusRef.current = interview?.status
  }, [interview?.status])

  // Track batch completion (only once per batch_id)
  useEffect(() => {
    if (batchData?.status === 'completed' && batchId && !allTime.batches?.includes(batchId)) {
      const bTotal     = batchData.total || 0
      const bQualified = batchData.candidates?.filter(c => c.filter_status === 'qualified').length || 0
      const bDone      = batchData.candidates?.filter(c =>
        ['completed','abandoned','failed','callback_scheduled'].includes(c.interview_status)
      ).length || 0
      addAllTime({ total: bTotal, qualified: bQualified, done: bDone, batchId })
      if (activeOpeningId) {
        const opening = openings.find(o => o.id === activeOpeningId)
        if (opening && !opening.batchIds?.includes(batchId)) {
          updateOpeningStat(activeOpeningId, { total: bTotal, qualified: bQualified, done: bDone, batchId })
        }
      }
    }
  }, [batchData?.status, batchId])

  // Auto-switch to batch page when files are added on single page
  useEffect(() => {
    if (batchFiles.length > 0 && activePage === 'single') setActivePage('batch')
  }, [batchFiles.length])

  // ── navigation handler ──
  const handleNavigate = (page) => {
    setActivePage(page)
    if (page === 'single') setBatchFiles([])
  }

  // ── single-candidate handlers ──
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

  // ── batch handlers ──
  const handleBatchStart = async (files, jd) => {
    setBatchLoading(true)
    setBatchError('')
    setBatchData(null)
    const form = new FormData()
    form.append('jd_text', jd)
    files.forEach(f => form.append('files', f))
    try {
      const res = await fetch('/batch/start', { method: 'POST', body: form })
      if (!res.ok) {
        const e = await res.json()
        throw new Error(e.detail || 'Failed to start batch')
      }
      const data = await res.json()
      setBatchId(data.batch_id)
      setActivePage('batch')
      startBatchPolling(data.batch_id)
    } catch (e) {
      setBatchError(e.message)
    } finally {
      setBatchLoading(false)
    }
  }

  const startBatchPolling = (id) => {
    clearInterval(batchPollRef.current)
    batchPollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/batch/status/${id}`)
        if (!res.ok) return
        const data = await res.json()
        setBatchData(data)
        if (data.status === 'completed') clearInterval(batchPollRef.current)
      } catch (_) {}
    }, 6000)
  }

  const handleBatchReset = () => {
    clearInterval(batchPollRef.current)
    setBatchFiles([])
    setBatchId(null)
    setBatchData(null)
    setBatchError('')
  }

  // ── derived values ──
  const activeCandidates = batchData?.candidates?.filter(c =>
    ['calling','in_progress'].includes(c.interview_status)
  ) || []
  const callbackCandidates = batchData?.candidates?.filter(c =>
    c.interview_status === 'callback_scheduled'
  ) || []

  return (
    <div className="app-shell">
      <Sidebar
        activePage={activePage}
        onNavigate={handleNavigate}
        batchData={batchData}
        batchId={batchId}
      />

      <div className="app-body">
        <div className="app-topbar">
          <h1 className="topbar-title">{PAGE_TITLES[activePage]}</h1>
          <div className="topbar-actions">
            <span className="topbar-online-badge">● System Online</span>
          </div>
        </div>

        <main className="app-main">

          {/* ── Dashboard ── */}
          {activePage === 'dashboard' && (
            <div>
              <div className="opening-grid">
                {openings.map(op => (
                  <div key={op.id} className="opening-card">
                    <div className="opening-card-header">
                      <span className="opening-card-title">{op.title}</span>
                      <button className="opening-card-delete" onClick={() => deleteOpening(op.id)}
                        title="Delete opening">✕</button>
                    </div>
                    <div className="opening-card-stats">
                      {[
                        { v: op.stats.total,     l: 'Analyzed'   },
                        { v: op.stats.qualified, l: 'Qualified'  },
                        { v: op.stats.done,      l: 'Interviewed' },
                      ].map(s => (
                        <div key={s.l} className="opening-stat">
                          <div className="opening-stat-value">{s.v}</div>
                          <div className="opening-stat-label">{s.l}</div>
                        </div>
                      ))}
                    </div>
                    <div className="opening-card-actions">
                      <button className="opening-btn opening-btn--single"
                        onClick={() => { setActiveOpeningId(op.id); setDefaultJd(op.jd); handleNavigate('single') }}>
                        👤 Single
                      </button>
                      <button className="opening-btn opening-btn--batch"
                        onClick={() => { setActiveOpeningId(op.id); setDefaultJd(op.jd); handleNavigate('batch') }}>
                        📂 Batch
                      </button>
                    </div>
                  </div>
                ))}

                {!showOpeningForm && (
                  <button className="opening-new-card" onClick={() => setShowOpeningForm(true)}>
                    <div className="opening-new-icon">+</div>
                    <div className="opening-new-label">New Job Opening</div>
                  </button>
                )}
              </div>

              {showOpeningForm && (
                <div className="opening-create-form">
                  <div className="opening-form-title">New Job Opening</div>
                  <input
                    className="opening-form-input"
                    placeholder="Job title (e.g. AI Engineer)"
                    value={newOpeningTitle}
                    onChange={e => setNewOpeningTitle(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && createOpening()}
                    autoFocus
                  />
                  <textarea
                    className="opening-form-jd"
                    placeholder="Paste the job description here…"
                    value={newOpeningJd}
                    onChange={e => setNewOpeningJd(e.target.value)}
                  />
                  <div className="opening-form-actions">
                    <button className="btn-analyze" onClick={createOpening}
                      disabled={!newOpeningTitle.trim()}>
                      Create Opening
                    </button>
                    <button className="btn-clear" onClick={() => {
                      setShowOpeningForm(false); setNewOpeningTitle(''); setNewOpeningJd('')
                    }}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {openings.length === 0 && !showOpeningForm && (
                <div className="db-empty-state" style={{ marginTop: 24 }}>
                  <div className="db-empty-icon">💼</div>
                  <div className="db-empty-title">No job openings yet</div>
                  <div className="db-empty-desc">
                    Create a job opening to organise candidates by role and pre-fill the JD automatically.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Single Candidate ── */}
          {activePage === 'single' && (
            <div>
              <InputSection
                key={activeOpeningId || 'single-no-opening'}
                mode="single"
                defaultJd={defaultJd}
                onAnalyze={handleAnalyze}
                loading={loading}
                error={error}
                batchFiles={[]}
                onBatchFilesChange={setBatchFiles}
                onBatchStart={handleBatchStart}
                batchLoading={batchLoading}
                batchError={batchError}
              />
              <div ref={resultsRef}>
                {result && (
                  <ResultsDashboard
                    data={result}
                    interview={interview}
                    callLoading={callLoading}
                    callError={callError}
                    onStartInterview={handleStartInterview}
                  />
                )}
              </div>
            </div>
          )}

          {/* ── Batch Pipeline ── */}
          {activePage === 'batch' && (
            <div>
              {!batchId && (
                <InputSection
                  key={activeOpeningId || 'batch-no-opening'}
                  mode="batch"
                  defaultJd={defaultJd}
                  onAnalyze={handleAnalyze}
                  loading={loading}
                  error={error}
                  batchFiles={batchFiles}
                  onBatchFilesChange={setBatchFiles}
                  onBatchStart={handleBatchStart}
                  batchLoading={batchLoading}
                  batchError={batchError}
                />
              )}
              {batchId && !batchData && (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-2)' }}>
                  <div className="spinner" style={{ margin: '0 auto 14px' }} />
                  <p style={{ fontSize: '0.9rem' }}>Starting batch pipeline…</p>
                </div>
              )}
              {batchData?.status === 'processing' && <BatchProgress batchData={batchData} />}
              {batchData?.candidates?.length > 0 && (
                <>
                  <BatchResultsTable
                    candidates={batchData.candidates}
                    isComplete={batchData.status === 'completed'}
                  />
                  {batchData.status === 'completed' && (
                    <div className="btn-row" style={{ marginTop: 28 }}>
                      <button className="btn-clear" onClick={handleBatchReset}>← Start New Batch</button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── Active Calls ── */}
          {activePage === 'active-calls' && (
            activeCandidates.length > 0
              ? <BatchResultsTable candidates={activeCandidates} isComplete={false} />
              : (
                <div className="db-empty-state">
                  <div className="db-empty-icon">📞</div>
                  <div className="db-empty-title">No active calls right now</div>
                  <div className="db-empty-desc">Start a batch pipeline to see live call status here.</div>
                  <button className="btn-analyze" onClick={() => handleNavigate('batch')}>
                    Go to Batch Pipeline
                  </button>
                </div>
              )
          )}

          {/* ── Callbacks ── */}
          {activePage === 'callbacks' && (
            callbackCandidates.length > 0
              ? <BatchResultsTable candidates={callbackCandidates} isComplete={false} />
              : (
                <div className="db-empty-state">
                  <div className="db-empty-icon">📅</div>
                  <div className="db-empty-title">No callbacks scheduled</div>
                  <div className="db-empty-desc">
                    Candidates who request a callback will appear here with their scheduled time.
                  </div>
                  <button className="btn-analyze" onClick={() => handleNavigate('batch')}>
                    Go to Batch Pipeline
                  </button>
                </div>
              )
          )}

          {/* ── Rankings ── */}
          {activePage === 'rankings' && (
            batchData?.candidates?.length > 0
              ? (
                <BatchResultsTable
                  candidates={batchData.candidates}
                  isComplete={batchData.status === 'completed'}
                />
              )
              : (
                <div className="db-empty-state">
                  <div className="db-empty-icon">🏆</div>
                  <div className="db-empty-title">No rankings yet</div>
                  <div className="db-empty-desc">
                    Run a batch pipeline to see candidates ranked by their combined resume and interview score.
                  </div>
                  <button className="btn-analyze" onClick={() => handleNavigate('batch')}>
                    Run Batch Pipeline
                  </button>
                </div>
              )
          )}

        </main>
      </div>
    </div>
  )
}
