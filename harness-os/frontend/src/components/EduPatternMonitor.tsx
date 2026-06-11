import { useEffect, useMemo, useState, type CSSProperties } from 'react'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  defaultOpen?: boolean
  mode?: 'inline' | 'page'
}

type PatternMonitorPayload = {
  generated_at?: string
  history?: Array<{
    generated_at?: string
    total_extracted_facts?: number
    pattern_count?: number
    complaint_fact_count?: number
    top_patterns?: Array<{
      pattern_id?: string
      label?: string
      segment?: string
      pattern_score?: number
      complaint_risk_score?: number
      complaint_count?: number
      supporting_evidence_count?: number
    }>
    summary?: {
      total_extracted_facts?: number
      pattern_count?: number
      complaint_fact_count?: number
      top_patterns?: Array<{ pattern_id?: string; label?: string; score?: number; segment?: string }>
    }
  }>
  refresh?: {
    attempted?: boolean
    ok?: boolean
    details?: {
      ran_at?: string
      steps?: Array<{ script?: string; ok?: boolean; stderr?: string; returncode?: number }>
    }
  }
  red_team?: {
    available?: boolean
    verdict?: string
    summary?: string
    path?: string | null
    url?: string | null
  }
  artifacts?: Record<string, string | null>
  monitor?: {
    purpose?: string
    source_inputs?: {
      evidence_bank?: { available?: boolean; item_count?: number; source_kind_counts?: Record<string, number>; path?: string }
      runtime_events?: { available?: boolean; event_count?: number; event_type_counts?: Record<string, number>; path?: string }
      manual_observations?: { available?: boolean; item_count?: number; path?: string }
      transcript_db?: { available?: boolean; case_count?: number; turn_count?: number; error?: string | null }
    }
    transparency?: {
      non_negotiables?: string[]
      scoring_formula?: string
      weights?: Record<string, number>
      normalization_rules?: Record<string, string>
      complaint_policy?: string[]
      fact_selection_definition?: Record<string, string>
      fact_selection_rules?: string[]
      fact_selection_why_low?: string[]
      pattern_catalog?: Array<{
        pattern_id: string
        segment: string
        label: string
        pain_category: string
        keywords: string[]
        urgency_keywords: string[]
        execution_keywords: string[]
      }>
    }
    summary?: {
      total_raw_input_rows?: number
      total_scanned_rows?: number
      total_unique_rows_linked?: number
      total_extracted_facts?: number
      pattern_count?: number
      complaint_fact_count?: number
      top_patterns?: Array<{ pattern_id: string; label: string; score: number; segment: string }>
    }
    patterns?: Array<{
      pattern_id: string
      label: string
      segment: string
      pain_category: string
      desire_category: string
      pattern_score: number
      complaint_risk_score: number
      supporting_evidence_count: number
      complaint_count: number
      source_types: string[]
      source_counts: Record<string, number>
      factor_breakdown: Record<string, number>
      why_it_ranked: string[]
      known_failure_modes: string[]
      safe_prompt_hints: string[]
      avoid_response_patterns: string[]
      evidence_samples: Array<{
        source_type: string
        source_label: string
        observed_at?: string | null
        excerpt: string
        matched_keywords?: string[]
        complaint_signal?: boolean
        complaint_type?: string | null
        source_ref?: {
          resolver?: string
          id?: string
          case_id?: number
          turn_no?: number
          ts?: string
          event_type?: string
        }
      }>
    }>
    extraction_funnel?: {
      raw_input_rows?: number
      scanned_rows?: number
      unique_rows_linked?: number
      extracted_facts?: number
      source_breakdown?: Array<{
        source_key?: string
        label?: string
        total_rows?: number
        scanned_rows?: number
        eligible_rows?: number
        rows_with_match?: number
        unique_rows_linked?: number
        included_fact_count?: number
        excluded_rows?: number
        excluded_reason_counts?: Record<string, number>
        excluded_samples?: Array<{
          reason?: string
          excerpt?: string
          meta?: Record<string, unknown>
          source_ref?: {
            resolver?: string
            id?: string
            case_id?: number
            turn_no?: number
            ts?: string
            event_type?: string
          }
        }>
        complaint_only_rows?: number
        notes?: string[]
        source_kind_counts?: Record<string, number>
        event_type_counts?: Record<string, number>
        segment_counts?: Record<string, number>
      }>
    }
  }
  fact_check?: {
    status?: string
    summary?: Record<string, number>
    policy?: Record<string, string | number>
    patterns?: Array<{
      pattern_id: string
      label: string
      status: string
      reasons: string[]
      metrics?: {
        supporting_evidence_count?: number
        distinct_source_types?: number
        source_types?: string[]
        pattern_score?: number
        complaint_count?: number
      }
    }>
  }
}

