import { useState, useEffect } from 'react'
import type { DashboardPayload } from './types'

type Monitor = NonNullable<DashboardPayload['data_collection_monitor']>

export type ScheduleService = {
  label: string
  name: string
  role: string
  schedule: string
  interval_type: 'calendar' | 'interval'
  interval_seconds?: number
  log_file: string
  loaded: boolean
  running: boolean
  pid: number | null
  last_exit_code: string | null
  log_tail: string[]
}

type Props = { monitor: Monitor; scheduleServices?: ScheduleService[] }

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  pending:       { label: '분류 대기',  color: 'var(--color-warn)' },
  filtered_pass: { label: '채택',   color: 'var(--color-ok)' },
  filtered_fail: { label: '제외',   color: 'var(--color-text-muted)' },
}

const SOURCE_STATUS_BADGE: Record<string, { label: string; color: string }> = {
  active: { label: '활성', color: 'var(--color-ok)' },
  standby: { label: '대기', color: 'var(--color-warn)' },
  restricted: { label: '제한', color: 'var(--color-danger)' },
}

function pct(n: number, total: number) {
  if (!total) return '0%'
  return `${((n / total) * 100).toFixed(1)}%`
}

function relativeTime(iso: string) {
  if (!iso) return '미실행'
  try {
    const diff = Date.now() - new Date(iso).getTime()
    if (diff < 60_000) return '방금'
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}시간 전`
    return `${Math.floor(diff / 86_400_000)}일 전`
  } catch {
    return iso.slice(0, 16)
  }
}

const CLUSTER_LABELS: Record<string, string> = {
  parenting_ai: '보호자 · 자녀 AI',
  worker_ai: '직장인 AI',
  job_seeker_ai: '취준생 · 취업 준비',
  military_ai: '군 복무 · 입대 준비',
  career_major: '진로 · 전공 선택',
  digital_dependence: '디지털 의존 · 스마트폰 갈등',
  general_ai_education: '일반 AI 교육',
  embodiment_robotics: '로봇 본체 · 자동화',
  compute_models: '반도체 · 연산 칩',
  memory_packaging: '메모리 · 패키징',
  networking_optics: '네트워킹 · 광통신',
  power_cooling: '전력 · 냉각',
  simulation_software: '시뮬레이션 · 산업 소프트웨어',
  warehouse_deployment: '물류 · 배포',
  edge_realtime: '엣지 · 실시간 추론',
  general_physical_ai: '일반 Physical AI',
}

function clusterLabel(key: string) {
  return CLUSTER_LABELS[key] || key.replaceAll('_', ' ')
}

export function DataCollectionMonitor({ monitor, scheduleServices = [] }: Props) {
  const [rawStats, setRawStats] = useState<any[]>([])
  const [selectedRawStat, setSelectedRawStat] = useState<any | null>(null)

  useEffect(() => {
    fetch('http://100.97.175.44:8000/api/statistics_data')
      .then(res => res.json())
      .then(data => {
        if (data && data.data) {
          setRawStats(data.data)
        }
      })
      .catch(err => console.error('Failed to fetch raw statistics data:', err))
  }, [])
  const {
    total,
    pending_count,
    pass_count,
    fail_count,
    sources = [],
    channel_coverage = [],
    tier2_worker,
    persona_fallbacks,
    topic_clusters = [],
    edu_topic_clusters = [],
    push_candidates,
    current_topics = [],
    suggested_topics = [],
    generated_query_sources = [],
    expansion_policy,
    workers,
    configured_languages = [],
    recent_activity = [],
  } = monitor
  const passRate = total ? (pass_count / total) * 100 : 0

  const healthVariant = passRate >= 15 ? 'ok' : passRate >= 5 ? 'warn' : 'danger'
  const healthColor = healthVariant === 'ok' ? 'var(--color-ok)' : healthVariant === 'warn' ? 'var(--color-warn)' : 'var(--color-danger)'
  const healthLabel = healthVariant === 'ok' ? '정상' : healthVariant === 'warn' ? '주의' : '저품질'

  return (
    <section className="ops-section" style={{ marginTop: '1.5rem' }}>
      {/* ── 자동 스케줄 현황 ── */}
      {scheduleServices.length > 0 && (
        <div className="panel" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            자동 스케줄 현황
          </p>
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {scheduleServices.map(svc => {
              const statusColor = svc.running
                ? 'var(--color-ok)'
                : svc.loaded && svc.last_exit_code !== null && svc.last_exit_code !== '0'
                ? 'var(--color-danger)'
                : svc.loaded
                ? 'var(--color-text-muted)'
                : 'var(--color-warn)'
              const statusLabel = svc.running
                ? '실행 중'
                : svc.loaded && svc.last_exit_code !== null && svc.last_exit_code !== '0'
                ? `오류 (exit ${svc.last_exit_code})`
                : svc.loaded
                ? '대기'
                : '미등록'
              return (
                <div key={svc.label} style={{
                  display: 'grid',
                  gridTemplateColumns: '10px 1fr auto auto',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.6rem 0.75rem',
                  borderRadius: 6,
                  background: 'var(--color-surface-lighter)',
                  border: '1px solid var(--color-border)',
                }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                    background: statusColor,
                    boxShadow: svc.running ? `0 0 6px ${statusColor}` : 'none',
                    display: 'inline-block',
                  }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.83rem' }}>{svc.name}</span>
                      <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{svc.role}</span>
                    </div>
                    {svc.log_tail.length > 0 && (
                      <div style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', marginTop: '0.15rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {svc.log_tail[svc.log_tail.length - 1]}
                      </div>
                    )}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                    {svc.schedule}
                  </span>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: statusColor, whiteSpace: 'nowrap', minWidth: '4rem', textAlign: 'right' }}>
                    {statusLabel}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="section-head">
        <div>
          <h2>데이터 수집 파이프라인</h2>
          <p>글로벌 AI 불안 신호 수집 · 필터링 · 분류 실시간 현황</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: healthColor, display: 'inline-block', boxShadow: `0 0 6px ${healthColor}` }} />
          <span style={{ color: healthColor, fontWeight: 700 }}>{healthLabel}</span>
          <span style={{ color: 'var(--color-text-muted)' }}>· 통과율 {pct(pass_count, total)}</span>
        </div>
      </div>

      {/* ── 상단 3개 패널: 파이프라인 / 소스 / 언어 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>

        {/* FUNNEL */}
        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            수집 처리 현황
          </p>
          {[
            { label: '수집됨', value: total, color: 'var(--color-text)', rate: null },
            { label: '채택', value: pass_count, color: 'var(--color-ok)', rate: pct(pass_count, total) },
            { label: '제외', value: fail_count, color: 'var(--color-text-muted)', rate: pct(fail_count, total) },
            { label: '분류 대기', value: pending_count, color: 'var(--color-warn)', rate: pct(pending_count, total) },
          ].map(({ label, value, color, rate }) => (
            <div key={label} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', alignItems: 'center', gap: '0.5rem', padding: '0.45rem 0', borderBottom: '1px solid var(--color-border)' }}>
              <span style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>{label}</span>
              <span style={{ fontSize: '0.75rem', color, fontWeight: 600, textAlign: 'right', minWidth: '3rem' }}>{rate ?? ''}</span>
              <span style={{ fontSize: '1.25rem', fontWeight: 800, color, textAlign: 'right', minWidth: '3rem', lineHeight: 1 }}>{value.toLocaleString('ko-KR')}</span>
            </div>
          ))}
        </div>

        {/* SOURCES */}
        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            데이터 소스
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {sources.map(src => (
              <div key={src.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: src.active ? 'var(--color-ok)' : 'var(--color-text-muted)',
                  boxShadow: src.active ? '0 0 5px var(--color-ok)' : 'none',
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{src.label}</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: src.active ? 'var(--color-text)' : 'var(--color-text-muted)' }}>
                      {src.active ? `${src.count.toLocaleString('ko-KR')}건` : SOURCE_STATUS_BADGE[src.status || 'standby']?.label || '미실행'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.73rem', color: 'var(--color-text-muted)', marginTop: '0.1rem' }}>
                    <span style={{ textTransform: 'uppercase', letterSpacing: '0.03em' }}>{src.channel || src.type}</span>
                    <span>{src.active ? relativeTime(src.last_ingested_at) : src.mode || '—'}</span>
                  </div>
                  {!src.active && src.notes && (
                    <div style={{ marginTop: '0.2rem', fontSize: '0.7rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {src.notes}
                    </div>
                  )}
                  {src.active && (
                    <div style={{ marginTop: '0.3rem', height: 3, borderRadius: 2, background: 'var(--color-border)', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.min(100, (src.count / Math.max(total, 1)) * 100)}%`, background: 'var(--color-accent)', borderRadius: 2 }} />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* LANGUAGES */}
        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            설정 언어 ({configured_languages.length}개)
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
            {configured_languages.map(lang => (
              <span
                key={lang.code}
                title={lang.label}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '6px',
                  background: 'var(--color-surface-lighter)',
                  border: '1px solid var(--color-border)',
                  fontSize: '0.78rem',
                  cursor: 'default',
                }}
              >
                <span style={{ fontSize: '1rem' }}>{lang.flag}</span>
                <span style={{ color: 'var(--color-text-muted)', fontWeight: 600 }}>{lang.code.toUpperCase()}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            기술 테마 클러스터
          </p>
          <div style={{ display: 'grid', gap: '0.45rem' }}>
            {topic_clusters.length === 0 ? (
              <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>아직 cluster 태깅 데이터가 없습니다.</div>
            ) : topic_clusters.map(item => (
              <div key={`physical-${item.cluster}`} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: '0.5rem', alignItems: 'center', padding: '0.5rem 0.6rem', border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700 }}>{clusterLabel(item.cluster)}</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{relativeTime(item.last_at || '')}</span>
                <span style={{ fontSize: '0.78rem', fontWeight: 700 }}>{item.count.toLocaleString('ko-KR')}건</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            교육 테마 클러스터
          </p>
          <div style={{ display: 'grid', gap: '0.45rem' }}>
            {edu_topic_clusters.length === 0 ? (
              <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>아직 cluster 태깅 데이터가 없습니다.</div>
            ) : edu_topic_clusters.map(item => (
              <div key={`edu-${item.cluster}`} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: '0.5rem', alignItems: 'center', padding: '0.5rem 0.6rem', border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700 }}>{clusterLabel(item.cluster)}</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{relativeTime(item.last_at || '')}</span>
                <span style={{ fontSize: '0.78rem', fontWeight: 700 }}>{item.count.toLocaleString('ko-KR')}건</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            기술 Push 후보
          </p>
          <div style={{ display: 'grid', gap: '0.45rem' }}>
            {(push_candidates?.physical_ai || []).slice(0, 5).map(item => (
              <div key={`push-tech-${item.cluster}-${item.title}`} style={{ padding: '0.55rem 0.65rem', border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: '0.15rem' }}>{clusterLabel(item.cluster)}</div>
                <div style={{ fontWeight: 700, fontSize: '0.8rem', lineHeight: 1.35 }}>{item.title}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            교육 Push 후보
          </p>
          <div style={{ display: 'grid', gap: '0.45rem' }}>
            {(push_candidates?.edu_consulting || []).slice(0, 5).map(item => (
              <div key={`push-edu-${item.cluster}-${item.title}`} style={{ padding: '0.55rem 0.65rem', border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: '0.15rem' }}>{clusterLabel(item.cluster)}</div>
                <div style={{ fontWeight: 700, fontSize: '0.8rem', lineHeight: 1.35 }}>{item.title}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            현재 수집 주제
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', marginBottom: '0.9rem' }}>
            {current_topics.map(item => (
              <span
                key={`${item.kind}-${item.topic}`}
                title={item.sample_title || item.reason || item.topic}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  padding: '0.28rem 0.55rem',
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                  background: item.kind === 'auto' ? 'rgba(80,180,255,0.12)' : 'var(--color-surface-lighter)',
                  fontSize: '0.78rem',
                }}
              >
                <span style={{ fontWeight: 700 }}>{item.topic}</span>
                <span style={{ color: 'var(--color-text-muted)' }}>{item.kind === 'auto' ? 'AUTO' : 'SEED'}</span>
              </span>
            ))}
          </div>
          <div style={{ display: 'grid', gap: '0.45rem' }}>
            {suggested_topics.slice(0, 6).map(item => (
              <div key={item.topic} style={{ padding: '0.55rem 0.65rem', border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.2rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.82rem' }}>{item.topic}</span>
                  <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                    근거 {item.evidence_count ?? 0}건
                  </span>
                </div>
                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.74rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {item.sample_title || item.reason}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel" style={{ padding: '1.25rem' }}>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
            CAPA / 자동 확장
          </p>
          <div style={{ display: 'grid', gap: '0.6rem', marginBottom: '0.9rem' }}>
            {[
              { key: 'mini', label: 'Mac Mini', meta: workers?.mini },
              { key: 'mbp', label: 'MBP', meta: workers?.mbp },
            ].map(({ key, label, meta }) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.84rem' }}>{label}</div>
                  <div style={{ fontSize: '0.73rem', color: 'var(--color-text-muted)' }}>{meta?.role || '—'}</div>
                </div>
                <span style={{ color: meta?.active ? 'var(--color-ok)' : 'var(--color-text-muted)', fontSize: '0.78rem', fontWeight: 700 }}>
                  {meta?.active ? '활성' : '대기'}
                </span>
              </div>
            ))}
          </div>
          <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>자동 생성 RSS 쿼리</span>
              <span style={{ fontWeight: 700 }}>{generated_query_sources.length}개</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: '0.45rem', color: 'var(--color-text-muted)' }}>
              <span>주제 자동 확장</span>
              <span>{expansion_policy?.auto_topic_expansion ? 'ON' : 'OFF'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: '0.55rem', color: 'var(--color-text-muted)' }}>
              <span>채널 자동 확장</span>
              <span>{expansion_policy?.auto_channel_expansion ? 'ON' : 'OFF'}</span>
            </div>
            <div style={{ display: 'grid', gap: '0.35rem' }}>
              {generated_query_sources.slice(0, 6).map(src => (
                <div key={src.name} style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {src.topic || src.name}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="panel" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
          채널 커버리지
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.7rem' }}>
          {channel_coverage.map(item => (
            <div key={item.channel} style={{ border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)', padding: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.35rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.82rem' }}>{item.label}</span>
                <span style={{ fontSize: '0.74rem', color: 'var(--color-text-muted)' }}>{item.total_sources}개</span>
              </div>
              <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', fontSize: '0.72rem', marginBottom: '0.35rem' }}>
                <span style={{ color: 'var(--color-ok)' }}>활성 {item.active_sources}</span>
                <span style={{ color: 'var(--color-warn)' }}>대기 {item.standby_sources}</span>
                <span style={{ color: 'var(--color-danger)' }}>제한 {item.restricted_sources}</span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                {item.preferred_worker ? `${item.preferred_worker.toUpperCase()} 우선` : '—'}
              </div>
              {item.notes?.[0] && (
                <div style={{ marginTop: '0.25rem', fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                  {item.notes[0]}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="panel" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
          Tier 2 분류 워커
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '0.75rem', marginBottom: '0.9rem' }}>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Pending</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800 }}>{tier2_worker?.pending_count?.toLocaleString('ko-KR') || 0}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>MBP 참여</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: tier2_worker?.mbp_active ? 'var(--color-ok)' : 'var(--color-text-muted)' }}>
              {tier2_worker?.mbp_active ? 'ON' : 'OFF'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>메인 워커</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: tier2_worker?.main?.running ? 'var(--color-ok)' : 'var(--color-text-muted)' }}>
              {tier2_worker?.main?.running ? 'RUN' : 'IDLE'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Fast lane</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: tier2_worker?.fast_lane?.running ? 'var(--color-warn)' : 'var(--color-text-muted)' }}>
              {tier2_worker?.fast_lane?.running ? 'RUN' : 'IDLE'}
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.8rem' }}>
          <div style={{ border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)', padding: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>메인 워커</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{tier2_worker?.main?.interval_seconds || 900}s</span>
            </div>
            <div style={{ fontSize: '0.73rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>
              pid {tier2_worker?.main?.pid ?? '—'} · exit {tier2_worker?.main?.last_exit_code ?? '—'}
            </div>
            {(tier2_worker?.main?.log_tail || []).slice(-2).map((line, idx) => (
              <div key={idx} style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {line}
              </div>
            ))}
          </div>
          <div style={{ border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)', padding: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>Fast lane</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                {(tier2_worker?.fast_lane?.interval_seconds || 300)}s / {tier2_worker?.fast_lane?.active_threshold || 4000}+
              </span>
            </div>
            <div style={{ fontSize: '0.73rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>
              pid {tier2_worker?.fast_lane?.pid ?? '—'} · exit {tier2_worker?.fast_lane?.last_exit_code ?? '—'}
            </div>
            {(tier2_worker?.fast_lane?.log_tail || []).slice(-2).map((line, idx) => (
              <div key={idx} style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {line}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="panel" style={{ padding: '1.25rem', marginBottom: '1rem' }}>
        <p style={{ margin: '0 0 1rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
          Persona Fallback
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.75rem', marginBottom: '0.9rem' }}>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Fallback 중</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800 }}>{persona_fallbacks?.fallback_count ?? 0}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Orchestration mode</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800 }}>{persona_fallbacks?.orchestration_provider_mode || 'auto'}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Jarvis reasoning</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800 }}>{persona_fallbacks?.jarvis_reasoning_provider || 'claude'}</div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.65rem' }}>
          {(persona_fallbacks?.personas || []).filter(p => p.fallback_active).map(item => (
            <div key={item.handle} style={{ border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)', padding: '0.7rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.2rem' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>{item.display}</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-warn)' }}>{item.primary_provider} → {item.active_provider}</span>
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                {item.reason || 'fallback_active'}
              </div>
            </div>
          ))}
          {(persona_fallbacks?.personas || []).filter(p => p.fallback_active).length === 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>현재 fallback 중인 persona 없음</div>
          )}
        </div>
        <div style={{ marginTop: '0.9rem' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: '0.45rem' }}>최근 10건</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
            {(persona_fallbacks?.recent_events || []).map((event, idx) => (
              <div key={`${event.ts}-${idx}`} style={{ border: '1px solid var(--color-border)', borderRadius: 6, background: 'var(--color-surface-lighter)', padding: '0.6rem 0.7rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.15rem' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700 }}>{event.persona_display}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{event.event_type}</span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                  {event.primary_provider} → {event.active_provider} · {event.reason || '-'}
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', marginTop: '0.15rem' }}>
                  {relativeTime(event.ts)}
                </div>
              </div>
            ))}
            {(persona_fallbacks?.recent_events || []).length === 0 && (
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>최근 fallback 이벤트 없음</div>
            )}
          </div>
        </div>
      </div>

      {/* ── 최근 활동 피드 ── */}
      <div className="panel" style={{ padding: '1.25rem' }}>
        <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
          최근 처리 내역
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {recent_activity.length === 0 && (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '1rem 0' }}>수집된 데이터가 없습니다.</p>
          )}
          {recent_activity.map((item, idx) => {
            const badge = STATUS_BADGE[item.status] ?? { label: item.status, color: 'var(--color-text-muted)' }
            return (
              <div key={idx} style={{
                display: 'grid',
                gridTemplateColumns: '110px 1fr 80px 90px',
                gap: '0.75rem',
                alignItems: 'center',
                padding: '0.5rem 0',
                borderBottom: idx < recent_activity.length - 1 ? '1px solid var(--color-border)' : 'none',
                fontSize: '0.8rem',
              }}>
                <span style={{ color: 'var(--color-text-muted)', fontWeight: 600, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {item.source.replace('_api', '').replace('semantic_', '')}
                </span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text)' }}>
                  {item.title}
                </span>
                <span style={{ color: badge.color, fontWeight: 700, textAlign: 'right' }}>{badge.label}</span>
                <span style={{ color: 'var(--color-text-muted)', textAlign: 'right' }}>{relativeTime(item.ingested_at)}</span>
              </div>
            )
          })}
        </div>
      </div>
      {/* ── Raw DB 적재 데이터 피드 ── */}
      <div className="panel" style={{ padding: '1.25rem', marginTop: '1rem' }}>
        <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
          DB 적재 원본 (raw_statistics_data)
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {rawStats.length === 0 && (
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '1rem 0' }}>적재된 알맹이 데이터가 없습니다.</p>
          )}
          {rawStats.map((item, idx) => (
            <div key={idx} 
              onClick={() => setSelectedRawStat(item)}
              style={{
                display: 'grid',
                gridTemplateColumns: '80px 1fr 1fr 100px',
                gap: '0.75rem',
                alignItems: 'center',
                padding: '0.5rem 0',
                borderBottom: idx < rawStats.length - 1 ? '1px solid var(--color-border)' : 'none',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}>
              <span style={{ color: 'var(--color-text-muted)', fontWeight: 600 }}>{item.source}</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-accent)', fontWeight: 600 }}>
                {item.file_name}
              </span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                {String(item.raw_content || '').substring(0, 100)}...
              </span>
              <span style={{ color: 'var(--color-text-muted)', textAlign: 'right' }}>{relativeTime(item.created_at)}</span>
            </div>
          ))}
        </div>
      </div>

      {selectedRawStat && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }} onClick={() => setSelectedRawStat(null)}>
          <div style={{
            background: 'var(--color-surface)', width: '80%', maxWidth: '800px', maxHeight: '80vh',
            borderRadius: '8px', padding: '1.5rem', display: 'flex', flexDirection: 'column',
            boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--color-text)' }}>{selectedRawStat.file_name}</h3>
              <button onClick={() => setSelectedRawStat(null)} style={{ background: 'transparent', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}>✕</button>
            </div>
            <div style={{
              flex: 1, overflowY: 'auto', background: 'var(--color-surface-lighter)',
              padding: '1rem', borderRadius: '6px', fontSize: '0.85rem', color: 'var(--color-text)',
              whiteSpace: 'pre-wrap', border: '1px solid var(--color-border)', fontFamily: 'monospace'
            }}>
              {selectedRawStat.raw_content || '내용 없음'}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
