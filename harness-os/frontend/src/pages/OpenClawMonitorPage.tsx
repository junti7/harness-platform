import { useEffect, useState, useCallback, useRef } from 'react'

type OpenClaw71Info = {
  watchdog_interval_sec: number
  session_persistence_active: boolean
  persisted_sessions_count: number
  ab_testing_enabled: boolean
  ab_model_b: string
  clawrouter_enabled: boolean
  provider_mode: string
}

type UnifiedUsage = {
  date: string
  today_cost_usd: number
  daily_limit_usd: number
  budget_utilization_pct: number | null
  harness_models: Record<string, { provider: string; model: string; input_tokens: number; output_tokens: number; calls: number }>
  gateway_models: Record<string, { provider: string; model: string; tokens: number; cost_usd: number; calls: number }>
}

type OpenClawStatus = {
  ok: boolean
  running: boolean
  gateway_reachable: boolean
  pid: number | null
  latency_ms: number | null
  gateway_url: string
  binary_exists: boolean
  binary_path: string
  launchagent_installed: boolean
  launchagent_label: string
  checked_at: string
  openclaw_71?: OpenClaw71Info
  snapshot?: {
    generated_at?: string
    openclaw_bridge?: string
    runtime?: {
      python?: string
      cwd?: string
      slack_phase?: string
      slack_delivery_mode?: string
      capital_actions_enabled?: string
    }
    integrations?: {
      codex?: { available: boolean; path?: string }
      openclaw?: { available: boolean; path?: string }
      claude?: { available: boolean; path?: string }
      gemini?: { available: boolean; path?: string }
      copilot?: { available: boolean; path?: string }
      ollama?: { available: boolean; path?: string }
      postgres?: { available: boolean; error?: string | null }
      slack_bot?: { available: boolean }
      slack_webhook?: { available: boolean }
      notion?: { available: boolean }
    }
    services?: {
      ollama_11434?: boolean
    }
    integrity?: {
      ok: boolean
      findings?: string[]
    }
    routes?: Record<string, string>
    supported_commands?: string[]
  }
  watchdog_logs?: string[]
}

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

