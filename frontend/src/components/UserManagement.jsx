import { useState, useEffect } from 'react'

function EyeIcon({ visible }) {
  if (visible) return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  )
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  )
}

function getAuthHeaders() {
  const token = sessionStorage.getItem('auth_token')
  return token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : {}
}

export default function UserManagement({ onClose, initialSection = null, onPasswordChanged }) {
  // inline mode when onClose is null (rendered as a page, not modal)
  const isPage = onClose === null
  const [users,       setUsers]       = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState('')
  const [newName,     setNewName]     = useState('')
  const [newEmail,    setNewEmail]    = useState('')
  const [newRole,     setNewRole]     = useState('admin')
  const [adding,      setAdding]      = useState(false)
  const [addError,    setAddError]    = useState('')
  const [addSuccess,  setAddSuccess]  = useState('')
  const [emailError,  setEmailError]  = useState('')

  const handleNameChange = (e) => {
    setNewName(e.target.value.replace(/[^a-zA-Z ]/g, ''))
  }

  const handleEmailChange = (e) => {
    const val = e.target.value
    setNewEmail(val)
    if (val && !val.toLowerCase().endsWith('@nickelfox.com')) {
      setEmailError('Email must end with @nickelfox.com')
    } else {
      setEmailError('')
    }
  }

  const me = JSON.parse(sessionStorage.getItem('auth_user') || '{}')

  // Change own password
  const [oldPass,     setOldPass]     = useState('')
  const [newPass,     setNewPass]     = useState('')
  const [showOld,     setShowOld]     = useState(false)
  const [showNew,     setShowNew]     = useState(false)
  const [changingPw,  setChangingPw]  = useState(false)
  const [changePwMsg, setChangePwMsg] = useState('')

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const res = await fetch('/auth/users', { headers: getAuthHeaders() })
      if (!res.ok) throw new Error('Failed to load users')
      const data = await res.json()
      setUsers(data.users)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (me.role === 'super_admin') fetchUsers() }, [])

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!newName.trim() || !newEmail.trim()) return
    if (!newEmail.trim().toLowerCase().endsWith('@nickelfox.com')) {
      setAddError('Email must be a @nickelfox.com address')
      return
    }
    setAdding(true); setAddError(''); setAddSuccess('')
    try {
      const res = await fetch('/auth/users', {
        method:  'POST',
        headers: getAuthHeaders(),
        body:    JSON.stringify({ full_name: newName.trim(), email: newEmail.trim().toLowerCase(), role: newRole }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || 'Failed to add user')
      }
      setNewName(''); setNewEmail(''); setNewRole('admin')
      setAddSuccess(`✓ Access granted. Email sent to ${newEmail.trim().toLowerCase()}`)
      await fetchUsers()
    } catch (e) {
      setAddError(e.message)
    } finally {
      setAdding(false)
    }
  }

  const handleRemove = async (uname) => {
    if (!window.confirm(`Remove access for "${uname}"? They will no longer be able to log in.`)) return
    try {
      await fetch(`/auth/users/${encodeURIComponent(uname)}`, {
        method: 'DELETE', headers: getAuthHeaders(),
      })
      await fetchUsers()
    } catch {}
  }

  const handleChangeMyPassword = async (e) => {
    e.preventDefault()
    if (!oldPass.trim() || !newPass.trim()) return
    setChangingPw(true); setChangePwMsg('')
    try {
      // Verify old password by attempting login
      const verifyRes = await fetch('/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: me.username, password: oldPass }),
      })
      if (!verifyRes.ok) throw new Error('Current password is incorrect')
      const res = await fetch('/auth/change-password', {
        method: 'PUT', headers: getAuthHeaders(),
        body: JSON.stringify({ new_password: newPass }),
      })
      if (!res.ok) throw new Error('Failed to update password')
      const data = await res.json()
      setOldPass(''); setNewPass('')
      setChangePwMsg('✓ Password changed successfully')
      onPasswordChanged?.({ token: data.token })
    } catch (e) {
      setChangePwMsg(`⚠️ ${e.message}`)
    } finally {
      setChangingPw(false)
    }
  }

  const handleResetPassword = async (uname) => {
    const newPass = window.prompt(`Set new password for "${uname}":`)
    if (!newPass) return
    try {
      const res = await fetch(`/auth/users/${encodeURIComponent(uname)}/password`, {
        method:  'PUT',
        headers: getAuthHeaders(),
        body:    JSON.stringify({ new_password: newPass }),
      })
      if (res.ok) alert('Password updated successfully.')
      else alert('Failed to update password.')
    } catch {}
  }

  const showSection = (section) =>
    !initialSection || initialSection === section

  if (isPage) {
    return (
      <div style={{ maxWidth: 560, margin: '0 auto', padding: '0 0 40px' }}>
        {showSection('change-password') && <div className="card" style={{ marginBottom: 20 }}>
          <div className="section-label" style={{ marginBottom: 12 }}>Change My Password</div>
          <form onSubmit={handleChangeMyPassword} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ position: 'relative' }}>
              <input className="login-input" type={showOld ? 'text' : 'password'} placeholder="Current password" value={oldPass} onChange={e => setOldPass(e.target.value)} style={{ width: '100%', paddingRight: 40, boxSizing: 'border-box' }} />
              <button type="button" onClick={() => setShowOld(p => !p)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)' }}><EyeIcon visible={showOld} /></button>
            </div>
            <div style={{ position: 'relative' }}>
              <input className="login-input" type={showNew ? 'text' : 'password'} placeholder="New password" value={newPass} onChange={e => setNewPass(e.target.value)} style={{ width: '100%', paddingRight: 40, boxSizing: 'border-box' }} />
              <button type="button" onClick={() => setShowNew(p => !p)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)' }}><EyeIcon visible={showNew} /></button>
            </div>
            {changePwMsg && <div style={{ fontSize: '0.82rem', color: changePwMsg.startsWith('✓') ? 'var(--green)' : 'var(--red)' }}>{changePwMsg}</div>}
            <button type="submit" className="btn-analyze" style={{ fontSize: '0.85rem', padding: '8px 0' }} disabled={changingPw || !oldPass.trim() || !newPass.trim()}>{changingPw ? 'Updating…' : 'Update Password'}</button>
          </form>
        </div>}

        {showSection('add-user') && <div className="card" style={{ marginBottom: 20 }}>
          <div className="section-label" style={{ marginBottom: 12 }}>Add New User</div>
          <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input className="login-input" type="text" placeholder="Full Name (e.g. Sarah Khan)" value={newName} onChange={handleNameChange} autoComplete="off" />
            <input className="login-input" type="text" placeholder="user@nickelfox.com" value={newEmail} onChange={handleEmailChange} autoComplete="off" />
            {emailError && <div style={{ fontSize: '0.78rem', color: 'var(--red)', marginTop: -4 }}>⚠ {emailError}</div>}
            <select className="login-input" value={newRole} onChange={e => setNewRole(e.target.value)}>
              <option value="super_admin">Super Admin</option>
              <option value="admin">Admin</option>
              <option value="user">User (View Only)</option>
            </select>
            {addError   && <div className="login-error">⚠️ {addError}</div>}
            {addSuccess && <div style={{ fontSize: '0.82rem', color: 'var(--green)' }}>{addSuccess}</div>}
            <button type="submit" className="btn-analyze" style={{ fontSize: '0.85rem', padding: '8px 0' }} disabled={adding || !newName.trim() || !newEmail.trim() || !!emailError}>{adding ? 'Sending…' : '+ Add User & Send Email'}</button>
          </form>
        </div>}

        {showSection('user-list') && <div className="card">
          <div className="section-label" style={{ marginBottom: 12 }}>Current Users</div>
          {loading ? <div style={{ color: 'var(--text-3)', fontSize: '0.85rem' }}>Loading…</div>
          : error ? <div className="login-error">⚠️ {error}</div>
          : <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {users.map(u => (
                <div key={u.username} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: 'var(--bg)', borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div className="candidate-avatar candidate-avatar--sm">{(u.full_name || u.username)[0].toUpperCase()}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text)' }}>{u.full_name || u.username}</div>
                    <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
                      <span className={`topbar-role-badge topbar-role-badge--${u.role}`}>
                        {u.role === 'super_admin' ? 'Super Admin' : u.role === 'admin' ? 'Admin' : 'User (View Only)'}
                      </span>
                      {u.must_change_password && (
                        <span style={{ display: 'inline-block', fontSize: '0.65rem', fontWeight: 600, padding: '2px 7px', borderRadius: 20, background: 'rgba(245,158,11,0.12)', color: '#B45309', border: '1px solid rgba(245,158,11,0.3)' }}>
                          Awaiting first login
                        </span>
                      )}
                    </div>
                  </div>
                  {u.username !== me.username ? (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn-clear" style={{ fontSize: '0.72rem', padding: '3px 8px' }} onClick={() => handleResetPassword(u.username)}>Reset Password</button>
                      <button className="btn-clear" style={{ fontSize: '0.72rem', padding: '3px 8px', color: 'var(--red)' }} onClick={() => handleRemove(u.username)}>Remove</button>
                    </div>
                  ) : <span style={{ fontSize: '0.72rem', color: 'var(--text-3)', fontStyle: 'italic' }}>You</span>}
                </div>
              ))}
              {users.length === 0 && <div style={{ color: 'var(--text-3)', fontSize: '0.85rem' }}>No users yet.</div>}
            </div>}
        </div>}
      </div>
    )
  }

  return (
    <div className="batch-modal-overlay" onClick={onClose}>
      <div className="batch-modal-panel" style={{ maxWidth: 560 }} onClick={e => e.stopPropagation()}>

        <div className="batch-modal-header">
          <button className="batch-modal-back" onClick={onClose}>← Back</button>
          <div className="batch-modal-title">
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>👥 Manage Access</div>
          </div>
        </div>

        <div className="batch-modal-body">

          {/* Change my password */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-label" style={{ marginBottom: 12 }}>Change My Password</div>
            <form onSubmit={handleChangeMyPassword} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ position: 'relative' }}>
                <input className="login-input" type={showOld ? 'text' : 'password'}
                  placeholder="Current password" value={oldPass}
                  onChange={e => setOldPass(e.target.value)}
                  style={{ width: '100%', paddingRight: 40, boxSizing: 'border-box' }} />
                <button type="button" onClick={() => setShowOld(p => !p)}
                  style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)' }}>
                  <EyeIcon visible={showOld} />
                </button>
              </div>
              <div style={{ position: 'relative' }}>
                <input className="login-input" type={showNew ? 'text' : 'password'}
                  placeholder="New password" value={newPass}
                  onChange={e => setNewPass(e.target.value)}
                  style={{ width: '100%', paddingRight: 40, boxSizing: 'border-box' }} />
                <button type="button" onClick={() => setShowNew(p => !p)}
                  style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)' }}>
                  <EyeIcon visible={showNew} />
                </button>
              </div>
              {changePwMsg && (
                <div style={{ fontSize: '0.82rem', color: changePwMsg.startsWith('✓') ? 'var(--green)' : 'var(--red)' }}>
                  {changePwMsg}
                </div>
              )}
              <button type="submit" className="btn-analyze"
                style={{ fontSize: '0.85rem', padding: '8px 0' }}
                disabled={changingPw || !oldPass.trim() || !newPass.trim()}>
                {changingPw ? 'Updating…' : 'Update Password'}
              </button>
            </form>
          </div>

          {/* Add user form */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="section-label" style={{ marginBottom: 12 }}>Add New User</div>
            <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <input className="login-input" type="text" placeholder="Full Name (e.g. Sarah Khan)" value={newName} onChange={handleNameChange} autoComplete="off" />
              <input className="login-input" type="text" placeholder="user@nickelfox.com" value={newEmail} onChange={handleEmailChange} autoComplete="off" />
              {emailError && <div style={{ fontSize: '0.78rem', color: 'var(--red)', marginTop: -4 }}>⚠ {emailError}</div>}
              <select className="login-input" value={newRole} onChange={e => setNewRole(e.target.value)}>
                <option value="super_admin">Super Admin</option>
                <option value="admin">Admin</option>
                <option value="user">User (View Only)</option>
              </select>
              {addError   && <div className="login-error">⚠️ {addError}</div>}
              {addSuccess && <div style={{ fontSize: '0.82rem', color: 'var(--green)' }}>{addSuccess}</div>}
              <button type="submit" className="btn-analyze"
                style={{ fontSize: '0.85rem', padding: '8px 0' }}
                disabled={adding || !newName.trim() || !newEmail.trim() || !!emailError}>
                {adding ? 'Sending…' : '+ Add User & Send Email'}
              </button>
            </form>
          </div>

          {/* Users list */}
          <div className="card">
            <div className="section-label" style={{ marginBottom: 12 }}>Current Users</div>
            {loading ? (
              <div style={{ color: 'var(--text-3)', fontSize: '0.85rem' }}>Loading…</div>
            ) : error ? (
              <div className="login-error">⚠️ {error}</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {users.map(u => (
                  <div key={u.username} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '10px 12px', background: 'var(--bg)',
                    borderRadius: 8, border: '1px solid var(--border)',
                  }}>
                    <div className="candidate-avatar candidate-avatar--sm">
                      {(u.full_name || u.username)[0].toUpperCase()}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text)' }}>{u.full_name || u.username}</div>
                      {u.full_name && <div style={{ fontSize: '0.72rem', color: 'var(--text-3)', marginBottom: 3 }}>{u.username}</div>}
                      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
                        <span className={`topbar-role-badge topbar-role-badge--${u.role}`}>
                          {u.role === 'super_admin' ? 'Super Admin' : u.role === 'admin' ? 'Admin' : 'User (View Only)'}
                        </span>
                        {u.must_change_password && (
                          <span style={{ display: 'inline-block', fontSize: '0.65rem', fontWeight: 600, padding: '2px 7px', borderRadius: 20, background: 'rgba(245,158,11,0.12)', color: '#B45309', border: '1px solid rgba(245,158,11,0.3)' }}>
                            Awaiting first login
                          </span>
                        )}
                      </div>
                    </div>
                    {u.username !== me.username ? (
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn-clear" style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                          onClick={() => handleResetPassword(u.username)}>
                          Reset Password
                        </button>
                        <button className="btn-clear" style={{ fontSize: '0.72rem', padding: '3px 8px', color: 'var(--red)' }}
                          onClick={() => handleRemove(u.username)}>
                          Remove
                        </button>
                      </div>
                    ) : (
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-3)', fontStyle: 'italic' }}>You</span>
                    )}
                  </div>
                ))}
                {users.length === 0 && (
                  <div style={{ color: 'var(--text-3)', fontSize: '0.85rem' }}>No users yet.</div>
                )}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
