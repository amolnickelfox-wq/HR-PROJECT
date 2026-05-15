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

export default function Sidebar({ activePage, onNavigate, batchData, batchId }) {
  const activeCalls = batchData?.candidates?.filter(c => c.interview_status === 'calling').length || 0
  const callbacks   = batchData?.candidates?.filter(c => c.interview_status === 'callback_scheduled').length || 0
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
        <NavItem id="dashboard" label="Dashboard" icon="dashboard" activePage={activePage} onNavigate={onNavigate} />

        <div className="sidebar-section-label">Recruitment</div>
        <NavItem id="single"  label="Single Candidate" icon="user"    activePage={activePage} onNavigate={onNavigate} />
        <NavItem id="batch"   label="Batch Pipeline"   icon="folder"  activePage={activePage} onNavigate={onNavigate}
          badge={isLive ? 'Live' : null} badgeType="live" />

        <div className="sidebar-section-label">Pipeline</div>
        <NavItem id="active-calls" label="Active Calls" icon="phone"    activePage={activePage} onNavigate={onNavigate}
          badge={activeCalls > 0 ? activeCalls : null} badgeType="amber" />
        <NavItem id="callbacks"    label="Callbacks"    icon="calendar" activePage={activePage} onNavigate={onNavigate}
          badge={callbacks > 0 ? callbacks : null} badgeType="amber" />
        <NavItem id="rankings"     label="Rankings"     icon="trophy"   activePage={activePage} onNavigate={onNavigate}
          badge={hasResults ? '✓' : null} badgeType="green" />
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
