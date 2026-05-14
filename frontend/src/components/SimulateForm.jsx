import { useState } from 'react'

export default function SimulateForm({ questions, onSubmit, onCancel, loading }) {
  const [answers, setAnswers] = useState(questions.map(() => ''))

  const setAnswer = (i, val) => setAnswers(prev => prev.map((a, idx) => idx === i ? val : a))

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="section-label" style={{ marginBottom: 16 }}>Simulate Interview — Type Your Answers</div>

      {questions.map((q, i) => (
        <div key={i} style={{ marginBottom: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-primary, #e2e8f0)', fontSize: '0.9rem' }}>
            Q{i + 1}: {q}
          </div>
          <textarea
            rows={3}
            placeholder="Type your answer here…"
            value={answers[i]}
            onChange={e => setAnswer(i, e.target.value)}
            style={{
              width: '100%',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 8,
              color: 'inherit',
              padding: '10px 12px',
              fontSize: '0.875rem',
              resize: 'vertical',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      ))}

      <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
        <button
          className="call-btn"
          onClick={() => onSubmit(answers)}
          disabled={loading}
          style={{ flex: 1 }}
        >
          {loading ? <><span className="call-btn__spinner" /> Scoring…</> : '▶ Submit & Score Answers'}
        </button>
        <button
          onClick={onCancel}
          disabled={loading}
          style={{
            padding: '10px 18px',
            borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.15)',
            background: 'transparent',
            color: 'inherit',
            cursor: 'pointer',
            fontSize: '0.875rem',
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
