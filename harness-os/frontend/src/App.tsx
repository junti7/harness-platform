import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import type { DashboardPayload, GmailSearchPayload, GmailMessageDetail } from './components/types'
import { TopBar } from './components/TopBar'
import { PlatformSelector } from './components/PlatformSelector'
import { KpiCard, RiskBanner } from './components/KpiCard'
import { JarvisConsole } from './components/JarvisConsole'
import { TradingApiMonitor } from './components/TradingApiMonitor'
import { TradingOpsCenter } from './components/TradingOpsCenter'
import { formatUsd, formatPercent, platformLabel } from './components/utils'

// Import newly structured pages
import { ApprovalsPage } from './pages/ApprovalsPage'
import { ConferenceRoomPage } from './pages/ConferenceRoomPage'
import { CostsPage } from './pages/CostsPage'
import { TokenUsagePage } from './pages/TokenUsagePage'
import { MeetingNotesPage } from './pages/MeetingNotesPage'
import { SettingsPage } from './pages/SettingsPage'
import { LoginPage } from './pages/LoginPage'
import { PipelinePage } from './pages/PipelinePage'
import { TradingDiaryPage } from './pages/TradingDiaryPage'
import { OpenClawMonitorPage } from './pages/OpenClawMonitorPage'
import { NewsCenterPage } from './pages/NewsCenterPage'
import { EduPilotPage } from './pages/EduPilotPage'

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
  } catch (err) {
    void err
  }
}

const API_BASE = import.meta.env.VITE_HARNESS_OS_API_BASE ?? ''
const SECRET_KEY = import.meta.env.VITE_HARNESS_OS_SECRET ?? ''

function authHeaders(): Record<string, string> {
  if (!SECRET_KEY) return {}
  return { 'X-Harness-Secret': SECRET_KEY }
}

// AR 필터 타입
type ArFilter = 'pending' | 'in_progress' | 'blocked' | 'hold' | 'waiting_external' | 'overdue' | 'completed' | 'all'
type ArItem = NonNullable<NonNullable<DashboardPayload['action_required']>['items']>[number]

function formatArDate(value?: string | null): string {
  if (!value) return '-'
  const datePart = value.includes('T') ? value.slice(0, 10) : value
  return datePart || '-'
}

