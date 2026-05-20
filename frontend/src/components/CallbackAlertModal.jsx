import { useState } from 'react'

function fmt(iso) {
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
      + ' · '
      + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

export default function CallbackAlertModal({ callbacks, onCall, onSnooze, onDismissAll }) {
  const [calling, setCalling] = useState(null)

  return (
    <div className="batch-modal-overlay" style={{ alignItems: 'center' }}>
      <div className="batch-modal-panel" style={{ maxWidth: 480 }}>
        <div className="batch-modal-header">
          <div className="batch-modal-title">📅 Callback Due</div>
          <button className="batch-modal-back" onClick={onDismissAll} title="Snooze all 10 min">✕</button>
        </div>
        <div className="batch-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {callbacks.map(cb => (
            <div key={cb.interview_id} className="card" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div className="candidate-avatar candidate-avatar--sm">
                {(cb.candidate_name || '?')[0].toUpperCase()}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-1)' }}>
                  {cb.candidate_name || 'Candidate'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-3)', marginTop: 2 }}>
                  {cb.job_title && <span>{cb.job_title} · </span>}
                  Requested: {cb.callback_time_raw || fmt(cb.callback_scheduled_at)}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-3)' }}>
                  Scheduled: {fmt(cb.callback_scheduled_at)}
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <button
                  className="btn-analyze"
                  style={{ padding: '6px 14px', fontSize: '0.8rem' }}
                  disabled={calling === cb.interview_id}
                  onClick={() => { setCalling(cb.interview_id); onCall(cb) }}
                >
                  {calling === cb.interview_id ? 'Calling…' : '📞 Call Now'}
                </button>
                <button
                  className="btn-clear"
                  style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  onClick={() => onSnooze(cb)}
                >
                  Snooze 10 min
                </button>
              </div>
            </div>
          ))}
          <p style={{ fontSize: '0.72rem', color: 'var(--text-3)', textAlign: 'center', margin: 0 }}>
            Auto-dial is also scheduled — this is an early alert for HR.
          </p>
        </div>
      </div>
    </div>
  )
}
