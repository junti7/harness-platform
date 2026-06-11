import { useEffect, useMemo, useState, type CSSProperties } from 'react'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

type PatternMonitorPayload = {
  generated_at?: string
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
      }>
    }>
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

export function EduPatternMonitor({ apiBase, authHeaders }: Props) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [payload, setPayload] = useState<PatternMonitorPayload | null>(null)

  async function load(force = false) {
    setLoading(true)
    setError(null)
    try {
      const qs = force ? '?force_refresh=true' : ''
      const res = await fetch(`${apiBase}/api/edu/pattern-intelligence${qs}`, { headers: authHeaders() })
      const data = await res.json()
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
  const factByPattern = useMemo(() => {
    const out = new Map<string, FactCheckPattern>()
    for (const item of (payload?.fact_check?.patterns ?? []) as FactCheckPattern[]) out.set(item.pattern_id, item)
    return out
  }, [payload?.fact_check?.patterns])

  return (
    <div style={{ marginBottom: 16, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 16, overflow: 'hidden' }}>
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
            <div style={{ fontSize: '.76rem', color: C.accent, fontWeight: 800, letterSpacing: '.04em', textTransform: 'uppercase' }}>Edu Pattern Monitor</div>
            <div style={{ fontSize: '1rem', color: C.ink, fontWeight: 800, marginTop: 3 }}>어떤 자료를 검토해 어떤 패턴으로 묶였는지 실시간 투명 모니터</div>
            <div style={{ fontSize: '.78rem', color: C.faint, marginTop: 5 }}>
              {summary ? `facts ${summary.total_extracted_facts ?? 0} · patterns ${summary.pattern_count ?? 0} · complaints ${summary.complaint_fact_count ?? 0}` : '펼치면 최신 패턴, 팩트체크, Red Team 결과를 불러옵니다.'}
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
          </div>

          {error && <div style={{ color: C.danger, fontSize: '.84rem' }}>{error}</div>}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 10 }}>
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: '.72rem', color: C.faint }}>검토된 fact</div>
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
          </div>

          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
            <div style={{ fontSize: '.86rem', fontWeight: 800, color: C.ink, marginBottom: 8 }}>검토한 자료 범위</div>
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ fontSize: '.8rem', color: C.muted }}>Evidence bank: {payload?.monitor?.source_inputs?.evidence_bank?.item_count ?? 0}건 · {payload?.monitor?.source_inputs?.evidence_bank?.path}</div>
              <div style={{ fontSize: '.8rem', color: C.muted }}>Runtime events: {payload?.monitor?.source_inputs?.runtime_events?.event_count ?? 0}건 · {payload?.monitor?.source_inputs?.runtime_events?.path}</div>
              <div style={{ fontSize: '.8rem', color: C.muted }}>Manual observations: {payload?.monitor?.source_inputs?.manual_observations?.item_count ?? 0}건 · {payload?.monitor?.source_inputs?.manual_observations?.path}</div>
              <div style={{ fontSize: '.8rem', color: C.muted }}>
                Transcript DB: cases {payload?.monitor?.source_inputs?.transcript_db?.case_count ?? 0} · turns {payload?.monitor?.source_inputs?.transcript_db?.turn_count ?? 0}
                {payload?.monitor?.source_inputs?.transcript_db?.error ? ` · ${payload?.monitor?.source_inputs?.transcript_db?.error}` : ''}
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
              {payload?.red_team?.summary && <div style={{ fontSize: '.8rem', color: C.muted, lineHeight: 1.6 }}>{payload.red_team.summary}</div>}
            </div>
          </div>

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
        </div>
      )}
    </div>
  )
}
