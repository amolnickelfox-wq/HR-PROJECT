import { useState } from 'react'
import BatchCandidateModal from './BatchCandidateModal'

function scoreColor(n) {
  if (n == null) return 'batch-score-none'
  if (n >= 75)   return 'batch-score-high'
  if (n >= 60)   return 'batch-score-medium'
  return 'batch-score-low'
}

function fmtCallbackTime(iso) {
  try {
    const d = new Date(iso)
    return `📅 ${d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })} · ${d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`
  } catch { return '📅 Callback Scheduled' }
}

function StatusBadge({ c }) {
  const iid = c.interview_status
  const hasActiveCall = iid && iid !== 'pending'

  // no_phone is always terminal
  if (c.filter_status === 'no_phone') {
    return <span className="score-verdict" style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>No Phone</span>
  }
  // filtered_out: only show if no call has ever been made
  if (c.filter_status === 'filtered_out' && !hasActiveCall) {
    return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>Filtered Out</span>
  }
  if (iid === 'callback_scheduled') {
    const label = c.callback_scheduled_at
      ? fmtCallbackTime(c.callback_scheduled_at)
      : c.callback_time_raw
      ? `📅 "${c.callback_time_raw}"`
      : '📅 Callback Scheduled'
    return <span className="score-verdict verdict-medium" style={{ fontSize: '0.7rem' }}>{label}</span>
  }
  if (iid === 'calling' || iid === 'in_progress') {
    return <span className="score-verdict verdict-medium" style={{ fontSize: '0.7rem' }}>📞 Calling…</span>
  }
  if (iid === 'processing') {
    const step = c.processing_step
    return <span className="score-verdict verdict-medium" style={{ fontSize: '0.7rem' }}>⚙ {step || 'Processing…'}</span>
  }
  if (iid === 'retry_queued') {
    return <span className="score-verdict verdict-medium" style={{ fontSize: '0.7rem' }}>🔄 Retry Queued</span>
  }
  if (iid === 'abandoned') {
    return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>📵 Call Dropped</span>
  }
  if (iid === 'failed') {
    const r = (c.fail_reason || '').toLowerCase()
    if (r.includes('not answered'))
      return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>📵 Not Answered</span>
    if (r.includes('busy'))
      return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>📵 Line Busy</span>
    return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>✕ Call Failed</span>
  }
  if (iid === 'timeout') {
    return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>Timed Out</span>
  }
  const verdict = c.score_result?.verdict
  if (verdict) {
    const cls = verdict.includes('Strongly') || verdict === 'Recommended'
      ? 'verdict-high'
      : verdict === 'Consider' ? 'verdict-medium' : 'verdict-low'
    return <span className={`score-verdict ${cls}`} style={{ fontSize: '0.7rem' }}>{verdict}</span>
  }
  return <span className="score-verdict" style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>—</span>
}

export default function BatchResultsTable({ candidates, isComplete = true, onCallCandidate }) {
  const [selected, setSelected] = useState(null)

  const sorted = [...candidates].sort((a, b) => {
    const aQ = a.filter_status === 'qualified'
    const bQ = b.filter_status === 'qualified'
    if (aQ && bQ) return (b.combined_score ?? b.resume_score ?? 0) - (a.combined_score ?? a.resume_score ?? 0)
    if (aQ) return -1
    if (bQ) return 1
    return (b.resume_score ?? 0) - (a.resume_score ?? 0)
  })

  const qualified  = candidates.filter(c => c.filter_status === 'qualified').length
  const filtered   = candidates.filter(c => c.filter_status === 'filtered_out' || c.filter_status === 'no_phone').length
  const doneCount  = candidates.filter(c =>
    ['completed', 'abandoned', 'failed', 'callback_scheduled', 'skipped', 'no_phone'].includes(c.interview_status)
  ).length

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <span className="section-label">
          {isComplete ? 'Final Rankings' : 'Live Rankings'}
        </span>
        <span className="char-count">
          {isComplete
            ? `${qualified} interviewed · ${filtered} filtered out`
            : `${doneCount} of ${candidates.length} done · click any row for details`
          }
        </span>
      </div>

      <div className="batch-table-wrap">
        <table className="batch-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Candidate</th>
              <th>Resume Score</th>
              <th>Interview Score</th>
              <th>Combined</th>
              <th>Status</th>
              {onCallCandidate && <th></th>}
            </tr>
          </thead>
          <tbody>
            {sorted.map((c, i) => (
              <tr key={i} className="batch-table-row--clickable" onClick={() => setSelected(c)}>
                <td>
                  <span className="batch-rank">#{i + 1}</span>
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div className="candidate-avatar candidate-avatar--sm">
                      {(c.name || c.file_name || '?')[0].toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-1)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {c.name || '—'}
                        {c._duplicate_of && (
                          <span title="This candidate was already in this opening" style={{ fontSize: '0.65rem', background: '#fef3c7', color: '#92400e', borderRadius: 4, padding: '1px 5px', fontWeight: 600 }}>
                            duplicate
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-3)' }}>
                        {c.email || c.file_name}
                      </div>
                    </div>
                  </div>
                </td>
                <td>
                  {c.resume_score != null
                    ? (
                      <span className={`batch-score-num ${scoreColor(c.resume_score)}`}>
                        {c.resume_score}
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-3)', fontWeight: 400 }}> / 100</span>
                      </span>
                    )
                    : <span className="batch-score-none">—</span>
                  }
                </td>
                <td>
                  {c.interview_score != null
                    ? (
                      <span className={`batch-score-num ${scoreColor(c.interview_score)}`}>
                        {c.interview_score}
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-3)', fontWeight: 400 }}> / 100</span>
                      </span>
                    )
                    : <span className="batch-score-none">—</span>
                  }
                </td>
                <td>
                  {c.combined_score != null
                    ? <span className="batch-combined-score">{c.combined_score}</span>
                    : <span className="batch-score-none">—</span>
                  }
                </td>
                <td>
                  <StatusBadge c={c} />
                </td>
                {onCallCandidate && (
                  <td onClick={e => e.stopPropagation()}>
                    {c.phone && c.filter_status !== 'no_phone' && (
                      <button
                        className={`batch-call-btn${c.filter_status === 'filtered_out' ? ' batch-call-btn--filtered' : ''}`}
                        title={c.filter_status === 'filtered_out' ? 'Call (below threshold)' : 'Call Candidate'}
                        onClick={() => onCallCandidate(c)}
                      >
                        {c.filter_status === 'filtered_out' ? '📞' : '📞 Call'}
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <BatchCandidateModal
          candidate={selected}
          onClose={() => setSelected(null)}
          onCallCandidate={onCallCandidate}
        />
      )}
    </div>
  )
}
