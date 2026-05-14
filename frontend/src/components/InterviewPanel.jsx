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

export default function InterviewPanel({ interview }) {
  const [showTranscript, setShowTranscript] = useState(false)

  if (!interview) return null

  const { status, questions, score_result, transcript } = interview

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

      {status === 'calling' && (
        <div className="iv-status iv-status--calling">
          <span className="iv-pulse" />
          Call in progress — waiting for candidate to complete interview…
        </div>
      )}

      {status === 'processing' && (
        <div className="iv-status iv-status--calling">
          <span className="iv-pulse" />
          Processing interview — transcribing and scoring…
        </div>
      )}

      {status === 'abandoned' && (
        <div className="iv-status iv-status--failed">
          ⚠️ {interview.fail_reason || 'Candidate disconnected before completing the interview.'}
        </div>
      )}

      {status === 'failed' && (
        <div className="iv-status iv-status--failed">
          ✕ {interview.fail_reason || 'Call could not be connected.'}
        </div>
      )}

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
