import { VP_TRAINING, vpGet, vpPost } from './api'
import type { Session } from './session'

/** 케이스 선택 화면이 쓰는 케이스 요약. (백엔드 /cases 응답) */
export type TrainingCase = {
  case_id: number
  status: string
  updated_at: string
  progress_pct: number
  case_label: string
  has_training_state: boolean
  flow_outline?: Array<Record<string, unknown>>
}

type AccountResponse = {
  ok: boolean
  customer_id: number
  email: string
  name?: string
  training_auth_token: string
}

export async function loginAccount(email: string, password: string): Promise<Session> {
  const r = await vpPost<AccountResponse>(VP_TRAINING.accountLogin, { email, password })
  return {
    customerId: r.customer_id,
    email: r.email,
    name: r.name ?? '',
    token: r.training_auth_token,
  }
}

export async function registerAccount(
  name: string,
  email: string,
  password: string,
): Promise<Session> {
  const r = await vpPost<AccountResponse>(VP_TRAINING.accountRegister, { name, email, password })
  // register 응답엔 name 이 없으므로 입력값을 사용한다.
  return {
    customerId: r.customer_id,
    email: r.email,
    name: name || r.name || '',
    token: r.training_auth_token,
  }
}

export async function listCases(email: string): Promise<TrainingCase[]> {
  const r = await vpGet<{ ok: boolean; cases: TrainingCase[] }>(VP_TRAINING.cases, { email })
  return r.cases ?? []
}

const CURRICULUM_ATTRS_STORAGE_KEY = 'vp_curriculum_attrs'
const START_NEW_CASE_TIMEOUT_MS = 45_000

const DEFAULT_CURRICULUM_ATTRS: CurriculumAttrs = {
  llm: 'chatgpt',
  level: 'beginner',
  motivation: 'work',
  env: 'mobile',
  job: '학부모',
  learning_goal: '',
  biggest_friction: '',
  media_preference: 'mixed',
}

export function loadSavedCurriculumAttrs(): CurriculumAttrs {
  try {
    const raw = localStorage.getItem(CURRICULUM_ATTRS_STORAGE_KEY)
    if (raw) return { ...DEFAULT_CURRICULUM_ATTRS, ...(JSON.parse(raw) as CurriculumAttrs) }
  } catch {
    /* ignore */
  }
  return DEFAULT_CURRICULUM_ATTRS
}

function intakeLlm(attrs: CurriculumAttrs): string {
  const v = String(attrs.llm || '').toLowerCase()
  if (v.includes('gemini') || v.includes('제미나이')) return 'gemini'
  if (v.includes('claude') || v.includes('클로드')) return 'claude'
  if (v.includes('gpt') || v.includes('chatgpt') || v.includes('챗')) return 'gpt'
  if (v.includes('genspark') || v.includes('젠스파크')) return 'genspark'
  if (v.includes('grok') || v.includes('그록')) return 'grok'
  if (v.includes('perplexity') || v.includes('퍼플렉시티')) return 'perplexity'
  return 'auto'
}

function intakeSegment(attrs: CurriculumAttrs): 'parent' | 'worker' {
  const job = String(attrs.job || '').toLowerCase()
  return job.includes('학부모') || job.includes('parent') || job.includes('주부') ? 'parent' : 'worker'
}

function intakeDevice(attrs: CurriculumAttrs): string {
  return attrs.env === 'pc' ? 'mac' : 'mobile'
}

function intakeGoal(attrs: CurriculumAttrs): string {
  const custom = String(attrs.learning_goal || '').trim()
  if (custom) return custom
  if (attrs.motivation === 'child_study') return '아이 공부와 숙제에 AI를 안전하게 활용하기'
  if (attrs.motivation === 'writing') return '글쓰기와 문장 정리에 AI를 활용하기'
  if (attrs.motivation === 'daily') return '일상 일정과 생활 정리에 AI를 활용하기'
  return '업무와 반복 작업에 AI를 활용하기'
}

function intakeFriction(attrs: CurriculumAttrs): string {
  const custom = String(attrs.biggest_friction || '').trim()
  if (custom) return custom
  const llmValue = intakeLlm(attrs)
  const llm =
    llmValue === 'gemini'
      ? 'Gemini'
      : llmValue === 'claude'
        ? 'Claude'
        : llmValue === 'genspark'
          ? 'Genspark'
          : llmValue === 'grok'
            ? 'Grok'
            : llmValue === 'perplexity'
              ? 'Perplexity'
              : 'ChatGPT'
  if (attrs.motivation === 'child_study') return `${llm}로 아이 숙제와 학습을 어디까지 도와도 되는지 막막함`
  if (attrs.motivation === 'writing') return `${llm}로 글 초안을 어떻게 시작해야 할지 막막함`
  if (attrs.motivation === 'daily') return `${llm}로 생활 메모와 일정을 어떻게 정리할지 막막함`
  return `${llm} 업무 활용을 어디서부터 시작해야 할지 막막함`
}

