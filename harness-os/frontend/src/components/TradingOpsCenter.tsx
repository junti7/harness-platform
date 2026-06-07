import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import type {
  AlpacaPaperDashboard,
  AlpacaPosition,
  AlpacaOrder,
  DropAlert,
} from './types'

// ── 타입 ──────────────────────────────────────────────────────────────────────

type IbkrAccount = {
  account_id: string
  nav: number
  cash: number
  baseline_nav: number
  total_pnl: number
  total_pnl_pct: number
}

type IbkrPosition = {
  symbol: string
  exchange: string
  qty: number
  entry_ts: string
  entry_price: number
  current_price: number | null
  market_value: number | null
  unrealized_pnl: number | null
  unrealized_pnl_pct: number | null
  atr: number
  stop_loss: number
  stop_distance_pct: number | null
  s1_low: number | null
  s1_distance_pct: number | null
  s2_low: number | null
  s2_distance_pct: number | null
  action: 'HOLD' | 'STOP_LOSS' | 'S1_EXIT' | 'S2_EXIT'
  near_stop: boolean
  near_s1: boolean
}

type IbkrCandidate = {
  symbol: string
  region: string        // "US" | "KR" | "TW" | "JP" | "HK"
  name: string
  sector: string
  currency: string      // "USD" | "KRW" | "JPY" | "TWD" | "HKD"
  current_price: number | null
  s1_high: number | null
  s2_high: number | null
  atr: number | null
  signal: string
  active_signal: string | null
  gap_pct: number | null
  in_position: boolean
}

type NavPoint = { date: string; value: number; pnl_pct: number }

type ForexRateInfo = {
  units_per_usd: number | null
  source: 'open.er-api.com' | 'IBKR_historical' | 'hardcoded' | string
  age_sec: number
}

type IbkrMonitorData = {
  ok: boolean
  ts: string
  mode: 'paper' | 'live'
  gateway_connected: boolean
  account: IbkrAccount | null
  positions: IbkrPosition[]
  exit_signals: string[]
  entry_candidates: IbkrCandidate[]
  universe_source: string
  nav_history: NavPoint[]
  forex_rates: Record<string, ForexRateInfo>
  error: string | null
}

type RunResult = { ok: boolean; stdout: string; stderr: string }
type PaperResetStatus = {
  ok: boolean
  exists: boolean
  reset_pending: boolean
  flat: boolean
  checked_at?: string
  next_action?: string
  market_context?: { now_ny?: string; market_open?: boolean; session?: string }
  alpaca?: { open_orders?: Array<[string, string, string, string]>; positions?: Array<[string, number]>; flat?: boolean }
  ibkr?: { open_orders?: Array<[number, string, string, string, number]>; positions?: Array<[string, number, string, string]>; flat?: boolean }
  post_open_verification?: {
    checked_at?: string
    ready_for_execute?: boolean
    next_action?: string[]
    alpaca_dry_run?: { status?: string; reason?: string; returncode?: number }
    ibkr_dry_run?: { status?: string; reason?: string; returncode?: number }
  }
}

type TradingSelectionFlow = {
  ok: boolean
  generated_at?: string
  pipeline?: {
    raw_total: number
    filtered_pass: number
    filtered_fail: number
    filtered_total: number
    signal_total: number
    selected_universe_count: number
  }
  selection_universe?: Array<{
    symbol: string
    name?: string
    region?: string
    sector?: string
    harness_score?: number
    evidence_count?: number
    evidence_score?: number
    matched_sources?: string[]
    selection_reason?: string
    selection_reason_ko?: string
    brokers?: string[]
  }>
  symbol_evidence?: Record<string, Array<{
    title?: string
    summary?: string
    source?: string
    score?: number
    created_at?: string
  }>>
  trade_flow?: Array<{
    ts?: string
    kind?: string
    symbol?: string
    title?: string
    source?: string
    detail?: Record<string, unknown>
  }>
  runtime_state?: {
    alpaca_tracked?: string[]
    ibkr_positions?: string[]
    ibkr_pending_orders?: string[]
  }
}

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

const INITIAL_CAPITAL = 100_000

// ── 심볼 이름 맵 ─────────────────────────────────────────────────────────────

// symbol→name 맵은 /api/trading/symbol-names 에서 동적 로드 (하드코딩 금지)
// ETF 등 파이프라인 외 종목은 여기서만 보완
const ETF_NAMES: Record<string, string> = {
  SMH: '반도체 ETF', SOXX: '반도체 ETF', BOTZ: '로보틱스 ETF',
  PLTR: 'Palantir', ROBO: '로봇 ETF', SPY: 'S&P 500 ETF', QQQ: '나스닥 100 ETF',
  GOOG: 'Google', GOOGL: 'Google', TSLA: 'Tesla', CRWV: 'CoreWeave',
}

// ── 글로벌 유니버스 지역/통화 헬퍼 ──────────────────────────────────────────

const REGION_FLAG: Record<string, string> = {
  US: '🇺🇸', KR: '🇰🇷', TW: '🇹🇼', JP: '🇯🇵', HK: '🇭🇰',
}
const CURRENCY_SYMBOL: Record<string, string> = {
  USD: '$', KRW: '₩', JPY: '¥', TWD: 'NT$', HKD: 'HK$',
}
function fmtLocalPrice(price: number | null, currency: string): string {
  if (price === null) return '—'
  const sym = CURRENCY_SYMBOL[currency] ?? (currency + ' ')
  if (currency === 'USD') return `${sym}${fmt(price)}`
  if (currency === 'JPY') return `${sym}${Math.round(price).toLocaleString()}`
  if (currency === 'KRW') return `${sym}${Math.round(price).toLocaleString()}`
  return `${sym}${fmt(price, 2)}`
}

function symDisplay(symbol?: string | null, names: Record<string, string> = {}) {
  const code = String(symbol || '').trim().toUpperCase()
  return { code: code || '—', name: names[code] || '—' }
}

// ── 포맷 헬퍼 ─────────────────────────────────────────────────────────────────

function fmt(n: number | undefined | null, decimals = 2): string {
  if (n === undefined || n === null || isNaN(n as number)) return '—'
  return (n as number).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function fmtPct(n: number | undefined | null): string {
  if (n === undefined || n === null || isNaN(n as number)) return '—'
  const v = n as number
  const sign = v >= 0 ? '+' : ''
  return `${sign}${fmt(v, 2)}%`
}

function fmtUsd(n: number | undefined | null): string {
  if (n === undefined || n === null || isNaN(n as number)) return '—'
  const v = n as number
  const sign = v >= 0 ? '+$' : '-$'
  return `${sign}${fmt(Math.abs(v), 2)}`
}

function relativeTime(iso: string): string {
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 60) return '방금 전'
    if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
    if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
    return `${Math.floor(diff / 86400)}일 전`
  } catch {
    return iso.slice(0, 16).replace('T', ' ')
  }
}

function formatEntryDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' })
  } catch {
    return iso.slice(0, 10)
  }
}

function flowEventLabel(kind?: string): string {
  const key = String(kind || '').toLowerCase()
  if (key === 'trade_entry') return '매수 기록 (Trade Entry, 진입 거래 기록 — 실제로 사기로 결정한 내역)'
  if (key === 'trade_exit') return '매도 기록 (Trade Exit, 청산 거래 기록 — 실제로 팔기로 결정한 내역)'
  if (key === 'signal_scan') return '신호 점검 (Signal Scan, 매수·매도 조건 확인 — 오늘 어떤 종목을 볼지 검사)'
  if (key === 'enter') return '매수 주문 시도 (Order Entry, 주문 넣기 — 실제 주문 제출 단계)'
  if (key === 'exit') return '매도 주문 시도 (Order Exit, 청산 주문 넣기 — 실제 매도 제출 단계)'
  if (key === 'enter_rejected') return '주문 거절 (Order Rejected, 주문 실패 — 거래소나 증권사에서 받지 않음)'
  if (key === 'gate_blocked') return '안전장치 차단 (Gate Blocked, 규칙 위반 차단 — 그냥 사지 않음)'
  if (key === 'ceo_note') return '대표 메모 (CEO Note, 운영 메모 — 사람이 남긴 판단 기록)'
  if (key === 'research_update') return '리서치 갱신 (Research Update, 조사 결과 갱신 — 새로 수집된 판단 근거)'
  return kind || '이벤트'
}

function flowEventTone(kind?: string): 'fresh' | 'aging' | 'stale' {
  const key = String(kind || '').toLowerCase()
  if (['trade_entry', 'enter', 'research_update'].includes(key)) return 'fresh'
  if (['trade_exit', 'exit', 'signal_scan', 'ceo_note'].includes(key)) return 'aging'
  return 'stale'
}

function flowEventShortLabel(kind?: string): string {
  const key = String(kind || '').toLowerCase()
  if (key === 'trade_entry') return '매수'
  if (key === 'trade_exit') return '매도'
  if (key === 'signal_scan') return '신호 점검'
  if (key === 'enter') return '주문 진입'
  if (key === 'exit') return '주문 청산'
  if (key === 'enter_rejected') return '주문 거절'
  if (key === 'gate_blocked') return '차단'
  if (key === 'ceo_note') return 'CEO 메모'
  if (key === 'research_update') return '리서치'
  return kind || '이벤트'
}

// ── 공통 서브 컴포넌트 ────────────────────────────────────────────────────────

function SymbolCell({ symbol, names = {} }: { symbol?: string | null; names?: Record<string, string> }) {
  const item = symDisplay(symbol, names)
  return (
    <span className="symbol-cell">
      <strong>{item.code}</strong>
      {item.name && item.name !== '—' && <small>{item.name}</small>}
    </span>
  )
}

