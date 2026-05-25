import { useCallback, useEffect, useRef, useState } from 'react'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

type JobStatus = 'running' | 'completed' | 'failed' | 'stopped' | 'error'

type Job = {
  id: string
  source: string
  label: string
  started_at: string
  status: JobStatus
  pid: number
  dry_run: boolean
  finished_at: string | null
  exit_code: number | null
  log_tail: string[]
  log_total: number
}

type Signal = {
  id: number
  source: string
  status: string
  ingested_at: string
  title: string
  url: string | null
  query: string | null
}

type SignalsResponse = {
  total: number
  limit: number
  offset: number
  items: Signal[]
}

const SOURCES = [
  { id: 'scholar', label: 'Semantic Scholar', type: 'Academic', icon: '🎓' },
  { id: 'arxiv', label: 'arXiv', type: 'Academic', icon: '📄' },
  { id: 'youtube', label: 'YouTube', type: 'Video', icon: '▶' },
  { id: 'rss', label: 'RSS', type: 'News', icon: '📡' },
  { id: 'filter', label: 'AI 필터링', type: 'Process', icon: '🔍' },
]

const STATUS_COLOR: Record<string, string> = {
  running: 'var(--color-accent)',
  completed: 'var(--color-ok)',
  failed: 'var(--color-danger)',
  stopped: 'var(--color-text-muted)',
  error: 'var(--color-danger)',
}

const STATUS_LABEL: Record<string, string> = {
  running: '실행 중',
  completed: '완료',
  failed: '실패',
  stopped: '중지됨',
  error: '오류',
}

const SIGNAL_STATUS_OPTIONS = [
  { value: '', label: '전체 상태' },
  { value: 'filtered_pass', label: '통과 (Pass)' },
  { value: 'filtered_fail', label: '탈락 (Fail)' },
  { value: 'pending', label: '대기 (Pending)' },
]

function elapsed(startedAt: string) {
  const ms = Date.now() - new Date(startedAt).getTime()
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}초`
  if (s < 3600) return `${Math.floor(s / 60)}분 ${s % 60}초`
  return `${Math.floor(s / 3600)}시간 ${Math.floor((s % 3600) / 60)}분`
}

function relTime(iso: string) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000) return '방금'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}시간 전`
  return `${Math.floor(diff / 86_400_000)}일 전`
}

