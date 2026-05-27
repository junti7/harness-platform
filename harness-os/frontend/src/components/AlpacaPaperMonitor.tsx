import { useCallback, useEffect, useRef, useState } from 'react'
import type { AlpacaPaperDashboard, AlpacaPosition, AlpacaOrder, DropAlert } from './types'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

const SYMBOL_NAMES: Record<string, string> = {
  GOOG: 'Google',
  GOOGL: 'Google',
  GOOP: 'Google',
  NVDA: 'NVIDIA',
  TER: 'Teradyne',
  TSLA: 'Tesla',
  SMH: '반도체 ETF',
  SOXX: '반도체 ETF',
  BOTZ: '로보틱스 ETF',
  PLTR: 'Palantir',
  ROBO: '로봇 ETF',
  SPY: 'S&P 500 ETF',
}

function symbolDisplay(symbol?: string | null) {
  const code = String(symbol || '').trim().toUpperCase()
  return { code: code || '—', name: SYMBOL_NAMES[code] || '종목명 확인 필요' }
}

function SymbolCell({ symbol }: { symbol?: string | null }) {
  const item = symbolDisplay(symbol)
  return (
    <span className="symbol-cell">
      <strong>{item.code}</strong>
      <small>{item.name}</small>
    </span>
  )
}

function fmt(n: number | undefined, decimals = 2): string {
  if (n === undefined || n === null || isNaN(n)) return '—'
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function fmtPct(n: number | undefined): string {
  if (n === undefined || n === null || isNaN(n)) return '—'
  const sign = n >= 0 ? '+' : ''
  return `${sign}${fmt(n, 2)}%`
}

function fmtUsd(n: number | undefined): string {
  if (n === undefined || n === null || isNaN(n)) return '—'
  const sign = n >= 0 ? '+$' : '-$'
  return `${sign}${fmt(Math.abs(n), 2)}`
}

type ChartPoint = { date: string; value: number; pnl_pct: number }

function PortfolioChart({ data }: { data: ChartPoint[] }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<{ x: number; y: number; idx: number } | null>(null)

  if (data.length < 2) return null

  const W = 520, H = 120
  const ml = 72, mr = 16, mt = 12, mb = 28  // margins
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
  const lineColor = isUp ? '#ef4444' : '#3b82f6' // 한국 증시: 상승=빨강, 하락=파랑

  // Y-axis ticks (3 levels)
  const yTicks = [yMin + yRange * 0.05, yMin + yRange * 0.5, yMin + yRange * 0.95]

  // X-axis ticks: first, ~middle, last
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
        <linearGradient id="pGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.25" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* Y-axis grid + labels */}
      {yTicks.map((v, i) => (
        <g key={i}>
          <line x1={ml} y1={py(v)} x2={ml + cw} y2={py(v)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
          <text x={ml - 6} y={py(v) + 4} textAnchor="end" className="chart-axis-label">
            ${(v / 1000).toFixed(1)}k
          </text>
        </g>
      ))}

      {/* X-axis labels */}
      {xIdxs.map(i => (
        <text key={i} x={px(i)} y={H - 6} textAnchor="middle" className="chart-axis-label">
          {data[i].date}
        </text>
      ))}

      {/* Area fill */}
      <polygon points={area} fill="url(#pGrad)" />

      {/* Line */}
      <polyline points={pts} fill="none" stroke={lineColor} strokeWidth="1.5" strokeLinejoin="round" />

      {/* Hover crosshair */}
      {hover && (
        <>
          <line x1={hover.x} y1={mt} x2={hover.x} y2={mt + ch} stroke="rgba(255,255,255,0.2)" strokeWidth="1" strokeDasharray="3,3" />
          <circle cx={hover.x} cy={hover.y} r="4" fill={lineColor} stroke="#1a1f2e" strokeWidth="2" />
          {/* Tooltip box */}
          <rect x={tooltipX} y={tooltipY} width="118" height="44" rx="5"
            fill="#1e2433" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
          <text x={tooltipX + 8} y={tooltipY + 14} className="chart-tooltip-label">{hPoint?.date}</text>
          <text x={tooltipX + 8} y={tooltipY + 28} className="chart-tooltip-value">
            ${hPoint ? (hPoint.value / 1000).toFixed(2) : ''}k
          </text>
          <text x={tooltipX + 80} y={tooltipY + 28} className={`chart-tooltip-pnl ${(hPoint?.pnl_pct ?? 0) >= 0 ? 'pnl-up' : 'pnl-down'}`}>
            {hPoint ? `${hPoint.pnl_pct >= 0 ? '+' : ''}${hPoint.pnl_pct.toFixed(2)}%` : ''}
          </text>
        </>
      )}
    </svg>
  )
}

