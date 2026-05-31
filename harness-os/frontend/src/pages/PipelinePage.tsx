import { useCallback, useEffect, useRef, useState } from 'react'
import { DataCollectionMonitor } from '../components/DataCollectionMonitor'
import type { ScheduleService } from '../components/DataCollectionMonitor'
import type { DashboardPayload } from '../components/types'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  monitor?: DashboardPayload['data_collection_monitor']
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
  topic?: string
  new_count?: number
}

type Signal = {
  id: number
  source: string
  status: string
  ingested_at: string
  title: string
  url: string | null
  query: string | null
  tier2_score?: number | null
  tier2_reason?: string | null
  tier2_insight?: string | null
  tier2_category?: string | null
}

type SignalsResponse = {
  total: number
  limit: number
  offset: number
  items: Signal[]
}

type CustomQuery = {
  text: string
  targets: string[]
  added_at: string
}

type SourceStat = {
  count: number
  last_at: string | null
}

// 프리셋 주제 (CEO가 바로 클릭 가능)
const PRESET_TOPICS = [
  'AI 교육 학부모 불안',
  'ChatGPT 학생 학습 의존',
  '생성형 AI 초등 중등 교육',
  'AI 대체 직업 불안 심리',
  '디지털 리터러시 자녀 교육',
  '인공지능 사교육 학원',
  'AI 교육격차 디지털 불평등',
  '메타인지 AI 비판적 사고',
]

const SOURCE_DEFS = [
  {
    id: 'scholar',
    label: 'Semantic Scholar',
    icon: '🎓',
    type: 'ACADEMIC',
    desc: '학술 논문 데이터베이스',
    match: (s: string) => s.toLowerCase().includes('scholar'),
  },
  {
    id: 'arxiv',
    label: 'arXiv',
    icon: '📄',
    type: 'ACADEMIC',
    desc: '프리프린트 논문 서버',
    match: (s: string) => s.toLowerCase().startsWith('arxiv') || s.toLowerCase() === 'arxiv_api',
  },
  {
    id: 'youtube',
    label: 'YouTube',
    icon: '▶',
    type: 'VIDEO',
    desc: '영상 콘텐츠 수집',
    match: (s: string) => s.toLowerCase().startsWith('youtube'),
  },
  {
    id: 'rss',
    label: 'RSS / 뉴스',
    icon: '📡',
    type: 'NEWS',
    desc: 'EdSurge, IEEE 등 뉴스피드',
    match: (s: string) => !s.toLowerCase().includes('scholar') && !s.toLowerCase().startsWith('arxiv') && !s.toLowerCase().startsWith('youtube'),
  },
  {
    id: 'filter',
    label: '투자 신호 정제',
    icon: '📈',
    type: '일봉 분석',
    desc: '종목 후보와 매수·매도 점검 시점을 정리',
    match: () => false,
  },
]



function elapsed(startedAt: string) {
  const ms = Date.now() - new Date(startedAt).getTime()
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}초`
  if (s < 3600) return `${Math.floor(s / 60)}분 ${s % 60}초`
  return `${Math.floor(s / 3600)}시간 ${Math.floor((s % 3600) / 60)}분`
}

function relTime(iso: string | null) {
  if (!iso) return '미실행'
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000) return '방금'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}시간 전`
  return `${Math.floor(diff / 86_400_000)}일 전`
}

function colorLine(line: string): string {
  if (line.includes('ERROR') || line.includes('error')) return 'var(--color-danger)'
  if (line.includes('WARN') || line.includes('warning')) return 'var(--color-warn)'
  if (line.includes('[dry-run]')) return 'var(--color-accent)'
  if (line.includes('새로 저장') || line.includes('new=') || line.includes('INFO')) return 'var(--color-text)'
  return 'var(--color-text-muted)'
}