export function OpenClawMonitorPage({ apiBase, authHeaders }: Props) {
  const [status, setStatus] = useState<OpenClawStatus | null>(null)
  const [usage, setUsage] = useState<UnifiedUsage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [restarting, setRestarting] = useState(false)
  const [restartResult, setRestartResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const [resStatus, resUsage] = await Promise.all([
        fetch(`${apiBase}/api/system/openclaw/status`, { headers: authHeaders() }),
        fetch(`${apiBase}/api/costs/unified-usage`, { headers: authHeaders() }).catch(() => null)
      ])
      if (!resStatus.ok) throw new Error(`HTTP ${resStatus.status}`)
      const data = (await resStatus.json()) as OpenClawStatus
      setStatus(data)
      if (resUsage && resUsage.ok) {
        const uData = (await resUsage.json()) as UnifiedUsage
        setUsage(uData)
      }
      setError(null)
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'OpenClaw 상태 조회 실패')
    }
  }, [apiBase, authHeaders])

  useEffect(() => {
    setLoading(true)
    void fetchStatus().finally(() => setLoading(false))
    intervalRef.current = setInterval(() => void fetchStatus(), 10000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchStatus])

  const handleRestart = async () => {
    if (!window.confirm('OpenClaw 게이트웨이 및 브릿지 서비스를 강제 재시동하시겠습니까?')) return
    setRestarting(true)
    setRestartResult(null)
    try {
      const res = await fetch(`${apiBase}/api/system/openclaw/restart`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const data = await res.json()
      setRestartResult({ ok: data.ok, msg: data.message ?? (data.ok ? '재시동 성공' : '재시동 실패') })
      if (data.status) setStatus(data.status)
      setTimeout(() => void fetchStatus(), 3000)
    } catch (err) {
      setRestartResult({ ok: false, msg: '서버 연결 실패' })
    } finally {
      setRestarting(false)
    }
  }

  const integrationList = status?.snapshot?.integrations
  const watchdogLogs = status?.watchdog_logs ?? []

  return (
    <main className="container page-pipeline" style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem' }}>
      <header className="page-header" style={{ marginBottom: '1.8rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.6rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span>🤖</span> OpenClaw 자가치유 통제 센터
            </h2>
            <p style={{ margin: '0.4rem 0 0', color: 'var(--color-text-muted)', fontSize: '0.88rem' }}>
              슬랙 비서 및 멀티 LLM 관계부서 오케스트레이션 24/7 백그라운드 엔진 실시간 관제 및 자동 자가치유 피드백
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={() => {
                setLoading(true)
                void fetchStatus().finally(() => setLoading(false))
              }}
              disabled={loading}
              className="btn btn-secondary"
              style={{ padding: '0.45rem 1rem', fontSize: '0.85rem', fontWeight: 600 }}
            >
              {loading ? '🔄 동기화 중...' : '🔄 강제 동기화'}
            </button>
            <button
              onClick={handleRestart}
              disabled={restarting}
              className="btn btn-danger"
              style={{
                padding: '0.45rem 1rem',
                fontSize: '0.85rem',
                fontWeight: 700,
                background: 'var(--color-danger)',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: restarting ? 'not-allowed' : 'pointer'
              }}
            >
              {restarting ? '⚡ 재시동 중...' : '⚡ 즉시 강제 재시동'}
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '1.5rem', padding: '1rem', borderRadius: '8px', background: 'rgba(235, 94, 85, 0.1)', border: '1px solid var(--color-danger)', color: 'var(--color-danger)' }}>
          <strong>⚠️ 통제 센터 연결 불가:</strong> {error}
        </div>
      )}

      {restartResult && (
        <div className={`alert ${restartResult.ok ? 'alert-success' : 'alert-danger'}`} style={{
          marginBottom: '1.5rem',
          padding: '1rem',
          borderRadius: '8px',
          background: restartResult.ok ? 'rgba(46, 213, 115, 0.1)' : 'rgba(235, 94, 85, 0.1)',
          border: `1px solid ${restartResult.ok ? 'var(--color-ok)' : 'var(--color-danger)'}`,
          color: restartResult.ok ? 'var(--color-ok)' : 'var(--color-danger)'
        }}>
          {restartResult.msg}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.2rem', marginBottom: '1.8rem' }}>
        {/* 게이트웨이 코어 카드 */}
        <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.2rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.4rem' }}>
            OpenClaw Gateway 상태
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem' }}>
            <span style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: status?.ok ? 'var(--color-ok)' : 'var(--color-danger)',
              display: 'inline-block'
            }} />
            <strong style={{ fontSize: '1.2rem', fontWeight: 800 }}>
              {status?.running ? '구동 중 (ACTIVE)' : '정지됨 (INACTIVE)'}
            </strong>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: '0.6rem' }}>
            PID: {status?.pid ?? 'N/A'} · 지연시간: {status?.latency_ms ?? '0'}ms
          </div>
        </div>

        {/* 자가치유 워치독 (300s) */}
        <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.2rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.4rem' }}>
            자가치유 워치독 (OpenClaw 7.1)
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem' }}>
            <span style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: status?.launchagent_installed ? 'var(--color-ok)' : 'var(--color-danger)',
              display: 'inline-block'
            }} />
            <strong style={{ fontSize: '1.2rem', fontWeight: 800 }}>
              {status?.launchagent_installed ? '감시 활성 (300s)' : '비활성 (DISABLED)'}
            </strong>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: '0.6rem' }}>
            주기: 300초(5분) 경량 자가복구 · OOM/Crash 추적
          </div>
        </div>

        {/* 대화 세션 영속화 (Crash 복구) */}
        <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.2rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.4rem' }}>
            세션 영속성 (Crash Recovery)
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem' }}>
            <span style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: 'var(--color-ok)',
              display: 'inline-block'
            }} />
            <strong style={{ fontSize: '1.2rem', fontWeight: 800 }}>
              보존 중 ({status?.openclaw_71?.persisted_sessions_count ?? 0}개 세션)
            </strong>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: '0.6rem' }}>
            JSONL Write-Behind · 복구 TTL: 24h
          </div>
        </div>

        {/* Sonnet 5 A/B & ClawRouter */}
        <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.2rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.4rem' }}>
            라우팅 엔진 & 실험
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, marginTop: '0.4rem' }}>
            A/B 실험: <span style={{ color: status?.openclaw_71?.ab_testing_enabled ? 'var(--color-ok)' : 'var(--color-text-muted)' }}>{status?.openclaw_71?.ab_testing_enabled ? `활성 (${status.openclaw_71.ab_model_b})` : '비활성 (Sonnet 4.5)'}</span>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: '0.4rem' }}>
            ClawRouter: {status?.openclaw_71?.clawrouter_enabled ? '동적 라우팅' : `Auto Mode (${status?.openclaw_71?.provider_mode ?? 'auto'})`}
          </div>
        </div>
      </div>

      {/* 통합 LLM 실시간 비용 및 예산 모니터링 */}
      {usage && (
        <section style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.5rem', marginBottom: '1.8rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: 0, marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>💳 실시간 통합 LLM 사용량 & 예산 (Unified LLM Cost View)</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', fontWeight: 400 }}>기준일: {usage.date}</span>
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.2rem' }}>
            <div style={{ padding: '0.8rem 1rem', borderRadius: '6px', background: 'var(--color-bg-dark, #0d1117)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '0.72rem', color: '#8b949e' }}>오늘 지출 누적</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#38edf6' }}>${usage.today_cost_usd.toFixed(4)}</div>
            </div>
            <div style={{ padding: '0.8rem 1rem', borderRadius: '6px', background: 'var(--color-bg-dark, #0d1117)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '0.72rem', color: '#8b949e' }}>일일 예산 한도</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#adbac7' }}>${usage.daily_limit_usd.toFixed(2)}</div>
            </div>
            <div style={{ padding: '0.8rem 1rem', borderRadius: '6px', background: 'var(--color-bg-dark, #0d1117)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '0.72rem', color: '#8b949e' }}>예산 소모율 (%)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: usage.budget_utilization_pct && usage.budget_utilization_pct > 80 ? 'var(--color-danger)' : 'var(--color-ok)' }}>
                {usage.budget_utilization_pct !== null ? `${usage.budget_utilization_pct}%` : 'N/A'}
              </div>
            </div>
          </div>
          {Object.keys(usage.harness_models).length > 0 && (
            <div style={{ fontSize: '0.8rem' }}>
              <strong style={{ color: 'var(--color-text-muted)', display: 'block', marginBottom: '0.4rem' }}>오늘 사용된 모델 현황 (Harness DB):</strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {Object.entries(usage.harness_models).map(([key, item]) => (
                  <span key={key} style={{ padding: '0.25rem 0.6rem', borderRadius: '4px', background: 'var(--color-surface-lighter)', border: '1px solid var(--color-border)', fontFamily: 'monospace' }}>
                    {item.model} ({item.provider}): {item.input_tokens + item.output_tokens} tokens ({item.calls}회)
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}


      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
        {/* 왼쪽: 연동 서비스 스캔 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <section style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: 0, marginBottom: '1.2rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.6rem' }}>
              🔌 연동 모듈 및 환경 스캔 (Integrations Scan)
            </h3>
            {integrationList ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.85rem' }}>
                {Object.entries(integrationList).map(([key, info]: [string, any]) => {
                  const available = info?.available ?? false
                  const err = info?.error
                  return (
                    <div key={key} style={{
                      padding: '0.75rem',
                      borderRadius: '6px',
                      border: '1px solid var(--color-border)',
                      background: available ? 'color-mix(in srgb, var(--color-ok) 5%, var(--color-surface))' : 'color-mix(in srgb, var(--color-danger) 5%, var(--color-surface))',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.2rem'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'capitalize' }}>{key}</span>
                        <span style={{
                          fontSize: '0.65rem',
                          padding: '0.1rem 0.35rem',
                          borderRadius: '4px',
                          fontWeight: 700,
                          background: available ? 'var(--color-ok)' : 'var(--color-danger)',
                          color: '#fff'
                        }}>
                          {available ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                      {err && <span style={{ fontSize: '0.65rem', color: 'var(--color-danger)' }}>{err}</span>}
                      {info?.path && <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={info.path}>{info.path}</span>}
                    </div>
                  )
                })}
              </div>
            ) : (
              <div style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>통합 브릿지 스냅샷이 존재하지 않습니다.</div>
            )}
          </section>

          {/* 실시간 워치독 자가 치유 로그 */}
          <section style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: 0, marginBottom: '0.8rem' }}>
              🛡️ 워치독 자가 치유 피드백 로그 (Watchdog Self-Healing Log)
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '1.2rem', marginTop: 0 }}>
              프로세스나 데이터베이스 커넥션 풀 다운 발생 시 감지하여 **자동으로 PostgreSQL 재시동 및 OpenClaw 세션을 복구**한 타임라인 기록입니다.
            </p>
            <div style={{
              background: 'var(--color-bg-dark, #0d1117)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              maxHeight: '300px',
              overflowY: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.78rem',
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              color: '#adbac7'
            }}>
              {watchdogLogs.length > 0 ? (
                watchdogLogs.map((line, idx) => {
                  const isErr = line.includes('DATABASE ERROR') || line.includes('DEAD')
                  const isHealing = line.includes('Rebooting') || line.includes('healing') || line.includes('restarted')
                  let color = '#adbac7'
                  if (isErr) color = 'var(--color-danger)'
                  else if (isHealing) color = 'var(--color-warn)'
                  else if (line.includes('OK')) color = 'var(--color-ok)'
                  return <div key={idx} style={{ color, marginBottom: '0.2rem' }}>{line}</div>
                })
              ) : (
                <div style={{ color: 'var(--color-text-muted)' }}>기록된 워치독 자가 회복 로그가 없습니다.</div>
              )}
            </div>
          </section>
        </div>

        {/* 오른쪽: 시스템 구성 메타 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <section style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: 0, marginBottom: '1.2rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.6rem' }}>
              ⚙️ 시스템 메타 정보
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.85rem' }}>
              <div>
                <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '0.72rem' }}>가상환경 파이썬 경로</span>
                <strong style={{ wordBreak: 'break-all' }}>{status?.snapshot?.runtime?.python ?? status?.binary_path ?? '—'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '0.72rem' }}>작동 디렉토리</span>
                <strong style={{ wordBreak: 'break-all' }}>{status?.snapshot?.runtime?.cwd ?? '—'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '0.72rem' }}>Slack 채널 설정</span>
                <span style={{ display: 'block' }}>전략 회의실: <code>{status?.snapshot?.routes?.executive ?? '#exec-president-decisions'}</code></span>
                <span style={{ display: 'block' }}>인시던트 채널: <code>{status?.snapshot?.routes?.incidents ?? '#ops-incidents'}</code></span>
              </div>
              <div>
                <span style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: '0.72rem' }}>자본 집행 통제 (Turtle Trading Gate)</span>
                <strong style={{ color: status?.snapshot?.runtime?.capital_actions_enabled === 'true' ? 'var(--color-danger)' : 'var(--color-ok)' }}>
                  {status?.snapshot?.runtime?.capital_actions_enabled === 'true' ? '잠금 해제 (GATES OPEN)' : '안전 잠금 (GATES SECURED)'}
                </strong>
              </div>
            </div>
          </section>

          <section style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: 0, marginBottom: '1.2rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.6rem' }}>
              ⌨️ 지원되는 CLI 원격 명령
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {(status?.snapshot?.supported_commands ?? []).map(cmd => (
                <span key={cmd} style={{
                  fontSize: '0.7rem',
                  padding: '0.15rem 0.45rem',
                  background: 'var(--color-surface-lighter)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '4px',
                  fontFamily: 'monospace'
                }}>
                  {cmd}
                </span>
              ))}
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}
