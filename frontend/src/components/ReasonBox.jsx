export default function ReasonBox({ reason }) {
  if (!reason) return null
  return (
    <div className="reason-box">
      <span className="reason-emoji">💡</span>
      <div className="reason-content">
        <div className="reason-label">AI Analysis & Verdict</div>
        <p className="reason-text">{reason}</p>
      </div>
    </div>
  )
}