type FactCheckPattern = {
  pattern_id: string
  label: string
  status: string
  reasons: string[]
  metrics?: {
    supporting_evidence_count?: number
    distinct_source_types?: number
    source_types?: string[]
    pattern_score?: number
    complaint_count?: number
  }
}

type SourceDetailPayload = {
  ok?: boolean
  pattern_id?: string
  sample_index?: number
  resolver?: string
  sample?: Record<string, unknown>
  detail?: unknown
}

const C = {
  ink: '#0f172a',
  muted: '#475569',
  faint: '#64748b',
  accent: '#2563eb',
  border: '#e2e8f0',
  surface: '#ffffff',
  bg: '#f8fafc',
  success: '#059669',
  successSoft: '#d1fae5',
  warning: '#d97706',
  warningSoft: '#fef3c7',
  danger: '#dc2626',
  dangerSoft: '#fee2e2',
}

function badgeStyle(color: string, soft: string): CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 9px',
    borderRadius: 999,
    fontSize: '.72rem',
    fontWeight: 800,
    color,
    background: soft,
    border: `1px solid ${color}33`,
  }
}

function statusBadge(status: string | undefined) {
  const normalized = (status || '').toLowerCase()
  if (normalized.includes('supported') && !normalized.includes('weak')) {
    return <span style={badgeStyle(C.success, C.successSoft)}>{status}</span>
  }
  if (normalized.includes('clear')) {
    return <span style={badgeStyle(C.success, C.successSoft)}>{status}</span>
  }
  if (normalized.includes('weak') || normalized.includes('conditional')) {
    return <span style={badgeStyle(C.warning, C.warningSoft)}>{status}</span>
  }
  return <span style={badgeStyle(C.danger, C.dangerSoft)}>{status || 'unknown'}</span>
}

function chipList(items: string[], color = C.accent) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {items.map(item => (
        <span key={item} style={{ display: 'inline-flex', alignItems: 'center', padding: '4px 8px', borderRadius: 999, fontSize: '.72rem', color, background: `${color}14`, border: `1px solid ${color}2d` }}>
          {item}
        </span>
      ))}
    </div>
  )
}

function miniTrendSvg(values: number[], color: string) {
  if (!values.length) return null
  const width = 180
  const height = 46
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const points = values.map((value, idx) => {
    const x = (idx / Math.max(values.length - 1, 1)) * (width - 8) + 4
    const y = height - 4 - ((value - min) / range) * (height - 12)
    return `${x},${y}`
  })
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="46" preserveAspectRatio="none" aria-hidden="true">
      <polyline fill="none" stroke={`${color}40`} strokeWidth="1" points={`4,${height - 4} ${width - 4},${height - 4}`} />
      <polyline fill="none" stroke={color} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" points={points.join(' ')} />
    </svg>
  )
}

function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2)
}

function countPairs(value?: Record<string, number>) {
  return Object.entries(value || {})
    .map(([key, count]) => `${key} ${count}`)
    .join(' · ')
}

function trendPatternScore(item: { score?: number; pattern_score?: number }) {
  return item.score ?? item.pattern_score ?? 0
}

