import { useEffect, useState } from 'react'

const LABELS = {
  skill_match:          { label: 'Skill Match',   icon: '🎯' },
  experience_relevance: { label: 'Experience',    icon: '⏱' },
  project_relevance:    { label: 'Projects',      icon: '🚀' },
  education:            { label: 'Education',     icon: '🎓' },
}

function BreakdownCard({ label, icon, score, max, weight, animate }) {
  const pct = Math.round((score / max) * 100)
  return (
    <div className="breakdown-card">
      <div className="bd-icon-wrap">{icon}</div>
      <div className="bd-label">{label}</div>
      <div className="bd-score">{score}</div>
      <div className="bd-max">/ {max} pts</div>
      <div className="bd-bar">
        <div className="bd-fill" style={{ width: animate ? `${pct}%` : '0%' }} />
      </div>
      <div className="bd-weight">{weight}</div>
    </div>
  )
}

export default function ScoreBreakdown({ breakdown }) {
  const [animate, setAnimate] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setAnimate(true), 200)
    return () => clearTimeout(t)
  }, [breakdown])

  return (
    <div style={{ marginBottom: 16 }}>
      <div className="section-label">Score Breakdown</div>
      <div className="breakdown-grid">
        {Object.entries(breakdown).map(([key, val]) => {
          const meta = LABELS[key] || { label: key, icon: '📊' }
          return (
            <BreakdownCard
              key={key}
              label={meta.label}
              icon={meta.icon}
              score={val.score}
              max={val.max}
              weight={val.weight}
              animate={animate}
            />
          )
        })}
      </div>
    </div>
  )
}
