import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ApprovalInboxPayload, ApprovalItem } from '../components/types'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  viewRole: 'ceo' | 'vp'
}

type InboxBox = 'pending' | 'resolved'

const APPROVAL_TYPE_LABELS: Record<string, string> = {
  signal_approve: '신호 검토',
  opportunity_approve: '사업기회 검토',
  vice_president_review_request: '부대표 검토 요청',
  customer_test_approve: '고객 검증 검토',
  monetization_experiment_approve: '수익화 실험 검토',
  report_publish_approve: '보고서 발행 검토',
  investment_thesis_approve: '투자 검토',
  capital_action_approve: '자본 집행 검토',
  legal_review_approve: '법무 검토',
  red_team_clear: '레드팀 통과',
  pre_mortem_approve: '사전 검토 통과',
  qa_clear: '품질 검증 통과',
  turtle_gate_clear: 'Turtle Gate 통과',
  turtle_gate_block: 'Turtle Gate 보류',
  trading_turtle_override: 'Turtle 규칙 예외 승인',
}

const TARGET_TYPE_LABELS: Record<string, string> = {
  signal: '신호',
  business_opportunity: '사업기회',
  customer_hypothesis: '고객 가설',
  monetization_experiment: '수익화 실험',
  research_report: '리포트',
  investment_thesis: '투자 논리',
  capital_action: '자본 집행',
  legal_review: '법무 검토',
  red_team: '레드팀 검토',
  pre_mortem: '사전 검토',
  qa: '품질 검증',
  approval: '결재',
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function labelize(value?: string | null, map?: Record<string, string>): string {
  if (!value) return '-'
  return map?.[value] ?? value.replaceAll('_', ' ')
}

function formatMetaValue(value?: string | number | null): string {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}

function roleLabel(role: 'ceo' | 'vp'): string {
  return role === 'ceo' ? 'CEO' : 'VP'
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

  const fetchInbox = useCallback(async (nextBox: InboxBox, preserveSelection = false) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/approvals?role=${viewRole}&box=${nextBox}`, {
        headers: authHeaders(),
      })
      if (!res.ok) throw new Error(`결재함 API ${res.status}`)
      const payload = (await res.json()) as ApprovalInboxPayload
      setInbox(payload)
      setSelectedId(current => (preserveSelection ? current : (payload.items[0]?.id ?? null)))
    } catch (err) {
      setError(err instanceof Error ? err.message : '결재함 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [apiBase, authHeaders, viewRole])

  const fetchDetail = useCallback(async (itemId: string | null) => {
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
  }, [apiBase, authHeaders, viewRole])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchInbox(box)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [box, fetchInbox])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchDetail(selectedId)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [fetchDetail, selectedId])

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
  const selectedCount = inbox?.items.length ?? 0

  const detailFields = useMemo(() => {
    if (!detail) return []

    return [
      { label: '상신자', value: detail.submitter_display },
      { label: '결재 대상', value: detail.target_type ? `${labelize(detail.target_type, TARGET_TYPE_LABELS)}${detail.target_id ? ` #${detail.target_id}` : ''}` : '-' },
      { label: '승인 유형', value: labelize(detail.approval_type, APPROVAL_TYPE_LABELS) },
      { label: '결재 구분', value: roleLabel(detail.approver_role) },
      { label: '상신 시각', value: formatDateTime(detail.submitted_at) },
      { label: '상태', value: detail.status_label },
      detail.decided_by_display ? { label: '처리자', value: detail.decided_by_display } : null,
      detail.correlation_id ? { label: '연결 ID', value: detail.correlation_id } : null,
      detail.openclaw_route ? { label: 'OpenClaw 경로', value: detail.openclaw_route } : null,
      detail.openclaw_command ? { label: 'OpenClaw 명령', value: detail.openclaw_command } : null,
    ].filter(Boolean) as Array<{ label: string; value: string }>
  }, [detail])

  return (
    <section className="approval-page">
      <article className="panel approval-shell">
        <div className="panel-head approval-head">
          <div className="approval-head-copy">
            <h2>결재</h2>
            <p className="subtitle">
              대표와 부대표가 모바일에서도 바로 판단할 수 있도록, 목록·상세·처리를 한 화면에서 읽히는 흐름으로 구성합니다.
            </p>
          </div>

          <div className="approval-box-switch" role="tablist" aria-label="결재함 선택">
            <button
              type="button"
              className={box === 'pending' ? 'approval-box-switch-button is-active' : 'approval-box-switch-button'}
              onClick={() => setBox('pending')}
              aria-pressed={box === 'pending'}
            >
              미결함 <span>{inbox?.counts.pending ?? 0}</span>
            </button>
            <button
              type="button"
              className={box === 'resolved' ? 'approval-box-switch-button is-active' : 'approval-box-switch-button'}
              onClick={() => setBox('resolved')}
              aria-pressed={box === 'resolved'}
            >
              기결함 <span>{inbox?.counts.resolved ?? 0}</span>
            </button>
          </div>
        </div>

        <div className="approval-summary-row">
          <div className="approval-summary-card">
            <span className="approval-summary-label">현재 목록</span>
            <strong>{box === 'pending' ? '미결함' : '기결함'}</strong>
          </div>
          <div className="approval-summary-card">
            <span className="approval-summary-label">표시 항목</span>
            <strong>{selectedCount}건</strong>
          </div>
          <div className="approval-summary-card">
            <span className="approval-summary-label">현재 역할</span>
            <strong>{roleLabel(viewRole)}</strong>
          </div>
          <div className="approval-summary-card">
            <span className="approval-summary-label">마지막 갱신</span>
            <strong>{formatDateTime(inbox?.updated_at ?? inbox?.generated_at)}</strong>
          </div>
        </div>

        {error && (
          <div className="banner banner-error">
            <div className="banner-title">결재함 오류</div>
            <div className="banner-desc">{error}</div>
          </div>
        )}

        {inbox?.suspended && (
          <div className="banner approval-warning-banner">
            <div className="banner-title">결재 보류</div>
            <div className="banner-desc">{inbox.suspension_message}</div>
          </div>
        )}

        <div className="approval-layout">
          <aside className="approval-list-panel">
            <div className="approval-panel-title">
              {box === 'pending' ? '미결함' : '기결함'}
            </div>

            {loading ? (
              <div className="approval-empty">결재 목록을 불러오는 중입니다…</div>
            ) : inbox && inbox.items.length > 0 ? (
              <div className="approval-list" role="list">
                {inbox.items.map(item => {
                  const isSelected = selectedId === item.id
                  const itemMeta = [
                    item.approval_type ? labelize(item.approval_type, APPROVAL_TYPE_LABELS) : null,
                    item.target_type ? labelize(item.target_type, TARGET_TYPE_LABELS) : null,
                  ].filter(Boolean)

                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={isSelected ? 'approval-item-card is-selected' : 'approval-item-card'}
                      onClick={() => setSelectedId(item.id)}
                      aria-pressed={isSelected}
                    >
                      <div className="approval-item-topline">
                        <div className="approval-item-title">{item.title}</div>
                        <div className="approval-item-status">{item.status_label}</div>
                      </div>
                      <div className="approval-item-meta">
                        <span>{item.submitter_display}</span>
                        <span>{formatDateTime(item.submitted_at)}</span>
                      </div>
                      {itemMeta.length > 0 && <div className="approval-item-tags">{itemMeta.map(value => <span key={value}>{value}</span>)}</div>}
                    </button>
                  )
                })}
              </div>
            ) : (
              <div className="approval-empty">{emptyLabel}</div>
            )}
          </aside>

          <main className="approval-detail-panel">
            {detailLoading ? (
              <div className="approval-empty">상세 결재문을 불러오는 중입니다…</div>
            ) : detail ? (
              <>
                <div className="approval-detail-head">
                  <div className="approval-detail-head-copy">
                    <div className="approval-detail-kicker">{detail.status_label}</div>
                    <h3 className="approval-detail-title">{detail.title}</h3>
                    <div className="approval-detail-subtitle">
                      <span>{detail.submitter_display}</span>
                      <span className="approval-separator">·</span>
                      <span>{formatDateTime(detail.submitted_at)}</span>
                    </div>
                  </div>

                  <button type="button" className="approval-workflow-toggle" onClick={() => setShowWorkflow(value => !value)}>
                    {showWorkflow ? '워크플로우 닫기' : '워크플로우 보기'}
                  </button>
                </div>

                <section className="approval-meta-grid" aria-label="결재 핵심 정보">
                  {detailFields.map(field => (
                    <div key={field.label} className="approval-meta-card">
                      <div className="approval-meta-label">{field.label}</div>
                      <div className="approval-meta-value">{formatMetaValue(field.value)}</div>
                    </div>
                  ))}
                </section>

                {showWorkflow && (
                  <section className="approval-workflow-card" aria-label="결재 흐름">
                    <div className="approval-section-label">결재 흐름</div>
                    <div className="approval-workflow-list">
                      {detail.workflow.map((row, idx) => (
                        <div key={`${row.stage}-${idx}`} className="approval-workflow-row">
                          <div className="approval-workflow-stage">{row.stage}</div>
                          <div className="approval-workflow-actor">{row.actor}</div>
                          <div className="approval-workflow-time">{formatDateTime(row.acted_at)}</div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                <section className="approval-content-card">
                  <div className="approval-section-label">상세 내용</div>
                  <div className="approval-body-copy">{detail.body}</div>
                </section>

                {detail.decision_note && (
                  <section className="approval-content-card">
                    <div className="approval-section-label">결재 메모</div>
                    <div className="approval-body-copy">{detail.decision_note}</div>
                  </section>
                )}

                <section className="approval-action-panel">
                  <div className="approval-action-status">
                    {detail.status === 'pending' ? '아직 처리되지 않은 결재입니다.' : `결재 완료 시각 ${formatDateTime(detail.decided_at)}`}
                  </div>

                  {detail.status === 'pending' ? (
                    <div className="approval-action-buttons">
                      <button
                        type="button"
                        onClick={() => openDecisionModal('rejected')}
                        disabled={acting !== null}
                        className="approval-action-button is-danger"
                      >
                        {acting === 'rejected' ? '반려 처리 중…' : '반려'}
                      </button>
                      <button
                        type="button"
                        onClick={() => openDecisionModal('approved')}
                        disabled={acting !== null}
                        className="approval-action-button is-primary"
                      >
                        {acting === 'approved' ? '결재 처리 중…' : '결재'}
                      </button>
                    </div>
                  ) : (
                    <div className="approval-action-done">결재 일시 {formatDateTime(detail.decided_at)}</div>
                  )}
                </section>
              </>
            ) : (
              <div className="approval-empty">왼쪽 목록에서 결재 건을 선택하세요.</div>
            )}
          </main>
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
