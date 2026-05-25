import type { DashboardPayload } from './types'

type Monitor = NonNullable<DashboardPayload['data_collection_monitor']>

type Props = { monitor: Monitor }

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  pending:       { label: 'Pending',  color: 'var(--color-warn)' },
  filtered_pass: { label: 'Passed',   color: 'var(--color-ok)' },
  filtered_fail: { label: 'Failed',   color: 'var(--color-text-muted)' },
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

export function DataCollectionMonitor({ monitor }: Props) {
  const { total, pending_count, pass_count, fail_count, sources = [], configured_languages = [], recent_activity = [] } = monitor
  const passRate = total ? (pass_count / total) * 100 : 0

  const healthVariant = passRate >= 15 ? 'ok' : passRate >= 5 ? 'warn' : 'danger'
  const healthColor = healthVariant === 'ok' ? 'var(--color-ok)' : healthVariant === 'warn' ? 'var(--color-warn)' : 'var(--color-danger)'
  const healthLabel = healthVariant === 'ok' ? '정상' : healthVariant === 'warn' ? '주의' : '저품질'

  return (
    <section className="ops-section" style={{ marginTop: '1.5rem' }}>
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
            Pipeline Funnel
          </p>
          <FunnelRow label="수집됨" value={total} color="var(--color-text)" bold />
          <FunnelArrow label={`→ ${pct(pass_count, total)}`} color="var(--color-ok)" />
          <FunnelRow label="통과 (Pass)" value={pass_count} color="var(--color-ok)" />
          <FunnelArrow label={`→ ${pct(fail_count, total)}`} color="var(--color-text-muted)" />
          <FunnelRow label="탈락 (Fail)" value={fail_count} color="var(--color-text-muted)" />
          <FunnelArrow label={`→ ${pct(pending_count, total)}`} color="var(--color-warn)" />
          <FunnelRow label="대기 (Pending)" value={pending_count} color="var(--color-warn)" />
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
                      {src.active ? `${src.count.toLocaleString('ko-KR')}건` : '미실행'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.73rem', color: 'var(--color-text-muted)', marginTop: '0.1rem' }}>
                    <span style={{ textTransform: 'uppercase', letterSpacing: '0.03em' }}>{src.type}</span>
                    <span>{src.active ? relativeTime(src.last_ingested_at) : '—'}</span>
                  </div>
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
    </section>
  )
}

function FunnelRow({ label, value, color, bold }: { label: string; value: number; color: string; bold?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.15rem' }}>
      <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ fontSize: bold ? '1.4rem' : '1.1rem', fontWeight: 800, color, lineHeight: 1 }}>
        {value.toLocaleString('ko-KR')}
      </span>
    </div>
  )
}

function FunnelArrow({ label, color }: { label: string; color: string }) {
  return (
    <div style={{ textAlign: 'center', fontSize: '0.72rem', color, margin: '0.1rem 0', opacity: 0.8 }}>
      {label}
    </div>
  )
}
