import { useCallback, useEffect, useState } from 'react'

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
  currency?: string
  primary_exchange?: string
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
  resident_stop_missing?: boolean
  adopted?: boolean
}

type IbkrPendingOrder = {
  symbol: string
  exchange: string
  currency: string
  region: string
  qty: number
  entry_ts: string
  entry_price: number
  stop_loss: number | null
  atr: number | null
  order_id: number | string | null
  status: string
  current_price: number | null
  gap_to_entry_pct: number | null
  age_hours: number | null
}

type IbkrCandidate = {
  symbol: string
  current_price: number | null
  s1_high: number | null
  s2_high: number | null
  atr: number | null
  signal: string
  active_signal: string | null
  gap_pct: number | null
  in_position: boolean
}

type IbkrMonitorData = {
  ok: boolean
  ts: string
  gateway_connected: boolean
  gateway_status?: {
    status: 'offline' | 'launching' | 'waiting_for_2fa' | 'ready'
    message: string
    source?: string
    updated_at?: string | null
    port_open?: boolean
    wait_timeout_sec?: number
  }
  account: IbkrAccount | null
  positions: IbkrPosition[]
  pending_orders?: IbkrPendingOrder[]
  exit_signals: string[]
  entry_candidates: IbkrCandidate[]
  universe_source: string
  error: string | null
}

type AlpacaCompareData = {
  account?: { portfolio_value?: number; total_pnl?: number; total_pnl_pct?: number }
  positions?: Array<{ symbol: string }>
  error?: string
}

type RunResult = { ok: boolean; stdout: string; stderr: string }

type PaperHealthOpenOrder = {
  order_id?: number | string
  symbol?: string
  side?: string
  action?: string
  type?: string
  order_type?: string
  stop_price?: number
  aux_price?: number
  qty?: number
  total_quantity?: number
  status?: string
}

type PaperTradingHealth = {
  ok: boolean
  exists?: boolean
  checked_at?: string
  error?: string | null
  problems?: string[]
  alpaca?: {
    ok?: boolean
    missing_stops?: string[]
    positions?: unknown[]
    stop_orders?: unknown[]
  }
  ibkr?: {
    ok?: boolean
    missing_stops?: string[]
    positions?: unknown[]
    open_orders?: PaperHealthOpenOrder[]
  }
  launchd_entry_lock?: Record<string, {
    loaded?: boolean
    max_positions_0?: boolean
    pyramid_disabled?: boolean
    auto_execute_disabled?: boolean
    trading_mode_paper?: boolean
  }>
  benchmarks?: Record<string, {
    close?: number | null
    change_pct_10d?: number | null
    ok?: boolean
  }>
}

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

// ── 포맷 헬퍼 ─────────────────────────────────────────────────────────────────

function fmt(n: number | undefined | null, decimals = 2): string {
  if (n === undefined || n === null || isNaN(n as number)) return '—'
  return (n as number).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function fmtPct(n: number | undefined | null, signed = true): string {
  if (n === undefined || n === null || isNaN(n as number)) return '—'
  const sign = signed ? ((n as number) >= 0 ? '+' : '') : ''
  return `${sign}${fmt(n, 2)}%`
}

function fmtUsd(n: number | undefined | null): string {
  if (n === undefined || n === null || isNaN(n as number)) return '—'
  const v = n as number
  const sign = v >= 0 ? '+$' : '-$'
  return `${sign}${fmt(Math.abs(v), 2)}`
}

function curSym(currency: string | undefined): string {
  switch (currency) {
    case 'KRW': return '₩'
    case 'JPY': return '¥'
    case 'TWD': return 'NT$'
    case 'HKD': return 'HK$'
    default: return '$'
  }
}

function fmtPrice(n: number | undefined | null, currency: string | undefined): string {
  if (n === undefined || n === null || isNaN(n as number)) return '—'
  const decimals = currency === 'KRW' || currency === 'JPY' ? 0 : 2
  return `${curSym(currency)}${fmt(n, decimals)}`
}

function relTime(iso: string): string {
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
    return new Date(iso).toLocaleDateString('ko-KR', {
      month: 'numeric', day: 'numeric',
    })
  } catch {
    return iso.slice(0, 10)
  }
}

const SYMBOL_NAMES: Record<string, string> = {
  NVDA: 'NVIDIA',
  AVGO: 'Broadcom',
  TSM:  'TSMC (ADR)',
  MU:   'Micron',
  ANET: 'Arista Networks',
  VRT:  'Vertiv',
  TER:  'Teradyne',
  SYM:  'Symbotic',
  ISRG: 'Intuitive Surgical',
  ROK:  'Rockwell Auto.',
  CEG:  'Constellation Energy',
  VST:  'Vistra',
  GEV:  'GE Vernova',
  PWR:  'Quanta Services',
}

