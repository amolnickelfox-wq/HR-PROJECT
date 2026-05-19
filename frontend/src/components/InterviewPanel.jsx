import { useState } from 'react'

const METRICS = [
  {
    key:    'communication',
    label:  'Communication',
    icon:   '🗣️',
    max:    35,
    color:  '#22d3ee',
    bg:     'rgba(34,211,238,0.1)',
    border: 'rgba(34,211,238,0.25)',
  },
  {
    key:    'confidence',
    label:  'Confidence',
    icon:   '💪',
    max:    30,
    color:  '#a78bfa',
    bg:     'rgba(167,139,250,0.1)',
    border: 'rgba(167,139,250,0.25)',
  },
  {
    key:    'motivation_fit',
    label:  'Motivation & Fit',
    icon:   '🎯',
    max:    20,
    color:  '#34d399',
    bg:     'rgba(52,211,153,0.1)',
    border: 'rgba(52,211,153,0.25)',
  },
  {
    key:    'behavioral_quality',
    label:  'Behavioral Quality',
    icon:   '🧠',
    max:    15,
    color:  '#f472b6',
    bg:     'rgba(244,114,182,0.1)',
    border: 'rgba(244,114,182,0.25)',
  },
]

function VerdictBadge({ verdict }) {
  const map = {
    'Strongly Recommended': 'verdict--green',
    'Recommended':          'verdict--blue',
    'Consider':             'verdict--yellow',
    'Not Recommended':      'verdict--red',
  }
  return (
    <span className={`verdict-badge ${map[verdict] || 'verdict--blue'}`}>
      {verdict}
    </span>
  )
}

