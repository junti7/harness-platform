import { useEffect, useMemo, useState } from 'react'

type AppView = 'dashboard' | 'approvals' | 'conference' | 'ars' | 'meetings' | 'costs' | 'tokens' | 'settings' | 'pipeline' | 'trading-diary' | 'openclaw' | 'news-center'

type Props = {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  viewRole: 'ceo' | 'vp'
  loading: boolean
  generatedAt?: string
  pendingApprovals?: number
  activeView: AppView
  onChangeView: (view: AppView) => void
  nickname?: string
  onLogout?: () => void
}

type NavGroup = {
  id: string
  label: string
  items: Array<{ view: AppView; label: string }>
}

const NAV_GROUPS: NavGroup[] = [
  {
    id: 'news',
    label: '뉴스',
    items: [
      { view: 'news-center', label: '뉴스 센터' },
    ],
  },
  {
    id: 'trading',
    label: '투자',
    items: [
      { view: 'trading-diary', label: '투자 일기장' },
    ],
  },
  {
    id: 'analysis',
    label: '분석',
    items: [
      { view: 'openclaw', label: 'OpenClaw 모니터' },
      { view: 'costs', label: '비용 분석기' },
      { view: 'tokens', label: '토큰 사용량' },
    ],
  },
  {
    id: 'records',
    label: '기록',
    items: [
      { view: 'ars', label: '실행요청 현황' },
      { view: 'meetings', label: '회의록' },
    ],
  },
]

