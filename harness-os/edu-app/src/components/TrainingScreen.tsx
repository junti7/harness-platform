import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  Check,
  ChevronDown,
  Clock,
  Copy,
  Download,
  ExternalLink,
  Loader2,
  Lock,
  MessageSquareText,
  Newspaper,
  PlayCircle,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Smartphone,
  Table2,
  Target,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from 'lucide-react'
import { ApiError } from '@/lib/api'
import {
  askSafetyCoach,
  fetchSession,
  rateSafetyCoachAnswer,
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

const BASE_STAGE_ORDER: StageKey[] = ['day0', 'day1']
const SAFETY_COACH_ANSWER_VERSION = '2026-06-28-source-format-v24'
const TRAINING_DEVICE_ID_KEY = 'vp_training_device_id'
const TRAINING_LOCAL_DRAFT_PREFIX = 'vp_training_stage_draft'
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
  conceptBody?: string
  question: string
  answer: string
  model?: string
  fallbackUsed?: boolean
  evidenceUsed?: boolean
  version: string
  createdAt: string
}
type SafetyCoachThreads = SafetyCoachThreadItem[]
type SafetyCoachAnswerRating = 'up' | 'down'
type SafetyCoachAnswerFeedback = Record<string, {
  rating: SafetyCoachAnswerRating
  status?: 'saved' | 'queued' | 'error'
  reviewedAt?: string
}>
type SafetyCoachThreadGroup = {
  stage: StageKey
  label: string
  items: SafetyCoachThreads
}
type SafetyDeletedAnswerKeys = string[]
type DeletedCoachAnswerBackup = {
  conceptId: string
  conceptTitle: string
  conceptBody?: string
  answer: SafetyCoachAnswers[string]
  deletedKey: string
}
type DeletedCoachAnswerBackups = Record<string, DeletedCoachAnswerBackup>
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
type StagePosition = {
  anchorId?: string
  capturedAt?: string
}

function loadTrainingDeviceId(): string {
  try {
    const existing = localStorage.getItem(TRAINING_DEVICE_ID_KEY)
    if (existing) return existing
    const created =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `device-${Date.now()}-${Math.random().toString(36).slice(2)}`
    localStorage.setItem(TRAINING_DEVICE_ID_KEY, created)
    return created
  } catch {
    return `session-device-${Date.now()}-${Math.random().toString(36).slice(2)}`
  }
}

function trainingDeviceType(): 'mobile' | 'tablet' | 'mac' | 'desktop' {
  if (typeof navigator === 'undefined') return 'desktop'
  const ua = navigator.userAgent.toLowerCase()
  const coarse = typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches
  const width = typeof window !== 'undefined' ? window.innerWidth : 1024
  if (/ipad|tablet/.test(ua) || (coarse && width >= 700)) return 'tablet'
  if (ua.includes(['i', 'phone'].join('')) || /android.*mobile|mobile/.test(ua) || (coarse && width < 700)) return 'mobile'
  if (/macintosh|mac os x/.test(ua)) return 'mac'
  return 'desktop'
}

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

function stageNumber(key: StageKey): number {
  const matched = key.match(/^day(\d+)$/)
  return matched ? Number(matched[1]) : 0
}

function stageLabel(key: StageKey): string {
  return `Day ${stageNumber(key)}`
}

function stageOrderFromState(st: TrainingState | null): StageKey[] {
  const fromFlow = (st?.flow_outline ?? []).map((item) => item.key)
  const fromState = Object.keys(st ?? {}).filter((key): key is StageKey => /^day\d+$/.test(key))
  return Array.from(new Set([...BASE_STAGE_ORDER, ...fromFlow, ...fromState])).sort((a, b) => stageNumber(a) - stageNumber(b))
}

function stageIsUnlocked(st: TrainingState | null, key: StageKey): boolean {
  const n = stageNumber(key)
  if (n <= 0) return true
  return Boolean(st?.[`day${n - 1}` as StageKey]?.completed)
}

/** ui_state.selected_stage 우선, 단 이전 Day 완료 시에만 허용. */
function pickStage(st: TrainingState): StageKey {
  const want = st.ui_state?.selected_stage
  if (want && stageIsUnlocked(st, want)) return want
  return 'day0'
}

function stageProgressPct(st: TrainingState | null, stageKey: StageKey): number {
  const flowItem = st?.flow_outline?.find((item) => item.key === stageKey)
  if (typeof flowItem?.pct === 'number') return Math.min(100, Math.max(0, Math.round(flowItem.pct)))
  if (st?.[stageKey]?.completed) return 100
  return Math.min(100, Math.max(0, Math.round(st?.progress?.pct ?? 0)))
}

