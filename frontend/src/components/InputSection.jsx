import { useState, useCallback, useRef } from 'react'

function PipelineIllustration() {
  return (
    <div className="pipeline-wrap">
      <svg viewBox="0 0 580 130" fill="none" xmlns="http://www.w3.org/2000/svg" className="pipeline-svg">
        {/* ── Node 1: Resume ── */}
        <circle cx="65" cy="65" r="48" fill="rgba(52,211,153,0.06)" stroke="rgba(52,211,153,0.18)" strokeWidth="1"/>
        <circle className="pipe-node-ring" cx="65" cy="65" r="48" fill="none" stroke="rgba(52,211,153,0.4)" strokeWidth="1"/>
        <text x="65" y="57" textAnchor="middle" fontSize="24" dominantBaseline="middle">📄</text>
        <text x="65" y="83" textAnchor="middle" fontSize="9" fill="#34d399" fontWeight="700" letterSpacing="1.5">RESUME</text>

        {/* ── Arrow 1→2 ── */}
        <line x1="116" y1="65" x2="164" y2="65" stroke="rgba(34,211,238,0.35)" strokeWidth="1.5" strokeDasharray="5 3" className="flow-line-1"/>
        <polygon points="161,60 170,65 161,70" fill="rgba(34,211,238,0.5)"/>

        {/* ── Node 2: AI Parse ── */}
        <circle cx="215" cy="65" r="48" fill="rgba(34,211,238,0.06)" stroke="rgba(34,211,238,0.18)" strokeWidth="1"/>
        <circle className="pipe-node-ring pipe-node-ring-2" cx="215" cy="65" r="48" fill="none" stroke="rgba(34,211,238,0.4)" strokeWidth="1"/>
        <text x="215" y="57" textAnchor="middle" fontSize="24" dominantBaseline="middle">🤖</text>
        <text x="215" y="83" textAnchor="middle" fontSize="9" fill="#22d3ee" fontWeight="700" letterSpacing="1.5">AI PARSE</text>

        {/* ── Arrow 2→3 ── */}
        <line x1="266" y1="65" x2="314" y2="65" stroke="rgba(167,139,250,0.35)" strokeWidth="1.5" strokeDasharray="5 3" className="flow-line-2"/>
        <polygon points="311,60 320,65 311,70" fill="rgba(167,139,250,0.5)"/>

        {/* ── Node 3: Scoring ── */}
        <circle cx="365" cy="65" r="48" fill="rgba(167,139,250,0.06)" stroke="rgba(167,139,250,0.18)" strokeWidth="1"/>
        <circle className="pipe-node-ring pipe-node-ring-3" cx="365" cy="65" r="48" fill="none" stroke="rgba(167,139,250,0.4)" strokeWidth="1"/>
        <text x="365" y="57" textAnchor="middle" fontSize="24" dominantBaseline="middle">🎯</text>
        <text x="365" y="83" textAnchor="middle" fontSize="9" fill="#a78bfa" fontWeight="700" letterSpacing="1.5">SCORING</text>

        {/* ── Arrow 3→4 ── */}
        <line x1="416" y1="65" x2="464" y2="65" stroke="rgba(251,191,36,0.35)" strokeWidth="1.5" strokeDasharray="5 3" className="flow-line-3"/>
        <polygon points="461,60 470,65 461,70" fill="rgba(251,191,36,0.5)"/>

        {/* ── Node 4: Interview ── */}
        <circle cx="515" cy="65" r="48" fill="rgba(251,191,36,0.06)" stroke="rgba(251,191,36,0.18)" strokeWidth="1"/>
        <circle className="pipe-node-ring pipe-node-ring-4" cx="515" cy="65" r="48" fill="none" stroke="rgba(251,191,36,0.4)" strokeWidth="1"/>
        <text x="515" y="57" textAnchor="middle" fontSize="24" dominantBaseline="middle">📞</text>
        <text x="515" y="83" textAnchor="middle" fontSize="9" fill="#fbbf24" fontWeight="700" letterSpacing="1.5">INTERVIEW</text>
      </svg>
    </div>
  )
}

const PILLS = [
  { icon: '⚡', label: 'Instant Analysis' },
  { icon: '🧠', label: 'Claude AI Powered' },
  { icon: '🎯', label: 'Smart JD Matching' },
  { icon: '📞', label: 'Twilio Phone Interviews' },
  { icon: '🔊', label: 'Groq Whisper STT' },
]

const RESUME_PLACEHOLDER = `Paste the candidate's full resume here...

Example:
John Doe
john@email.com | +91-9876543210

Skills: Python, Machine Learning, NLP, Docker...
Experience: 3 years at ABC Corp as ML Engineer...`

