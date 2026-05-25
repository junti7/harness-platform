import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import type { DashboardPayload } from './components/types'
import { TopBar } from './components/TopBar'
import { PlatformSelector } from './components/PlatformSelector'
import { KpiCard, RiskBanner } from './components/KpiCard'
import { SparkChart } from './components/SparkChart'
import { JarvisConsole } from './components/JarvisConsole'
import { TradingApiMonitor } from './components/TradingApiMonitor'
import { DataCollectionMonitor } from './components/DataCollectionMonitor'
import { formatUsd, formatKrw, formatPercent, platformLabel } from './components/utils'

// Import newly structured pages
import { ApprovalsPage } from './pages/ApprovalsPage'
import { ConferenceRoomPage } from './pages/ConferenceRoomPage'
import { CostsPage } from './pages/CostsPage'
import { TokenUsagePage } from './pages/TokenUsagePage'
import { MeetingNotesPage } from './pages/MeetingNotesPage'
import { SettingsPage } from './pages/SettingsPage'
import { LoginPage } from './pages/LoginPage'
import { PipelinePage } from './pages/PipelinePage'

const SESSION_KEY = 'harness-session'
const SESSION_TIMEOUT_MS = 30 * 60 * 1000 // 30분

type SessionData = { role: 'ceo' | 'vp'; lastActivity: number }

function loadSession(): SessionData | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const s = JSON.parse(raw) as SessionData
    if (Date.now() - s.lastActivity > SESSION_TIMEOUT_MS) {
      localStorage.removeItem(SESSION_KEY)
      return null
    }
    return s
  } catch {
    return null
  }
}

function saveSession(role: 'ceo' | 'vp') {
  const s: SessionData = { role, lastActivity: Date.now() }
  localStorage.setItem(SESSION_KEY, JSON.stringify(s))
}

function touchSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return
    const s = JSON.parse(raw) as SessionData
    s.lastActivity = Date.now()
    localStorage.setItem(SESSION_KEY, JSON.stringify(s))
  } catch {}
}

const API_BASE = import.meta.env.VITE_HARNESS_OS_API_BASE ?? 'http://127.0.0.1:8000'
const SECRET_KEY = import.meta.env.VITE_HARNESS_OS_SECRET ?? ''

function authHeaders(): Record<string, string> {
  if (!SECRET_KEY) return {}
  return { 'X-Harness-Secret': SECRET_KEY }
}

// AR 필터 타입
type ArFilter = 'open' | 'in_progress' | 'pending' | 'blocked' | 'hold' | 'waiting_external' | 'completed' | 'all'

