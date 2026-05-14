function fitClass(fit) {
  const f = (fit || '').toLowerCase()
  if (f === 'good')    return 'fit-badge fit-good'
  if (f === 'average') return 'fit-badge fit-average'
  return 'fit-badge fit-poor'
}

function Avatar({ name }) {
  const initials = (name || '?')
    .split(' ')
    .filter(Boolean)
    .map(w => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
  return <div className="candidate-avatar">{initials}</div>
}

export default function CandidateCard({ data }) {
  const edu = data.education?.[0] || 'N/A'

  return (
    <div className="card">
      <Avatar name={data.name} />
      <div className="section-label">Candidate Profile</div>
      <div className="info-list">
        <div className="info-item">
          <div className="info-icon-wrap">👤</div>
          <div className="info-body">
            <div className="info-lbl">Full Name</div>
            <div className="info-val">{data.name || 'N/A'}</div>
          </div>
        </div>

        <div className="info-item">
          <div className="info-icon-wrap">⏱</div>
          <div className="info-body">
            <div className="info-lbl">Experience</div>
            <div className="info-val">{data.experience_years || 'N/A'}</div>
          </div>
        </div>

        <div className="info-item">
          <div className="info-icon-wrap">📊</div>
          <div className="info-body">
            <div className="info-lbl">Experience Fit</div>
            <div className="info-val">
              <span className={fitClass(data.experience_fit)}>
                {data.experience_fit || 'N/A'}
              </span>
            </div>
          </div>
        </div>

        <div className="info-item">
          <div className="info-icon-wrap">🎓</div>
          <div className="info-body">
            <div className="info-lbl">Education</div>
            <div className="info-val small">{edu}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
