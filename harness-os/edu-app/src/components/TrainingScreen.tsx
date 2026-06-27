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
  Trash2,
} from 'lucide-react'
import { ApiError } from '@/lib/api'
import {
  askSafetyCoach,
  fetchSession,
  routeSafetyQuestion,
  saveStageArtifact,
  syncSession,
  type ChecklistItem,
  type CurriculumHighlight,
  type DynamicCurriculumItem,
  type PersonalizedCurriculum,
  type PlannedCurriculumItem,
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
const SAFETY_COACH_ANSWER_VERSION = '2026-06-27-rag-query-v6'
type SafetyConceptFeedback = Record<string, string>
type SafetyCoachAnswers = Record<string, {
  answer: string
  model?: string
  fallbackUsed?: boolean
  question?: string
  version?: string
  duplicateReused?: boolean
  evidenceUsed?: boolean
}>
type SafetyCoachThreadItem = {
  id: string
  conceptId: string
  conceptTitle: string
  question: string
  answer: string
  model?: string
  fallbackUsed?: boolean
  evidenceUsed?: boolean
  version: string
  createdAt: string
}
type SafetyCoachThreads = SafetyCoachThreadItem[]
type SafetyCoachThreadGroup = {
  stage: StageKey
  label: string
  items: SafetyCoachThreads
}
type SafetyDeletedAnswerKeys = string[]
type FoundationConcept = NonNullable<TrainingStage['foundation_concepts']>[number]
type RoutedQuestionTarget = {
  target: FoundationConcept & { checkId: string }
  targetIndex: number
}
type DeferredSafetyQuestion = {
  id: string
  question: string
  sourceConceptId: string
  sourceConceptTitle: string
  status: 'unassigned'
  targetDay?: number
  targetTitle?: string
  bridgeAnswer: string
  createdAt: string
}
type DeferredSafetyQuestions = DeferredSafetyQuestion[]

function safetyAnswerKey(conceptId: string, version: string | undefined, question: string | undefined): string {
  return `${conceptId}::${version || SAFETY_COACH_ANSWER_VERSION}::${(question || '').trim()}`
}

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

function conceptId(concept: NonNullable<TrainingStage['foundation_concepts']>[number], index: number): string {
  return concept.id || `safety_concept_${index}`
}

function routeKeywords(text: string): string[] {
  const normalized = text.toLowerCase()
  const tokens = new Set((normalized.match(/[0-9a-zA-Z가-힣]{2,}/g) ?? []).map((token) => {
    if (token.endsWith('하나요') || token.endsWith('해요') || token.endsWith('해')) return token.replace(/(하나요|해요|해)$/, '')
    return token.replace(/(은|는|이|가|을|를|에|의|으로|에서|에게)$/, '')
  }))
  const groups: Array<[string[], string[]]> = [
    [['명사', '조사', '단어', '토큰', '이어질', '다음', '추측', '확률'], ['다음', '말', '고르는', '가능성', '숫자', '반복']],
    [['transformer', '트랜스포머', 'attention', '어텐션', '논문', '저자'], ['transformer', 'attention', '논문', '중요한']],
    [['다정', '친구', '사람', '감정', '마음', '의존'], ['사람', '다정', '책임', '친구', '보호자', '감정']],
    [['잘못', '피해', '문제', '과의존', '검증', '맡기', '맡길', '오래'], ['잘못', '피해', '검증', '민감', '개인정보', '현실', '브레이크', '멈춰']],
    [['안전장치', '우회', '위험', '자해', '전문가'], ['안전장치', '위험', '경계', '사람']],
    [['돈', '법률', '건강', '개인정보', '민감정보', '일정', '제출'], ['초안', '민감정보', '원문', '전문가', '기준']],
  ]
  for (const [needles, expansions] of groups) {
    if (needles.some((needle) => normalized.includes(needle))) {
      expansions.forEach((item) => tokens.add(item))
    }
  }
  return Array.from(tokens).filter((token) => token.length >= 2)
}

function routeQuestionTarget(
  conceptItems: Array<FoundationConcept & { checkId: string }>,
  sourceId: string,
  question: string,
): RoutedQuestionTarget | null {
  const sourceIndex = conceptItems.findIndex((item) => item.checkId === sourceId)
  if (sourceIndex < 0) return null
  const questionTerms = routeKeywords(question)
  if (questionTerms.length < 2) return null
  const scoreConcept = (item: FoundationConcept): number => {
    const haystack = `${item.title} ${item.body} ${item.comprehension_check ?? ''} ${item.question_prompt ?? ''}`.toLowerCase()
    const hits = questionTerms.filter((term) => haystack.includes(term))
    return hits.length / Math.max(1, Math.min(questionTerms.length, 8))
  }
  const sourceScore = scoreConcept(conceptItems[sourceIndex])
  let best: RoutedQuestionTarget | null = null
  let bestScore = 0
  conceptItems.forEach((item, index) => {
    if (index <= sourceIndex) return
    const score = scoreConcept(item)
    if (score > bestScore) {
      bestScore = score
      best = { target: item, targetIndex: index }
    }
  })
  return best && bestScore >= 0.18 && bestScore >= sourceScore + 0.18 ? best : null
}

function routePlannedCurriculumQuestion(
  outline: PlannedCurriculumItem[] | undefined,
  currentStage: StageKey,
  question: string,
): PlannedCurriculumItem | null {
  const currentDay = currentStage === 'day1' ? 1 : 0
  const questionTerms = routeKeywords(question)
  if (!outline?.length || questionTerms.length < 2) return null
  let best: PlannedCurriculumItem | null = null
  let bestScore = 0
  for (const item of outline) {
    if (Number(item.day) <= currentDay) continue
    const haystack = `${item.title} ${item.focus} ${item.outcome}`.toLowerCase()
    const hits = questionTerms.filter((term) => haystack.includes(term))
    const score = hits.length / Math.max(1, Math.min(questionTerms.length, 8))
    if (score > bestScore) {
      bestScore = score
      best = item
    }
  }
  return best && bestScore >= 0.18 ? best : null
}

function day0BridgeAnswerForUnassignedQuestion(question: string, planned?: PlannedCurriculumItem | null): string | null {
  if (planned) {
    return `이 질문은 현재 러프 커리큘럼상 ${planned.title} 후보입니다. 아직 상세 카드는 확정 전이라 지금은 Day 0 수준으로만 답합니다. ${planned.outcome}`
  }
  const normalized = question.toLowerCase()
  if (normalized.includes('transformer') || normalized.includes('트랜스포머') || normalized.includes('machine learning') || normalized.includes('머신러닝')) {
    return '좋은 심화 질문입니다. 다만 이 주제는 아직 별도 훈련 카드로 배정되지 않았습니다. Day 0에서는 Transformer가 머신러닝 안에서 쓰이는 모델 구조 중 하나이고, LLM은 그 구조를 큰 글 데이터로 학습해 말을 만든다는 정도만 먼저 기억하면 됩니다.'
  }
  if (normalized.includes('rag') || normalized.includes('자료') || normalized.includes('근거') || normalized.includes('검증') || normalized.includes('출처')) {
    return '좋은 심화 질문입니다. 다만 이 주제는 아직 별도 훈련 카드로 배정되지 않았습니다. Day 0에서는 AI 답을 그대로 믿지 말고, 원문이나 믿을 만한 자료로 다시 확인해야 한다는 점만 먼저 기억하면 됩니다.'
  }
  if (normalized.includes('프롬프트') || normalized.includes('질문') || normalized.includes('후속')) {
    return '좋은 심화 질문입니다. 다만 이 주제는 아직 별도 훈련 카드로 배정되지 않았습니다. Day 0에서는 질문을 잘하려면 상황, 원하는 결과, 확인할 기준을 같이 적으면 된다는 정도만 먼저 기억하면 됩니다.'
  }
  return null
}

function currentSafetyCoachAnswers(raw: unknown, feedback: SafetyConceptFeedback, deletedKeys: SafetyDeletedAnswerKeys = []): SafetyCoachAnswers {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const deleted = new Set(deletedKeys)
  const out: SafetyCoachAnswers = {}
  for (const [id, value] of Object.entries(raw as Record<string, unknown>)) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) continue
    const item = value as SafetyCoachAnswers[string]
    if (item.version !== SAFETY_COACH_ANSWER_VERSION) continue
    if (item.question && feedback[id] && item.question.trim() !== feedback[id].trim()) continue
    if (deleted.has(safetyAnswerKey(id, item.version, item.question))) continue
    if (typeof item.answer === 'string' && item.answer.trim()) out[id] = item
  }
  return out
}

