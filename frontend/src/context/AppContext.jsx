import { createContext, useContext, useState, useEffect, useRef } from 'react'
import { apiCallbacksDue, apiGetOpenings, apiCreateOpening, apiUpdateOpening, apiDeleteOpening } from '../api/client'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  // ── all-time stats (localStorage) ──
  const [allTime, setAllTime] = useState(() => {
    try {
      const s = localStorage.getItem('recruitai_stats')
      return s ? JSON.parse(s) : { total: 0, qualified: 0, done: 0, batches: [] }
    } catch {
      return { total: 0, qualified: 0, done: 0, batches: [] }
    }
  })

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

  // ── job openings (localStorage + backend) ──
  const [openings, setOpenings] = useState(() => {
    try {
      const s = localStorage.getItem('recruitai_openings')
      return s ? JSON.parse(s) : []
    } catch { return [] }
  })

  // Sync openings from backend on mount — merges DB openings with localStorage candidates
  useEffect(() => {
    apiGetOpenings().then(r => r.json()).then(dbOpenings => {
      if (!Array.isArray(dbOpenings) || dbOpenings.length === 0) return
      setOpenings(prev => {
        const prevMap = Object.fromEntries(prev.map(o => [o.id, o]))
        const merged = dbOpenings.map(dbo => ({
          id:         dbo.id,
          title:      dbo.title,
          jd:         dbo.jd || '',
          createdAt:  dbo.createdAt || '',
          stats:      prevMap[dbo.id]?.stats      || { total: 0, qualified: 0, done: 0 },
          batchIds:   prevMap[dbo.id]?.batchIds   || [],
          candidates: prevMap[dbo.id]?.candidates || [],
        }))
        try { localStorage.setItem('recruitai_openings', JSON.stringify(merged)) } catch {}
        return merged
      })
    }).catch(() => {})
  }, [])

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
  const defaultJd     = activeOpening?.jd || ''

  // ── opening form state ──
  const [showOpeningForm,  setShowOpeningForm]  = useState(false)
  const [newOpeningTitle,  setNewOpeningTitle]  = useState('')
  const [newOpeningJd,     setNewOpeningJd]     = useState('')
  const [editingOpeningId, setEditingOpeningId] = useState(null)
  const [editingJd,        setEditingJd]        = useState('')
  const [viewingOpeningId, setViewingOpeningId] = useState(null)
  const [duplicateModal,   setDuplicateModal]   = useState(null)

  // ── callbacks ──
  const [dueCallbacks,       setDueCallbacks]       = useState([])
  const [dismissedCallbacks, setDismissedCallbacks] = useState({})
  const callbackAlertRef = useRef(null)

  // Poll /callbacks/due every 60s
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await apiCallbacksDue()
        if (!res.ok) return
        const data = await res.json()
        setDueCallbacks(data.due || [])
      } catch (_) {}
    }
    poll()
    callbackAlertRef.current = setInterval(poll, 60_000)
    return () => clearInterval(callbackAlertRef.current)
  }, [])

  // ── opening management functions ──
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
      id:        Date.now().toString(),
      title:     newOpeningTitle.trim(),
      jd:        newOpeningJd.trim(),
      createdAt: new Date().toISOString().slice(0, 10),
      stats:     { total: 0, qualified: 0, done: 0 },
      batchIds:  [],
      candidates: [],
    }
    const next = [...openings, o]
    setOpenings(next); saveOpenings(next)
    setNewOpeningTitle(''); setNewOpeningJd(''); setShowOpeningForm(false)
    apiCreateOpening({ id: o.id, title: o.title, jd: o.jd, createdAt: o.createdAt }).catch(() => {})
  }

  const deleteOpening = (id) => {
    const next = openings.filter(o => o.id !== id)
    setOpenings(next); saveOpenings(next)
    if (activeOpeningId === id) { setActiveOpening(null); setViewingOpeningId(null) }
    if (viewingOpeningId === id) setViewingOpeningId(null)
    apiDeleteOpening(id).catch(() => {})
  }

  const updateOpeningJd = (id, jd) => {
    const next = openings.map(o => o.id === id ? { ...o, jd } : o)
    setOpenings(next); saveOpenings(next)
    setEditingOpeningId(null); setEditingJd('')
    apiUpdateOpening(id, { jd }).catch(() => {})
  }

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

  return (
    <AppContext.Provider value={{
      allTime, addAllTime, resetAllTime,
      openings, setOpenings, saveOpenings,
      activeOpeningId, setActiveOpening, activeOpening, defaultJd,
      showOpeningForm, setShowOpeningForm,
      newOpeningTitle, setNewOpeningTitle,
      newOpeningJd, setNewOpeningJd,
      editingOpeningId, setEditingOpeningId,
      editingJd, setEditingJd,
      viewingOpeningId, setViewingOpeningId,
      duplicateModal, setDuplicateModal,
      dueCallbacks, dismissedCallbacks, setDismissedCallbacks,
      createOpening, deleteOpening, updateOpeningJd,
      addSingleToOpening, updateSingleInterviewInOpening,
      saveOpeningBatch, syncBatchToOpenings,
      findDuplicateInOpening, candidateStatusLabel,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export const useAppContext = () => useContext(AppContext)
