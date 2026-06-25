import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  Check,
  ChevronDown,
  Clock,
  ExternalLink,
  Loader2,
  Lock,
  Newspaper,
  PlayCircle,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Target,
} from 'lucide-react'
import { ApiError } from '@/lib/api'
import {
  fetchSession,
  rebuildCaseFromSavedCurriculum,
  saveStageArtifact,
  syncSession,
  trainingStateMatchesSavedCurriculum,
  type ChecklistItem,
  type CurriculumHighlight,
  type DynamicCurriculumItem,
  type PersonalizedCurriculum,
  type StageKey,
  type TrainingStage,
  type TrainingState,
} from '@/lib/vpTraining'

/*
 * TrainingScreen — 훈련 단계 흐름 (모바일 우선).
 * GET /session 으로 training_state 를 받아 day0/day1 단계를 읽고,
 * 단계 전환은 POST /session/sync, 단계 완료는 POST /artifact 로 서버에 반영한다.
 * day0 완료 시 day1 이 해금된다(백엔드 flow_outline 규칙).
 * Props 는 컨테이너(App.tsx)와의 계약이다.
 */
export type TrainingScreenProps = {
  caseId: number
  email: string
  onBack: () => void
}

const STAGE_ORDER: StageKey[] = ['day0', 'day1']
const STAGE_LABEL: Record<StageKey, string> = { day0: 'Day 0', day1: 'Day 1' }

function errMsg(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403) return '접근 권한이 없습니다. 다시 로그인해주세요.'
    return e.message || '요청 처리 중 문제가 발생했습니다.'
  }
  return '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
}

/** 단계의 체크리스트(없으면 합격 기준을 항목으로 변환). */
function stageChecklist(stage: TrainingStage | undefined): ChecklistItem[] {
  if (stage?.checklist?.length) return stage.checklist
  return (stage?.pass_fail_rubric ?? []).map((t, i) => ({ id: `rubric-${i}`, title: t }))
}

/** ui_state.selected_stage 우선, 단 day1 은 day0 완료 시에만 허용. */
function pickStage(st: TrainingState): StageKey {
  const want = st.ui_state?.selected_stage
  if (want === 'day1' && st.day0?.completed) return 'day1'
  return 'day0'
}

function llmLabel(value?: string): string {
  const v = (value ?? '').toLowerCase()
  if (v.includes('gpt') || v.includes('chatgpt')) return 'ChatGPT'
  if (v.includes('claude')) return 'Claude'
  if (v.includes('gemini')) return 'Gemini'
  return 'AI 도구'
}

function levelLabel(value?: string): string {
  if (value === 'advanced') return '고급'
  if (value === 'intermediate') return '중급'
  return '왕초보'
}

function trustScoreLabel(value?: number): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '검수 통과'
  return `검수 ${Math.round(value * 100)}%`
}

function trustReasons(highlight: CurriculumHighlight): string[] {
  return (highlight.trust_reasons?.length ? highlight.trust_reasons : highlight.relevance_reasons ?? []).slice(0, 2)
}

function segmentLabel(value?: string | null): string {
  if (value === 'parent') return '학부모'
  if (value === 'worker') return '직장인'
  return '사용자'
}

function ageLabel(days?: number | null): string {
  if (days === null || days === undefined || days >= 900) return '최근'
  if (days <= 0) return '오늘'
  if (days === 1) return '어제'
  return `${days}일 전`
}

function mediaLabel(kind?: string): string {
  if (kind === 'video') return '영상'
  if (kind === 'paper') return '논문/근거'
  if (kind === 'article') return '글/RSS'
  return '자료'
}

function MediaIcon({ kind }: { kind?: string }) {
  if (kind === 'video') return <PlayCircle size={16} />
  if (kind === 'paper') return <ScrollText size={16} />
  return <Newspaper size={16} />
}

function languageLabel(value?: string): string {
  if (value === 'ko') return '한국어'
  if (value === 'ja') return '일본어'
  if (value === 'zh') return '중국어'
  if (value) return '외국어'
  return ''
}

