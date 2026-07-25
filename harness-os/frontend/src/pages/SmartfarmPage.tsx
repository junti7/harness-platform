import { useCallback, useEffect, useMemo, useState } from 'react'
import './SmartfarmPage.css'

// 시각 표기는 KST 고정 (2026-07-25 CEO 지시). 브라우저 로케일에 맡기면 해외에서
// 접속하거나 기기 시간대가 틀어졌을 때 같은 화면이 다른 시각을 보여준다.
const KST: Intl.DateTimeFormatOptions = { timeZone: 'Asia/Seoul' }

type HeadersFactory = () => Record<string, string>

type Metric = {
  value: number
  quality: string
  recorded_at: string
  age_s: number
}

type Zone = {
  zone_id: string
  metrics: Record<string, Metric>
  pump: { state: string; observed_at?: string | null }
}

type Device = {
  device_id: string
  kind: string
  zone_id?: string | null
  board?: string
  firmware?: string
  ip?: string
  rssi_dbm?: number | null
  uptime_s?: number | null
  watchdog_max_run_ms?: number | null
  health: 'online' | 'stale' | 'offline' | 'fault' | 'unknown'
  last_seen_age_s: number
  last_seen_at?: string
  capabilities: { sensors?: string[]; actuators?: string[] }
}

type Command = {
  command_id: string
  device_id?: string | null
  zone_id: string
  kind: string
  actor: string
  status: string
  safety_reason?: string | null
  issued_at: string
  observed_state?: string | null
}

type Overview = {
  generated_at: string
  runtime: {
    mqtt_configured: boolean
    mqtt_connected: boolean
    mqtt_host?: string | null
    last_message_at?: string | null
    error?: string | null
    db_ok: boolean
    writer_queue_depth: number
    actuation_enabled: boolean
    pump_test_enabled: boolean
    pump_control_zones: string[]
    pump_max_duration_s: number
  }
  summary: {
    devices_total: number
    devices: Record<string, number>
    zones_total: number
    alerts_open: number
  }
  zones: Zone[]
  devices: Device[]
  commands: Command[]
}

type HistoryPoint = { value: number; quality: string; recorded_at: string }

const METRICS: Record<string, { label: string; unit: string; decimals: number }> = {
  soil_pct: { label: '토양수분', unit: '%', decimals: 0 },
  soil_raw: { label: 'Soil raw', unit: '', decimals: 0 },
  temp_c: { label: '온도', unit: '°C', decimals: 1 },
  humidity_pct: { label: '습도', unit: '%', decimals: 0 },
  light_lux: { label: '조도', unit: ' lx', decimals: 0 },
  water_level_pct: { label: '수위', unit: '%', decimals: 0 },
  flow_lpm: { label: '유량', unit: ' L/min', decimals: 2 },
}

function ageLabel(seconds?: number | null) {
  if (seconds == null) return '수신 이력 없음'
  if (seconds < 60) return `${Math.round(seconds)}초 전`
  if (seconds < 3600) return `${Math.round(seconds / 60)}분 전`
  return `${Math.round(seconds / 3600)}시간 전`
}