export function PipelinePage({ apiBase, authHeaders }: Props) {
  const [tab, setTab] = useState<'control' | 'raw'>('control')
  const [jobs, setJobs] = useState<Job[]>([])
  const [expandedJob, setExpandedJob] = useState<string | null>(null)
  const [launching, setLaunching] = useState<string | null>(null)
  const [dryRun, setDryRun] = useState(false)
  const [signals, setSignals] = useState<SignalsResponse | null>(null)
  const [sigFilter, setSigFilter] = useState({ source: '', status: '', q: '' })
  const [sigOffset, setSigOffset] = useState(0)
  const [sigLoading, setSigLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/pipeline/status`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setJobs(data.jobs ?? [])
    } catch {}
  }, [apiBase, authHeaders])

  // 실행 중인 job이 있으면 3초, 없으면 15초마다 폴링
  useEffect(() => {
    fetchStatus()
    const tick = () => {
      fetchStatus()
      const hasRunning = jobs.some(j => j.status === 'running')
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(fetchStatus, hasRunning ? 3000 : 15000)
    }
    tick()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [jobs.some(j => j.status === 'running')])

  // 로그 자동 스크롤
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [jobs])

  const runJob = async (source: string) => {
    setLaunching(source)
    try {
      const res = await fetch(`${apiBase}/api/pipeline/run`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, dry_run: dryRun }),
      })
      const data = await res.json()
      if (!res.ok) {
        alert(data.detail ?? '실행 실패')
        return
      }
      setExpandedJob(data.job_id)
      await fetchStatus()
    } catch (e) {
      alert(`실행 오류: ${e}`)
    } finally {
      setLaunching(null)
    }
  }

  const stopJob = async (jobId: string) => {
    await fetch(`${apiBase}/api/pipeline/stop/${jobId}`, { method: 'POST', headers: authHeaders() })
    await fetchStatus()
  }

  const fetchSignals = useCallback(async (offset = 0) => {
    setSigLoading(true)
    try {
      const params = new URLSearchParams({ limit: '50', offset: String(offset) })
      if (sigFilter.source) params.set('source', sigFilter.source)
      if (sigFilter.status) params.set('status', sigFilter.status)
      if (sigFilter.q) params.set('q', sigFilter.q)
      const res = await fetch(`${apiBase}/api/pipeline/signals?${params}`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setSignals(data)
      setSigOffset(offset)
    } catch {} finally {
      setSigLoading(false)
    }
  }, [apiBase, authHeaders, sigFilter])

  useEffect(() => {
    if (tab === 'raw') fetchSignals(0)
  }, [tab, sigFilter])

  const runningJobs = jobs.filter(j => j.status === 'running')
  const recentJobs = jobs.filter(j => j.status !== 'running').slice(0, 10)

  return (
    <div style={{ padding: '1.5rem', maxWidth: 1400, margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800 }}>파이프라인 제어 센터</h2>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            데이터 수집 · 필터링 · 분류 전 과정을 실시간으로 관찰하고 제어합니다
          </p>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
          Dry-run 모드 (실제 저장 안 함)
        </label>
      </div>

      {/* 탭 */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0' }}>
        {[
          { key: 'control', label: '제어판' },
          { key: 'raw', label: `원본 데이터 ${signals ? `(${signals.total.toLocaleString('ko-KR')}건)` : ''}` },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as 'control' | 'raw')} style={{
            padding: '0.5rem 1rem',
            border: 'none',
            borderBottom: tab === t.key ? '2px solid var(--color-accent)' : '2px solid transparent',
            background: 'transparent',
            color: tab === t.key ? 'var(--color-accent)' : 'var(--color-text-muted)',
            fontWeight: tab === t.key ? 700 : 500,
            fontSize: '0.9rem',
            cursor: 'pointer',
            marginBottom: -1,
          }}>{t.label}</button>
        ))}
      </div>

      {tab === 'control' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {/* ── 지금 실행 중 ── */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              {runningJobs.length > 0 && (
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-accent)', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
              )}
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>
                지금 실행 중 ({runningJobs.length}건)
              </h3>
            </div>

            {runningJobs.length === 0 ? (
              <div className="panel" style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
                실행 중인 작업 없음 — 아래에서 소스를 선택해 실행하세요
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {runningJobs.map(job => (
                  <JobCard key={job.id} job={job} expanded={expandedJob === job.id}
                    onExpand={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                    onStop={() => stopJob(job.id)}
                    logEndRef={logEndRef} />
                ))}
              </div>
            )}
          </div>

          {/* ── 소스별 실행 제어 ── */}
          <div>
            <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>
              소스별 실행
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
              {SOURCES.map(src => {
                const isRunning = runningJobs.some(j => j.source === src.id)
                const isLaunching = launching === src.id
                return (
                  <div key={src.id} className="panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span style={{ fontSize: '1.1rem' }}>{src.icon}</span>
                          <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{src.label}</span>
                        </div>
                        <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{src.type}</span>
                      </div>
                      {isRunning && (
                        <span style={{ fontSize: '0.72rem', color: 'var(--color-accent)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <span className="spinner" style={{ width: 10, height: 10, margin: 0 }} />실행 중
                        </span>
                      )}
                    </div>
                    <button
                      disabled={isRunning || isLaunching !== null}
                      onClick={() => runJob(src.id)}
                      style={{
                        padding: '0.55rem 0',
                        borderRadius: '6px',
                        border: 'none',
                        background: isRunning ? 'var(--color-surface-lighter)' : 'var(--color-accent)',
                        color: isRunning ? 'var(--color-text-muted)' : '#fff',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                        cursor: isRunning ? 'not-allowed' : 'pointer',
                        opacity: isLaunching && !isRunning ? 0.6 : 1,
                        transition: 'all 0.15s',
                      }}
                    >
                      {isLaunching === src.id ? '시작 중...' : isRunning ? '이미 실행 중' : dryRun ? '▶ 테스트 실행' : '▶ 실행'}
                    </button>
                  </div>
                )
              })}
              {/* 전체 실행 */}
              <div className="panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', border: '1px solid var(--color-accent)', opacity: 0.85 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>🚀 전체 수집 + 필터</div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>All Sources</span>
                </div>
                <button
                  disabled={runningJobs.length > 0}
                  onClick={() => runJob('all')}
                  style={{
                    padding: '0.55rem 0',
                    borderRadius: '6px',
                    border: '1.5px solid var(--color-accent)',
                    background: 'transparent',
                    color: 'var(--color-accent)',
                    fontWeight: 700,
                    fontSize: '0.82rem',
                    cursor: runningJobs.length > 0 ? 'not-allowed' : 'pointer',
                    opacity: runningJobs.length > 0 ? 0.5 : 1,
                  }}
                >
                  {runningJobs.length > 0 ? '다른 작업 실행 중' : dryRun ? '▶ 전체 테스트' : '▶ 전체 실행'}
                </button>
              </div>
            </div>
          </div>

          {/* ── 최근 실행 이력 ── */}
          {recentJobs.length > 0 && (
            <div>
              <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>
                최근 실행 이력
              </h3>
              <div className="panel" style={{ padding: '0' }}>
                {recentJobs.map((job, idx) => (
                  <div key={job.id} onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                    style={{
                      display: 'grid', gridTemplateColumns: '1fr auto auto auto',
                      gap: '1rem', alignItems: 'center',
                      padding: '0.75rem 1.25rem',
                      borderBottom: idx < recentJobs.length - 1 ? '1px solid var(--color-border)' : 'none',
                      cursor: 'pointer',
                    }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{job.label ?? job.source}</span>
                      {job.dry_run && <span style={{ marginLeft: '0.4rem', fontSize: '0.7rem', color: 'var(--color-text-muted)', border: '1px solid var(--color-border)', borderRadius: 4, padding: '0.05rem 0.3rem' }}>dry-run</span>}
                    </div>
                    <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                      {job.log_total}줄 로그
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                      {job.finished_at ? relTime(job.finished_at) : relTime(job.started_at)}
                    </span>
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: STATUS_COLOR[job.status] ?? 'var(--color-text-muted)' }}>
                      {STATUS_LABEL[job.status] ?? job.status}
                      {job.exit_code != null && job.exit_code !== 0 && ` (code ${job.exit_code})`}
                    </span>
                  </div>
                ))}
              </div>
              {/* 확장된 로그 */}
              {recentJobs.filter(j => j.id === expandedJob).map(job => (
                <div key={`log-${job.id}`} className="panel" style={{ marginTop: '0.5rem', padding: '1rem', background: 'var(--color-surface)' }}>
                  <LogViewer job={job} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'raw' && (
        <div>
          {/* 필터 바 */}
          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <select
              value={sigFilter.source}
              onChange={e => setSigFilter(f => ({ ...f, source: e.target.value }))}
              style={selectStyle}
            >
              <option value="">전체 소스</option>
              <option value="semantic_scholar">Semantic Scholar</option>
              <option value="arxiv">arXiv</option>
              <option value="youtube">YouTube</option>
              <option value="rss">RSS</option>
            </select>
            <select
              value={sigFilter.status}
              onChange={e => setSigFilter(f => ({ ...f, status: e.target.value }))}
              style={selectStyle}
            >
              {SIGNAL_STATUS_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="제목 검색..."
              value={sigFilter.q}
              onChange={e => setSigFilter(f => ({ ...f, q: e.target.value }))}
              style={{ ...selectStyle, flex: 1, minWidth: 200 }}
            />
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
              총 {signals?.total.toLocaleString('ko-KR') ?? '—'}건
            </span>
          </div>

          {/* 테이블 */}
          <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface-lighter)' }}>
                    {['소스', '제목', '검색어', '상태', '수집 시간'].map(h => (
                      <th key={h} style={{ padding: '0.6rem 1rem', textAlign: 'left', fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sigLoading ? (
                    <tr><td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>로딩 중...</td></tr>
                  ) : signals?.items.length === 0 ? (
                    <tr><td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>결과 없음</td></tr>
                  ) : signals?.items.map((sig, idx) => (
                    <tr key={sig.id} style={{ borderBottom: '1px solid var(--color-border)', background: idx % 2 === 0 ? 'transparent' : 'color-mix(in srgb, var(--color-surface-lighter) 40%, transparent)' }}>
                      <td style={{ padding: '0.6rem 1rem', whiteSpace: 'nowrap', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                        {sig.source.replace('semantic_', '').replace('_api', '')}
                      </td>
                      <td style={{ padding: '0.6rem 1rem', maxWidth: 480 }}>
                        {sig.url ? (
                          <a href={sig.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-accent)', textDecoration: 'none', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {sig.title}
                          </a>
                        ) : (
                          <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sig.title}</span>
                        )}
                      </td>
                      <td style={{ padding: '0.6rem 1rem', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-muted)' }}>
                        {sig.query ?? '—'}
                      </td>
                      <td style={{ padding: '0.6rem 1rem', whiteSpace: 'nowrap' }}>
                        <span style={{
                          fontSize: '0.72rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: 4,
                          background: sig.status === 'filtered_pass' ? 'color-mix(in srgb, var(--color-ok) 15%, transparent)'
                            : sig.status === 'filtered_fail' ? 'color-mix(in srgb, var(--color-text-muted) 15%, transparent)'
                            : 'color-mix(in srgb, var(--color-warn) 15%, transparent)',
                          color: sig.status === 'filtered_pass' ? 'var(--color-ok)'
                            : sig.status === 'filtered_fail' ? 'var(--color-text-muted)'
                            : 'var(--color-warn)',
                        }}>
                          {sig.status === 'filtered_pass' ? 'Pass' : sig.status === 'filtered_fail' ? 'Fail' : 'Pending'}
                        </span>
                      </td>
                      <td style={{ padding: '0.6rem 1rem', whiteSpace: 'nowrap', color: 'var(--color-text-muted)' }}>
                        {relTime(sig.ingested_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* 페이지네이션 */}
            {signals && signals.total > signals.limit && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', borderTop: '1px solid var(--color-border)' }}>
                <button disabled={sigOffset === 0} onClick={() => fetchSignals(Math.max(0, sigOffset - 50))} style={btnStyle}>← 이전</button>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                  {sigOffset + 1}–{Math.min(sigOffset + 50, signals.total)} / {signals.total.toLocaleString('ko-KR')}건
                </span>
                <button disabled={sigOffset + 50 >= signals.total} onClick={() => fetchSignals(sigOffset + 50)} style={btnStyle}>다음 →</button>
              </div>
            )}
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.3; } }
      `}</style>
    </div>
  )
}