function AlpacaSignalBadge({ signal }: { signal: string }) {
  const cls =
    signal === 'breakout_long' ? 'signal-long'
    : signal === 'breakout_short' ? 'signal-short'
    : signal === 'neutral' ? 'signal-neutral'
    : 'signal-na'
  const label =
    signal === 'breakout_long' ? '▲ LONG'
    : signal === 'breakout_short' ? '▼ SHORT'
    : signal === 'neutral' ? '— 중립'
    : signal === 'insufficient_data' ? '데이터 부족'
    : signal
  return <span className={`signal-badge ${cls}`}>{label}</span>
}

function IbkrSignalBadge({ signal, active }: { signal: string; active: string | null }) {
  if (signal === 'breakout_long')
    return <span className="signal-badge signal-long">▲ {active === 'S2' ? 'S2 LONG' : 'S1 LONG'}</span>
  if (signal === 'neutral') return <span className="signal-badge signal-neutral">— 중립</span>
  if (signal === 'insufficient_data') return <span className="signal-badge signal-na">데이터 부족</span>
  if (signal === 'no_connection') return <span className="signal-badge signal-na">미연결</span>
  return <span className="signal-badge signal-na">{signal}</span>
}

function ActionBadge({ action }: { action: IbkrPosition['action'] }) {
  if (action === 'HOLD') return <span className="position-action-badge action-hold">HOLD</span>
  if (action === 'STOP_LOSS') return <span className="position-action-badge action-exit-badge">손절 청산!</span>
  if (action === 'S1_EXIT') return <span className="position-action-badge action-warn-badge">S1 청산</span>
  if (action === 'S2_EXIT') return <span className="position-action-badge action-warn-badge">S2 청산</span>
  return <span className="position-action-badge action-hold">{action}</span>
}

function PnlCell({ v }: { v: number | undefined | null }) {
  if (v === undefined || v === null) return <td className="num">—</td>
  const cls = v > 0 ? 'pnl-pos' : v < 0 ? 'pnl-neg' : ''
  return <td className={`num ${cls}`}>{fmtPct(v)}</td>
}

function KpiRow({ label, value, pass, note }: { label: string; value: string; pass?: boolean; note?: string }) {
  const icon = pass === undefined ? '○' : pass ? '✓' : '✗'
  const cls = pass === undefined ? '' : pass ? 'ok' : 'danger'
  return (
    <li className={`kpi-row ${cls}`}>
      <span className="kpi-icon">{icon}</span>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {note && <span className="kpi-note">{note}</span>}
    </li>
  )
}

function MobileField({ label, value, tone = 'normal' }: { label: string; value: ReactNode; tone?: 'normal' | 'muted' }) {
  return (
    <div className="mobile-field">
      <span className="mobile-field-label">{label}</span>
      <span className={`mobile-field-value ${tone === 'muted' ? 'muted' : ''}`}>{value}</span>
    </div>
  )
}

// ── 포트폴리오 차트 (Alpaca 30D) ──────────────────────────────────────────────

type ChartPoint = { date: string; value: number; pnl_pct: number }

function PortfolioChart({ data, gradientId = 'tocPGrad' }: { data: ChartPoint[]; gradientId?: string }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<{ x: number; y: number; idx: number } | null>(null)

  if (data.length < 2) return null

  const W = 520, H = 120
  const ml = 72, mr = 16, mt = 12, mb = 28
  const cw = W - ml - mr
  const ch = H - mt - mb

  const vals = data.map(d => d.value)
  const minV = Math.min(...vals)
  const maxV = Math.max(...vals)
  const range = maxV - minV || Math.max(maxV * 0.002, 1)
  const padV = range * 0.1

  const yMin = minV - padV
  const yMax = maxV + padV
  const yRange = yMax - yMin

  const px = (i: number) => ml + (i / (data.length - 1)) * cw
  const py = (v: number) => mt + (1 - (v - yMin) / yRange) * ch

  const pts = data.map((d, i) => `${px(i)},${py(d.value)}`).join(' ')
  const area = data.map((d, i) => `${px(i)},${py(d.value)}`).join(' ')
    + ` ${px(data.length - 1)},${mt + ch} ${ml},${mt + ch}`

  const isUp = vals[vals.length - 1] >= vals[0]
  const lineColor = isUp ? '#ef4444' : '#3b82f6'

  const yTicks = [yMin + yRange * 0.05, yMin + yRange * 0.5, yMin + yRange * 0.95]
  const xIdxs = [0, Math.floor((data.length - 1) / 2), data.length - 1]

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return
    const relX = (e.clientX - rect.left) * (W / rect.width)
    const chartX = relX - ml
    if (chartX < 0 || chartX > cw) { setHover(null); return }
    const idx = Math.round((chartX / cw) * (data.length - 1))
    const clampedIdx = Math.max(0, Math.min(data.length - 1, idx))
    setHover({ x: px(clampedIdx), y: py(data[clampedIdx].value), idx: clampedIdx })
  }

  const hPoint = hover !== null ? data[hover.idx] : null
  const tooltipX = hover ? Math.min(hover.x + 8, W - 130) : 0
  const tooltipY = hover ? Math.max(hover.y - 48, mt) : 0

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="spark-svg spark-full"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHover(null)}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.25" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {yTicks.map((v, i) => (
        <g key={i}>
          <line x1={ml} y1={py(v)} x2={ml + cw} y2={py(v)} stroke="rgba(0,0,0,0.06)" strokeWidth="1" />
          <text x={ml - 6} y={py(v) + 4} textAnchor="end" className="chart-axis-label">
            ${(v / 1000).toFixed(1)}k
          </text>
        </g>
      ))}
      {xIdxs.map(i => (
        <text key={i} x={px(i)} y={H - 6} textAnchor="middle" className="chart-axis-label">
          {data[i].date}
        </text>
      ))}
      <polygon points={area} fill={`url(#${gradientId})`} />
      <polyline points={pts} fill="none" stroke={lineColor} strokeWidth="1.5" strokeLinejoin="round" />
      {hover && (
        <>
          <line x1={hover.x} y1={mt} x2={hover.x} y2={mt + ch} stroke="rgba(0,0,0,0.15)" strokeWidth="1" strokeDasharray="3,3" />
          <circle cx={hover.x} cy={hover.y} r="4" fill={lineColor} stroke="#fff" strokeWidth="2" />
          <rect x={tooltipX} y={tooltipY} width="118" height="44" rx="5"
            fill="#fff" stroke="#e2e8f0" strokeWidth="1" />
          <text x={tooltipX + 8} y={tooltipY + 14} className="chart-axis-label" style={{ fill: '#64748b' }}>{hPoint?.date}</text>
          <text x={tooltipX + 8} y={tooltipY + 30} style={{ fill: '#0f172a', fontSize: '0.72rem', fontWeight: '600' }}>
            ${hPoint ? (hPoint.value / 1000).toFixed(2) : ''}k
          </text>
          <text x={tooltipX + 80} y={tooltipY + 30} style={{ fill: (hPoint?.pnl_pct ?? 0) >= 0 ? '#ef4444' : '#3b82f6', fontSize: '0.7rem', fontWeight: '600' }}>
            {hPoint ? `${hPoint.pnl_pct >= 0 ? '+' : ''}${hPoint.pnl_pct.toFixed(2)}%` : ''}
          </text>
        </>
      )}
    </svg>
  )
}

// ── 급락 브리핑 패널 (Alpaca 전용) ───────────────────────────────────────────

function triggerLabel(trigger: DropAlert['trigger']) {
  return trigger === 'rapid' ? '급속 낙폭' : '누적 낙폭'
}

