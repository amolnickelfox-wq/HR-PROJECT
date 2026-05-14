import { useState, useRef } from 'react'

const ACCEPTED_EXT = ['.pdf', '.docx', '.doc']

function isAccepted(name) {
  return ACCEPTED_EXT.some(ext => name.toLowerCase().endsWith(ext))
}

// Recursively read a FileSystemEntry (file or directory) → flat File array
async function readEntry(entry) {
  if (entry.isFile) {
    return new Promise((resolve, reject) => entry.file(resolve, reject))
  }
  if (entry.isDirectory) {
    const reader = entry.createReader()
    const allEntries = []
    // readEntries returns max 100 at a time — loop until exhausted
    await new Promise((resolve) => {
      const read = () => {
        reader.readEntries((batch) => {
          if (batch.length === 0) { resolve(); return }
          allEntries.push(...batch)
          read()
        })
      }
      read()
    })
    const nested = await Promise.all(allEntries.map(readEntry))
    return nested.flat()
  }
  return []
}

export default function BatchDropZone({ files, onFilesChange, disabled }) {
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef   = useRef(null)
  const folderInputRef = useRef(null)

  const addFiles = (newFiles) => {
    const accepted = Array.from(newFiles).filter(f => isAccepted(f.name))
    const existing = new Set(files.map(f => f.name))
    const merged   = [...files, ...accepted.filter(f => !existing.has(f.name))]
    onFilesChange(merged)
  }

  const removeFile = (name) => onFilesChange(files.filter(f => f.name !== name))

  const handleDrop = async (e) => {
    e.preventDefault()
    setDragOver(false)
    if (disabled) return

    const items = Array.from(e.dataTransfer.items || [])
    if (items.length > 0 && items[0].webkitGetAsEntry) {
      // Use FileSystem API to support dropped folders
      const entries = items.map(i => i.webkitGetAsEntry()).filter(Boolean)
      const allFiles = (await Promise.all(entries.map(readEntry))).flat()
      addFiles(allFiles)
    } else {
      addFiles(e.dataTransfer.files)
    }
  }

  return (
    <div
      className={`batch-drop-zone input-card${dragOver ? ' drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc"
        style={{ display: 'none' }}
        onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
        disabled={disabled}
      />
      <input
        ref={folderInputRef}
        type="file"
        webkitdirectory="true"
        mozdirectory="true"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
        disabled={disabled}
      />

      <div className="batch-drop-icon">📂</div>
      <p className="batch-drop-hint">
        Drag &amp; drop resumes or a folder here
      </p>

      <div className="batch-drop-btns">
        <button
          className="batch-browse-btn"
          onClick={() => !disabled && fileInputRef.current?.click()}
          disabled={disabled}
          type="button"
        >
          📄 Browse Files
        </button>
        <button
          className="batch-browse-btn batch-browse-btn--folder"
          onClick={() => !disabled && folderInputRef.current?.click()}
          disabled={disabled}
          type="button"
        >
          📁 Select Folder
        </button>
      </div>

      <p className="batch-drop-hint" style={{ fontSize: '0.74rem', color: 'var(--text-3)', marginTop: 4 }}>
        PDF and DOCX · select individual files or a whole folder
      </p>

      {files.length > 0 && (
        <div
          className="chips-container"
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
