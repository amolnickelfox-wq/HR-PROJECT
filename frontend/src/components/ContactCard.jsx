function ValidationBadge({ valid }) {
  return valid
    ? <span className="valid-badge">✓ Valid</span>
    : <span className="invalid-badge">✗ Invalid</span>
}

export default function ContactCard({ data, onStartInterview, callLoading, callError }) {
  const canCall = data.phone && data.phone_valid

  return (
    <div className="card">
      <div className="section-label">Contact Validation</div>

      <div className="contact-group">
        <div className="info-item">
          <div className="info-icon-wrap">✉</div>
          <div className="info-body">
            <div className="info-lbl">Email Address</div>
            <div className="info-val small">{data.email || 'Not found'}</div>
            <ValidationBadge valid={data.email_valid} />
          </div>
        </div>
      </div>

      <div className="contact-group">
        <div className="info-item">
          <div className="info-icon-wrap">📞</div>
          <div className="info-body">
            <div className="info-lbl">Phone Number</div>
            <div className="info-val">{data.phone || 'Not found'}</div>
            <ValidationBadge valid={data.phone_valid} />
          </div>
        </div>
      </div>

      {data.roles && data.roles.length > 0 && (
        <>
          <div className="section-label" style={{ marginTop: 18 }}>Work History</div>
          <div className="roles-list">
            {data.roles.map((r, i) => (
              <div key={i} className="role-item">💼 {r}</div>
            ))}
          </div>
        </>
      )}

      {/* Outbound call button */}
      <button
        className={`call-btn ${!canCall ? 'call-btn--disabled' : ''}`}
        onClick={onStartInterview}
        disabled={!canCall || callLoading}
        title={!canCall ? 'Valid phone number required' : 'Start AI phone interview'}
      >
        {callLoading
          ? <><span className="call-btn__spinner" /> Initiating Call…</>
          : <>📞 Start AI Interview Call</>
        }
      </button>

      {!canCall && (
        <div className="call-note">Valid phone number required to start interview</div>
      )}
      {callError && (
        <div className="call-error">{callError}</div>
      )}

    </div>
  )
}