function JobCard({ job, expanded, onExpand, onStop, logEndRef }: {
  job: Job; expanded: boolean
  onExpand: () => void; onStop: () => void
  logEndRef: React.RefObject<HTMLDivElement>
}) {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="panel" style={{ padding: '1.25rem', border: `1.5px solid var(--color-accent)` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: expanded ? '1rem' : 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="spinner" style={{ width: 14, height: 14, margin: 0 }} />
          <div>
            <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{job.label ?? job.source}</span>
            <span style={{ marginLeft: '0.75rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
              {elapsed(job.started_at)} 경과 · PID {job.pid} · {job.log_total}줄
            </span>
            {job.dry_run && <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', color: 'var(--color-warn)', border: '1px solid var(--color-warn)', borderRadius: 4, padding: '0.05rem 0.3rem' }}>dry-run</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={onExpand} style={{ ...btnStyle, fontSize: '0.78rem' }}>
            {expanded ? '로그 접기' : '로그 보기'}
          </button>
          <button onClick={onStop} style={{ ...btnStyle, color: 'var(--color-danger)', borderColor: 'var(--color-danger)', fontSize: '0.78rem' }}>
            중지
          </button>
        </div>
      </div>
      {expanded && <LogViewer job={job} logEndRef={logEndRef} />}
    </div>
  )
}

function LogViewer({ job, logEndRef }: { job: Job; logEndRef?: React.RefObject<HTMLDivElement> }) {
  return (
    <div style={{
      background: '#0d1117', borderRadius: 6, padding: '0.75rem 1rem',
      fontFamily: 'monospace', fontSize: '0.75rem', lineHeight: 1.6,
      maxHeight: 320, overflowY: 'auto', color: '#e6edf3',
    }}>
      {job.log_tail.length === 0 ? (
        <span style={{ color: '#6e7681' }}>로그 대기 중...</span>
      ) : job.log_tail.map((line, i) => (
        <div key={i} style={{
          color: line.includes('[ERROR]') || line.includes('Error') ? '#ff6b6b'
            : line.includes('[완료]') || line.includes('완료') || line.includes('success') ? '#3fb950'
            : line.includes('[시작]') || line.includes('INFO') ? '#79c0ff'
            : '#e6edf3',
          whiteSpace: 'pre-wrap', wordBreak: 'break-all',
        }}>
          {line || ' '}
        </div>
      ))}
      <div ref={logEndRef} />
    </div>
  )
}

const selectStyle: React.CSSProperties = {
  padding: '0.45rem 0.75rem',
  borderRadius: 6,
  border: '1px solid var(--color-border)',
  background: 'var(--color-surface-lighter)',
  color: 'var(--color-text)',
  fontSize: '0.82rem',
  outline: 'none',
}

const btnStyle: React.CSSProperties = {
  padding: '0.35rem 0.75rem',
  borderRadius: 6,
  border: '1px solid var(--color-border)',
  background: 'transparent',
  color: 'var(--color-text-muted)',
  fontSize: '0.8rem',
  cursor: 'pointer',
}