function curriculumAttrsToIntake(email: string, name: string, attrs: CurriculumAttrs, caseId?: number) {
  return {
    case_id: caseId,
    email,
    name,
    preferred_llm: intakeLlm(attrs),
    segment: intakeSegment(attrs),
    current_device: intakeDevice(attrs),
    desktop_os: 'mac',
    ai_experience: attrs.level || 'beginner',
    motivation: attrs.motivation || 'work',
    biggest_friction: intakeFriction(attrs),
    learning_goal: intakeGoal(attrs),
    media_preference: attrs.media_preference || 'mixed',
  }
}

/** 새 훈련 케이스 시작(intake force_new). 맞춤 커리큘럼 선택값을 intake 에 주입한다. */
export async function startNewCase(email: string, name: string): Promise<number | null> {
  const attrs = loadSavedCurriculumAttrs()
  const r = await vpPost<{ ok: boolean; case_id?: number }>(VP_TRAINING.intake, {
    ...curriculumAttrsToIntake(email, name, attrs),
    force_new: true,
  }, START_NEW_CASE_TIMEOUT_MS)
  return typeof r.case_id === 'number' ? r.case_id : null
}

/** 케이스를 완전 삭제(되돌릴 수 없음). 백엔드에서 edu_cases 행을 DELETE 한다. */
export async function deleteCase(email: string, caseId: number): Promise<void> {
  await vpPost(VP_TRAINING.casesDelete, { email, case_id: caseId })
}

/* ── 훈련 세션(단계 흐름) ──────────────────────────────────────────────
 * 형태의 단일 출처는 백엔드 _edu_vp_build_day0/day1 + _edu_vp_refresh_state.
 * 콘솔(EduVpTrainingPage.tsx)이 동일 training_state 를 소비한다. */

export type StageKey = `day${number}`

export type ChecklistItem = {
  id: string
  title: string
  instruction?: string
  success_signal?: string
}

export type TrainingStage = {
  title?: string
  learning_why?: string
  learning_outcome?: string
  estimated_minutes?: number
  completion_rule?: string
  foundation_concepts?: Array<{
    id?: string
    title: string
    body: string
    comprehension_check?: string
    question_prompt?: string
  }>
  schedule_blocks?: Array<{ title: string; minutes?: number; goal?: string }>
  sample_materials?: Array<{ kit_id?: string; title: string; description?: string; files?: string[] }>
  tutorial_steps?: Array<{ id?: string; title: string; body?: string; instruction?: string }>
  practice_lab?: {
    version?: string
    headline?: string
    visual_assets?: Array<{ src: string; alt?: string; caption?: string }>
    install_guide?: {
      title?: string
      intro?: string
      steps?: string[]
      fallback?: string
      image_src?: string
      image_alt?: string
      tool_options?: string[]
      selected_tool?: string
    }
    tool_cards?: Array<{ title: string; body?: string; action?: string; visual?: string; image_src?: string; image_alt?: string }>
    practice_table?: Array<{ step: string; in_app?: string; outside_app?: string }>
    prompt_template?: string
    verification_rows?: Array<{ item: string; source?: string; ai_check?: string }>
    result_slots?: string[]
    context_hint?: string
  }
  practice_lab_version?: string
  practice_prompt_template?: string
  required_action?: string
  proof_artifact_hint?: string
  pass_fail_rubric?: string[]
  evidence_cards?: Array<{ title: string; source_kind?: string; cite?: string; snippet?: string; url?: string }>
  retrieval_mode?: string
  customer_facing_safe?: boolean
  fallback_used?: boolean
  checklist?: ChecklistItem[]
  proof_artifact?: string
  notes?: string
  completed?: boolean
  completed_at?: string
  saved_at?: string
  safety_confirmed?: boolean
}

export type FlowOutlineItem = {
  key: StageKey
  label: string
  title: string
  completed: boolean
  pct: number
}

export type TrainingProgress = {
  completed_stages: number
  total_stages: number
  pct: number
}

export type DynamicCurriculumItem = {
  key: string
  day: number
  title: string
  topic: string
  concern: string
  highlight: string
  model_signal: string
  role: string
  llm: string
  depth: number
  mission: string
}

export type AdaptiveCurriculumModule = {
  module: number
  title: string
  topic: string
  start_day: number
  end_day: number
  lesson_count: number
  concerns: string[]
  sample_missions: string[]
  outcome: string
}