function DropAlertPanel({ alerts, onAck, threshold }: {
  alerts: DropAlert[]
  onAck: (id: string) => void
  threshold: number
}) {
  const unacked = alerts.filter(a => !a.acknowledged)
  const hasActive = unacked.length > 0

  return (
    <article className={`panel alpaca-full drop-alert-panel ${hasActive ? 'drop-alert-active' : ''}`}>
      <div className="panel-head">
        <h3 className="drop-alert-title">
          {hasActive && <span className="drop-alert-badge">{unacked.length}</span>}
          급락 브리핑 <span className="broker-tag alpaca">Alpaca</span>
        </h3>
        <span className="data-meta">임계값: 단기 {threshold}% | 진입가 대비 -5% | 60초 폴링 · 30분 쿨다운</span>
        <span className="term-note">OpenClaw가 급락 감지 시 자동 수집 후 Claude가 원인을 분석하고 CEO에게 Slack 긴급 보고합니다.</span>
      </div>
      {alerts.length === 0 ? (
        <p className="drop-alert-empty">현재 감지된 급락 이벤트 없음 — 실시간 모니터링 중</p>
      ) : (
        <div className="drop-alert-list">
          {alerts.map(a => (
            <div key={a.id} className={`drop-alert-card ${a.acknowledged ? 'drop-alert-acked' : 'drop-alert-unacked'}`}>
              <div className="drop-alert-header">
                <span className="drop-alert-symbol">{a.symbol}</span>
                <span className={`drop-alert-pct ${a.drop_pct <= -5 ? 'severe' : ''}`}>{a.drop_pct.toFixed(1)}%</span>
                <span className="signal-badge signal-short">{triggerLabel(a.trigger)}</span>
                <span className="drop-alert-time">{relativeTime(a.detected_at)}</span>
                {!a.acknowledged && (
                  <button className="drop-alert-ack-btn" onClick={() => onAck(a.id)}>확인</button>
                )}
              </div>
              <div className="drop-alert-price">${a.prev_price.toFixed(2)} → ${a.current_price.toFixed(2)}</div>
              {a.news_titles.length > 0 && (
                <ul className="drop-alert-news">
                  {a.news_titles.slice(0, 3).map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              )}
              <p className="drop-alert-briefing">{a.briefing}</p>
            </div>
          ))}
        </div>
      )}
    </article>
  )
}

// ── IBKR 위험 바 ──────────────────────────────────────────────────────────────

function RiskBar({ label, distancePct, referencePrice }: {
  label: string
  distancePct: number | null
  referencePrice: number | null
}) {
  if (distancePct === null || referencePrice === null) {
    return (
      <div className="risk-bar-row">
        <span className="risk-bar-label">{label}</span>
        <span className="risk-bar-ref">—</span>
        <div className="risk-bar-track"><div className="risk-bar-fill safe" style={{ width: '0%' }} /></div>
        <span className="risk-bar-pct">—</span>
      </div>
    )
  }
  const clampedPct = Math.min(Math.max(distancePct, 0), 100)
  const fillClass = distancePct < 5 ? 'danger' : distancePct < 15 ? 'warn' : 'safe'
  return (
    <div className="risk-bar-row">
      <span className="risk-bar-label">{label}</span>
      <span className="risk-bar-ref">${fmt(referencePrice)}</span>
      <div className="risk-bar-track">
        <div className={`risk-bar-fill ${fillClass}`} style={{ width: `${clampedPct}%` }} />
      </div>
      <span className={`risk-bar-pct ${fillClass}`}>{fmt(distancePct, 1)}% 여유</span>
    </div>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────

export function TradingOpsCenter({ apiBase, authHeaders }: Props) {
  // Alpaca state
  const [alpacaData, setAlpacaData] = useState<AlpacaPaperDashboard | null>(null)
  const [alpacaLoading, setAlpacaLoading] = useState(true)
  const [alpacaError, setAlpacaError] = useState<string | null>(null)
  const [alpacaLastFetch, setAlpacaLastFetch] = useState<string | null>(null)
  const [alpacaRunning, setAlpacaRunning] = useState(false)
  const [alpacaRunResult, setAlpacaRunResult] = useState<RunResult | null>(null)
  const [dropAlerts, setDropAlerts] = useState<DropAlert[]>([])
  const [resetStatus, setResetStatus] = useState<PaperResetStatus | null>(null)
  const [selectionFlow, setSelectionFlow] = useState<TradingSelectionFlow | null>(null)
  const [selectedFlowSymbol, setSelectedFlowSymbol] = useState<string | null>(null)

  // symbol→name 맵 (API에서 로드, ETF 보완)
  const [symbolNames, setSymbolNames] = useState<Record<string, string>>(ETF_NAMES)

  // IBKR state
  const [ibkrData, setIbkrData] = useState<IbkrMonitorData | null>(null)
  const [ibkrLoading, setIbkrLoading] = useState(true)
  const [ibkrError, setIbkrError] = useState<string | null>(null)
  const [ibkrLastFetch, setIbkrLastFetch] = useState<string | null>(null)
  const [ibkrRunning, setIbkrRunning] = useState(false)
  const [ibkrRunResult, setIbkrRunResult] = useState<RunResult | null>(null)
  const [confirmIbkrExecute, setConfirmIbkrExecute] = useState(false)

  // UI state
  const [activeSignalTab, setActiveSignalTab] = useState<'alpaca' | 'ibkr'>('ibkr')
  const [regionFilter, setRegionFilter] = useState<string>('ALL')

  // ── Alpaca 데이터 로드 ──────────────────────────────────────────────────────

  const loadAlpaca = useCallback(async (silent = false) => {
    if (!silent) setAlpacaLoading(true)
    setAlpacaError(null)
    try {
      const res = await fetch(`${apiBase}/api/paper-trading/dashboard`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = (await res.json()) as AlpacaPaperDashboard
      if (json.error && !json.account) throw new Error(json.error)
      setAlpacaData(json)
      setAlpacaLastFetch(new Date().toLocaleTimeString('ko-KR'))
    } catch (e) {
      setAlpacaError(e instanceof Error ? e.message : '로드 실패')
    } finally {
      setAlpacaLoading(false)
    }
  }, [apiBase, authHeaders])

  const runAlpacaTrader = useCallback(async (execute: boolean) => {
    setAlpacaRunning(true)
    setAlpacaRunResult(null)
    try {
      const endpoint = execute ? 'execute' : 'run'
      const res = await fetch(`${apiBase}/api/paper-trading/${endpoint}`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const json = (await res.json()) as RunResult
      setAlpacaRunResult(json)
      if (json.ok) void loadAlpaca(true)
    } catch (e) {
      setAlpacaRunResult({ ok: false, stdout: '', stderr: e instanceof Error ? e.message : '실행 실패' })
    } finally {
      setAlpacaRunning(false)
    }
  }, [apiBase, authHeaders, loadAlpaca])

  const loadDropAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/paper-trading/drop-alerts`, { headers: authHeaders() })
      if (!res.ok) return
      const json = await res.json() as { ok: boolean; alerts: DropAlert[] }
      if (json.ok) setDropAlerts(json.alerts)
    } catch { /* silent */ }
  }, [apiBase, authHeaders])

  const loadResetStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/paper-trading/reset-status`, { headers: authHeaders() })
      if (!res.ok) return
      const json = (await res.json()) as PaperResetStatus
      setResetStatus(json)
    } catch { /* silent */ }
  }, [apiBase, authHeaders])

  const loadSelectionFlow = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/trading/selection-flow`, { headers: authHeaders() })
      if (!res.ok) return
      const json = (await res.json()) as TradingSelectionFlow
      setSelectionFlow(json)
    } catch { /* silent */ }
  }, [apiBase, authHeaders])

  const ackAlert = useCallback(async (alertId: string) => {
    try {
      await fetch(`${apiBase}/api/paper-trading/drop-alerts/ack`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alertId }),
      })
      setDropAlerts(prev => prev.map(a => a.id === alertId ? { ...a, acknowledged: true } : a))
    } catch { /* silent */ }
  }, [apiBase, authHeaders])

  // ── IBKR 데이터 로드 ──────────────────────────────────────────────────────

  const loadIbkr = useCallback(async (silent = false) => {
    if (!silent) setIbkrLoading(true)
    setIbkrError(null)
    try {
      const res = await fetch(`${apiBase}/api/ibkr/monitor`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = (await res.json()) as IbkrMonitorData
      setIbkrData(json)
      setIbkrLastFetch(new Date().toLocaleTimeString('ko-KR'))
    } catch (e) {
      setIbkrError(e instanceof Error ? e.message : '로드 실패')
    } finally {
      setIbkrLoading(false)
    }
  }, [apiBase, authHeaders])

  const runIbkrMonitor = useCallback(async (mode: 'scan' | 'execute') => {
    setIbkrRunning(true)
    setIbkrRunResult(null)
    setConfirmIbkrExecute(false)
    try {
      const endpoint = mode === 'execute' ? 'execute' : 'scan'
      const res = await fetch(`${apiBase}/api/ibkr/monitor/${endpoint}`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const json = (await res.json()) as RunResult
      setIbkrRunResult(json)
      if (json.ok) void loadIbkr(true)
    } catch (e) {
      setIbkrRunResult({ ok: false, stdout: '', stderr: e instanceof Error ? e.message : '실행 실패' })
    } finally {
      setIbkrRunning(false)
    }
  }, [apiBase, authHeaders, loadIbkr])

  // ── 초기 로드 + 자동 갱신 ────────────────────────────────────────────────

  useEffect(() => {
    const t = setTimeout(() => void loadAlpaca(), 0)
    const iv = setInterval(() => void loadAlpaca(true), 5 * 60 * 1000)
    return () => { clearTimeout(t); clearInterval(iv) }
  }, [loadAlpaca])

  useEffect(() => {
    void loadDropAlerts()
    const iv = setInterval(() => void loadDropAlerts(), 30 * 1000)
    return () => clearInterval(iv)
  }, [loadDropAlerts])

  useEffect(() => {
    void loadResetStatus()
    const iv = setInterval(() => void loadResetStatus(), 60 * 1000)
    return () => clearInterval(iv)
  }, [loadResetStatus])

  useEffect(() => {
    void loadSelectionFlow()
    const iv = setInterval(() => void loadSelectionFlow(), 60 * 1000)
    return () => clearInterval(iv)
  }, [loadSelectionFlow])

  useEffect(() => {
    const t = setTimeout(() => void loadIbkr(), 0)
    const iv = setInterval(() => void loadIbkr(true), 5 * 60 * 1000)
    return () => { clearTimeout(t); clearInterval(iv) }
  }, [loadIbkr])

  // symbol-names는 최초 1회만 로드 (universe.json 단일 소스)
  useEffect(() => {
    fetch(`${apiBase}/api/trading/symbol-names`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : {})
      .then((data: Record<string, string>) => setSymbolNames({ ...ETF_NAMES, ...data }))
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase])

  // ── 파생 값 계산 ─────────────────────────────────────────────────────────

  const alpacaAccount = alpacaData?.account
  const alpacaPositions = (alpacaData?.positions ?? []).filter(
    (p): p is AlpacaPosition & { symbol: string } => !p.error && !!p.symbol
  )
  const alpacaSignals = (alpacaData?.signals ?? []).filter(s => !s.error)
  const alpacaActiveSignals = alpacaData?.active_signals ?? []
  const alpacaOrders = alpacaData?.orders ?? []
  const ar018Kpi = alpacaData?.ar018_kpi

  const ibkrAccount = ibkrData?.account
  const ibkrPositions = ibkrData?.positions ?? []
  const ibkrCandidates = ibkrData?.entry_candidates ?? []
  const ibkrExitSignals = ibkrData?.exit_signals ?? []
  const gatewayConnected = ibkrData?.gateway_connected ?? false

  const totalPnl = alpacaAccount?.total_pnl ?? 0
  const totalPnlPct = alpacaAccount?.total_pnl_pct ?? 0

  const alpacaChartData = (() => {
    if (!alpacaData) return []
    const base = alpacaData.history.base ?? INITIAL_CAPITAL
    const current = alpacaAccount?.portfolio_value ?? base
    const pct = base > 0 ? ((current - base) / base) * 100 : 0
    const today = new Date().toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }).replace('. ', '/').replace('.', '')
    const raw = alpacaData.history.chart.filter(d => d.value > 0).slice(-30)
    if (raw.length >= 2) {
      return [...raw.slice(0, -1), { ...raw[raw.length - 1], value: current, pnl_pct: pct }]
    }
    return [
      { date: 'start', value: base, pnl_pct: 0 },
      { date: today, value: current, pnl_pct: pct },
    ]
  })()

  const hasAnyPositions = alpacaPositions.length > 0 || ibkrPositions.length > 0
  const ibkrMode = ibkrData?.mode ?? 'paper'
  const isLive = ibkrMode === 'live'

  // IBKR 차트 데이터 (nav_history 기반)
  const ibkrChartData: NavPoint[] = (() => {
    const hist = ibkrData?.nav_history ?? []
    if (hist.length >= 1) return hist
    // 단일 포인트: baseline → current
    const acct = ibkrData?.account
    if (!acct) return []
    const today = new Date().toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }).replace('. ', '/').replace('.', '')
    return [
      { date: 'start', value: acct.baseline_nav, pnl_pct: 0 },
      { date: today,   value: acct.nav, pnl_pct: acct.total_pnl_pct },
    ]
  })()

  const selectedUniverseRow = selectedFlowSymbol
    ? (selectionFlow?.selection_universe ?? []).find((row) => row.symbol === selectedFlowSymbol) ?? null
    : null
  const selectedEvidence = selectedFlowSymbol
    ? selectionFlow?.symbol_evidence?.[selectedFlowSymbol] ?? []
    : []
  const selectedSymbolEvents = selectedFlowSymbol
    ? (selectionFlow?.trade_flow ?? []).filter((event) => event.symbol === selectedFlowSymbol).slice(0, 8)
    : []

  // ── 렌더 ──────────────────────────────────────────────────────────────────

  return (
    <section className="trading-ops-section">

      {/* ── 실전 투자 모드 경고 배너 ── */}
      {isLive && (
        <div className="live-mode-banner">
          <span className="live-mode-icon">⚠</span>
          <span>
            <strong>IBKR 실전 투자 모드</strong> — 모든 주문은 실제 자금으로 체결됩니다.
            IB Gateway 포트 4001 · capital_action_approve 필요
          </span>
        </div>
      )}

      {/* ── 섹션 헤더 ── */}
      <div className="section-head">
        <div>
          <h2>트레이딩 오퍼레이션</h2>
          <p>Alpaca(모의투자)와 IBKR({isLive ? '실전 투자' : '실전 동일 규칙'})을 동등하게 비교합니다.</p>
          <p className="term-note">두 브로커 모두 Turtle Trading 5원칙을 기반으로 운영됩니다.</p>
        </div>
        <div className="section-head-actions trading-action-buttons">
          <span className="data-meta">
            {alpacaLastFetch && `Alpaca: ${alpacaLastFetch}`}
            {alpacaLastFetch && ibkrLastFetch && ' · '}
            {ibkrLastFetch && `IBKR: ${ibkrLastFetch}`}
          </span>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => { void loadAlpaca(); void loadIbkr() }}
            disabled={alpacaRunning || ibkrRunning}
          >
            새로고침
          </button>
          {/* Alpaca 버튼 */}
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => void runAlpacaTrader(false)}
            disabled={alpacaRunning || ibkrRunning}
            title="Alpaca: 신호 스캔 + 포지션 관리 (주문 없음)"
          >
            {alpacaRunning ? '실행 중…' : 'Alpaca 점검'}
          </button>
          <button
            type="button"
            className="btn-execute btn-sm"
            onClick={() => void runAlpacaTrader(true)}
            disabled={alpacaRunning || ibkrRunning}
            title="Alpaca: Turtle 신호 시 실제 Paper 주문 실행"
          >
            {alpacaRunning ? '실행 중…' : 'Alpaca 가상 주문'}
          </button>
          {/* IBKR 버튼 */}
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => void runIbkrMonitor('scan')}
            disabled={alpacaRunning || ibkrRunning}
            title="IBKR: 신호 스캔 (주문 없음)"
          >
            {ibkrRunning ? '실행 중…' : 'IBKR 점검'}
          </button>
          {!confirmIbkrExecute ? (
            <button
              type="button"
              className="btn-execute btn-sm"
              onClick={() => setConfirmIbkrExecute(true)}
              disabled={alpacaRunning || ibkrRunning || ibkrExitSignals.length === 0}
              title={ibkrExitSignals.length > 0 ? `EXIT 신호: ${ibkrExitSignals.join(', ')}` : '현재 EXIT 신호 없음'}
            >
              IBKR 청산 실행
            </button>
          ) : (
            <span className="ibkr-confirm-row">
              <span className="ibkr-confirm-label">{ibkrExitSignals.join(', ')} 청산?</span>
              <button type="button" className="btn-danger btn-sm" onClick={() => void runIbkrMonitor('execute')} disabled={ibkrRunning}>확인</button>
              <button type="button" className="btn-secondary btn-sm" onClick={() => setConfirmIbkrExecute(false)}>취소</button>
            </span>
          )}
        </div>
      </div>

      {resetStatus?.exists && (
        <article className="panel alpaca-full" style={{ marginBottom: '1rem' }}>
          <div className="panel-head">
            <h3>Paper Reset 상태</h3>
            <span className="data-meta">{resetStatus.checked_at ? `${relativeTime(resetStatus.checked_at)} 점검` : '상태 파일 기준'}</span>
          </div>
          <div className="alpaca-gate-status">
            {resetStatus.reset_pending ? (
              <span className="gate-chip blocked">청산 대기 중</span>
            ) : resetStatus.flat ? (
              <span className="gate-chip clear">Flat 완료</span>
            ) : (
              <span className="gate-chip aging">상태 확인 필요</span>
            )}
            <span className="data-meta">
              Alpaca 주문 {resetStatus.alpaca?.open_orders?.length ?? 0}건 · 포지션 {resetStatus.alpaca?.positions?.length ?? 0}건 · IBKR 주문 {resetStatus.ibkr?.open_orders?.length ?? 0}건 · 포지션 {resetStatus.ibkr?.positions?.length ?? 0}건
            </span>
          </div>
          {resetStatus.post_open_verification && (
            <div className="alpaca-gate-status" style={{ marginTop: '0.6rem' }}>
              {resetStatus.post_open_verification.ready_for_execute ? (
                <span className="gate-chip clear">재개 준비 완료</span>
              ) : (
                <span className="gate-chip aging">재개 준비 미완료</span>
              )}
              <span className="data-meta">
                {resetStatus.post_open_verification.checked_at
                  ? `${relativeTime(resetStatus.post_open_verification.checked_at)} 점검`
                  : '장 개장 후 점검 전'}
                {' · '}
                Alpaca dry-run {resetStatus.post_open_verification.alpaca_dry_run?.status ?? '대기'}
                {' · '}
                IBKR dry-run {resetStatus.post_open_verification.ibkr_dry_run?.status ?? '대기'}
              </span>
            </div>
          )}
          <p className="term-note">청산이 끝나기 전에는 새 진입이 자동 차단됩니다.</p>
          {resetStatus.next_action && <p className="term-note">{resetStatus.next_action}</p>}
          {resetStatus.post_open_verification?.next_action?.map((item, idx) => (
            <p key={`post-open-${idx}`} className="term-note">{item}</p>
          ))}
        </article>
      )}

      {selectionFlow?.ok && (
        <div className="sf-flow-stack">
          <article className="panel">
            <div className="panel-head">
              <h3>종목 선정 흐름</h3>
              <span className="data-meta">{selectionFlow.generated_at ? relativeTime(selectionFlow.generated_at) : '실시간'}</span>
            </div>
            <div className="sf-stats">
              <div className="sf-stat" title="Raw Signals — 아직 걸러지지 않은 초안 데이터">
                <span className="sf-stat-val">{selectionFlow.pipeline?.raw_total ?? 0}</span>
                <span className="sf-stat-lbl">원천</span>
              </div>
              <span className="sf-arr">→</span>
              <div className="sf-stat" title="Filtered Pass — 1차 필터를 통과한 데이터">
                <span className="sf-stat-val">{selectionFlow.pipeline?.filtered_pass ?? 0}</span>
                <span className="sf-stat-lbl">통과</span>
              </div>
              <span className="sf-arr">→</span>
              <div className="sf-stat" title="Signals — 실제 투자 후보로 승격된 신호">
                <span className="sf-stat-val">{selectionFlow.pipeline?.signal_total ?? 0}</span>
                <span className="sf-stat-lbl">후보</span>
              </div>
              <span className="sf-arr">→</span>
              <div className="sf-stat sf-stat-hi" title="Selected Universe — 실제로 감시하는 종목 목록">
                <span className="sf-stat-val">{selectionFlow.pipeline?.selected_universe_count ?? 0}</span>
                <span className="sf-stat-lbl">최종</span>
              </div>
              <span className="sf-sep" />
              <div className="sf-stat sf-stat-dim" title="Filtered Fail — 버려진 데이터">
                <span className="sf-stat-val">{selectionFlow.pipeline?.filtered_fail ?? 0}</span>
                <span className="sf-stat-lbl">제외</span>
              </div>
              <div className="sf-stat sf-stat-dim" title="Pending Orders — 아직 체결되지 않은 IBKR 주문">
                <span className="sf-stat-val">{selectionFlow.runtime_state?.ibkr_pending_orders?.length ?? 0}</span>
                <span className="sf-stat-lbl">미체결</span>
              </div>
            </div>
            <div className="mobile-card-list trading-mobile-only">
              {(selectionFlow.selection_universe ?? []).map((row) => (
                <button
                  key={`mobile-${row.symbol}`}
                  type="button"
                  className={`mobile-detail-card mobile-symbol-card ${selectedFlowSymbol === row.symbol ? 'selected' : ''}`}
                  onClick={() => setSelectedFlowSymbol(row.symbol)}
                >
                  <div className="mobile-card-head">
                    <div>
                      <strong>{row.symbol}</strong>
                      {(row.name || symbolNames[row.symbol]) && (
                        <span>{row.name || symbolNames[row.symbol]}</span>
                      )}
                    </div>
                    <span className="freshness-chip fresh">선정됨</span>
                  </div>
                  <div className="mobile-field-grid">
                    <MobileField label="시장" value={`${row.region ?? '—'} · ${row.sector ?? '—'}`} tone="muted" />
                    <MobileField label="선정 점수" value={row.harness_score ?? '—'} />
                    <MobileField label="근거 건수" value={row.evidence_count ?? '—'} />
                    <MobileField label="주문 가능 증권사" value={(row.brokers ?? []).join(', ') || '—'} tone="muted" />
                    <MobileField label="근거 출처" value={(row.matched_sources ?? []).slice(0, 3).join(', ') || '—'} tone="muted" />
                  </div>
                  <p className="mobile-card-note">{row.selection_reason || '선정 이유 정보가 없습니다.'}</p>
                </button>
              ))}
            </div>
            <div className="table-wrap trading-mobile-hide" style={{ marginTop: '0.75rem' }}>
              <table className="data-table sf-universe-table">
                <colgroup>
                  <col style={{ width: '120px' }} />
                  <col style={{ width: '48px' }} />
                  <col style={{ width: '48px' }} />
                  <col style={{ width: '150px' }} />
                  <col style={{ width: '80px' }} />
                  <col />
                </colgroup>
                <thead>
                  <tr>
                    <th>종목</th>
                    <th title="Harness Score — 얼마나 강하게 뽑혔는지">선정 점수</th>
                    <th title="Evidence Count — 판단 근거 개수">근거 건수</th>
                    <th title="Sources — 어디서 근거가 나왔는지">근거 출처</th>
                    <th title="Brokers — 어디서 실제 주문 가능한지">증권사</th>
                    <th>선정 이유</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectionFlow.selection_universe ?? []).map((row) => (
                    <tr
                      key={row.symbol}
                      onClick={() => setSelectedFlowSymbol(row.symbol)}
                      style={{ cursor: 'pointer', background: selectedFlowSymbol === row.symbol ? 'var(--bg-elevated)' : undefined }}
                    >
                      <td><SymbolCell symbol={row.symbol} /><div className="data-meta">{row.region} · {row.sector ?? '—'}</div></td>
                      <td className="num">{row.harness_score ?? '—'}</td>
                      <td className="num">{row.evidence_count ?? '—'}</td>
                      <td className="sf-td-truncate" title={(row.matched_sources ?? []).join(', ')}>{(row.matched_sources ?? []).slice(0, 3).join(', ') || '—'}</td>
                      <td className="sf-td-truncate" title={(row.brokers ?? []).join(', ')}>{(row.brokers ?? []).join(', ') || '—'}</td>
                      <td className="sf-reason-cell">{row.selection_reason_ko || row.selection_reason || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedUniverseRow && (
              <div style={{ marginTop: '0.9rem', borderTop: '1px solid var(--gridline)', paddingTop: '0.9rem' }}>
                <p className="data-label" style={{ marginBottom: '0.35rem' }}>
                  선택 종목 상세: {selectedUniverseRow.symbol} ({selectedUniverseRow.name ?? '종목명 확인 필요'})
                </p>
                <p className="term-note">
                  이 종목은 점수 {selectedUniverseRow.harness_score ?? '—'}점, 근거 {selectedUniverseRow.evidence_count ?? 0}건으로 선택됐습니다.
                  아래는 실제로 이 종목을 뽑는 데 쓰인 최근 근거입니다.
                </p>
                <div className="mobile-card-list trading-mobile-only" style={{ marginTop: '0.5rem' }}>
                  {selectedEvidence.length === 0 ? (
                    <div className="mobile-detail-card">
                      <p className="mobile-card-note">근거 원문 샘플이 없습니다.</p>
                    </div>
                  ) : selectedEvidence.map((row, idx) => (
                    <article key={`${selectedFlowSymbol}-mobile-evidence-${idx}`} className="mobile-detail-card">
                      <div className="mobile-card-head">
                        <div>
                          <strong>{row.source ?? '출처 미상'}</strong>
                          <span>{row.created_at ? String(row.created_at).slice(5, 16).replace('T', ' ') : '—'}</span>
                        </div>
                        <span className="freshness-chip aging">근거</span>
                      </div>
                      <p className="mobile-card-title">{row.title ?? '제목 없음'}</p>
                      <p className="mobile-card-note">{row.summary ?? '요약 없음'}</p>
                    </article>
                  ))}
                </div>
                <div className="table-wrap trading-mobile-hide" style={{ marginTop: '0.5rem' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>근거 시각</th>
                        <th>출처</th>
                        <th>제목</th>
                        <th>요약</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedEvidence.length === 0 ? (
                        <tr><td colSpan={4} className="data-meta">근거 원문 샘플이 없습니다.</td></tr>
                      ) : selectedEvidence.map((row, idx) => (
                        <tr key={`${selectedFlowSymbol}-evidence-${idx}`}>
                          <td className="data-meta">{row.created_at ? String(row.created_at).slice(5, 16).replace('T', ' ') : '—'}</td>
                          <td>{row.source ?? '—'}</td>
                          <td>{row.title ?? '—'}</td>
                          <td className="data-meta">{row.summary ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {selectedSymbolEvents.length > 0 && (
                  <div style={{ marginTop: '0.75rem' }}>
                    <p className="data-label" style={{ marginBottom: '0.35rem' }}>이 종목의 최근 매수·매도 이벤트</p>
                    <div className="mobile-card-list trading-mobile-only">
                      {selectedSymbolEvents.map((event, idx) => (
                        <article key={`${selectedFlowSymbol}-mobile-event-${idx}`} className="mobile-detail-card">
                          <div className="mobile-card-head">
                            <div>
                              <strong>{event.ts ? event.ts.slice(5, 16).replace('T', ' ') : '—'}</strong>
                              <span>{event.source ?? '출처 없음'}</span>
                            </div>
                            <span className={`freshness-chip ${flowEventTone(event.kind)}`} title={flowEventLabel(event.kind)}>{flowEventShortLabel(event.kind)}</span>
                          </div>
                          <p className="mobile-card-note">{event.title ?? '설명 없음'}</p>
                        </article>
                      ))}
                    </div>
                    <ul className="kpi-list">
                      {selectedSymbolEvents.map((event, idx) => (
                        <li key={`${selectedFlowSymbol}-event-${idx}`}>
                          <strong>{event.ts ? event.ts.slice(5, 16).replace('T', ' ') : '—'}</strong> · {flowEventLabel(event.kind)} · {event.title ?? '—'}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </article>

          <article className="panel">
            <div className="panel-head">
              <h3>매수·매도 흐름</h3>
              <span className="data-meta">최근 80건</span>
            </div>
            <p className="term-note">이 표는 조사, 신호 점검, 매수 시도, 매도 시도, 주문 거절, 사람 메모까지 시간순으로 보여줍니다.</p>
            <div className="mobile-card-list trading-mobile-only">
              {(selectionFlow.trade_flow ?? []).slice(0, 20).map((event, idx) => (
                <article key={`mobile-flow-${event.ts ?? 'na'}-${event.kind ?? 'na'}-${idx}`} className="mobile-detail-card">
                  <div className="mobile-card-head">
                    <div>
                      <strong>{event.symbol ?? '공통 이벤트'}</strong>
                      <span>{event.ts ? event.ts.slice(5, 16).replace('T', ' ') : '—'}</span>
                    </div>
                    <span className={`freshness-chip ${flowEventTone(event.kind)}`} title={flowEventLabel(event.kind)}>{flowEventShortLabel(event.kind)}</span>
                  </div>
                  <div className="mobile-field-grid">
                    <MobileField label="출처" value={event.source ?? '—'} tone="muted" />
                    <MobileField label="세부" value={event.title ?? '설명 없음'} tone="muted" />
                  </div>
                </article>
              ))}
            </div>
            <div className="table-wrap trading-mobile-hide">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>시각</th>
                    <th>종목</th>
                    <th>이벤트</th>
                    <th>출처</th>
                    <th>세부</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectionFlow.trade_flow ?? []).slice(0, 30).map((event, idx) => (
                    <tr key={`${event.ts ?? 'na'}-${event.kind ?? 'na'}-${idx}`}>
                      <td className="data-meta">{event.ts ? event.ts.slice(5, 16).replace('T', ' ') : '—'}</td>
                      <td>{event.symbol ? <SymbolCell symbol={event.symbol} /> : '—'}</td>
                      <td><span className={`freshness-chip ${flowEventTone(event.kind)}`} title={flowEventLabel(event.kind)}>{flowEventShortLabel(event.kind)}</span></td>
                      <td className="data-meta">{event.source ?? '—'}</td>
                      <td className="sf-td-truncate data-meta" title={event.title ?? ''}>{event.title ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </div>
      )}

      {/* ── ROW 1: 계좌 요약 (side-by-side) ── */}
      <div className="trading-accounts-grid">

        {/* Alpaca 계좌 카드 */}
        <article className="trading-account-card alpaca">
          <div className="panel-head">
            <h3>Alpaca <span className="broker-tag alpaca">모의투자</span></h3>
          </div>
          {alpacaLoading ? (
            <p className="data-meta loading-pulse">Alpaca 계좌 로드 중…</p>
          ) : alpacaError || !alpacaAccount ? (
            <div>
              <p className="data-warn">연결 오류: {alpacaError ?? '알 수 없는 오류'}</p>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void loadAlpaca()}>재시도</button>
            </div>
          ) : !alpacaAccount.ok ? (
            <p className="data-warn">계좌 조회 실패: {alpacaAccount.error}</p>
          ) : (
            <>
              <div className="split-2">
                <div>
                  <p className="data-label">포트폴리오 가치</p>
                  <p className="data-value">${fmt(alpacaAccount.portfolio_value)}</p>
                </div>
                <div>
                  <p className="data-label">총 손익</p>
                  <p className={`data-value ${totalPnl >= 0 ? 'pnl-pos' : 'pnl-neg'}`}>
                    {fmtUsd(totalPnl)}
                    <span className="data-sub"> ({fmtPct(totalPnlPct)})</span>
                  </p>
                </div>
              </div>
              <div className="split-3 mt-2">
                <div>
                  <p className="data-label">현금</p>
                  <p className="data-value-sm">${fmt(alpacaAccount.cash)}</p>
                </div>
                <div>
                  <p className="data-label">매수 가능</p>
                  <p className="data-value-sm">${fmt(alpacaAccount.buying_power)}</p>
                </div>
                <div>
                  <p className="data-label">당일 매매</p>
                  <p className="data-value-sm">{alpacaAccount.day_trade_count ?? 0}회</p>
                </div>
              </div>
              <div className="alpaca-spark">
                <p className="data-label">포트폴리오 추이 (30D)</p>
                <PortfolioChart data={alpacaChartData} />
              </div>
            </>
          )}
        </article>

        {/* IBKR 계좌 카드 */}
        <article className={`trading-account-card ibkr${isLive ? ' live-mode' : ''}`}>
          <div className="panel-head">
            <h3>
              IBKR{' '}
              {isLive
                ? <span className="broker-tag live">실전 투자</span>
                : <span className="broker-tag ibkr">실전 동일 규칙</span>
              }
            </h3>
            {ibkrAccount?.account_id && (
              <span className="data-meta mono">
                {ibkrAccount.account_id} · {isLive ? '실전 투자' : 'Paper Trading'}
              </span>
            )}
          </div>
          {ibkrLoading ? (
            <p className="data-meta loading-pulse">IBKR 계좌 로드 중…</p>
          ) : ibkrError && !ibkrData ? (
            <div>
              <p className="data-warn">연결 오류: {ibkrError}</p>
              <button type="button" className="btn-secondary btn-sm" onClick={() => void loadIbkr()}>재시도</button>
            </div>
          ) : (
            <>
              {/* 게이트웨이 상태 */}
              <div className={`ibkr-status-row ${ibkrExitSignals.length > 0 ? 'has-exit' : ''}`} style={{ marginBottom: '0.75rem' }}>
                <span className={`gateway-dot ${gatewayConnected ? 'online' : 'offline'}`} />
                <span className="ibkr-status-item">
                  <span className="ibkr-status-label">Gateway</span>
                  <span className="ibkr-status-value">{gatewayConnected ? '연결됨' : '오프라인'}</span>
                </span>
                {ibkrData?.ts && (
                  <>
                    <span className="ibkr-status-sep">·</span>
                    <span className="ibkr-status-meta">{relativeTime(ibkrData.ts)}</span>
                  </>
                )}
                {ibkrExitSignals.length > 0 && (
                  <>
                    <span className="ibkr-status-sep">·</span>
                    <span className="ibkr-exit-alert">⚠ EXIT {ibkrExitSignals.length}건</span>
                  </>
                )}
              </div>

              {ibkrAccount ? (
                <>
                  <div className="split-2">
                    <div>
                      <p className="data-label">NAV</p>
                      <p className="data-value">${fmt(ibkrAccount.nav)}</p>
                    </div>
                    <div>
                      <p className="data-label">총 손익</p>
                      <p className={`data-value ${ibkrAccount.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg'}`}>
                        {fmtUsd(ibkrAccount.total_pnl)}
                        <span className="data-sub"> ({fmtPct(ibkrAccount.total_pnl_pct)})</span>
                      </p>
                    </div>
                  </div>
                  <div className="split-3 mt-2">
                    <div>
                      <p className="data-label">현금</p>
                      <p className="data-value-sm">${fmt(ibkrAccount.cash, 0)}</p>
                    </div>
                    <div>
                      <p className="data-label">포지션</p>
                      <p className="data-value-sm">{ibkrPositions.length}건</p>
                    </div>
                    <div>
                      <p className="data-label">신호</p>
                      <p className="data-value-sm">{ibkrExitSignals.length > 0 ? `EXIT ${ibkrExitSignals.length}` : '없음'}</p>
                    </div>
                  </div>
                </>
              ) : (
                <p className="data-meta">{gatewayConnected ? '계좌 정보 없음' : 'Gateway 연결 후 계좌 정보 표시'}</p>
              )}

              {/* IBKR 포지션 미니 요약 */}
              {ibkrPositions.length > 0 && (
                <div className="ibkr-pos-summary">
                  <p className="data-label" style={{ marginBottom: '0.35rem' }}>포지션 현황</p>
                  {ibkrPositions.map(pos => (
                    <div key={pos.symbol} className={`ibkr-pos-row ${pos.action !== 'HOLD' ? 'ibkr-pos-exit' : ''}`}>
                      <span className="ibkr-pos-symbol">
                        <strong>{pos.symbol}</strong>
                        {symbolNames[pos.symbol] && <small>{symbolNames[pos.symbol]}</small>}
                      </span>
                      <span className={`ibkr-pos-pnl ${(pos.unrealized_pnl_pct ?? 0) >= 0 ? 'pnl-pos' : 'pnl-neg'}`}>
                        {fmtPct(pos.unrealized_pnl_pct)}
                      </span>
                      <ActionBadge action={pos.action} />
                    </div>
                  ))}
                </div>
              )}

              {/* IBKR 포트폴리오 추이 차트 */}
              {ibkrChartData.length >= 2 && (
                <div className="alpaca-spark" style={{ marginTop: '0.75rem' }}>
                  <p className="data-label">포트폴리오 추이</p>
                  <PortfolioChart data={ibkrChartData} gradientId="ibkrGrad" />
                </div>
              )}

              {/* 실시간 환율 */}
              {ibkrData?.forex_rates && Object.keys(ibkrData.forex_rates).length > 0 && (
                <div className="forex-rates-row">
                  {Object.entries(ibkrData.forex_rates).map(([cur, info]) => (
                    <span key={cur} className="forex-rate-chip" title={`출처: ${info.source} · ${info.age_sec}초 전`}>
                      <span className="forex-cur">{cur}</span>
                      <span className="forex-val">
                        {info.units_per_usd != null
                          ? cur === 'JPY' || cur === 'KRW'
                            ? Math.round(info.units_per_usd).toLocaleString()
                            : info.units_per_usd.toFixed(2)
                          : '—'}
                      </span>
                      <span className={`forex-src ${info.source === 'open.er-api.com' ? 'live' : info.source === 'IBKR_historical' ? 'ibkr' : 'fallback'}`}>
                        {info.source === 'open.er-api.com' ? '실시간' : info.source === 'IBKR_historical' ? 'IBKR' : '근사'}
                      </span>
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
        </article>
      </div>

      {/* ── ROW 1.5: IBKR 오프라인 / EXIT 배너 ── */}
      {!ibkrLoading && ibkrData && !gatewayConnected && (
        <div className="ibkr-offline-banner">
          <span className="gateway-dot offline" />
          IB Gateway 오프라인 — 포지션은 상태 파일 기준으로 표시됩니다. 현재가 및 신호는 연결 후 갱신됩니다.
        </div>
      )}
      {!ibkrLoading && ibkrExitSignals.length > 0 && (
        <div className="ibkr-exit-banner">
          <span>⚠ EXIT 신호 발생: </span>
          {ibkrExitSignals.map(s => <strong key={s}>{s} </strong>)}
          <span>— "IBKR 청산 실행" 버튼으로 GTC 매도 주문을 발행하세요.</span>
        </div>
      )}

      {/* ── 실행 결과 박스 ── */}
      {alpacaRunResult && (
        <div className={`run-result-box ${alpacaRunResult.ok ? 'run-ok' : 'run-err'}`}>
          <div className="run-result-head">
            <span>Alpaca 실행 결과 — {alpacaRunResult.ok ? '✓ 완료' : '✗ 실패'}</span>
            <button type="button" className="btn-ghost btn-xs" onClick={() => setAlpacaRunResult(null)}>✕</button>
          </div>
          {alpacaRunResult.stdout && <pre className="run-output">{alpacaRunResult.stdout}</pre>}
          {alpacaRunResult.stderr && <pre className="run-output run-stderr">{alpacaRunResult.stderr}</pre>}
        </div>
      )}
      {ibkrRunResult && (
        <div className={`run-result-box ${ibkrRunResult.ok ? 'run-ok' : 'run-err'}`}>
          <div className="run-result-head">
            <span>IBKR 실행 결과 — {ibkrRunResult.ok ? '✓ 완료' : '✗ 실패'}</span>
            <button type="button" className="btn-ghost btn-xs" onClick={() => setIbkrRunResult(null)}>✕</button>
          </div>
          {ibkrRunResult.stdout && <pre className="run-output">{ibkrRunResult.stdout}</pre>}
          {ibkrRunResult.stderr && <pre className="run-output run-stderr">{ibkrRunResult.stderr}</pre>}
        </div>
      )}

      {/* ── ROW 2: 통합 포지션 테이블 ── */}
      {hasAnyPositions && (
        <article className="panel alpaca-full">
          <div className="panel-head">
            <h3>현재 포지션</h3>
            <span className="data-meta">
              총 {alpacaPositions.length + ibkrPositions.length}건
              {alpacaPositions.length > 0 && ` (Alpaca ${alpacaPositions.length})`}
              {ibkrPositions.length > 0 && ` (IBKR ${ibkrPositions.length})`}
            </span>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>브로커</th>
                  <th>종목</th>
                  <th className="num">수량</th>
                  <th className="num">진입가</th>
                  <th className="num">현재가</th>
                  <th className="num">손익</th>
                  <th className="num">손익%</th>
                  <th className="num">손절가</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {alpacaPositions.map(p => (
                  <tr key={`alpaca-${p.symbol}`} className={p.near_stop ? 'row-warning' : ''}>
                    <td><span className="broker-tag alpaca">Alpaca</span></td>
                    <td><SymbolCell symbol={p.symbol} names={symbolNames} /></td>
                    <td className="num">{p.qty}</td>
                    <td className="num">${fmt(p.entry_price)}</td>
                    <td className="num">${fmt(p.current_price)}</td>
                    <td className={`num ${(p.unrealized_pnl ?? 0) > 0 ? 'pnl-pos' : (p.unrealized_pnl ?? 0) < 0 ? 'pnl-neg' : ''}`}>
                      {fmtUsd(p.unrealized_pnl)}
                    </td>
                    <PnlCell v={p.unrealized_pnl_pct} />
                    <td className="num">{p.stop_loss ? `$${fmt(p.stop_loss)}` : '—'}</td>
                    <td>
                      {p.near_stop
                        ? <span className="signal-badge signal-short">⚠ 손절 근접</span>
                        : <span className="signal-badge signal-neutral">정상</span>}
                    </td>
                  </tr>
                ))}
                {ibkrPositions.map(pos => (
                  <tr key={`ibkr-${pos.symbol}`} className={pos.near_stop ? 'row-warning' : pos.action !== 'HOLD' ? 'row-highlight' : ''}>
                    <td><span className="broker-tag ibkr">IBKR</span></td>
                    <td><SymbolCell symbol={pos.symbol} names={symbolNames} /></td>
                    <td className="num">{pos.qty}</td>
                    <td className="num">${fmt(pos.entry_price)}</td>
                    <td className="num">{pos.current_price !== null ? `$${fmt(pos.current_price)}` : '—'}</td>
                    <td className={`num ${(pos.unrealized_pnl ?? 0) > 0 ? 'pnl-pos' : (pos.unrealized_pnl ?? 0) < 0 ? 'pnl-neg' : ''}`}>
                      {fmtUsd(pos.unrealized_pnl)}
                    </td>
                    <PnlCell v={pos.unrealized_pnl_pct} />
                    <td className="num">${fmt(pos.stop_loss)}{pos.stop_distance_pct !== null ? ` (${fmt(pos.stop_distance_pct, 1)}%)` : ''}</td>
                    <td><ActionBadge action={pos.action} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* IBKR 포지션 위험 바 (포지션이 있을 때만) */}
          {ibkrPositions.length > 0 && (
            <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border, #e2e8f0)', paddingTop: '0.75rem' }}>
              <p className="data-label" style={{ marginBottom: '0.5rem' }}>IBKR 위험 지표 (손절·청산선 거리)</p>
              <div className="position-cards-grid">
                {ibkrPositions.map(pos => (
                  <div key={`risk-${pos.symbol}`} className={`position-risk-card ${pos.action !== 'HOLD' ? 'action-exit' : ''}`}>
                    <div className="prcard-header">
                      <div className="prcard-symbol">
                        <strong>{pos.symbol}</strong>
                        {symbolNames[pos.symbol] && <small>{symbolNames[pos.symbol]}</small>}
                      </div>
                      <ActionBadge action={pos.action} />
                    </div>
                    <div className="prcard-meta">{pos.qty}주 · {pos.exchange} · 진입 {formatEntryDate(pos.entry_ts)}</div>
                    <div className="prcard-prices">
                      <div className="prcard-price-main">{pos.current_price !== null ? `$${fmt(pos.current_price)}` : '—'}</div>
                      <div className="prcard-price-entry">진입 ${fmt(pos.entry_price)}</div>
                      <div className={`prcard-pnl ${(pos.unrealized_pnl ?? 0) >= 0 ? 'pnl-pos' : 'pnl-neg'}`}>
                        {fmtUsd(pos.unrealized_pnl)}<span> ({fmtPct(pos.unrealized_pnl_pct)})</span>
                      </div>
                    </div>
                    <div className="prcard-risk-section">
                      <p className="prcard-risk-title">위험 지표 <small>(낮을수록 청산 임박)</small></p>
                      <RiskBar label="손절가" distancePct={pos.stop_distance_pct} referencePrice={pos.stop_loss} />
                      <RiskBar label="S1 청산" distancePct={pos.s1_distance_pct} referencePrice={pos.s1_low} />
                      <RiskBar label="S2 청산" distancePct={pos.s2_distance_pct} referencePrice={pos.s2_low} />
                    </div>
                    <div className="prcard-footer">
                      <span>ATR ${fmt(pos.atr)}</span>
                      {pos.market_value !== null && <span>시장가치 ${fmt(pos.market_value, 0)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </article>
      )}

      {/* ── ROW 3: 투자 신호 모니터 (탭) ── */}
      <article className="panel alpaca-full">
        <div className="panel-head">
          <h3>투자 신호 모니터</h3>
          <span className="term-note">Turtle Trading S1(20일)/S2(55일) 브레이크아웃 기준</span>
        </div>

        <div className="signal-tabs">
          <button
            type="button"
            className={`signal-tab ${activeSignalTab === 'ibkr' ? 'active' : ''}`}
            onClick={() => setActiveSignalTab('ibkr')}
          >
            IBKR 유니버스
            {ibkrCandidates.filter(c => c.signal === 'breakout_long').length > 0 && (
              <span className="signal-tab-badge">{ibkrCandidates.filter(c => c.signal === 'breakout_long').length}</span>
            )}
          </button>
          <button
            type="button"
            className={`signal-tab ${activeSignalTab === 'alpaca' ? 'active' : ''}`}
            onClick={() => setActiveSignalTab('alpaca')}
          >
            Alpaca 유니버스
            {alpacaActiveSignals.length > 0 && (
              <span className="signal-tab-badge">{alpacaActiveSignals.length}</span>
            )}
          </button>
        </div>

        {/* IBKR 신호 탭 */}
        {activeSignalTab === 'ibkr' && (
          <>
            <span className="data-meta" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Universe 소스: <code>{ibkrData?.universe_source ?? '—'}</code>
              {ibkrCandidates.filter(c => c.signal === 'breakout_long').length > 0 && (
                <span className="entry-scanner-active">
                  {' '}· 활성 신호 {ibkrCandidates.filter(c => c.signal === 'breakout_long').length}건
                </span>
              )}
            </span>

            {/* 지역 필터 */}
            {ibkrCandidates.length > 0 && (() => {
              const regions = ['ALL', 'US', 'KR', 'TW', 'JP', 'HK']
              return (
                <div className="region-filter-bar">
                  {regions.map(r => (
                    <button
                      key={r}
                      type="button"
                      className={`region-filter-btn ${regionFilter === r ? 'active' : ''}`}
                      onClick={() => setRegionFilter(r)}
                    >
                      {r === 'ALL' ? '전체' : `${REGION_FLAG[r] ?? ''} ${r}`}
                      <span className="region-count">
                        {r === 'ALL'
                          ? ibkrCandidates.length
                          : ibkrCandidates.filter(c => (c.region ?? 'US') === r).length}
                      </span>
                    </button>
                  ))}
                </div>
              )
            })()}

            {ibkrLoading ? (
              <p className="data-meta loading-pulse">IBKR 신호 로드 중…</p>
            ) : ibkrCandidates.length === 0 ? (
              <p className="data-meta">IBKR 신호 데이터 없음</p>
            ) : (
              <>
                {ibkrCandidates.filter(c => c.signal === 'breakout_long').length > 0 && (
                  <div className="entry-breakout-bar">
                    <span className="data-label-inline">활성 신호:</span>
                    {ibkrCandidates.filter(c => c.signal === 'breakout_long').map(c => (
                      <span key={c.symbol} className="active-signal-chip">
                        <span className="region-flag">{REGION_FLAG[c.region ?? 'US'] ?? '🌐'}</span>
                        <strong>{c.symbol}</strong>
                        {(c.name || symbolNames[c.symbol]) && <small>{c.name || symbolNames[c.symbol]}</small>}
                        <IbkrSignalBadge signal={c.signal} active={c.active_signal} />
                        {c.in_position && <span className="in-pos-chip">보유 중</span>}
                      </span>
                    ))}
                  </div>
                )}
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>종목</th>
                        <th className="num">현재가</th>
                        <th className="num">S1 돌파기준</th>
                        <th className="num">S2 돌파기준</th>
                        <th className="num">S2 거리</th>
                        <th className="num">ATR</th>
                        <th>신호</th>
                        <th>상태</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        const filtered = regionFilter === 'ALL'
                          ? ibkrCandidates
                          : ibkrCandidates.filter(c => (c.region ?? 'US') === regionFilter)
                        const sorted = [
                          ...filtered.filter(c => c.signal === 'breakout_long'),
                          ...filtered.filter(c => c.signal !== 'breakout_long'),
                        ]
                        return sorted.map(c => (
                          <tr key={c.symbol} className={c.signal === 'breakout_long' ? 'row-highlight' : c.in_position ? 'row-in-position' : ''}>
                            <td>
                              <div className="intl-symbol-cell">
                                <span className="region-flag">{REGION_FLAG[c.region ?? 'US'] ?? '🌐'}</span>
                                <div>
                                  <strong>{c.symbol}</strong>
                                  <small>{c.name || symbolNames[c.symbol] || ''}</small>
                                </div>
                                {c.sector && <span className="sector-chip">{c.sector}</span>}
                              </div>
                            </td>
                            <td className="num">{fmtLocalPrice(c.current_price, c.currency ?? 'USD')}</td>
                            <td className="num">{c.s1_high !== null ? fmtLocalPrice(c.s1_high, c.currency ?? 'USD') : '—'}</td>
                            <td className="num">{c.s2_high !== null ? fmtLocalPrice(c.s2_high, c.currency ?? 'USD') : '—'}</td>
                            <td className={`num ${c.gap_pct !== null && c.gap_pct > 0 ? 'pnl-pos' : c.gap_pct !== null && c.gap_pct < 0 ? 'pnl-neg' : ''}`}>
                              {c.gap_pct !== null ? `${c.gap_pct >= 0 ? '+' : ''}${fmt(c.gap_pct, 1)}%` : '—'}
                            </td>
                            <td className="num">{c.atr !== null ? fmt(c.atr, 2) : '—'}</td>
                            <td><IbkrSignalBadge signal={c.signal} active={c.active_signal} /></td>
                            <td>{c.in_position ? <span className="in-pos-chip">보유 중</span> : <span className="data-meta">—</span>}</td>
                          </tr>
                        ))
                      })()}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}

        {/* Alpaca 신호 탭 */}
        {activeSignalTab === 'alpaca' && (
          <>
            <span className="data-meta" style={{ display: 'block', marginBottom: '0.5rem' }}>
              관찰 종목: {(alpacaData?.universe ?? []).map(sym => {
                const item = symDisplay(sym, symbolNames)
                return `${item.code}(${item.name})`
              }).join(', ') || '—'}
            </span>
            {alpacaLoading ? (
              <p className="data-meta loading-pulse">Alpaca 신호 로드 중…</p>
            ) : alpacaSignals.length === 0 ? (
              <p className="data-meta">Alpaca 신호 데이터 없음</p>
            ) : (
              <>
                {alpacaActiveSignals.length > 0 && (
                  <div className="active-signals-bar">
                    <span className="data-label-inline">활성 신호:</span>
                    {alpacaActiveSignals.map(s => (
                      <span key={s.symbol} className="active-signal-chip">
                        <SymbolCell symbol={s.symbol} names={symbolNames} />
                        <AlpacaSignalBadge signal={s.signal} />
                        {s.system}
                      </span>
                    ))}
                  </div>
                )}
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>종목</th>
                        <th>신호</th>
                        <th>시스템</th>
                        <th className="num">현재가</th>
                        <th className="num">ATR</th>
                        <th className="num">S1 고가</th>
                        <th className="num">S1 저가</th>
                        <th className="num">S2 고가</th>
                        <th className="num">S2 저가</th>
                        <th className="num">손절(롱)</th>
                        <th>기준일</th>
                      </tr>
                    </thead>
                    <tbody>
                      {alpacaSignals.map(s => (
                        <tr key={s.symbol} className={s.signal !== 'neutral' ? 'row-highlight' : ''}>
                          <td><SymbolCell symbol={s.symbol} names={symbolNames} /></td>
                          <td><AlpacaSignalBadge signal={s.signal} /></td>
                          <td>{s.system ?? '—'}</td>
                          <td className="num">${fmt(s.current_price)}</td>
                          <td className="num">{s.atr ? fmt(s.atr, 4) : '—'}</td>
                          <td className="num">${fmt(s.s1_high)}</td>
                          <td className="num">${fmt(s.s1_low)}</td>
                          <td className="num">${fmt(s.s2_high)}</td>
                          <td className="num">${fmt(s.s2_low)}</td>
                          <td className="num">{s.stop_long ? `$${fmt(s.stop_long)}` : '—'}</td>
                          <td>{s.as_of ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </article>

      {/* ── ROW 4: Turtle 시스템 준비도 ── */}
      <div className="turtle-readiness-grid">
        {/* Alpaca AR-018 KPI */}
        <article className="panel">
          <div className="panel-head">
            <h3>AR-018 통과 기준 <span className="broker-tag alpaca">Alpaca</span></h3>
            <span className="data-meta">8주 모의 투자 기간에 반드시 확인할 조건</span>
          </div>
          {ar018Kpi ? (
            <ul className="kpi-list">
              <KpiRow
                label="누적 수익률"
                value={fmtPct(totalPnlPct)}
                pass={undefined}
                note="목표: 미국 대표 주가지수보다 5%p 이상 뒤처지지 않기"
              />
              <KpiRow
                label="최대 단일 포지션 손실"
                value={fmtPct(ar018Kpi.max_position_loss_pct)}
                pass={ar018Kpi.max_loss_pass}
                note="기준: ≤ −15%"
              />
              <KpiRow
                label="실제 입금 한도"
                value={`$${ar018Kpi.deposit_cap_usd} hard-cap`}
                pass={undefined}
                note="8주 기준을 통과하기 전에는 실제 입금 금지"
              />
              <KpiRow
                label="모의투자 기간 목표"
                value={`${ar018Kpi.week_target}주`}
                pass={undefined}
                note="실제 증권계좌로 옮기기 전 선행 조건"
              />
            </ul>
          ) : (
            <p className="data-meta">{alpacaLoading ? '로드 중…' : 'KPI 데이터 없음'}</p>
          )}
          <div className="alpaca-gate-status">
            <span className="gate-chip blocked">실전 투자 잠금</span>
            <span className="data-meta"> — 일부 안전 조건이 아직 끝나지 않았습니다</span>
            <p className="term-note">TurtleGate는 손절가·위험 한도·사전 검토가 모두 맞는지 보는 자동 안전장치입니다.</p>
          </div>
        </article>

        {/* IBKR TurtleGate 상태 */}
        <article className="panel">
          <div className="panel-head">
            <h3>TurtleGate 상태 <span className="broker-tag ibkr">IBKR</span></h3>
            <span className="data-meta">capital_action_approve 선행 조건</span>
          </div>
          <ul className="kpi-list">
            <KpiRow
              label="Gateway 연결"
              value={gatewayConnected ? '연결됨' : '오프라인'}
              pass={gatewayConnected}
              note="IB Gateway 4002 포트 연결 상태"
            />
            <KpiRow
              label="포지션 모니터링"
              value={ibkrPositions.length > 0 ? `${ibkrPositions.length}건 감시 중` : '포지션 없음'}
              pass={ibkrPositions.length === 0 || ibkrPositions.every(p => p.stop_loss > 0)}
              note="모든 포지션에 손절가 설정 확인"
            />
            <KpiRow
              label="계좌 리스크"
              value={ibkrAccount ? `NAV $${fmt(ibkrAccount.nav, 0)}` : '—'}
              pass={ibkrAccount ? Math.abs(ibkrAccount.total_pnl_pct) < 1 : undefined}
              note="단일 트레이드 계좌 리스크 ≤ 1% 원칙"
            />
            <KpiRow
              label="EXIT 신호"
              value={ibkrExitSignals.length > 0 ? `${ibkrExitSignals.join(', ')}` : '없음'}
              pass={ibkrExitSignals.length === 0}
              note="청산 신호 발생 시 즉시 실행 필요"
            />
          </ul>
          <div className="alpaca-gate-status">
            {ibkrError ? (
              <span className="gate-chip blocked">연결 오류</span>
            ) : gatewayConnected ? (
              <span className="gate-chip clear">Gateway 정상</span>
            ) : (
              <span className="gate-chip blocked">Gateway 오프라인</span>
            )}
            <p className="term-note">turtle_gate_clear는 6대 파라미터(진입 신호·ATR·포지션 리스크·손절가·청산·pre_mortem) 전부 통과 시 발행됩니다.</p>
          </div>
        </article>
      </div>

      {/* ── ROW 5: 최근 주문 내역 (Alpaca) ── */}
      {alpacaOrders.length > 0 && !alpacaOrders[0]?.error && (
        <article className="panel alpaca-full">
          <div className="panel-head">
            <h3>최근 주문 내역 <span className="broker-tag alpaca">Alpaca</span></h3>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>주문ID</th><th>종목</th><th>방향</th><th>유형</th>
                  <th className="num">수량</th><th className="num">체결수량</th>
                  <th className="num">체결가</th><th>상태</th><th>제출시각</th>
                </tr>
              </thead>
              <tbody>
                {(alpacaOrders as AlpacaOrder[]).map((o, i) => (
                  <tr key={`${o.id ?? ''}-${i}`}>
                    <td className="mono">{o.id}</td>
                    <td><SymbolCell symbol={o.symbol} names={symbolNames} /></td>
                    <td>
                      <span className={`signal-badge ${o.side === 'buy' ? 'signal-long' : 'signal-short'}`}>
                        {o.side === 'buy' ? '매수' : '매도'}
                      </span>
                    </td>
                    <td>{o.type}</td>
                    <td className="num">{o.qty}</td>
                    <td className="num">{o.filled_qty ?? '—'}</td>
                    <td className="num">{o.fill_price ? `$${fmt(parseFloat(o.fill_price))}` : '—'}</td>
                    <td>
                      <span className={`freshness-chip ${o.status === 'filled' ? 'fresh' : o.status === 'canceled' ? 'stale' : 'aging'}`}>
                        {o.status}
                      </span>
                    </td>
                    <td className="data-meta">{o.submitted_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* IBKR EXIT 신호 노트 */}
          {ibkrExitSignals.length > 0 && (
            <p className="term-note" style={{ marginTop: '0.5rem' }}>
              IBKR EXIT 신호: {ibkrExitSignals.join(', ')} — 위 "IBKR 청산 실행" 버튼으로 실행하세요.
            </p>
          )}
        </article>
      )}

      {/* ── ROW 6: 급락 브리핑 (Alpaca 전용) ── */}
      <DropAlertPanel
        alerts={dropAlerts}
        onAck={ackAlert}
        threshold={-3}
      />

    </section>
  )
}