function currentSafetyCoachThreads(raw: unknown, deletedKeys: SafetyDeletedAnswerKeys = []): SafetyCoachThreads {
  if (!Array.isArray(raw)) return []
  const deleted = new Set(deletedKeys)
  return raw
    .filter((item): item is SafetyCoachThreadItem => {
      if (!item || typeof item !== 'object' || Array.isArray(item)) return false
      const row = item as SafetyCoachThreadItem
      if (deleted.has(safetyAnswerKey(row.conceptId, row.version, row.question))) return false
      return row.version === SAFETY_COACH_ANSWER_VERSION && Boolean(row.question?.trim()) && Boolean(row.answer?.trim())
    })
    .slice(-40)
}

function currentDeferredSafetyQuestions(raw: unknown, deletedKeys: SafetyDeletedAnswerKeys = []): DeferredSafetyQuestions {
  if (!Array.isArray(raw)) return []
  const deleted = new Set(deletedKeys)
  return raw
    .filter((item): item is DeferredSafetyQuestion => {
      if (!item || typeof item !== 'object' || Array.isArray(item)) return false
      const row = item as DeferredSafetyQuestion
      if (deleted.has(safetyAnswerKey(row.sourceConceptId, SAFETY_COACH_ANSWER_VERSION, row.question))) return false
      return Boolean(row.question?.trim()) && Boolean(row.bridgeAnswer?.trim())
    })
    .slice(-40)
}

function appendSafetyCoachThread(threads: SafetyCoachThreads, item: SafetyCoachThreadItem): SafetyCoachThreads {
  const key = `${item.conceptId}::${item.version}::${item.question.trim()}`
  const withoutDuplicate = threads.filter((thread) => `${thread.conceptId}::${thread.version}::${thread.question.trim()}` !== key)
  return [...withoutDuplicate, item].slice(-40)
}

function appendDeferredSafetyQuestion(items: DeferredSafetyQuestions, item: DeferredSafetyQuestion): DeferredSafetyQuestions {
  const key = `${item.sourceConceptId}::${item.question.trim()}`
  const withoutDuplicate = items.filter((row) => `${row.sourceConceptId}::${row.question.trim()}` !== key)
  return [...withoutDuplicate, item].slice(-40)
}

function currentDeletedSafetyAnswerKeys(raw: unknown): SafetyDeletedAnswerKeys {
  if (!Array.isArray(raw)) return []
  return Array.from(new Set(raw.map((item) => String(item || '').trim()).filter(Boolean))).slice(-120)
}

function safetyQuestionWasDeleted(conceptId: string, question: string | undefined, deletedKeys: SafetyDeletedAnswerKeys): boolean {
  const q = (question || '').trim()
  if (!q) return false
  return deletedKeys.some((key) => {
    const prefix = `${conceptId}::`
    return key.startsWith(prefix) && key.endsWith(`::${q}`)
  })
}

function currentSafetyConceptFeedback(raw: unknown, deletedKeys: SafetyDeletedAnswerKeys = []): SafetyConceptFeedback {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const out: SafetyConceptFeedback = {}
  for (const [id, value] of Object.entries(raw as Record<string, unknown>)) {
    const text = String(value ?? '')
    if (safetyQuestionWasDeleted(id, text, deletedKeys)) continue
    out[id] = text
  }
  return out
}

function evidenceBadge(value?: boolean): string {
  if (value === true) return '자료 반영'
  if (value === false) return '자료 없음'
  return '자료 -'
}

function mergeSafetyCoachThreads(...groups: SafetyCoachThreads[]): SafetyCoachThreads {
  return groups.flat().reduce<SafetyCoachThreads>((acc, item) => appendSafetyCoachThread(acc, item), [])
}

function safetyCoachThreadGroups(
  state: TrainingState | null,
  activeStage: StageKey,
  activeThreads: SafetyCoachThreads,
  activeDeletedKeys: SafetyDeletedAnswerKeys,
): SafetyCoachThreadGroup[] {
  const drafts = state?.ui_state?.stage_drafts ?? {}
  return STAGE_ORDER.map((key) => {
    const draftDeleted = currentDeletedSafetyAnswerKeys(drafts[key]?.deleted_safety_answer_keys)
    const deleted = key === activeStage ? Array.from(new Set([...draftDeleted, ...activeDeletedKeys])) : draftDeleted
    const draftThreads = currentSafetyCoachThreads(drafts[key]?.safety_coach_threads, deleted)
    const items = key === activeStage ? mergeSafetyCoachThreads(draftThreads, activeThreads) : draftThreads
    return { stage: key, label: STAGE_LABEL[key], items }
  })
}

function mergeDeferredSafetyQuestions(...groups: DeferredSafetyQuestions[]): DeferredSafetyQuestions {
  return groups.flat().reduce<DeferredSafetyQuestions>((acc, item) => appendDeferredSafetyQuestion(acc, item), [])
}

function deferredSafetyQuestionItems(
  state: TrainingState | null,
  activeStage: StageKey,
  activeItems: DeferredSafetyQuestions,
  activeDeletedKeys: SafetyDeletedAnswerKeys,
): DeferredSafetyQuestions {
  const drafts = state?.ui_state?.stage_drafts ?? {}
  const all = STAGE_ORDER.map((key) => {
    const draftDeleted = currentDeletedSafetyAnswerKeys(drafts[key]?.deleted_safety_answer_keys)
    const deleted = key === activeStage ? Array.from(new Set([...draftDeleted, ...activeDeletedKeys])) : draftDeleted
    const draftItems = currentDeferredSafetyQuestions(drafts[key]?.deferred_safety_questions, deleted)
    return key === activeStage ? mergeDeferredSafetyQuestions(draftItems, activeItems) : draftItems
  })
  return mergeDeferredSafetyQuestions(...all)
}