function SignalBadge({ signal }: { signal: string }) {
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

function PnlCell({ v }: { v: number | undefined }) {
  if (v === undefined || v === null) return <td className="num">—</td>
  const cls = v > 0 ? 'pnl-pos' : v < 0 ? 'pnl-neg' : ''
  return <td className={`num ${cls}`}>{fmtPct(v)}</td>
}

function KpiRow({
  label, value, pass, note,
}: { label: string; value: string; pass?: boolean; note?: string }) {
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

const INITIAL_CAPITAL = 100_000

// ── 급락 브리핑 패널 ────────────────────────────────────────────────────────

function triggerLabel(trigger: DropAlert['trigger']) {
  return trigger === 'rapid' ? '급속 낙폭' : '누적 낙폭'
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

function DropAlertPanel({
  alerts,
  onAck,
  threshold,
}: {
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
          급락 브리핑
        </h3>
        <span className="data-meta">
          임계값: 단기 {threshold}% | 진입가 대비 -5% | 60초 폴링 · 30분 쿨다운
        </span>
        <span className="term-note">OpenClaw가 급락 감지 시 자동 수집 후 Claude가 원인을 분석하고 CEO에게 Slack 긴급 보고합니다.</span>
      </div>

      {alerts.length === 0 ? (
        <p className="drop-alert-empty">현재 감지된 급락 이벤트 없음 — 실시간 모니터링 중</p>
      ) : (
        <div className="drop-alert-list">
          {alerts.map(a => (
            <div
              key={a.id}
              className={`drop-alert-card ${a.acknowledged ? 'drop-alert-acked' : 'drop-alert-unacked'}`}
            >
              <div className="drop-alert-header">
                <span className="drop-alert-symbol">{a.symbol}</span>
                <span className={`drop-alert-pct ${a.drop_pct <= -5 ? 'severe' : ''}`}>
                  {a.drop_pct.toFixed(1)}%
                </span>
                <span className="signal-badge signal-short">{triggerLabel(a.trigger)}</span>
                <span className="drop-alert-time">{relativeTime(a.detected_at)}</span>
                {!a.acknowledged && (
                  <button className="drop-alert-ack-btn" onClick={() => onAck(a.id)}>
                    확인
                  </button>
                )}
              </div>
              <div className="drop-alert-price">
                ${a.prev_price.toFixed(2)} → ${a.current_price.toFixed(2)}
              </div>
              {a.news_titles.length > 0 && (
                <ul className="drop-alert-news">
                  {a.news_titles.slice(0, 3).map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
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

// ─────────────────────────────────────────────────────────────────────────────

type RunResult = { ok: boolean; stdout: string; stderr: string }

export function AlpacaPaperMonitor({ apiBase, authHeaders }: Props) {
  const [data, setData] = useState<AlpacaPaperDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState<RunResult | null>(null)
  const [dropAlerts, setDropAlerts] = useState<DropAlert[]>([])

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${apiBase}/api/paper-trading/dashboard`, {
          headers: authHeaders(),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = (await res.json()) as AlpacaPaperDashboard
        if (json.error && !json.account) throw new Error(json.error)
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

  const runTrader = useCallback(
    async (execute: boolean) => {
      setRunning(true)
      setRunResult(null)
      try {
        const endpoint = execute ? 'execute' : 'run'
        const res = await fetch(`${apiBase}/api/paper-trading/${endpoint}`, {
          method: 'POST',
          headers: authHeaders(),
        })
        const json = (await res.json()) as RunResult
        setRunResult(json)
        if (json.ok) void load(true)
      } catch (e) {
        setRunResult({ ok: false, stdout: '', stderr: e instanceof Error ? e.message : '실행 실패' })
      } finally {
        setRunning(false)
      }
    },
    [apiBase, authHeaders, load],
  )

  const loadDropAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/paper-trading/drop-alerts`, { headers: authHeaders() })
      if (!res.ok) return
      const json = await res.json() as { ok: boolean; alerts: DropAlert[] }
      if (json.ok) setDropAlerts(json.alerts)
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

  useEffect(() => {
    const initial = setTimeout(() => void load(), 0)
    const iv = setInterval(() => void load(true), 5 * 60 * 1000)
    return () => {
      clearInterval(iv)
      window.clearTimeout(initial)
    }
  }, [load])

  useEffect(() => {
    void loadDropAlerts()
    const iv = setInterval(() => void loadDropAlerts(), 30 * 1000)
    return () => clearInterval(iv)
  }, [loadDropAlerts])

  if (loading) {
    return (
      <article className="panel alpaca-panel">
        <div className="panel-head"><h3>모의 투자 점검</h3></div>
        <p className="data-meta loading-pulse">가상 투자 계좌 데이터를 불러오는 중…</p>
      </article>
    )
  }

  if (error || !data) {
    return (
      <article className="panel alpaca-panel">
        <div className="panel-head"><h3>모의 투자 점검</h3></div>
        <p className="data-warn">연결 오류: {error ?? '알 수 없는 오류'}</p>
        <button type="button" className="btn-secondary" onClick={() => void load()}>재시도</button>
      </article>
    )
  }

  const { account, positions, signals, active_signals, orders, ar018_kpi } = data
  const hasAcctError = !account.ok

  const maxLossPass = ar018_kpi.max_loss_pass
  const totalPnl = account.total_pnl ?? 0
  const totalPnlPct = account.total_pnl_pct ?? 0

  // Chart spark: last 30 points — always show, last point = current portfolio value
  const chartData = (() => {
    const base = data.history.base ?? INITIAL_CAPITAL
    const current = account.portfolio_value ?? base
    const pct = base > 0 ? ((current - base) / base) * 100 : 0
    const today = new Date().toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }).replace('. ', '/').replace('.', '')
    const raw = data.history.chart.filter(d => d.value > 0).slice(-30)
    if (raw.length >= 2) {
      // Pin last point to live portfolio value
      const updated = [...raw.slice(0, -1), { ...raw[raw.length - 1], value: current, pnl_pct: pct }]
      return updated
    }
    // Fallback: synthesise start→current
    return [
      { date: 'start', value: base, pnl_pct: 0 },
      { date: today, value: current, pnl_pct: pct },
    ]
  })()

  const validPositions = positions.filter((p): p is AlpacaPosition & { symbol: string } => !p.error && !!p.symbol)
  const validSignals = signals.filter(s => !s.error)

  return (
    <section className="alpaca-section">
      {/* ── 헤더 ── */}
      <div className="section-head">
        <h2>모의 투자 점검</h2>
        <p>실제 돈을 넣기 전, 가상 계좌로 투자 규칙과 손실 제한을 확인합니다.</p>
        <p className="term-note">Alpaca는 가상 투자 계좌 서비스입니다. Paper trading은 실제 돈 없이 해보는 모의 투자입니다.</p>
        <div className="section-head-actions">
          <span className="data-meta">{lastFetch ? `마지막 갱신: ${lastFetch}` : ''}</span>
          <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={running}>새로고침</button>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => void runTrader(false)}
            disabled={running}
            title="신호 스캔 + 포지션 관리 (주문 없음)"
          >
            {running ? '실행 중…' : '주문 없이 점검'}
          </button>
          <button
            type="button"
            className="btn-execute btn-sm"
            onClick={() => void runTrader(true)}
            disabled={running}
            title="Turtle 신호 시 실제 Paper 주문 실행"
          >
            {running ? '실행 중…' : '가상 주문 실행'}
          </button>
        </div>
      </div>

      {/* ── 실행 결과 ── */}
      {runResult && (
        <div className={`run-result-box ${runResult.ok ? 'run-ok' : 'run-err'}`}>
          <div className="run-result-head">
            <span>{runResult.ok ? '✓ 실행 완료' : '✗ 실행 실패'}</span>
            <button type="button" className="btn-ghost btn-xs" onClick={() => setRunResult(null)}>✕</button>
          </div>
          {runResult.stdout && <pre className="run-output">{runResult.stdout}</pre>}
          {runResult.stderr && <pre className="run-output run-stderr">{runResult.stderr}</pre>}
        </div>
      )}

      {/* ── ROW 1: 계좌 요약 + 통과 기준 ── */}
      <div className="alpaca-grid-2">

        {/* 계좌 요약 */}
        <article className="panel">
          <div className="panel-head"><h3>계좌 요약</h3></div>
          {hasAcctError ? (
            <p className="data-warn">계좌 조회 실패: {account.error}</p>
          ) : (
            <>
              <div className="split-2">
                <div>
                  <p className="data-label">포트폴리오 가치</p>
                  <p className="data-value">${fmt(account.portfolio_value)}</p>
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
                  <p className="data-value-sm">${fmt(account.cash)}</p>
                </div>
                <div>
                  <p className="data-label">매수 가능</p>
                  <p className="data-value-sm">${fmt(account.buying_power)}</p>
                </div>
                <div>
                  <p className="data-label">당일 매매</p>
                  <p className="data-value-sm">{account.day_trade_count ?? 0}회</p>
                </div>
              </div>

              {/* 포트폴리오 차트 */}
              <div className="alpaca-spark">
                <p className="data-label">포트폴리오 추이 (30D)</p>
                <PortfolioChart data={chartData} />
              </div>
            </>
          )}
        </article>

        {/* 통과 기준 */}
        <article className="panel">
          <div className="panel-head">
            <h3>실전 투자 전 통과 기준</h3>
            <span className="data-meta">8주 모의 투자 기간에 반드시 확인할 조건</span>
          </div>
          <ul className="kpi-list">
            <KpiRow
              label="누적 수익률"
              value={fmtPct(totalPnlPct)}
              pass={undefined}
              note="목표: 미국 대표 주가지수보다 5%p 이상 뒤처지지 않기"
            />
            <KpiRow
              label="최대 단일 포지션 손실"
              value={fmtPct(ar018_kpi.max_position_loss_pct)}
              pass={maxLossPass}
              note="기준: ≤ −15%"
            />
            <KpiRow
              label="실제 입금 한도"
              value={`$${ar018_kpi.deposit_cap_usd} hard-cap`}
              pass={undefined}
              note="8주 기준을 통과하기 전에는 실제 입금 금지"
            />
            <KpiRow
              label="모의투자 기간 목표"
              value={`${ar018_kpi.week_target}주`}
              pass={undefined}
              note="실제 증권계좌로 옮기기 전 선행 조건"
            />
          </ul>
          <div className="alpaca-gate-status">
            <span className="gate-chip blocked">실전 투자 잠금</span>
            <span className="data-meta"> — 일부 안전 조건이 아직 끝나지 않았습니다</span>
            <p className="term-note">TurtleGate는 손절가·위험 한도·사전 검토가 모두 맞는지 보는 자동 안전장치입니다.</p>
          </div>
        </article>
      </div>

      {/* ── ROW 2: 현재 포지션 ── */}
      {validPositions.length > 0 && (
        <article className="panel alpaca-full">
          <div className="panel-head"><h3>현재 포지션</h3></div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>종목</th>
                  <th className="num">수량</th>
                  <th className="num">진입가</th>
                  <th className="num">현재가</th>
                  <th className="num">평가금액</th>
                  <th className="num">손익</th>
                  <th className="num">손익%</th>
                  <th className="num">ATR(20)</th>
                  <th className="num">손절가</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {validPositions.map(p => (
                  <tr key={p.symbol} className={p.near_stop ? 'row-warning' : ''}>
                    <td><SymbolCell symbol={p.symbol} /></td>
                    <td className="num">{p.qty}</td>
                    <td className="num">${fmt(p.entry_price)}</td>
                    <td className="num">${fmt(p.current_price)}</td>
                    <td className="num">${fmt(p.market_value)}</td>
                    <td className={`num ${(p.unrealized_pnl ?? 0) > 0 ? 'pnl-pos' : (p.unrealized_pnl ?? 0) < 0 ? 'pnl-neg' : ''}`}>
                      {fmtUsd(p.unrealized_pnl)}
                    </td>
                    <PnlCell v={p.unrealized_pnl_pct} />
                    <td className="num">{p.atr ? fmt(p.atr, 4) : '—'}</td>
                    <td className="num">{p.stop_loss ? `$${fmt(p.stop_loss)}` : '—'}</td>
                    <td>
                      {p.near_stop
                        ? <span className="signal-badge signal-short">⚠ 손절 근접</span>
                        : <span className="signal-badge signal-neutral">정상</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}

      {/* ── ROW 3: 투자 신호 모니터 ── */}
      <article className="panel alpaca-full">
        <div className="panel-head">
          <h3>투자 신호 모니터</h3>
          <span className="data-meta">관찰 종목: {data.universe.map(symbol => {
            const item = symbolDisplay(symbol)
            return `${item.code}(${item.name})`
          }).join(', ')}</span>
          <span className="term-note">Turtle 신호는 정해진 가격 돌파 규칙에 따라 매수·매도 후보를 표시하는 방식입니다.</span>
        </div>

        {active_signals.length > 0 && (
          <div className="active-signals-bar">
            <span className="data-label-inline">활성 신호:</span>
            {active_signals.map(s => (
              <span key={s.symbol} className="active-signal-chip">
                <SymbolCell symbol={s.symbol} /> <SignalBadge signal={s.signal} /> {s.system}
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
              {validSignals.map(s => (
                <tr key={s.symbol} className={s.signal !== 'neutral' ? 'row-highlight' : ''}>
                  <td><SymbolCell symbol={s.symbol} /></td>
                  <td><SignalBadge signal={s.signal} /></td>
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
      </article>

      {/* ── ROW 4: 급락 브리핑 ── */}
      <DropAlertPanel
        alerts={dropAlerts}
        onAck={ackAlert}
        threshold={-3}
      />

      {/* ── ROW 5: 최근 주문 ── */}
      {orders.length > 0 && !orders[0]?.error && (
        <article className="panel alpaca-full">
          <div className="panel-head"><h3>최근 주문 내역</h3></div>
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
                {(orders as AlpacaOrder[]).map((o, i) => (
                  <tr key={`${o.id ?? ''}-${i}`}>
                    <td className="mono">{o.id}</td>
                    <td><SymbolCell symbol={o.symbol} /></td>
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
        </article>
      )}
    </section>
  )
}