function isRepoPath(value?: string | null): boolean {
  return Boolean(value && /^(docs|scripts|harness-os|adapters|infra|tests|agents|data)\//.test(value))
}

function arEvidenceSummary(item: ArItem): string {
  if (item.evidence_required && !isRepoPath(item.evidence_required)) return item.evidence_required
  return item.title || '필요 결과물'
}

function arStatusBadgeClass(item: ArItem): string {
  if (item.is_closed) return 'ar-status-badge ar-status-badge-ok'
  if (item.status_code === 'blocked' || item.status_code === 'overdue') return 'ar-status-badge ar-status-badge-danger'
  if (item.status_code === 'waiting_external') return 'ar-status-badge ar-status-badge-waiting'
  if (item.status_code === 'hold') return 'ar-status-badge ar-status-badge-muted'
  if (item.status_code === 'in_progress') return 'ar-status-badge ar-status-badge-accent'
  return 'ar-status-badge ar-status-badge-warn'
}

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
  const [activeView, setActiveView] = useState<'dashboard' | 'approvals' | 'conference' | 'ars' | 'meetings' | 'costs' | 'tokens' | 'settings' | 'pipeline' | 'trading-diary' | 'openclaw' | 'news-center' | 'edu-pilot'>('dashboard')
  const [selectedPlatform, setSelectedPlatform] = useState('all')
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [arFilter, setArFilter] = useState<ArFilter>('pending')
  const [selectedArItem, setSelectedArItem] = useState<ArItem | null>(null)
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0)
  const [gmailInbox, setGmailInbox] = useState<GmailSearchPayload | null>(null)
  const [gmailLoading, setGmailLoading] = useState(false)
  const [gmailError, setGmailError] = useState<string | null>(null)
  const [gmailLastSuccessAt, setGmailLastSuccessAt] = useState<string | null>(null)
  const [selectedGmailId, setSelectedGmailId] = useState<string | null>(null)
  const [gmailDetail, setGmailDetail] = useState<{ [id: string]: GmailMessageDetail }>({})
  const [gmailDetailLoading, setGmailDetailLoading] = useState<{ [id: string]: boolean }>({})
  const [gmailDetailError, setGmailDetailError] = useState<{ [id: string]: string }>({})
  const [gmailDays, setGmailDays] = useState<number>(14)
  const [gmailLimit, setGmailLimit] = useState<number>(10)
  const [gmailExcludePromotions, setGmailExcludePromotions] = useState<boolean>(true)
  const [gmailExcludeSocial, setGmailExcludeSocial] = useState<boolean>(true)
  const [gmailExcludeForums, setGmailExcludeForums] = useState<boolean>(false)
  const [gmailExcludeUpdates, setGmailExcludeUpdates] = useState<boolean>(false)
  const [gmailCategory, setGmailCategory] = useState<'business' | 'notifications' | 'all'>('business')

  const isNotification = useCallback((item: { subject?: string; from?: string }) => {
    const subject = (item.subject || '').toLowerCase()
    const from = (item.from || '').toLowerCase()
    
    const notificationKeywords = [
      '알리미', '알럿', 'alert', '쿠팡', 'coupang', '주문', '배송', '결제', 
      '광고', '구독', 'bill', 'receipt', 'invoice', '설문', 'newsletter', 
      '뉴스레터', '티켓', '예약'
    ]
    const notificationSenders = [
      'alerts', 'noreply', 'no-reply', 'coupang', 'info', 'news', 'billing'
    ]
    
    return (
      notificationKeywords.some(keyword => subject.includes(keyword)) ||
      notificationSenders.some(sender => from.includes(sender))
    )
  }, [])


  // 로그인 시 역할 동기화
  useEffect(() => {
    if (session?.role && session.role !== viewRole) setViewRole(session.role)
  }, [session, viewRole])

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
    } catch (err) {
      void err
    }
  }, [viewRole])

  const loadGmailInbox = useCallback(async (options?: { silent?: boolean; forceDays?: number; forceLimit?: number; excludePromotions?: boolean; excludeSocial?: boolean; excludeForums?: boolean; excludeUpdates?: boolean }) => {
    if (viewRole !== 'ceo') {
      setGmailInbox(null)
      setGmailError(null)
      setGmailLoading(false)
      return
    }

    const days = options?.forceDays !== undefined ? options.forceDays : gmailDays
    const limit = options?.forceLimit !== undefined ? options.forceLimit : gmailLimit
    const exPromotions = options?.excludePromotions !== undefined ? options.excludePromotions : gmailExcludePromotions
    const exSocial = options?.excludeSocial !== undefined ? options.excludeSocial : gmailExcludeSocial
    const exForums = options?.excludeForums !== undefined ? options.excludeForums : gmailExcludeForums
    const exUpdates = options?.excludeUpdates !== undefined ? options.excludeUpdates : gmailExcludeUpdates

    if (!options?.silent) setGmailLoading(true)
    try {
      const qParts = ['in:inbox', `newer_than:${days}d`]
      if (exPromotions) qParts.push('-category:promotions')
      if (exSocial) qParts.push('-category:social')
      if (exForums) qParts.push('-category:forums')
      if (exUpdates) qParts.push('-category:updates')

      const queryStr = qParts.join(' ')
      const query = encodeURIComponent(queryStr)
      const res = await fetch(`${API_BASE}/api/gmail/search?q=${query}&limit=${limit}`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`Gmail API ${res.status}`)
      const payload = (await res.json()) as GmailSearchPayload
      setGmailInbox(payload)
      setGmailError(null)
      setGmailLastSuccessAt(new Date().toISOString())
    } catch (err) {
      setGmailError(err instanceof Error ? err.message : 'Gmail load failed')
    } finally {
      if (!options?.silent) setGmailLoading(false)
    }
  }, [viewRole, gmailDays, gmailLimit, gmailExcludePromotions, gmailExcludeSocial, gmailExcludeForums, gmailExcludeUpdates, authHeaders])

  // 필터 및 설정 변경 시 즉시 메일 갱신
  useEffect(() => {
    if (viewRole === 'ceo') {
      void loadGmailInbox({ silent: true })
    }
  }, [gmailDays, gmailLimit, gmailExcludePromotions, gmailExcludeSocial, gmailExcludeForums, gmailExcludeUpdates, viewRole, loadGmailInbox])

  const loadGmailMessage = useCallback(async (msgId: string) => {
    if (gmailDetail[msgId]) return
    setGmailDetailLoading(prev => ({ ...prev, [msgId]: true }))
    setGmailDetailError(prev => ({ ...prev, [msgId]: '' }))
    try {
      const res = await fetch(`${API_BASE}/api/gmail/message/${msgId}`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`Gmail Get API ${res.status}`)
      const data = (await res.json()) as GmailMessageDetail
      setGmailDetail(prev => ({ ...prev, [msgId]: data }))
    } catch (err) {
      setGmailDetailError(prev => ({ ...prev, [msgId]: err instanceof Error ? err.message : 'Failed to load mail body' }))
    } finally {
      setGmailDetailLoading(prev => ({ ...prev, [msgId]: false }))
    }
  }, [gmailDetail, authHeaders])

  useEffect(() => {
    void loadDashboard()
    void loadPendingApprovals()
    if (viewRole === 'ceo') void loadGmailInbox()
    const timer = setInterval(() => {
      void loadDashboard({ silent: true })
      void loadPendingApprovals()
      if (viewRole === 'ceo') void loadGmailInbox({ silent: true })
    }, 60_000)
    return () => clearInterval(timer)
  }, [loadPendingApprovals, loadGmailInbox, viewRole])

  const availablePlatforms = dashboard?.available_platforms ?? ['all']
  const costTrend = (dashboard?.cost_history ?? []).map(r => Number(r.cost_usd || 0))
  const costDates = (dashboard?.cost_history ?? []).map(r => r.day?.slice(5) ?? '')

  const dashboardArItems = dashboard?.action_required?.items ?? []
  const pendingArCount = dashboardArItems.length > 0
    ? dashboardArItems.filter(item => item.status_code === 'pending').length
    : (dashboard?.action_required?.open ?? 0)
  const openAr = pendingArCount
  const closedAr = dashboard?.action_required?.closed ?? 0
  const arCompletion = openAr + closedAr > 0 ? Math.round((closedAr / (openAr + closedAr)) * 100) : 0

  const llmCost = dashboard?.kpis.llm_daily_cost_usd.value ?? 0
  const llmBudget = dashboard?.kpis.llm_daily_cost_usd.budget_limit_usd ?? 5
  const llmCostPct = llmCost / Math.max(0.0001, llmBudget)
  const llmStatusVariant = llmCostPct > 0.9 ? 'danger' : llmCostPct > 0.7 ? 'warn' : 'ok'

  const pendingRedTeam = dashboard?.kpis.pending_red_team_reviews.value ?? 0

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
            <RiskBanner level="danger" title="화면 데이터 오류" message={error} />
          )}
          {viewRole === 'ceo' && gmailError && (
            <RiskBanner
              level="danger"
              title="대표 메일 연결 점검 필요"
              message={`자동화 서버의 Gmail 연결 상태를 확인해야 합니다 · ${gmailError}`}
            />
          )}
          {openAr > 0 && (
            <RiskBanner
              level={openAr > 5 ? 'danger' : 'warn'}
              title={`미완료 요청 ${openAr}건`}
              message={`아직 처리되지 않은 실행 요청 ${openAr}건 · 완료율 ${arCompletion}%`}
            />
          )}
          {pendingRedTeam > 0 && (
            <RiskBanner
              level="warn"
              title={`위험 검토 대기 ${pendingRedTeam}건`}
              message="외부 발행 전 다른 AI 모델로 한 번 더 검토해야 하는 산출물이 있습니다"
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

          {/* ── LAYER 1: 핵심 지표 ── */}
          <section className="kpi-section" aria-label="핵심 지표">
            <div className="section-head">
              <h2>핵심 지표</h2>
              <p>오늘 대표가 먼저 볼 사업 상태입니다.</p>
              <p className="term-note">KPI는 핵심 성과 지표라는 뜻입니다. 화면에서는 되도록 쉬운 지표명으로 표시합니다.</p>
            </div>
            <div className="kpi-grid">
              <KpiCard
                title="오늘 AI 사용 비용"
                value={formatUsd(llmCost)}
                subtitle={`예산 ${formatUsd(llmBudget)} · 사용률 ${formatPercent(llmCostPct)}`}
                progress={llmCostPct}
                trend={costTrend}
                trendColorClass="cost"
                trendDates={costDates}
                statusVariant={llmStatusVariant}
                badge="AI"
              />
            </div>
          </section>

          {/* ── 트레이딩 오퍼레이션 센터 (Alpaca + IBKR 통합) ── */}
          <TradingOpsCenter apiBase={API_BASE} authHeaders={authHeaders} />

          {/* ── LAYER 2: CHECKLIST / COMMANDS ── */}
          {viewRole === 'ceo' ? (
            <section className="checklist-section">
              <article className="panel">
                <div className="panel-head">
                  <h3>CEO 운영 및 의사결정 체크리스트</h3>
                </div>
                <ul className="checklist checklist-inline">
                  <li className="open">
                    <span className="check-dot open" />
                    <strong>[AI 교육 Pretotyping 게이트]</strong> red_team_clear (✅ 완료) | legal_review_approve (✅ 카피 조건부 승인) | qa_clear (⏳ 랜딩 제작 후 대기)
                  </li>
                  <li className="open">
                    <span className="check-dot open" />
                    <strong>[TurtleGate 트레이딩 검증]</strong> 매매 주문 전 6대 조건 (진입 신호, 20일 ATR N값, 리스크 ≤ 1%, 손절가 2ATR, 청산 시스템, Pre-Mortem) 준수 여부 점검
                  </li>
                  <li className="open">
                    <span className="check-dot open" />
                    <strong>[자본 집행 제한]</strong> CAPITAL_ACTIONS_ENABLED=false (승인 없는 비용 집행 잠금 상태 확인)
                  </li>
                </ul>
              </article>
            </section>
          ) : (
            <section className="checklist-section">
              <article className="panel">
                <div className="panel-head">
                  <h3>분석 글 점검표</h3>
                </div>
                <ul className="checklist checklist-inline">
                  <li className="open"><span className="check-dot open" />핵심 시나리오가 한 줄로 설명되는지</li>
                  <li className="open"><span className="check-dot open" />손실 가능성과 중단 조건이 명확한지</li>
                  <li className="open"><span className="check-dot open" />오늘 바로 할 수 있는 행동인지</li>
                </ul>
              </article>
            </section>
          )}

          {viewRole === 'ceo' && (
            <section className="ops-section gmail-section" aria-label="CEO inbox pulse">
              <div className="section-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem 1rem' }}>
                <div>
                  <h2>CEO Inbox Pulse</h2>
                  <p>자동화 서버 연결됨 · 대표 중요 수신함 읽기 전용 모니터</p>
                </div>
                <button
                  type="button"
                  onClick={() => void loadGmailInbox()}
                  className="gmail-refresh-btn"
                  disabled={gmailLoading}
                >
                  {gmailLoading ? '🔄 동기화 중...' : '🔄 강제 동기화'}
                </button>
              </div>
              <article className="panel gmail-panel">
                <div className="gmail-panel-head">
                  <div>
                    <p className="gmail-runtime-label">메일 자동화 연결 상태</p>
                    <h3>{gmailInbox?.runtime?.account ?? '대표 메일 모니터'}</h3>
                  </div>
                  <div className="gmail-panel-meta">
                    <span className={`gmail-runtime-badge ${gmailError ? 'error' : 'ok'}`}>
                      {gmailError ? '자동화 서버 연결 점검 필요' : gmailLoading ? '메일 동기화 중' : '메일 자동화 연결됨'}
                    </span>
                    <span className="gmail-runtime-target">{gmailInbox?.runtime?.target ?? '자동화 서버'}</span>
                    <span className="gmail-runtime-target">
                      Last successful probe: {gmailLastSuccessAt ? new Date(gmailLastSuccessAt).toLocaleString('ko-KR') : '기록 없음'}
                    </span>
                  </div>
                </div>

                {gmailError ? (
                  <div className="gmail-empty-state">
                    <strong>Gmail 연결 오류</strong>
                    <p>{gmailError}</p>
                  </div>
                ) : (
                  <>
                    <div className="gmail-summary-grid">
                      <div className="gmail-summary-card">
                        <span className="gmail-summary-label">조회 결과 및 한도</span>
                        <select
                          value={gmailLimit}
                          onChange={(e) => setGmailLimit(Number(e.target.value))}
                          className="gmail-select"
                        >
                          <option value={6}>최근 6건</option>
                          <option value={10}>최근 10건</option>
                          <option value={20}>최근 20건</option>
                          <option value={50}>최근 50건</option>
                        </select>
                      </div>
                      <div className="gmail-summary-card">
                        <span className="gmail-summary-label">조회 기간 (검색 기준)</span>
                        <select
                          value={gmailDays}
                          onChange={(e) => setGmailDays(Number(e.target.value))}
                          className="gmail-select"
                        >
                          <option value={3}>최근 3일</option>
                          <option value={7}>최근 7일</option>
                          <option value={14}>최근 14일</option>
                          <option value={30}>최근 30일</option>
                          <option value={90}>최근 90일</option>
                        </select>
                      </div>
                      <div className="gmail-summary-card">
                        <span className="gmail-summary-label">제외할 항목 선택</span>
                        <div className="gmail-excludes-container">
                          <label className="gmail-checkbox-label">
                            <input
                              type="checkbox"
                              checked={gmailExcludePromotions}
                              onChange={(e) => setGmailExcludePromotions(e.target.checked)}
                            />
                            프로모션 제외
                          </label>
                          <label className="gmail-checkbox-label">
                            <input
                              type="checkbox"
                              checked={gmailExcludeSocial}
                              onChange={(e) => setGmailExcludeSocial(e.target.checked)}
                            />
                            소셜 미디어 제외
                          </label>
                          <label className="gmail-checkbox-label">
                            <input
                              type="checkbox"
                              checked={gmailExcludeForums}
                              onChange={(e) => setGmailExcludeForums(e.target.checked)}
                            />
                            토론 포럼 제외
                          </label>
                          <label className="gmail-checkbox-label">
                            <input
                              type="checkbox"
                              checked={gmailExcludeUpdates}
                              onChange={(e) => setGmailExcludeUpdates(e.target.checked)}
                            />
                            시스템 업데이트 제외
                          </label>
                        </div>
                      </div>
                    </div>

                    {/* Gmail Category Tabs */}
                    <div className="gmail-tabs">
                      <button
                        className={`gmail-tab-btn ${gmailCategory === 'business' ? 'active' : ''}`}
                        onClick={() => setGmailCategory('business')}
                      >
                        💼 회사/업무 메일
                        <span className="gmail-tab-count">
                          {(gmailInbox?.items ?? []).filter(item => !isNotification(item)).length}
                        </span>
                      </button>
                      <button
                        className={`gmail-tab-btn ${gmailCategory === 'notifications' ? 'active' : ''}`}
                        onClick={() => setGmailCategory('notifications')}
                      >
                        🔔 알림 및 기타
                        <span className="gmail-tab-count">
                          {(gmailInbox?.items ?? []).filter(item => isNotification(item)).length}
                        </span>
                      </button>
                      <button
                        className={`gmail-tab-btn ${gmailCategory === 'all' ? 'active' : ''}`}
                        onClick={() => setGmailCategory('all')}
                      >
                        📂 전체 메일
                        <span className="gmail-tab-count">
                          {(gmailInbox?.items ?? []).length}
                        </span>
                      </button>
                    </div>

                    <div className="gmail-list">
                      {(gmailInbox?.items ?? [])
                        .filter(item => {
                          if (gmailCategory === 'business') return !isNotification(item)
                          if (gmailCategory === 'notifications') return isNotification(item)
                          return true
                        })
                        .map(item => {
                          const isExpanded = selectedGmailId === item.id
                          const detail = gmailDetail[item.id]
                          const isLoading = gmailDetailLoading[item.id]
                          const detailErr = gmailDetailError[item.id]

                          return (
                            <article
                              key={item.id}
                              className={`gmail-item ${isExpanded ? 'active' : ''}`}
                              onClick={() => {
                                if (isExpanded) {
                                  setSelectedGmailId(null)
                                } else {
                                  setSelectedGmailId(item.id)
                                  void loadGmailMessage(item.id)
                                }
                              }}
                              style={{ cursor: 'pointer' }}
                            >
                              <div className="gmail-item-header">
                                <div className="gmail-item-main">
                                  <div className="gmail-item-subject-row">
                                    <h4>{item.subject}</h4>
                                    <span className="gmail-item-date">{item.date ?? '시간 미상'}</span>
                                  </div>
                                  <p className="gmail-item-from">{item.from}</p>
                                </div>
                                <div className="gmail-item-side">
                                  <div className="gmail-item-labels">
                                    {(item.labels ?? []).slice(0, 3).map(label => (
                                      <span key={label} className="gmail-item-label">{label}</span>
                                    ))}
                                  </div>
                                  {(item.messageCount ?? 1) > 1 && (
                                    <span className="gmail-thread-count">{item.messageCount} msgs</span>
                                  )}
                                </div>
                              </div>

                              {isExpanded && (
                                <div
                                  className="gmail-item-body"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  {isLoading ? (
                                    <div className="gmail-detail-loading">메일 본문 동기화 중...</div>
                                  ) : detailErr ? (
                                    <div className="gmail-detail-error">오류: {detailErr}</div>
                                  ) : detail ? (
                                    <>
                                      <div className="gmail-body-meta">
                                        <span>보낸 사람: <strong>{detail.from}</strong></span>
                                        {detail.to && <span>받는 사람: <strong>{detail.to}</strong></span>}
                                        <span>날짜: <strong>{detail.date}</strong></span>
                                      </div>
                                      <div className="gmail-body-content">
                                        {detail.body || detail.snippet || '(본문 내용 없음)'}
                                      </div>
                                    </>
                                  ) : (
                                    <div className="gmail-detail-loading">본문 없음</div>
                                  )}
                                </div>
                              )}
                            </article>
                          )
                        })}
                      {!gmailLoading && (gmailInbox?.items ?? [])
                        .filter(item => {
                          if (gmailCategory === 'business') return !isNotification(item)
                          if (gmailCategory === 'notifications') return isNotification(item)
                          return true
                        }).length === 0 && (
                        <div className="gmail-empty-state">
                          <strong>표시할 메일이 없습니다.</strong>
                          <p>현재 탭에 표시할 수 있는 최근 메일이 없습니다.</p>
                        </div>
                      )}
                    </div>
                  </>
                )}
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
        <PipelinePage
          apiBase={API_BASE}
          authHeaders={authHeaders}
          monitor={dashboard?.data_collection_monitor}
        />
      )}

      {activeView === 'trading-diary' && (
        <TradingDiaryPage
          apiBase={API_BASE}
          authHeaders={authHeaders()}
        />
      )}

      {activeView === 'openclaw' && (
        <OpenClawMonitorPage
          apiBase={API_BASE}
          authHeaders={authHeaders}
        />
      )}

      {activeView === 'news-center' && (
        <NewsCenterPage
          apiBase={API_BASE}
          authHeaders={authHeaders}
        />
      )}

      {activeView === 'edu-pilot' && (
        <EduPilotPage apiBase={API_BASE} authHeaders={authHeaders} />
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
          if (arFilter === 'completed') return item.is_closed === true
          return item.status_code === arFilter
        })
        const countByStatus = (status: string) => allItems.filter(i => i.status_code === status).length
        const filterButtons: { key: ArFilter; label: string; count: number; tone: string }[] = [
          { key: 'pending', label: '미결', count: countByStatus('pending'), tone: 'warn' },
          { key: 'in_progress', label: '진행중', count: countByStatus('in_progress'), tone: 'accent' },
          { key: 'overdue', label: '지연', count: countByStatus('overdue'), tone: 'danger' },
          { key: 'blocked', label: '차단', count: countByStatus('blocked'), tone: 'danger' },
          { key: 'waiting_external', label: '외부대기', count: countByStatus('waiting_external'), tone: 'waiting' },
          { key: 'hold', label: '보류', count: countByStatus('hold'), tone: 'muted' },
          { key: 'completed', label: '완료', count: allItems.filter(i => i.is_closed).length, tone: 'ok' },
          { key: 'all', label: '전체', count: allItems.length, tone: 'muted' },
        ]
        const activeSummaryLabel = filterButtons.find(button => button.key === arFilter)?.label ?? '미결'
        return (
          <section className="ops-section ar-status-section">
            <div className="section-head">
              <h2>실행요청 현황</h2>
              <p>기본 화면은 실제 미결 상태만 보여주고, 차단·보류·외부대기 항목은 별도 상태로 분리합니다.</p>
              <p className="term-note">AR은 Action Required의 약자로, 여기서는 대표나 팀이 처리해야 할 실행요청을 뜻합니다.</p>
            </div>
            <div className="panel ar-status-panel">
              <div className="ar-summary-grid">
                <div className="ar-summary-card ar-summary-card-warn">
                  <span className="ar-summary-label">미결</span>
                  <strong>{countByStatus('pending')}</strong>
                  <span>즉시 확인 대상</span>
                </div>
                <div className="ar-summary-card ar-summary-card-danger">
                  <span className="ar-summary-label">차단·지연</span>
                  <strong>{countByStatus('blocked') + countByStatus('overdue')}</strong>
                  <span>해소 조건 필요</span>
                </div>
                <div className="ar-summary-card">
                  <span className="ar-summary-label">보류·외부대기</span>
                  <strong>{countByStatus('hold') + countByStatus('waiting_external')}</strong>
                  <span>미결 기본 목록 제외</span>
                </div>
                <div className="ar-summary-card ar-summary-card-ok">
                  <span className="ar-summary-label">완료율</span>
                  <strong>{arCompletion}%</strong>
                  <span>{dashboard?.action_required?.closed ?? 0}건 종결</span>
                </div>
              </div>

              <div className="ar-filter-bar" role="tablist" aria-label="실행요청 상태 필터">
                {filterButtons.map(({ key, label, count, tone }) => (
                  <button
                    key={key}
                    type="button"
                    className={`ar-filter-button ar-filter-${tone}${arFilter === key ? ' active' : ''}`}
                    onClick={() => setArFilter(key)}
                    role="tab"
                    aria-selected={arFilter === key}
                  >
                    <span>{label}</span>
                    <strong>{count}</strong>
                  </button>
                ))}
              </div>

              <div className="ar-table-headline">
                <div>
                  <strong>{activeSummaryLabel}</strong>
                  <span>{filteredItems.length}건 표시</span>
                </div>
                <span>데이터 출처: {dashboard?.action_required?.source ?? '알 수 없음'}</span>
              </div>

              <div className="ar-table-wrap">
                <table className="ar-table">
                  <thead>
                    <tr>
                      <th>요청번호</th>
                      <th>상태</th>
                      <th>담당</th>
                      <th>기한</th>
                      <th>요청 내용</th>
                      <th>결과물 / 메모</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item) => (
                      <tr key={item.id || item.title} className={item.is_closed ? 'is-closed' : undefined}>
                        <td className="ar-id-cell">
                          <strong>{item.id || '-'}</strong>
                          {item.category && <span>{item.category}</span>}
                        </td>
                        <td>
                          <span className={arStatusBadgeClass(item)}>
                            {item.status_label ?? (item.is_closed ? '종결' : item.status_code ?? '미분류')}
                          </span>
                        </td>
                        <td className="ar-owner-cell">{item.owner_display ?? item.owner ?? '미지정'}</td>
                        <td className="ar-date-cell">
                          <strong>{formatArDate(item.due_date)}</strong>
                          <span>갱신 {formatArDate(item.last_updated_at)}</span>
                        </td>
                        <td className="ar-main-cell">
                          <strong>{item.title || '제목 없음'}</strong>
                          {item.description && <p>{item.description}</p>}
                        </td>
                        <td className="ar-evidence-cell">
                          {(item.evidence_required || item.evidence_path || item.completion_note) ? (
                            <div className="ar-evidence-block">
                              <span className="ar-evidence-label">대표 확인 포인트</span>
                              <strong>{arEvidenceSummary(item)}</strong>
                              <p>
                                {item.is_closed
                                  ? '완료 기록과 산출물을 확인할 수 있습니다.'
                                  : item.evidence_available
                                    ? '결과 파일이 준비되어 있습니다. 상세에서 저장 위치와 메모를 확인하세요.'
                                    : '완료 판단 전 결과물 제출 상태를 확인해야 합니다.'}
                              </p>
                              <button
                                type="button"
                                className="ar-detail-button"
                                onClick={() => setSelectedArItem(item)}
                              >
                                상세 보기
                              </button>
                            </div>
                          ) : (
                            <span className="ar-evidence-empty">필요 결과물 없음</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filteredItems.length === 0 && (
                  <div className="ar-empty-state">
                    해당 조건의 액션 아이템이 없습니다.
                  </div>
                )}
              </div>
            </div>
          </section>
        )
      })()}

      {selectedArItem && (
        <div className="ar-detail-backdrop" role="dialog" aria-modal="true" aria-label="실행요청 상세 정보">
          <article className="ar-detail-modal">
            <div className="ar-detail-head">
              <div>
                <span className="ar-detail-kicker">{selectedArItem.id || '실행요청'}</span>
                <h3>{selectedArItem.title || '제목 없음'}</h3>
              </div>
              <button type="button" className="ar-detail-close" onClick={() => setSelectedArItem(null)}>닫기</button>
            </div>
            <div className="ar-detail-grid">
              <div>
                <span>상태</span>
                <strong>{selectedArItem.status_label ?? selectedArItem.status_code ?? '미분류'}</strong>
              </div>
              <div>
                <span>담당</span>
                <strong>{selectedArItem.owner_display ?? selectedArItem.owner ?? '미지정'}</strong>
              </div>
              <div>
                <span>기한</span>
                <strong>{formatArDate(selectedArItem.due_date)}</strong>
              </div>
              <div>
                <span>최근 갱신</span>
                <strong>{formatArDate(selectedArItem.last_updated_at)}</strong>
              </div>
            </div>
            {selectedArItem.description && (
              <section className="ar-detail-section">
                <h4>요청 내용</h4>
                <p>{selectedArItem.description}</p>
              </section>
            )}
            <section className="ar-detail-section">
              <h4>결과물 확인</h4>
              <p>{arEvidenceSummary(selectedArItem)}</p>
              {selectedArItem.evidence_path ? (
                <div className="ar-detail-file">
                  <span>{selectedArItem.evidence_available ? '결과 파일 확인됨' : '결과 파일 미확인'}</span>
                  <code>{selectedArItem.evidence_path}</code>
                </div>
              ) : selectedArItem.evidence_required && isRepoPath(selectedArItem.evidence_required) ? (
                <div className="ar-detail-file">
                  <span>결과 파일 필요</span>
                  <code>{selectedArItem.evidence_required}</code>
                </div>
              ) : null}
            </section>
            {selectedArItem.completion_note && (
              <section className="ar-detail-section">
                <h4>완료 메모</h4>
                <p>{selectedArItem.completion_note}</p>
              </section>
            )}
          </article>
        </div>
      )}

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