function MetricCard({ metric, score }) {
  const pct = Math.round((score / metric.max) * 100)
  return (
    <div className="iv-metric-card" style={{ borderColor: metric.border }}>
      <div className="iv-metric-icon" style={{ background: metric.bg, borderColor: metric.border }}>
        {metric.icon}
      </div>
      <div className="iv-metric-label">{metric.label}</div>
      <div className="iv-metric-score">
        <span className="iv-metric-num" style={{ color: metric.color }}>{score}</span>
        <span className="iv-metric-max">/{metric.max}</span>
      </div>
      <div className="iv-bar-track" style={{ marginTop: 10 }}>
        <div
          className="iv-bar-fill"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${metric.color}, ${metric.color}99)`,
            boxShadow: `0 0 8px ${metric.color}55`,
          }}
        />
      </div>
      <div className="iv-metric-pct" style={{ color: metric.color }}>{pct}%</div>
    </div>
  )
}

function fmt(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
      + ' · '
      + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function callDuration(start, end) {
  if (!start || !end) return null
  const secs = Math.round((new Date(end) - new Date(start)) / 1000)
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

function CallLogBadge({ status, failReason, callbackScheduledAt, isCallback }) {
  let label, cls
  if (status === 'completed')  { label = '✓ Completed';     cls = 'verdict-high'   }
  else if (status === 'calling' || status === 'processing') {
    label = isCallback ? '📞 Callback In Progress' : '📞 In Progress'
    cls = 'verdict-medium'
  }
  else if (status === 'callback_scheduled') {
    label = callbackScheduledAt
      ? `📅 Callback at ${fmt(callbackScheduledAt)}`
      : '📅 Callback Scheduled'
    cls = 'verdict-medium'
  }
  else if (status === 'abandoned') { label = '📵 Call Dropped';  cls = 'verdict-low'  }
  else if (status === 'failed') {
    const r = (failReason || '').toLowerCase()
    label = r.includes('not answered') ? '📵 Not Answered'
          : r.includes('busy')         ? '📵 Line Busy'
          : '✕ Failed'
    cls = 'verdict-low'
  } else { label = status; cls = '' }

  return (
    <span className={`score-verdict ${cls}`} style={{ fontSize: '0.7rem' }}>
      {label}
    </span>
  )
}

export default function InterviewPanel({ interview }) {
  const [showTranscript, setShowTranscript] = useState(false)

  if (!interview) return null

  const { status, questions, score_result, transcript, call_log } = interview

  const totalScore = score_result
    ? (score_result.communication?.score      || 0) +
      (score_result.confidence?.score         || 0) +
      (score_result.motivation_fit?.score     || 0) +
      (score_result.behavioral_quality?.score || 0)
    : 0

  return (
    <div className="iv-panel">
      <div className="section-label" style={{ marginBottom: 16 }}>
        HR Phone Screening
      </div>

      {call_log?.length > 0 && (
        <div className="card iv-call-history">
          <div className="section-label" style={{ marginBottom: 10 }}>Call History</div>
          {call_log.map((entry, i) => (
            <div key={i} className="iv-call-entry">
              <div className="iv-call-attempt">
                #{entry.attempt}
                {entry.is_callback && (
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-3)', fontWeight: 400 }}>callback</div>
                )}
              </div>
              <div className="iv-call-meta">
                <div className="iv-call-time">{fmt(entry.started_at)}</div>
                {entry.ended_at && callDuration(entry.started_at, entry.ended_at) && (
                  <div className="iv-call-duration">
                    Duration: {callDuration(entry.started_at, entry.ended_at)}
                  </div>
                )}
              </div>
              <CallLogBadge
                status={entry.status}
                failReason={entry.fail_reason}
                callbackScheduledAt={entry.callback_scheduled_at}
                isCallback={entry.is_callback}
              />
            </div>
          ))}
        </div>
      )}

      {status === 'calling' && (
        <div className="iv-status iv-status--calling">
          <span className="iv-pulse" />
          Call in progress — waiting for candidate to complete interview…
        </div>
      )}

      {status === 'processing' && (
        <div className="iv-status iv-status--calling">
          <span className="iv-pulse" />
          {interview.processing_step
            ? `${interview.processing_step}…`
            : 'Processing interview — transcribing and scoring…'}
        </div>
      )}

      {status === 'abandoned' && (
        <div className="iv-status iv-status--failed">
          📵 Candidate ended the call before completing the interview.
        </div>
      )}

      {status === 'failed' && (() => {
        const r = (interview.fail_reason || '').toLowerCase()
        const msg = r.includes('not answered')
          ? 'Candidate did not answer the call.'
          : r.includes('busy')
          ? 'Candidate\'s line was busy.'
          : interview.fail_reason || 'Call could not be connected.'
        return (
          <div className="iv-status iv-status--failed">
            📵 {msg}
          </div>
        )
      })()}

      {questions && questions.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="section-label" style={{ marginBottom: 12 }}>Questions Asked</div>
          <ol className="iv-questions">
            {questions.map((q, i) => (
              <li key={i} className="iv-question-item">{q}</li>
            ))}
          </ol>
        </div>
      )}

      {status === 'completed' && score_result && (
        <>
          {/* Score header */}
          <div className="iv-result-header">
            <div className="iv-total-score">
              <div className="iv-score-num">{totalScore}</div>
              <div className="iv-score-denom">/100</div>
              <div className="iv-score-lbl">Overall Score</div>
            </div>
            <div className="iv-verdict-block">
              <VerdictBadge verdict={score_result.verdict} />
              <p className="iv-summary">{score_result.summary}</p>
            </div>
          </div>

          {/* Metric cards */}
          <div className="iv-metrics-grid">
            {METRICS.map(m => (
              <MetricCard
                key={m.key}
                metric={m}
                score={score_result[m.key]?.score || 0}
              />
            ))}
          </div>

          {/* Strengths & improvements */}
          <div className="iv-two-col">
            {score_result.strengths?.length > 0 && (
              <div className="card iv-strengths">
                <div className="section-label" style={{ marginBottom: 10 }}>Strengths</div>
                {score_result.strengths.map((s, i) => (
                  <div key={i} className="iv-bullet iv-bullet--green">✓ {s}</div>
                ))}
              </div>
            )}
            {score_result.improvements?.length > 0 && (
              <div className="card iv-improvements">
                <div className="section-label" style={{ marginBottom: 10 }}>Areas to Improve</div>
                {score_result.improvements.map((s, i) => (
                  <div key={i} className="iv-bullet iv-bullet--yellow">⚠ {s}</div>
                ))}
              </div>
            )}
          </div>

          {/* Transcript */}
          {transcript && (
            <div className="iv-transcript-section">
              <button
                className={`iv-transcript-btn ${showTranscript ? 'open' : ''}`}
                onClick={() => setShowTranscript(v => !v)}
              >
                <span>📋 {showTranscript ? 'Hide' : 'View'} Full Interview Transcript</span>
                <span className={`iv-chevron ${showTranscript ? 'open' : ''}`}>▼</span>
              </button>
              {showTranscript && (
                <div className="iv-transcript-body">
                  {transcript.split('\n\n').map((block, i) => {
                    const lines = block.split('\n')
                    return (
                      <div key={i} className="iv-transcript-block">
                        {lines.map((line, j) => (
                          <div
                            key={j}
                            className={line.startsWith('Q') ? 'iv-t-question' : 'iv-t-answer'}
                          >
                            {line}
                          </div>
                        ))}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