function durationLabel(seconds?: number | null) {
  if (seconds == null) return '—'
  if (seconds < 3600) return `${Math.round(seconds / 60)}분`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}시간 ${Math.round((seconds % 3600) / 60)}분`
  return `${Math.floor(seconds / 86400)}일`
}

function metricValue(metric: string, value?: Metric) {
  if (!value) return '—'
  const spec = METRICS[metric]
  return `${value.value.toFixed(spec?.decimals ?? 1)}${spec?.unit ?? ''}`
}

function chartTimeLabel(timestamp: number, rangeSeconds: number) {
  const date = new Date(timestamp)
  const datePart = new Intl.DateTimeFormat('ko-KR', {
    ...KST,
    month: '2-digit',
    day: '2-digit',
  }).format(date).replace(/\s/g, '')
  const timePart = new Intl.DateTimeFormat('ko-KR', {
    ...KST,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(date)
  return rangeSeconds >= 21600 ? `${datePart} ${timePart}` : timePart
}

function MiniChart({ points, rangeSeconds }: { points: HistoryPoint[]; rangeSeconds: number }) {
  const chart = useMemo(() => {
    if (points.length < 2) return { line: '', ticks: [] as { x: number; label: string }[] }
    const timedPoints = points
      .map((point, index) => ({
        ...point,
        timestamp: Date.parse(point.recorded_at),
        fallbackTimestamp: index,
      }))
      .sort((a, b) => (Number.isFinite(a.timestamp) ? a.timestamp : a.fallbackTimestamp)
        - (Number.isFinite(b.timestamp) ? b.timestamp : b.fallbackTimestamp))
    const timestamps = timedPoints.map(point => Number.isFinite(point.timestamp) ? point.timestamp : point.fallbackTimestamp)
    const start = timestamps[0]
    const end = timestamps[timestamps.length - 1]
    const timeSpan = Math.max(end - start, 1)
    const values = timedPoints.map(point => point.value)
    const min = Math.min(...values)
    const max = Math.max(...values)
    const span = Math.max(max - min, 1)
    const line = timedPoints.map((point, index) => {
      const x = ((timestamps[index] - start) / timeSpan) * 100
      const y = 36 - ((point.value - min) / span) * 32
      return `${x.toFixed(2)},${y.toFixed(2)}`
    }).join(' ')
    const tickCount = 5
    const ticks = Array.from({ length: tickCount }, (_, index) => {
      const ratio = index / (tickCount - 1)
      const timestamp = start + timeSpan * ratio
      return {
        x: ratio * 100,
        label: chartTimeLabel(timestamp, rangeSeconds),
      }
    })
    return { line, ticks }
  }, [points, rangeSeconds])
  return (
    <div className="sf-chart-frame">
      <div className="sf-chart" aria-label={`추세 데이터 ${points.length}개`}>
        {chart.line ? (
          <svg viewBox="0 0 100 40" preserveAspectRatio="none" role="img">
            <defs>
              <linearGradient id="sf-chart-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--sf-green)" stopOpacity=".3" />
                <stop offset="100%" stopColor="var(--sf-green)" stopOpacity="0" />
              </linearGradient>
            </defs>
            <polygon points={`0,40 ${chart.line} 100,40`} fill="url(#sf-chart-fill)" />
            <polyline points={chart.line} fill="none" stroke="var(--sf-green)" strokeWidth="1.8" vectorEffect="non-scaling-stroke" />
          </svg>
        ) : <span>추세 데이터 대기 중</span>}
      </div>
      {chart.ticks.length > 0 && (
        <div className="sf-chart-axis" aria-label="날짜 및 시간 축">
          {chart.ticks.map(tick => (
            <time key={`${tick.x}-${tick.label}`} style={{ left: `${tick.x}%` }}>{tick.label}</time>
          ))}
        </div>
      )}
    </div>
  )
}

export function SmartfarmPage({
  apiBase,
  authHeaders,
  viewRole,
}: {
  apiBase: string
  authHeaders: HeadersFactory
  viewRole: 'ceo' | 'vp'
}) {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastSuccess, setLastSuccess] = useState<Date | null>(null)
  const [selectedZone, setSelectedZone] = useState('')
  const [selectedControlZone, setSelectedControlZone] = useState('')
  const [selectedMetric, setSelectedMetric] = useState('soil_pct')
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [historyRange, setHistoryRange] = useState(86400)
  const [actionBusy, setActionBusy] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [controlOpen, setControlOpen] = useState(false)
  const [controlAction, setControlAction] = useState<'off' | 'test'>('off')
  const [duration, setDuration] = useState(3)
  const [confirmation, setConfirmation] = useState('')

  const loadOverview = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const response = await fetch(`${apiBase}/api/smartfarm/overview`, { headers: authHeaders() })
      if (!response.ok) throw new Error(`Smartfarm API ${response.status}`)
      const payload = await response.json() as Overview
      setOverview(payload)
      setSelectedZone(current => current || payload.zones[0]?.zone_id || payload.devices.find(item => item.zone_id)?.zone_id || '')
      setSelectedControlZone(current => (
        payload.runtime.pump_control_zones.includes(current)
          ? current
          : payload.runtime.pump_control_zones[0] || ''
      ))
      setDuration(current => Math.min(current, payload.runtime.pump_max_duration_s))
      setError(null)
      setLastSuccess(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Smartfarm dashboard load failed')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [apiBase, authHeaders])

  useEffect(() => {
    const initial = window.setTimeout(() => void loadOverview(), 0)
    const timer = window.setInterval(() => void loadOverview(true), 2000)
    return () => {
      window.clearTimeout(initial)
      window.clearInterval(timer)
    }
  }, [loadOverview])

  useEffect(() => {
    if (!selectedZone) {
      const clear = window.setTimeout(() => setHistory([]), 0)
      return () => window.clearTimeout(clear)
    }
    let cancelled = false
    const load = async () => {
      try {
        const query = new URLSearchParams({
          zone_id: selectedZone,
          metric: selectedMetric,
          since_s: String(historyRange),
          limit: '600',
        })
        const response = await fetch(`${apiBase}/api/smartfarm/history?${query}`, { headers: authHeaders() })
        if (!response.ok) throw new Error(`History API ${response.status}`)
        const payload = await response.json() as { points: HistoryPoint[] }
        if (!cancelled) setHistory(payload.points)
      } catch {
        if (!cancelled) setHistory([])
      }
    }
    void load()
    const timer = window.setInterval(() => void load(), 10000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [apiBase, authHeaders, historyRange, selectedMetric, selectedZone])

  const submitPump = async () => {
    const controlZone = selectedControlZone
    if (!controlZone || confirmation !== controlZone) {
      setActionMessage('zone ID를 정확히 입력하세요.')
      return
    }
    setActionBusy(true)
    setActionMessage(null)
    try {
      let nonce: string | undefined
      if (controlAction === 'test') {
        const tokenResponse = await fetch(`${apiBase}/api/smartfarm/actuation/session-token`, {
          method: 'POST',
          headers: authHeaders(),
        })
        const tokenPayload = await tokenResponse.json()
        if (!tokenResponse.ok) throw new Error(tokenPayload.detail || 'CEO 세션 확인 실패')
        nonce = tokenPayload.actuation_nonce
      }
      const response = await fetch(`${apiBase}/api/smartfarm/zones/${encodeURIComponent(controlZone)}/pump`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: controlAction,
          duration_s: duration,
          confirmation,
          actuation_nonce: nonce,
        }),
      })
      const payload = await response.json()
      if (!response.ok) {
        const detail = typeof payload.detail === 'object' ? payload.detail.code || payload.detail.message : payload.detail
        throw new Error(detail || `Pump API ${response.status}`)
      }
      setActionMessage(
        controlAction === 'test'
          ? `펌프 테스트 ${payload.command_id.slice(0, 8)} 시작 · 자동 OFF와 실제 상태 확인 중`
          : `OFF 명령 ${payload.command_id.slice(0, 8)} · ${payload.status}`,
      )
      if (controlAction === 'test') {
        let completed = false
        const maxAttempts = Math.ceil((duration + 7) * 2)
        for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
          await new Promise(resolve => window.setTimeout(resolve, 500))
          const commandResponse = await fetch(
            `${apiBase}/api/smartfarm/commands/${encodeURIComponent(payload.command_id)}`,
            { headers: authHeaders() },
          )
          if (!commandResponse.ok) continue
          const command = await commandResponse.json() as Command
          if (command.status === 'completed' && command.observed_state === 'off') {
            setActionMessage(
              `펌프 테스트 ${payload.command_id.slice(0, 8)} 완료 · 실제 ON 후 자동 OFF 확인`,
            )
            completed = true
            break
          }
          if (command.status === 'rejected' || command.status === 'blocked' || command.status === 'unknown') {
            const reason = command.safety_reason === 'active_or_cooldown'
              ? '펌프 동작 또는 5초 재실행 대기 중'
              : command.safety_reason || command.status
            throw new Error(`펌프 테스트 거부: ${reason}`)
          }
        }
        if (!completed) throw new Error('펌프 실제 ON/OFF 확인 시간 초과')
      }
      void loadOverview(true)
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : '명령 실패')
    } finally {
      setActionBusy(false)
    }
  }

  const runDiagnostic = async (device: Device) => {
    setActionBusy(true)
    setActionMessage(null)
    try {
      const response = await fetch(`${apiBase}/api/smartfarm/devices/${encodeURIComponent(device.device_id)}/test`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ checks: ['connectivity', 'sensors'], invasive: false }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : payload.detail?.message || `Test API ${response.status}`)
      setActionMessage(`진단 ${payload.command_id.slice(0, 8)} 요청됨 · ack/result 대기`)
      void loadOverview(true)
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : '진단 요청 실패')
    } finally {
      setActionBusy(false)
    }
  }

  const selectedZoneData = overview?.zones.find(zone => zone.zone_id === selectedZone)
  const controlZone = selectedControlZone
  const controlZoneData = overview?.zones.find(zone => zone.zone_id === controlZone)
  const durationLimit = Math.min(3, overview?.runtime.pump_max_duration_s ?? 3)
  const devices = overview?.devices ?? []
  const unhealthy = devices.filter(device => device.health !== 'online').length

  if (loading && !overview) {
    return <main className="sf-page"><div className="sf-loading">스마트팜 운영 상태 연결 중…</div></main>
  }

  return (
    <main className="sf-page">
      <header className="sf-hero">
        <div>
          <span className="sf-eyebrow">PHYSICAL OPERATIONS</span>
          <h2>Smartfarm Control Center</h2>
          <p>센서 신호, edge fleet, 급수 안전 상태를 한곳에서 추적합니다.</p>
        </div>
        <div className="sf-live">
          <span className={`sf-live-dot ${overview?.runtime.mqtt_connected ? 'online' : 'offline'}`} />
          <div>
            <strong>{overview?.runtime.mqtt_connected ? 'LIVE MQTT' : 'MQTT DISCONNECTED'}</strong>
            <span>{lastSuccess ? `${lastSuccess.toLocaleTimeString('ko-KR', KST)} 화면 갱신` : '연결 대기'}</span>
          </div>
        </div>
      </header>

      {error && <div className="sf-banner danger"><strong>실시간 갱신 중단</strong><span>{error} · 마지막 정상 데이터를 유지합니다.</span></div>}
      {!overview?.runtime.mqtt_configured && <div className="sf-banner warn"><strong>Broker 미설정</strong><span>HARNESS_SMARTFARM_MQTT_HOST를 설정해야 실제 device telemetry가 들어옵니다.</span></div>}
      {actionMessage && <div className="sf-banner info"><strong>작업 상태</strong><span>{actionMessage}</span></div>}

      <section className="sf-kpis" aria-label="Smartfarm 핵심 상태">
        <article><span>운영 구역</span><strong>{overview?.summary.zones_total ?? 0}</strong><small>configured + observed</small></article>
        <article><span>온라인 기기</span><strong>{overview?.summary.devices.online ?? 0}<em> / {overview?.summary.devices_total ?? 0}</em></strong><small>heartbeat fresh</small></article>
        <article className={unhealthy > 0 ? 'attention' : ''}><span>확인 필요</span><strong>{unhealthy}</strong><small>stale · offline · fault</small></article>
        <article className={(overview?.summary.alerts_open ?? 0) > 0 ? 'danger' : ''}><span>활성 경보</span><strong>{overview?.summary.alerts_open ?? 0}</strong><small>open incidents</small></article>
        <article><span>관제 DB</span><strong>{overview?.runtime.db_ok ? '정상' : '오류'}</strong><small>queue {overview?.runtime.writer_queue_depth ?? 0}</small></article>
      </section>

      <div className="sf-layout">
        <section className="sf-main-column">
          <div className="sf-section-head">
            <div><span>ZONE STATUS</span><h3>구역별 생육 환경</h3></div>
            <select value={selectedZone} onChange={event => setSelectedZone(event.target.value)} aria-label="구역 선택">
              {(overview?.zones ?? []).map(zone => <option key={zone.zone_id}>{zone.zone_id}</option>)}
              {!overview?.zones.length && <option value="">관측 구역 없음</option>}
            </select>
          </div>

          <div className="sf-zone-grid">
            {(overview?.zones ?? []).map(zone => {
              const worstAge = Math.max(0, ...Object.values(zone.metrics).map(metric => metric.age_s))
              const stale = worstAge > 90
              return (
                <button key={zone.zone_id} className={`sf-zone-card ${selectedZone === zone.zone_id ? 'selected' : ''}`} onClick={() => setSelectedZone(zone.zone_id)}>
                  <div className="sf-zone-title">
                    <div><span className={`sf-health-dot ${stale ? 'stale' : 'online'}`} /><strong>{zone.zone_id}</strong></div>
                    <span className={`sf-pump ${zone.pump.state}`}>PUMP {zone.pump.state.toUpperCase()}</span>
                  </div>
                  <div className="sf-zone-metrics">
                    {['soil_pct', 'temp_c', 'humidity_pct'].map(metric => (
                      <div key={metric}>
                        <span>{METRICS[metric].label}</span>
                        <strong>{metricValue(metric, zone.metrics[metric])}</strong>
                        <small>{ageLabel(zone.metrics[metric]?.age_s)}</small>
                      </div>
                    ))}
                  </div>
                </button>
              )
            })}
            {!overview?.zones.length && <div className="sf-empty">아직 DB에 수신된 zone telemetry가 없습니다.</div>}
          </div>

          <section className="sf-panel sf-telemetry">
            <div className="sf-section-head">
              <div><span>LIVE TELEMETRY</span><h3>{selectedZone || '구역 미선택'} 추세</h3></div>
              <div className="sf-controls">
                <select value={selectedMetric} onChange={event => setSelectedMetric(event.target.value)} aria-label="센서 지표">
                  {Object.entries(METRICS).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}
                </select>
                <select value={historyRange} onChange={event => setHistoryRange(Number(event.target.value))} aria-label="조회 기간">
                  <option value={3600}>1시간</option>
                  <option value={86400}>24시간</option>
                  <option value={604800}>7일</option>
                </select>
              </div>
            </div>
            <div className="sf-chart-summary">
              <div>
                <span>현재</span>
                <strong>{metricValue(selectedMetric, selectedZoneData?.metrics[selectedMetric])}</strong>
                <small>{history.length} samples · 보간 없음</small>
              </div>
              <MiniChart points={history} rangeSeconds={historyRange} />
            </div>
          </section>
        </section>

        <aside className="sf-side-column">
          <section className="sf-panel">
            <div className="sf-section-head">
              <div><span>CONTROL</span><h3>{controlZone || '미설정'} 급수 제어</h3></div>
              <span className={`sf-mode ${overview?.runtime.pump_test_enabled ? 'armed' : ''}`}>
                {overview?.runtime.pump_test_enabled ? 'TEST READY' : 'SAFE LOCK'}
              </span>
            </div>
            {(overview?.runtime.pump_control_zones.length ?? 0) > 1 && (
              <label className="sf-note">펌프 구역
                <select value={controlZone} onChange={event => setSelectedControlZone(event.target.value)}>
                  {overview?.runtime.pump_control_zones.map(zone => <option key={zone}>{zone}</option>)}
                </select>
              </label>
            )}
            <div className="sf-pump-state">
              <span>관측 상태</span>
              <strong>{controlZoneData?.pump.state?.toUpperCase() ?? 'UNKNOWN'}</strong>
              <small>명령 발행과 실제 상태는 별도 추적</small>
            </div>
            {viewRole === 'ceo' ? (
              <button className="sf-primary" disabled={!controlZone} onClick={() => setControlOpen(open => !open)}>
                {controlOpen ? '제어 패널 닫기' : '안전 제어 열기'}
              </button>
            ) : <p className="sf-note">부대표 계정은 모니터링과 read-only 진단만 가능합니다.</p>}
            {controlOpen && (
              <div className="sf-control-form">
                <div className="sf-segmented">
                  <button className={controlAction === 'off' ? 'active' : ''} onClick={() => setControlAction('off')}>OFF</button>
                  <button className={controlAction === 'test' ? 'active test' : ''} onClick={() => {
                    setControlAction('test')
                    setDuration(current => Math.min(current, 3, overview?.runtime.pump_max_duration_s ?? 3))
                  }}>TEST</button>
                </div>
                <label>최대 동작시간
                  <input
                    type="number"
                    min={1}
                    max={durationLimit}
                    value={duration}
                    onChange={event => {
                      const parsed = Number.parseInt(event.target.value, 10)
                      setDuration(Number.isFinite(parsed) ? Math.max(1, Math.min(parsed, durationLimit)) : 1)
                    }}
                  />
                </label>
                <label>오작동 방지 확인 — <code>{controlZone}</code> 입력
                  <input value={confirmation} onChange={event => setConfirmation(event.target.value)} autoComplete="off" />
                </label>
                <button className="sf-submit" disabled={actionBusy || confirmation !== controlZone} onClick={() => void submitPump()}>
                  {actionBusy
                    ? '안전 조건 검사 중…'
                    : controlAction === 'test'
                      ? `${duration}초 펌프 테스트 실행`
                      : '펌프 즉시 OFF'}
                </button>
                {actionMessage && <p className="sf-control-result" role="status">{actionMessage}</p>}
              </div>
            )}
          </section>

          <section className="sf-panel">
            <div className="sf-section-head"><div><span>RUNTIME</span><h3>데이터 경로</h3></div></div>
            <dl className="sf-runtime-list">
              <div><dt>MQTT broker</dt><dd className={overview?.runtime.mqtt_connected ? 'ok' : 'bad'}>{overview?.runtime.mqtt_connected ? 'connected' : 'disconnected'}</dd></div>
              <div><dt>Operational DB</dt><dd className="ok">connected</dd></div>
              <div><dt>Last message</dt><dd>{overview?.runtime.last_message_at ? new Date(overview.runtime.last_message_at).toLocaleTimeString('ko-KR', KST) : 'none'}</dd></div>
              <div><dt>Actuation</dt><dd>{overview?.runtime.actuation_enabled ? 'enabled' : 'blocked'}</dd></div>
            </dl>
            {overview?.runtime.error && <p className="sf-runtime-error">{overview.runtime.error}</p>}
          </section>
        </aside>
      </div>

      <section className="sf-panel sf-fleet">
        <div className="sf-section-head"><div><span>EDGE FLEET</span><h3>Raspberry Pi · ESP8266 · ESP32</h3></div><span>{devices.length} devices</span></div>
        <div className="sf-table-wrap">
          <table>
            <thead><tr><th>상태</th><th>기기</th><th>종류 / 보드</th><th>Zone</th><th>네트워크</th><th>Firmware</th><th>Uptime</th><th>Watchdog</th><th>진단</th></tr></thead>
            <tbody>
              {devices.map(device => (
                <tr key={device.device_id}>
                  <td><span className={`sf-status ${device.health}`}>{device.health}</span></td>
                  <td><strong>{device.device_id}</strong><small>{ageLabel(device.last_seen_age_s)}</small></td>
                  <td>{device.kind}<small>{device.board || 'identity pending'}</small></td>
                  <td>{device.zone_id || 'system'}</td>
                  <td>{device.ip || '—'}<small>{device.rssi_dbm != null ? `${device.rssi_dbm} dBm` : 'RSSI —'}</small></td>
                  <td>{device.firmware || 'unknown'}</td>
                  <td>{durationLabel(device.uptime_s)}</td>
                  <td>{device.watchdog_max_run_ms ? `${device.watchdog_max_run_ms / 1000}s` : '미검증'}</td>
                  <td><button disabled={actionBusy || !device.zone_id || device.health === 'offline'} onClick={() => void runDiagnostic(device)}>Self-test</button></td>
                </tr>
              ))}
              {!devices.length && <tr><td colSpan={9} className="sf-empty">heartbeat를 수신한 기기가 없습니다.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="sf-panel sf-audit">
        <div className="sf-section-head"><div><span>AUDIT TRAIL</span><h3>명령 · 확인 · 실제 상태</h3></div></div>
        <div className="sf-command-list">
          {(overview?.commands ?? []).map(command => (
            <article key={command.command_id}>
              <span className={`sf-command-status ${command.status}`}>{command.status}</span>
              <div><strong>{command.kind.replace('_', ' ').toUpperCase()} · {command.zone_id}</strong><small>{command.command_id} · {command.actor}</small></div>
              <time>{new Date(command.issued_at).toLocaleString('ko-KR', KST)}</time>
              <span>{command.observed_state ? `observed ${command.observed_state}` : command.safety_reason || 'observation pending'}</span>
            </article>
          ))}
          {!overview?.commands.length && <div className="sf-empty">아직 관제 명령 감사 이력이 없습니다.</div>}
        </div>
      </section>
    </main>
  )
}