export function PipelinePage({ apiBase, authHeaders, monitor }: Props) {
  type Tab = 'status' | 'topics' | 'raw'
  const [tab, setTab] = useState<Tab>('status')
  const [jobs, setJobs] = useState<Job[]>([])
  const [sourceStats, setSourceStats] = useState<Record<string, SourceStat>>({})
  const [customQueries, setCustomQueries] = useState<CustomQuery[]>([])
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())
  const [launching, setLaunching] = useState<string | null>(null)
  const [dryRun, setDryRun] = useState(false)
  const [selectedTopic, setSelectedTopic] = useState('')
  const [customTopicInput, setCustomTopicInput] = useState('')
  const [topicMode, setTopicMode] = useState<'preset' | 'custom'>('preset')
  const [maxRssItems, setMaxRssItems] = useState(50)
  const [scholarMode, setScholarMode] = useState<'en_only' | 'multilingual'>('en_only')

  // 2026 AI launchd 데몬 모니터링 상태
  type DaemonStatus = {
    label: string
    is_active: boolean
    pid: number | null
    last_exit_code: number | null
    last_run_time: string | null
    last_collected_count: number
    db_count_today: number
    db_count_total: number
    latest_logs: string[]
    interval_hours: number
  }
  const [daemonStatus, setDaemonStatus] = useState<DaemonStatus | null>(null)
  const [daemonLoading, setDaemonLoading] = useState(false)
  const [scheduleServices, setScheduleServices] = useState<ScheduleService[]>([])

  // 최근 실행 이력용 검색 및 지능형 필터 상태
  const [historySearch, setHistorySearch] = useState('')
  const [historySourceFilter, setHistorySourceFilter] = useState('')
  const [historyStatusFilter, setHistoryStatusFilter] = useState('')
  const [historyPeriodFilter, setHistoryPeriodFilter] = useState('all')

  // 연구 주제 관리 탭 상태
  const [newQuery, setNewQuery] = useState('')
  const [addingQuery, setAddingQuery] = useState(false)

  // 수집 데이터 탭 상태
  const [signals, setSignals] = useState<SignalsResponse | null>(null)
  const [sigFilter, setSigFilter] = useState({ source: '', status: '', q: '' })
  const [sigOffset, setSigOffset] = useState(0)
  const [sigLoading, setSigLoading] = useState(false)

  const jobsRef = useRef<Job[]>([])
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => { jobsRef.current = jobs }, [jobs])

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/pipeline/status`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setJobs(data.jobs ?? [])
    } catch (err) {
      void err
    }
  }, [apiBase, authHeaders])

  const fetchSourceStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/pipeline/source-stats`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setSourceStats(data.stats ?? {})
    } catch (err) {
      void err
    }
  }, [apiBase, authHeaders])

  const fetchQueries = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/pipeline/queries`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setCustomQueries(data.queries ?? [])
    } catch (err) {
      void err
    }
  }, [apiBase, authHeaders])

  const fetchSignals = useCallback(async (offset = 0) => {
    setSigLoading(true)
    try {
      const params = new URLSearchParams({ limit: '50', offset: String(offset) })
      if (sigFilter.source) params.set('source', sigFilter.source)
      if (sigFilter.status) params.set('status', sigFilter.status)
      if (sigFilter.q) params.set('q', sigFilter.q)
      const res = await fetch(`${apiBase}/api/pipeline/signals?${params}`, { headers: authHeaders() })
      if (!res.ok) return
      setSignals(await res.json())
      setSigOffset(offset)
    } catch (err) {
      void err
    } finally {
      setSigLoading(false)
    }
  }, [apiBase, authHeaders, sigFilter])

  const fetchDaemonStatus = useCallback(async () => {
    setDaemonLoading(true)
    try {
      const res = await fetch(`${apiBase}/api/pipeline/daemon/status`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setDaemonStatus(data)
    } catch (err) {
      void err
    } finally {
      setDaemonLoading(false)
    }
  }, [apiBase, authHeaders])

  const fetchScheduleStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/pipeline/schedule-status`, { headers: authHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setScheduleServices(data.services ?? [])
    } catch (err) {
      void err
    }
  }, [apiBase, authHeaders])

  // 폴링 설정 (stale closure 방지: jobsRef 사용)
  const resetPoll = useCallback((fast: boolean) => {
    if (pollRef.current) clearInterval(pollRef.current)
    const intervalMs = fast ? 2000 : 15000
    pollRef.current = setInterval(async () => {
      await fetchStatus()
      await fetchDaemonStatus()
      await fetchScheduleStatus()
      const nowRunning = jobsRef.current.some(j => j.status === 'running')
      if (!nowRunning && fast) {
        if (pollRef.current) clearInterval(pollRef.current)
        pollRef.current = setInterval(async () => {
          await fetchStatus()
          await fetchDaemonStatus()
          await fetchScheduleStatus()
        }, 15000)
        fetchSourceStats()
      }
    }, intervalMs)
  }, [fetchStatus, fetchSourceStats, fetchDaemonStatus, fetchScheduleStatus])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchStatus()
      void fetchSourceStats()
      void fetchQueries()
      void fetchDaemonStatus()
      void fetchScheduleStatus()
      resetPoll(false)
    }, 0)
    return () => {
      window.clearTimeout(timer)
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (tab === 'raw') void fetchSignals(0)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [tab, sigFilter])

  const runJob = async (source: string) => {
    if (launching !== null) return
    const topic = topicMode === 'custom' ? customTopicInput.trim() : selectedTopic
    setLaunching(source)
    try {
      const res = await fetch(`${apiBase}/api/pipeline/run`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, dry_run: dryRun, topic, topic_only: topicMode === 'custom' && !!topic, max_rss_items: maxRssItems, scholar_mode: scholarMode }),
      })
      const data = await res.json()
      if (!res.ok) {
        alert(data.detail ?? '실행 실패')
        return
      }
      // 새 잡을 바로 펼쳐서 로그 보이게
      setExpandedJobs(prev => new Set([...prev, data.job_id]))
      resetPoll(true)
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

  const addQuery = async () => {
    if (!newQuery.trim()) return
    setAddingQuery(true)
    try {
      const res = await fetch(`${apiBase}/api/pipeline/queries`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: newQuery.trim(), targets: ['scholar', 'arxiv'] }),
      })
      if (res.ok) { setNewQuery(''); await fetchQueries() }
    } catch (err) {
      void err
    } finally { setAddingQuery(false) }
  }

  const deleteQuery = async (idx: number) => {
    await fetch(`${apiBase}/api/pipeline/queries/${idx}`, { method: 'DELETE', headers: authHeaders() })
    await fetchQueries()
  }

  // 소스별 DB 건수 집계
  const getSourceStat = (srcId: string) => {
    const def = SOURCE_DEFS.find(s => s.id === srcId)
    if (!def || srcId === 'filter') return { count: 0, last_at: null }
    let count = 0; let last_at: string | null = null
    for (const [key, val] of Object.entries(sourceStats)) {
      if (def.match(key)) {
        count += val.count
        if (val.last_at && (!last_at || val.last_at > last_at)) last_at = val.last_at
      }
    }
    return { count, last_at }
  }

  const runningJobs = jobs.filter(j => j.status === 'running')
  const recentJobs = jobs.filter(j => j.status !== 'running')

  // CEO 1-클릭 실물 데이터 바로가기 연동
  const viewIngestedData = (jobSource: string, jobTopic: string | undefined) => {
    let srcVal = ''
    const s = jobSource.toLowerCase()
    if (s.includes('scholar')) srcVal = 'semantic_scholar'
    else if (s.startsWith('arxiv')) srcVal = 'arxiv_api'
    else if (s.startsWith('youtube')) srcVal = 'youtube'
    else if (s.startsWith('rss')) srcVal = 'rss'

    setSigFilter({
      source: srcVal,
      status: '',
      q: jobTopic && jobTopic !== '기본 쿼리 수집' ? jobTopic : '',
    })
    setTab('raw')
  }

  // 지능형 상황 요약 (Intelligent Natural Language Summary)
  const generateSmartSummary = (job: Job) => {
    const logStr = job.log_tail.join('\n')
    
    if (job.status === 'failed' || job.status === 'error') {
      if (logStr.includes('429') || logStr.includes('Too Many Requests')) {
        return {
          text: '구글/유튜브 차단(429 Too Many Requests)으로 인해 수집 중단. yt-dlp 우회 가동 필요.',
          type: 'danger'
        }
      }
      if (logStr.includes('Quota Exceeded') || logStr.includes('quota')) {
        return {
          text: '유튜브 API 일일 할당량(Quota) 초과. yt-dlp 예비 수집 기동 권장.',
          type: 'danger'
        }
      }
      return {
        text: '수집 도중 치명적 시스템 오류 발생. 상세 개발 로그를 검토해주십시오.',
        type: 'danger'
      }
    }
    
    if (job.status === 'stopped') {
      return {
        text: '사용자 명령 또는 관리자에 의해 수집 프로세스가 강제 중지되었습니다.',
        type: 'warn'
      }
    }

    const hasSubtitleBypass = logStr.includes('자막 없음') || logStr.includes('설명글') || logStr.includes('description')
    const has429Bypass = logStr.includes('yt-dlp 우회') || logStr.includes('429 우회')
    const noChannel = logStr.includes('채널 없음') || logStr.includes('WARNING |   채널 없음')
    
    if (job.new_count && job.new_count > 0) {
      let warnDetails = []
      if (hasSubtitleBypass) warnDetails.push('자막 유실로 설명글 대체 수집')
      if (has429Bypass) warnDetails.push('yt-dlp 429 우회 통로 개척')
      if (noChannel) warnDetails.push('일부 타깃 채널 실종 경고')
      
      return {
        text: `주제에 맞는 신규 실물 영상 및 자료 ${job.new_count}건을 무결 적재 완료했습니다.` + 
              (warnDetails.length > 0 ? ` (⚠️ ${warnDetails.join(', ')})` : ''),
        type: warnDetails.length > 0 ? 'warn' : 'success'
      }
    } else {
      if (logStr.includes('완료: 0개 신규') || logStr.includes('0개 신규') || logStr.includes('already exists')) {
        return {
          text: '모든 자료가 이미 최신 상태(Up-to-date)로 중복 없는 완벽한 아카이브 상태를 유지하고 있습니다.',
          type: 'info'
        }
      }
      return {
        text: '수집 사이클이 정상 수행되었으나, 이 주제로 새로 발표되거나 적재할 신규 신호는 검출되지 않았습니다.',
        type: 'info'
      }
    }
  }

  // 지능형 검색 필터 적용
  const filteredRecentJobs = recentJobs.filter(job => {
    // 1. 검색어 필터 (주제, 소스, 라벨 등)
    if (historySearch.trim()) {
      const q = historySearch.toLowerCase()
      const matchesTopic = job.topic ? job.topic.toLowerCase().includes(q) : false
      const matchesSource = job.source.toLowerCase().includes(q)
      const matchesLabel = job.label ? job.label.toLowerCase().includes(q) : false
      if (!matchesTopic && !matchesSource && !matchesLabel) return false
    }
    
    // 2. 소스 필터
    if (historySourceFilter) {
      if (job.source !== historySourceFilter) return false
    }
    
    // 3. 성과/상태 필터
    if (historyStatusFilter) {
      if (historyStatusFilter === 'has_new') {
        if (!job.new_count || job.new_count === 0) return false
      } else if (historyStatusFilter === 'completed') {
        if (job.status !== 'completed') return false
      } else if (historyStatusFilter === 'failed') {
        if (job.status !== 'failed' && job.status !== 'error') return false
      }
    }
    
    // 4. 기간 필터
    if (historyPeriodFilter && historyPeriodFilter !== 'all') {
      const jobTime = new Date(job.started_at).getTime()
      const now = Date.now()
      if (historyPeriodFilter === 'today') {
        const todayStart = new Date().setHours(0,0,0,0)
        if (jobTime < todayStart) return false
      } else if (historyPeriodFilter === 'week') {
        const weekAgo = now - 7 * 24 * 60 * 60 * 1000
        if (jobTime < weekAgo) return false
      } else if (historyPeriodFilter === 'month') {
        const monthAgo = now - 30 * 24 * 60 * 60 * 1000
        if (jobTime < monthAgo) return false
      }
    }
    
    return true
  })

  const effectiveTopic = topicMode === 'custom' ? customTopicInput.trim() : selectedTopic

  return (
    <div style={{ padding: '1.5rem', maxWidth: 1400, margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800 }}>자료수집 제어 센터</h2>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            원천 자료 수집과 일봉 기준 투자 후보 정제를 실행합니다.
          </p>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)', cursor: 'pointer', userSelect: 'none' }}>
          <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
          테스트 실행 모드 (실제 저장 안 함)
        </label>
      </div>

      {/* 탭 */}
      <div style={{ display: 'flex', gap: 0, marginBottom: '1.5rem', borderBottom: '1px solid var(--color-border)' }}>
        {([
          { key: 'status', label: '수집 현황' },
          { key: 'topics', label: `연구 주제 관리 ${customQueries.length > 0 ? `(${customQueries.length})` : ''}` },
          { key: 'raw', label: `수집 데이터 ${signals ? `(${signals.total.toLocaleString('ko-KR')}건)` : ''}` },
        ] as const).map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '0.6rem 1.25rem',
            border: 'none',
            borderBottom: tab === t.key ? '2px solid var(--color-accent)' : '2px solid transparent',
            background: 'transparent',
            color: tab === t.key ? 'var(--color-accent)' : 'var(--color-text-muted)',
            fontWeight: tab === t.key ? 700 : 500,
            fontSize: '0.88rem',
            cursor: 'pointer',
            marginBottom: -1,
          }}>{t.label}</button>
        ))}
      </div>

      {/* ── 수집 현황 탭 ── */}
      {tab === 'status' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* launchd 데몬 모니터링 섹션 카드 */}
          <div className="panel" style={{ padding: '1.25rem', border: '1px solid var(--color-border)', borderRadius: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span style={{ fontSize: '1.3rem' }}>📡</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 800 }}>
                    2026 AI 글로벌 대량 수집 자동화 데몬 (launchd)
                  </h3>
                  <p style={{ margin: '0.15rem 0 0', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                    6시간 주기 백그라운드 구동 · 상호 보완형 이중화 및 429 설명글 폴백 아키텍처 탑재
                  </p>
                </div>
              </div>
              
              {daemonStatus && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                    backgroundColor: daemonStatus.is_active ? 'var(--color-ok)' : 'var(--color-warn)',
                    boxShadow: daemonStatus.is_active ? '0 0 8px var(--color-ok)' : 'none',
                  }} />
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: daemonStatus.is_active ? 'var(--color-ok)' : 'var(--color-warn)' }}>
                    {daemonStatus.is_active ? '동작 중 (Active)' : '정지됨 (Inactive)'}
                  </span>
                  {daemonStatus.pid && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', background: 'var(--color-surface-lighter)', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>
                      PID: {daemonStatus.pid}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* 통계 카드 그리드 */}
            {daemonStatus && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.85rem', marginBottom: '1.25rem' }}>
                <div style={{ background: 'var(--color-surface-lighter)', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.3rem' }}>
                    오늘 적재 실적 (유튜브)
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-accent)' }}>
                      {daemonStatus.db_count_today.toLocaleString('ko-KR')}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>건 적재</span>
                  </div>
                </div>

                <div style={{ background: 'var(--color-surface-lighter)', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.3rem' }}>
                    2026 AI 누적 적재
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-text)' }}>
                      {daemonStatus.db_count_total.toLocaleString('ko-KR')}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>건 누적</span>
                  </div>
                </div>

                <div style={{ background: 'var(--color-surface-lighter)', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.3rem' }}>
                    최근 수집 성공 규모
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-ok)' }}>
                      +{daemonStatus.last_collected_count}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>개 신규 영상</span>
                  </div>
                </div>

                <div style={{ background: 'var(--color-surface-lighter)', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.3rem' }}>
                    마지막 백그라운드 동작
                  </div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-text)', marginTop: '0.2rem' }}>
                    {daemonStatus.last_run_time ? daemonStatus.last_run_time : '대기 중'}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', marginTop: '0.1rem' }}>
                    다음 주기: 6시간 간격 순환
                  </div>
                </div>
              </div>
            )}

            {/* 터미널 로그 */}
            {daemonStatus && daemonStatus.latest_logs && daemonStatus.latest_logs.length > 0 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-text)' }}>
                    📡 데몬 실시간 동작 로그 (최신 30줄)
                  </span>
                  <button onClick={fetchDaemonStatus} disabled={daemonLoading} style={{
                    background: 'transparent', border: 'none', color: 'var(--color-accent)',
                    fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                  }}>
                    {daemonLoading ? '갱신 중...' : '🔄 로그 새로고침'}
                  </button>
                </div>
                <div style={{
                  background: 'var(--color-bg-dark, #0d1117)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '6px',
                  padding: '0.65rem 0.85rem',
                  maxHeight: '180px',
                  overflowY: 'auto',
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  lineHeight: '1.4',
                  whiteSpace: 'pre-wrap',
                }}>
                  {daemonStatus.latest_logs.map((line, idx) => (
                    <div key={idx} style={{ color: colorLine(line), marginBottom: '0.2rem' }}>
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {monitor && <DataCollectionMonitor monitor={monitor} scheduleServices={scheduleServices} />}

          {/* 1단계: 연구 주제 선택 */}
          <div className="panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 22, height: 22, borderRadius: '50%',
                background: 'var(--color-accent)', color: '#fff',
                fontSize: '0.75rem', fontWeight: 800,
              }}>1</span>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700 }}>연구 주제 선택</h3>
              {effectiveTopic && (
                <span style={{ marginLeft: 'auto', fontSize: '0.78rem', color: 'var(--color-ok)', fontWeight: 600 }}>
                  ✓ 선택됨: "{effectiveTopic}"
                </span>
              )}
            </div>

            {/* 프리셋 / 직접입력 전환 */}
            <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.85rem' }}>
              <button onClick={() => setTopicMode('preset')} style={{
                padding: '0.3rem 0.8rem', borderRadius: '6px', border: '1px solid var(--color-border)',
                background: topicMode === 'preset' ? 'var(--color-accent)' : 'transparent',
                color: topicMode === 'preset' ? '#fff' : 'var(--color-text-muted)',
                fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
              }}>프리셋 주제</button>
              <button onClick={() => setTopicMode('custom')} style={{
                padding: '0.3rem 0.8rem', borderRadius: '6px', border: '1px solid var(--color-border)',
                background: topicMode === 'custom' ? 'var(--color-accent)' : 'transparent',
                color: topicMode === 'custom' ? '#fff' : 'var(--color-text-muted)',
                fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
              }}>직접 입력</button>
              {effectiveTopic && (
                <button onClick={() => { setSelectedTopic(''); setCustomTopicInput('') }} style={{
                  padding: '0.3rem 0.8rem', borderRadius: '6px', border: '1px solid var(--color-border)',
                  background: 'transparent', color: 'var(--color-text-muted)',
                  fontSize: '0.78rem', cursor: 'pointer', marginLeft: 'auto',
                }}>선택 해제</button>
              )}
            </div>

            {topicMode === 'preset' ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {[...PRESET_TOPICS, ...customQueries.map(q => q.text)].map(t => (
                  <button
                    key={t}
                    onClick={() => setSelectedTopic(selectedTopic === t ? '' : t)}
                    style={{
                      padding: '0.4rem 0.85rem', borderRadius: '20px',
                      border: selectedTopic === t ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
                      background: selectedTopic === t ? 'color-mix(in srgb, var(--color-accent) 12%, transparent)' : 'var(--color-surface-lighter)',
                      color: selectedTopic === t ? 'var(--color-accent)' : 'var(--color-text)',
                      fontSize: '0.82rem', fontWeight: selectedTopic === t ? 700 : 400,
                      cursor: 'pointer', transition: 'all 0.12s',
                    }}
                  >{t}</button>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input
                  type="text"
                  value={customTopicInput}
                  onChange={e => setCustomTopicInput(e.target.value)}
                  placeholder="예: AI 교육 학부모 불안 한국 초등학교"
                  style={{
                    flex: 1, padding: '0.65rem 0.9rem',
                    borderRadius: '8px', border: '1.5px solid var(--color-border)',
                    background: 'var(--color-surface-lighter)', color: 'var(--color-text)',
                    fontSize: '0.9rem', outline: 'none',
                  }}
                />
                <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                  입력 후 바로 실행 가능
                </span>
              </div>
            )}

            {!effectiveTopic && (
              <p style={{ margin: '0.75rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                💡 주제 없이 실행하면 기본 쿼리(AI literacy, cognitive offloading 등)로 수집합니다.
              </p>
            )}
          </div>

          {/* 1.5단계: 수집 설정 */}
          <div className="panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 22, height: 22, borderRadius: '50%',
                background: 'var(--color-accent)', color: '#fff',
                fontSize: '0.75rem', fontWeight: 800,
              }}>⚙</span>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700 }}>수집 설정</h3>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              {/* RSS 최대 항목 */}
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text)' }}>
                  RSS 소스당 최대 항목: <span style={{ color: 'var(--color-accent)', fontWeight: 800 }}>{maxRssItems}개</span>
                </label>
                <input
                  type="range"
                  min={10} max={200} step={10}
                  value={maxRssItems}
                  onChange={e => setMaxRssItems(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--color-accent)' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--color-text-muted)', marginTop: '0.2rem' }}>
                  <span>10개 (빠름)</span>
                  <span>200개 (느림)</span>
                </div>
                <p style={{ margin: '0.4rem 0 0', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  OpenAI Blog처럼 항목이 많은 소스를 제한합니다. 기본값 50 권장.
                </p>
              </div>
              {/* Scholar 모드 */}
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text)' }}>
                  Semantic Scholar 쿼리 모드
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {([
                    { value: 'en_only', label: '영어 핵심만 (빠름)', desc: '20개 쿼리 · 약 5~10분' },
                    { value: 'multilingual', label: '전체 다국어 (느림)', desc: '60개+ 쿼리 · 약 30분 · 429 위험' },
                  ] as const).map(opt => (
                    <label key={opt.value} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', cursor: 'pointer' }}>
                      <input
                        type="radio"
                        name="scholarMode"
                        value={opt.value}
                        checked={scholarMode === opt.value}
                        onChange={() => setScholarMode(opt.value)}
                        style={{ marginTop: '0.15rem', accentColor: 'var(--color-accent)' }}
                      />
                      <div>
                        <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>{opt.label}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{opt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 2단계: 소스별 실행 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 22, height: 22, borderRadius: '50%',
                background: 'var(--color-accent)', color: '#fff',
                fontSize: '0.75rem', fontWeight: 800,
              }}>2</span>
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700 }}>자료 출처 및 정제 작업 실행</h3>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
              {SOURCE_DEFS.map(src => {
                const stat = getSourceStat(src.id)
                const isRunning = runningJobs.some(j => j.source === src.id)
                const isLaunching = launching === src.id
                const neverRun = stat.count === 0 && stat.last_at === null && src.id !== 'filter'
                return (
                  <div key={src.id} className="panel" style={{
                    padding: '1rem',
                    border: isRunning ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                    display: 'flex', flexDirection: 'column', gap: '0.6rem',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.15rem' }}>
                          <span style={{ fontSize: '1.1rem' }}>{src.icon}</span>
                          <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>{src.label}</span>
                        </div>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{src.type}</span>
                      </div>
                      {isRunning && (
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-accent)', fontWeight: 700 }}>● 실행 중</span>
                      )}
                    </div>

                    {src.id !== 'filter' && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{
                          fontSize: '1.3rem', fontWeight: 800,
                          color: stat.count > 0 ? 'var(--color-text)' : 'var(--color-text-muted)',
                        }}>
                          {stat.count.toLocaleString('ko-KR')}건
                        </span>
                        <span style={{
                          fontSize: '0.72rem',
                          color: neverRun ? 'var(--color-warn)' : 'var(--color-text-muted)',
                          fontWeight: neverRun ? 600 : 400,
                        }}>
                          {neverRun ? '미실행' : relTime(stat.last_at)}
                        </span>
                      </div>
                    )}

                    <button
                      disabled={launching !== null || isRunning}
                      onClick={() => runJob(src.id)}
                      style={{
                        padding: '0.5rem 0', borderRadius: '6px', border: 'none',
                        background: isRunning
                          ? 'var(--color-surface-lighter)'
                          : launching !== null
                          ? 'var(--color-surface-lighter)'
                          : 'var(--color-accent)',
                        color: isRunning || launching !== null ? 'var(--color-text-muted)' : '#fff',
                        fontWeight: 700, fontSize: '0.82rem',
                        cursor: isRunning || launching !== null ? 'not-allowed' : 'pointer',
                        transition: 'all 0.15s',
                        opacity: isLaunching ? 0.7 : 1,
                      }}
                    >
                      {isLaunching ? '시작 중...' : isRunning ? '● 실행 중' : dryRun ? '▶ 테스트 실행' : '▶ 실행'}
                    </button>
                  </div>
                )
              })}

              {/* 전체 실행 카드 */}
              <div className="panel" style={{
                padding: '1rem',
                border: '1px solid var(--color-accent)',
                display: 'flex', flexDirection: 'column', gap: '0.6rem',
              }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: '0.15rem' }}>🚀 전체 수집</div>
                  <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>전체 자료 출처</span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                  뉴스 피드 + 논문 검색 + 동영상 자료를 함께 수집합니다. 투자 신호 정제는 별도 버튼으로 하루 1회 실행합니다.
                </div>
                <button
                  disabled={launching !== null || runningJobs.length > 0}
                  onClick={() => runJob('all')}
                  style={{
                    padding: '0.5rem 0', borderRadius: '6px',
                    border: '1.5px solid var(--color-accent)',
                    background: 'transparent', color: 'var(--color-accent)',
                    fontWeight: 700, fontSize: '0.82rem',
                    cursor: (launching !== null || runningJobs.length > 0) ? 'not-allowed' : 'pointer',
                    opacity: (launching !== null || runningJobs.length > 0) ? 0.5 : 1,
                  }}
                >
                  {runningJobs.length > 0 ? '실행 중...' : dryRun ? '▶ 전체 테스트' : '▶ 전체 실행'}
                </button>
              </div>
            </div>
          </div>

          {/* 지금 실행 중 — 로그 즉시 표시 */}
          {runningJobs.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-accent)', display: 'inline-block', animation: 'pulse 1.2s infinite' }} />
                <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>
                  실행 중 ({runningJobs.length}건)
                </h3>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {runningJobs.map(job => (
                  <JobPanel
                    key={job.id}
                    job={job}
                    expanded={expandedJobs.has(job.id)}
                    onToggle={() => setExpandedJobs(prev => {
                      const next = new Set(prev)
                      if (next.has(job.id)) next.delete(job.id)
                      else next.add(job.id)
                      return next
                    })}
                    onStop={() => stopJob(job.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* 최근 완료 이력 */}
          {recentJobs.length > 0 && (
            <div style={{ marginTop: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text)' }}>
                  지능형 수집 이력 및 성과 피드 (Timeline)
                </h3>
                <span style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
                  필터 결과: <strong>{filteredRecentJobs.length}건</strong> / 총 {recentJobs.length}건
                </span>
              </div>

              {/* 지능형 다차원 검색 필터바 */}
              <div className="panel" style={{ padding: '1rem', marginBottom: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {/* 1열: 검색어 입력 및 기간 선택 */}
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <div style={{ flex: 1, minWidth: '260px', position: 'relative' }}>
                    <input
                      type="text"
                      placeholder="🔍 수집 주제, 출처명, 키워드 검색..."
                      value={historySearch}
                      onChange={e => setHistorySearch(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.55rem 0.85rem',
                        borderRadius: '6px',
                        border: '1.5px solid var(--color-border)',
                        background: 'var(--color-surface-lighter)',
                        color: 'var(--color-text)',
                        fontSize: '0.85rem',
                        outline: 'none',
                        boxSizing: 'border-box'
                      }}
                    />
                    {historySearch && (
                      <button 
                        onClick={() => setHistorySearch('')}
                        style={{
                          position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                          background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.85rem'
                        }}
                      >
                        ✕
                      </button>
                    )}
                  </div>

                  <select
                    value={historyPeriodFilter}
                    onChange={e => setHistoryPeriodFilter(e.target.value)}
                    style={{
                      padding: '0.55rem 0.75rem',
                      borderRadius: '6px',
                      border: '1.5px solid var(--color-border)',
                      background: 'var(--color-surface-lighter)',
                      color: 'var(--color-text)',
                      fontSize: '0.85rem',
                      outline: 'none',
                      minWidth: '130px'
                    }}
                  >
                    <option value="all">🗓️ 전체 기간</option>
                    <option value="today">오늘 수집</option>
                    <option value="week">최근 7일</option>
                    <option value="month">최근 30일</option>
                  </select>
                </div>

                {/* 2열: 소스 퀵 필터 칩 */}
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginRight: '0.4rem' }}>자료 소스:</span>
                  {[
                    { id: '', label: '전체' },
                    { id: 'youtube', label: '🔴 YouTube' },
                    { id: 'scholar', label: '🎓 Scholar' },
                    { id: 'arxiv', label: '🔬 arXiv' },
                    { id: 'rss', label: '📡 RSS/뉴스' },
                    { id: 'filter', label: '📈 투자 분석' }
                  ].map(chip => (
                    <button
                      key={chip.id}
                      onClick={() => setHistorySourceFilter(chip.id)}
                      style={{
                        padding: '0.25rem 0.65rem',
                        borderRadius: '15px',
                        border: '1px solid',
                        borderColor: historySourceFilter === chip.id ? 'var(--color-accent)' : 'var(--color-border)',
                        background: historySourceFilter === chip.id ? 'rgba(0, 229, 153, 0.15)' : 'var(--color-surface-lighter)',
                        color: historySourceFilter === chip.id ? 'var(--color-accent)' : 'var(--color-text-muted)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>

                {/* 3열: 수집 성과/상황 퀵 필터 칩 */}
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginRight: '0.4rem' }}>수집 성과:</span>
                  {[
                    { id: '', label: '전체' },
                    { id: 'has_new', label: '📊 신규 적재 완료 건만' },
                    { id: 'completed', label: '✅ 정상 완료' },
                    { id: 'failed', label: '❌ 수집 오류/실패 건만' }
                  ].map(chip => (
                    <button
                      key={chip.id}
                      onClick={() => setHistoryStatusFilter(chip.id)}
                      style={{
                        padding: '0.25rem 0.65rem',
                        borderRadius: '15px',
                        border: '1px solid',
                        borderColor: historyStatusFilter === chip.id ? 'var(--color-accent)' : 'var(--color-border)',
                        background: historyStatusFilter === chip.id ? 'rgba(0, 229, 153, 0.15)' : 'var(--color-surface-lighter)',
                        color: historyStatusFilter === chip.id ? 'var(--color-accent)' : 'var(--color-text-muted)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 타임라인 피드 목록 */}
              {filteredRecentJobs.length === 0 ? (
                <div className="panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🔍</div>
                  <h4 style={{ margin: '0 0 0.25rem', color: 'var(--color-text)' }}>부합하는 수집 이력이 없습니다</h4>
                  <p style={{ margin: 0, fontSize: '0.8rem' }}>검색어나 필터 조건을 조정해 보십시오.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', position: 'relative', paddingLeft: '1.5rem' }}>
                  {/* 타임라인 수직선 */}
                  <div style={{
                    position: 'absolute', left: '7px', top: '10px', bottom: '10px', width: '2px',
                    background: 'linear-gradient(180deg, var(--color-border) 0%, rgba(255,255,255,0.05) 100%)',
                    zIndex: 1
                  }} />

                  {filteredRecentJobs.map((job) => {
                    const summary = generateSmartSummary(job)
                    const isExpanded = expandedJobs.has(job.id)
                    
                    // 수집 소스 매핑 및 스타일 지정
                    let sourceInfo = { label: job.label ?? job.source, color: 'var(--color-text-muted)', icon: '⚙️' }
                    const srcL = job.source.toLowerCase()
                    if (srcL.startsWith('youtube')) {
                      sourceInfo = { label: 'YouTube', color: '#ff4d4d', icon: '🔴' }
                    } else if (srcL.includes('scholar')) {
                      sourceInfo = { label: 'Semantic Scholar', color: '#6666ff', icon: '🎓' }
                    } else if (srcL.startsWith('arxiv')) {
                      sourceInfo = { label: 'arXiv', color: '#cc66ff', icon: '🔬' }
                    } else if (srcL.startsWith('rss')) {
                      sourceInfo = { label: 'RSS/뉴스', color: '#00e599', icon: '📡' }
                    } else if (srcL === 'filter') {
                      sourceInfo = { label: '투자 신호 정제', color: '#ffb300', icon: '📈' }
                    } else if (srcL === 'all') {
                      sourceInfo = { label: '전체 수집', color: 'var(--color-accent)', icon: '🚀' }
                    }

                    // 성과 유형별 CSS 테두리 및 그림자 (Glow) 매핑
                    let summaryStyle = { border: '1px solid var(--color-border)', bg: 'rgba(255,255,255,0.02)' }
                    if (summary.type === 'success') {
                      summaryStyle = { border: '1.5px solid rgba(0, 229, 153, 0.4)', bg: 'rgba(0, 229, 153, 0.04)' }
                    } else if (summary.type === 'danger') {
                      summaryStyle = { border: '1.5px solid rgba(255, 77, 77, 0.4)', bg: 'rgba(255, 77, 77, 0.04)' }
                    } else if (summary.type === 'warn') {
                      summaryStyle = { border: '1.5px solid rgba(255, 179, 0, 0.4)', bg: 'rgba(255, 179, 0, 0.04)' }
                    }

                    return (
                      <div key={job.id} style={{ position: 'relative', zIndex: 2 }}>
                        {/* 타임라인 노드 도트 */}
                        <div style={{
                          position: 'absolute', left: '-22px', top: '16px', width: '12px', height: '12px',
                          borderRadius: '50%', border: '2px solid var(--color-bg)',
                          background: job.status === 'completed' ? 'var(--color-ok)' : (job.status === 'failed' || job.status === 'error' ? 'var(--color-danger)' : 'var(--color-text-muted)'),
                          boxShadow: job.status === 'completed' ? '0 0 8px var(--color-ok)' : 'none'
                        }} />

                        {/* 피드 카드 본체 */}
                        <div className="panel" style={{
                          padding: '1.1rem',
                          background: 'var(--color-surface)',
                          border: isExpanded ? '1px dashed var(--color-accent)' : '1px solid var(--color-border)',
                          borderRadius: '8px',
                          transition: 'all 0.2s',
                          boxShadow: isExpanded ? '0 4px 15px rgba(0, 229, 153, 0.08)' : 'none'
                        }}>
                          {/* 1행: 출처 배지 및 시각 */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span style={{
                                display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                                padding: '0.15rem 0.55rem', borderRadius: '4px',
                                background: 'var(--color-surface-lighter)', border: `1px solid ${sourceInfo.color}33`,
                                color: sourceInfo.color, fontSize: '0.72rem', fontWeight: 700
                              }}>
                                {sourceInfo.icon} {sourceInfo.label}
                              </span>

                              {job.dry_run && (
                                <span style={{
                                  padding: '0.15rem 0.55rem', borderRadius: '4px',
                                  background: 'rgba(255,255,255,0.05)', border: '1px solid var(--color-border)',
                                  color: 'var(--color-text-muted)', fontSize: '0.72rem', fontWeight: 600
                                }}>
                                  🧪 테스트 모드
                                </span>
                              )}
                            </div>

                            <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                              <span>⏱️ 경과: {job.finished_at ? elapsed(job.started_at) : '수집 완료'}</span>
                              <span>•</span>
                              <span>{job.finished_at ? relTime(job.finished_at) : relTime(job.started_at)} ({new Date(job.started_at).toLocaleString('ko-KR', { hour12: false }).substring(2, 16)})</span>
                            </div>
                          </div>

                          {/* 2행: 핵심 수집 주제 */}
                          <div style={{ marginBottom: '0.75rem' }}>
                            <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text)' }}>
                              <span style={{ color: 'var(--color-text-muted)', fontWeight: 500, marginRight: '0.4rem' }}>수집 주제:</span>
                              "{job.topic ?? '기본 쿼리 수집'}"
                            </h4>
                          </div>

                          {/* 3행: 지능형 상황 요약 블록 (Smart Summary Card) */}
                          <div style={{
                            padding: '0.75rem 0.9rem',
                            borderRadius: '6px',
                            background: summaryStyle.bg,
                            border: summaryStyle.border,
                            marginBottom: '0.85rem'
                          }}>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                              <span style={{ fontSize: '0.95rem', lineHeight: '1.2' }}>
                                {summary.type === 'success' ? '📊' : summary.type === 'danger' ? '🚨' : summary.type === 'warn' ? '⚠️' : 'ℹ️'}
                              </span>
                              <div>
                                <strong style={{ 
                                  display: 'block', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em',
                                  color: summary.type === 'success' ? 'var(--color-ok)' : summary.type === 'danger' ? 'var(--color-danger)' : summary.type === 'warn' ? 'var(--color-warn)' : 'var(--color-accent)',
                                  marginBottom: '0.2rem'
                                }}>
                                  {summary.type === 'success' ? '성공 리포트' : summary.type === 'danger' ? '장애 검출됨' : summary.type === 'warn' ? '상황 경고 발생' : '일반 정보'}
                                </strong>
                                <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--color-text)', lineHeight: '1.4', fontWeight: 500 }}>
                                  {summary.text}
                                </p>
                              </div>
                            </div>
                          </div>

                          {/* 4행: 하단 제어 & 연동 액션 바 */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              {/* 1-클릭 실물 데이터 바로가기 연동 (scholar, arxiv, youtube, rss 한정) */}
                              {['youtube', 'scholar', 'arxiv', 'rss', 'all'].includes(job.source.toLowerCase()) && (
                                <button
                                  onClick={() => viewIngestedData(job.source, job.topic)}
                                  style={{
                                    display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                                    padding: '0.4rem 0.8rem', borderRadius: '6px',
                                    border: 'none', background: 'var(--color-accent)',
                                    color: '#000', fontWeight: 700, fontSize: '0.78rem',
                                    cursor: 'pointer', transition: 'all 0.15s'
                                  }}
                                  onMouseOver={e => e.currentTarget.style.filter = 'brightness(1.1)'}
                                  onMouseOut={e => e.currentTarget.style.filter = 'none'}
                                >
                                  🔍 이 주제의 실물 데이터 조회 →
                                </button>
                              )}
                            </div>

                            <button
                              onClick={() => setExpandedJobs(prev => {
                                const next = new Set(prev)
                                if (next.has(job.id)) next.delete(job.id)
                                else next.add(job.id)
                                return next
                              })}
                              style={{
                                display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                                padding: '0.4rem 0.8rem', borderRadius: '6px',
                                border: '1px solid var(--color-border)', background: isExpanded ? 'var(--color-surface-lighter)' : 'transparent',
                                color: 'var(--color-text-muted)', fontSize: '0.75rem', fontWeight: 600,
                                cursor: 'pointer', transition: 'all 0.15s'
                              }}
                            >
                              {isExpanded ? '📋 원본 로그 닫기 ▲' : '📋 원본 로그 조회 ▼'} ({job.log_total}줄)
                            </button>
                          </div>

                          {/* 확장 시 실시간/최종 로그 뷰어 */}
                          {isExpanded && (
                            <div style={{ marginTop: '0.85rem', borderTop: '1px solid var(--color-border)', paddingTop: '0.85rem' }}>
                              <LogViewer lines={job.log_tail} />
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── 연구 주제 관리 탭 ── */}
      {tab === 'topics' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="panel" style={{ padding: '1.25rem' }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem', fontWeight: 700 }}>새 연구 주제 추가</h3>
            <p style={{ margin: '0 0 1rem', fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
              추가된 주제는 Scholar/arXiv 수집 시 쿼리로 사용됩니다. "수집 현황" 탭의 프리셋 목록에도 표시됩니다.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                value={newQuery}
                onChange={e => setNewQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addQuery()}
                placeholder="예: AI 학습 의존도 부모 교육 전략"
                style={{
                  flex: 1, padding: '0.65rem 0.9rem',
                  borderRadius: '8px', border: '1.5px solid var(--color-border)',
                  background: 'var(--color-surface-lighter)', color: 'var(--color-text)',
                  fontSize: '0.9rem', outline: 'none',
                }}
              />
              <button
                onClick={addQuery}
                disabled={addingQuery || !newQuery.trim()}
                style={{
                  padding: '0.65rem 1.25rem', borderRadius: '8px', border: 'none',
                  background: 'var(--color-accent)', color: '#fff',
                  fontWeight: 700, fontSize: '0.85rem',
                  cursor: !newQuery.trim() ? 'not-allowed' : 'pointer',
                  opacity: !newQuery.trim() ? 0.5 : 1,
                }}
              >
                {addingQuery ? '추가 중...' : '+ 추가'}
              </button>
            </div>
          </div>

          <div className="panel" style={{ padding: '1.25rem' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', fontWeight: 700 }}>
              저장된 연구 주제 ({customQueries.length}개)
            </h3>
            {customQueries.length === 0 ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '1rem 0' }}>
                저장된 주제가 없습니다. 위에서 추가해 주세요.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {customQueries.map((q, idx) => (
                  <div key={idx} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0.65rem 0.85rem', borderRadius: '8px',
                    background: 'var(--color-surface-lighter)',
                    border: '1px solid var(--color-border)',
                  }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>{q.text}</span>
                      <span style={{ marginLeft: '0.75rem', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                        {q.targets.join(' + ')} · {relTime(q.added_at)}
                      </span>
                    </div>
                    <button
                      onClick={() => deleteQuery(idx)}
                      style={{
                        padding: '0.25rem 0.6rem', borderRadius: '5px',
                        border: '1px solid var(--color-danger)',
                        background: 'transparent', color: 'var(--color-danger)',
                        fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
                      }}
                    >삭제</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel" style={{ padding: '1.25rem' }}>
            <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', fontWeight: 700 }}>기본 내장 쿼리 (읽기 전용)</h3>
            <p style={{ margin: '0 0 0.75rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
              스크립트에 하드코딩된 기본 쿼리들입니다. 주제 선택 없이 실행하면 아래 쿼리가 사용됩니다.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
              {[
                'AI literacy cognitive offloading students',
                'generative AI student learning critical thinking',
                'student dependence on ChatGPT learning loss',
                'k-12 AI safety guidelines parental concern',
                'AI educational technology home learning impact',
                'ti:AI+literacy+education',
                'abs:cognitive+offloading+artificial+intelligence',
                'ti:AI+replacement+anxiety',
              ].map(q => (
                <span key={q} style={{
                  padding: '0.2rem 0.6rem', borderRadius: '5px',
                  background: 'var(--color-surface-lighter)',
                  border: '1px solid var(--color-border)',
                  fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: 'monospace',
                }}>{q}</span>
              ))}
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', alignSelf: 'center' }}>...외 30+개</span>
            </div>
          </div>
        </div>
      )}

      {/* ── 수집 데이터 탭 ── */}
      {tab === 'raw' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <select
              value={sigFilter.source}
              onChange={e => setSigFilter(f => ({ ...f, source: e.target.value }))}
              style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'var(--color-surface-lighter)', color: 'var(--color-text)', fontSize: '0.85rem' }}
            >
              <option value="">전체 소스</option>
              <option value="arxiv">arXiv (ML · AI · Robotics)</option>
              <option value="youtube">YouTube</option>
              <option value="rss">RSS / 뉴스 (IEEE · MIT · TechCrunch 등)</option>
            </select>
            <select
              value={sigFilter.status}
              onChange={e => setSigFilter(f => ({ ...f, status: e.target.value }))}
              style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'var(--color-surface-lighter)', color: 'var(--color-text)', fontSize: '0.85rem' }}
            >
              <option value="">전체 상태</option>
              <option value="filtered_pass">채택</option>
              <option value="filtered_fail">제외</option>
              <option value="pending">분류 대기</option>
            </select>
            <input
              type="text"
              placeholder="제목/내용 검색"
              value={sigFilter.q}
              onChange={e => setSigFilter(f => ({ ...f, q: e.target.value }))}
              style={{ padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'var(--color-surface-lighter)', color: 'var(--color-text)', fontSize: '0.85rem', minWidth: 200 }}
            />
            <button onClick={() => fetchSignals(0)} style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--color-accent)', color: '#fff', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer' }}>
              검색
            </button>
            <span style={{ alignSelf: 'center', fontSize: '0.82rem', color: 'var(--color-text-muted)', marginLeft: 'auto' }}>
              {signals ? `총 ${signals.total.toLocaleString('ko-KR')}건` : ''}
            </span>
          </div>

          {sigLoading ? (
            <div className="panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>불러오는 중...</div>
          ) : signals && signals.items.length > 0 ? (
            <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr 90px 100px', gap: 0 }}>
                {/* 헤더 */}
                {['소스', '제목', '상태', '수집시각'].map(h => (
                  <div key={h} style={{ padding: '0.6rem 1rem', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface-lighter)' }}>{h}</div>
                ))}
                {/* 행 */}
                {signals.items.map((item, idx) => {
                  const isLast = idx === signals.items.length - 1
                  const statusColor = item.status === 'filtered_pass' ? 'var(--color-ok)' : item.status === 'filtered_fail' ? 'var(--color-text-muted)' : 'var(--color-warn)'
                  const statusLabel = item.status === 'filtered_pass' ? '채택' : item.status === 'filtered_fail' ? '제외' : '분류 대기'
                  
                  const hasTier2 = item.tier2_score !== undefined && item.tier2_score !== null
                  const rawScore = item.tier2_score as number
                  // edu_consulting: score 1-10 정수 / physical_ai: 0-1 소수 — 둘 다 /10으로 통일
                  const scoreNum = hasTier2 ? (rawScore > 1 ? Math.round(rawScore) : Math.round(rawScore * 10)) : null
                  const scoreColor = scoreNum !== null
                    ? scoreNum >= 7 ? 'var(--color-ok)' : scoreNum >= 5 ? 'var(--color-warn)' : 'var(--color-danger)'
                    : 'var(--color-text-muted)'
                  const categoryLabel: Record<string, string> = {
                    physical_ai: '🤖 Physical AI',
                    deep_scraped: '🔍 딥 스크랩',
                    keyword_pass: '🔑 키워드 통과',
                  }
                  const stripHtml = (s: string) => s.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim()

                  return [
                    <div key={`src-${item.id}`} style={{ padding: '0.8rem 1rem', fontSize: '0.78rem', color: 'var(--color-text-muted)', borderBottom: isLast ? 'none' : '1px solid var(--color-border)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.source}</div>,
                    <div key={`ttl-${item.id}`} style={{ padding: '0.8rem 1rem', fontSize: '0.82rem', borderBottom: isLast ? 'none' : '1px solid var(--color-border)', overflow: 'hidden' }}>
                      <div style={{ marginBottom: hasTier2 ? '0.5rem' : 0 }}>
                        {item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-accent)', textDecoration: 'none', fontWeight: 600 }}>{item.title || '(제목 없음)'}</a> : (item.title || '(제목 없음)')}
                      </div>
                      {hasTier2 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', padding: '0.5rem 0.75rem', borderRadius: '6px', background: 'var(--color-surface)', border: '1px solid var(--color-border)', fontSize: '0.75rem' }}>
                          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.1rem 0.4rem', borderRadius: '4px', background: 'var(--color-surface-lighter)', color: scoreColor, fontWeight: 700, fontSize: '0.7rem' }}>
                              Tier 2 점수 {scoreNum}/10
                            </span>
                            {item.tier2_category && (
                              <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', padding: '0.1rem 0.35rem', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                                {categoryLabel[item.tier2_category] ?? item.tier2_category}
                              </span>
                            )}
                          </div>
                          {item.tier2_reason && (
                            <div style={{ color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
                              <strong style={{ color: 'var(--color-text)' }}>판단 근거:</strong> {stripHtml(item.tier2_reason)}
                            </div>
                          )}
                          {item.tier2_insight && (
                            <div style={{ color: 'var(--color-text)', lineHeight: 1.4, borderLeft: '2px solid var(--color-ok)', paddingLeft: '0.4rem' }}>
                              <strong>인사이트:</strong> {stripHtml(item.tier2_insight)}
                            </div>
                          )}
                        </div>
                      )}
                    </div>,
                    <div key={`st-${item.id}`} style={{ padding: '0.8rem 1rem', fontSize: '0.78rem', fontWeight: 700, color: statusColor, borderBottom: isLast ? 'none' : '1px solid var(--color-border)' }}>{statusLabel}</div>,
                    <div key={`tm-${item.id}`} style={{ padding: '0.8rem 1rem', fontSize: '0.75rem', color: 'var(--color-text-muted)', borderBottom: isLast ? 'none' : '1px solid var(--color-border)' }}>{relTime(item.ingested_at)}</div>,
                  ]
                })}
              </div>
            </div>
          ) : (
            <div className="panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>수집된 데이터가 없습니다.</div>
          )}

          {signals && (
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', alignItems: 'center' }}>
              <button disabled={sigOffset === 0} onClick={() => fetchSignals(Math.max(0, sigOffset - 50))}
                style={{ padding: '0.4rem 0.8rem', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: sigOffset === 0 ? 'not-allowed' : 'pointer', opacity: sigOffset === 0 ? 0.4 : 1 }}>
                ← 이전
              </button>
              <span style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
                {sigOffset + 1}–{Math.min(sigOffset + 50, signals.total)} / {signals.total.toLocaleString('ko-KR')}건
              </span>
              <button disabled={sigOffset + 50 >= signals.total} onClick={() => fetchSignals(sigOffset + 50)}
                style={{ padding: '0.4rem 0.8rem', borderRadius: '6px', border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text)', cursor: sigOffset + 50 >= signals.total ? 'not-allowed' : 'pointer', opacity: sigOffset + 50 >= signals.total ? 0.4 : 1 }}>
                다음 →
              </button>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.3 } }
      `}</style>
    </div>
  )
}

// ── 실행 중 Job 패널 (로그 즉시 표시) ─────────────────────────────
function JobPanel({ job, expanded, onToggle, onStop }: {
  job: Job
  expanded: boolean
  onToggle: () => void
  onStop: () => void
}) {
  const [, setTick] = useState(0)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setInterval(() => setTick(n => n + 1), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    if (expanded) logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [job.log_tail, expanded])

  return (
    <div className="panel" style={{ overflow: 'hidden', border: '1px solid var(--color-accent)' }}>
      {/* 잡 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.85rem 1.25rem' }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--color-accent)', flexShrink: 0, animation: 'pulse 1.2s infinite' }} />
        <div style={{ flex: 1 }}>
          <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>{job.label ?? job.source}</span>
          {job.dry_run && <span style={{ marginLeft: '0.4rem', fontSize: '0.7rem', color: 'var(--color-text-muted)', border: '1px solid var(--color-border)', borderRadius: 4, padding: '0.05rem 0.3rem' }}>테스트 실행</span>}
        </div>
        <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
          경과 {elapsed(job.started_at)} · 작업번호 {job.pid} · 기록 {job.log_total}줄
        </span>
        <button onClick={onToggle} style={{ padding: '0.25rem 0.65rem', borderRadius: '5px', border: '1px solid var(--color-border)', background: 'transparent', color: 'var(--color-text-muted)', fontSize: '0.75rem', cursor: 'pointer' }}>
          {expanded ? '로그 닫기' : '로그 보기'}
        </button>
        <button onClick={onStop} style={{ padding: '0.25rem 0.65rem', borderRadius: '5px', border: '1px solid var(--color-danger)', background: 'transparent', color: 'var(--color-danger)', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}>
          중지
        </button>
      </div>

      {/* 로그 뷰어 — 실행 중이면 기본 표시, 토글 가능 */}
      {expanded && <LogViewer lines={job.log_tail} logEndRef={logEndRef} />}
      {!expanded && job.log_tail.length > 0 && (
        <div style={{ padding: '0.5rem 1.25rem', borderTop: '1px solid var(--color-border)', background: '#0d1117', cursor: 'pointer' }} onClick={onToggle}>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-ok)', fontFamily: 'monospace' }}>
            ▶ {job.log_tail[job.log_tail.length - 1]?.slice(0, 100)}…
          </span>
        </div>
      )}
    </div>
  )
}

// ── 로그 뷰어 ──────────────────────────────────────────────────────
function LogViewer({ lines, logEndRef }: { lines: string[]; logEndRef?: React.RefObject<HTMLDivElement | null> }) {
  return (
    <div style={{
      background: '#0d1117',
      borderTop: '1px solid var(--color-border)',
      padding: '0.75rem 1.25rem',
      maxHeight: 320,
      overflowY: 'auto',
      fontFamily: 'ui-monospace, SFMono-Regular, monospace',
      fontSize: '0.75rem',
      lineHeight: 1.6,
    }}>
      {lines.length === 0 && (
        <span style={{ color: '#555' }}>로그 대기 중...</span>
      )}
      {lines.map((line, i) => (
        <div key={i} style={{ color: colorLine(line), whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {line}
        </div>
      ))}
      <div ref={logEndRef} />
    </div>
  )
}