function App() {
  // ── 인증 세션 ──
  const [session, setSession] = useState<SessionData | null>(() => loadSession())
  const activityTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleLogin = useCallback((role: 'ceo' | 'vp') => {
    saveSession(role)
    setSession({ role, lastActivity: Date.now() })
  }, [])

  const handleLogout = useCallback(() => {
    localStorage.removeItem(SESSION_KEY)
    setSession(null)
  }, [])

  // 활동 감지 → 세션 갱신
  useEffect(() => {
    if (!session) return
    const touch = () => touchSession()
    window.addEventListener('mousemove', touch)
    window.addEventListener('keydown', touch)
    window.addEventListener('click', touch)
    // 1분마다 만료 체크
    activityTimer.current = setInterval(() => {
      if (!loadSession()) setSession(null)
    }, 60_000)
    return () => {
      window.removeEventListener('mousemove', touch)
      window.removeEventListener('keydown', touch)
      window.removeEventListener('click', touch)
      if (activityTimer.current) clearInterval(activityTimer.current)
    }
  }, [session])

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('harness-theme')
    if (saved === 'dark' || saved === 'light') return saved
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  const [viewRole, setViewRole] = useState<'ceo' | 'vp'>(() => session?.role ?? 'ceo')
  const [activeView, setActiveView] = useState<'dashboard' | 'approvals' | 'conference' | 'ars' | 'meetings' | 'costs' | 'tokens' | 'settings' | 'pipeline'>('dashboard')
  const [selectedPlatform, setSelectedPlatform] = useState('all')
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [arFilter, setArFilter] = useState<ArFilter>('open')
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0)

  // 로그인 시 역할 동기화
  useEffect(() => {
    if (session?.role && session.role !== viewRole) setViewRole(session.role)
  }, [session])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('harness-theme', theme)
  }, [theme])

  const loadDashboard = async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/dashboard/advanced`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`Dashboard API ${res.status}`)
      const payload = (await res.json()) as DashboardPayload
      setDashboard(payload)
      setSelectedPlatform(current => {
        const available = payload.available_platforms ?? ['all']
        return available.includes(current) ? current : (payload.selected_platform ?? available[0] ?? 'all')
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Dashboard load failed')
    } finally {
      if (!options?.silent) setLoading(false)
    }
  }

  const loadPendingApprovals = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/approvals?role=${viewRole}&box=pending`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setPendingApprovalsCount(data?.counts?.pending ?? 0)
    } catch {}
  }, [viewRole])

  useEffect(() => {
    void loadDashboard()
    void loadPendingApprovals()
    const timer = setInterval(() => {
      void loadDashboard({ silent: true })
      void loadPendingApprovals()
    }, 60_000)
    return () => clearInterval(timer)
  }, [loadPendingApprovals])

  const availablePlatforms = dashboard?.available_platforms ?? ['all']
  const activePlatformView = dashboard?.platform_views?.[selectedPlatform]
  const activeSnapshot = activePlatformView?.latest_snapshot ?? dashboard?.latest_snapshot
  const subscriberHistory = activePlatformView?.subscriber_history ?? dashboard?.subscriber_signal?.history ?? []
  const freeTrend = subscriberHistory.map(r => Number(r.free_subscribers || 0))
  const paidTrend = subscriberHistory.map(r => Number(r.paid_subscribers || 0))
  const trendDates = subscriberHistory.map(r => r.snapshot_date?.slice(5) ?? '')
  const costTrend = (dashboard?.cost_history ?? []).map(r => Number(r.cost_usd || 0))
  const costDates = (dashboard?.cost_history ?? []).map(r => r.day?.slice(5) ?? '')

  const freeValue = activeSnapshot?.free_subscribers ?? dashboard?.kpis.free_subscribers.value ?? 0
  const paidValue = activeSnapshot?.paid_subscribers ?? dashboard?.kpis.paid_subscribers.value ?? 0
  const freeTarget = dashboard?.kpis.free_subscribers.target ?? 50
  const paidTarget = dashboard?.kpis.paid_subscribers.target ?? 1
  const freeProgress = Math.min(1, freeValue / Math.max(1, freeTarget))
  const paidProgress = Math.min(1, paidValue / Math.max(1, paidTarget))

  const openAr = dashboard?.action_required?.open ?? 0
  const closedAr = dashboard?.action_required?.closed ?? 0
  const arCompletion = openAr + closedAr > 0 ? Math.round((closedAr / (openAr + closedAr)) * 100) : 0

  const engagementTotal = useMemo(() => {
    const e = activePlatformView?.engagement
    if (e) return Number(e.opens || 0) + Number(e.clicks || 0) + Number(e.replies || 0) + Number(e.shares || 0)
    if (!dashboard) return 0
    return Number(dashboard.latest_snapshot.opens || 0) + Number(dashboard.latest_snapshot.clicks || 0) +
      Number(dashboard.latest_snapshot.replies || 0) + Number(dashboard.latest_snapshot.shares || 0)
  }, [dashboard, activePlatformView])

  const llmCost = dashboard?.kpis.llm_daily_cost_usd.value ?? 0
  const llmBudget = dashboard?.kpis.llm_daily_cost_usd.budget_limit_usd ?? 5
  const llmCostPct = llmCost / Math.max(0.0001, llmBudget)
  const llmStatusVariant = llmCostPct > 0.9 ? 'danger' : llmCostPct > 0.7 ? 'warn' : 'ok'

  const riskOpen = dashboard?.risk_overview?.open ?? 0
  const pendingRedTeam = dashboard?.kpis.pending_red_team_reviews.value ?? 0
  const riskStatusVariant = riskOpen > 5 || pendingRedTeam > 3 ? 'danger' : riskOpen > 2 || pendingRedTeam > 1 ? 'warn' : 'ok'

  const platformDescription = selectedPlatform === 'all'
    ? '통합 집계 — 전체 플랫폼 합산 뷰'
    : `${platformLabel(selectedPlatform)} 단독 뷰`

  // 미인증 시 로그인 화면
  if (!session) {
    return <LoginPage onLogin={handleLogin} apiBase={API_BASE} authHeaders={authHeaders} />
  }

  return (
    <div className="dashboard-shell">
      <TopBar
        theme={theme}
        onToggleTheme={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
        viewRole={viewRole}
        loading={loading}
        generatedAt={dashboard?.generated_at}
        pendingApprovals={pendingApprovalsCount}
        activeView={activeView}
        onChangeView={setActiveView}
        onLogout={handleLogout}
      />

      {/* ── LAYER 1: RISK / JUDGMENT ── */}
      {(openAr > 0 || pendingRedTeam > 0 || error) && activeView === 'dashboard' && (
        <div className="risk-strip">
          {error && (
            <RiskBanner level="danger" title="Dashboard Error" message={error} />
          )}
          {openAr > 0 && (
            <RiskBanner
              level={openAr > 5 ? 'danger' : 'warn'}
              title={`AR Open: ${openAr}`}
              message={`미이행 Action Required ${openAr}건 · Closure rate ${arCompletion}%`}
            />
          )}
          {pendingRedTeam > 0 && (
            <RiskBanner
              level="warn"
              title={`Red Team 미결 ${pendingRedTeam}건`}
              message="발행 전 cross-LLM 검증이 필요한 산출물이 있습니다"
            />
          )}
        </div>
      )}

      {activeView === 'dashboard' && dashboard && (
        <>
          {/* ── PLATFORM SELECTOR ── */}
          <PlatformSelector
            selected={selectedPlatform}
            available={availablePlatforms}
            onSelect={setSelectedPlatform}
            description={platformDescription}
          />

          {/* ── LAYER 1: KPI BAND ── */}
          <section className="kpi-section" aria-label="KPI overview">
            <div className="section-head">
              <h2>KPI Overview</h2>
              <p>핵심 사업 지표 — 판단 우선 스캔 레이어</p>
            </div>
            <div className="kpi-grid">
              <KpiCard
                title="Subscriber Coverage"
                value={`${freeValue} / ${freeTarget}`}
                progress={freeProgress}
                progressLabel={`목표 ${freeTarget}명 · ${formatPercent(freeProgress)} 달성`}
                trend={freeTrend}
                trendColorClass="free"
                trendDates={trendDates}
                statusVariant={freeProgress >= 1 ? 'ok' : freeProgress > 0.5 ? 'neutral' : 'warn'}
                badge="Free"
              />
              <KpiCard
                title="Paid Readiness"
                value={`${paidValue} / ${paidTarget}`}
                progress={paidProgress}
                progressLabel={paidValue === 0 ? '첫 paid subscriber 전환 미완료' : `목표 달성 ${formatPercent(paidProgress)}`}
                trend={paidTrend}
                trendColorClass="paid"
                trendDates={trendDates}
                statusVariant={paidProgress >= 1 ? 'ok' : paidValue > 0 ? 'neutral' : 'warn'}
                badge="Paid"
              />
              <KpiCard
                title="Research Burn (Daily)"
                value={formatUsd(llmCost)}
                subtitle={`Budget ${formatUsd(llmBudget)} · Usage ${formatPercent(llmCostPct)}`}
                progress={llmCostPct}
                trend={costTrend}
                trendColorClass="cost"
                trendDates={costDates}
                statusVariant={llmStatusVariant}
                badge="LLM"
              />
              <KpiCard
                title="Risk Gates"
                value={riskOpen + pendingRedTeam}
                subtitle={`Risk Open ${riskOpen} · Red Team 미결 ${pendingRedTeam}`}
                statusVariant={riskStatusVariant}
                badge="Risk"
              />
            </div>
          </section>

          {/* ── DATA COLLECTION MONITOR ── */}
          {dashboard.data_collection_monitor && (
            <DataCollectionMonitor monitor={dashboard.data_collection_monitor} />
          )}

          {/* ── LAYER 2: OPERATIONS ── */}
          <section className="ops-section" aria-label="Trading operations">
            <div className="section-head">
              <h2>Trading Operations</h2>
              <p>플랫폼 전환과 무관한 판단 레이어</p>
            </div>
            <div className="ops-grid">
              <article className="panel">
                <div className="panel-head">
                  <h3>Risk Board &amp; Action Items</h3>
                </div>
                <div className="split-2">
                  <div>
                    <p className="data-label">Open AR</p>
                    <p className={`data-value ${openAr > 0 ? 'warn' : 'ok'}`}>{openAr}</p>
                  </div>
                  <div>
                    <p className="data-label">Closure Rate</p>
                    <p className={`data-value ${arCompletion >= 80 ? 'ok' : 'neutral'}`}>{arCompletion}%</p>
                  </div>
                </div>
                <ul className="data-list">
                  <li>Risk Open: <strong>{dashboard.risk_overview?.open ?? 0}</strong></li>
                  <li>Mitigating: <strong>{dashboard.risk_overview?.mitigating ?? 0}</strong></li>
                  <li>Resolved: <strong>{dashboard.risk_overview?.resolved ?? 0}</strong></li>
                  <li>Accepted: <strong>{dashboard.risk_overview?.accepted ?? 0}</strong></li>
                </ul>
                {paidTrend.length > 0 && (
                  <div className="trend-block">
                    <p className="data-label">Paid Conviction Trend (14d)</p>
                    <SparkChart values={paidTrend} colorClass="paid" dates={trendDates} />
                  </div>
                )}
              </article>

              <article className="panel">
                <div className="panel-head">
                  <h3>Execution Throughput</h3>
                </div>
                <div className="split-2">
                  <div>
                    <p className="data-label">Runs Today</p>
                    <p className="data-value">{dashboard.orchestration?.runs_today ?? 0}</p>
                  </div>
                  <div>
                    <p className="data-label">Runs (90d)</p>
                    <p className="data-value">{dashboard.orchestration?.runs_last_90 ?? 0}</p>
                  </div>
                </div>
                <p className="data-meta">
                  Avg cost (last 20): {formatUsd(dashboard.orchestration?.avg_estimated_cost_usd_last_20 ?? 0)}
                </p>
                {costTrend.length > 0 && (
                  <div className="trend-block">
                    <p className="data-label">Research Burn Trend (14d)</p>
                    <SparkChart values={costTrend} colorClass="cost" dates={costDates} />
                  </div>
                )}
              </article>
            </div>
          </section>

          {/* ── LAYER 2: SUBSCRIBER & PLATFORM ── */}
          <section className="platform-section" aria-label="Subscriber and platform performance">
            <div className="section-head">
              <h2>Subscriber &amp; Platform Performance</h2>
              <p>{platformLabel(selectedPlatform)} 기준 구독자 반응 흐름</p>
            </div>
            <div className="platform-grid">
              <article className="panel">
                <div className="panel-head">
                  <h3>Desk Pulse</h3>
                </div>
                <div className="split-2">
                  <div>
                    <p className="data-label">Revenue (KRW proxy)</p>
                    <p className="data-value">{formatKrw(activeSnapshot?.paid_revenue_krw)}</p>
                  </div>
                  <div>
                    <p className="data-label">Engagement Total</p>
                    <p className="data-value">{engagementTotal.toLocaleString('ko-KR')}</p>
                  </div>
                </div>
                <ul className="data-list">
                  <li>Platform: <strong>{platformLabel(activeSnapshot?.platform ?? selectedPlatform)}</strong></li>
                  <li>Opens: {activeSnapshot?.opens ?? 0}</li>
                  <li>Clicks: {activeSnapshot?.clicks ?? 0}</li>
                  <li>Replies: {activeSnapshot?.replies ?? 0}</li>
                  <li>Shares: {activeSnapshot?.shares ?? 0}</li>
                  <li>Unsubs: {activeSnapshot?.unsubscribe_count ?? 0}</li>
                </ul>
                {freeTrend.length > 0 && (
                  <div className="trend-block">
                    <p className="data-label">Coverage Trend (14d)</p>
                    <SparkChart values={freeTrend} colorClass="free" dates={trendDates} />
                  </div>
                )}
              </article>

              <article className="panel">
                <div className="panel-head">
                  <h3>Platform Scope</h3>
                </div>
                <ul className="data-list">
                  <li>Current view: <strong>{platformLabel(selectedPlatform)}</strong></li>
                  <li>Baseline mode: All (통합 집계)</li>
                  <li>Snapshot date: {activeSnapshot?.snapshot_date ?? '데이터 없음'}</li>
                  <li>
                    Maily:{' '}
                    {availablePlatforms.includes('maily') ? (
                      <span className="badge-ok">활성 데이터 소스</span>
                    ) : (
                      <span className="badge-dim">준비중 (데이터 대기)</span>
                    )}
                  </li>
                  <li>
                    Substack:{' '}
                    {availablePlatforms.includes('substack') ? (
                      <span className="badge-ok">활성</span>
                    ) : (
                      <span className="badge-dim">데이터 없음</span>
                    )}
                  </li>
                </ul>
              </article>
            </div>
          </section>

          {/* ── LAYER 2: CHECKLIST / COMMANDS ── */}
          {viewRole === 'ceo' ? (
            <section className="checklist-section">
              <article className="panel">
                <div className="panel-head">
                  <h3>Portfolio Manager Checklist</h3>
                </div>
                <ul className="checklist checklist-inline">
                  <li className="open"><span className="check-dot open" />Bias: risk-on vs risk-off signal alignment</li>
                  <li className="open"><span className="check-dot open" />Sizing: exposure by confidence and drawdown tolerance</li>
                  <li className="open"><span className="check-dot open" />Gate: legal / red-team / QA blockers before execution</li>
                </ul>
              </article>
            </section>
          ) : (
            <section className="checklist-section">
              <article className="panel">
                <div className="panel-head">
                  <h3>Analyst Clarity Checklist</h3>
                </div>
                <ul className="checklist checklist-inline">
                  <li className="open"><span className="check-dot open" />Signal clarity: 핵심 시나리오가 한 줄로 설명되는지</li>
                  <li className="open"><span className="check-dot open" />Risk wording: 손실 가능성과 트리거가 명확한지</li>
                  <li className="open"><span className="check-dot open" />Actionability: 오늘 실행 가능한 액션인지</li>
                </ul>
              </article>
            </section>
          )}

          {/* ── LAYER 3: TRADING API ── */}
          {dashboard.trading_api && (
            <TradingApiMonitor
              tradingApi={dashboard.trading_api}
              apiBase={API_BASE}
              authHeaders={authHeaders}
            />
          )}

          {/* ── LAYER 3: JARVIS CONSOLE ── */}
          <JarvisConsole
            apiBase={API_BASE}
            authHeaders={authHeaders}
            templateCommands={dashboard.command_templates}
            viewRole={viewRole}
          />
        </>
      )}

      {/* ── SUB-PAGE ROUTING ── */}
      {activeView === 'approvals' && (
        <ApprovalsPage apiBase={API_BASE} authHeaders={authHeaders} viewRole={viewRole} />
      )}

      {activeView === 'conference' && (
        <ConferenceRoomPage
          apiBase={API_BASE}
          authHeaders={authHeaders}
          viewRole={viewRole}
          actorDisplay={viewRole === 'ceo' ? '대표님' : '부대표님'}
        />
      )}

      {activeView === 'costs' && (
        <CostsPage apiSecret={SECRET_KEY} backendUrl={API_BASE} />
      )}

      {activeView === 'tokens' && (
        <TokenUsagePage apiSecret={SECRET_KEY} backendUrl={API_BASE} />
      )}

      {activeView === 'meetings' && (
        <MeetingNotesPage apiBase={API_BASE} authHeaders={authHeaders} />
      )}

      {activeView === 'pipeline' && (
        <PipelinePage apiBase={API_BASE} authHeaders={authHeaders} />
      )}

      {activeView === 'settings' && (
        <SettingsPage
          currentRole={viewRole}
          apiBase={API_BASE}
          authHeaders={authHeaders}
          onSettingsChange={(role, settings) => {
            localStorage.setItem(`harness-settings-${role}`, JSON.stringify(settings))
            if (settings.theme) setTheme(settings.theme)
            if (role !== viewRole) setViewRole(role)
          }}
          onLogout={() => setActiveView('dashboard')}
        />
      )}

      {activeView === 'ars' && dashboard && (() => {
        const allItems = dashboard?.action_required?.items ?? []
        const filteredItems = allItems.filter(item => {
          if (arFilter === 'all') return true
          if (arFilter === 'open') return !item.is_closed
          if (arFilter === 'completed') return item.is_closed === true
          return item.status_code === arFilter
        })
        const filterButtons: { key: ArFilter; label: string; count: number; colorClass: string }[] = [
          { key: 'open', label: '미결 전체', count: allItems.filter(i => !i.is_closed).length, colorClass: 'warn' },
          { key: 'in_progress', label: '진행중', count: allItems.filter(i => i.status_code === 'in_progress').length, colorClass: 'accent' },
          { key: 'pending', label: 'Pending', count: allItems.filter(i => i.status_code === 'pending').length, colorClass: 'warn' },
          { key: 'blocked', label: '차단됨', count: allItems.filter(i => i.status_code === 'blocked').length, colorClass: 'danger' },
          { key: 'hold', label: '보류', count: allItems.filter(i => i.status_code === 'hold').length, colorClass: 'muted' },
          { key: 'waiting_external', label: '외부대기', count: allItems.filter(i => i.status_code === 'waiting_external').length, colorClass: 'muted' },
          { key: 'completed', label: '완료', count: allItems.filter(i => i.is_closed).length, colorClass: 'ok' },
          { key: 'all', label: '전체', count: allItems.length, colorClass: 'muted' },
        ]
        const badgeClass = (item: typeof allItems[0]) => {
          if (item.is_closed) return 'badge-ok'
          if (item.status_code === 'blocked') return 'badge-dim'
          if (item.status_code === 'waiting_external' || item.status_code === 'hold') return 'badge-dim'
          return 'badge-warn'
        }
        return (
          <section className="ops-section" style={{ marginTop: '1.5rem', padding: '0 1.5rem' }}>
            <div className="section-head">
              <h2>Action Required 현황</h2>
              <p>대표 및 부대표 조치가 필요한 핵심 운영 액션 아이템 목록</p>
            </div>
            <div className="panel" style={{ padding: '1.5rem' }}>
              {/* 요약 카드 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ background: 'var(--color-surface-lighter)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 700 }}>미결 (Open)</p>
                  <p style={{ margin: '0.2rem 0 0 0', fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-warn)' }}>
                    {dashboard?.action_required?.open ?? 0} <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>건</span>
                  </p>
                </div>
                <div style={{ background: 'var(--color-surface-lighter)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 700 }}>완료 (Closed)</p>
                  <p style={{ margin: '0.2rem 0 0 0', fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-ok)' }}>
                    {dashboard?.action_required?.closed ?? 0} <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>건</span>
                  </p>
                </div>
                <div style={{ background: 'var(--color-surface-lighter)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 700 }}>완료율</p>
                  <p style={{ margin: '0.2rem 0 0 0', fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-accent)' }}>
                    {arCompletion} <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>%</span>
                  </p>
                </div>
              </div>

              {/* 필터 버튼 */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.25rem' }}>
                {filterButtons.map(({ key, label, count }) => (
                  <button
                    key={key}
                    onClick={() => setArFilter(key)}
                    style={{
                      padding: '0.35rem 0.85rem',
                      borderRadius: '999px',
                      border: arFilter === key
                        ? '1.5px solid var(--color-accent)'
                        : '1.5px solid var(--color-border)',
                      background: arFilter === key
                        ? 'color-mix(in srgb, var(--color-accent) 15%, transparent)'
                        : 'var(--color-surface-lighter)',
                      color: arFilter === key ? 'var(--color-accent)' : 'var(--color-text-muted)',
                      fontWeight: arFilter === key ? 700 : 500,
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      transition: 'all 0.12s',
                    }}
                  >
                    {label} <span style={{ opacity: 0.7 }}>({count})</span>
                  </button>
                ))}
              </div>

              {/* 아이템 리스트 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {filteredItems.map((item) => (
                  <div key={item.id} style={{ padding: '1rem', background: 'var(--color-surface-lighter)', borderRadius: '8px', border: '1px solid var(--color-border)', opacity: item.is_closed ? 0.65 : 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem', gap: '0.5rem' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{item.id && <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginRight: '0.5rem' }}>{item.id}</span>}{item.title}</span>
                      <span className={badgeClass(item)} style={{ flexShrink: 0 }}>
                        {item.status_label ?? (item.is_closed ? '완료' : item.status_code ?? '대기')}
                      </span>
                    </div>
                    {item.description && <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', margin: '0 0 0.4rem 0', lineHeight: 1.5 }}>{item.description}</p>}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', fontSize: '0.76rem', color: 'var(--color-text-muted)' }}>
                      <span>담당: <strong>{item.owner_display ?? item.owner}</strong></span>
                      <span>기한: <strong>{item.due_date}</strong></span>
                      {item.category && <span>카테고리: <strong>{item.category}</strong></span>}
                      {item.evidence_required && <span style={{ color: 'var(--color-warn)' }}>필요 증적: {item.evidence_required}</span>}
                    </div>
                  </div>
                ))}
                {filteredItems.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                    해당 조건의 액션 아이템이 없습니다.
                  </div>
                )}
              </div>
            </div>
          </section>
        )
      })()}

      {loading && !dashboard && (
        <div className="loading-state">
          <span className="spinner" />
          <p>대시보드 로딩 중…</p>
        </div>
      )}
    </div>
  )
}

export default App
