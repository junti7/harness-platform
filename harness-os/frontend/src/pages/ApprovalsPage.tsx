import { useEffect, useMemo, useState } from 'react'
import type { ApprovalInboxPayload, ApprovalItem } from '../components/types'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  viewRole: 'ceo' | 'vp'
}

type InboxBox = 'pending' | 'resolved'

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export function ApprovalsPage({ apiBase, authHeaders, viewRole }: Props) {
  const [box, setBox] = useState<InboxBox>('pending')
  const [inbox, setInbox] = useState<ApprovalInboxPayload | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ApprovalItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showWorkflow, setShowWorkflow] = useState(false)
  const [acting, setActing] = useState<'approved' | 'rejected' | null>(null)
  const [modalDecision, setModalDecision] = useState<'approved' | 'rejected' | null>(null)
  const [decisionNote, setDecisionNote] = useState('')

  const fetchInbox = async (nextBox: InboxBox, preserveSelection = false) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/approvals?role=${viewRole}&box=${nextBox}`, {
        headers: authHeaders(),
      })
      if (!res.ok) throw new Error(`결재함 API ${res.status}`)
      const payload = (await res.json()) as ApprovalInboxPayload
      setInbox(payload)
      const nextSelectedId = preserveSelection ? selectedId : (payload.items[0]?.id ?? null)
      setSelectedId(nextSelectedId)
    } catch (err) {
      setError(err instanceof Error ? err.message : '결재함 로드 실패')
    } finally {
      setLoading(false)
    }
  }

  const fetchDetail = async (itemId: string | null) => {
    if (!itemId) {
      setDetail(null)
      return
    }
    setDetailLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/approvals/${itemId}?role=${viewRole}`, {
        headers: authHeaders(),
      })
      if (!res.ok) throw new Error(`결재 상세 API ${res.status}`)
      const payload = (await res.json()) as ApprovalItem
      setDetail(payload)
      setShowWorkflow(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : '결재 상세 로드 실패')
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    void fetchInbox(box)
  }, [box, viewRole])

  useEffect(() => {
    void fetchDetail(selectedId)
  }, [selectedId, viewRole])

  const decide = async (decision: 'approved' | 'rejected', note?: string) => {
    if (!detail) return
    setActing(decision)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/approvals/${detail.id}/decision`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          decision,
          actor_role: viewRole,
          note: note?.trim() ? note.trim() : null,
        }),
      })
      if (!res.ok) throw new Error(`결재 처리 API ${res.status}`)
      setModalDecision(null)
      setDecisionNote('')
      await fetchInbox(box, false)
    } catch (err) {
      setError(err instanceof Error ? err.message : '결재 처리 실패')
    } finally {
      setActing(null)
    }
  }

  const openDecisionModal = (decision: 'approved' | 'rejected') => {
    setModalDecision(decision)
    setDecisionNote('')
  }

  const closeDecisionModal = () => {
    if (acting) return
    setModalDecision(null)
    setDecisionNote('')
  }

  const emptyLabel = useMemo(() => (box === 'pending' ? '미결함에 결재 대기 항목이 없습니다.' : '기결함에 기록된 항목이 없습니다.'), [box])

  return (
    <section className="approval-page" style={{ display: 'grid', gap: '1rem' }}>
      <article className="panel" style={{ display: 'grid', gap: '1rem' }}>
        <div className="panel-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ margin: 0 }}>결재</h2>
            <p className="subtitle" style={{ marginTop: '0.35rem' }}>
              대표/부대표의 승인 이력과 OpenClaw handoff를 함께 남기는 정식 결재함입니다.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => setBox('pending')}
              style={{
                padding: '0.45rem 0.8rem',
                borderRadius: '999px',
                border: `1px solid ${box === 'pending' ? 'var(--color-accent)' : 'var(--color-border)'}`,
                background: box === 'pending' ? 'rgba(9, 132, 227, 0.12)' : 'var(--color-surface-lighter)',
                color: box === 'pending' ? 'var(--color-accent)' : 'var(--color-text-muted)',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              미결함 {inbox?.counts.pending ?? 0}
            </button>
            <button
              type="button"
              onClick={() => setBox('resolved')}
              style={{
                padding: '0.45rem 0.8rem',
                borderRadius: '999px',
                border: `1px solid ${box === 'resolved' ? 'var(--color-accent)' : 'var(--color-border)'}`,
                background: box === 'resolved' ? 'rgba(9, 132, 227, 0.12)' : 'var(--color-surface-lighter)',
                color: box === 'resolved' ? 'var(--color-accent)' : 'var(--color-text-muted)',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              기결함 {inbox?.counts.resolved ?? 0}
            </button>
          </div>
        </div>

        {error && (
          <div className="banner banner-error">
            <div className="banner-title">결재함 오류</div>
            <div className="banner-desc">{error}</div>
          </div>
        )}

        {inbox?.suspended && (
          <div className="banner" style={{ background: 'rgba(243, 156, 18, 0.08)', border: '1px solid rgba(243, 156, 18, 0.28)', borderRadius: '10px', padding: '0.9rem 1rem' }}>
            <div className="banner-title">결재 보류</div>
            <div className="banner-desc">{inbox.suspension_message}</div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 360px) minmax(0, 1fr)', gap: '1rem' }}>
          <div style={{ border: '1px solid var(--color-border)', borderRadius: '12px', overflow: 'hidden', background: 'var(--color-surface-lighter)' }}>
            <div style={{ padding: '0.9rem 1rem', borderBottom: '1px solid var(--color-border)', fontWeight: 700 }}>
              {box === 'pending' ? '미결함' : '기결함'}
            </div>
            {loading ? (
              <div style={{ padding: '1rem', color: 'var(--color-text-muted)' }}>결재 목록 로드 중…</div>
            ) : inbox && inbox.items.length > 0 ? (
              <div style={{ display: 'grid' }}>
                {inbox.items.map(item => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    style={{
                      textAlign: 'left',
                      padding: '1rem',
                      border: 'none',
                      borderBottom: '1px solid var(--color-border)',
                      background: selectedId === item.id ? 'rgba(9, 132, 227, 0.08)' : 'transparent',
                      color: 'var(--color-text)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontWeight: 700, lineHeight: 1.45 }}>{item.title}</div>
                    <div style={{ marginTop: '0.35rem', fontSize: '0.76rem', color: 'var(--color-text-muted)' }}>
                      {formatDateTime(item.submitted_at)}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div style={{ padding: '1rem', color: 'var(--color-text-muted)' }}>{emptyLabel}</div>
            )}
          </div>

          <div className="panel" style={{ minHeight: '420px' }}>
            {detailLoading ? (
              <div style={{ color: 'var(--color-text-muted)' }}>상세 결재문 로드 중…</div>
            ) : detail ? (
              <div style={{ display: 'grid', gap: '1rem' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.2rem', lineHeight: 1.4 }}>{detail.title}</h3>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>상신자</span>
                    <strong>{detail.submitter_display}</strong>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowWorkflow(value => !value)}
                    style={{
                      padding: '0.4rem 0.7rem',
                      borderRadius: '6px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface-lighter)',
                      color: 'var(--color-accent)',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    상황조회
                  </button>
                </div>

                {showWorkflow && (
                  <div style={{ border: '1px solid var(--color-border)', borderRadius: '10px', padding: '0.9rem 1rem', background: 'var(--color-surface-lighter)' }}>
                    {detail.workflow.map((row, idx) => (
                      <div key={`${row.stage}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 180px', gap: '0.75rem', alignItems: 'start', padding: idx === 0 ? '0 0 0.7rem 0' : '0.7rem 0 0 0', borderTop: idx === 0 ? 'none' : '1px solid var(--color-border)' }}>
                        <div style={{ fontWeight: 700 }}>{row.stage}</div>
                        <div>{row.actor}</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{formatDateTime(row.acted_at)}</div>
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
                  <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: '0.4rem' }}>상세 상신 내용</div>
                  <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65 }}>{detail.body}</div>
                </div>

                {detail.decision_note && (
                  <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
                    <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: '0.4rem' }}>결재 메모</div>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65 }}>{detail.decision_note}</div>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                    상태: <strong style={{ color: 'var(--color-text)' }}>{detail.status_label}</strong>
                  </div>
                  {detail.status === 'pending' ? (
                    <div style={{ display: 'flex', gap: '0.6rem' }}>
                      <button
                        type="button"
                        onClick={() => openDecisionModal('approved')}
                        disabled={acting !== null}
                        style={{
                          padding: '0.55rem 0.95rem',
                          borderRadius: '8px',
                          border: 'none',
                          background: 'var(--color-accent)',
                          color: '#fff',
                          fontWeight: 700,
                          cursor: acting ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {acting === 'approved' ? '처리 중…' : '결재'}
                      </button>
                      <button
                        type="button"
                        onClick={() => openDecisionModal('rejected')}
                        disabled={acting !== null}
                        style={{
                          padding: '0.55rem 0.95rem',
                          borderRadius: '8px',
                          border: '1px solid var(--color-border)',
                          background: 'var(--color-surface-lighter)',
                          color: 'var(--color-danger)',
                          fontWeight: 700,
                          cursor: acting ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {acting === 'rejected' ? '처리 중…' : '반려'}
                      </button>
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
                      결재 일시 {formatDateTime(detail.decided_at)}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--color-text-muted)' }}>좌측 목록에서 결재 건을 선택하세요.</div>
            )}
          </div>
        </div>
      </article>

      {modalDecision && detail && (
        <div className="approval-modal-backdrop" onClick={closeDecisionModal} role="presentation">
          <div
            className="approval-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="approval-modal-title"
            onClick={event => event.stopPropagation()}
          >
            <div className="approval-modal-head">
              <div>
                <div className="approval-modal-eyebrow">{modalDecision === 'approved' ? '결재 확인' : '반려 확인'}</div>
                <h3 id="approval-modal-title">
                  {modalDecision === 'approved' ? '최종 결재를 진행합니다.' : '이 결재건을 반려합니다.'}
                </h3>
              </div>
              <button type="button" className="approval-modal-close" onClick={closeDecisionModal} disabled={acting !== null}>
                닫기
              </button>
            </div>

            <div className="approval-modal-body">
              <div className="approval-modal-summary">
                <div className="approval-modal-label">결재 제목</div>
                <div className="approval-modal-value">{detail.title}</div>
              </div>

              <label className="approval-modal-field">
                <span className="approval-modal-label">결재 의견</span>
                <span className="approval-modal-hint">선택 입력입니다. 비워둬도 최종 결재 또는 반려가 가능합니다.</span>
                <textarea
                  className="approval-modal-textarea"
                  value={decisionNote}
                  onChange={event => setDecisionNote(event.target.value)}
                  placeholder={modalDecision === 'approved' ? '필요하면 승인 배경이나 지시사항을 남기세요.' : '필요하면 반려 사유나 재작업 지시를 남기세요.'}
                  rows={6}
                  disabled={acting !== null}
                />
              </label>
            </div>

            <div className="approval-modal-actions">
              <button type="button" className="approval-modal-secondary" onClick={closeDecisionModal} disabled={acting !== null}>
                취소
              </button>
              <button
                type="button"
                className={modalDecision === 'approved' ? 'approval-modal-primary' : 'approval-modal-danger'}
                onClick={() => void decide(modalDecision, decisionNote)}
                disabled={acting !== null}
              >
                {acting === modalDecision
                  ? modalDecision === 'approved'
                    ? '결재 처리 중…'
                    : '반려 처리 중…'
                  : modalDecision === 'approved'
                    ? '최종 결재'
                    : '최종 반려'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