export function TopBar({
  theme,
  onToggleTheme,
  viewRole,
  loading,
  generatedAt,
  pendingApprovals = 0,
  activeView,
  onChangeView,
  nickname,
  onLogout,
}: Props) {
  const currentNickname = nickname || (viewRole === 'ceo' ? '대표님' : '부대표님')
  const [openGroup, setOpenGroup] = useState<string | null>(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const activeGroupId = useMemo(
    () => NAV_GROUPS.find(group => group.items.some(item => item.view === activeView))?.id ?? null,
    [activeView],
  )

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setMobileMenuOpen(false)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [activeView])

  useEffect(() => {
    document.body.style.overflow = mobileMenuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [mobileMenuOpen])

  const handleGroupBlur = (groupId: string, nextTarget: EventTarget | null, currentTarget: HTMLDivElement) => {
    if (nextTarget instanceof Node && currentTarget.contains(nextTarget)) return
    if (openGroup === groupId) setOpenGroup(null)
  }

  return (
    <>
    <header className="topbar">
      <div className="topbar-brand" onClick={() => onChangeView('dashboard')} style={{ cursor: 'pointer' }}>
        <div className="brand-icon" aria-hidden="true">⬡</div>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            Harness OS
            <span
              style={{
                fontSize: '0.75rem',
                background: 'var(--color-accent)',
                color: '#fff',
                padding: '0.1rem 0.4rem',
                borderRadius: '4px',
                fontWeight: 700,
                letterSpacing: '0.5px',
              }}
            >
              {viewRole.toUpperCase()}
            </span>
          </h1>
          <p className="subtitle">
            종합 관제 콘솔 · <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>{currentNickname}</span> 통제실
          </p>
        </div>
      </div>

      <nav className="topbar-nav topbar-nav-groups topbar-nav-desktop" aria-label="Primary">
        <button
          type="button"
          className={`nav-trigger nav-trigger-standalone ${activeView === 'dashboard' ? 'active' : ''}`}
          onClick={() => onChangeView('dashboard')}
        >
          <span>Home</span>
        </button>

        <button
          type="button"
          className={`nav-trigger nav-trigger-standalone ${activeView === 'approvals' ? 'active' : ''}`}
          onClick={() => onChangeView('approvals')}
        >
          <span>결재</span>
          {pendingApprovals > 0 && (
            <span className={`nav-trigger-badge ${activeView === 'approvals' ? 'active' : ''}`} aria-label={`미결 결재 ${pendingApprovals}건`}>
              {pendingApprovals > 99 ? '99+' : pendingApprovals}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`nav-trigger nav-trigger-standalone ${activeView === 'conference' ? 'active' : ''}`}
          onClick={() => onChangeView('conference')}
        >
          <span>회의실</span>
        </button>

        <button
          type="button"
          className={`nav-trigger nav-trigger-standalone ${activeView === 'pipeline' ? 'active' : ''}`}
          onClick={() => onChangeView('pipeline')}
        >
          <span>자료수집</span>
        </button>

        {NAV_GROUPS.map(group => {
          const isOpen = openGroup === group.id
          const isActive = activeGroupId === group.id
          return (
            <div
              key={group.id}
              className={`nav-group ${isOpen ? 'open' : ''}`}
              onMouseEnter={() => setOpenGroup(group.id)}
              onMouseLeave={() => setOpenGroup(current => (current === group.id ? null : current))}
              onFocus={() => setOpenGroup(group.id)}
              onBlur={event => handleGroupBlur(group.id, event.relatedTarget, event.currentTarget)}
            >
              <button
                type="button"
                className={`nav-trigger ${isActive ? 'active' : ''}`}
                onClick={() => setOpenGroup(current => (current === group.id ? null : group.id))}
                aria-expanded={isOpen}
              >
                <span>{group.label}</span>
              </button>

              <div className="nav-dropdown">
                {group.items.map(item => (
                  <button
                    key={item.view}
                    type="button"
                    className={`nav-dropdown-item ${activeView === item.view ? 'active' : ''}`}
                    onClick={() => {
                      onChangeView(item.view)
                      setOpenGroup(null)
                    }}
                  >
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )
        })}

        <button
          type="button"
          className={`nav-trigger nav-trigger-standalone ${activeView === 'settings' ? 'active' : ''}`}
          onClick={() => onChangeView('settings')}
        >
          <span>설정</span>
        </button>
      </nav>

      <div className="topbar-controls">
        <button
          type="button"
          className="topbar-mobile-menu-button"
          onClick={() => setMobileMenuOpen(current => !current)}
          aria-expanded={mobileMenuOpen}
          aria-label={mobileMenuOpen ? '모바일 메뉴 닫기' : '모바일 메뉴 열기'}
          title={mobileMenuOpen ? '모바일 메뉴 닫기' : '모바일 메뉴 열기'}
        >
          <svg className="mobile-menu-icon" viewBox="0 0 24 24" aria-hidden="true">
            {mobileMenuOpen ? (
              <>
                <path d="M6 6l12 12" />
                <path d="M18 6L6 18" />
              </>
            ) : (
              <>
                <path d="M4 7h16" />
                <path d="M4 12h16" />
                <path d="M4 17h16" />
              </>
            )}
          </svg>
        </button>
        <button
          type="button"
          className="theme-toggle"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '☀︎' : '☽'}
        </button>
        {onLogout && (
          <button
            type="button"
            className="theme-toggle"
            onClick={onLogout}
            aria-label="로그아웃"
            title="로그아웃"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        )}
        <div className="status-chip">
          <span className={loading ? 'status-pulse' : 'status-ok'}>
            {loading ? '동기화 중' : '실시간'}
          </span>
          {generatedAt && <small>{generatedAt}</small>}
        </div>
      </div>

    </header>

    {mobileMenuOpen && (
      <div className="mobile-nav-backdrop" onClick={() => setMobileMenuOpen(false)}>
        <div className="mobile-nav-sheet" onClick={event => event.stopPropagation()}>
            <div className="mobile-nav-head">
              <div>
                <strong>빠른 이동</strong>
                <p>{currentNickname} 모바일 운영 메뉴</p>
              </div>
              <button type="button" className="mobile-nav-close" onClick={() => setMobileMenuOpen(false)}>
                닫기
              </button>
            </div>

            <div className="mobile-nav-section">
              <span className="mobile-nav-label">자주 쓰는 메뉴</span>
              <div className="mobile-nav-list">
                <button type="button" className={`mobile-nav-item ${activeView === 'dashboard' ? 'active' : ''}`} onClick={() => onChangeView('dashboard')}>
                  <span>Home</span>
                </button>
                <button type="button" className={`mobile-nav-item ${activeView === 'approvals' ? 'active' : ''}`} onClick={() => onChangeView('approvals')}>
                  <span>결재</span>
                  {pendingApprovals > 0 && <span className="nav-item-badge">{pendingApprovals > 99 ? '99+' : pendingApprovals}</span>}
                </button>
                <button type="button" className={`mobile-nav-item ${activeView === 'conference' ? 'active' : ''}`} onClick={() => onChangeView('conference')}>
                  <span>회의실</span>
                </button>
                <button type="button" className={`mobile-nav-item ${activeView === 'pipeline' ? 'active' : ''}`} onClick={() => onChangeView('pipeline')}>
                  <span>자료수집</span>
                </button>
                <button type="button" className={`mobile-nav-item ${activeView === 'settings' ? 'active' : ''}`} onClick={() => onChangeView('settings')}>
                  <span>설정</span>
                </button>
              </div>
            </div>

            {NAV_GROUPS.map(group => (
              <div key={group.id} className="mobile-nav-section">
                <span className="mobile-nav-label">{group.label}</span>
                <div className="mobile-nav-list">
                  {group.items.map(item => (
                    <button
                      key={item.view}
                      type="button"
                      className={`mobile-nav-item ${activeView === item.view ? 'active' : ''}`}
                      onClick={() => onChangeView(item.view)}
                    >
                      <span>{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </div>
    )}
    </>
  )
}
