import { useState } from 'react'

function highlight(json) {
  return json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let cls = 'json-num'
        if (/^"/.test(match)) {
          cls = /:$/.test(match) ? 'json-key' : 'json-str'
        } else if (/true|false/.test(match)) {
          cls = 'json-bool'
        } else if (/null/.test(match)) {
          cls = 'json-null'
        }
        return `<span class="${cls}">${match}</span>`
      }
    )
}

export default function JsonViewer({ data }) {
  const [open, setOpen] = useState(false)

  const cleanOutput = {
    name:             data.name,
    email:            data.email,
    phone:            data.phone,
    skills:           data.skills,
    experience_years: data.experience_years,
    match_score:      data.match_score,
    matching_skills:  data.matching_skills,
    missing_skills:   data.missing_skills,
    experience_fit:   data.experience_fit,
    reason:           data.reason,
  }

  const formatted = JSON.stringify(cleanOutput, null, 2)

  return (
    <div className="card json-viewer-card">
      <div className="section-label">Raw JSON Output</div>
      <button
        className={`json-toggle-btn ${open ? 'open' : ''}`}
        onClick={() => setOpen(v => !v)}
      >
        <span className="toggle-icon">▶</span>
        {open ? 'Hide' : 'Show'} JSON Output
      </button>
      {open && (
        <pre
          className="json-block"
          dangerouslySetInnerHTML={{ __html: highlight(formatted) }}
        />
      )}
    </div>
  )
}
