import { useState, useRef } from 'react'

const ACCEPTED_EXT = ['.pdf', '.docx', '.doc']

export default function BatchDropZone({ files, onFilesChange, disabled }) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const addFiles = (newFiles) => {
    const accepted = Array.from(newFiles).filter(f =>
      ACCEPTED_EXT.some(ext => f.name.toLowerCase().endsWith(ext))
    )
    const existing = new Set(files.map(f => f.name))
    const merged   = [...files, ...accepted.filter(f => !existing.has(f.name))]
    onFilesChange(merged)
  }

  const removeFile = (name) => onFilesChange(files.filter(f => f.name !== name))

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    if (!disabled) addFiles(e.dataTransfer.files)
  }

  return (
    <div
      className={`batch-drop-zone input-card${dragOver ? ' drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      style={{ cursor: disabled ? 'default' : 'pointer' }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc"
        style={{ display: 'none' }}
        onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
        disabled={disabled}
      />

      <div className="batch-drop-icon">📂</div>
      <p className="batch-drop-hint">
        Drag &amp; drop PDF / DOCX resumes here
        <br />
        <span style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>
          or click to browse
        </span>
      </p>
      <p className="batch-drop-hint" style={{ fontSize: '0.74rem', color: 'var(--text-3)', marginTop: 0 }}>
        Supports PDF and DOCX · up to 30 files
      </p>

      {files.length > 0 && (
        <div
          className="chips-container"
          onClick={e => e.stopPropagation()}
          style={{ marginTop: 14, justifyContent: 'center' }}
        >
          {files.map(f => (
            <span
              key={f.name}
              className="chip chip-skill"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}
            >
              📄 {f.name}
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(f.name) }}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--text-3)', fontSize: '1rem', padding: 0, lineHeight: 1,
                }}
                title="Remove"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
