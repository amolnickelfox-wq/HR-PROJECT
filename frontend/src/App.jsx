import { useState, useRef, useEffect } from 'react'
import Sidebar           from './components/Sidebar'
import InputSection      from './components/InputSection'
import ResultsDashboard  from './components/ResultsDashboard'
import BatchProgress     from './components/BatchProgress'
import BatchResultsTable    from './components/BatchResultsTable'
import CallbackAlertModal  from './components/CallbackAlertModal'

const safeJson = async (res) => {
  try { return await res.json() } catch { return {} }
}

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

  const resultsRef       = useRef(null)
  const pollRef          = useRef(null)
  const batchPollRef     = useRef(null)
  const abortRef         = useRef(null)
  const callbackAlertRef = useRef(null)

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
  const [activeOpeningId, setActiveOpeningId] = useState(() => {
    try { return localStorage.getItem('recruitai_activeOpening') || null } catch { return null }
  })
  const setActiveOpening = (id) => {
    setActiveOpeningId(id)
    try {
      if (id) localStorage.setItem('recruitai_activeOpening', id)
      else localStorage.removeItem('recruitai_activeOpening')
    } catch {}
  }
  const activeOpening = openings.find(o => o.id === activeOpeningId) || null
  const defaultJd = activeOpening?.jd || ''
  const [showOpeningForm,  setShowOpeningForm]   = useState(false)
  const [newOpeningTitle,  setNewOpeningTitle]   = useState('')
  const [newOpeningJd,     setNewOpeningJd]      = useState('')
  const [editingOpeningId, setEditingOpeningId]  = useState(null)
  const [editingJd,        setEditingJd]         = useState('')
  const [viewingOpeningId, setViewingOpeningId]  = useState(null)
  const [duplicateModal,      setDuplicateModal]      = useState(null)
  const [dueCallbacks,        setDueCallbacks]        = useState([])
  const [dismissedCallbacks,  setDismissedCallbacks]  = useState({})
  const currentSingleIdRef = useRef(null)

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

  const candidateStatusLabel = (c) => {
    if (!c) return '—'
    if (c.filter_status === 'filtered_out') return 'Filtered Out (resume score too low)'
    if (c.filter_status === 'no_phone') return 'No Phone Number'
    if (c.interview_status === 'completed') return 'Interview Completed'
    if (c.interview_status === 'callback_scheduled') return 'Callback Scheduled'
    if (c.interview_status === 'failed') return 'Call Failed'
    if (c.interview_status === 'timeout') return 'Call Timed Out'
    if (c.interview_status === 'abandoned') return 'Candidate Disconnected'
    if (c.interview_status === 'retry_queued') return 'Retry Queued'
    if (c.interview_status === 'pending') return 'Awaiting Interview'
    return 'Pending'
  }

  const findDuplicateInOpening = (opening, name, email) => {
    if (!opening?.candidates?.length) return null
    return opening.candidates.find(c => {
      const n1 = (name  || '').trim().toLowerCase()
      const n2 = (c.name || '').trim().toLowerCase()
      const e1 = (email  || '').trim().toLowerCase()
      const e2 = (c.email || '').trim().toLowerCase()
      if (e1 && e2 && e1 === e2) return true
      if (n1 && n2 && n1 === n2) return true
      return false
    }) || null
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
      candidates: [],
    }
    const next = [...openings, o]
    setOpenings(next); saveOpenings(next)
    setNewOpeningTitle(''); setNewOpeningJd(''); setShowOpeningForm(false)
  }

  const deleteOpening = (id) => {
    const next = openings.filter(o => o.id !== id)
    setOpenings(next); saveOpenings(next)
    if (activeOpeningId === id) { setActiveOpening(null); setViewingOpeningId(null) }
    if (viewingOpeningId === id) setViewingOpeningId(null)
  }

  const updateOpeningJd = (id, jd) => {
    const next = openings.map(o => o.id === id ? { ...o, jd } : o)
    setOpenings(next); saveOpenings(next)
    setEditingOpeningId(null); setEditingJd('')
  }

  // Save a single analysis result as a candidate entry in the opening
  const addSingleToOpening = (openingId, candidateEntry, statsDelta) => {
    setOpenings(prev => {
      const next = prev.map(o => {
        if (o.id !== openingId) return o
        return {
          ...o,
          stats: {
            total:     (o.stats.total     || 0) + (statsDelta.total     || 0),
            qualified: (o.stats.qualified || 0) + (statsDelta.qualified || 0),
            done:      (o.stats.done      || 0),
          },
          candidates: [...(o.candidates || []), candidateEntry],
        }
      })
      saveOpenings(next)
      return next
    })
  }

  // Update a single candidate's interview result in the opening (any status change)
  const updateSingleInterviewInOpening = (openingId, singleId, iv) => {
    setOpenings(prev => {
      const next = prev.map(o => {
        if (o.id !== openingId) return o
        const iscore = parseInt(
          (iv.score_result?.interview_score || '0').toString().split('/')[0]
        ) || 0
        const isDone = ['completed','abandoned','failed','callback_scheduled'].includes(iv.status)
        return {
          ...o,
          stats: isDone ? { ...o.stats, done: (o.stats.done || 0) + 1 } : o.stats,
          candidates: (o.candidates || []).map(c => {
            if (c._singleId !== singleId) return c
            const rscore = c.resume_score || 0
            return {
              ...c,
              interview_status:      iv.status,
              interview_score:       iscore || null,
              combined_score:        iscore > 0 ? Math.round(rscore * 0.4 + iscore * 0.6) : null,
              score_result:          iv.score_result          || null,
              transcript:            iv.transcript            || null,
              questions:             iv.questions             || [],
              call_log:              iv.call_log              || [],
              fail_reason:           iv.fail_reason           || null,
              callback_scheduled_at: iv.callback_scheduled_at || null,
            }
          }),
        }
      })
      saveOpenings(next)
      return next
    })
  }

  // Save completed batch candidates to the opening (replaces old entries from same batchId)
  const saveOpeningBatch = (openingId, batchId, candidates, statsDelta) => {
    setOpenings(prev => {
      const next = prev.map(o => {
        if (o.id !== openingId) return o
        const stripped = candidates.map(({ resume_text, ...rest }) => ({ ...rest, _batchId: batchId }))
        const existing = (o.candidates || []).filter(c => c._batchId !== batchId)
        return {
          ...o,
          stats: {
            total:     (o.stats.total     || 0) + (statsDelta.total     || 0),
            qualified: (o.stats.qualified || 0) + (statsDelta.qualified || 0),
            done:      (o.stats.done      || 0) + (statsDelta.done      || 0),
          },
          batchIds:   [...(o.batchIds   || []), batchId],
          candidates: [...existing, ...stripped],
        }
      })
      saveOpenings(next)
      return next
    })
  }

  // Track single-candidate analysis
  useEffect(() => {
    if (result && result !== prevResultRef.current) {
      const score    = parseInt(result.match_score) || 0
      const delta    = { total: 1, qualified: score >= 75 ? 1 : 0 }
      const singleId = Date.now().toString()
      const entry    = {
        _singleId:        singleId,
        _batchId:         null,
        _type:            'single',
        name:             result.name   || null,
        email:            result.email  || null,
        phone:            result.phone  || null,
        file_name:        result.name   || 'Single Candidate',
        resume_score:     score,
        filter_status:    score >= 75 ? 'qualified' : 'filtered_out',
        interview_status: 'pending',
        interview_score:  null,
        combined_score:   null,
        score_result:     null,
        transcript:       null,
        questions:        [],
        analyze_result:   result,
      }

      if (activeOpeningId) {
        const opening  = openings.find(o => o.id === activeOpeningId)
        const existing = findDuplicateInOpening(opening, result.name, result.email)
        if (existing) {
          setDuplicateModal({
            existing,
            onAddAnyway: () => {
              currentSingleIdRef.current = singleId
              addSingleToOpening(activeOpeningId, entry, delta)
              addAllTime(delta)
              setDuplicateModal(null)
            },
            onCancel: () => setDuplicateModal(null),
          })
        } else {
          currentSingleIdRef.current = singleId
          addSingleToOpening(activeOpeningId, entry, delta)
          addAllTime(delta)
        }
      } else {
        addAllTime(delta)
      }
    }
    prevResultRef.current = result
  }, [result])

  // Track single interview — sync every status change to opening
  useEffect(() => {
    const s   = interview?.status
    const prev = prevIvStatusRef.current
    if (s && s !== prev) {
      if (activeOpeningId && currentSingleIdRef.current) {
        updateSingleInterviewInOpening(activeOpeningId, currentSingleIdRef.current, interview)
      }
      if (s === 'completed' && prev !== 'completed') addAllTime({ done: 1 })
    }
    prevIvStatusRef.current = s
  }, [interview?.status])

  // Sync live interview data from a polled batch back into any matching opening
  const syncBatchToOpenings = (bid, updatedCandidates) => {
    setOpenings(prev => {
      const hasMatch = prev.some(o => o.batchIds?.includes(bid))
      if (!hasMatch) return prev
      const next = prev.map(o => {
        if (!o.batchIds?.includes(bid)) return o
        return {
          ...o,
          candidates: (o.candidates || []).map(c => {
            if (c._batchId !== bid) return c
            const u = updatedCandidates.find(uc => uc.file_name === c.file_name)
            if (!u) return c
            const iscore = parseInt(
              (u.score_result?.interview_score || '0').toString().split('/')[0]
            ) || 0
            return {
              ...c,
              interview_status:      u.interview_status,
              interview_score:       iscore || c.interview_score || null,
              combined_score:        iscore > 0
                ? Math.round((c.resume_score || 0) * 0.4 + iscore * 0.6)
                : c.combined_score,
              score_result:          u.score_result          ?? c.score_result,
              transcript:            u.transcript            ?? c.transcript,
              questions:             u.questions             ?? c.questions,
              call_log:              u.call_log              ?? c.call_log,
              fail_reason:           u.fail_reason           ?? c.fail_reason,
              callback_scheduled_at: u.callback_scheduled_at ?? c.callback_scheduled_at,
              processing_step:       u.processing_step       ?? null,
            }
          }),
        }
      })
      saveOpenings(next)
      return next
    })
  }

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
          // Flag duplicates in batch candidates before saving
          const cands = batchData.candidates.map(c => {
            const dup = findDuplicateInOpening(opening, c.name, c.email)
            return dup ? { ...c, _duplicate_of: dup._singleId || dup._batchId || 'existing' } : c
          })
          saveOpeningBatch(activeOpeningId, batchId, cands,
            { total: bTotal, qualified: bQualified, done: bDone })
        }
      }
    }
  }, [batchData?.status, batchId])

  // Auto-switch to batch page when files are added on single page
  useEffect(() => {
    if (batchFiles.length > 0 && activePage === 'single') setActivePage('batch')
  }, [batchFiles.length])

  // Poll /callbacks/due every 60 s to alert HR about due callbacks
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('/callbacks/due')
        if (!res.ok) return
        const data = await res.json()
        setDueCallbacks(data.due || [])
      } catch (_) {}
    }
    poll()
    callbackAlertRef.current = setInterval(poll, 60_000)
    return () => clearInterval(callbackAlertRef.current)
  }, [])

  // ── navigation handler ──
  const handleNavigate = (page) => {
    setActivePage(page)
    if (page === 'single') setBatchFiles([])
  }

  // ── single-candidate handlers ──
  const handleClearAll = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
    setError('')
    setResult(null)
    setInterview(null)
    clearTimeout(pollRef.current)
  }

  const handleAnalyze = async (rText, jText) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    const timer = setTimeout(() => ctrl.abort(), 90000)
    setLoading(true)
    setError('')
    setResult(null)
    setInterview(null)
    setResumeText(rText)
    setJdText(jText)
    // Auto-save JD to opening if not already stored
    if (activeOpeningId && jText.trim()) {
      const op = openings.find(o => o.id === activeOpeningId)
      if (op && !op.jd) updateOpeningJd(activeOpeningId, jText.trim())
    }
    try {
      const res = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: rText, jd_text: jText }),
        signal: ctrl.signal,
      })
      if (!res.ok) {
        const err = await safeJson(res)
        throw new Error(err.detail || 'Analysis failed')
      }
      const data = await res.json()
      setResult(data)
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    } catch (e) {
      if (e.name !== 'AbortError')
        setError(e.message || 'Something went wrong. Is the backend running?')
    } finally {
      clearTimeout(timer)
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
          job_title:      openings.find(o => o.id === activeOpeningId)?.title || '',
        }),
      })
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

  const startPolling = (callId) => {
    clearTimeout(pollRef.current)
    const tick = async () => {
      try {
        const res = await fetch(`/interview/status/${callId}`)
        if (!res.ok) return
        const data = await res.json()
        setInterview(data)
        if (['completed', 'abandoned', 'failed', 'callback_scheduled'].includes(data.status)) return
        const interval = ['calling', 'processing'].includes(data.status) ? 2500 : 6000
        pollRef.current = setTimeout(tick, interval)
      } catch (_) {}
    }
    pollRef.current = setTimeout(tick, 2500)
  }

  // ── batch handlers ──
  const handleBatchStart = async (files, jd) => {
    setBatchLoading(true)
    setBatchError('')
    setBatchData(null)
    // Auto-save JD to opening if not already stored
    if (activeOpeningId && jd.trim()) {
      const op = openings.find(o => o.id === activeOpeningId)
      if (op && !op.jd) updateOpeningJd(activeOpeningId, jd.trim())
    }
    const form = new FormData()
    form.append('jd_text', jd)
    form.append('job_title', openings.find(o => o.id === activeOpeningId)?.title || '')
    files.forEach(f => form.append('files', f))
    try {
      const res = await fetch('/batch/start', { method: 'POST', body: form })
      if (!res.ok) {
        const e = await safeJson(res)
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
    clearTimeout(batchPollRef.current)
    const tick = async () => {
      try {
        const res = await fetch(`/batch/status/${id}`)
        if (!res.ok) return
        const data = await res.json()
        setBatchData(data)
        if (data.candidates?.length) syncBatchToOpenings(id, data.candidates)
        const hasActive = data.candidates?.some(c =>
          ['calling', 'in_progress', 'processing'].includes(c.interview_status)
        )
        if (data.status === 'completed' && !hasActive) return
        // Poll faster while a call is active or being processed
        const interval = hasActive || data.status === 'processing' ? 2500 : 6000
        batchPollRef.current = setTimeout(tick, interval)
      } catch (_) {}
    }
    batchPollRef.current = setTimeout(tick, 2500)
  }

  const handleBatchReset = () => {
    clearTimeout(batchPollRef.current)
    setBatchFiles([])
    setBatchId(null)
    setBatchData(null)
    setBatchError('')
  }

  const handleCallCandidate = async (candidate) => {
    if (!candidate.phone) return
    try {
      let newIid = candidate.interview_id
      let res

      if (newIid) {
        // Already has interview session — re-dial it
        res = await fetch(`/interview/recall/${newIid}`, { method: 'POST' })
      } else {
        // No interview yet — start fresh using batch resume data
        const bid = candidate._batchId || batchId
        if (!bid) {
          alert('Cannot start call: batch ID not found. Please re-run the batch.')
          return
        }
        res = await fetch(`/batch/${bid}/interview/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_name: candidate.file_name }),
        })
        if (res.ok) {
          const d = await res.json()
          newIid = d.interview_id
        }
      }

      if (!res.ok) {
        const err = await safeJson(res)
        alert(err.detail || 'Failed to start call.')
        return
      }

      // Update status in live batch data
      if (batchData) {
        setBatchData(prev => ({
          ...prev,
          candidates: prev.candidates.map(c =>
            c.file_name === candidate.file_name
              ? { ...c, interview_id: newIid, interview_status: 'calling' }
              : c
          ),
        }))
        const pid = candidate._batchId || batchId
        if (pid) startBatchPolling(pid)
      }

      // Update status in opening rankings
      if (viewingOpeningId) {
        setOpenings(prev => {
          const next = prev.map(o => {
            if (o.id !== viewingOpeningId) return o
            return {
              ...o,
              candidates: (o.candidates || []).map(c =>
                c.file_name === candidate.file_name
                  ? { ...c, interview_id: newIid, interview_status: 'calling' }
                  : c
              ),
            }
          })
          saveOpenings(next)
          return next
        })
      }
    } catch (e) {
      alert(e.message || 'Failed to start call.')
    }
  }

  // ── derived values ──
  const activeCandidates = batchData?.candidates?.filter(c =>
    ['calling','in_progress'].includes(c.interview_status)
  ) || []
  const callbackCandidates = batchData?.candidates?.filter(c =>
    c.interview_status === 'callback_scheduled'
  ) || []
  const visibleDueCallbacks = dueCallbacks.filter(cb => {
    const snoozedAt = dismissedCallbacks[cb.interview_id]
    if (!snoozedAt) return true
    return Date.now() - snoozedAt > 10 * 60 * 1000
  })

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
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="opening-card-delete"
                          onClick={() => { setEditingOpeningId(op.id); setEditingJd(op.jd || '') }}
                          title="Edit JD">✏️</button>
                        <button className="opening-card-delete" onClick={() => deleteOpening(op.id)}
                          title="Delete opening">✕</button>
                      </div>
                    </div>

                    {editingOpeningId === op.id ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <textarea
                          className="opening-form-jd"
                          placeholder="Paste the job description here…"
                          value={editingJd}
                          onChange={e => setEditingJd(e.target.value)}
                          autoFocus
                        />
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button className="btn-analyze" style={{ flex: 1, fontSize: '0.8rem', padding: '7px 0' }}
                            onClick={() => updateOpeningJd(op.id, editingJd.trim())}>
                            Save JD
                          </button>
                          <button className="btn-clear" style={{ flex: 1, fontSize: '0.8rem', padding: '7px 0' }}
                            onClick={() => { setEditingOpeningId(null); setEditingJd('') }}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
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
                        {!op.jd && (
                          <div style={{ fontSize: '0.72rem', color: '#f59e0b', marginBottom: 4 }}>
                            ⚠️ No JD saved — click ✏️ to add one
                          </div>
                        )}
                        <div className="opening-card-actions">
                          <button className="opening-btn opening-btn--single"
                            onClick={() => { setActiveOpening(op.id); setResult(null); setInterview(null); handleNavigate('single') }}>
                            👤 Single
                          </button>
                          <button className="opening-btn opening-btn--batch"
                            onClick={() => { setActiveOpening(op.id); handleBatchReset(); handleNavigate('batch') }}>
                            📂 Batch
                          </button>
                        </div>
                        {op.stats.total > 0 && (
                          <button className="opening-btn opening-btn--results"
                            onClick={() => { setViewingOpeningId(op.id); handleNavigate('rankings') }}>
                            🏆 View Results &amp; Rankings
                          </button>
                        )}
                      </>
                    )}
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
              {activeOpening && (
                <div className="opening-context-bar">
                  <span className="opening-context-label">📁 {activeOpening.title}</span>
                  <button className="opening-context-clear" onClick={() => setActiveOpening(null)} title="Unlink opening">✕</button>
                </div>
              )}
              {!activeOpening && openings.length > 0 && (
                <div className="opening-context-bar opening-context-bar--empty">
                  <span style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>No opening selected — </span>
                  <select className="opening-context-select" value="" onChange={e => setActiveOpening(e.target.value)}>
                    <option value="" disabled>select a job opening to pre-fill JD</option>
                    {openings.map(o => <option key={o.id} value={o.id}>{o.title}</option>)}
                  </select>
                </div>
              )}
              <InputSection
                key={activeOpeningId || 'single-no-opening'}
                mode="single"
                defaultJd={defaultJd}
                onAnalyze={handleAnalyze}
                onClear={handleClearAll}
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
              {activeOpening && (
                <div className="opening-context-bar">
                  <span className="opening-context-label">📁 {activeOpening.title}</span>
                  <button className="opening-context-clear" onClick={() => setActiveOpening(null)} title="Unlink opening">✕</button>
                </div>
              )}
              {!activeOpening && openings.length > 0 && !batchId && (
                <div className="opening-context-bar opening-context-bar--empty">
                  <span style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>No opening selected — </span>
                  <select className="opening-context-select" value="" onChange={e => setActiveOpening(e.target.value)}>
                    <option value="" disabled>select a job opening to pre-fill JD</option>
                    {openings.map(o => <option key={o.id} value={o.id}>{o.title}</option>)}
                  </select>
                </div>
              )}
              {!batchId && (
                <InputSection
                  key={activeOpeningId || 'batch-no-opening'}
                  mode="batch"
                  defaultJd={defaultJd}
                  onAnalyze={handleAnalyze}
                  onClear={handleClearAll}
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
                    onCallCandidate={handleCallCandidate}
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
          {activePage === 'rankings' && (() => {
            const viewOpening = viewingOpeningId ? openings.find(o => o.id === viewingOpeningId) : null
            const savedCandidates = viewOpening?.candidates?.length > 0 ? viewOpening.candidates : null
            const liveCandidates  = batchData?.candidates?.length > 0   ? batchData.candidates   : null
            const rankCandidates  = savedCandidates || liveCandidates
            return rankCandidates
              ? (
                <div>
                  {viewOpening && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                      <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text)' }}>
                        {viewOpening.title}
                      </div>
                      <span className="char-count">{viewOpening.candidates.length} candidate{viewOpening.candidates.length !== 1 ? 's' : ''} · all runs</span>
                      <button className="btn-clear" style={{ marginLeft: 'auto', padding: '4px 12px', fontSize: '0.8rem' }}
                        onClick={() => { setViewingOpeningId(null) }}>
                        Clear filter
                      </button>
                    </div>
                  )}
                  <BatchResultsTable
                    candidates={rankCandidates}
                    isComplete={true}
                    onCallCandidate={handleCallCandidate}
                  />
                </div>
              )
              : result
              ? (
                <div>
                  <div className="db-section-title" style={{ marginBottom: 16 }}>
                    Single Candidate Result
                  </div>
                  <div className="db-recent-card" onClick={() => handleNavigate('single')}
                    style={{ cursor: 'pointer', maxWidth: 560 }}>
                    <div className="db-recent-avatar">
                      {(result.name || '?')[0].toUpperCase()}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div className="db-recent-name">{result.name || 'Candidate'}</div>
                      <div className="db-recent-meta">
                        Resume score: {result.match_score || '—'}
                        {result.email ? ` · ${result.email}` : ''}
                      </div>
                    </div>
                    <span className={`score-verdict ${
                      (parseInt(result.match_score) || 0) >= 75 ? 'verdict-high'
                      : (parseInt(result.match_score) || 0) >= 60 ? 'verdict-medium'
                      : 'verdict-low'
                    }`} style={{ fontSize: '0.75rem' }}>
                      {result.verdict || 'Analyzed'}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-2)', marginTop: 12 }}>
                    Click the card to view the full analysis. Run a batch to see ranked results across multiple candidates.
                  </p>
                  <button className="btn-analyze" style={{ marginTop: 16 }} onClick={() => handleNavigate('batch')}>
                    Run Batch Pipeline
                  </button>
                </div>
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
          })()}

        </main>
      </div>

      {/* ── Duplicate Candidate Modal ── */}
      {duplicateModal && (
        <div className="batch-modal-overlay" onClick={duplicateModal.onCancel}>
          <div
            className="batch-modal-panel"
            style={{ maxWidth: 460, padding: '32px 28px' }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ fontSize: '1.5rem', marginBottom: 10 }}>⚠️</div>
            <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-1)', marginBottom: 6 }}>
              Candidate Already Exists
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-2)', marginBottom: 20 }}>
              A candidate with the same{' '}
              {duplicateModal.existing.email && duplicateModal.existing.email === duplicateModal.existing.email
                ? 'email or name' : 'name'}{' '}
              was previously submitted to this opening.
            </div>

            <div style={{ background: 'var(--surface-2, #f8f9fa)', borderRadius: 10, padding: '14px 16px', marginBottom: 22 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                <div className="candidate-avatar candidate-avatar--sm">
                  {(duplicateModal.existing.name || '?')[0].toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-1)' }}>
                    {duplicateModal.existing.name || '—'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>
                    {duplicateModal.existing.email || duplicateModal.existing.file_name || '—'}
                  </div>
                </div>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-2)', display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div>
                  <span style={{ color: 'var(--text-3)' }}>Resume Score: </span>
                  <strong>{duplicateModal.existing.resume_score ?? '—'}</strong>
                  {duplicateModal.existing.resume_score != null && ' / 100'}
                </div>
                <div>
                  <span style={{ color: 'var(--text-3)' }}>Last Status: </span>
                  <strong>{candidateStatusLabel(duplicateModal.existing)}</strong>
                </div>
                {duplicateModal.existing.combined_score != null && (
                  <div>
                    <span style={{ color: 'var(--text-3)' }}>Combined Score: </span>
                    <strong>{duplicateModal.existing.combined_score}</strong>
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                className="btn-analyze"
                style={{ flex: 1, fontSize: '0.85rem', padding: '9px 0' }}
                onClick={duplicateModal.onAddAnyway}
              >
                Add Anyway
              </button>
              <button
                className="btn-clear"
                style={{ flex: 1, fontSize: '0.85rem', padding: '9px 0' }}
                onClick={duplicateModal.onCancel}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {visibleDueCallbacks.length > 0 && (
        <CallbackAlertModal
          callbacks={visibleDueCallbacks}
          onCall={(cb) => {
            handleCallCandidate({ interview_id: cb.interview_id, phone: cb.phone, file_name: null })
            setDismissedCallbacks(prev => ({ ...prev, [cb.interview_id]: Date.now() }))
          }}
          onSnooze={(cb) => setDismissedCallbacks(prev => ({ ...prev, [cb.interview_id]: Date.now() }))}
          onDismissAll={() => {
            const all = {}
            visibleDueCallbacks.forEach(cb => { all[cb.interview_id] = Date.now() })
            setDismissedCallbacks(prev => ({ ...prev, ...all }))
          }}
        />
      )}

    </div>
  )
}
