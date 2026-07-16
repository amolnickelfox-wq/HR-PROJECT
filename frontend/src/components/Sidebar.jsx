function NavIcon({ name }) {
  const paths = {
    dashboard: [
      'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z',
      'M9 22V12h6v10',
    ],
    user: [
      'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2',
      'M12 11a4 4 0 100-8 4 4 0 000 8z',
    ],
    folder: [
      'M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z',
    ],
    phone: [
      'M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z',
    ],
    calendar: [
      'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
    ],
    trophy: [
      'M6 9H4.5a2.5 2.5 0 010-5H6m12 0h1.5a2.5 2.5 0 010 5H18M8 9h8m-4 0v12',
      'M8 21h8',
      'M3 5h18',
    ],
    lock: [
      'M19 11H5a2 2 0 00-2 2v7a2 2 0 002 2h14a2 2 0 002-2v-7a2 2 0 00-2-2z',
      'M7 11V7a5 5 0 0110 0v4',
    ],
    'user-plus': [
      'M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2',
      'M12 11a4 4 0 100-8 4 4 0 000 8z',
      'M19 8v6M22 11h-6',
    ],
    users: [
      'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2',
      'M9 11a4 4 0 100-8 4 4 0 000 8z',
      'M23 21v-2a4 4 0 00-3-3.87',
      'M16 3.13a4 4 0 010 7.75',
    ],
    gear: [
      'M12 15a3 3 0 100-6 3 3 0 000 6z',
      'M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z',
    ],
  }
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {(paths[name] || []).map((d, i) => <path key={i} d={d} />)}
    </svg>
  )
}

function NavItem({ id, label, icon, activePage, onNavigate, badge, badgeType = 'primary' }) {
  return (
    <button
      className={`sidebar-nav-item${activePage === id ? ' active' : ''}`}
      onClick={() => onNavigate(id)}
    >
      <NavIcon name={icon} />
      {label}
      {badge != null && (
        <span className={`sidebar-badge sidebar-badge--${badgeType}`}>{badge}</span>
      )}
    </button>
  )
}

export default function Sidebar({ activePage, onNavigate, batchData, batchId, userRole, activeCallsCount = 0, callbackCount = 0 }) {
  const activeCalls = activeCallsCount || batchData?.candidates?.filter(c => c.interview_status === 'calling').length || 0
  const callbacks   = callbackCount || batchData?.candidates?.filter(c => c.interview_status === 'callback_scheduled').length || 0
  const hasResults  = (batchData?.candidates?.length ?? 0) > 0
  const isLive      = batchId && batchData?.status === 'processing'

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">AI</div>
        <div>
          <div className="sidebar-app-name">RecruitAI</div>
          <div className="sidebar-app-sub">Powered by Claude</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavItem id="dashboard" label="Job Openings" icon="dashboard" activePage={activePage} onNavigate={onNavigate} />

        <div className="sidebar-section-label">Pipeline</div>
        <NavItem id="active-calls" label="Active Calls" icon="phone"    activePage={activePage} onNavigate={onNavigate}
          badge={activeCalls > 0 ? activeCalls : null} badgeType="amber" />
        <NavItem id="callbacks"    label="Callbacks"    icon="calendar" activePage={activePage} onNavigate={onNavigate}
          badge={callbacks > 0 ? callbacks : null} badgeType="amber" />
        <NavItem id="rankings"     label="Rankings"     icon="trophy"   activePage={activePage} onNavigate={onNavigate}
          badge={hasResults ? '✓' : null} badgeType="green" />

        {userRole !== 'user' && <>
          <div className="sidebar-section-label">Tools</div>
          <NavItem id="jd-builder" label="JD Builder" icon="folder" activePage={activePage} onNavigate={onNavigate} />
        </>}

        <div className="sidebar-section-label">Account</div>
        <NavItem id="change-password" label="Change Password" icon="lock" activePage={activePage} onNavigate={onNavigate} />

        {userRole === 'super_admin' && <>
          <div className="sidebar-section-label">Manage Access</div>
          <NavItem id="add-user"  label="Add User"  icon="user-plus" activePage={activePage} onNavigate={onNavigate} />
          <NavItem id="user-list" label="User List" icon="users"     activePage={activePage} onNavigate={onNavigate} />
          <div className="sidebar-section-label">System</div>
          <NavItem id="settings" label="Settings" icon="gear" activePage={activePage} onNavigate={onNavigate} />
        </>}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-online">
          <span className="sidebar-online-dot" />
          System Online
        </div>
      </div>
    </aside>
  )
}
