type Props = {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  viewRole: 'ceo' | 'vp'
  onToggleRole: (role: 'ceo' | 'vp') => void
  loading: boolean
  generatedAt?: string
}

export function TopBar({ theme, onToggleTheme, viewRole, onToggleRole, loading, generatedAt }: Props) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <div className="brand-icon" aria-hidden="true">⬡</div>
        <div>
          <h1>Harness OS</h1>
          <p className="subtitle">Mission Control · Risk-First Decision Dashboard</p>
        </div>
      </div>
      <div className="topbar-controls">
        <div className="role-toggle" role="tablist" aria-label="view role">
          <button
            type="button"
            className={viewRole === 'ceo' ? 'active' : ''}
            onClick={() => onToggleRole('ceo')}
            aria-selected={viewRole === 'ceo'}
          >
            CEO
          </button>
          <button
            type="button"
            className={viewRole === 'vp' ? 'active' : ''}
            onClick={() => onToggleRole('vp')}
            aria-selected={viewRole === 'vp'}
          >
            VP
          </button>
        </div>
        <button
          type="button"
          className="theme-toggle"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '☀︎' : '☽'}
        </button>
        <div className="status-chip">
          <span className={loading ? 'status-pulse' : 'status-ok'} translate="no">
            {loading ? 'SYNCING' : 'LIVE'}
          </span>
          {generatedAt && <small>{generatedAt}</small>}
        </div>
      </div>
    </header>
  )
}
