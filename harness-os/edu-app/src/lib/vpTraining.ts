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

/** 새 훈련 케이스 시작(intake force_new). 인테이크 상세값은 추후 화면에서 수집. */
export async function startNewCase(email: string, name: string): Promise<void> {
  await vpPost(VP_TRAINING.intake, {
    email,
    name,
    preferred_llm: 'claude',
    current_device: 'iphone',
    desktop_os: 'mac',
    ai_experience: 'beginner',
    biggest_friction: '',
    learning_goal: '',
    force_new: true,
  })
}

/** 케이스를 완전 삭제(되돌릴 수 없음). 백엔드에서 edu_cases 행을 DELETE 한다. */
export async function deleteCase(email: string, caseId: number): Promise<void> {
  await vpPost(VP_TRAINING.casesDelete, { email, case_id: caseId })
}

/* ── 훈련 세션(단계 흐름) ──────────────────────────────────────────────
 * 형태의 단일 출처는 백엔드 _edu_vp_build_day0/day1 + _edu_vp_refresh_state.
 * 콘솔(EduVpTrainingPage.tsx)이 동일 training_state 를 소비한다. */

export type StageKey = 'day0' | 'day1'

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
  required_action?: string
  proof_artifact_hint?: string
  pass_fail_rubric?: string[]
  checklist?: ChecklistItem[]
  proof_artifact?: string
  notes?: string
  completed?: boolean
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

export type TrainingUiState = {
  selected_stage?: StageKey
  active_curriculum_index?: number
  last_client_seq?: number
}

export type TrainingState = {
  case?: { id?: number; case_label?: string } & Record<string, unknown>
  day0?: TrainingStage
  day1?: TrainingStage
  flow_outline?: FlowOutlineItem[]
  progress?: TrainingProgress
  ui_state?: TrainingUiState
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
  clientSeq: number
  eventName?: string
  eventPayload?: Record<string, unknown>
}): Promise<TrainingState> {
  const r = await vpPost<{ training_state: TrainingState }>(VP_TRAINING.sessionSync, {
    case_id: input.caseId,
    email: input.email,
    selected_stage: input.selectedStage,
    active_curriculum_index: input.activeCurriculumIndex ?? 0,
    client_seq: input.clientSeq,
    event_type: 'ui_sync',
    event_name: input.eventName ?? 'state_sync',
    event_payload: input.eventPayload ?? {},
  })
  return r.training_state
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
}

export type CurriculumOrderItem = { topic: string; weight: number }
export type CurriculumOverlayItem = { model: string; freshness: number }
export type CurriculumConcern = { concern: string; count: number }
export type CurriculumHighlight = {
  title: string
  days_ago: number
  models: string[]
  concern: string
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
  segment: string | null
  base_pool: string
  order: CurriculumOrderItem[]
  overlay: CurriculumOverlayItem[]
  top_concerns: CurriculumConcern[]
  highlights: CurriculumHighlight[]
  fresh_note: CurriculumFreshNote
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
  })
}