function llmLabel(value?: string): string {
  const v = (value ?? '').toLowerCase()
  if (v.includes('gpt') || v.includes('chatgpt')) return 'ChatGPT'
  if (v.includes('claude')) return 'Claude'
  if (v.includes('gemini')) return 'Gemini'
  if (v.includes('genspark')) return 'Genspark'
  if (v.includes('grok')) return 'Grok'
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

function isDirectPrincipleQuestion(text: string): boolean {
  const normalized = text.toLowerCase()
  const asksPrinciple = ['왜', '어떻게', '원리', '이유', '작동', '계산', '만들', '나오', '생기', '되는', 'why', 'how', 'principle', 'mechanism', 'work', 'compute'].some((term) => normalized.includes(term))
  const principleTopics = [
    'ai',
    'llm',
    'gpt',
    '챗gpt',
    'chatgpt',
    'claude',
    'gemini',
    '생성형',
    '답변',
    '답',
    '문장',
    '말',
    '단어',
    '토큰',
    'attention',
    '어텐션',
    'transformer',
    '트랜스포머',
    '학습',
    '패턴',
    '추측',
    '이어질',
    '확률',
    '가능성',
    '틀린',
    '오류',
    '거짓',
    '환각',
    '확인',
    '검증',
    '전기',
    '전력',
    '전기세',
    '전기요금',
    '에너지',
    '데이터센터',
    '냉각',
    '서버',
    'gpu',
    '환경',
    '탄소',
    'power',
    'electric',
    'energy',
    'datacenter',
    'data center',
    'cooling',
  ]
  return asksPrinciple && principleTopics.some((term) => normalized.includes(term))
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
  if (currentStage === 'day0' && isDirectPrincipleQuestion(question)) return null
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

function plannedCurriculumGuide(planned?: PlannedCurriculumItem | null): string {
  if (!planned) return ''
  const outcome = String(planned.outcome || '').replace(/다\.$/, '게 됩니다.')
  return `지금 바로 길게 들어가면 Day 0의 핵심이 흐려질 수 있어서, 오늘은 관련 주제가 뒤 훈련에 준비되어 있다는 점만 먼저 알려드립니다. ${planned.title} 과정에서 ${outcome}`
}

function day0BridgeAnswerForUnassignedQuestion(question: string, planned?: PlannedCurriculumItem | null): string | null {
  if (planned) return null
  const normalized = question.toLowerCase()
  const laterGuide = '나중에 이어지는 훈련에서 이 내용을 더 차근차근 다루게 됩니다.'
  if (isDirectPrincipleQuestion(question)) return null
  if (normalized.includes('attention') || normalized.includes('어텐션')) {
    return `좋은 질문입니다. attention은 사람이 문장마다 직접 정해주는 버튼이 아니라, 모델이 아주 많은 글을 학습하면서 “지금 단어가 앞뒤의 어떤 말과 더 관련 있는지”를 계산하도록 배운 값입니다. 예를 들어 “철수가 영희에게 우산을 줬다. 그는 비를 맞고 있었다” 같은 문장에서, 모델은 “그”가 누구를 가리킬지 보려고 주변 단어들 사이의 관련도를 계산합니다. 오늘은 attention을 “문장 안에서 중요한 연결을 찾는 계산 방식” 정도로 이해하면 충분합니다. ${laterGuide}`
  }
  if (normalized.includes('transformer') || normalized.includes('트랜스포머') || normalized.includes('machine learning') || normalized.includes('머신러닝')) {
    return `좋은 질문입니다. Transformer는 머신러닝 안에서 쓰이는 모델 구조 중 하나이고, LLM은 그 구조를 큰 글 데이터로 학습해 말을 만드는 AI라고 보면 됩니다. 오늘은 “LLM이 사람처럼 이해해서 말하는 것이 아니라, 학습한 말의 흐름을 바탕으로 다음 말을 만든다” 정도만 먼저 잡으면 됩니다. ${laterGuide}`
  }
  if (normalized.includes('rag') || normalized.includes('자료') || normalized.includes('근거') || normalized.includes('검증') || normalized.includes('출처')) {
    return `좋은 질문입니다. 수집된 자료를 활용한다는 것은 AI 답을 그대로 믿지 않고, 원문이나 믿을 만한 자료와 다시 맞춰 보는 일입니다. 오늘은 “AI 답은 초안이고, 중요한 내용은 원문이나 수집된 자료로 다시 확인한다” 정도만 기억하면 됩니다. ${laterGuide}`
  }
  if (normalized.includes('프롬프트') || normalized.includes('질문') || normalized.includes('후속')) {
    return `좋은 질문입니다. AI에게 질문을 잘하려면 상황, 원하는 결과, 지켜야 할 조건을 같이 적어주는 것이 좋습니다. 예를 들어 “짧게”, “초등학생도 이해하게”, “틀릴 수 있는 부분도 알려줘”처럼 기준을 붙이면 답이 더 쓸 만해집니다. ${laterGuide}`
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

function currentSafetyCoachAnswerFeedback(raw: unknown, deletedKeys: SafetyDeletedAnswerKeys = []): SafetyCoachAnswerFeedback {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const deleted = new Set(deletedKeys)
  const out: SafetyCoachAnswerFeedback = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (deleted.has(key)) continue
    if (!value || typeof value !== 'object' || Array.isArray(value)) continue
    const row = value as { rating?: string; status?: string; reviewedAt?: string }
    if (row.rating !== 'up' && row.rating !== 'down') continue
    out[key] = {
      rating: row.rating,
      status: row.status === 'queued' || row.status === 'error' ? row.status : 'saved',
      reviewedAt: typeof row.reviewedAt === 'string' ? row.reviewedAt : undefined,
    }
  }
  return out
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

function currentStageChecked(raw: unknown): Record<string, boolean> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const out: Record<string, boolean> = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof key === 'string' && key && typeof value === 'boolean') out[key] = value
  }
  return out
}

function localStageDraftKey(caseId: number, stage: StageKey): string {
  return `${TRAINING_LOCAL_DRAFT_PREFIX}:${caseId}:${stage}`
}

function saveLocalStageDraft(caseId: number, stage: StageKey, draft: Record<string, unknown>) {
  try {
    localStorage.setItem(
      localStageDraftKey(caseId, stage),
      JSON.stringify({ ...draft, local_saved_at: new Date().toISOString() }),
    )
  } catch {
    /* ignore local backup failures */
  }
}

function loadLocalStageDraft(caseId: number, stage: StageKey): Record<string, unknown> {
  try {
    const raw = localStorage.getItem(localStageDraftKey(caseId, stage))
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, unknown> : {}
  } catch {
    return {}
  }
}

function currentStagePosition(raw: unknown): StagePosition {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const item = raw as Record<string, unknown>
  const anchorId = String(item.anchor_id || item.anchorId || '').trim()
  const capturedAt = String(item.captured_at || item.capturedAt || '').trim()
  return {
    ...(anchorId ? { anchorId } : {}),
    ...(capturedAt ? { capturedAt } : {}),
  }
}

function evidenceBadge(value?: boolean): string {
  if (value === true) return '수집된 자료 반영'
  if (value === false) return '일반 원칙 답변'
  return '수집된 자료 반영 전'
}

function coachModelBadge(coach: { model?: string; fallbackUsed?: boolean }): string {
  if (coach.fallbackUsed) return '기본 안전 코치'
  if (!coach.model) return ''
  if (coach.model.includes('fast-template')) return '빠른 안전 코치'
  return coach.model
}

const SAFETY_COACH_ALLOWED_BOLD_LABELS = new Set(['막아야 할 선', '해도 되는 선', '간단히 말하면,', '결론은', '출처:'])

const SAFETY_COACH_ACTION_EMPHASIS_PATTERNS = [
  /"[^"]+"\s*,\s*"[^"]+"\s*같은\s+질문을\s+[^.!?。]*아이(?:가|에게)?\s*직접\s*생각하게\s*하(?:는|게|세요|도록)(?:\s*게)?(?=\s+중요한|\s*것이\s+중요한|\s*점|\s*입니다|[.!?。])/g,
  /[^.!?。]*같은\s+질문을\s+[^.!?。]*아이(?:가|에게)?\s*직접\s*생각하게\s*하(?:는|게|세요|도록)(?:\s*게)?(?=\s+중요한|\s*것이\s+중요한|\s*점|\s*입니다|[.!?。])/g,
]

function sanitizeCoachAnswerForDisplay(value: string): string {
  return String(value || '')
    .split('\n')
    .map((line) => {
      let next = line
      next = next.replace(/\*\*/g, '')
      return next
    })
    .join('\n')
    .trim()
}

function renderInlineCoachMarkdown(text: string, keyPrefix: string) {
  const safeText = sanitizeCoachAnswerForDisplay(text)
  const labelPattern = Array.from(SAFETY_COACH_ALLOWED_BOLD_LABELS)
    .map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  const actionPattern = SAFETY_COACH_ACTION_EMPHASIS_PATTERNS.map((pattern) => pattern.source).join('|')
  const parts = safeText.split(new RegExp(`(\`[^\`]+\`|\\[[^\\]]+\\]\\(https?:\\/\\/[^)\\s]+\\)|${labelPattern}|${actionPattern})`, 'g')).filter(Boolean)
  return parts.map((part, partIndex) => {
    if (SAFETY_COACH_ALLOWED_BOLD_LABELS.has(part.trim()) || SAFETY_COACH_ACTION_EMPHASIS_PATTERNS.some((pattern) => {
      pattern.lastIndex = 0
      return pattern.test(part)
    })) {
      return <strong key={`${keyPrefix}-${partIndex}`} className="font-bold text-ink">{part}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return <code key={`${keyPrefix}-${partIndex}`} className="rounded bg-card px-1 py-0.5 font-mono text-[0.95em] text-ink">{part.slice(1, -1)}</code>
    }
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/)
    if (link) {
      return (
        <a
          key={`${keyPrefix}-${partIndex}`}
          href={link[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-primary underline underline-offset-2"
        >
          {link[1]}
        </a>
      )
    }
    return <span key={`${keyPrefix}-${partIndex}`}>{part}</span>
  })
}

function markdownTableCells(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim())
}

function isMarkdownTableSeparator(line: string): boolean {
  const cells = markdownTableCells(line)
  return cells.length >= 2 && cells.every((cell) => /^:?-{3,}:?$/.test(cell))
}

function isMarkdownTableStart(lines: string[], index: number): boolean {
  return Boolean(lines[index]?.includes('|') && lines[index + 1]?.includes('|') && isMarkdownTableSeparator(lines[index + 1]))
}

function renderCoachTable(lines: string[], start: number): { node: React.ReactNode; next: number } {
  const header = markdownTableCells(lines[start])
  const rows: string[][] = []
  let index = start + 2
  while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
    rows.push(markdownTableCells(lines[index]))
    index += 1
  }
  return {
    next: index,
    node: (
      <div key={`table-${start}`} className="my-2 overflow-x-auto rounded-[10px] border border-border bg-card">
        <table className="w-full min-w-[360px] border-collapse text-left text-[11px]">
          <thead className="bg-secondary text-ink">
            <tr>
              {header.map((cell, cellIndex) => (
                <th key={`head-${cellIndex}`} className="border-b border-border px-2.5 py-2 font-semibold">
                  {renderInlineCoachMarkdown(cell, `table-${start}-head-${cellIndex}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`} className="border-t border-border/70">
                {header.map((_, cellIndex) => (
                  <td key={`cell-${rowIndex}-${cellIndex}`} className="px-2.5 py-2 align-top text-text-muted">
                    {renderInlineCoachMarkdown(row[cellIndex] || '', `table-${start}-${rowIndex}-${cellIndex}`)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ),
  }
}

function renderCoachAnswer(text: string) {
  const lines = sanitizeCoachAnswerForDisplay(text).split('\n')
  const nodes: React.ReactNode[] = []
  let index = 0
  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()
    if (!trimmed) {
      nodes.push(<div key={`gap-${index}`} className="h-2" />)
      index += 1
      continue
    }
    if (isMarkdownTableStart(lines, index)) {
      const rendered = renderCoachTable(lines, index)
      nodes.push(rendered.node)
      index = rendered.next
      continue
    }
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      nodes.push(
        <div key={`heading-${index}`} className="mt-2 font-bold text-ink">
          {renderInlineCoachMarkdown(heading[2], `heading-${index}`)}
        </div>,
      )
      index += 1
      continue
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/)
    if (bullet) {
      const items: string[] = []
      while (index < lines.length) {
        const match = lines[index].trim().match(/^[-*]\s+(.+)$/)
        if (!match) break
        items.push(match[1])
        index += 1
      }
      nodes.push(
        <ul key={`ul-${index}`} className="my-1 list-disc space-y-1 pl-4">
          {items.map((item, itemIndex) => (
            <li key={`li-${itemIndex}`}>{renderInlineCoachMarkdown(item, `ul-${index}-${itemIndex}`)}</li>
          ))}
        </ul>,
      )
      continue
    }
    const numbered = trimmed.match(/^\d+[.)]\s+(.+)$/)
    if (numbered) {
      const items: string[] = []
      while (index < lines.length) {
        const match = lines[index].trim().match(/^\d+[.)]\s+(.+)$/)
        if (!match) break
        items.push(match[1])
        index += 1
      }
      nodes.push(
        <ol key={`ol-${index}`} className="my-1 list-decimal space-y-1 pl-4">
          {items.map((item, itemIndex) => (
            <li key={`li-${itemIndex}`}>{renderInlineCoachMarkdown(item, `ol-${index}-${itemIndex}`)}</li>
          ))}
        </ol>,
      )
      continue
    }
    nodes.push(
      <p key={`p-${index}`} className="my-1">
        {renderInlineCoachMarkdown(line, `p-${index}`)}
      </p>,
    )
    index += 1
  }
  return nodes
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
  return stageOrderFromState(state).map((key) => {
    const draftDeleted = currentDeletedSafetyAnswerKeys(drafts[key]?.deleted_safety_answer_keys)
    const deleted = key === activeStage ? Array.from(new Set([...draftDeleted, ...activeDeletedKeys])) : draftDeleted
    const draftThreads = currentSafetyCoachThreads(drafts[key]?.safety_coach_threads, deleted)
    const items = key === activeStage ? mergeSafetyCoachThreads(draftThreads, activeThreads) : draftThreads
    return { stage: key, label: stageLabel(key), items }
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
  const all = stageOrderFromState(state).map((key) => {
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
  const ua = navigator.userAgent.toLowerCase()
  const isMobile = ua.includes(['i', 'phone'].join('')) || ua.includes('ipad') || ua.includes('ipod') || ua.includes('android')
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
                {activeLength.toLocaleString()}개 개인화 항목이 수집된 자료와 목표에 따라 생성됨
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

function StageDetailPreview({ stage, active = false }: { stage?: TrainingStage; active?: boolean }) {
  const [open, setOpen] = useState(active)
  if (!stage?.title) return null
  const concepts = stage.foundation_concepts ?? []
  const schedule = stage.schedule_blocks ?? []
  const materials = stage.sample_materials ?? []
  const tutorials = stage.tutorial_steps ?? []
  const evidence = stage.evidence_cards ?? []
  const evidenceLabel =
    stage.customer_facing_safe && evidence.length
      ? `수집된 자료 ${evidence.length}개`
      : '맞는 수집된 자료 없음'

  return (
    <section className="rounded-2xl border border-border bg-card p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-faint">
            <ScrollText size={13} />{active ? '오늘의 과정' : '다음 훈련 상세'}
          </div>
          <h2 className="text-base font-bold leading-snug text-ink-strong">
            {active ? '전체 흐름' : stage.title}
          </h2>
          {stage.learning_outcome ? (
            <p className="mt-1 text-xs leading-relaxed text-text-muted">{stage.learning_outcome}</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="shrink-0 rounded-[9px] border border-border bg-secondary px-3 py-2 text-xs font-semibold text-ink transition hover:bg-card"
        >
          {open ? '접기' : '목록'}
        </button>
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <div className="rounded-[12px] bg-secondary px-3 py-2.5">
          <div className="text-[11px] font-semibold text-text-faint">진행</div>
          <div className="mt-0.5 text-sm font-semibold text-ink">{schedule.length || 0}개 블록</div>
        </div>
        <div className="rounded-[12px] bg-secondary px-3 py-2.5">
          <div className="text-[11px] font-semibold text-text-faint">실습팩</div>
          <div className="mt-0.5 text-sm font-semibold text-ink">{materials.length || 0}개</div>
        </div>
        <div className="rounded-[12px] bg-secondary px-3 py-2.5">
          <div className="text-[11px] font-semibold text-text-faint">수집된 자료</div>
          <div className="mt-0.5 text-sm font-semibold text-ink">{evidenceLabel}</div>
        </div>
      </div>

      {open ? (
        <div className="mt-3 grid gap-3">
          {!active && concepts.length ? (
            <div className="rounded-[12px] border border-border bg-secondary/70 p-3">
              <div className="mb-2 text-xs font-semibold text-ink">기초 설명</div>
              <ol className="grid gap-1.5">
                {concepts.slice(0, 6).map((item, index) => (
                  <li key={`${item.title}-${index}`} className="text-xs leading-relaxed text-text-muted">
                    {index + 1}. {item.title}
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
          {schedule.length ? (
            <div className="rounded-[12px] border border-border bg-secondary/70 p-3">
              <div className="mb-2 text-xs font-semibold text-ink">시간표</div>
              <ol className="grid gap-1.5">
                {schedule.map((item, index) => (
                  <li key={`${item.title}-${index}`} className="text-xs leading-relaxed text-text-muted">
                    {item.minutes ? `${item.minutes}분 · ` : ''}{item.title}
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
          {materials.length ? (
            <div className="rounded-[12px] border border-border bg-secondary/70 p-3">
              <div className="mb-2 text-xs font-semibold text-ink">실습 자료</div>
              <div className="grid gap-2">
                {materials.map((item) => (
                  <div key={item.kit_id || item.title} className="rounded-[10px] bg-card px-3 py-2">
                    <div className="text-xs font-semibold text-ink">{item.title}</div>
                    {item.description ? <p className="mt-1 text-[11px] leading-relaxed text-text-faint">{item.description}</p> : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {tutorials.length ? (
            <div className="rounded-[12px] border border-border bg-secondary/70 p-3">
              <div className="mb-2 text-xs font-semibold text-ink">실습 순서</div>
              <ol className="grid gap-1.5">
                {tutorials.map((item, index) => (
                  <li key={item.id || `${item.title}-${index}`} className="text-xs leading-relaxed text-text-muted">
                    {index + 1}. {item.title}
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
          <div className="rounded-[12px] border border-border bg-secondary/70 p-3">
            <div className="mb-2 text-xs font-semibold text-ink">수집된 자료 반영</div>
            {evidence.length && stage.customer_facing_safe ? (
              <div className="grid gap-2">
                {evidence.map((item, index) => (
                  <div key={`${item.title}-${index}`} className="rounded-[10px] bg-card px-3 py-2">
                    <div className="text-xs font-semibold leading-snug text-ink">{item.title}</div>
                    {item.snippet ? <p className="mt-1 text-[11px] leading-relaxed text-text-faint">{item.snippet}</p> : null}
                    {item.cite ? <p className="mt-1 text-[11px] leading-relaxed text-text-faint">{item.cite}</p> : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs leading-relaxed text-text-muted">
                현재 질문과 딱 맞는 수집된 자료가 없어서 사용자 답변에는 자료를 억지로 붙이지 않습니다.
              </p>
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function StageConceptBlock({
  stage,
  checked,
  conceptFeedback,
  coachAnswers,
  coachFeedback,
  coachLoading,
  coachErrors,
  onToggle,
  onConceptFeedback,
  onAskCoach,
  onRateCoachAnswer,
  onDeleteCoachAnswer,
}: {
  stage: TrainingStage
  checked: Record<string, boolean>
  conceptFeedback: SafetyConceptFeedback
  coachAnswers: SafetyCoachAnswers
  coachFeedback: SafetyCoachAnswerFeedback
  coachLoading: Record<string, boolean>
  coachErrors: Record<string, string>
  onToggle: (id: string) => void
  onConceptFeedback: (id: string, value: string) => void
  onAskCoach: (concept: NonNullable<TrainingStage['foundation_concepts']>[number], id: string) => void
  onRateCoachAnswer: (
    concept: NonNullable<TrainingStage['foundation_concepts']>[number],
    id: string,
    item: SafetyCoachAnswers[string] | SafetyCoachThreadItem,
    rating: SafetyCoachAnswerRating,
  ) => void
  onDeleteCoachAnswer: (id: string) => void
}) {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const concepts = stage.foundation_concepts ?? []
  const conceptItems = concepts.map((concept, index) => ({ ...concept, checkId: conceptId(concept, index) }))
  if (!conceptItems.length) return null
  const renderAnswerRating = (
    concept: NonNullable<TrainingStage['foundation_concepts']>[number],
    id: string,
    item: SafetyCoachAnswers[string] | SafetyCoachThreadItem,
  ) => {
    const key = safetyAnswerKey(id, item.version, item.question)
    const selected = coachFeedback[key]?.rating
    return (
      <div className="mt-2 flex items-center gap-1.5" aria-label="AI 코치 답변 평가">
        <button
          type="button"
          onClick={() => onRateCoachAnswer(concept, id, item, 'up')}
          className={`inline-flex h-8 w-8 items-center justify-center rounded-[8px] border transition ${
            selected === 'up'
              ? 'border-primary bg-primary text-primary-foreground'
              : 'border-border bg-secondary text-text-muted hover:bg-card hover:text-primary'
          }`}
          title="좋아요"
          aria-label="좋아요"
        >
          <ThumbsUp size={14} />
        </button>
        <button
          type="button"
          onClick={() => onRateCoachAnswer(concept, id, item, 'down')}
          className={`inline-flex h-8 w-8 items-center justify-center rounded-[8px] border transition ${
            selected === 'down'
              ? 'border-danger bg-danger-soft text-danger'
              : 'border-border bg-secondary text-text-muted hover:bg-card hover:text-danger'
          }`}
          title="싫어요"
          aria-label="싫어요"
        >
          <ThumbsDown size={14} />
        </button>
        {selected ? (
          <span className="text-[11px] leading-relaxed text-text-faint">
            {selected === 'up' ? '좋아요 반영됨' : '자동강화 분석 예약됨'}
          </span>
        ) : null}
      </div>
    )
  }

  return (
    <section className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
      <div className="mb-3 flex items-start gap-2.5">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-card text-primary">
          <Target size={18} />
        </span>
        <div className="min-w-0">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-primary">
            실습 전 기준 확인
          </div>
          <h2 className="text-base font-bold leading-snug text-ink-strong">AI를 쓰기 전에 오늘의 기준부터 확인하기</h2>
          <p className="mt-1 text-sm leading-relaxed text-text-muted">
            Day 0처럼 먼저 기준을 읽고, 이해한 항목을 체크하고, 헷갈리는 점을 적어둔 뒤 실제 자료 실습으로 넘어갑니다.
          </p>
        </div>
      </div>

      <div className="grid gap-2">
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
            <div key={concept.checkId} id={`concept-card-${concept.checkId}`} data-training-anchor="true" className="rounded-[12px] border border-border bg-card p-3">
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
                placeholder={concept.question_prompt ?? '실습 전에 더 묻고 싶은 점을 적어주세요.'}
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
                      {coachModelBadge(coach) ? <span>{coachModelBadge(coach)}</span> : null}
                    </span>
                  </div>
                  {renderCoachAnswer(coach.answer)}
                  {renderAnswerRating(concept, concept.checkId, coach)}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </section>
  )
}

function Day1PracticeLab({ stage }: { stage: TrainingStage }) {
  const [copied, setCopied] = useState(false)
  const lab = stage.practice_lab
  if (!lab) return null
  const toolCards = lab.tool_cards ?? []
  const visualAssets = lab.visual_assets ?? []
  const installGuide = lab.install_guide
  const rows = lab.practice_table ?? []
  const checks = lab.verification_rows ?? []
  const slots = lab.result_slots ?? []
  const prompt = lab.prompt_template || stage.practice_prompt_template || ''

  async function copyPrompt() {
    if (!prompt.trim()) return
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="rounded-2xl border border-primary/25 bg-card p-4 shadow-[0_0_0_1px_rgba(37,99,235,0.05)]">
      <div className="mb-4 flex items-start gap-2.5">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-primary text-primary-foreground">
          <PlayCircle size={18} />
        </span>
        <div className="min-w-0">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-primary">화면 안 실습실</div>
          <h2 className="text-base font-bold leading-snug text-ink-strong">{lab.headline || '앱 안에서 먼저 준비하고 실습합니다'}</h2>
          {lab.context_hint ? <p className="mt-1 text-xs leading-relaxed text-text-muted">{lab.context_hint}</p> : null}
        </div>
      </div>

      {visualAssets.length ? (
        <div className="mb-4 grid gap-2 sm:grid-cols-4">
          {visualAssets.map((asset) => (
            <figure key={asset.src} className="overflow-hidden rounded-[14px] border border-border bg-secondary/70">
              <img
                src={asset.src}
                alt={asset.alt || asset.caption || ''}
                loading="lazy"
                className="aspect-[16/9] w-full bg-card object-cover"
              />
              {asset.caption ? <figcaption className="px-3 py-2 text-xs font-semibold text-ink">{asset.caption}</figcaption> : null}
            </figure>
          ))}
        </div>
      ) : null}

      {toolCards.length ? (
        <div className="mb-4 grid gap-2 sm:grid-cols-3">
          {toolCards.map((item, index) => {
            const Icon = item.visual === 'phone' ? Smartphone : item.visual === 'app' ? Download : MessageSquareText
            return (
              <div key={`${item.title}-${index}`} className="rounded-[14px] border border-border bg-secondary/70 p-3">
                {item.image_src ? (
                  <img
                    src={item.image_src}
                    alt={item.image_alt || item.title}
                    loading="lazy"
                    className="mb-3 aspect-[16/9] w-full rounded-[12px] border border-border bg-card object-cover"
                  />
                ) : null}
                <div className="mb-2 flex items-center gap-2">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-card text-primary">
                    <Icon size={17} />
                  </span>
                  <div className="text-sm font-bold leading-snug text-ink">{item.title}</div>
                </div>
                {item.body ? <p className="text-xs leading-relaxed text-text-muted">{item.body}</p> : null}
                {item.action ? (
                  <div className="mt-2 rounded-[10px] border border-primary/20 bg-primary/5 px-3 py-2 text-[11px] font-semibold leading-relaxed text-primary">
                    {item.action}
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      ) : null}

      {installGuide ? (
        <div className="mb-4 grid gap-3 rounded-[14px] border border-primary/20 bg-primary/5 p-3 md:grid-cols-[0.9fr_1.1fr]">
          {installGuide.image_src ? (
            <img
              src={installGuide.image_src}
              alt={installGuide.image_alt || installGuide.title || 'AI 앱 설치 안내'}
              loading="lazy"
              className="aspect-[16/9] w-full rounded-[12px] border border-primary/15 bg-card object-cover"
            />
          ) : null}
          <div className="min-w-0">
            <div className="mb-1 flex items-center gap-2 text-xs font-bold text-primary">
              <Download size={15} /> 설치가 처음이라면
            </div>
            {installGuide.title ? <h3 className="text-sm font-bold leading-snug text-ink">{installGuide.title}</h3> : null}
            {installGuide.intro ? <p className="mt-1 text-xs leading-relaxed text-text-muted">{installGuide.intro}</p> : null}
            {installGuide.tool_options?.length ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {installGuide.tool_options.map((tool) => {
                  const selected = installGuide.selected_tool === tool
                  return (
                    <span
                      key={tool}
                      className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
                        selected
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-primary/20 bg-card text-primary'
                      }`}
                    >
                      {tool}
                    </span>
                  )
                })}
              </div>
            ) : null}
            {installGuide.steps?.length ? (
              <ol className="mt-3 space-y-2">
                {installGuide.steps.map((step, index) => (
                  <li key={`${step}-${index}`} className="flex gap-2 text-xs leading-relaxed text-ink">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                      {index + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            ) : null}
            {installGuide.fallback ? (
              <div className="mt-3 rounded-[10px] border border-primary/20 bg-card px-3 py-2 text-[11px] font-semibold leading-relaxed text-primary">
                {installGuide.fallback}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {rows.length ? (
        <div className="mb-4 overflow-hidden rounded-[14px] border border-border">
          <div className="flex items-center gap-2 border-b border-border bg-secondary px-3 py-2 text-xs font-bold text-ink">
            <Table2 size={15} className="text-primary" /> 어디서 무엇을 하나요?
          </div>
          <div className="grid grid-cols-[0.72fr_1fr_1fr] bg-card text-[11px] leading-relaxed">
            <div className="border-b border-border bg-secondary px-3 py-2 font-semibold text-text-muted">단계</div>
            <div className="border-b border-l border-border bg-secondary px-3 py-2 font-semibold text-text-muted">이 앱 안에서</div>
            <div className="border-b border-l border-border bg-secondary px-3 py-2 font-semibold text-text-muted">AI 앱에서</div>
            {rows.map((row) => (
              <div key={row.step} className="contents">
                <div className="border-b border-border px-3 py-2 font-semibold text-ink">{row.step}</div>
                <div className="border-b border-l border-border px-3 py-2 text-text-muted">{row.in_app}</div>
                <div className="border-b border-l border-border px-3 py-2 text-text-muted">{row.outside_app}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {prompt ? (
        <div className="mb-4 rounded-[14px] border border-border bg-secondary/70 p-3">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-bold text-ink">
              <Copy size={15} className="text-primary" /> 복붙 프롬프트
            </div>
            <button
              type="button"
              onClick={copyPrompt}
              className="rounded-[9px] bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground transition hover:brightness-105"
            >
              {copied ? '복사됨' : '복사'}
            </button>
          </div>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-[12px] bg-card p-3 text-xs leading-relaxed text-ink">{prompt}</pre>
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
        {checks.length ? (
          <div className="rounded-[14px] border border-border bg-card">
            <div className="border-b border-border px-3 py-2 text-xs font-bold text-ink">원문 대조표</div>
            <div className="grid gap-2 p-3">
              {checks.map((item) => (
                <div key={item.item} className="grid gap-1 rounded-[12px] bg-secondary px-3 py-2">
                  <div className="text-xs font-bold text-primary">{item.item}</div>
                  <div className="text-[11px] leading-relaxed text-text-muted">원문: {item.source}</div>
                  <div className="text-[11px] leading-relaxed text-text-muted">확인: {item.ai_check}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {slots.length ? (
          <div className="rounded-[14px] border border-border bg-card">
            <div className="border-b border-border px-3 py-2 text-xs font-bold text-ink">결과 붙여넣기 4칸</div>
            <ol className="grid gap-2 p-3">
              {slots.map((slot, index) => (
                <li key={slot} className="flex items-center gap-2 rounded-[12px] bg-secondary px-3 py-2 text-xs font-semibold text-ink">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-bold text-primary">
                    {index + 1}
                  </span>
                  {slot}
                </li>
              ))}
            </ol>
          </div>
        ) : null}
      </div>
    </section>
  )
}

function SafetyOrientationBlock({
  stage,
  checked,
  conceptFeedback,
  coachAnswers,
  coachThreads,
  coachFeedback,
  coachLoading,
  coachErrors,
  saving,
  error,
  notice,
  routedConceptId,
  onToggle,
  onConceptFeedback,
  onAskCoach,
  onRateCoachAnswer,
  onDeleteCoachAnswer,
  onReady,
  reviewMode = false,
}: {
  stage: TrainingStage
  checked: Record<string, boolean>
  conceptFeedback: SafetyConceptFeedback
  coachAnswers: SafetyCoachAnswers
  coachThreads: SafetyCoachThreads
  coachFeedback: SafetyCoachAnswerFeedback
  coachLoading: Record<string, boolean>
  coachErrors: Record<string, string>
  saving: boolean
  error?: string | null
  notice?: string | null
  routedConceptId?: string | null
  onToggle: (id: string) => void
  onConceptFeedback: (id: string, value: string) => void
  onAskCoach: (concept: NonNullable<TrainingStage['foundation_concepts']>[number], id: string) => void
  onRateCoachAnswer: (
    concept: NonNullable<TrainingStage['foundation_concepts']>[number],
    id: string,
    item: SafetyCoachAnswers[string] | SafetyCoachThreadItem,
    rating: SafetyCoachAnswerRating,
  ) => void
  onDeleteCoachAnswer: (id: string) => void
  onReady: () => void
  reviewMode?: boolean
}) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const concepts = stage.foundation_concepts ?? []
  const conceptItems = concepts.map((concept, index) => ({ ...concept, checkId: conceptId(concept, index) }))
  const ready =
    conceptItems.length > 0 &&
    conceptItems.every((item) => checked[item.checkId])
  const renderAnswerRating = (
    concept: NonNullable<TrainingStage['foundation_concepts']>[number],
    id: string,
    item: SafetyCoachAnswers[string] | SafetyCoachThreadItem,
  ) => {
    const key = safetyAnswerKey(id, item.version, item.question)
    const selected = coachFeedback[key]?.rating
    return (
      <div className="mt-2 flex items-center gap-1.5" aria-label="AI 코치 답변 평가">
        <button
          type="button"
          onClick={() => onRateCoachAnswer(concept, id, item, 'up')}
          className={`inline-flex h-8 w-8 items-center justify-center rounded-[8px] border transition ${
            selected === 'up'
              ? 'border-primary bg-primary text-primary-foreground'
              : 'border-border bg-secondary text-text-muted hover:bg-card hover:text-primary'
          }`}
          title="좋아요"
          aria-label="좋아요"
        >
          <ThumbsUp size={14} />
        </button>
        <button
          type="button"
          onClick={() => onRateCoachAnswer(concept, id, item, 'down')}
          className={`inline-flex h-8 w-8 items-center justify-center rounded-[8px] border transition ${
            selected === 'down'
              ? 'border-danger bg-danger-soft text-danger'
              : 'border-border bg-secondary text-text-muted hover:bg-card hover:text-danger'
          }`}
          title="싫어요"
          aria-label="싫어요"
        >
          <ThumbsDown size={14} />
        </button>
        {selected ? (
          <span className="text-[11px] leading-relaxed text-text-faint">
            {selected === 'up' ? '좋아요 반영됨' : '자동강화 분석 예약됨'}
          </span>
        ) : null}
      </div>
    )
  }

  return (
    <section className="rounded-2xl border border-danger/20 bg-danger-soft/45 p-4">
      <div className="mb-3 flex items-start gap-2.5">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-card text-danger">
          <ShieldCheck size={18} />
        </span>
        <div className="min-w-0">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-danger">
            {reviewMode ? '저장된 안전 확인 기록' : '실습 전 안전 확인'}
          </div>
          <h2 className="text-base font-bold leading-snug text-ink-strong">AI를 쓰기 전에 먼저 알아야 할 것</h2>
          <p className="mt-1 text-sm leading-relaxed text-text-muted">
            {reviewMode
              ? 'Day 0에서 체크했던 항목, 남긴 질문, AI 코치 답변을 다시 볼 수 있습니다.'
              : '먼저 AI, LLM(큰 언어 모델), 생성형 AI가 무엇인지 아주 쉬운 말로 확인합니다. 각 단락을 읽고 이해했는지 표시하거나, 헷갈리는 점을 적어 질문으로 남긴 뒤 실제 질문 실습으로 넘어갑니다.'}
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
              {coachThreads.slice().reverse().map((item) => {
                const concept = conceptItems.find((row) => row.checkId === item.conceptId)
                const ratingConcept = concept ?? {
                  title: item.conceptTitle,
                  body: item.conceptBody ?? '',
                }
                return (
                  <div key={item.id} className="rounded-[10px] border border-border bg-secondary px-3 py-2">
                    <div className="mb-1 text-[11px] font-semibold text-primary">{item.conceptTitle}</div>
                    <p className="text-xs font-semibold leading-relaxed text-ink">Q. {item.question}</p>
                    <p className="mt-1 text-xs leading-relaxed text-text-muted">A. {item.answer}</p>
                    {renderAnswerRating(ratingConcept, item.conceptId, item)}
                  </div>
                )
              })}
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
              data-training-anchor="true"
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
                      {coachModelBadge(coach) ? (
                        <span>
                          {coachModelBadge(coach)}
                        </span>
                      ) : null}
                    </span>
                  </div>
                  {renderCoachAnswer(coach.answer)}
                  {renderAnswerRating(concept, concept.checkId, coach)}
                </div>
              ) : null}
            </div>
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

      {!reviewMode ? (
        <>
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
              설명 단락을 모두 체크하면 실제 AI 실습이 열립니다. 이해되지 않으면 질문을 남겨주세요.
            </p>
          ) : null}
        </>
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
  const [coachAnswerFeedback, setCoachAnswerFeedback] = useState<SafetyCoachAnswerFeedback>({})
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
  const deviceIdRef = useRef(loadTrainingDeviceId())
  const deviceTypeRef = useRef(trainingDeviceType())
  const checkedRef = useRef<Record<string, boolean>>({})
  const conceptFeedbackRef = useRef<SafetyConceptFeedback>({})
  const coachAnswersRef = useRef<SafetyCoachAnswers>({})
  const coachThreadsRef = useRef<SafetyCoachThreads>([])
  const coachAnswerFeedbackRef = useRef<SafetyCoachAnswerFeedback>({})
  const deferredSafetyQuestionsRef = useRef<DeferredSafetyQuestions>([])
  const deletedSafetyAnswerKeysRef = useRef<SafetyDeletedAnswerKeys>([])
  const deletedCoachAnswerBackupsRef = useRef<DeletedCoachAnswerBackups>({})
  const lastPositionRef = useRef<StagePosition>({})
  const restoreAnchorRef = useRef<string>('')
  const restoringPositionRef = useRef(false)
  const positionSyncTimerRef = useRef<number | null>(null)
  const initialSessionKeyRef = useRef('')

  const stageDraftForSync = useCallback((extras: Record<string, unknown> = {}, stageKey: StageKey = stage): Record<string, unknown> => {
    const draft = {
      safety_concept_feedback: conceptFeedbackRef.current,
      safety_coach_answers: coachAnswersRef.current,
      safety_coach_threads: coachThreadsRef.current,
      safety_coach_answer_feedback: coachAnswerFeedbackRef.current,
      deferred_safety_questions: deferredSafetyQuestionsRef.current,
      deleted_safety_answer_keys: deletedSafetyAnswerKeysRef.current,
      stage_checked: checkedRef.current,
      last_position: lastPositionRef.current.anchorId
        ? {
            anchor_id: lastPositionRef.current.anchorId,
            captured_at: lastPositionRef.current.capturedAt || new Date().toISOString(),
          }
        : lastPositionRef.current,
      ...extras,
    }
    saveLocalStageDraft(caseId, stageKey, draft)
    return draft
  }, [caseId, stage])

  const syncStageDraft = useCallback((eventName: string, eventPayload: Record<string, unknown> = {}) => {
    if (!state) return
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: stage,
      clientSeq: seqRef.current,
      eventName,
      eventPayload: { stage, ...eventPayload },
      stageDrafts: {
        [stage]: stageDraftForSync(),
      },
    })
      .then((next) => setState(next))
      .catch((e) => console.error(`${eventName} sync failed`, e))
  }, [caseId, email, stage, stageDraftForSync, state])

  const claimTrainingDevice = useCallback((stageKey: StageKey, anchorId = '') => {
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: stageKey,
      clientSeq: seqRef.current,
      eventName: 'claim_training_device',
      eventPayload: {
        device_id: deviceIdRef.current,
        device_type: deviceTypeRef.current,
        anchor_id: anchorId,
      },
      stageDrafts: {
        [stageKey]: stageDraftForSync({}, stageKey),
      },
    })
      .then((next) => {
        const serverSeq = Number(next.ui_state?.last_client_seq ?? 0)
        if (serverSeq >= seqRef.current) setState(next)
        seqRef.current = Math.max(seqRef.current, serverSeq)
      })
      .catch((e) => console.error('claim training device failed', e))
  }, [caseId, email, stageDraftForSync])

  // 단계 전환 시 로컬 입력(증거물/체크)을 그 단계 값으로 재시드.
  const hydrateStageInputs = useCallback((st: TrainingState, next: StageKey) => {
    setStage(next)
    setProof(String(st[next]?.proof_artifact ?? ''))
    const serverDraft = st.ui_state?.stage_drafts?.[next]
    const localDraft = loadLocalStageDraft(caseId, next)
    const draft = serverDraft || localDraft
    const serverChecked = currentStageChecked(serverDraft?.stage_checked)
    const localChecked = currentStageChecked(localDraft?.stage_checked)
    const nextChecked = Object.keys(serverChecked).length ? serverChecked : localChecked
    const nextPosition = currentStagePosition(draft?.last_position)
    const feedback = draft?.safety_concept_feedback
    const answers = draft?.safety_coach_answers
    const threads = draft?.safety_coach_threads
    const answerFeedback = draft?.safety_coach_answer_feedback
    const deferred = draft?.deferred_safety_questions
    const deleted = currentDeletedSafetyAnswerKeys(draft?.deleted_safety_answer_keys)
    const nextFeedback = currentSafetyConceptFeedback(feedback, deleted)
    const nextAnswers = currentSafetyCoachAnswers(answers, nextFeedback, deleted)
    const nextThreads = currentSafetyCoachThreads(threads, deleted)
    const nextAnswerFeedback = currentSafetyCoachAnswerFeedback(answerFeedback, deleted)
    const nextDeferred = currentDeferredSafetyQuestions(deferred, deleted)
    checkedRef.current = nextChecked
    conceptFeedbackRef.current = nextFeedback
    coachAnswersRef.current = nextAnswers
    coachThreadsRef.current = nextThreads
    coachAnswerFeedbackRef.current = nextAnswerFeedback
    deferredSafetyQuestionsRef.current = nextDeferred
    deletedSafetyAnswerKeysRef.current = deleted
    lastPositionRef.current = nextPosition
    restoreAnchorRef.current = nextPosition.anchorId || ''
    restoringPositionRef.current = Boolean(nextPosition.anchorId)
    setChecked(nextChecked)
    setConceptFeedback(nextFeedback)
    setCoachAnswers(nextAnswers)
    setCoachThreads(nextThreads)
    setCoachAnswerFeedback(nextAnswerFeedback)
    setDeferredSafetyQuestions(nextDeferred)
    setDeletedSafetyAnswerKeys(deleted)
    setCoachLoading({})
    setCoachErrors({})
    setWhyOpen(false)
    setSafetyReady(Boolean(st[next]?.completed || st.ui_state?.safety_confirmed?.[next]))
    setSafetySyncing(false)
    setNotice(null)
    setRoutedConceptId(null)
  }, [caseId])

  // 마운트 시 세션 1회 로드. setState 는 async 콜백 안에서만 호출.
  useEffect(() => {
    const sessionKey = `${email}:${caseId}`
    if (initialSessionKeyRef.current === sessionKey) return
    initialSessionKeyRef.current = sessionKey
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
        const nextStage = pickStage(nextState)
        hydrateStageInputs(nextState, nextStage)
        setLoading(false)
        claimTrainingDevice(nextStage, currentStagePosition(nextState.ui_state?.stage_drafts?.[nextStage]?.last_position).anchorId || '')
      } catch (e) {
        initialSessionKeyRef.current = ''
        if (!alive) return
        setError(errMsg(e))
        setLoading(false)
      }
    })()
    return () => {
      alive = false
      if (positionSyncTimerRef.current !== null) {
        window.clearTimeout(positionSyncTimerRef.current)
        positionSyncTimerRef.current = null
      }
    }
  }, [email, caseId, claimTrainingDevice, hydrateStageInputs])

  useEffect(() => {
    if (loading || !state) return
    const anchorId = restoreAnchorRef.current
    if (!anchorId) return
    restoreAnchorRef.current = ''
    window.setTimeout(() => {
      const el = document.getElementById(anchorId)
      if (!el) {
        restoringPositionRef.current = false
        return
      }
      el.scrollIntoView({ block: 'start', behavior: 'auto' })
      window.scrollBy({ top: -12, left: 0, behavior: 'auto' })
      window.setTimeout(() => {
        restoringPositionRef.current = false
      }, 120)
    }, 80)
  }, [loading, state, stage, safetyReady])

  useEffect(() => {
    if (loading || !state || questionArchiveOpen) return
    const captureVisibleAnchor = () => {
      if (restoringPositionRef.current) return
      const anchors = Array.from(document.querySelectorAll<HTMLElement>('[data-training-anchor="true"]'))
      if (!anchors.length) return
      let best: HTMLElement | null = null
      let bestDistance = Number.POSITIVE_INFINITY
      for (const el of anchors) {
        const rect = el.getBoundingClientRect()
        if (rect.bottom < 0 || rect.top > window.innerHeight) continue
        const distance = Math.abs(rect.top - 16)
        if (distance < bestDistance) {
          bestDistance = distance
          best = el
        }
      }
      const anchorId = best?.id || ''
      if (!anchorId || lastPositionRef.current.anchorId === anchorId) return
      const capturedAt = new Date().toISOString()
      lastPositionRef.current = { anchorId, capturedAt }
      if (positionSyncTimerRef.current !== null) window.clearTimeout(positionSyncTimerRef.current)
      positionSyncTimerRef.current = window.setTimeout(() => {
        positionSyncTimerRef.current = null
        syncStageDraft('training_position_saved', { anchor_id: anchorId, captured_at: capturedAt })
      }, 900)
    }
    captureVisibleAnchor()
    window.addEventListener('scroll', captureVisibleAnchor, { passive: true })
    window.addEventListener('resize', captureVisibleAnchor)
    return () => {
      window.removeEventListener('scroll', captureVisibleAnchor)
      window.removeEventListener('resize', captureVisibleAnchor)
    }
  }, [loading, state, stage, safetyReady, questionArchiveOpen, syncStageDraft])

  useEffect(() => {
    if (loading || !state) return
    const timer = window.setInterval(() => {
      void fetchSession(email, caseId)
        .then((result) => {
          if (!result.exists) return
          const activeDeviceId = result.state.ui_state?.active_training_device_id || ''
          const activeCaseId = Number(result.state.ui_state?.active_training_case_id || 0)
          if (activeDeviceId && activeDeviceId !== deviceIdRef.current && activeCaseId === caseId) {
            try {
              sessionStorage.setItem('vp_training_handoff_notice', `${result.state.ui_state?.active_training_device_type || '다른 기기'}에서 이어가는 중입니다.`)
            } catch {
              /* ignore */
            }
            onBack()
            return
          }
          seqRef.current = Math.max(seqRef.current, Number(result.state.ui_state?.last_client_seq ?? 0))
        })
        .catch((e) => console.error('training handoff poll failed', e))
    }, 5000)
    return () => window.clearInterval(timer)
  }, [caseId, email, loading, onBack, state])

  function selectStage(next: StageKey) {
    if (!state || next === stage) return
    if (!stageIsUnlocked(state, next)) return
    hydrateStageInputs(state, next)
    claimTrainingDevice(next, currentStagePosition(state.ui_state?.stage_drafts?.[next]?.last_position).anchorId || '')
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: next,
      clientSeq: seqRef.current,
      eventName: 'select_stage',
      eventPayload: { selected_stage: next },
      stageDrafts: {
        [next]: stageDraftForSync({}, next),
      },
    })
      .then((nextState) => {
        const serverSeq = Number(nextState.ui_state?.last_client_seq ?? 0)
        if (serverSeq >= seqRef.current) {
          setState({
            ...nextState,
            ui_state: {
              ...nextState.ui_state,
              selected_stage: next,
            },
          })
        }
        seqRef.current = Math.max(seqRef.current, serverSeq)
      })
      .catch((e) => console.error('syncSession failed', e))
  }

  function toggleCheck(id: string) {
    setChecked((prev) => {
      const next = { ...prev, [id]: !prev[id] }
      checkedRef.current = next
      stageDraftForSync({ stage_checked: next })
      return next
    })
    window.setTimeout(() => {
      syncStageDraft('training_check_saved', { check_id: id, checked: Boolean(checkedRef.current[id]) })
    }, 0)
  }

  function updateConceptFeedback(id: string, value: string) {
    let nextFeedback: SafetyConceptFeedback = conceptFeedbackRef.current
    setConceptFeedback((prev) => {
      const next = { ...prev, [id]: value }
      conceptFeedbackRef.current = next
      nextFeedback = next
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
    stageDraftForSync({ safety_concept_feedback: nextFeedback })
  }

  function deleteCoachAnswer(id: string) {
    const currentAnswer = coachAnswersRef.current[id]
    if (!state || !currentAnswer?.answer) return
    const deleteKey = safetyAnswerKey(id, currentAnswer.version, currentAnswer.question)
    const deletedAt = new Date().toISOString()
    const conceptItems = (current?.foundation_concepts ?? []).map((item, index) => ({ ...item, checkId: conceptId(item, index) }))
    const sourceConcept = conceptItems.find((item) => item.checkId === id)
    deletedCoachAnswerBackupsRef.current[deleteKey] = {
      conceptId: id,
      conceptTitle: sourceConcept?.title ?? '',
      conceptBody: sourceConcept?.body,
      answer: currentAnswer,
      deletedKey: deleteKey,
    }
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
          safety_coach_answer_feedback: coachAnswerFeedbackRef.current,
          deferred_safety_questions: persistedDeferred,
          deleted_safety_answer_keys: nextDeleted,
          stage_checked: checkedRef.current,
          last_position: lastPositionRef.current.anchorId
            ? {
                anchor_id: lastPositionRef.current.anchorId,
                captured_at: lastPositionRef.current.capturedAt || new Date().toISOString(),
              }
            : lastPositionRef.current,
        },
      },
    }).then((next) => setState(next)).catch((e) => {
      console.error('delete safety answer sync failed', e)
      setCoachErrors((prev) => ({ ...prev, [id]: errMsg(e) }))
    })
  }

  function restoreDeletedCoachAnswerAfterTimeout(
    concept: NonNullable<TrainingStage['foundation_concepts']>[number],
    id: string,
    question: string,
  ): boolean {
    if (!state) return false
    const normalizedQuestion = question.trim()
    const backup = Object.values(deletedCoachAnswerBackupsRef.current).find((item) => {
      const answerQuestion = (item.answer.question ?? '').trim()
      return item.conceptId === id && answerQuestion === normalizedQuestion && Boolean(item.answer.answer?.trim())
    })
    if (!backup) return false
    const restoredAt = new Date().toISOString()
    const answerVersion = backup.answer.version || SAFETY_COACH_ANSWER_VERSION
    const restoredAnswer: SafetyCoachAnswers[string] = {
      ...backup.answer,
      question: normalizedQuestion,
      version: answerVersion,
    }
    const threadItem: SafetyCoachThreadItem = {
      id: `${id}-${restoredAt}`,
      conceptId: id,
      conceptTitle: backup.conceptTitle || concept.title,
      conceptBody: backup.conceptBody || concept.body,
      question: normalizedQuestion,
      answer: restoredAnswer.answer,
      model: restoredAnswer.model || 'local-timeout-restore',
      fallbackUsed: Boolean(restoredAnswer.fallbackUsed),
      evidenceUsed: restoredAnswer.evidenceUsed,
      version: answerVersion,
      createdAt: restoredAt,
    }
    const restoreKey = safetyAnswerKey(id, answerVersion, normalizedQuestion)
    const nextDeleted = deletedSafetyAnswerKeysRef.current.filter((key) => key !== restoreKey && key !== backup.deletedKey)
    const nextAnswers = { ...coachAnswersRef.current, [id]: restoredAnswer }
    const nextThreads = appendSafetyCoachThread(coachThreadsRef.current, threadItem)
    delete deletedCoachAnswerBackupsRef.current[backup.deletedKey]
    coachAnswersRef.current = nextAnswers
    coachThreadsRef.current = nextThreads
    deletedSafetyAnswerKeysRef.current = nextDeleted
    setCoachAnswers(nextAnswers)
    setCoachThreads(nextThreads)
    setDeletedSafetyAnswerKeys(nextDeleted)
    setCoachErrors((prev) => ({ ...prev, [id]: '' }))
    setNotice('요청이 오래 걸려서 방금 삭제한 답변을 다시 보여드렸어요. 다시 생성하려면 잠시 뒤 한 번 더 시도해주세요.')
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: stage,
      clientSeq: seqRef.current,
      eventName: 'safety_coach_answer_timeout_restored',
      eventPayload: {
        stage,
        concept_id: id,
        concept_title: concept.title,
        question: normalizedQuestion,
        restored_from_deleted_key: backup.deletedKey,
      },
      stageDrafts: {
        [stage]: {
          safety_concept_feedback: conceptFeedbackRef.current,
          safety_coach_answers: nextAnswers,
          safety_coach_threads: nextThreads,
          safety_coach_answer_feedback: coachAnswerFeedbackRef.current,
          deferred_safety_questions: deferredSafetyQuestionsRef.current,
          deleted_safety_answer_keys: nextDeleted,
          stage_checked: checkedRef.current,
          last_position: lastPositionRef.current.anchorId
            ? {
                anchor_id: lastPositionRef.current.anchorId,
                captured_at: lastPositionRef.current.capturedAt || new Date().toISOString(),
              }
            : lastPositionRef.current,
        },
      },
    }).then((next) => setState(next)).catch((e) => {
      console.error('timeout restore sync failed', e)
    })
    return true
  }

  function rateCoachAnswer(
    concept: NonNullable<TrainingStage['foundation_concepts']>[number],
    id: string,
    item: SafetyCoachAnswers[string] | SafetyCoachThreadItem,
    rating: SafetyCoachAnswerRating,
  ) {
    if (!state || !item.answer) return
    const answerVersion = item.version || SAFETY_COACH_ANSWER_VERSION
    const key = safetyAnswerKey(id, answerVersion, item.question)
    const currentRating = coachAnswerFeedbackRef.current[key]?.rating
    if (currentRating === rating) {
      const nextFeedback = { ...coachAnswerFeedbackRef.current }
      delete nextFeedback[key]
      coachAnswerFeedbackRef.current = nextFeedback
      setCoachAnswerFeedback(nextFeedback)
      setNotice('피드백 선택을 취소했어요.')
      seqRef.current += 1
      void syncSession({
        caseId,
        email,
        selectedStage: stage,
        clientSeq: seqRef.current,
        eventName: 'safety_coach_answer_feedback_cleared',
        eventPayload: {
          stage,
          concept_id: id,
          concept_title: concept.title,
          question: item.question ?? '',
          answer_version: answerVersion,
          cleared_rating: rating,
        },
        stageDrafts: {
          [stage]: stageDraftForSync({ safety_coach_answer_feedback: nextFeedback }),
        },
      })
        .then((next) => setState(next))
        .catch((e) => {
          console.error('safety coach feedback clear sync failed', e)
          setCoachErrors((prev) => ({ ...prev, [id]: errMsg(e) }))
        })
      return
    }
    const savedAt = new Date().toISOString()
    const nextFeedback: SafetyCoachAnswerFeedback = {
      ...coachAnswerFeedbackRef.current,
      [key]: {
        rating,
        status: rating === 'down' ? 'queued' : 'saved',
        reviewedAt: savedAt,
      },
    }
    coachAnswerFeedbackRef.current = nextFeedback
    setCoachAnswerFeedback(nextFeedback)
    setNotice(rating === 'up' ? '좋아요를 반영했어요. 좋은 답변 패턴으로 보관합니다.' : '싫어요를 반영했어요. 백그라운드에서 답변을 정밀 분석합니다.')
    seqRef.current += 1
    void syncSession({
      caseId,
      email,
      selectedStage: stage,
      clientSeq: seqRef.current,
      eventName: 'safety_coach_answer_feedback_saved',
      eventPayload: {
        stage,
        concept_id: id,
        concept_title: concept.title,
        question: item.question ?? '',
        answer: item.answer,
        answer_version: answerVersion,
        rating,
      },
      stageDrafts: {
        [stage]: stageDraftForSync({ safety_coach_answer_feedback: nextFeedback }),
      },
    })
      .then((next) => setState(next))
      .catch((e) => {
        console.error('safety coach feedback sync failed', e)
        setCoachAnswerFeedback((prev) => {
          const fallback = { ...prev, [key]: { ...nextFeedback[key], status: 'error' as const } }
          coachAnswerFeedbackRef.current = fallback
          return fallback
        })
      })
    void rateSafetyCoachAnswer({
      caseId,
      email,
      stage,
      conceptId: id,
      conceptTitle: concept.title,
      conceptBody: concept.body,
      question: item.question ?? '',
      answer: item.answer,
      answerVersion,
      rating,
      model: item.model,
      fallbackUsed: item.fallbackUsed,
      evidenceUsed: item.evidenceUsed,
    }).catch((e) => {
      console.error('safety coach answer rating failed', e)
      setCoachAnswerFeedback((prev) => {
        const fallback = { ...prev, [key]: { ...nextFeedback[key], status: 'error' as const } }
        coachAnswerFeedbackRef.current = fallback
        return fallback
      })
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
        conceptBody: concept.body,
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
            safety_coach_answer_feedback: coachAnswerFeedbackRef.current,
            deferred_safety_questions: nextDeferred,
            deleted_safety_answer_keys: nextDeleted,
            stage_checked: checkedRef.current,
            last_position: lastPositionRef.current.anchorId
              ? {
                  anchor_id: lastPositionRef.current.anchorId,
                  captured_at: lastPositionRef.current.capturedAt || new Date().toISOString(),
                }
              : lastPositionRef.current,
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
        const guide = plannedCurriculumGuide(planned)
        const finalAnswer = guide && !res.answer.includes(guide) ? `${res.answer}\n\n${guide}` : res.answer
        const answerRecord = {
          answer: finalAnswer,
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
          conceptBody: concept.body,
          question,
          answer: finalAnswer,
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
            answer: finalAnswer,
            model: res.model,
            fallback_used: Boolean(res.fallback_used),
            answer_version: res.answer_version || SAFETY_COACH_ANSWER_VERSION,
            duplicate_reused: Boolean(res.duplicate_reused),
            evidence_used: res.evidence_used,
            planned_key: planned?.key,
            planned_title: planned?.title,
            planned_guide: guide,
          },
          stageDrafts: {
            [stage]: {
              safety_concept_feedback: latestFeedback,
              safety_coach_answers: nextAnswers,
              safety_coach_threads: nextThreads,
              safety_coach_answer_feedback: coachAnswerFeedbackRef.current,
              deferred_safety_questions: latestDeferred,
              deleted_safety_answer_keys: nextDeleted,
              stage_checked: checkedRef.current,
              last_position: lastPositionRef.current.anchorId
                ? {
                    anchor_id: lastPositionRef.current.anchorId,
                    captured_at: lastPositionRef.current.capturedAt || new Date().toISOString(),
                  }
                : lastPositionRef.current,
            },
          },
        })
      })
      .then((next) => {
        setState(next)
      })
      .catch((e) => {
        console.error('safety coach failed', e)
        if (e instanceof ApiError && e.status === 408 && restoreDeletedCoachAnswerAfterTimeout(concept, id, question)) return
        setCoachErrors((prev) => ({ ...prev, [id]: errMsg(e) }))
      })
      .finally(() => {
        setCoachLoading((prev) => ({ ...prev, [id]: false }))
      })
  }

  function confirmSafetyOrientation() {
    if (!state || safetySyncing) return
    const latestFeedback = conceptFeedbackRef.current
    const latestAnswers = coachAnswersRef.current
    const latestThreads = coachThreadsRef.current
    const latestDeferred = deferredSafetyQuestionsRef.current
    const latestDeleted = deletedSafetyAnswerKeysRef.current
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
          safety_coach_answer_feedback: coachAnswerFeedbackRef.current,
          deferred_safety_questions: latestDeferred,
          deleted_safety_answer_keys: latestDeleted,
          safety_concept_confirmed_ids: confirmedConceptIds,
          stage_checked: checkedRef.current,
          last_position: lastPositionRef.current.anchorId
            ? {
                anchor_id: lastPositionRef.current.anchorId,
                captured_at: lastPositionRef.current.capturedAt || new Date().toISOString(),
              }
            : lastPositionRef.current,
        },
      },
    })
      .then((next) => {
        setState(next)
        setSafetyReady(Boolean(next.ui_state?.safety_confirmed?.[stage] || next[stage]?.completed))
        if (stage === 'day0' && next.day0?.completed) {
          hydrateStageInputs(next, 'day1')
          setNotice('Day 0 완료! Day 1 실습으로 이동했어요.')
        }
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
      <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6 lg:max-w-[960px] xl:max-w-[1120px] xl:px-8">
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
      <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6 lg:max-w-[960px] xl:max-w-[1120px] xl:px-8">
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
  const stageOrder = stageOrderFromState(state)
  const items = stageChecklist(current)
  const doneCount = items.filter((it) => checked[it.id]).length
  const allChecked = items.length === 0 || doneCount === items.length
  const currentStagePct = stageProgressPct(state, stage)
  const learnerName = String(state?.customer?.name || '오늘의 학습자')
  const personalizedCurriculum =
    stage === 'day0' && state?.personalized_curriculum?.available ? state.personalized_curriculum : null
  const dynamicPath = stage === 'day0' ? state?.dynamic_curriculum_path ?? [] : []
  const plannedOutline = stage === 'day0' ? state?.planned_curriculum_outline ?? [] : []
  const safetyGateActive = stage === 'day0' && !safetyReady && !current?.completed
  const showSafetyRecords = stage === 'day0' && !safetyGateActive && Boolean(current?.foundation_concepts?.length)

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6 lg:max-w-[960px] xl:max-w-[1120px] xl:px-8">
      {header}

      {questionArchiveOpen ? (
        <QuestionArchivePanel groups={questionGroups} deferred={deferredQuestions} onClose={() => setQuestionArchiveOpen(false)} />
      ) : null}

      <div className={questionArchiveOpen ? 'hidden print:hidden' : ''}>
      {/* 현재 단계 진행률 */}
      <div className="mb-4 flex items-center gap-2.5">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
          <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${currentStagePct}%` }} />
        </div>
        <span className="w-9 shrink-0 text-right text-xs font-semibold tabular-nums text-text-muted">
          {currentStagePct}%
        </span>
      </div>

      {/* 단계 탭 */}
      <div className="mb-5 grid grid-cols-2 gap-1 rounded-[12px] bg-secondary p-1 sm:grid-cols-4">
        {stageOrder.map((k) => {
          const locked = !stageIsUnlocked(state, k)
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
              {stageLabel(k)}
            </button>
          )
        })}
      </div>

      {/* 단계 본문 */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-base font-bold leading-snug text-ink-strong">
              {String(current?.title ?? stageLabel(stage))}
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
            coachFeedback={coachAnswerFeedback}
            coachLoading={coachLoading}
            coachErrors={coachErrors}
            saving={safetySyncing}
            error={error}
            notice={notice}
            routedConceptId={routedConceptId}
            onToggle={toggleCheck}
            onConceptFeedback={updateConceptFeedback}
            onAskCoach={requestCoachAnswer}
            onRateCoachAnswer={rateCoachAnswer}
            onDeleteCoachAnswer={deleteCoachAnswer}
            onReady={confirmSafetyOrientation}
          />
        ) : null}

        {showSafetyRecords && current ? (
          <SafetyOrientationBlock
            stage={current}
            checked={checked}
            conceptFeedback={conceptFeedback}
            coachAnswers={coachAnswers}
            coachThreads={coachThreads}
            coachFeedback={coachAnswerFeedback}
            coachLoading={coachLoading}
            coachErrors={coachErrors}
            saving={safetySyncing}
            error={error}
            notice={notice}
            routedConceptId={routedConceptId}
            onToggle={toggleCheck}
            onConceptFeedback={updateConceptFeedback}
            onAskCoach={requestCoachAnswer}
            onRateCoachAnswer={rateCoachAnswer}
            onDeleteCoachAnswer={deleteCoachAnswer}
            onReady={confirmSafetyOrientation}
            reviewMode
          />
        ) : null}

        {!safetyGateActive && personalizedCurriculum ? (
          <PersonalizedDay0Block curriculum={personalizedCurriculum} learnerName={learnerName} />
        ) : null}

        {stage === 'day0' && plannedOutline.length ? (
          <PlannedCurriculumPreview items={plannedOutline} />
        ) : null}

        {stage === 'day0' && state?.day1 ? (
          <StageDetailPreview stage={state.day1} />
        ) : null}

        {stage !== 'day0' && current ? (
          <StageConceptBlock
            stage={current}
            checked={checked}
            conceptFeedback={conceptFeedback}
            coachAnswers={coachAnswers}
            coachFeedback={coachAnswerFeedback}
            coachLoading={coachLoading}
            coachErrors={coachErrors}
            onToggle={toggleCheck}
            onConceptFeedback={updateConceptFeedback}
            onAskCoach={requestCoachAnswer}
            onRateCoachAnswer={rateCoachAnswer}
            onDeleteCoachAnswer={deleteCoachAnswer}
          />
        ) : null}

        {stage !== 'day0' && current ? (
          <Day1PracticeLab stage={current} />
        ) : null}

        {stage !== 'day0' && current ? (
          <StageDetailPreview stage={current} active />
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
                      id={`check-card-${it.id}`}
                      data-training-anchor="true"
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
