import { useCallback, useEffect, useMemo, useState } from 'react'
import './SmartfarmPage.css'

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

function MiniChart({ points }: { points: HistoryPoint[] }) {
  const line = useMemo(() => {
    if (points.length < 2) return ''
    const values = points.map(point => point.value)
    const min = Math.min(...values)
    const max = Math.max(...values)
    const span = Math.max(max - min, 1)
    return points.map((point, index) => {
      const x = (index / (points.length - 1)) * 100
      const y = 36 - ((point.value - min) / span) * 32
      return `${x.toFixed(2)},${y.toFixed(2)}`
    }).join(' ')
  }, [points])
  return (
    <div className="sf-chart" aria-label={`추세 데이터 ${points.length}개`}>
      {line ? (
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" role="img">
          <defs>
            <linearGradient id="sf-chart-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--sf-green)" stopOpacity=".3" />
              <stop offset="100%" stopColor="var(--sf-green)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <polygon points={`0,40 ${line} 100,40`} fill="url(#sf-chart-fill)" />
          <polyline points={line} fill="none" stroke="var(--sf-green)" strokeWidth="1.8" vectorEffect="non-scaling-stroke" />
        </svg>
      ) : <span>추세 데이터 대기 중</span>}
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
  const [selectedMetric, setSelectedMetric] = useState('soil_pct')
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [historyRange, setHistoryRange] = useState(86400)
  const [actionBusy, setActionBusy] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [controlOpen, setControlOpen] = useState(false)
  const [controlAction, setControlAction] = useState<'on' | 'off'>('off')
  const [duration, setDuration] = useState(10)
  const [confirmation, setConfirmation] = useState('')
  const [password, setPassword] = useState('')

  const loadOverview = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const response = await fetch(`${apiBase}/api/smartfarm/overview`, { headers: authHeaders() })
      if (!response.ok) throw new Error(`Smartfarm API ${response.status}`)
      const payload = await response.json() as Overview
      setOverview(payload)
      setSelectedZone(current => current || payload.zones[0]?.zone_id || payload.devices.find(item => item.zone_id)?.zone_id || '')
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
    if (!selectedZone || confirmation !== selectedZone) {
      setActionMessage('zone ID를 정확히 입력하세요.')
      return
    }
    setActionBusy(true)
    setActionMessage(null)
    try {
      let nonce: string | undefined
      if (controlAction === 'on') {
        const authResponse = await fetch(`${apiBase}/api/smartfarm/actuation/authorize`, {
          method: 'POST',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        })
        const authPayload = await authResponse.json()
        if (!authResponse.ok) throw new Error(authPayload.detail || '대표 재인증 실패')
        nonce = authPayload.actuation_nonce
      }
      const response = await fetch(`${apiBase}/api/smartfarm/zones/${encodeURIComponent(selectedZone)}/pump`, {
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
      setActionMessage(`명령 ${payload.command_id.slice(0, 8)} · ${payload.status}. 실제 상태 확인 전 성공 아님.`)
      setPassword('')
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
            <span>{lastSuccess ? `${lastSuccess.toLocaleTimeString('ko-KR')} 화면 갱신` : '연결 대기'}</span>
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
              <MiniChart points={history} />
            </div>
          </section>
        </section>

        <aside className="sf-side-column">
          <section className="sf-panel">
            <div className="sf-section-head">
              <div><span>CONTROL</span><h3>급수 제어</h3></div>
              <span className={`sf-mode ${overview?.runtime.actuation_enabled ? 'armed' : ''}`}>
                {overview?.runtime.actuation_enabled ? 'ARMED' : 'SAFE LOCK'}
              </span>
            </div>
            <div className="sf-pump-state">
              <span>관측 상태</span>
              <strong>{selectedZoneData?.pump.state?.toUpperCase() ?? 'UNKNOWN'}</strong>
              <small>명령 발행과 실제 상태는 별도 추적</small>
            </div>
            {viewRole === 'ceo' ? (
              <button className="sf-primary" disabled={!selectedZone} onClick={() => setControlOpen(open => !open)}>
                {controlOpen ? '제어 패널 닫기' : '안전 제어 열기'}
              </button>
            ) : <p className="sf-note">부대표 계정은 모니터링과 read-only 진단만 가능합니다.</p>}
            {controlOpen && (
              <div className="sf-control-form">
                <div className="sf-segmented">
                  <button className={controlAction === 'off' ? 'active' : ''} onClick={() => setControlAction('off')}>OFF</button>
                  <button className={controlAction === 'on' ? 'active danger' : ''} onClick={() => setControlAction('on')}>ON</button>
                </div>
                <label>최대 동작시간
                  <input type="number" min={1} max={300} value={duration} onChange={event => setDuration(Number(event.target.value))} />
                </label>
                <label>확인: <code>{selectedZone}</code> 입력
                  <input value={confirmation} onChange={event => setConfirmation(event.target.value)} autoComplete="off" />
                </label>
                {controlAction === 'on' && <label>대표 비밀번호 재확인
                  <input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" />
                </label>}
                <button className={`sf-submit ${controlAction === 'on' ? 'danger' : ''}`} disabled={actionBusy || confirmation !== selectedZone} onClick={() => void submitPump()}>
                  {actionBusy ? '안전 조건 검사 중…' : `${controlAction.toUpperCase()} 명령 검토 후 전송`}
                </button>
              </div>
            )}
          </section>

          <section className="sf-panel">
            <div className="sf-section-head"><div><span>RUNTIME</span><h3>데이터 경로</h3></div></div>
            <dl className="sf-runtime-list">
              <div><dt>MQTT broker</dt><dd className={overview?.runtime.mqtt_connected ? 'ok' : 'bad'}>{overview?.runtime.mqtt_connected ? 'connected' : 'disconnected'}</dd></div>
              <div><dt>Operational DB</dt><dd className="ok">connected</dd></div>
              <div><dt>Last message</dt><dd>{overview?.runtime.last_message_at ? new Date(overview.runtime.last_message_at).toLocaleTimeString('ko-KR') : 'none'}</dd></div>
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
              <time>{new Date(command.issued_at).toLocaleString('ko-KR')}</time>
              <span>{command.observed_state ? `observed ${command.observed_state}` : command.safety_reason || 'observation pending'}</span>
            </article>
          ))}
          {!overview?.commands.length && <div className="sf-empty">아직 관제 명령 감사 이력이 없습니다.</div>}
        </div>
      </section>
    </main>
  )
}