function QuestionArchivePanel({
  groups,
  deferred,
  onClose,
}: {
  groups: SafetyCoachThreadGroup[]
  deferred: DeferredSafetyQuestions
  onClose: () => void
}) {
  const hasItems = groups.some((group) => group.items.length > 0) || deferred.length > 0
  return (
    <section className="mb-4 rounded-2xl border border-primary/25 bg-sky-50/80 p-4 shadow-[0_0_0_1px_rgba(37,99,235,0.08)] print:border-0 print:bg-card print:p-0 print:shadow-none">
      <div className="mb-3 flex items-start justify-between gap-3 print:hidden">
        <div className="min-w-0">
          <div className="mb-1 inline-flex rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary">
            질문 아카이브
          </div>
          <h2 className="text-base font-bold leading-snug text-ink-strong">Day별 질문 모아보기</h2>
          <p className="mt-1 text-xs leading-relaxed text-text-faint">
            삭제한 질문은 제외하고, Day별 질문과 AI 코치 답변만 따로 봅니다.
          </p>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-[9px] border border-border bg-secondary px-3 py-2 text-xs font-semibold text-ink transition hover:bg-card"
          >
            전체 프린트
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-[9px] border border-border bg-secondary px-3 py-2 text-xs font-semibold text-ink transition hover:bg-card"
          >
            닫기
          </button>
        </div>
      </div>
      <div className="hidden print:block">
        <h1 className="text-xl font-bold text-ink-strong">Day별 질문 모아보기</h1>
      </div>
      {!hasItems ? (
        <div className="rounded-[12px] border border-dashed border-border bg-secondary px-3 py-6 text-center text-sm text-text-muted">
          아직 저장된 질문이 없습니다.
        </div>
      ) : (
        <div className="grid gap-3">
          {groups.map((group) => (
            <div key={group.stage} className="rounded-[12px] border border-primary/15 bg-card p-3 print:break-inside-avoid print:bg-card">
              <h3 className="text-sm font-bold text-ink">{group.label}</h3>
              {group.items.length ? (
                <div className="mt-2 grid gap-2">
                  {group.items.slice().reverse().map((item) => (
                    <article key={`${group.stage}-${item.id}`} className="rounded-[10px] border border-border bg-card px-3 py-2 print:border-border">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <span className="text-[11px] font-semibold text-primary">{item.conceptTitle}</span>
                        <span className="shrink-0 text-[9px] font-medium text-text-faint/70">
                          {evidenceBadge(item.evidenceUsed)}
                        </span>
                      </div>
                      <p className="text-xs font-semibold leading-relaxed text-ink">Q. {item.question}</p>
                      <p className="mt-1 text-xs leading-relaxed text-text-muted">A. {item.answer}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-xs leading-relaxed text-text-faint">이 Day에는 아직 질문이 없습니다.</p>
              )}
            </div>
          ))}
          {deferred.length ? (
            <div className="rounded-[12px] border border-primary/15 bg-card p-3 print:break-inside-avoid print:bg-card">
              <h3 className="text-sm font-bold text-ink">심화 질문 · 커리큘럼 후보</h3>
              <p className="mt-1 text-xs leading-relaxed text-text-faint">
                상세 카드가 아직 확정되지 않은 질문입니다. 러프 커리큘럼 조정 후보로 남깁니다.
              </p>
              <div className="mt-2 grid gap-2">
                {deferred.slice().reverse().map((item) => (
                  <article key={item.id} className="rounded-[10px] border border-border bg-card px-3 py-2 print:border-border">
                    <div className="mb-1 text-[11px] font-semibold text-primary">{item.sourceConceptTitle}</div>
                    {item.targetTitle ? (
                      <div className="mb-1 text-[10px] font-medium text-text-faint">
                        후보: Day {item.targetDay} · {item.targetTitle.replace(/^Day\s+\d+\s*·\s*/, '')}
                      </div>
                    ) : null}
                    <p className="text-xs font-semibold leading-relaxed text-ink">Q. {item.question}</p>
                    <p className="mt-1 text-xs leading-relaxed text-text-muted">A. {item.bridgeAnswer}</p>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </section>
  )
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
            {activeLength.toLocaleString()}개 개인화 항목 · {modules.length || topicCount}개 모듈 · {concernCount}개 실제 고민
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
          <div className="text-[10px] font-medium text-text-faint">항목</div>
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
                {activeLength.toLocaleString()}개 개인화 항목이 수집 자료와 목표에 따라 생성됨
              </h3>
            </div>
            <ol className="max-h-[68dvh] overflow-y-auto p-3">
              {(modules.length ? modules : []).map((mod) => (
                <li key={`${mod.module}-${mod.topic}`} className="mb-2 rounded-[12px] bg-secondary px-3 py-3">
                  <div className="text-xs font-semibold text-primary">
                    {mod.title} · {mod.lesson_count}개 항목 묶음
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
                    <div className="mt-2">
                      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-text-faint">대표 실습 예</div>
                      <ul className="space-y-1">
                        {mod.sample_missions.map((mission) => (
                          <li key={mission} className="text-xs leading-relaxed text-text-faint">
                            {mission}
                          </li>
                        ))}
                      </ul>
                    </div>
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

function PlannedCurriculumPreview({ items }: { items: PlannedCurriculumItem[] }) {
  const [open, setOpen] = useState(false)
  if (!items.length) return null
  const visible = open ? items : items.slice(0, 4)
  return (
    <section className="rounded-2xl border border-border bg-card p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-faint">러프 커리큘럼</div>
          <h2 className="text-base font-bold leading-snug text-ink-strong">전체 골격은 미리 잡고, 상세 내용은 질문과 관심사로 조정합니다</h2>
          <p className="mt-1 text-xs leading-relaxed text-text-faint">
            Day 2 이후는 확정 상세안이 아니라 현재 기준의 큰 흐름입니다.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="shrink-0 rounded-[9px] border border-border bg-secondary px-3 py-2 text-xs font-semibold text-ink transition hover:bg-card"
        >
          {open ? '접기' : '전체'}
        </button>
      </div>
      <ol className="grid gap-2">
        {visible.map((item) => (
          <li key={item.key} className="rounded-[12px] bg-secondary px-3 py-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs font-semibold text-primary">Day {item.day}</div>
              <div className="shrink-0 text-[10px] font-medium text-text-faint">
                {item.status === 'rough_planned' ? '러프' : item.status === 'detailed_ready' ? '상세 준비' : '진행'}
              </div>
            </div>
            <div className="mt-0.5 text-sm font-semibold leading-snug text-ink">{item.title.replace(/^Day\s+\d+\s*·\s*/, '')}</div>
            <p className="mt-1 text-xs leading-relaxed text-text-muted">{item.focus}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

function SafetyOrientationBlock({
  stage,
  checked,
  conceptFeedback,
  coachAnswers,
  coachThreads,
  coachLoading,
  coachErrors,
  saving,
  error,
  notice,
  routedConceptId,
  onToggle,
  onConceptFeedback,
  onAskCoach,
  onDeleteCoachAnswer,
  onSaveQuestions,
  onReady,
}: {
  stage: TrainingStage
  checked: Record<string, boolean>
  conceptFeedback: SafetyConceptFeedback
  coachAnswers: SafetyCoachAnswers
  coachThreads: SafetyCoachThreads
  coachLoading: Record<string, boolean>
  coachErrors: Record<string, string>
  saving: boolean
  error?: string | null
  notice?: string | null
  routedConceptId?: string | null
  onToggle: (id: string) => void
  onConceptFeedback: (id: string, value: string) => void
  onAskCoach: (concept: NonNullable<TrainingStage['foundation_concepts']>[number], id: string) => void
  onDeleteCoachAnswer: (id: string) => void
  onSaveQuestions: () => void
  onReady: () => void
}) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const concepts = stage.foundation_concepts ?? []
  const blocks = stage.schedule_blocks ?? []
  const safetyItems = stageChecklist(stage).filter((item) => item.id.startsWith('understand_'))
  const conceptItems = concepts.map((concept, index) => ({ ...concept, checkId: conceptId(concept, index) }))
  const ready =
    safetyItems.length > 0 &&
    safetyItems.every((item) => checked[item.id]) &&
    conceptItems.length > 0 &&
    conceptItems.every((item) => checked[item.checkId])
  const hasQuestions = Object.values(conceptFeedback).some((value) => value.trim())

  return (
    <section className="rounded-2xl border border-danger/20 bg-danger-soft/45 p-4">
      <div className="mb-3 flex items-start gap-2.5">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-card text-danger">
          <ShieldCheck size={18} />
        </span>
        <div className="min-w-0">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-danger">실습 전 안전 확인</div>
          <h2 className="text-base font-bold leading-snug text-ink-strong">AI를 쓰기 전에 먼저 알아야 할 것</h2>
          <p className="mt-1 text-sm leading-relaxed text-text-muted">
            먼저 AI, LLM(큰 언어 모델), 생성형 AI가 무엇인지 아주 쉬운 말로 확인합니다. 각 단락을 읽고
            이해했는지 표시하거나, 헷갈리는 점을 적어 질문으로 남긴 뒤 실제 질문 실습으로 넘어갑니다.
          </p>
        </div>
      </div>

      {coachThreads.length ? (
        <div className="mb-4 rounded-[14px] border border-primary/25 bg-sky-50/85 p-3 shadow-[0_0_0_1px_rgba(37,99,235,0.06)]">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="mb-1 inline-flex rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary">
                질문 아카이브
              </div>
              <div className="text-xs font-semibold text-ink">내 질문 모아보기</div>
              <p className="mt-0.5 text-xs leading-relaxed text-text-faint">
                지금까지 남긴 질문 {coachThreads.length}개를 한 번에 다시 볼 수 있어요.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setHistoryOpen((v) => !v)}
              className="shrink-0 rounded-[9px] border border-border bg-secondary px-3 py-2 text-xs font-semibold text-ink transition hover:bg-card"
            >
              {historyOpen ? '접기' : '보기'}
            </button>
          </div>
          {historyOpen ? (
            <div className="mt-3 grid gap-2">
              {coachThreads.slice().reverse().map((item) => (
                <div key={item.id} className="rounded-[10px] border border-border bg-secondary px-3 py-2">
                  <div className="mb-1 text-[11px] font-semibold text-primary">{item.conceptTitle}</div>
                  <p className="text-xs font-semibold leading-relaxed text-ink">Q. {item.question}</p>
                  <p className="mt-1 text-xs leading-relaxed text-text-muted">A. {item.answer}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {concepts.length ? (
        <div className="grid gap-2">
          {coachThreads.length ? (
            <div className="mb-1 flex items-center gap-2" aria-label="훈련 카드 시작">
              <span className="h-px flex-1 bg-danger/20" />
              <span className="rounded-full border border-danger/20 bg-card px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-danger">
                훈련 카드
              </span>
              <span className="h-px flex-1 bg-danger/20" />
            </div>
          ) : null}
          {conceptItems.map((concept) => {
            const on = Boolean(checked[concept.checkId])
            const feedback = conceptFeedback[concept.checkId] ?? ''
            const coach = coachAnswers[concept.checkId]
            const loading = Boolean(coachLoading[concept.checkId])
            const coachError = coachErrors[concept.checkId]
            const hasCurrentAnswer =
              Boolean(coach?.answer) &&
              coach?.version === SAFETY_COACH_ANSWER_VERSION &&
              (coach.question ?? '').trim() === feedback.trim()
            const confirmingDelete = confirmDeleteId === concept.checkId
            return (
            <div
              key={concept.checkId}
              id={`concept-card-${concept.checkId}`}
              className={`rounded-[12px] border bg-card p-3 transition ${
                routedConceptId === concept.checkId
                  ? 'border-amber-500 bg-amber-50 shadow-[0_0_0_4px_rgba(245,158,11,0.2)] ring-2 ring-amber-400'
                  : 'border-border'
              }`}
            >
              {routedConceptId === concept.checkId ? (
                <div className="-mx-1 mb-3 rounded-[10px] border border-amber-300 bg-amber-100 px-3 py-2 text-xs font-semibold leading-relaxed text-amber-900 shadow-sm">
                  이 카드에 질문과 가장 가까운 설명이 있어요.
                </div>
              ) : null}
              <div className="text-sm font-semibold leading-snug text-ink">{concept.title}</div>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">{concept.body}</p>
              <button
                type="button"
                onClick={() => onToggle(concept.checkId)}
                className="mt-3 flex w-full items-start gap-2 rounded-[10px] border border-border bg-secondary px-3 py-2.5 text-left transition active:scale-[0.99]"
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                    on ? 'border-primary bg-primary text-primary-foreground' : 'border-border-strong bg-card'
                  }`}
                >
                  {on ? <Check size={14} strokeWidth={3} /> : null}
                </span>
                <span className="text-xs font-medium leading-relaxed text-ink">
                  {concept.comprehension_check ?? '이 단락을 읽고 이해했어요.'}
                </span>
              </button>
              <label className="mt-3 block text-xs font-semibold text-text-muted" htmlFor={`${concept.checkId}-feedback`}>
                잘 이해되지 않는 점이나 질문
              </label>
              <textarea
                id={`${concept.checkId}-feedback`}
                value={feedback}
                onChange={(e) => onConceptFeedback(concept.checkId, e.target.value)}
                onKeyDown={(e) => {
                  if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing) return
                  e.preventDefault()
                  if (!feedback.trim() || loading || hasCurrentAnswer) return
                  onAskCoach(concept, concept.checkId)
                }}
                rows={2}
                placeholder={concept.question_prompt ?? '예: 이 부분이 잘 이해되지 않아요.'}
                className="mt-1 w-full resize-y rounded-[10px] border border-border bg-secondary px-3 py-2 text-xs leading-relaxed text-ink outline-none transition placeholder:text-text-faint focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30"
              />
              {feedback.trim() ? (
                <button
                  type="button"
                  onClick={() => onAskCoach(concept, concept.checkId)}
                  disabled={loading || hasCurrentAnswer}
                  className="mt-2 inline-flex h-9 items-center gap-1.5 rounded-[9px] bg-primary px-3 text-xs font-semibold text-primary-foreground transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? <Loader2 size={13} className="animate-spin" /> : null}
                  {loading ? '답변 생성 중' : hasCurrentAnswer ? '이미 답변 완료' : '질문에 답변 받기'}
                </button>
              ) : null}
              {hasCurrentAnswer ? (
                <div className="mt-1 flex items-center justify-between gap-2">
                  <p className="text-[11px] leading-relaxed text-text-faint">
                    같은 질문은 다시 생성하지 않아요. 삭제하면 다시 답변을 받을 수 있습니다.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      if (confirmingDelete) {
                        setConfirmDeleteId(null)
                        onDeleteCoachAnswer(concept.checkId)
                        return
                      }
                      setConfirmDeleteId(concept.checkId)
                      window.setTimeout(() => {
                        setConfirmDeleteId((value) => (value === concept.checkId ? null : value))
                      }, 6000)
                    }}
                    className={`inline-flex h-7 shrink-0 items-center gap-1 rounded-[8px] border px-2 text-[11px] font-semibold transition ${
                      confirmingDelete
                        ? 'border-danger bg-danger-soft text-danger hover:brightness-95'
                        : 'border-border bg-secondary text-text-muted hover:bg-card hover:text-danger'
                    }`}
                  >
                    <Trash2 size={12} />
                    {confirmingDelete ? '삭제 확인' : '삭제'}
                  </button>
                  {confirmingDelete ? (
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(null)}
                      className="inline-flex h-7 shrink-0 items-center rounded-[8px] border border-border bg-card px-2 text-[11px] font-semibold text-text-muted"
                    >
                      취소
                    </button>
                  ) : null}
                </div>
              ) : null}
              {coachError ? (
                <div className="mt-2 rounded-[10px] bg-danger-soft px-3 py-2 text-xs leading-relaxed text-danger">
                  {coachError}
                </div>
              ) : null}
              {coach?.answer ? (
                <div className="mt-2 rounded-[10px] border border-primary/20 bg-primary/5 px-3 py-2 text-xs leading-relaxed text-text-muted">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="font-semibold text-primary">AI 코치 답변</span>
                    <span className="flex shrink-0 items-center gap-1.5 text-[10px] font-medium text-text-faint">
                      <span className="text-text-faint/70">{evidenceBadge(coach.evidenceUsed)}</span>
                      {coach.model ? (
                        <span>
                          {coach.fallbackUsed ? 'fallback' : coach.model}
                        </span>
                      ) : null}
                    </span>
                  </div>
                  {coach.answer}
                </div>
              ) : null}
            </div>
            )
          })}
        </div>
      ) : null}

      {blocks.length ? (
        <div className="mt-3 rounded-[12px] border border-border bg-card p-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-faint">오늘의 순서</div>
          <ol className="grid gap-2">
            {blocks.slice(0, 4).map((block) => (
              <li key={block.title} className="flex gap-2 text-xs leading-relaxed text-text-muted">
                <span className="mt-0.5 shrink-0 font-semibold text-primary">{block.minutes ?? '-'}분</span>
                <span>
                  <span className="font-semibold text-ink">{block.title}</span>
                  {block.goal ? ` · ${block.goal}` : ''}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {safetyItems.length ? (
        <div className="mt-3 grid gap-2">
          {safetyItems.map((item) => {
            const on = Boolean(checked[item.id])
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onToggle(item.id)}
                className="flex w-full items-start gap-3 rounded-[12px] border border-border bg-card p-3 text-left transition active:scale-[0.99]"
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
                    on ? 'border-primary bg-primary text-primary-foreground' : 'border-border-strong'
                  }`}
                >
                  {on ? <Check size={14} strokeWidth={3} /> : null}
                </span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-sm font-semibold text-ink">{item.title}</span>
                  {item.instruction ? (
                    <span className="text-xs leading-relaxed text-text-faint">{item.instruction}</span>
                  ) : null}
                </span>
              </button>
            )
          })}
        </div>
      ) : null}

      {error ? (
        <div className="mt-3 flex items-start gap-2 rounded-[10px] bg-danger-soft px-3.5 py-3 text-sm text-danger">
          <AlertCircle size={17} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}
      {notice ? (
        <div className="mt-3 flex items-center gap-2 rounded-[10px] bg-success-soft px-3.5 py-3 text-sm font-medium text-success">
          <Check size={16} className="shrink-0" />
          <span>{notice}</span>
        </div>
      ) : null}

      {hasQuestions ? (
        <button
          type="button"
          onClick={onSaveQuestions}
          disabled={saving}
          className="mt-3 flex h-10 w-full items-center justify-center rounded-[10px] border border-border bg-card text-sm font-semibold text-ink transition hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
        >
          질문만 먼저 저장
        </button>
      ) : null}

      <button
        type="button"
        onClick={onReady}
        disabled={!ready || saving}
        className="mt-3 flex h-11 w-full items-center justify-center rounded-[10px] bg-primary text-sm font-semibold text-primary-foreground transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? '확인 저장 중…' : '이해했습니다. 실습으로 이동'}
      </button>
      {!ready ? (
        <p className="mt-2 text-center text-xs leading-relaxed text-text-faint">
          설명 단락과 안전 확인을 모두 체크하면 실제 AI 실습이 열립니다. 이해되지 않으면 질문을 먼저 남겨주세요.
        </p>
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
  const [conceptFeedback, setConceptFeedback] = useState<SafetyConceptFeedback>({})
  const [coachAnswers, setCoachAnswers] = useState<SafetyCoachAnswers>({})
  const [coachThreads, setCoachThreads] = useState<SafetyCoachThreads>([])
  const [deferredSafetyQuestions, setDeferredSafetyQuestions] = useState<DeferredSafetyQuestions>([])
  const [deletedSafetyAnswerKeys, setDeletedSafetyAnswerKeys] = useState<SafetyDeletedAnswerKeys>([])
  const [coachLoading, setCoachLoading] = useState<Record<string, boolean>>({})
  const [coachErrors, setCoachErrors] = useState<Record<string, string>>({})
  const [whyOpen, setWhyOpen] = useState(false)
  const [safetyReady, setSafetyReady] = useState(false)
  const [safetySyncing, setSafetySyncing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [questionArchiveOpen, setQuestionArchiveOpen] = useState(false)
  const [routedConceptId, setRoutedConceptId] = useState<string | null>(null)
  const seqRef = useRef(0)
  const conceptFeedbackRef = useRef<SafetyConceptFeedback>({})
  const coachAnswersRef = useRef<SafetyCoachAnswers>({})
  const coachThreadsRef = useRef<SafetyCoachThreads>([])
  const deferredSafetyQuestionsRef = useRef<DeferredSafetyQuestions>([])
  const deletedSafetyAnswerKeysRef = useRef<SafetyDeletedAnswerKeys>([])

  // 단계 전환 시 로컬 입력(증거물/체크)을 그 단계 값으로 재시드.
  function hydrateStageInputs(st: TrainingState, next: StageKey) {
    setStage(next)
    setProof(String(st[next]?.proof_artifact ?? ''))
    setChecked({})
    const draft = st.ui_state?.stage_drafts?.[next]
    const feedback = draft?.safety_concept_feedback
    const answers = draft?.safety_coach_answers
    const threads = draft?.safety_coach_threads
    const deferred = draft?.deferred_safety_questions
    const deleted = currentDeletedSafetyAnswerKeys(draft?.deleted_safety_answer_keys)
    const nextFeedback = currentSafetyConceptFeedback(feedback, deleted)
    const nextAnswers = currentSafetyCoachAnswers(answers, nextFeedback, deleted)
    const nextThreads = currentSafetyCoachThreads(threads, deleted)
    const nextDeferred = currentDeferredSafetyQuestions(deferred, deleted)
    conceptFeedbackRef.current = nextFeedback
    coachAnswersRef.current = nextAnswers
    coachThreadsRef.current = nextThreads
    deferredSafetyQuestionsRef.current = nextDeferred
    deletedSafetyAnswerKeysRef.current = deleted
    setConceptFeedback(nextFeedback)
    setCoachAnswers(nextAnswers)
    setCoachThreads(nextThreads)
    setDeferredSafetyQuestions(nextDeferred)
    setDeletedSafetyAnswerKeys(deleted)
    setCoachLoading({})
    setCoachErrors({})
    setWhyOpen(false)
    setSafetyReady(Boolean(st[next]?.completed || st.ui_state?.safety_confirmed?.[next]))
    setSafetySyncing(false)
    setNotice(null)
    setRoutedConceptId(null)
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
        const nextState = r.state
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

  function updateConceptFeedback(id: string, value: string) {
    setConceptFeedback((prev) => {
      const next = { ...prev, [id]: value }
      conceptFeedbackRef.current = next
      return next
    })
    setCoachAnswers((prev) => {
      const current = prev[id]
      if (!current) return prev
      if ((current.question ?? '').trim() === value.trim()) return prev
      const next = { ...prev }
      delete next[id]
      coachAnswersRef.current = next
      return next
    })
    setCoachErrors((prev) => ({ ...prev, [id]: '' }))
  }

  function deleteCoachAnswer(id: string) {
    const currentAnswer = coachAnswersRef.current[id]
    if (!state || !currentAnswer?.answer) return
    const deleteKey = safetyAnswerKey(id, currentAnswer.version, currentAnswer.question)
    const deletedAt = new Date().toISOString()
    const nextDeleted = Array.from(new Set([...deletedSafetyAnswerKeysRef.current, deleteKey])).slice(-120)
    const persistedAnswers = {
      ...coachAnswersRef.current,
      [id]: { ...currentAnswer, deletedAt },
    } as SafetyCoachAnswers
    const nextAnswers = currentSafetyCoachAnswers(persistedAnswers, conceptFeedbackRef.current, nextDeleted)
    const persistedThreads = coachThreadsRef.current.map((thread) =>
      safetyAnswerKey(thread.conceptId, thread.version, thread.question) === deleteKey ? { ...thread, deletedAt } : thread,
    )
    const persistedDeferred = deferredSafetyQuestionsRef.current.map((item) =>
      safetyAnswerKey(item.sourceConceptId, SAFETY_COACH_ANSWER_VERSION, item.question) === deleteKey ? { ...item, deletedAt } : item,
    )
    const nextThreads = currentSafetyCoachThreads(persistedThreads, nextDeleted)
    const nextDeferred = currentDeferredSafetyQuestions(persistedDeferred, nextDeleted)
    const currentQuestion = (currentAnswer.question ?? '').trim()
    const currentDraftQuestion = (conceptFeedbackRef.current[id] ?? '').trim()
    const nextFeedback =
      currentQuestion && currentDraftQuestion === currentQuestion
        ? { ...conceptFeedbackRef.current, [id]: '' }
        : conceptFeedbackRef.current
    conceptFeedbackRef.current = nextFeedback
    coachAnswersRef.current = nextAnswers
    coachThreadsRef.current = nextThreads
    deferredSafetyQuestionsRef.current = nextDeferred
    deletedSafetyAnswerKeysRef.current = nextDeleted
    setConceptFeedback(nextFeedback)
    setCoachAnswers(nextAnswers)
    setCoachThreads(nextThreads)
    setDeferredSafetyQuestions(nextDeferred)
    setDeletedSafetyAnswerKeys(nextDeleted)
    setCoachErrors((prev) => ({ ...prev, [id]: '' }))
    setNotice('답변을 삭제했어요. 같은 질문으로 다시 답변을 받을 수 있습니다.')
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: stage,
      clientSeq: seqRef.current,
      eventName: 'safety_coach_answer_deleted',
      eventPayload: {
        stage,
        concept_id: id,
        question: currentAnswer.question ?? '',
        deleted_key: deleteKey,
      },
      stageDrafts: {
        [stage]: {
          safety_concept_feedback: nextFeedback,
          safety_coach_answers: persistedAnswers,
          safety_coach_threads: persistedThreads,
          deferred_safety_questions: persistedDeferred,
          deleted_safety_answer_keys: nextDeleted,
        },
      },
    }).then((next) => setState(next)).catch((e) => {
      console.error('delete safety answer sync failed', e)
      setCoachErrors((prev) => ({ ...prev, [id]: errMsg(e) }))
    })
  }

  async function requestCoachAnswer(concept: NonNullable<TrainingStage['foundation_concepts']>[number], id: string) {
    const question = (conceptFeedback[id] ?? '').trim()
    if (!state || !question || coachLoading[id]) return
    const conceptItems = (current?.foundation_concepts ?? []).map((item, index) => ({ ...item, checkId: conceptId(item, index) }))
    const routed = routeQuestionTarget(conceptItems, id, question)
    if (routed) {
      const previousUnconfirmed = conceptItems
        .slice(0, routed.targetIndex)
        .filter((item) => !checked[item.checkId])
      setRoutedConceptId(routed.target.checkId)
      setNotice(
        previousUnconfirmed.length
          ? `질문에 가장 가까운 설명 카드로 이동했어요. 앞 카드 ${previousUnconfirmed.length}개를 확인해야 다음 단계로 넘어갈 수 있습니다.`
          : '질문에 가장 가까운 설명 카드로 이동했어요.',
      )
      window.setTimeout(() => {
        const el = document.getElementById(`concept-card-${routed.target.checkId}`)
        if (!el) return
        const top = el.getBoundingClientRect().top + window.scrollY - 12
        window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
      }, 50)
      window.setTimeout(() => setRoutedConceptId((value) => (value === routed.target.checkId ? null : value)), 5000)
      return
    }
    setCoachLoading((prev) => ({ ...prev, [id]: true }))
    setCoachErrors((prev) => ({ ...prev, [id]: '' }))
    try {
      const semantic = await routeSafetyQuestion({
        caseId,
        email,
        stage,
        sourceConceptId: id,
        question,
        concepts: conceptItems.map((item) => ({
          id: item.checkId,
          title: item.title,
          body: item.body,
          comprehension_check: item.comprehension_check,
          question_prompt: item.question_prompt,
        })),
        plannedOutline: state.planned_curriculum_outline ?? [],
      })
      const targetId = semantic.target_concept_id || ''
      if (targetId && targetId !== id) {
        const sourceIndex = conceptItems.findIndex((item) => item.checkId === id)
        const targetIndex = conceptItems.findIndex((item) => item.checkId === targetId)
        const target = conceptItems[targetIndex]
        if (target && targetIndex > sourceIndex) {
          const previousUnconfirmed = conceptItems
            .slice(0, targetIndex)
            .filter((item) => !checked[item.checkId])
          setRoutedConceptId(target.checkId)
          setNotice(
            previousUnconfirmed.length
              ? `질문에 가장 가까운 설명 카드로 이동했어요. 앞 카드 ${previousUnconfirmed.length}개를 확인해야 다음 단계로 넘어갈 수 있습니다.`
              : '질문에 가장 가까운 설명 카드로 이동했어요.',
          )
          window.setTimeout(() => {
            const el = document.getElementById(`concept-card-${target.checkId}`)
            if (!el) return
            const top = el.getBoundingClientRect().top + window.scrollY - 12
            window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
          }, 50)
          window.setTimeout(() => setRoutedConceptId((value) => (value === target.checkId ? null : value)), 5000)
          setCoachLoading((prev) => ({ ...prev, [id]: false }))
          return
        }
      }
    } catch (e) {
      console.warn('semantic safety route failed', e)
    }
    const currentAnswer = coachAnswersRef.current[id]
    if (
      currentAnswer?.answer &&
      currentAnswer.version === SAFETY_COACH_ANSWER_VERSION &&
      (currentAnswer.question ?? '').trim() === question
    ) {
      setNotice('이미 이 질문에 답변했어요. 질문을 바꾸면 새 답변을 받을 수 있습니다.')
      setCoachLoading((prev) => ({ ...prev, [id]: false }))
      return
    }
    const planned = stage === 'day0' ? routePlannedCurriculumQuestion(state.planned_curriculum_outline, stage, question) : null
    const bridgeAnswer = stage === 'day0' ? day0BridgeAnswerForUnassignedQuestion(question, planned) : null
    if (bridgeAnswer) {
      const now = new Date().toISOString()
      const itemId = `${id}-${now}`
      const answerRecord: SafetyCoachAnswers[string] = {
        question,
        answer: bridgeAnswer,
        model: 'curriculum-backlog',
        fallbackUsed: false,
        evidenceUsed: false,
        version: SAFETY_COACH_ANSWER_VERSION,
      }
      const threadItem: SafetyCoachThreadItem = {
        id: itemId,
        conceptId: id,
        conceptTitle: concept.title,
        question,
        answer: bridgeAnswer,
        model: 'curriculum-backlog',
        fallbackUsed: false,
        evidenceUsed: false,
        version: SAFETY_COACH_ANSWER_VERSION,
        createdAt: now,
      }
      const deferredItem: DeferredSafetyQuestion = {
        id: itemId,
        question,
        sourceConceptId: id,
        sourceConceptTitle: concept.title,
        status: 'unassigned',
        targetDay: planned?.day,
        targetTitle: planned?.title,
        bridgeAnswer,
        createdAt: now,
      }
      const latestAnswers = coachAnswersRef.current
      const latestThreads = coachThreadsRef.current
      const latestFeedback = conceptFeedbackRef.current
      const latestDeferred = deferredSafetyQuestionsRef.current
      const nextDeleted = deletedSafetyAnswerKeysRef.current.filter((key) => key !== safetyAnswerKey(id, SAFETY_COACH_ANSWER_VERSION, question))
      const nextAnswers = { ...latestAnswers, [id]: answerRecord }
      const nextThreads = appendSafetyCoachThread(latestThreads, threadItem)
      const nextDeferred = appendDeferredSafetyQuestion(latestDeferred, deferredItem)
      coachAnswersRef.current = nextAnswers
      coachThreadsRef.current = nextThreads
      deferredSafetyQuestionsRef.current = nextDeferred
      deletedSafetyAnswerKeysRef.current = nextDeleted
      setCoachAnswers(nextAnswers)
      setCoachThreads(nextThreads)
      setDeferredSafetyQuestions(nextDeferred)
      setDeletedSafetyAnswerKeys(nextDeleted)
      setCoachErrors((prev) => ({ ...prev, [id]: '' }))
      setNotice('심화 질문으로 저장했어요. 아직 배정된 훈련 카드는 없습니다.')
      seqRef.current += 1
      void syncSession({
        caseId,
        email,
        selectedStage: stage,
        clientSeq: seqRef.current,
        eventName: 'safety_advanced_question_saved',
        eventPayload: {
          stage,
          concept_id: id,
          concept_title: concept.title,
          question,
          answer: bridgeAnswer,
          status: 'unassigned',
          target_day: planned?.day,
          target_title: planned?.title,
          reason: planned ? 'rough_curriculum_match_detail_pending' : 'no_future_curriculum_card',
        },
        stageDrafts: {
          [stage]: {
            safety_concept_feedback: latestFeedback,
            safety_coach_answers: nextAnswers,
            safety_coach_threads: nextThreads,
            deferred_safety_questions: nextDeferred,
            deleted_safety_answer_keys: nextDeleted,
          },
        },
      })
        .then((next) => setState(next))
        .catch((e) => {
          console.error('advanced safety question sync failed', e)
          setCoachErrors((prev) => ({ ...prev, [id]: errMsg(e) }))
        })
        .finally(() => {
          setCoachLoading((prev) => ({ ...prev, [id]: false }))
        })
      return
    }
    void askSafetyCoach({
      caseId,
      email,
      stage,
      conceptId: id,
      conceptTitle: concept.title,
      conceptBody: concept.body,
      question,
      answerVersion: SAFETY_COACH_ANSWER_VERSION,
      })
      .then((res) => {
        const answerRecord = {
          answer: res.answer,
          model: res.model,
          fallbackUsed: Boolean(res.fallback_used),
          question,
          version: res.answer_version || SAFETY_COACH_ANSWER_VERSION,
          duplicateReused: Boolean(res.duplicate_reused),
          evidenceUsed: res.evidence_used,
        }
        const threadItem: SafetyCoachThreadItem = {
          id: `${id}-${Date.now()}`,
          conceptId: id,
          conceptTitle: concept.title,
          question,
          answer: res.answer,
          model: res.model,
          fallbackUsed: Boolean(res.fallback_used),
          evidenceUsed: res.evidence_used,
          version: res.answer_version || SAFETY_COACH_ANSWER_VERSION,
          createdAt: new Date().toISOString(),
        }
        const latestAnswers = coachAnswersRef.current
        const latestThreads = coachThreadsRef.current
        const latestFeedback = conceptFeedbackRef.current
        const latestDeferred = deferredSafetyQuestionsRef.current
        const answerVersion = res.answer_version || SAFETY_COACH_ANSWER_VERSION
        const nextDeleted = deletedSafetyAnswerKeysRef.current.filter((key) => key !== safetyAnswerKey(id, answerVersion, question))
        const nextAnswers = { ...latestAnswers, [id]: answerRecord }
        const nextThreads = appendSafetyCoachThread(latestThreads, threadItem)
        coachAnswersRef.current = nextAnswers
        coachThreadsRef.current = nextThreads
        deletedSafetyAnswerKeysRef.current = nextDeleted
        setCoachAnswers(nextAnswers)
        setCoachThreads(nextThreads)
        setDeletedSafetyAnswerKeys(nextDeleted)
        seqRef.current += 1
        return syncSession({
          caseId,
          email,
          selectedStage: stage,
          clientSeq: seqRef.current,
          eventName: 'safety_coach_answer_saved',
          eventPayload: {
            stage,
            concept_id: id,
            concept_title: concept.title,
            question,
            answer: res.answer,
            model: res.model,
            fallback_used: Boolean(res.fallback_used),
            answer_version: res.answer_version || SAFETY_COACH_ANSWER_VERSION,
            duplicate_reused: Boolean(res.duplicate_reused),
            evidence_used: res.evidence_used,
          },
          stageDrafts: {
            [stage]: {
              safety_concept_feedback: latestFeedback,
              safety_coach_answers: nextAnswers,
              safety_coach_threads: nextThreads,
              deferred_safety_questions: latestDeferred,
              deleted_safety_answer_keys: nextDeleted,
            },
          },
        })
      })
      .then((next) => {
        setState(next)
      })
      .catch((e) => {
        console.error('safety coach failed', e)
        setCoachErrors((prev) => ({ ...prev, [id]: errMsg(e) }))
      })
      .finally(() => {
        setCoachLoading((prev) => ({ ...prev, [id]: false }))
      })
  }

  function saveSafetyQuestions() {
    if (!state || safetySyncing) return
    const latestFeedback = conceptFeedbackRef.current
    const latestAnswers = coachAnswersRef.current
    const latestThreads = coachThreadsRef.current
    const latestDeferred = deferredSafetyQuestionsRef.current
    const latestDeleted = deletedSafetyAnswerKeysRef.current
    setSafetySyncing(true)
    setError(null)
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: stage,
      clientSeq: seqRef.current,
      eventName: 'safety_orientation_feedback_saved',
      eventPayload: { stage, concept_feedback: latestFeedback },
      stageDrafts: {
        [stage]: {
          safety_concept_feedback: latestFeedback,
          safety_coach_answers: latestAnswers,
          safety_coach_threads: latestThreads,
          deferred_safety_questions: latestDeferred,
          deleted_safety_answer_keys: latestDeleted,
        },
      },
    })
      .then((next) => {
        setState(next)
        setNotice('질문을 저장했어요. 이해되는 단락부터 체크해도 됩니다.')
      })
      .catch((e) => {
        console.error('safety feedback sync failed', e)
        setError(errMsg(e))
      })
      .finally(() => setSafetySyncing(false))
  }

  function confirmSafetyOrientation() {
    if (!state || safetySyncing) return
    const latestFeedback = conceptFeedbackRef.current
    const latestAnswers = coachAnswersRef.current
    const latestThreads = coachThreadsRef.current
    const latestDeferred = deferredSafetyQuestionsRef.current
    const latestDeleted = deletedSafetyAnswerKeysRef.current
    const confirmedCheckIds = stageChecklist(current).filter((item) => item.id.startsWith('understand_') && checked[item.id]).map((item) => item.id)
    const confirmedConceptIds = (current?.foundation_concepts ?? [])
      .map((concept, index) => conceptId(concept, index))
      .filter((id) => checked[id])
    setSafetySyncing(true)
    setError(null)
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: stage,
      clientSeq: seqRef.current,
      eventName: 'safety_orientation_confirmed',
      eventPayload: {
        stage,
        confirmed_check_ids: confirmedCheckIds,
        confirmed_concept_ids: confirmedConceptIds,
        concept_feedback: latestFeedback,
        coach_answers: latestAnswers,
        coach_threads: latestThreads,
        deferred_safety_questions: latestDeferred,
        deleted_safety_answer_keys: latestDeleted,
      },
      stageDrafts: {
        [stage]: {
          safety_concept_feedback: latestFeedback,
          safety_coach_answers: latestAnswers,
          safety_coach_threads: latestThreads,
          deferred_safety_questions: latestDeferred,
          deleted_safety_answer_keys: latestDeleted,
          safety_concept_confirmed_ids: confirmedConceptIds,
        },
      },
    })
      .then((next) => {
        setState(next)
        setSafetyReady(Boolean(next.ui_state?.safety_confirmed?.[stage] || next[stage]?.completed))
      })
      .catch((e) => {
        console.error('safety confirmation sync failed', e)
        setError(errMsg(e))
        setSafetyReady(false)
      })
      .finally(() => setSafetySyncing(false))
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
  const questionGroups = safetyCoachThreadGroups(state, stage, coachThreads, deletedSafetyAnswerKeys)
  const deferredQuestions = deferredSafetyQuestionItems(state, stage, deferredSafetyQuestions, deletedSafetyAnswerKeys)
  const header = (
    <header className="mb-5 flex items-center gap-3 print:hidden">
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
      {state ? (
        <button
          type="button"
          onClick={() => setQuestionArchiveOpen((v) => !v)}
          className="ml-auto shrink-0 rounded-[9px] border border-border bg-card px-3 py-2 text-xs font-semibold text-ink transition hover:bg-secondary"
        >
          질문 모아보기
        </button>
      ) : null}
    </header>
  )

  if (loading) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6">
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
      <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6">
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
  const allChecked = items.length === 0 || doneCount === items.length
  const day1Locked = !state?.day0?.completed
  const overallPct = Math.min(100, Math.max(0, Math.round(state?.progress?.pct ?? 0)))
  const learnerName = String(state?.customer?.name || '오늘의 학습자')
  const personalizedCurriculum =
    stage === 'day0' && state?.personalized_curriculum?.available ? state.personalized_curriculum : null
  const dynamicPath = stage === 'day0' ? state?.dynamic_curriculum_path ?? [] : []
  const plannedOutline = stage === 'day0' ? state?.planned_curriculum_outline ?? [] : []
  const safetyGateActive = stage === 'day0' && !safetyReady && !current?.completed

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6">
      {header}

      {questionArchiveOpen ? (
        <QuestionArchivePanel groups={questionGroups} deferred={deferredQuestions} onClose={() => setQuestionArchiveOpen(false)} />
      ) : null}

      <div className={questionArchiveOpen ? 'hidden print:hidden' : ''}>
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

        {safetyGateActive && current ? (
          <SafetyOrientationBlock
            stage={current}
            checked={checked}
            conceptFeedback={conceptFeedback}
            coachAnswers={coachAnswers}
            coachThreads={coachThreads}
            coachLoading={coachLoading}
            coachErrors={coachErrors}
            saving={safetySyncing}
            error={error}
            notice={notice}
            routedConceptId={routedConceptId}
            onToggle={toggleCheck}
            onConceptFeedback={updateConceptFeedback}
            onAskCoach={requestCoachAnswer}
            onDeleteCoachAnswer={deleteCoachAnswer}
            onSaveQuestions={saveSafetyQuestions}
            onReady={confirmSafetyOrientation}
          />
        ) : null}

        {!safetyGateActive && personalizedCurriculum ? (
          <PersonalizedDay0Block curriculum={personalizedCurriculum} learnerName={learnerName} />
        ) : null}

        {plannedOutline.length ? (
          <PlannedCurriculumPreview items={plannedOutline} />
        ) : null}

        {!safetyGateActive && dynamicPath.length ? (
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
        {!safetyGateActive && current?.required_action ? (
          <div className="rounded-2xl border border-border bg-accent/40 p-4">
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-accent-cyan">
              <Sparkles size={13} />오늘의 미션
            </div>
            <p className="text-sm leading-relaxed text-ink">{current.required_action}</p>
          </div>
        ) : null}

        {/* 체크리스트 */}
        {!safetyGateActive && items.length > 0 ? (
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
        {!safetyGateActive ? (
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
            disabled={saving || !proof.trim() || !allChecked}
            className="mt-1 flex h-12 items-center justify-center gap-2 rounded-[10px] bg-primary text-[15px] font-semibold text-primary-foreground transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? <Loader2 size={18} className="animate-spin" /> : null}
            {saving ? '저장 중…' : current?.completed ? '완료 상태 업데이트' : '이 단계 완료로 표시'}
          </button>
          {!proof.trim() ? (
            <p className="text-center text-xs text-text-faint">결과를 한 줄이라도 붙여넣으면 완료할 수 있어요.</p>
          ) : !allChecked ? (
            <p className="text-center text-xs text-text-faint">체크리스트를 모두 확인하면 완료할 수 있어요.</p>
          ) : null}
        </div>
        ) : null}
      </div>
      </div>
    </div>
  )
}