export function EduPatternMonitor({ apiBase, authHeaders, defaultOpen = false, mode = 'inline' }: Props) {
  const [open, setOpen] = useState(defaultOpen)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [payload, setPayload] = useState<PatternMonitorPayload | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailPayload, setDetailPayload] = useState<SourceDetailPayload | null>(null)

  async function load(force = false) {
    setLoading(true)
    setError(null)
    try {
      const qs = force ? '?force_refresh=true' : ''
      const res = await fetch(`${apiBase}/api/edu/pattern-intelligence${qs}`, { headers: authHeaders() })
      const raw = await res.text()
      const contentType = res.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) {
        throw new Error(`패턴 API가 JSON이 아니라 ${contentType || 'unknown'}을 반환했습니다. 응답 시작: ${raw.slice(0, 160)}`)
      }
      const data = JSON.parse(raw)
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setPayload(data as PatternMonitorPayload)
    } catch (err) {
      setError(err instanceof Error ? err.message : '패턴 모니터 로드 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!open) return
    void load(false)
    const timer = window.setInterval(() => void load(false), 45000)
    return () => window.clearInterval(timer)
  }, [open])

  const summary = payload?.monitor?.summary
  const topPatterns = payload?.monitor?.patterns ?? []
  const history = payload?.history ?? []
  const funnel = payload?.monitor?.extraction_funnel
  const factByPattern = useMemo(() => {
    const out = new Map<string, FactCheckPattern>()
    for (const item of (payload?.fact_check?.patterns ?? []) as FactCheckPattern[]) out.set(item.pattern_id, item)
    return out
  }, [payload?.fact_check?.patterns])
  const overallTrend = useMemo(() => ({
    facts: history.map(row => row.total_extracted_facts ?? row.summary?.total_extracted_facts ?? 0),
    complaints: history.map(row => row.complaint_fact_count ?? row.summary?.complaint_fact_count ?? 0),
    patterns: history.map(row => row.pattern_count ?? row.summary?.pattern_count ?? 0),
  }), [history])
  const patternTrendMap = useMemo(() => {
    const out = new Map<string, { score: number[]; complaints: number[]; support: number[] }>()
    for (const row of history) {
      for (const item of row.top_patterns ?? []) {
        const key = item.pattern_id || ''
        if (!key) continue
        if (!out.has(key)) out.set(key, { score: [], complaints: [], support: [] })
        const bucket = out.get(key)!
        bucket.score.push(item.pattern_score ?? 0)
        bucket.complaints.push(item.complaint_count ?? 0)
        bucket.support.push(item.supporting_evidence_count ?? 0)
      }
    }
    return out
  }, [history])

  async function loadDetail(patternId: string, sampleIndex: number) {
    setDetailLoading(true)
    setDetailError(null)
    try {
      const qs = new URLSearchParams({ pattern_id: patternId, sample_index: String(sampleIndex) })
      const res = await fetch(`${apiBase}/api/edu/pattern-intelligence/source-detail?${qs.toString()}`, { headers: authHeaders() })
      const raw = await res.text()
      const contentType = res.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) {
        throw new Error(`source-detail API가 JSON이 아니라 ${contentType || 'unknown'}을 반환했습니다. 응답 시작: ${raw.slice(0, 160)}`)
      }
      const data = JSON.parse(raw)
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setDetailPayload(data as SourceDetailPayload)
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : '원문 detail 로드 실패')
      setDetailPayload(null)
    } finally {
      setDetailLoading(false)
    }
  }

  async function loadExcludedDetail(sourceKey: string, sampleIndex: number) {
    setDetailLoading(true)
    setDetailError(null)
    try {
      const qs = new URLSearchParams({ source_key: sourceKey, sample_index: String(sampleIndex) })
      const res = await fetch(`${apiBase}/api/edu/pattern-intelligence/excluded-detail?${qs.toString()}`, { headers: authHeaders() })
      const raw = await res.text()
      const contentType = res.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) {
        throw new Error(`excluded-detail API가 JSON이 아니라 ${contentType || 'unknown'}을 반환했습니다. 응답 시작: ${raw.slice(0, 160)}`)
      }
      const data = JSON.parse(raw)
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setDetailPayload(data as SourceDetailPayload)
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : '제외 raw detail 로드 실패')
      setDetailPayload(null)
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div style={{ marginBottom: 16, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: mode === 'page' ? '0 12px 30px rgba(15,23,42,.05)' : 'none' }}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        style={{
          width: '100%',
          background: open ? 'linear-gradient(135deg,#eff6ff,#f8fafc)' : C.surface,
          border: 'none',
          padding: '14px 16px',
          textAlign: 'left',
          cursor: 'pointer',
          fontFamily: 'inherit',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '.76rem', color: C.accent, fontWeight: 800, letterSpacing: '.04em', textTransform: 'uppercase' }}>{mode === 'page' ? 'Pattern Intelligence Control Room' : 'Edu Pattern Monitor'}</div>
            <div style={{ fontSize: mode === 'page' ? '1.08rem' : '1rem', color: C.ink, fontWeight: 800, marginTop: 3 }}>어떤 자료를 검토해 어떤 패턴으로 묶였는지 실시간 투명 모니터</div>
            <div style={{ fontSize: '.78rem', color: C.faint, marginTop: 5 }}>
              {summary ? `raw ${summary.total_raw_input_rows ?? 0} · linked rows ${summary.total_unique_rows_linked ?? 0} · extracted facts ${summary.total_extracted_facts ?? 0}` : '펼치면 최신 패턴, 팩트체크, Red Team 결과를 불러옵니다.'}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {payload?.red_team?.verdict && statusBadge(payload.red_team.verdict)}
            <span style={{ color: C.faint, fontSize: '.76rem' }}>{open ? '접기 ▲' : '열기 ▼'}</span>
          </div>
        </div>
      </button>

      {open && (
        <div style={{ padding: 16, borderTop: `1px solid ${C.border}`, background: C.bg, display: 'grid', gap: 14 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => void load(true)}
              disabled={loading}
              style={{ background: C.accent, color: '#fff', border: 'none', borderRadius: 10, padding: '9px 12px', fontSize: '.82rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}
            >
              {loading ? '갱신 중…' : '실시간 재계산'}
            </button>
            {payload?.artifacts?.monitor_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.monitor_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                raw JSON
              </button>
            )}
            {payload?.artifacts?.fact_check_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.fact_check_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                fact check
              </button>
            )}
            {payload?.artifacts?.history_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.history_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                history
              </button>
            )}
            {payload?.artifacts?.red_team_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.red_team_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                RED TEAM
              </button>
            )}
            {payload?.artifacts?.plan_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.plan_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                구현 계획
              </button>
            )}
            {payload?.artifacts?.backlog_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.backlog_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                backlog
              </button>
            )}
            {payload?.artifacts?.handoff_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.handoff_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                handoff
              </button>
            )}
            {payload?.artifacts?.red_team_prompt_url && (
              <button type="button" onClick={() => window.open(`${apiBase}${payload.artifacts?.red_team_prompt_url}`, '_blank', 'noopener,noreferrer')} style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 10, padding: '9px 12px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                red-team prompt
              </button>
            )}
          </div>

          {error && <div style={{ color: C.danger, fontSize: '.84rem' }}>{error}</div>}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 10 }}>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>raw 입력 row</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: C.ink }}>{summary?.total_raw_input_rows ?? 0}</div>
            </div>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>실제 스캔 row</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: C.ink }}>{summary?.total_scanned_rows ?? 0}</div>
            </div>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>pattern 연결 row</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: C.ink }}>{summary?.total_unique_rows_linked ?? 0}</div>
            </div>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>extracted fact</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: C.ink }}>{summary?.total_extracted_facts ?? 0}</div>
            </div>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>추출 패턴</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: C.ink }}>{summary?.pattern_count ?? 0}</div>
            </div>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>불만 signal</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: C.ink }}>{summary?.complaint_fact_count ?? 0}</div>
            </div>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>생성 시각</div>
              <div style={{ fontSize: '.82rem', fontWeight: 700, color: C.ink, lineHeight: 1.45 }}>{payload?.generated_at ?? '-'}</div>
            </div>
          </div>

          <div style={{ background: '#fff7ed', border: '1px solid #fdba74', borderRadius: 14, padding: 14 }}>
            <div style={{ fontSize: '.88rem', fontWeight: 800, color: '#9a3412', marginBottom: 8 }}>왜 검토된 fact가 이 숫자인가</div>
            <div style={{ fontSize: '.82rem', color: '#7c2d12', lineHeight: 1.65 }}>
              raw 입력 {funnel?.raw_input_rows ?? 0}건 중 실제 스캔 {funnel?.scanned_rows ?? 0}건, pattern과 연결된 고유 row {funnel?.unique_rows_linked ?? 0}건,
              그리고 pattern별로 펼쳐진 extracted fact {funnel?.extracted_facts ?? 0}건입니다. 이 숫자는 저장된 전체 자료 수가 아니라 pattern keyword 또는 complaint rule에 걸린 신호만 집계한 값입니다.
            </div>
          </div>

          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
              <div style={{ fontSize: '.86rem', fontWeight: 800, color: C.ink }}>시간축 변화량</div>
              <div style={{ fontSize: '.76rem', color: C.faint }}>최근 {history.length || 0}회 산출 기준</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 10 }}>
              <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
                <div style={{ fontSize: '.74rem', color: C.faint, marginBottom: 6 }}>검토 fact 추이</div>
                {miniTrendSvg(overallTrend.facts, C.accent)}
                <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 6 }}>{overallTrend.facts.join(' → ') || 'history 없음'}</div>
              </div>
              <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
                <div style={{ fontSize: '.74rem', color: C.faint, marginBottom: 6 }}>불만 signal 추이</div>
                {miniTrendSvg(overallTrend.complaints, C.warning)}
                <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 6 }}>{overallTrend.complaints.join(' → ') || 'history 없음'}</div>
              </div>
              <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
                <div style={{ fontSize: '.74rem', color: C.faint, marginBottom: 6 }}>활성 패턴 수 추이</div>
                {miniTrendSvg(overallTrend.patterns, C.success)}
                <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 6 }}>{overallTrend.patterns.join(' → ') || 'history 없음'}</div>
              </div>
            </div>
            {mode === 'page' && history.length > 0 && (
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                {history.slice(-8).map((row, idx) => (
                  <div key={`${row.generated_at || 'history'}-${idx}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '9px 11px' }}>
                    <div style={{ fontSize: '.76rem', color: C.ink, fontWeight: 700 }}>{row.generated_at || 'unknown run'}</div>
                    <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 4 }}>
                      facts {row.total_extracted_facts ?? row.summary?.total_extracted_facts ?? 0} · patterns {row.pattern_count ?? row.summary?.pattern_count ?? 0} · complaints {row.complaint_fact_count ?? row.summary?.complaint_fact_count ?? 0}
                    </div>
                    <div style={{ fontSize: '.74rem', color: C.faint, marginTop: 4 }}>
                      top: {(row.top_patterns || row.summary?.top_patterns || []).map(item => `${item.label || item.pattern_id}(${trendPatternScore(item)})`).join(' · ') || '없음'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
            <div style={{ fontSize: '.86rem', fontWeight: 800, color: C.ink, marginBottom: 8 }}>100% 투명 로직</div>
            <div style={{ fontSize: '.8rem', color: C.muted, lineHeight: 1.65, marginBottom: 8 }}>{payload?.monitor?.purpose}</div>
            <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>score formula</div>
            <code style={{ display: 'block', background: '#0f172a', color: '#e2e8f0', padding: '10px 12px', borderRadius: 10, fontSize: '.75rem', whiteSpace: 'pre-wrap' }}>
              {payload?.monitor?.transparency?.scoring_formula || 'loading...'}
            </code>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 8, marginTop: 10 }}>
              {Object.entries(payload?.monitor?.transparency?.weights || {}).map(([key, value]) => (
                <div key={key} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 10px' }}>
                  <div style={{ fontSize: '.72rem', color: C.faint }}>{key}</div>
                  <div style={{ fontSize: '.92rem', color: C.ink, fontWeight: 800 }}>{value}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>non-negotiables</div>
              <ul style={{ margin: 0, paddingLeft: 18, color: C.muted, fontSize: '.82rem', lineHeight: 1.6 }}>
                {(payload?.monitor?.transparency?.non_negotiables || []).map(item => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>fact 선정 정의</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {Object.entries(payload?.monitor?.transparency?.fact_selection_definition || {}).map(([key, value]) => (
                  <div key={key} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 10px' }}>
                    <div style={{ fontSize: '.74rem', color: C.ink, fontWeight: 700 }}>{key}</div>
                    <div style={{ fontSize: '.78rem', color: C.muted, lineHeight: 1.55, marginTop: 3 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>fact 선정 규칙</div>
              <ul style={{ margin: 0, paddingLeft: 18, color: C.muted, fontSize: '.82rem', lineHeight: 1.6 }}>
                {(payload?.monitor?.transparency?.fact_selection_rules || []).map(item => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>fact 수가 적어 보일 수 있는 이유</div>
              <ul style={{ margin: 0, paddingLeft: 18, color: C.muted, fontSize: '.82rem', lineHeight: 1.6 }}>
                {(payload?.monitor?.transparency?.fact_selection_why_low || []).map(item => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>정규화 규칙</div>
              <div style={{ display: 'grid', gap: 8 }}>
                {Object.entries(payload?.monitor?.transparency?.normalization_rules || {}).map(([key, value]) => (
                  <div key={key} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 10px' }}>
                    <div style={{ fontSize: '.74rem', color: C.ink, fontWeight: 700 }}>{key}</div>
                    <div style={{ fontSize: '.78rem', color: C.muted, lineHeight: 1.55, marginTop: 3 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
            <div style={{ fontSize: '.86rem', fontWeight: 800, color: C.ink, marginBottom: 8 }}>raw → linked → fact 퍼널</div>
            <div style={{ display: 'grid', gap: 10, marginBottom: 12 }}>
              {(payload?.monitor?.extraction_funnel?.source_breakdown || []).map((row, idx) => (
                <div key={`${row.source_key || row.label || 'source'}-${idx}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '10px 12px' }}>
                  <div style={{ fontSize: '.78rem', color: C.ink, fontWeight: 700 }}>{row.label}</div>
                  <div style={{ fontSize: '.8rem', color: C.muted, marginTop: 5, lineHeight: 1.6 }}>
                    raw {row.total_rows ?? 0} → scanned {row.scanned_rows ?? 0} → linked rows {row.unique_rows_linked ?? 0} → facts {row.included_fact_count ?? 0}
                  </div>
                  <div style={{ fontSize: '.74rem', color: C.faint, marginTop: 6 }}>
                    제외: {countPairs(row.excluded_reason_counts) || '없음'}
                  </div>
                  {!!row.complaint_only_rows && (
                    <div style={{ fontSize: '.74rem', color: C.warning, marginTop: 4 }}>
                      complaint-only rows: {row.complaint_only_rows}
                    </div>
                  )}
                  {row.notes?.length ? (
                    <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: C.muted, fontSize: '.78rem', lineHeight: 1.55 }}>
                      {row.notes.map(note => <li key={note}>{note}</li>)}
                    </ul>
                  ) : null}
                  {row.excluded_samples?.length ? (
                    <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                      <div style={{ fontSize: '.74rem', color: C.ink, fontWeight: 700 }}>탈락한 raw 예시</div>
                      {row.excluded_samples.map((sample, sampleIdx) => (
                        <div key={`${row.source_key || row.label || 'source'}-excluded-${sampleIdx}`} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 9, padding: '8px 10px' }}>
                          <div style={{ fontSize: '.72rem', color: C.warning, fontWeight: 700 }}>{sample.reason || 'excluded'}</div>
                          <div style={{ fontSize: '.78rem', color: C.ink, lineHeight: 1.55, marginTop: 4 }}>{sample.excerpt || '-'}</div>
                          {!!sample.meta && Object.keys(sample.meta).length > 0 && (
                            <div style={{ fontSize: '.72rem', color: C.faint, marginTop: 5 }}>
                              {Object.entries(sample.meta).map(([key, value]) => `${key}=${String(value)}`).join(' · ')}
                            </div>
                          )}
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 8 }}>
                            <div style={{ fontSize: '.72rem', color: C.faint }}>
                              resolver: {sample.source_ref?.resolver || row.source_key || 'unknown'}
                            </div>
                            <button
                              type="button"
                              onClick={() => void loadExcludedDetail(row.source_key || '', sampleIdx)}
                              style={{ background: C.bg, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 9, padding: '6px 9px', fontSize: '.75rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}
                            >
                              제외 원문 보기
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {!!row.source_kind_counts && <div style={{ fontSize: '.74rem', color: C.faint, marginTop: 6 }}>source kinds: {countPairs(row.source_kind_counts)}</div>}
                  {!!row.event_type_counts && <div style={{ fontSize: '.74rem', color: C.faint, marginTop: 4 }}>event types: {countPairs(row.event_type_counts)}</div>}
                  {!!row.segment_counts && <div style={{ fontSize: '.74rem', color: C.faint, marginTop: 4 }}>segments: {countPairs(row.segment_counts)}</div>}
                </div>
              ))}
            </div>
            <div style={{ fontSize: '.86rem', fontWeight: 800, color: C.ink, marginBottom: 8 }}>검토한 자료 범위</div>
            <div style={{ display: 'grid', gap: 10 }}>
              <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '10px 12px' }}>
                <div style={{ fontSize: '.76rem', color: C.ink, fontWeight: 700 }}>Evidence bank</div>
                <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 4 }}>{payload?.monitor?.source_inputs?.evidence_bank?.item_count ?? 0}건 · {payload?.monitor?.source_inputs?.evidence_bank?.path}</div>
                <div style={{ fontSize: '.74rem', color: C.faint, marginTop: 6 }}>
                  {countPairs(payload?.monitor?.source_inputs?.evidence_bank?.source_kind_counts)}
                </div>
              </div>
              <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '10px 12px' }}>
                <div style={{ fontSize: '.76rem', color: C.ink, fontWeight: 700 }}>Runtime events</div>
                <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 4 }}>{payload?.monitor?.source_inputs?.runtime_events?.event_count ?? 0}건 · {payload?.monitor?.source_inputs?.runtime_events?.path}</div>
                <div style={{ fontSize: '.74rem', color: C.faint, marginTop: 6 }}>
                  {countPairs(payload?.monitor?.source_inputs?.runtime_events?.event_type_counts) || 'event 없음'}
                </div>
              </div>
              <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '10px 12px' }}>
                <div style={{ fontSize: '.76rem', color: C.ink, fontWeight: 700 }}>Manual observations / transcript DB</div>
                <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 4 }}>observations {payload?.monitor?.source_inputs?.manual_observations?.item_count ?? 0}건 · {payload?.monitor?.source_inputs?.manual_observations?.path}</div>
                <div style={{ fontSize: '.78rem', color: C.muted, marginTop: 4 }}>
                  transcript cases {payload?.monitor?.source_inputs?.transcript_db?.case_count ?? 0} · turns {payload?.monitor?.source_inputs?.transcript_db?.turn_count ?? 0}
                </div>
                {payload?.monitor?.source_inputs?.transcript_db?.error && <div style={{ fontSize: '.74rem', color: C.warning, marginTop: 6 }}>{payload?.monitor?.source_inputs?.transcript_db?.error}</div>}
              </div>
            </div>
          </div>

          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
              <div style={{ fontSize: '.86rem', fontWeight: 800, color: C.ink }}>팩트체크 + RED TEAM</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {payload?.fact_check?.status && statusBadge(payload.fact_check.status)}
                {payload?.red_team?.verdict && statusBadge(payload.red_team.verdict)}
              </div>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ fontSize: '.8rem', color: C.muted }}>
                Fact check summary: {Object.entries(payload?.fact_check?.summary || {}).map(([key, value]) => `${key} ${value}`).join(' · ') || '없음'}
              </div>
              <div style={{ fontSize: '.78rem', color: C.muted, lineHeight: 1.6 }}>
                {Object.entries(payload?.fact_check?.policy || {}).map(([key, value]) => <div key={key}>- {key}: {String(value)}</div>)}
              </div>
              {payload?.red_team?.summary && <div style={{ fontSize: '.8rem', color: C.muted, lineHeight: 1.6 }}>{payload.red_team.summary}</div>}
              {payload?.refresh?.details?.steps?.length ? (
                <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '10px 12px' }}>
                  <div style={{ fontSize: '.76rem', color: C.ink, fontWeight: 700, marginBottom: 6 }}>최근 재계산 파이프라인</div>
                  {(payload.refresh.details.steps || []).map((step, idx) => (
                    <div key={`${step.script}-${idx}`} style={{ fontSize: '.78rem', color: step.ok ? C.muted : C.danger, lineHeight: 1.55, marginBottom: 4 }}>
                      - {step.script} · {step.ok ? 'ok' : `fail(${step.returncode ?? '-'})`} {step.stderr ? `· ${step.stderr}` : ''}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          {mode === 'page' && (
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
              <div style={{ fontSize: '.86rem', fontWeight: 800, color: C.ink, marginBottom: 10 }}>패턴 catalog 전체</div>
              <div style={{ display: 'grid', gap: 12 }}>
                {(payload?.monitor?.transparency?.pattern_catalog || []).map((pattern) => (
                  <div key={pattern.pattern_id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: '12px 14px' }}>
                    <div style={{ fontSize: '.72rem', color: C.accent, fontWeight: 800, textTransform: 'uppercase' }}>{pattern.segment} · {pattern.pain_category}</div>
                    <div style={{ fontSize: '.9rem', color: C.ink, fontWeight: 800, marginTop: 4 }}>{pattern.label}</div>
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: '.74rem', color: C.faint, marginBottom: 4 }}>keywords</div>
                      {chipList(pattern.keywords)}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: '.74rem', color: C.faint, marginBottom: 4 }}>urgency</div>
                      {chipList(pattern.urgency_keywords, C.warning)}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: '.74rem', color: C.faint, marginBottom: 4 }}>execution block</div>
                      {chipList(pattern.execution_keywords, C.success)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gap: 12 }}>
            {topPatterns.map((pattern) => {
              const fact = factByPattern.get(pattern.pattern_id)
              return (
                <details key={pattern.pattern_id} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
                  <summary style={{ cursor: 'pointer', listStyle: 'none' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                      <div>
                        <div style={{ fontSize: '.72rem', color: C.accent, fontWeight: 800, textTransform: 'uppercase' }}>{pattern.segment} · {pattern.pain_category}</div>
                        <div style={{ fontSize: '.98rem', color: C.ink, fontWeight: 800, marginTop: 4 }}>{pattern.label}</div>
                        <div style={{ fontSize: '.78rem', color: C.faint, marginTop: 6 }}>
                          score {pattern.pattern_score} · support {pattern.supporting_evidence_count} · complaints {pattern.complaint_count} · sources {pattern.source_types.join(', ')}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {statusBadge(fact?.status)}
                        {pattern.complaint_risk_score > 0 ? <span style={badgeStyle(C.warning, C.warningSoft)}>complaint {pattern.complaint_risk_score}</span> : <span style={badgeStyle(C.success, C.successSoft)}>complaint 0</span>}
                      </div>
                    </div>
                  </summary>

                  <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
                    <div>
                      <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>왜 이 패턴이 올라왔나</div>
                      <ul style={{ margin: 0, paddingLeft: 18, color: C.muted, fontSize: '.82rem', lineHeight: 1.6 }}>
                        {pattern.why_it_ranked.map(item => <li key={item}>{item}</li>)}
                      </ul>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 8 }}>
                      {Object.entries(pattern.factor_breakdown || {}).map(([key, value]) => (
                        <div key={key} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 10px' }}>
                          <div style={{ fontSize: '.72rem', color: C.faint }}>{key}</div>
                          <div style={{ fontSize: '.92rem', color: C.ink, fontWeight: 800 }}>{value}</div>
                        </div>
                      ))}
                    </div>

                    {patternTrendMap.get(pattern.pattern_id) && (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 8 }}>
                        <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 10px' }}>
                          <div style={{ fontSize: '.72rem', color: C.faint, marginBottom: 4 }}>pattern score trend</div>
                          {miniTrendSvg(patternTrendMap.get(pattern.pattern_id)?.score || [], C.accent)}
                        </div>
                        <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 10px' }}>
                          <div style={{ fontSize: '.72rem', color: C.faint, marginBottom: 4 }}>complaint trend</div>
                          {miniTrendSvg(patternTrendMap.get(pattern.pattern_id)?.complaints || [], C.warning)}
                        </div>
                        <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '8px 10px' }}>
                          <div style={{ fontSize: '.72rem', color: C.faint, marginBottom: 4 }}>support trend</div>
                          {miniTrendSvg(patternTrendMap.get(pattern.pattern_id)?.support || [], C.success)}
                        </div>
                      </div>
                    )}

                    {fact && (
                      <div>
                        <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>팩트체크 판단</div>
                        <div style={{ fontSize: '.82rem', color: C.muted, lineHeight: 1.6 }}>
                          {(fact.reasons || []).map((reason: string) => <div key={reason}>- {reason}</div>)}
                        </div>
                      </div>
                    )}

                    <div>
                      <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>실제 근거 샘플</div>
                      <div style={{ display: 'grid', gap: 8 }}>
                        {(pattern.evidence_samples || []).map((sample, idx) => (
                          <div key={`${pattern.pattern_id}-${idx}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: '10px 12px' }}>
                            <div style={{ fontSize: '.74rem', color: C.faint, marginBottom: 4 }}>
                              {sample.source_type} · {sample.source_label} {sample.observed_at ? `· ${sample.observed_at}` : ''}
                            </div>
                            <div style={{ fontSize: '.82rem', color: C.ink, lineHeight: 1.6 }}>{sample.excerpt}</div>
                            <div style={{ fontSize: '.72rem', color: C.faint, marginTop: 6 }}>
                              keywords: {(sample.matched_keywords || []).join(', ') || '-'}
                              {sample.complaint_signal ? ` · complaint=${sample.complaint_type || 'yes'}` : ''}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 8 }}>
                              <div style={{ fontSize: '.72rem', color: C.faint }}>
                                resolver: {sample.source_ref?.resolver || sample.source_type}
                              </div>
                              <button
                                type="button"
                                onClick={() => void loadDetail(pattern.pattern_id, idx)}
                                style={{ background: C.surface, color: C.accent, border: `1px solid ${C.accent}`, borderRadius: 9, padding: '6px 9px', fontSize: '.75rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}
                              >
                                원문 detail 보기
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ display: 'grid', gap: 10 }}>
                      <div>
                        <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>답변에서 피해야 할 패턴</div>
                        <ul style={{ margin: 0, paddingLeft: 18, color: C.muted, fontSize: '.82rem', lineHeight: 1.6 }}>
                          {(pattern.avoid_response_patterns || []).map(item => <li key={item}>{item}</li>)}
                        </ul>
                      </div>
                      <div>
                        <div style={{ fontSize: '.76rem', color: C.faint, marginBottom: 6 }}>runtime에 들어갈 안전 힌트</div>
                        <ul style={{ margin: 0, paddingLeft: 18, color: C.muted, fontSize: '.82rem', lineHeight: 1.6 }}>
                          {(pattern.safe_prompt_hints || []).map(item => <li key={item}>{item}</li>)}
                        </ul>
                      </div>
                    </div>
                  </div>
                </details>
              )
            })}
          </div>

          {(detailLoading || detailError || detailPayload) && (
            <div style={{ background: '#0f172a', color: '#e2e8f0', borderRadius: 14, padding: 14, display: 'grid', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '.78rem', color: '#93c5fd', fontWeight: 800, textTransform: 'uppercase' }}>Source Drill-Down</div>
                  <div style={{ fontSize: '.92rem', fontWeight: 800 }}>근거 원문 / 이벤트 / transcript 창</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setDetailPayload(null)
                    setDetailError(null)
                  }}
                  style={{ background: 'transparent', color: '#cbd5e1', border: '1px solid #475569', borderRadius: 9, padding: '6px 10px', fontSize: '.75rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}
                >
                  닫기
                </button>
              </div>
              {detailLoading && <div style={{ fontSize: '.82rem', color: '#cbd5e1' }}>원문 detail 로드 중…</div>}
              {detailError && <div style={{ fontSize: '.82rem', color: '#fca5a5' }}>{detailError}</div>}
              {detailPayload && (
                <>
                  <div style={{ fontSize: '.78rem', color: '#cbd5e1' }}>
                    pattern {detailPayload.pattern_id} · sample {detailPayload.sample_index} · resolver {detailPayload.resolver}
                  </div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    <div>
                      <div style={{ fontSize: '.74rem', color: '#93c5fd', marginBottom: 4 }}>sample metadata</div>
                      <pre style={{ margin: 0, background: '#111827', borderRadius: 10, padding: '10px 12px', fontSize: '.75rem', whiteSpace: 'pre-wrap', overflowX: 'auto' }}>
                        {prettyJson(detailPayload.sample)}
                      </pre>
                    </div>
                    <div>
                      <div style={{ fontSize: '.74rem', color: '#93c5fd', marginBottom: 4 }}>resolved detail</div>
                      <pre style={{ margin: 0, background: '#111827', borderRadius: 10, padding: '10px 12px', fontSize: '.75rem', whiteSpace: 'pre-wrap', overflowX: 'auto' }}>
                        {prettyJson(detailPayload.detail)}
                      </pre>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