export type AdaptiveCurriculumMeta = {
  target_length: number
  active_length: number
  skipped_count: number
  modules?: AdaptiveCurriculumModule[]
  skipped_items_sample?: { candidate: string; reason: string }[]
  basis?: Record<string, unknown>
}

export type PlannedCurriculumItem = {
  key: string
  day: number
  title: string
  focus: string
  outcome: string
  status: 'active' | 'detailed_ready' | 'rough_planned' | string
}

export type TrainingUiState = {
  selected_stage?: StageKey
  active_curriculum_index?: number
  preferred_llm?: string
  safety_confirmed?: Record<string, boolean>
  stage_drafts?: Record<string, Record<string, unknown>>
  active_training_device_id?: string
  active_training_device_type?: string
  active_training_case_id?: number
  active_training_stage?: StageKey
  active_training_anchor_id?: string
  show_continue_from?: StageKey | string
  device_claimed_at?: string
  last_client_seq?: number
}

export type TrainingState = Partial<Record<StageKey, TrainingStage>> & {
  case?: { id?: number; case_label?: string } & Record<string, unknown>
  customer?: { name?: string; segment?: string; preferred_llm?: string } & Record<string, unknown>
  intake?: Record<string, string>
  day0?: TrainingStage
  day1?: TrainingStage
  flow_outline?: FlowOutlineItem[]
  progress?: TrainingProgress
  ui_state?: TrainingUiState
  dynamic_curriculum_path?: DynamicCurriculumItem[]
  adaptive_curriculum_meta?: AdaptiveCurriculumMeta
  planned_curriculum_outline?: PlannedCurriculumItem[]
  personalized_curriculum?: PersonalizedCurriculum
}

export type SessionResult =
  | { exists: false; caseId: number }
  | { exists: true; caseId: number; state: TrainingState }

type SessionResponse = {
  ok: boolean
  exists?: boolean
  case_id?: number
  training_state?: TrainingState
}

/** 케이스의 훈련 세션을 불러온다. 데이터가 없으면 exists:false. */
export async function fetchSession(email: string, caseId: number): Promise<SessionResult> {
  const r = await vpGet<SessionResponse>(VP_TRAINING.session, { email, case_id: caseId })
  if (!r.exists || !r.training_state) return { exists: false, caseId: r.case_id ?? caseId }
  return { exists: true, caseId: r.case_id ?? caseId, state: r.training_state }
}

/** 네비게이션 상태(선택 단계 등)를 서버에 sync. client_seq 로 stale 갱신을 막는다. */
export async function syncSession(input: {
  caseId: number
  email: string
  selectedStage: StageKey
  activeCurriculumIndex?: number
  preferredLlm?: string
  stageDrafts?: Record<string, Record<string, unknown>>
  clientSeq: number
  eventName?: string
  eventPayload?: Record<string, unknown>
}): Promise<TrainingState> {
  const r = await vpPost<{ training_state: TrainingState }>(VP_TRAINING.sessionSync, {
    case_id: input.caseId,
    email: input.email,
    selected_stage: input.selectedStage,
    active_curriculum_index: input.activeCurriculumIndex ?? 0,
    preferred_llm: input.preferredLlm ?? '',
    stage_drafts: input.stageDrafts ?? {},
    client_seq: input.clientSeq,
    event_type: 'ui_sync',
    event_name: input.eventName ?? 'state_sync',
    event_payload: input.eventPayload ?? {},
  })
  return r.training_state
}

export type SafetyCoachResponse = {
  answer: string
  model?: string
  fallback_used?: boolean
  answer_version?: string
  duplicate_reused?: boolean
  evidence_used?: boolean
}

export type SafetyRouteResponse = {
  ok: boolean
  target_concept_id?: string
  planned_key?: string
  confidence?: number
  reason?: string
  model?: string
  provider?: string
}

export async function routeSafetyQuestion(input: {
  caseId: number
  email: string
  stage: StageKey
  sourceConceptId: string
  question: string
  concepts: Array<{
    id?: string
    title: string
    body: string
    comprehension_check?: string
    question_prompt?: string
  }>
  plannedOutline?: PlannedCurriculumItem[]
}): Promise<SafetyRouteResponse> {
  return vpPost<SafetyRouteResponse>(VP_TRAINING.safetyRoute, {
    case_id: input.caseId,
    email: input.email,
    stage: input.stage,
    source_concept_id: input.sourceConceptId,
    question: input.question,
    concepts: input.concepts,
    planned_outline: input.plannedOutline ?? [],
  }, 1200)
}

