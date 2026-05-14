import { useState } from 'react'
import BatchCandidateModal from './BatchCandidateModal'

function scoreColor(n) {
  if (n == null) return 'batch-score-none'
  if (n >= 75)   return 'batch-score-high'
  if (n >= 60)   return 'batch-score-medium'
  return 'batch-score-low'
}

function StatusBadge({ c }) {
  if (c.filter_status === 'filtered_out') {
    return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>Filtered Out</span>
  }
  if (c.filter_status === 'no_phone') {
    return <span className="score-verdict" style={{ fontSize: '0.7rem', color: 'var(--text-3)' }}>No Phone</span>
  }
  if (c.interview_status === 'callback_scheduled') {
    let label = '📅 Callback'
    if (c.callback_scheduled_at) {
      try {
        const d = new Date(c.callback_scheduled_at)
        label = `📅 ${d.toLocaleDateString('en-IN', { weekday: 'short' })} ${d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`
      } catch (_) {}
    }
    return <span className="score-verdict verdict-medium" style={{ fontSize: '0.7rem' }}>{label}</span>
  }
  if (c.interview_status === 'failed' || c.interview_status === 'abandoned') {
    return <span className="score-verdict verdict-low" style={{ fontSize: '0.7rem' }}>Call Failed</span>
  }
  if (c.interview_status === 'timeout') {
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

export default function BatchResultsTable({ candidates }) {
  const [selected, setSelected] = useState(null)

  const sorted = [...candidates].sort((a, b) => {
    const aQ = a.filter_status === 'qualified'
    const bQ = b.filter_status === 'qualified'
    if (aQ && bQ) return (b.combined_score ?? b.resume_score ?? 0) - (a.combined_score ?? a.resume_score ?? 0)
    if (aQ) return -1
    if (bQ) return 1
    return (b.resume_score ?? 0) - (a.resume_score ?? 0)
  })

  const qualified = candidates.filter(c => c.filter_status === 'qualified').length
  const filtered  = candidates.filter(c => c.filter_status === 'filtered_out' || c.filter_status === 'no_phone').length

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <span className="section-label">Final Rankings</span>
        <span className="char-count">
          {qualified} interviewed · {filtered} filtered out
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
                      <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-1)' }}>
                        {c.name || '—'}
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <BatchCandidateModal candidate={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