function youtubeVideoId(url?: string): string {
  if (!url) return ''
  try {
    const u = new URL(url)
    if (u.hostname.includes('youtu.be')) return u.pathname.replace('/', '')
    if (u.hostname.includes('youtube.com')) return u.searchParams.get('v') ?? ''
  } catch {
    return ''
  }
  return ''
}

function openSourceUrl(url?: string) {
  if (!url) return
  const videoId = youtubeVideoId(url)
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
  if (videoId && isMobile) {
    window.location.href = `youtube://watch?v=${videoId}`
    window.setTimeout(() => {
      window.open(url, '_blank', 'noopener,noreferrer')
    }, 900)
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

function PersonalizedDay0Block({
  curriculum,
  learnerName,
}: {
  curriculum: PersonalizedCurriculum
  learnerName: string
}) {
  const [selectedHighlight, setSelectedHighlight] = useState<CurriculumHighlight | null>(null)
  const [highlightsOpen, setHighlightsOpen] = useState(false)
  if (!curriculum.available) return null
  const attrs = curriculum.attrs ?? {}
  const fresh = curriculum.fresh_note
  const concern = curriculum.top_concerns[0]?.concern
  const topTopics = curriculum.order.slice(0, 3)
  const highlights = curriculum.highlights.slice(0, 12)
  const mediaTypes = Array.from(new Set(highlights.map((h) => mediaLabel(h.media_kind)))).slice(0, 3)
  return (
    <section className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-primary">
            <Sparkles size={13} />맞춤 시작점
          </div>
          <p className="text-sm font-semibold leading-relaxed text-ink-strong">
            {learnerName}님 상황({segmentLabel(curriculum.segment)} · {llmLabel(attrs.llm)} ·{' '}
            {levelLabel(attrs.level)})에 맞춰 Day 0를 다시 잡았어요.
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-card px-2.5 py-1 text-[11px] font-semibold text-primary shadow-sm">
          {ageLabel(fresh.newest_days_ago)} 반영
        </span>
      </div>

      <p className="text-sm leading-relaxed text-text-muted">
        {concern
          ? `같은 분들이 최근 많이 묻는 '${concern}' 흐름을 먼저 보고, 설치보다 첫 질문 성공에 무게를 둡니다.`
          : '같은 세그먼트의 최근 evidence를 기준으로 첫 질문 성공에 무게를 둡니다.'}
      </p>

      {topTopics.length ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {topTopics.map((item) => (
            <span
              key={item.topic}
              className="rounded-full border border-border bg-card px-2.5 py-1 text-[11px] font-semibold text-text-muted"
            >
              {item.topic}
            </span>
          ))}
        </div>
      ) : null}

      {highlights.length ? (
        <div className="mt-3 rounded-[12px] border border-border bg-card">
          <button
            type="button"
            onClick={() => setHighlightsOpen((v) => !v)}
            aria-expanded={highlightsOpen}
            className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left"
          >
            <div className="min-w-0">
              <div className="mb-1 flex flex-wrap items-center gap-1.5">
                <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-primary">
                  관련 자료 {highlights.length}개
                </span>
                <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-text-muted">
                  {ageLabel(fresh.newest_days_ago)} 기준
                </span>
                {mediaTypes.length ? (
                  <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-text-muted">
                    {mediaTypes.join(' · ')}
                  </span>
                ) : null}
              </div>
              <p className="line-clamp-2 text-xs leading-relaxed text-text-muted">
                {concern
                  ? `이 안에는 '${concern}'와 가까운 최근 자료, 원문/영상 링크, 짧은 발췌가 들어있어요.`
                  : '이 안에는 현재 학습 순서와 가까운 최근 자료, 원문/영상 링크, 짧은 발췌가 들어있어요.'}
              </p>
            </div>
            <ChevronDown
              size={17}
              className={`shrink-0 text-text-faint transition ${highlightsOpen ? 'rotate-180' : ''}`}
            />
          </button>
          {highlightsOpen ? (
            <div className="grid gap-2 border-t border-border p-3">
              {highlights.map((h) => (
                <div
                  key={`${h.title}-${h.days_ago}`}
                  className="rounded-[12px] border border-border bg-card p-3 text-left"
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-accent-cyan">
                      <MediaIcon kind={h.media_kind} />{mediaLabel(h.media_kind)}
                    </span>
                    <span className="shrink-0 text-[11px] font-medium text-text-faint">{ageLabel(h.days_ago)}</span>
                  </div>
                  <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                    <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-primary">
                      <ShieldCheck size={11} />{trustScoreLabel(h.trust_score ?? h.relevance_score)}
                    </span>
                    {trustReasons(h).map((reason) => (
                      <span
                        key={reason}
                        className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold text-text-muted"
                      >
                        {reason}
                      </span>
                    ))}
                  </div>
                  <p className="line-clamp-2 text-xs font-medium leading-relaxed text-ink">{h.title}</p>
                  {h.original_title ? (
                    <p className="mt-1 line-clamp-1 text-[11px] leading-relaxed text-text-faint">
                      원제: {h.original_title}
                    </p>
                  ) : null}
                  {h.excerpt ? (
                    <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-text-faint">{h.excerpt}</p>
                  ) : null}
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedHighlight(h)}
                      className="h-8 rounded-[9px] border border-border px-3 text-[11px] font-semibold text-ink"
                    >
                      {h.media_kind === 'video' ? h.script_label || '스크립트 전문' : '원문 보기'}
                    </button>
                    {h.url ? (
                      <button
                        type="button"
                        onClick={() => openSourceUrl(h.url)}
                        className="inline-flex h-8 items-center gap-1 rounded-[9px] bg-primary px-3 text-[11px] font-semibold text-primary-foreground"
                      >
                        {h.media_kind === 'video' ? 'YouTube 열기' : '링크 열기'} <ExternalLink size={12} />
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {selectedHighlight ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink-strong/40 px-4 pb-4"
          onClick={() => setSelectedHighlight(null)}
        >
          <div
            className="max-h-[86dvh] w-full max-w-[480px] overflow-y-auto rounded-2xl border border-border bg-card p-5 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-accent-cyan">
              {selectedHighlight.media_kind === 'video'
                ? selectedHighlight.script_label || '스크립트 전문'
                : mediaLabel(selectedHighlight.media_kind)}{' '}
              · {ageLabel(selectedHighlight.days_ago)} 확인
            </div>
            <h3 className="mb-3 text-base font-bold leading-snug text-ink-strong">{selectedHighlight.title}</h3>
            {selectedHighlight.original_title ? (
              <p className="mb-3 rounded-[12px] bg-secondary px-3 py-2 text-xs leading-relaxed text-text-muted">
                원제({languageLabel(selectedHighlight.language)}): {selectedHighlight.original_title}
              </p>
            ) : null}
            {selectedHighlight.source || selectedHighlight.url ? (
              <div className="mb-3 rounded-[12px] bg-secondary px-3 py-2 text-xs leading-relaxed text-text-muted">
                <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full bg-card px-2 py-0.5 text-[10px] font-semibold text-primary">
                    <ShieldCheck size={11} />{trustScoreLabel(selectedHighlight.trust_score ?? selectedHighlight.relevance_score)}
                  </span>
                  {trustReasons(selectedHighlight).map((reason) => (
                    <span
                      key={reason}
                      className="rounded-full bg-card px-2 py-0.5 text-[10px] font-semibold text-text-muted"
                    >
                      {reason}
                    </span>
                  ))}
                </div>
                {selectedHighlight.source ? <div>출처: {selectedHighlight.source}</div> : null}
                {selectedHighlight.url ? (
                  <button
                    type="button"
                    onClick={() => openSourceUrl(selectedHighlight.url)}
                    className="mt-1 inline-flex items-center gap-1 font-semibold text-primary"
                  >
                    {selectedHighlight.media_kind === 'video' ? 'YouTube 앱/영상 열기' : '원본 링크 열기'}{' '}
                    <ExternalLink size={12} />
                  </button>
                ) : null}
              </div>
            ) : null}
            {selectedHighlight.concern ? (
              <p className="mb-3 text-sm leading-relaxed text-text-muted">
                이 자료는 현재 선택한 상황과 가까운 고민인 ‘{selectedHighlight.concern}’ 흐름에서 올라온 항목입니다.
              </p>
            ) : null}
            {selectedHighlight.script_text || selectedHighlight.body || selectedHighlight.excerpt ? (
              <div className="mb-4 whitespace-pre-wrap rounded-[12px] border border-border bg-secondary/70 p-3 text-sm leading-relaxed text-ink">
                {selectedHighlight.script_text || selectedHighlight.body || selectedHighlight.excerpt}
              </div>
            ) : (
              <p className="mb-4 rounded-[12px] border border-border bg-secondary/70 p-3 text-sm leading-relaxed text-text-muted">
                {selectedHighlight.media_kind === 'video'
                  ? '이 영상은 아직 스크립트 전문이 적재되지 않았습니다. YouTube에서 영상을 바로 확인할 수 있습니다.'
                  : '이 항목은 제목과 링크 중심으로 수집된 자료입니다. 원본 링크에서 전체 내용을 바로 확인할 수 있습니다.'}
              </p>
            )}
            {selectedHighlight.models.length ? (
              <div className="mb-4 flex flex-wrap gap-1.5">
                {selectedHighlight.models.map((m) => (
                  <span key={m} className="rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold text-text-muted">
                    {m}
                  </span>
                ))}
              </div>
            ) : null}
            <button
              type="button"
              onClick={() => setSelectedHighlight(null)}
              className="flex h-11 w-full items-center justify-center rounded-[10px] bg-primary text-sm font-semibold text-primary-foreground"
            >
              닫기
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}

function DynamicPathPreview({
  items,
  meta,
}: {
  items: DynamicCurriculumItem[]
  meta?: TrainingState['adaptive_curriculum_meta']
}) {
  const [open, setOpen] = useState(false)
  if (!items.length) return null
  const topicCount = new Set(items.map((item) => item.topic)).size
  const concernCount = new Set(items.map((item) => item.concern)).size
  const activeLength = meta?.active_length ?? items.length
  const modules = meta?.modules ?? []
  return (
    <section className="rounded-2xl border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-faint">
            <Sparkles size={13} className="text-accent-cyan" />전체 커리큘럼 구조
          </div>
          <p className="text-sm font-semibold text-ink-strong">
            {activeLength.toLocaleString()}개 실습 · {modules.length || topicCount}개 모듈 · {concernCount}개 실제 고민
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="shrink-0 rounded-[10px] bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground"
        >
          전체 보기
        </button>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-[12px] bg-secondary px-2 py-2">
          <div className="text-base font-bold text-ink">{activeLength.toLocaleString()}</div>
          <div className="text-[10px] font-medium text-text-faint">실습</div>
        </div>
        <div className="rounded-[12px] bg-secondary px-2 py-2">
          <div className="text-base font-bold text-ink">{modules.length || topicCount}</div>
          <div className="text-[10px] font-medium text-text-faint">모듈</div>
        </div>
        <div className="rounded-[12px] bg-secondary px-2 py-2">
          <div className="text-base font-bold text-ink">{meta?.skipped_count ?? 0}</div>
          <div className="text-[10px] font-medium text-text-faint">스킵</div>
        </div>
      </div>
      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink-strong/40 px-4 pb-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="max-h-[88dvh] w-full max-w-[480px] overflow-hidden rounded-2xl border border-border bg-card shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-border p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-accent-cyan">개인화 전체 과정</div>
              <h3 className="mt-1 text-base font-bold text-ink-strong">
                {activeLength.toLocaleString()}개 실습이 수집 자료와 목표에 따라 생성됨
              </h3>
            </div>
            <ol className="max-h-[68dvh] overflow-y-auto p-3">
              {(modules.length ? modules : []).map((mod) => (
                <li key={`${mod.module}-${mod.topic}`} className="mb-2 rounded-[12px] bg-secondary px-3 py-3">
                  <div className="text-xs font-semibold text-primary">
                    {mod.title} · {mod.lesson_count}개 실습
                  </div>
                  <div className="mt-1 text-sm font-semibold leading-snug text-ink">{mod.outcome}</div>
                  {mod.concerns?.length ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {mod.concerns.map((c) => (
                        <span key={c} className="rounded-full bg-card px-2 py-0.5 text-[10px] font-medium text-text-muted">
                          {c}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {mod.sample_missions?.length ? (
                    <div className="mt-2 text-xs leading-relaxed text-text-faint">{mod.sample_missions[0]}</div>
                  ) : null}
                </li>
              ))}
              {!modules.length
                ? items.slice(0, 24).map((item) => (
                    <li key={item.key} className="mb-2 rounded-[12px] bg-secondary px-3 py-2.5">
                      <div className="text-xs font-semibold text-primary">Day {item.day} · {item.topic}</div>
                      <div className="mt-0.5 text-sm font-medium leading-snug text-ink">{item.concern}</div>
                      <div className="mt-1 text-xs leading-relaxed text-text-faint">{item.mission}</div>
                    </li>
                  ))
                : null}
            </ol>
            <div className="border-t border-border p-3">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="flex h-11 w-full items-center justify-center rounded-[10px] bg-primary text-sm font-semibold text-primary-foreground"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default function TrainingScreen({ caseId, email, onBack }: TrainingScreenProps) {
  const [state, setState] = useState<TrainingState | null>(null)
  const [exists, setExists] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState<StageKey>('day0')
  const [proof, setProof] = useState('')
  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [whyOpen, setWhyOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const seqRef = useRef(0)

  // 단계 전환 시 로컬 입력(증거물/체크)을 그 단계 값으로 재시드.
  function hydrateStageInputs(st: TrainingState, next: StageKey) {
    setStage(next)
    setProof(String(st[next]?.proof_artifact ?? ''))
    setChecked({})
    setWhyOpen(false)
    setNotice(null)
  }

  // 마운트 시 세션 1회 로드. setState 는 async 콜백 안에서만 호출.
  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const r = await fetchSession(email, caseId)
        if (!alive) return
        if (!r.exists) {
          setExists(false)
          setLoading(false)
          return
        }
        let nextState = r.state
        if (!trainingStateMatchesSavedCurriculum(nextState)) {
          nextState = await rebuildCaseFromSavedCurriculum(email, caseId, String(nextState.customer?.name || ''))
        }
        if (!alive) return
        seqRef.current = Math.max(seqRef.current, Number(nextState.ui_state?.last_client_seq ?? 0))
        setState(nextState)
        hydrateStageInputs(nextState, pickStage(nextState))
        setLoading(false)
      } catch (e) {
        if (!alive) return
        setError(errMsg(e))
        setLoading(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [email, caseId])

  function selectStage(next: StageKey) {
    if (!state || next === stage) return
    if (next === 'day1' && !state.day0?.completed) return // 잠금
    hydrateStageInputs(state, next)
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: next,
      clientSeq: seqRef.current,
      eventName: 'select_stage',
      eventPayload: { selected_stage: next },
    }).catch((e) => console.error('syncSession failed', e))
  }

  function toggleCheck(id: string) {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  async function completeStage() {
    if (!state || saving || !proof.trim()) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const next = await saveStageArtifact({
        caseId,
        stage,
        proofArtifact: proof.trim(),
        completed: true,
      })
      setState(next)
      // day0 를 막 완료했으면 해금된 day1 로 이동, 아니면 현재 단계 유지하며 입력 재시드.
      if (stage === 'day0' && next.day0?.completed) {
        hydrateStageInputs(next, 'day1')
        setNotice('Day 0 완료! Day 1이 열렸어요. ✓')
      } else {
        setProof(String(next[stage]?.proof_artifact ?? ''))
        setNotice('저장했어요. ✓')
      }
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  // ── 렌더 ──────────────────────────────────────────────
  const header = (
    <header className="mb-5 flex items-center gap-3">
      <button
        type="button"
        onClick={onBack}
        aria-label="목록으로"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-card text-text-muted transition hover:text-ink"
      >
        <ArrowLeft size={18} />
      </button>
      <div className="flex min-w-0 flex-col">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-text-faint">
          훈련 세션
        </span>
        <h1 className="truncate text-lg font-bold text-ink-strong">
          {String(state?.case?.case_label ?? `훈련 #${caseId}`)}
        </h1>
      </div>
    </header>
  )

  if (loading) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7">
        {header}
        <div className="flex flex-1 items-center justify-center gap-2 text-text-muted">
          <Loader2 size={18} className="animate-spin" />
          <span className="text-sm">세션 불러오는 중…</span>
        </div>
      </div>
    )
  }

  if (!exists) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7">
        {header}
        <div className="mt-6 flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-12 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
            <Target size={24} />
          </span>
          <p className="text-sm font-medium text-ink">이 케이스에 훈련 데이터가 없어요</p>
          <p className="text-xs leading-relaxed text-text-faint">
            목록에서 ‘새 훈련 시작’으로 케이스를 다시 만들어보세요.
          </p>
        </div>
      </div>
    )
  }

  const current = state?.[stage]
  const items = stageChecklist(current)
  const doneCount = items.filter((it) => checked[it.id]).length
  const day1Locked = !state?.day0?.completed
  const overallPct = Math.min(100, Math.max(0, Math.round(state?.progress?.pct ?? 0)))
  const learnerName = String(state?.customer?.name || '오늘의 학습자')
  const personalizedCurriculum =
    stage === 'day0' && state?.personalized_curriculum?.available ? state.personalized_curriculum : null
  const dynamicPath = stage === 'day0' ? state?.dynamic_curriculum_path ?? [] : []

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7">
      {header}

      {/* 전체 진행률 */}
      <div className="mb-4 flex items-center gap-2.5">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
          <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${overallPct}%` }} />
        </div>
        <span className="w-9 shrink-0 text-right text-xs font-semibold tabular-nums text-text-muted">
          {overallPct}%
        </span>
      </div>

      {/* 단계 탭 */}
      <div className="mb-5 grid grid-cols-2 gap-1 rounded-[12px] bg-secondary p-1">
        {STAGE_ORDER.map((k) => {
          const locked = k === 'day1' && day1Locked
          const done = Boolean(state?.[k]?.completed)
          const active = stage === k
          return (
            <button
              key={k}
              type="button"
              onClick={() => selectStage(k)}
              disabled={locked}
              aria-pressed={active}
              className={`flex h-10 items-center justify-center gap-1.5 rounded-[9px] text-sm font-semibold transition ${
                active
                  ? 'bg-card text-ink-strong shadow-sm'
                  : locked
                    ? 'cursor-not-allowed text-text-faint'
                    : 'text-text-muted hover:text-ink'
              }`}
            >
              {locked ? <Lock size={13} /> : done ? <Check size={14} className="text-success" /> : null}
              {STAGE_LABEL[k]}
            </button>
          )
        })}
      </div>

      {/* 단계 본문 */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-base font-bold leading-snug text-ink-strong">
              {String(current?.title ?? STAGE_LABEL[stage])}
            </h2>
            {current?.completed ? (
              <span className="shrink-0 rounded-full bg-success-soft px-2.5 py-0.5 text-[11px] font-semibold text-success">
                완료
              </span>
            ) : null}
          </div>
          {typeof current?.estimated_minutes === 'number' ? (
            <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-text-muted">
              <Clock size={13} />약 {current.estimated_minutes}분
            </span>
          ) : null}
        </div>

        {personalizedCurriculum ? (
          <PersonalizedDay0Block curriculum={personalizedCurriculum} learnerName={learnerName} />
        ) : null}

        {dynamicPath.length ? (
          <DynamicPathPreview items={dynamicPath} meta={state?.adaptive_curriculum_meta} />
        ) : null}

        {/* 왜 배우나요 (접이식) */}
        {current?.learning_why || current?.learning_outcome ? (
          <div className="rounded-2xl border border-border bg-card">
            <button
              type="button"
              onClick={() => setWhyOpen((v) => !v)}
              className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-semibold text-ink"
            >
              왜 배우나요?
              <ChevronDown
                size={17}
                className={`shrink-0 text-text-faint transition ${whyOpen ? 'rotate-180' : ''}`}
              />
            </button>
            {whyOpen ? (
              <div className="flex flex-col gap-2.5 border-t border-border px-4 py-3.5 text-sm leading-relaxed text-text-muted">
                {current?.learning_why ? <p>{current.learning_why}</p> : null}
                {current?.learning_outcome ? (
                  <p className="text-text-faint">{current.learning_outcome}</p>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* 오늘의 미션 */}
        {current?.required_action ? (
          <div className="rounded-2xl border border-border bg-accent/40 p-4">
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-accent-cyan">
              <Sparkles size={13} />오늘의 미션
            </div>
            <p className="text-sm leading-relaxed text-ink">{current.required_action}</p>
          </div>
        ) : null}

        {/* 체크리스트 */}
        {items.length > 0 ? (
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-ink">단계 체크리스트</span>
              <span className="text-xs font-medium tabular-nums text-text-faint">
                {doneCount}/{items.length}
              </span>
            </div>
            <ul className="flex flex-col gap-2">
              {items.map((it) => {
                const on = Boolean(checked[it.id])
                return (
                  <li key={it.id}>
                    <button
                      type="button"
                      onClick={() => toggleCheck(it.id)}
                      className="flex w-full items-start gap-3 rounded-[12px] border border-border bg-card p-3.5 text-left transition active:scale-[0.99]"
                    >
                      <span
                        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                          on ? 'border-primary bg-primary text-primary-foreground' : 'border-border-strong'
                        }`}
                      >
                        {on ? <Check size={14} strokeWidth={3} /> : null}
                      </span>
                      <span className="flex min-w-0 flex-col gap-0.5">
                        <span className={`text-sm font-medium ${on ? 'text-text-faint line-through' : 'text-ink'}`}>
                          {it.title}
                        </span>
                        {it.instruction ? (
                          <span className="text-xs leading-relaxed text-text-faint">{it.instruction}</span>
                        ) : null}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ) : null}

        {/* 증거물 + 완료 */}
        <div className="flex flex-col gap-2.5">
          <label className="text-sm font-semibold text-ink" htmlFor="proof">
            결과 붙여넣기
          </label>
          <textarea
            id="proof"
            value={proof}
            onChange={(e) => setProof(e.target.value)}
            rows={4}
            placeholder={String(current?.proof_artifact_hint ?? 'AI가 답한 결과나 내가 고친 문장을 붙여넣으세요.')}
            className="w-full resize-y rounded-[12px] border border-border bg-card px-3.5 py-3 text-sm leading-relaxed text-ink outline-none transition placeholder:text-text-faint focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"
          />

          {error ? (
            <div className="flex items-start gap-2 rounded-[10px] bg-danger-soft px-3.5 py-3 text-sm text-danger">
              <AlertCircle size={17} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}
          {notice ? (
            <div className="flex items-center gap-2 rounded-[10px] bg-success-soft px-3.5 py-3 text-sm font-medium text-success">
              <Check size={16} className="shrink-0" />
              <span>{notice}</span>
            </div>
          ) : null}

          <button
            type="button"
            onClick={completeStage}
            disabled={saving || !proof.trim()}
            className="mt-1 flex h-12 items-center justify-center gap-2 rounded-[10px] bg-primary text-[15px] font-semibold text-primary-foreground transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? <Loader2 size={18} className="animate-spin" /> : null}
            {saving ? '저장 중…' : current?.completed ? '완료 상태 업데이트' : '이 단계 완료로 표시'}
          </button>
          {!proof.trim() ? (
            <p className="text-center text-xs text-text-faint">결과를 한 줄이라도 붙여넣으면 완료할 수 있어요.</p>
          ) : null}
        </div>
      </div>
    </div>
  )
}
