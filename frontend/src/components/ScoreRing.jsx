import { useEffect, useState } from 'react'

const R    = 68
const CIRC = 2 * Math.PI * R

function getColors(n) {
  if (n >= 80) return ['#34d399', '#22d3ee']
  if (n >= 60) return ['#fbbf24', '#fb923c']
  return ['#fb7185', '#f43f5e']
}

function getVerdict(n) {
  if (n >= 80) return { text: 'Strong Match',  cls: 'verdict-high' }
  if (n >= 60) return { text: 'Good Match',    cls: 'verdict-medium' }
  return             { text: 'Weak Match',     cls: 'verdict-low' }
}

export default function ScoreRing({ score }) {
  const num = parseInt(score) || 0
  const [displayed, setDisplayed] = useState(0)
  const [animated,  setAnimated]  = useState(false)

  useEffect(() => {
    setDisplayed(0)
    setAnimated(false)
    const t = setTimeout(() => setAnimated(true), 80)
    let frame = 0
    const total = 55
    const iv = setInterval(() => {
      frame++
      setDisplayed(Math.round((frame / total) * num))
      if (frame >= total) clearInterval(iv)
    }, 16)
    return () => { clearTimeout(t); clearInterval(iv) }
  }, [num])

  const offset   = CIRC - (num / 100) * CIRC
  const [c1, c2] = getColors(num)
  const verdict  = getVerdict(num)
  const gid      = `sg-${num}`

  return (
    <div className="card score-card">
      <div className="section-label" style={{ width: '100%', marginBottom: 20 }}>
        Match Score
      </div>
      <div className="score-ring">
        <svg width="165" height="165" viewBox="0 0 165 165">
          <defs>
            <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%"   stopColor={c1} />
              <stop offset="100%" stopColor={c2} />
            </linearGradient>
          </defs>
          {/* Subtle outer glow ring */}
          <circle cx="82.5" cy="82.5" r={R + 8} fill="none"
            stroke={c1} strokeWidth="1" strokeOpacity="0.1" />
          <circle className="ring-track"    cx="82.5" cy="82.5" r={R} />
          <circle
            className="ring-progress"
            cx="82.5" cy="82.5" r={R}
            stroke={`url(#${gid})`}
            strokeDasharray={CIRC}
            strokeDashoffset={animated ? offset : CIRC}
          />
        </svg>
        <div className="score-center">
          <span className="score-num" style={{ color: c1 }}>{displayed}</span>
          <span className="score-denom">/ 100</span>
        </div>
      </div>
      <span className={`score-verdict ${verdict.cls}`}>{verdict.text}</span>
    </div>
  )
}