const JD_PLACEHOLDER = `Paste the job description here...

Example:
Job Title: Machine Learning Engineer
Required Skills: Python, TensorFlow, NLP...
Experience: 2-4 years...`

export default function InputSection({ onAnalyze, loading, error }) {
  const [resume,      setResume]      = useState('')
  const [jd,          setJd]          = useState('')
  const [uploading,   setUploading]   = useState(false)
  const [fileName,    setFileName]    = useState('')
  const [uploadErr,   setUploadErr]   = useState('')
  const [resumeDrag,  setResumeDrag]  = useState(false)
  const [jdDrag,      setJdDrag]      = useState(false)
  const fileInputRef = useRef(null)

  const handleSubmit = useCallback(() => {
    if (!resume.trim() || !jd.trim()) return
    onAnalyze(resume, jd)
  }, [resume, jd, onAnalyze])

  const handleKeyDown = useCallback((e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') handleSubmit()
  }, [handleSubmit])

  const handleClear = () => { setResume(''); setJd(''); setFileName(''); setUploadErr('') }

  const uploadFile = async (file) => {
    setUploading(true)
    setUploadErr('')
    setFileName(file.name)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch('/upload-resume', { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
      const data = await res.json()
      setResume(data.resume_text)
    } catch (e) {
      setUploadErr(e.message || 'Failed to parse file.')
      setFileName('')
    } finally {
      setUploading(false)
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    await uploadFile(file)
    e.target.value = ''
  }

  const handleResumeDrop = async (e) => {
    e.preventDefault()
    setResumeDrag(false)
    const file = e.dataTransfer.files?.[0]
    if (file) await uploadFile(file)
  }

  const handleJdDrop = (e) => {
    e.preventDefault()
    setJdDrag(false)
    const file = e.dataTransfer.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setJd(ev.target.result || '')
    reader.readAsText(file)
  }

  return (
    <section className="input-section" onKeyDown={handleKeyDown}>

      {/* Hero */}
      <div className="hero">
        <div className="hero-eyebrow">
          <span className="hero-dot" />
          Powered by Claude AI · Groq Whisper · Twilio
        </div>
        <h2 className="hero-title">
          AI Recruitment <span className="hero-gradient">Intelligence</span>
        </h2>
        <p className="hero-sub">
          Parse resumes, score candidates against job requirements, and run fully automated AI-powered phone interviews — all in one seamless flow.
        </p>
        <PipelineIllustration />
        <div className="feature-pills">
          {PILLS.map(p => (
            <div key={p.label} className="feature-pill">
              <span className="feature-pill-icon">{p.icon}</span>
              {p.label}
            </div>
          ))}
        </div>
      </div>

      <div className="input-grid">
        {/* Resume */}
        <div
          className={`input-card${resumeDrag ? ' drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setResumeDrag(true) }}
          onDragLeave={() => setResumeDrag(false)}
          onDrop={handleResumeDrop}
        >
          <div className="input-card-header">
            <div className="input-card-title">
              <span className="icon">📄</span>
              Resume Text
            </div>
            <div className="resume-header-right">
              {fileName && !uploadErr && (
                <span className="upload-filename">{fileName}</span>
              )}
              <button
                className="btn-upload-pdf"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading || loading}
                title="Upload PDF or DOCX resume"
              >
                {uploading ? <><div className="spinner-sm" /> Parsing...</> : <>Upload PDF</>}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <span className="char-count">{resume.length} chars</span>
            </div>
          </div>
          {uploadErr && <div className="upload-error">{uploadErr}</div>}
          <textarea
            className="input-area"
            placeholder={RESUME_PLACEHOLDER}
            value={resume}
            onChange={e => setResume(e.target.value)}
            spellCheck={false}
          />
        </div>

        {/* JD */}
        <div
          className={`input-card${jdDrag ? ' drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setJdDrag(true) }}
          onDragLeave={() => setJdDrag(false)}
          onDrop={handleJdDrop}
        >
          <div className="input-card-header">
            <div className="input-card-title">
              <span className="icon">📋</span>
              Job Description
            </div>
            <span className="char-count">{jd.length} chars</span>
          </div>
          <textarea
            className="input-area"
            placeholder={JD_PLACEHOLDER}
            value={jd}
            onChange={e => setJd(e.target.value)}
            spellCheck={false}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="btn-row">
        <button
          className="btn-analyze"
          onClick={handleSubmit}
          disabled={loading || !resume.trim() || !jd.trim()}
        >
          {loading
            ? <><div className="spinner" /> Analyzing...</>
            : <>⚡ Analyze Resume</>
          }
        </button>
        <button className="btn-clear" onClick={handleClear} disabled={loading}>
          Clear
        </button>
      </div>
      <p className="hint">
        Press <kbd>Ctrl</kbd>+<kbd>Enter</kbd> to analyze
      </p>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}
    </section>
  )
}