export async function askSafetyCoach(input: {
  caseId: number
  email: string
  stage: StageKey
  conceptId: string
  conceptTitle: string
  conceptBody: string
  question: string
  answerVersion: string
  preferredLlm?: string
}): Promise<SafetyCoachResponse> {
  return vpPost<SafetyCoachResponse>(VP_TRAINING.safetyCoach, {
    case_id: input.caseId,
    email: input.email,
    stage: input.stage,
    concept_id: input.conceptId,
    concept_title: input.conceptTitle,
    concept_body: input.conceptBody,
    question: input.question,
    answer_version: input.answerVersion,
    preferred_llm: input.preferredLlm ?? '',
  }, 30_000)
}

export async function rateSafetyCoachAnswer(input: {
  caseId: number
  email: string
  stage: StageKey
  conceptId: string
  conceptTitle: string
  conceptBody: string
  question: string
  answer: string
  answerVersion: string
  rating: 'up' | 'down'
  model?: string
  fallbackUsed?: boolean
  evidenceUsed?: boolean
}): Promise<{ ok: boolean; rating: 'up' | 'down'; auto_reinforcement_status?: string }> {
  return vpPost<{ ok: boolean; rating: 'up' | 'down'; auto_reinforcement_status?: string }>(VP_TRAINING.safetyCoachFeedback, {
    case_id: input.caseId,
    email: input.email,
    stage: input.stage,
    concept_id: input.conceptId,
    concept_title: input.conceptTitle,
    concept_body: input.conceptBody,
    question: input.question,
    answer: input.answer,
    answer_version: input.answerVersion,
    rating: input.rating,
    model: input.model ?? '',
    fallback_used: Boolean(input.fallbackUsed),
    evidence_used: Boolean(input.evidenceUsed),
  })
}

/** 단계 완료/증거물 커밋. day0 completed=true 면 day1 이 해금된다. */
export async function saveStageArtifact(input: {
  caseId: number
  stage: StageKey
  proofArtifact: string
  notes?: string
  blockedAtStep?: string
  completed: boolean
}): Promise<TrainingState> {
  const r = await vpPost<{ training_state: TrainingState }>(VP_TRAINING.artifact, {
    case_id: input.caseId,
    stage: input.stage,
    proof_artifact: input.proofArtifact,
    blocked_at_step: input.blockedAtStep ?? '',
    notes: input.notes ?? '',
    completed: input.completed,
  })
  return r.training_state
}

// ── 개인화 커리큘럼 ──────────────────────────────────────────────
export type CurriculumAttrs = {
  llm?: string
  level?: '' | 'beginner' | 'intermediate' | 'advanced'
  motivation?: '' | 'work' | 'child_study' | 'daily' | 'writing'
  env?: '' | 'mobile' | 'pc' | 'voice'
  job?: string
  learning_goal?: string
  biggest_friction?: string
  media_preference?: '' | 'text' | 'video' | 'visual' | 'mixed'
}

export type CurriculumOrderItem = { topic: string; weight: number }
export type CurriculumOverlayItem = { model: string; freshness: number }
export type CurriculumConcern = { concern: string; count: number }
export type CurriculumHighlight = {
  title: string
  generated_title?: string
  original_title?: string
  language?: string
  days_ago: number
  models: string[]
  concern: string
  source?: string
  url?: string
  relevance_score?: number
  relevance_reasons?: string[]
  trust_status?: 'trusted' | 'quarantined' | string
  trust_score?: number
  trust_reasons?: string[]
  refined_id?: number
  body?: string
  script_text?: string
  script_label?: string
  excerpt?: string
  media_kind?: 'video' | 'paper' | 'article' | 'reference' | string
}
export type CurriculumFreshNote = {
  pool_total: number
  recent_30d: number
  newest_days_ago: number | null
}

export type PersonalizedCurriculum = {
  ok: boolean
  available: boolean
  total_evidence?: number
  attrs?: CurriculumAttrs
  source?: string
  segment: string | null
  base_pool: string
  order: CurriculumOrderItem[]
  overlay: CurriculumOverlayItem[]
  top_concerns: CurriculumConcern[]
  highlights: CurriculumHighlight[]
  fresh_note: CurriculumFreshNote
  user_intent?: {
    learning_goal?: string
    biggest_friction?: string
    media_preference?: string
  }
}

/** 요청 시점에 evidence 풀을 속성으로 재편한 커리큘럼을 받는다(파이프라인 무재실행). */
export async function fetchPersonalizedCurriculum(
  email: string,
  attrs: CurriculumAttrs,
): Promise<PersonalizedCurriculum> {
  return vpPost<PersonalizedCurriculum>(VP_TRAINING.curriculum, {
    email,
    llm: attrs.llm ?? '',
    level: attrs.level ?? '',
    motivation: attrs.motivation ?? '',
    env: attrs.env ?? '',
    job: attrs.job ?? '',
    learning_goal: attrs.learning_goal ?? '',
    biggest_friction: attrs.biggest_friction ?? '',
    media_preference: attrs.media_preference ?? 'mixed',
  })
}
