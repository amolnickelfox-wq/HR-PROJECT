import { useState } from 'react'

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

export default function LoginPage({ onLogin }) {
  const [username,    setUsername]    = useState('')
  const [password,    setPassword]    = useState('')
  const [showPass,    setShowPass]    = useState(false)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/auth/login', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ username: username.trim(), password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Invalid credentials')
      }
      const data = await res.json()
      sessionStorage.setItem('auth_token', data.token)
      sessionStorage.setItem('auth_user',  JSON.stringify({ username: data.username, full_name: data.full_name, role: data.role, must_change_password: data.must_change_password }))
      onLogin({ username: data.username, full_name: data.full_name, role: data.role, must_change_password: data.must_change_password })
    } catch (e) {
      setError(e.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="sidebar-logo" style={{ width: 48, height: 48, fontSize: '1.1rem' }}>AI</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.3rem', color: 'var(--text)' }}>RecruitAI</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>Powered by Claude</div>
          </div>
        </div>

        <h2 className="login-title">Sign in to your account</h2>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label className="login-label">Email or Username</label>
            <input
              className="login-input"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="your.name@nickelfox.com"
              autoFocus
              autoComplete="username"
            />
          </div>

          <div className="login-field">
            <label className="login-label">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                className="login-input"
                type={showPass ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                style={{ width: '100%', paddingRight: 40, boxSizing: 'border-box' }}
              />
              <button
                type="button"
                onClick={() => setShowPass(p => !p)}
                style={{
                  position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', padding: 4,
                  color: 'var(--text-3)', fontSize: '1rem', lineHeight: 1,
                }}
                title={showPass ? 'Hide password' : 'Show password'}
              >
                <EyeIcon visible={showPass} />
              </button>
            </div>
          </div>

          {error && (
            <div className="login-error">⚠️ {error}</div>
          )}

          <button
            type="submit"
            className="btn-analyze"
            style={{ width: '100%', marginTop: 8 }}
            disabled={loading || !username.trim() || !password.trim()}
          >
            {loading ? <><div className="spinner" /> Signing in…</> : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