function symName(symbol: string) {
  return SYMBOL_NAMES[symbol.toUpperCase()] || '—'
}

function gatewayStatusLabel(status: IbkrMonitorData['gateway_status'] | undefined, connected: boolean): string {
  if (connected) return '준비 완료'
  switch (status?.status) {
    case 'launching':
      return '실행 중'
    case 'waiting_for_2fa':
      return '2FA 대기'
    case 'ready':
      return '준비 완료'
    default:
      return '오프라인'
  }
}

function gatewayDotClass(status: IbkrMonitorData['gateway_status'] | undefined, connected: boolean): string {
  if (connected || status?.status === 'ready') return 'online'
  if (status?.status === 'launching' || status?.status === 'waiting_for_2fa') return 'warn'
  return 'offline'
}

// ── 위험 바 ───────────────────────────────────────────────────────────────────

function RiskBar({
  label,
  distancePct,
  referencePrice,
  currency,
}: {
  label: string
  distancePct: number | null
  referencePrice: number | null
  currency?: string
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
  const fillWidth = `${clampedPct}%`
  const fillClass = distancePct < 5 ? 'danger' : distancePct < 15 ? 'warn' : 'safe'

  return (
    <div className="risk-bar-row">
      <span className="risk-bar-label">{label}</span>
      <span className="risk-bar-ref">{fmtPrice(referencePrice, currency)}</span>
      <div className="risk-bar-track">
        <div className={`risk-bar-fill ${fillClass}`} style={{ width: fillWidth }} />
      </div>
      <span className={`risk-bar-pct ${fillClass}`}>{fmt(distancePct, 1)}% 여유</span>
    </div>
  )
}

// ── 액션 배지 ─────────────────────────────────────────────────────────────────

function ActionBadge({ action }: { action: IbkrPosition['action'] }) {
  if (action === 'HOLD') return <span className="position-action-badge action-hold">HOLD</span>
  if (action === 'STOP_LOSS') return <span className="position-action-badge action-exit-badge">손절 청산!</span>
  if (action === 'S1_EXIT') return <span className="position-action-badge action-warn-badge">S1 청산</span>
  if (action === 'S2_EXIT') return <span className="position-action-badge action-warn-badge">S2 청산</span>
  return <span className="position-action-badge action-hold">{action}</span>
}

// ── 신호 배지 ─────────────────────────────────────────────────────────────────

function SignalBadge({ signal, active }: { signal: string; active: string | null }) {
  if (signal === 'breakout_long') {
    return (
      <span className="signal-badge signal-long">
        ▲ {active === 'S2' ? 'S2 LONG' : 'S1 LONG'}
      </span>
    )
  }
  if (signal === 'neutral') return <span className="signal-badge signal-neutral">— 중립</span>
  if (signal === 'insufficient_data') return <span className="signal-badge signal-na">데이터 부족</span>
  if (signal === 'no_connection') return <span className="signal-badge signal-na">미연결</span>
  return <span className="signal-badge signal-na">{signal}</span>
}

// ── 브로커 비교 바 ───────────────────────────────────────────────────────────

function BrokerCompareBar({
  alpaca,
  ibkr,
}: {
  alpaca: AlpacaCompareData | null
  ibkr: IbkrMonitorData | null
}) {
  const alpacaPV    = alpaca?.account?.portfolio_value
  const alpacaPnl   = alpaca?.account?.total_pnl
  const alpacaPnlPct = alpaca?.account?.total_pnl_pct
  const alpacaPosCnt = alpaca?.positions?.length ?? 0

  const ibkrNav     = ibkr?.account?.nav
  const ibkrPnl     = ibkr?.account?.total_pnl
  const ibkrPnlPct  = ibkr?.account?.total_pnl_pct
  const ibkrPosCnt  = ibkr?.positions?.length ?? 0

  return (
    <div className="broker-compare-bar">
      {/* Alpaca */}
      <div className="broker-compare-card alpaca">
        <div className="broker-compare-head">
          <span className="broker-compare-name">Alpaca</span>
          <span className="broker-chip">모의투자</span>
        </div>
        <div className="broker-compare-metrics">
          <div className="broker-metric">
            <span className="broker-metric-label">포트폴리오</span>
            <span className="broker-metric-value">${fmt(alpacaPV, 0)}</span>
          </div>
          <div className="broker-metric">
            <span className="broker-metric-label">총 손익</span>
            <span className={`broker-metric-value ${(alpacaPnl ?? 0) >= 0 ? 'pnl-pos' : 'pnl-neg'}`}>
              {fmtUsd(alpacaPnl)}
              <small> ({fmtPct(alpacaPnlPct)})</small>
            </span>
          </div>
          <div className="broker-metric">
            <span className="broker-metric-label">포지션</span>
            <span className="broker-metric-value">{alpacaPosCnt}건</span>
          </div>
        </div>
        {!alpaca && <p className="broker-compare-loading">로딩 중…</p>}
      </div>

      {/* IBKR */}
      <div className="broker-compare-card ibkr">
        <div className="broker-compare-head">
          <span className="broker-compare-name">IBKR</span>
          <span className="broker-chip ibkr-chip">실전 동일 규칙</span>
        </div>
        {ibkr?.account?.account_id && (
          <div className="broker-account-line">
            <span className="broker-account-id">{ibkr.account.account_id}</span>
            <span className="broker-account-type">Paper Trading</span>
          </div>
        )}
        <div className="broker-compare-metrics">
          <div className="broker-metric">
            <span className="broker-metric-label">NAV</span>
            <span className="broker-metric-value">${fmt(ibkrNav, 0)}</span>
          </div>
          <div className="broker-metric">
            <span className="broker-metric-label">총 손익</span>
            <span className={`broker-metric-value ${(ibkrPnl ?? 0) >= 0 ? 'pnl-pos' : 'pnl-neg'}`}>
              {fmtUsd(ibkrPnl)}
              <small> ({fmtPct(ibkrPnlPct)})</small>
            </span>
          </div>
          <div className="broker-metric">
            <span className="broker-metric-label">포지션</span>
            <span className="broker-metric-value">{ibkrPosCnt}건</span>
          </div>
        </div>
        {!ibkr && <p className="broker-compare-loading">로딩 중…</p>}
      </div>
    </div>
  )
}

// ── 시스템 상태 행 ────────────────────────────────────────────────────────────

function SystemStatusRow({
  data,
  lastFetch,
}: {
  data: IbkrMonitorData | null
  lastFetch: string | null
}) {
  const connected = data?.gateway_connected ?? false
  const gatewayStatus = data?.gateway_status
  const acct      = data?.account
  const exitCnt   = data?.exit_signals?.length ?? 0
  const posCnt    = data?.positions?.length ?? 0
  const pendingCnt = data?.pending_orders?.length ?? 0
  const statusLabel = gatewayStatusLabel(gatewayStatus, connected)
  const dotClass = gatewayDotClass(gatewayStatus, connected)

  return (
    <div className={`ibkr-status-row ${exitCnt > 0 ? 'has-exit' : ''}`}>
      <span className={`gateway-dot ${dotClass}`} title={gatewayStatus?.message || (connected ? 'IB Gateway 연결됨' : '게이트웨이 오프라인')} />
      <span className="ibkr-status-item">
        <span className="ibkr-status-label">Gateway</span>
        <span className="ibkr-status-value">{statusLabel}</span>
      </span>
      {gatewayStatus?.message && (
        <>
          <span className="ibkr-status-sep">·</span>
          <span className="ibkr-status-item">
            <span className="ibkr-status-label">상태</span>
            <span className="ibkr-status-value">{gatewayStatus.message}</span>
          </span>
        </>
      )}
      {acct && (
        <>
          <span className="ibkr-status-sep">·</span>
          <span className="ibkr-status-item">
            <span className="ibkr-status-label">계좌</span>
            <span className="ibkr-status-value mono">{acct.account_id}</span>
          </span>
          <span className="ibkr-status-sep">·</span>
          <span className="ibkr-status-item">
            <span className="ibkr-status-label">NAV</span>
            <span className="ibkr-status-value">${fmt(acct.nav, 0)}</span>
          </span>
        </>
      )}
      <span className="ibkr-status-sep">·</span>
      <span className="ibkr-status-item">
        <span className="ibkr-status-label">포지션</span>
        <span className="ibkr-status-value">{posCnt}건</span>
      </span>
      {pendingCnt > 0 && (
        <>
          <span className="ibkr-status-sep">·</span>
          <span className="ibkr-status-item">
            <span className="ibkr-status-label">대기주문</span>
            <span className="ibkr-status-value">{pendingCnt}건</span>
          </span>
        </>
      )}
      {exitCnt > 0 && (
        <>
          <span className="ibkr-status-sep">·</span>
          <span className="ibkr-exit-alert">⚠ EXIT 신호 {exitCnt}건</span>
        </>
      )}
      <span className="ibkr-status-spacer" />
      {lastFetch && (
        <span className="ibkr-status-meta">
          갱신: {lastFetch}
          {data?.ts && ` (스크립트: ${relTime(data.ts)})`}
        </span>
      )}
    </div>
  )
}

function boolLabel(v: boolean | undefined): string {
  return v ? 'OK' : '확인 필요'
}

function healthStopLabel(order: PaperHealthOpenOrder): string {
  const stop = order.stop_price ?? order.aux_price
  const qty = order.qty ?? order.total_quantity
  const type = order.order_type ?? order.type ?? 'STP'
  return `${order.symbol ?? '—'} ${order.side ?? order.action ?? 'SELL'} ${type} ${qty ?? '—'} @ ${stop ?? '—'}`
}

function PaperTradingHealthCard({
  health,
  loading,
  error,
}: {
  health: PaperTradingHealth | null
  loading: boolean
  error: string | null
}) {
  const problems = health?.problems ?? []
  const ok = Boolean(health?.ok)
  const alpacaMissing = health?.alpaca?.missing_stops ?? []
  const ibkrMissing = health?.ibkr?.missing_stops ?? []
  const locks = health?.launchd_entry_lock ?? {}
  const ibkrStops = (health?.ibkr?.open_orders ?? []).filter(o => {
    const side = String(o.side ?? o.action ?? '').toLowerCase()
    const type = String(o.order_type ?? o.type ?? '').toLowerCase()
    return side === 'sell' && type.includes('stp')
  })

  return (
    <article className={`paper-health-card ${ok ? 'health-ok' : 'health-warn'}`}>
      <div className="paper-health-head">
        <div>
          <h3>Paper Trading Health</h3>
          <p>자동 신규 진입 차단, 상주손절, broker/state 일치 상태를 표시합니다.</p>
        </div>
        <span className={`paper-health-badge ${ok ? 'ok' : 'warn'}`}>
          {loading ? '확인 중' : ok ? '정상' : '점검 필요'}
        </span>
      </div>

      {error && <p className="paper-health-error">로드 오류: {error}</p>}
      {!loading && health?.exists === false && (
        <p className="paper-health-error">health report가 아직 생성되지 않았습니다.</p>
      )}
      {!loading && health?.error && (
        <p className="paper-health-error">{health.error}</p>
      )}

      <div className="paper-health-grid">
        <div className="paper-health-metric">
          <span className="paper-health-label">Alpaca stop</span>
          <strong>{boolLabel(health?.alpaca?.ok)}</strong>
          <small>{health?.alpaca?.positions?.length ?? 0} positions · {health?.alpaca?.stop_orders?.length ?? 0} stops</small>
        </div>
        <div className="paper-health-metric">
          <span className="paper-health-label">IBKR stop</span>
          <strong>{boolLabel(health?.ibkr?.ok)}</strong>
          <small>{health?.ibkr?.positions?.length ?? 0} positions · {ibkrStops.length} stops</small>
        </div>
        <div className="paper-health-metric">
          <span className="paper-health-label">신규 진입</span>
          <strong>중지</strong>
          <small>
            Alpaca {boolLabel(locks.alpaca?.max_positions_0 && locks.alpaca?.pyramid_disabled)}
            {' · '}
            IBKR {boolLabel(locks.ibkr?.max_positions_0 && locks.ibkr?.pyramid_disabled)}
          </small>
        </div>
        <div className="paper-health-metric">
          <span className="paper-health-label">최근 점검</span>
          <strong>{health?.checked_at ? relTime(health.checked_at) : '—'}</strong>
          <small>{health?.checked_at ?? 'no timestamp'}</small>
        </div>
      </div>

      {(problems.length > 0 || alpacaMissing.length > 0 || ibkrMissing.length > 0) && (
        <div className="paper-health-alerts">
          {[...problems, ...alpacaMissing.map(s => `alpaca_missing_stop:${s}`), ...ibkrMissing.map(s => `ibkr_missing_stop:${s}`)].map(item => (
            <span key={item}>{item}</span>
          ))}
        </div>
      )}

      {ibkrStops.length > 0 && (
        <div className="paper-health-stops">
          {ibkrStops.slice(0, 3).map(o => (
            <span key={`${o.order_id ?? o.symbol}-${o.stop_price ?? o.aux_price}`}>
              {healthStopLabel(o)}
            </span>
          ))}
        </div>
      )}
    </article>
  )
}

// ── 포지션 카드 ───────────────────────────────────────────────────────────────

function PositionCard({ pos }: { pos: IbkrPosition }) {
  const isExit = pos.action !== 'HOLD'
  const pnlPos = (pos.unrealized_pnl ?? 0) >= 0
  const currency = pos.currency || 'USD'
  const primaryExch = pos.primary_exchange || pos.exchange || 'SMART'
  const exchLabel = primaryExch !== 'SMART' ? primaryExch : pos.exchange

  return (
    <article className={`position-risk-card ${isExit ? 'action-exit' : ''} ${pos.resident_stop_missing ? 'stop-missing' : ''}`}>
      {/* 헤더 */}
      <div className="prcard-header">
        <div className="prcard-symbol">
          <strong>{pos.symbol}</strong>
          <small>{symName(pos.symbol)}</small>
        </div>
        <div className="prcard-badges">
          <ActionBadge action={pos.action} />
          {pos.adopted && <span className="position-action-badge action-adopted-badge">입양</span>}
        </div>
      </div>

      {/* resident_stop_missing 경고 */}
      {pos.resident_stop_missing && (
        <div className="stop-missing-alert">
          ⚠ 상주손절 미발행 — 다음 run에서 재시도 또는 즉시 청산 대기 중
        </div>
      )}

      {/* 메타 */}
      <div className="prcard-meta">
        {pos.qty}주 · {exchLabel}
        {currency !== 'USD' && <span className="currency-tag"> · {currency}</span>}
        {' · 진입 '}{formatEntryDate(pos.entry_ts)}
      </div>

      {/* 가격 */}
      <div className="prcard-prices">
        <div className="prcard-price-main">
          {pos.current_price !== null ? fmtPrice(pos.current_price, currency) : '—'}
        </div>
        <div className="prcard-price-entry">
          진입 {fmtPrice(pos.entry_price, currency)}
        </div>
        <div className={`prcard-pnl ${pnlPos ? 'pnl-pos' : 'pnl-neg'}`}>
          {fmtUsd(pos.unrealized_pnl)}
          <span> ({fmtPct(pos.unrealized_pnl_pct)})</span>
        </div>
      </div>

      {/* 위험 지표 */}
      <div className="prcard-risk-section">
        <p className="prcard-risk-title">위험 지표 <small>(낮을수록 청산 임박)</small></p>
        <RiskBar label="손절가" distancePct={pos.stop_distance_pct} referencePrice={pos.stop_loss} currency={currency} />
        <RiskBar label="S1 청산" distancePct={pos.s1_distance_pct} referencePrice={pos.s1_low} currency={currency} />
        <RiskBar label="S2 청산" distancePct={pos.s2_distance_pct} referencePrice={pos.s2_low} currency={currency} />
      </div>

      {/* 푸터 */}
      <div className="prcard-footer">
        <span>ATR {fmtPrice(pos.atr, currency)}</span>
        {pos.market_value !== null && (
          <span>시장가치 ${fmt(pos.market_value, 0)}</span>
        )}
      </div>
    </article>
  )
}

// ── 대기 주문(미체결) 카드 ────────────────────────────────────────────────────

function PendingStatusBadge({ status }: { status: string }) {
  const s = (status || '').toLowerCase()
  const label =
    s === 'presubmitted' ? 'PreSubmitted'
    : s === 'pendingsubmit' ? 'PendingSubmit'
    : s === 'submitted' ? 'Submitted'
    : status || '대기'
  return <span className="position-action-badge action-pending-badge">{label}</span>
}

function PendingOrderCard({ po }: { po: IbkrPendingOrder }) {
  const stale = (po.age_hours ?? 0) >= 24
  const gap = po.gap_to_entry_pct
  return (
    <article className={`position-risk-card pending-order-card ${stale ? 'pending-stale' : ''}`}>
      {/* 헤더 */}
      <div className="prcard-header">
        <div className="prcard-symbol">
          <strong>{po.symbol}</strong>
          <small>{symName(po.symbol)}</small>
        </div>
        <PendingStatusBadge status={po.status} />
      </div>

      {/* 메타 */}
      <div className="prcard-meta">
        {po.qty}주 · {po.exchange} · 주문 {po.order_id ?? '—'}
        {po.age_hours !== null && po.age_hours !== undefined && ` · ${fmt(po.age_hours, 1)}h 경과`}
      </div>

      {/* 가격 */}
      <div className="prcard-prices">
        <div className="prcard-price-main">
          {po.current_price !== null ? fmtPrice(po.current_price, po.currency) : '대기 중'}
        </div>
        <div className="prcard-price-entry">
          진입기준 {fmtPrice(po.entry_price, po.currency)}
        </div>
        {gap !== null && gap !== undefined && (
          <div className={`prcard-pnl ${gap >= 0 ? 'pnl-pos' : 'pnl-neg'}`}>
            <span>현재가 대비 {fmtPct(gap)}</span>
          </div>
        )}
      </div>

      {/* 푸터 */}
      <div className="prcard-footer">
        <span>손절 {fmtPrice(po.stop_loss, po.currency)}</span>
        {po.atr !== null && po.atr !== undefined && <span>ATR {fmt(po.atr)}</span>}
      </div>

      {stale && (
        <div className="pending-stale-note">
          ⚠ 24시간+ 미체결 — IB Gateway 연결/주문 상태를 확인하세요
        </div>
      )}
    </article>
  )
}

// ── 진입 신호 스캐너 ──────────────────────────────────────────────────────────

function EntrySignalScanner({ candidates }: { candidates: IbkrCandidate[] }) {
  if (candidates.length === 0) return null

  const breakouts = candidates.filter(c => c.signal === 'breakout_long')
  const others    = candidates.filter(c => c.signal !== 'breakout_long')
  const sorted    = [...breakouts, ...others]

  return (
    <article className="panel alpaca-full entry-scanner-section">
      <div className="panel-head">
        <h3>진입 신호 스캐너</h3>
        <span className="data-meta">
          Turtle Trading S1(20일)/S2(55일) 브레이크아웃 기준
          {breakouts.length > 0 && (
            <span className="entry-scanner-active"> · 활성 신호 {breakouts.length}건</span>
          )}
        </span>
        <span className="term-note">
          현재가가 20일(S1) 또는 55일(S2) 최고가를 돌파하면 매수 신호입니다.
          이미 보유 중인 종목은 '보유 중'으로 표시됩니다.
        </span>
      </div>

      {breakouts.length > 0 && (
        <div className="entry-breakout-bar">
          <span className="data-label-inline">활성 신호:</span>
          {breakouts.map(c => (
            <span key={c.symbol} className="active-signal-chip">
              <strong>{c.symbol}</strong>
              <SignalBadge signal={c.signal} active={c.active_signal} />
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
            {sorted.map(c => (
              <tr
                key={c.symbol}
                className={
                  c.signal === 'breakout_long'
                    ? 'row-highlight'
                    : c.in_position
                    ? 'row-in-position'
                    : ''
                }
              >
                <td>
                  <span className="symbol-cell">
                    <strong>{c.symbol}</strong>
                    <small>{symName(c.symbol)}</small>
                  </span>
                </td>
                <td className="num">{c.current_price !== null ? `$${fmt(c.current_price)}` : '—'}</td>
                <td className="num">{c.s1_high !== null ? `$${fmt(c.s1_high)}` : '—'}</td>
                <td className="num">{c.s2_high !== null ? `$${fmt(c.s2_high)}` : '—'}</td>
                <td className={`num ${c.gap_pct !== null && c.gap_pct > 0 ? 'pnl-pos' : c.gap_pct !== null && c.gap_pct < 0 ? 'pnl-neg' : ''}`}>
                  {c.gap_pct !== null ? `${c.gap_pct >= 0 ? '+' : ''}${fmt(c.gap_pct, 1)}%` : '—'}
                </td>
                <td className="num">{c.atr !== null ? fmt(c.atr, 2) : '—'}</td>
                <td><SignalBadge signal={c.signal} active={c.active_signal} /></td>
                <td>
                  {c.in_position
                    ? <span className="in-pos-chip">보유 중</span>
                    : <span className="data-meta">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────

export function IbkrTurtleMonitor({ apiBase, authHeaders }: Props) {
  const [data, setData]           = useState<IbkrMonitorData | null>(null)
  const [alpacaData, setAlpacaData] = useState<AlpacaCompareData | null>(null)
  const [health, setHealth]       = useState<PaperTradingHealth | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<string | null>(null)
  const [running, setRunning]     = useState(false)
  const [runResult, setRunResult] = useState<RunResult | null>(null)
  const [confirmExecute, setConfirmExecute] = useState(false)

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${apiBase}/api/ibkr/monitor`, {
          headers: authHeaders(),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = (await res.json()) as IbkrMonitorData
        setData(json)
        setLastFetch(new Date().toLocaleTimeString('ko-KR'))
      } catch (e) {
        setError(e instanceof Error ? e.message : '로드 실패')
      } finally {
        setLoading(false)
      }
    },
    [apiBase, authHeaders],
  )

  const loadAlpaca = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/paper-trading/dashboard`, {
        headers: authHeaders(),
      })
      if (!res.ok) return
      const json = (await res.json()) as AlpacaCompareData
      setAlpacaData(json)
    } catch {
      // silent — compare bar는 부가 정보
    }
  }, [apiBase, authHeaders])

  const loadHealth = useCallback(async () => {
    setHealthError(null)
    try {
      const res = await fetch(`${apiBase}/api/paper-trading/health`, {
        headers: authHeaders(),
      })
      const json = (await res.json()) as PaperTradingHealth
      if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`)
      setHealth(json)
    } catch (e) {
      setHealthError(e instanceof Error ? e.message : 'health 로드 실패')
    } finally {
      setHealthLoading(false)
    }
  }, [apiBase, authHeaders])

  const runMonitor = useCallback(
    async (mode: 'scan' | 'execute') => {
      setRunning(true)
      setRunResult(null)
      setConfirmExecute(false)
      try {
        const endpoint = mode === 'execute' ? 'execute' : 'scan'
        const res = await fetch(`${apiBase}/api/ibkr/monitor/${endpoint}`, {
          method: 'POST',
          headers: authHeaders(),
        })
        const json = (await res.json()) as RunResult
        setRunResult(json)
        if (json.ok) void load(true)
      } catch (e) {
        setRunResult({
          ok: false, stdout: '',
          stderr: e instanceof Error ? e.message : '실행 실패',
        })
      } finally {
        setRunning(false)
      }
    },
    [apiBase, authHeaders, load],
  )

  useEffect(() => {
    const t = setTimeout(() => void load(), 0)
    const iv = setInterval(() => void load(true), 5 * 60 * 1000)
    return () => { clearInterval(iv); clearTimeout(t) }
  }, [load])

  useEffect(() => {
    void loadAlpaca()
    // Alpaca 데이터는 5분마다 갱신
    const iv = setInterval(() => void loadAlpaca(), 5 * 60 * 1000)
    return () => clearInterval(iv)
  }, [loadAlpaca])

  useEffect(() => {
    void loadHealth()
    const iv = setInterval(() => void loadHealth(), 5 * 60 * 1000)
    return () => clearInterval(iv)
  }, [loadHealth])

  // ── 로딩 ───────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <section className="ibkr-section">
        <div className="section-head">
          <h2>IBKR Turtle Monitor</h2>
        </div>
        <article className="panel">
          <p className="data-meta loading-pulse">IBKR 포지션 및 신호를 불러오는 중…</p>
        </article>
      </section>
    )
  }

  // ── 오류 ───────────────────────────────────────────────────────────────────
  if (error && !data) {
    return (
      <section className="ibkr-section">
        <div className="section-head">
          <h2>IBKR Turtle Monitor</h2>
        </div>
        <article className="panel">
          <p className="data-warn">연결 오류: {error}</p>
          <button type="button" className="btn-secondary" onClick={() => void load()}>재시도</button>
        </article>
      </section>
    )
  }

  const positions        = data?.positions ?? []
  const pendingOrders    = data?.pending_orders ?? []
  const candidates       = data?.entry_candidates ?? []
  const exitSignals      = data?.exit_signals ?? []
  const hasExitSignals   = exitSignals.length > 0
  const gatewayConnected = data?.gateway_connected ?? false
  const gatewayStatus = data?.gateway_status
  const gatewayStatusCode = gatewayStatus?.status ?? (gatewayConnected ? 'ready' : 'offline')

  return (
    <section className="ibkr-section">
      {/* ── 브로커 비교 바 ── */}
      <BrokerCompareBar alpaca={alpacaData} ibkr={data} />

      {/* ── 헤더 ── */}
      <div className="section-head">
        <div>
          <h2>IBKR Turtle Monitor</h2>
          {data?.account?.account_id && (
            <p className="ibkr-section-acct">
              계좌 <span className="mono">{data.account.account_id}</span> · Paper Trading · IB Gateway 4002
            </p>
          )}
        </div>
        <p>Turtle Trading 5원칙을 기반으로 IBKR 포지션을 실시간 점검합니다.</p>
        <p className="term-note">
          손절가(진입가 − 2ATR), S1 청산(10일 저가), S2 청산(20일 저가) 기준을 자동 계산합니다.
          Universe 소스: <code>{data?.universe_source ?? '—'}</code>
        </p>
        <div className="section-head-actions">
          <span className="data-meta">{lastFetch ? `마지막 갱신: ${lastFetch}` : ''}</span>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => void load()}
            disabled={running}
          >
            새로고침
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => void runMonitor('scan')}
            disabled={running}
            title="신호 스캔 (주문 없음)"
          >
            {running ? '실행 중…' : '신호 점검'}
          </button>
          {!confirmExecute ? (
            <button
              type="button"
              className="btn-execute btn-sm"
              onClick={() => setConfirmExecute(true)}
              disabled={running || !hasExitSignals}
              title={hasExitSignals ? `EXIT 신호: ${exitSignals.join(', ')}` : '현재 EXIT 신호 없음'}
            >
              청산 실행
            </button>
          ) : (
            <span className="ibkr-confirm-row">
              <span className="ibkr-confirm-label">
                {exitSignals.join(', ')} 청산?
              </span>
              <button
                type="button"
                className="btn-danger btn-sm"
                onClick={() => void runMonitor('execute')}
                disabled={running}
              >
                확인 실행
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => setConfirmExecute(false)}
              >
                취소
              </button>
            </span>
          )}
        </div>
      </div>

      {/* ── 시스템 상태 ── */}
      <SystemStatusRow data={data} lastFetch={lastFetch} />
      <PaperTradingHealthCard health={health} loading={healthLoading} error={healthError} />

      {/* ── 실행 결과 ── */}
      {runResult && (
        <div className={`run-result-box ${runResult.ok ? 'run-ok' : 'run-err'}`}>
          <div className="run-result-head">
            <span>{runResult.ok ? '✓ 실행 완료' : '✗ 실행 실패'}</span>
            <button
              type="button"
              className="btn-ghost btn-xs"
              onClick={() => setRunResult(null)}
            >
              ✕
            </button>
          </div>
          {runResult.stdout && <pre className="run-output">{runResult.stdout}</pre>}
          {runResult.stderr && <pre className="run-output run-stderr">{runResult.stderr}</pre>}
        </div>
      )}

      {/* ── 오프라인 경고 ── */}
      {!gatewayConnected && (
        <div className="ibkr-offline-banner">
          <span className={`gateway-dot ${gatewayDotClass(gatewayStatus, gatewayConnected)}`} />
          {gatewayStatusCode === 'launching' && 'IB Gateway 실행 중 — Mac Mini에서 앱이 뜨는지 확인하세요. 포트가 열리면 자동으로 다음 스캔이 진행됩니다.'}
          {gatewayStatusCode === 'waiting_for_2fa' && 'IB Gateway 2FA 승인 대기 중 — Mac Mini 로그인 창 비밀번호 입력 후 IBKR Mobile 2FA 승인을 완료하면 자동 재시도됩니다.'}
          {gatewayStatusCode === 'offline' && 'IB Gateway 오프라인 — 포지션은 상태 파일 기준으로 표시됩니다. 현재가 및 신호는 연결 후 갱신됩니다.'}
          {gatewayStatusCode === 'ready' && 'IB Gateway 상태는 준비 완료로 기록됐지만 현재 모니터 캐시 연결은 아직 갱신 전입니다. 잠시 후 다시 새로고침하세요.'}
        </div>
      )}

      {/* ── 포지션 카드 그리드 ── */}
      {hasExitSignals && (
        <div className="ibkr-exit-banner">
          <span>⚠ EXIT 신호 발생: </span>
          {exitSignals.map(s => (
            <strong key={s}>{s} </strong>
          ))}
          <span>— "청산 실행" 버튼으로 GTC 매도 주문을 발행하세요.</span>
        </div>
      )}

      {positions.length > 0 ? (
        <div>
          <div className="panel-head" style={{ marginBottom: '0.5rem' }}>
            <h3>현재 포지션</h3>
            <span className="data-meta">{positions.length}건 보유 중</span>
          </div>
          <div className="position-cards-grid">
            {positions.map(pos => (
              <PositionCard key={pos.symbol} pos={pos} />
            ))}
          </div>
        </div>
      ) : (
        <article className="panel">
          <div className="panel-head"><h3>현재 포지션</h3></div>
          <p className="data-meta">현재 IBKR에 보유 중인 포지션이 없습니다.</p>
          <p className="term-note">신호 스캐너에서 진입 기회를 확인하세요.</p>
        </article>
      )}

      {/* ── 대기 주문(미체결) ── */}
      {pendingOrders.length > 0 && (
        <div className="ibkr-pending-section">
          <div className="panel-head" style={{ marginBottom: '0.5rem' }}>
            <h3>대기 주문 (미체결)</h3>
            <span className="data-meta">
              {pendingOrders.length}건 · 진입 주문이 아직 체결되지 않았습니다
            </span>
            <span className="term-note">
              브로커에 제출됐으나 아직 체결 전(PreSubmitted / PendingSubmit / Submitted)인 진입 주문입니다.
              체결되면 '현재 포지션'으로 이동합니다.
            </span>
          </div>
          <div className="position-cards-grid">
            {pendingOrders.map(po => (
              <PendingOrderCard key={`${po.symbol}-${po.order_id ?? 'na'}`} po={po} />
            ))}
          </div>
        </div>
      )}

      {/* ── 진입 신호 스캐너 ── */}
      <EntrySignalScanner candidates={candidates} />
    </section>
  )
}
