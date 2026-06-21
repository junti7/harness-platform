import { useEffect, useRef, useState } from 'react'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  currentRole?: 'ceo' | 'vp'
}

type MaterialKit = {
  kit_id: string
  title: string
  description: string
  files: string[]
  download_url: string
}

type TutorialStep = {
  id: string
  title: string
  body: string
}

type StageKey = 'day0' | 'day1'

type LearningLink = {
  title: string
  url: string
  source_kind: string
}

type TrainingStage = {
  title?: string
  learning_why?: string
  learning_outcome?: string
  estimated_minutes?: number
  completion_rule?: string
  foundation_concepts?: Array<{ title: string; body: string }>
  schedule_blocks?: Array<{ title: string; minutes: number; goal: string }>
  required_action?: string
  proof_artifact_hint?: string
  pass_fail_rubric?: string[]
  home_priority_missions?: Array<{ title: string; why: string; use_when: string; result_shape: string }>
  scenario_bank?: Array<{ title: string; situation: string; prompt: string }>
  sample_materials?: MaterialKit[]
  blocked_step_options?: string[]
  checklist?: Array<{ id: string; title: string; instruction: string; success_signal: string }>
  tutorial_steps?: TutorialStep[]
  practice_prompt_template?: string
  recommended_learning?: LearningLink[]
  home_life_recommended_learning?: LearningLink[]
  evidence_bundle_id?: string
  retrieval_mode?: string
  customer_facing_safe?: boolean
  fallback_used?: boolean
  external_reuse_safe?: boolean
  evidence_cards?: Array<{ title: string; source_kind: string; cite: string; snippet: string; url?: string }>
  proof_artifact?: string
  blocked_at_step?: string
  notes?: string
  completed?: boolean
  vp_feedback?: {
    empathy_score?: number
    clarity_score?: number
    motivation_score?: number
    biggest_blocker?: string
    freeform_feedback?: string
    submitted_at?: string
  }
}

type FlowItem = {
  key: StageKey
  label: string
  title: string
  completed: boolean
  pct: number
}

type UiStageDraft = {
  proof_artifact?: string
  blocked_at_step?: string
  notes?: string
  completed?: boolean
  empathy_score?: number
  clarity_score?: number
  motivation_score?: number
  biggest_blocker?: string
  freeform_feedback?: string
}

type UiState = {
  selected_stage?: StageKey
  active_curriculum_index?: number
  show_case_archive?: boolean
  show_continue_from?: StageKey | ''
  preferred_llm?: string
  current_device?: string
  desktop_os?: string
  stage_drafts?: Partial<Record<StageKey, UiStageDraft>>
  last_client_seq?: number
  last_event?: Record<string, unknown>
  last_synced_at?: string
}

type TrainingState = {
  program_objective?: string
  primary_llm_path?: string
  active_persona?: string
  intake?: Record<string, string>
  progress?: { completed_stages: number; total_stages: number; pct: number }
  persona_library?: {
    core_persona: string
    core_label: string
    unlocked: boolean
    unlock_rule: string
    personas: Array<{ key: string; label: string; group: string; description: string }>
  }
  flow_outline?: FlowItem[]
  ui_state?: UiState
  day0?: TrainingStage
  day1?: TrainingStage
}

type CaseItem = {
  case_id: number
  status?: string
  updated_at?: string
  progress_pct: number
  case_label?: string
  flow_outline?: FlowItem[]
  has_training_state?: boolean
}

const VP_TRAINING_CASE_STORAGE_KEY = 'vp_training_case_id'
const VP_TRAINING_AUTH_EMAIL_KEY = 'vp_training_auth_email'
const VP_TRAINING_AUTH_TOKEN_KEY = 'vp_training_auth_token'
const VP_TRAINING_SESSION_CACHE_KEY = 'vp_training_session_cache'

function roleDefaultEmail(role?: 'ceo' | 'vp') {
  if (role === 'ceo') return 'junti7@gmail.com'
  if (role === 'vp') return 'fox_jazz@naver.com'
  return ''
}

function resolveTrainingEmail(role?: 'ceo' | 'vp') {
  if (!role) return ''
  try {
    const raw = window.localStorage.getItem(`harness-settings-${role}`)
    if (raw) {
      const parsed = JSON.parse(raw) as { email?: string }
      const savedEmail = String(parsed?.email || '').trim().toLowerCase()
      if (savedEmail) return savedEmail
    }
  } catch {
    // ignore parse failure and use default
  }
  return roleDefaultEmail(role)
}

function caseStorageKey(email: string) {
  return `${VP_TRAINING_CASE_STORAGE_KEY}:${email}`
}

function sessionCacheKey(email: string) {
  return `${VP_TRAINING_SESSION_CACHE_KEY}:${email}`
}

function displayStageTitle(title?: string) {
  return String(title || '').replace(/^Day\s+\d+\s*[·.]\s*/i, '').trim() || '준비 중'
}

function lessonLabel(stageKey: StageKey) {
  return stageKey === 'day0' ? '첫날 수업' : '이번 수업'
}

function curriculumBlockId(stageKey: StageKey, index: number) {
  return `${stageKey}-curriculum-${index}`
}

function curriculumDetailBlockId(stageKey: StageKey, index: number) {
  return `${stageKey}-curriculum-detail-${index}`
}

function curriculumNavId(stageKey: StageKey, index: number) {
  return `${stageKey}-curriculum-nav-${index}`
}

function scrollCurriculumNavItemIntoView(stageKey: StageKey, index: number) {
  const item = document.getElementById(curriculumNavId(stageKey, index))
  const container = item?.parentElement
  if (!item || !container || container.scrollHeight <= container.clientHeight) return
  const nextTop = item.offsetTop - container.clientHeight / 2 + item.clientHeight / 2
  container.scrollTo({ top: Math.max(0, nextTop), behavior: 'smooth' })
}

function scrollCurriculumBlockToTop(stageKey: StageKey, index: number) {
  const target = document.getElementById(curriculumDetailBlockId(stageKey, index))
    || document.getElementById(curriculumBlockId(stageKey, index))
  if (!target) return
  const offset = 24
  let parent = target.parentElement
  while (parent && parent !== document.body) {
    const style = window.getComputedStyle(parent)
    const canScroll = /(auto|scroll)/.test(`${style.overflowY}${style.overflow}`) && parent.scrollHeight > parent.clientHeight
    if (canScroll) {
      const parentRect = parent.getBoundingClientRect()
      const targetRect = target.getBoundingClientRect()
      parent.scrollTo({ top: parent.scrollTop + targetRect.top - parentRect.top - offset, behavior: 'smooth' })
      return
    }
    parent = parent.parentElement
  }
  const targetTop = target.getBoundingClientRect().top + window.scrollY - offset
  window.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' })
}

async function readJsonSafe(res: Response) {
  const raw = await res.text()
  let data: Record<string, unknown> = {}
  if (raw) {
    try {
      data = JSON.parse(raw) as Record<string, unknown>
    } catch {
      data = {}
    }
  }
  return { raw, data }
}

const C = {
  ink: '#111827',
  muted: '#475569',
  faint: '#64748b',
  accent: '#0f766e',
  accentSoft: '#ccfbf1',
  surface: '#ffffff',
  border: '#dbe4ee',
  bg: '#f8fafc',
  warn: '#d97706',
  warnSoft: '#fff7ed',
  progress: '#111827',
}

function TrainingHeroVisual() {
  return (
    <svg viewBox="0 0 520 240" style={{ width: '100%', height: 'auto', display: 'block' }} aria-hidden="true">
      <rect x="0" y="0" width="520" height="240" rx="28" fill="#f8fafc" />
      <circle cx="80" cy="58" r="26" fill="#ccfbf1" />
      <circle cx="420" cy="52" r="22" fill="#fde68a" />
      <rect x="40" y="92" width="138" height="96" rx="18" fill="#ffffff" stroke="#dbe4ee" strokeWidth="2" />
      <rect x="58" y="108" width="102" height="54" rx="10" fill="#e0f2fe" />
      <rect x="69" y="118" width="56" height="8" rx="4" fill="#0f766e" />
      <rect x="69" y="133" width="72" height="7" rx="3.5" fill="#64748b" />
      <rect x="69" y="146" width="48" height="7" rx="3.5" fill="#64748b" />
      <rect x="210" y="58" width="210" height="132" rx="20" fill="#ffffff" stroke="#dbe4ee" strokeWidth="2" />
      <rect x="232" y="80" width="166" height="20" rx="10" fill="#111827" opacity="0.08" />
      <rect x="232" y="112" width="118" height="14" rx="7" fill="#0f766e" opacity="0.88" />
      <rect x="232" y="134" width="150" height="12" rx="6" fill="#94a3b8" />
      <rect x="232" y="154" width="110" height="12" rx="6" fill="#94a3b8" />
      <path d="M178 138 C205 126, 213 116, 226 102" stroke="#0f766e" strokeWidth="6" fill="none" strokeLinecap="round" />
      <circle cx="226" cy="102" r="7" fill="#0f766e" />
      <text x="56" y="203" fill="#111827" fontSize="14" fontWeight="700">Mobile first</text>
      <text x="232" y="210" fill="#111827" fontSize="14" fontWeight="700">PC / Mac handoff</text>
    </svg>
  )
}

function progressBar(pct: number) {
  return (
    <div style={{ width: '100%', height: 10, background: '#e5e7eb', borderRadius: 999 }}>
      <div style={{ width: `${pct}%`, height: 10, background: C.progress, borderRadius: 999, transition: 'width 200ms ease' }} />
    </div>
  )
}

function normalizeTrainingState(raw: TrainingState | Record<string, unknown> | null | undefined): TrainingState | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const normalized: TrainingState = {
    ...source as TrainingState,
    day0: (source.day0 as TrainingStage | undefined) || (source.week0 as TrainingStage | undefined),
    day1: (source.day1 as TrainingStage | undefined) || (source.week1 as TrainingStage | undefined),
  }
  const uiStateRaw = (source.ui_state as UiState | undefined) || undefined
  if (uiStateRaw) {
    const nextUiState: UiState = { ...uiStateRaw }
    if (nextUiState.selected_stage === 'week0' as never) nextUiState.selected_stage = 'day0'
    if (nextUiState.selected_stage === 'week1' as never) nextUiState.selected_stage = 'day1'
    if (nextUiState.show_continue_from === 'week0' as never) nextUiState.show_continue_from = 'day0'
    if (nextUiState.show_continue_from === 'week1' as never) nextUiState.show_continue_from = 'day1'
    const drafts = nextUiState.stage_drafts || {}
    nextUiState.stage_drafts = {
      day0: drafts.day0 || (drafts as Record<string, UiStageDraft>).week0,
      day1: drafts.day1 || (drafts as Record<string, UiStageDraft>).week1,
    }
    normalized.ui_state = nextUiState
  }
  normalized.flow_outline = (normalized.flow_outline || []).map((item) => ({
    ...item,
    key: item.key === ('week1' as never) ? 'day1' : 'day0',
  }))
  return normalized
}

function curriculumActiveIndex(stageKey: StageKey, blockedAtStep?: string, completed?: boolean, blockCount?: number) {
  if (completed && blockCount && blockCount > 0) return blockCount - 1
  if (stageKey === 'day0') {
    if (blockedAtStep === 'open_tool' || blockedAtStep === 'login_ok') return 2
    if (blockedAtStep === 'first_prompt') return 3
    if (blockedAtStep === 'copy_result') return 4
    return 0
  }
  if (blockedAtStep === 'pick_scene') return 1
  if (blockedAtStep === 'ask_ai') return 2
  if (blockedAtStep === 'rewrite') return 3
  if (blockedAtStep === 'save_output') return 5
  return 0
}

function stageHasWork(stage?: TrainingStage) {
  if (!stage) return false
  return Boolean(
    stage.completed ||
    (stage.proof_artifact || '').trim() ||
    (stage.notes || '').trim() ||
    (stage.blocked_at_step || '').trim() ||
    stage.vp_feedback?.submitted_at,
  )
}

function resumeStageFromState(state?: TrainingState | null): StageKey {
  const normalized = normalizeTrainingState(state)
  if (!normalized) return 'day0'
  if (!normalized.day0?.completed) return 'day0'
  if (normalized.ui_state?.selected_stage === 'day1') return 'day1'
  if (stageHasWork(normalized.day1)) return 'day1'
  if (normalized.day0?.completed) return 'day1'
  return 'day0'
}

function StageCard({
  stage,
  stageKey,
  draft,
  onSave,
  onSaveFeedback,
  onDraftChange,
  onInteraction,
  onContinue,
  saving,
  feedbackSaving,
  apiBase,
  authHeaders,
  showContinue,
  reminder,
}: {
  stage: TrainingStage | undefined
  stageKey: StageKey
  draft?: UiStageDraft
  onSave: (stageKey: StageKey, payload: { proof_artifact: string; blocked_at_step: string; notes: string; completed: boolean }) => void
  onSaveFeedback: (stageKey: StageKey, payload: { empathy_score: number; clarity_score: number; motivation_score: number; biggest_blocker: string; freeform_feedback: string }) => void
  onDraftChange: (stageKey: StageKey, draft: UiStageDraft) => void
  onInteraction: (eventName: string, payload?: Record<string, unknown>) => void
  onContinue: () => void
  saving: boolean
  feedbackSaving: boolean
  apiBase: string
  authHeaders: () => Record<string, string>
  showContinue: boolean
  reminder?: string | null
}) {
  const [proof, setProof] = useState(draft?.proof_artifact ?? stage?.proof_artifact ?? '')
  const [blocked, setBlocked] = useState(draft?.blocked_at_step ?? stage?.blocked_at_step ?? '')
  const [notes, setNotes] = useState(draft?.notes ?? stage?.notes ?? '')
  const [completed, setCompleted] = useState(Boolean(draft?.completed ?? stage?.completed))
  const [empathyScore, setEmpathyScore] = useState(draft?.empathy_score ?? stage?.vp_feedback?.empathy_score ?? 3)
  const [clarityScore, setClarityScore] = useState(draft?.clarity_score ?? stage?.vp_feedback?.clarity_score ?? 3)
  const [motivationScore, setMotivationScore] = useState(draft?.motivation_score ?? stage?.vp_feedback?.motivation_score ?? 3)
  const [biggestBlocker, setBiggestBlocker] = useState(draft?.biggest_blocker ?? stage?.vp_feedback?.biggest_blocker ?? '')
  const [freeformFeedback, setFreeformFeedback] = useState(draft?.freeform_feedback ?? stage?.vp_feedback?.freeform_feedback ?? '')

  useEffect(() => {
    setProof(draft?.proof_artifact ?? stage?.proof_artifact ?? '')
    setBlocked(draft?.blocked_at_step ?? stage?.blocked_at_step ?? '')
    setNotes(draft?.notes ?? stage?.notes ?? '')
    setCompleted(Boolean(draft?.completed ?? stage?.completed))
    setEmpathyScore(draft?.empathy_score ?? stage?.vp_feedback?.empathy_score ?? 3)
    setClarityScore(draft?.clarity_score ?? stage?.vp_feedback?.clarity_score ?? 3)
    setMotivationScore(draft?.motivation_score ?? stage?.vp_feedback?.motivation_score ?? 3)
    setBiggestBlocker(draft?.biggest_blocker ?? stage?.vp_feedback?.biggest_blocker ?? '')
    setFreeformFeedback(draft?.freeform_feedback ?? stage?.vp_feedback?.freeform_feedback ?? '')
  }, [stageKey, stage, draft])

  useEffect(() => {
    onDraftChange(stageKey, {
      proof_artifact: proof,
      blocked_at_step: blocked,
      notes,
      completed,
      empathy_score: empathyScore,
      clarity_score: clarityScore,
      motivation_score: motivationScore,
      biggest_blocker: biggestBlocker,
      freeform_feedback: freeformFeedback,
    })
  }, [stageKey, proof, blocked, notes, completed, empathyScore, clarityScore, motivationScore, biggestBlocker, freeformFeedback, onDraftChange])

  async function downloadKit(downloadUrl: string, kitId: string) {
    const res = await fetch(`${apiBase}${downloadUrl}`, { headers: { ...authHeaders() } })
    if (!res.ok) throw new Error(`material download failed: ${res.status}`)
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${kitId}.zip`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  return (
    <section id={curriculumDetailBlockId(stageKey, 0)} style={{ scrollMarginTop: 18, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 24, padding: 20, display: 'grid', gap: 16 }}>
      <div>
        <div style={{ fontSize: '.82rem', color: C.accent, fontWeight: 900, letterSpacing: '.05em', marginBottom: 6 }}>{stageKey === 'day0' ? 'DAY 0' : 'DAY 1'}</div>
        <h2 style={{ margin: 0, fontSize: '1.55rem', lineHeight: 1.3, color: '#000000' }}>{displayStageTitle(stage?.title)}</h2>
      </div>

      {reminder && (
        <div style={{ background: C.warnSoft, border: '1px solid #fdba74', borderRadius: 16, padding: 14, color: C.ink, lineHeight: 1.55 }}>
          <strong style={{ display: 'block', marginBottom: 4 }}>복습 제안</strong>
          {reminder}
        </div>
      )}

      {(stage?.estimated_minutes || stage?.completion_rule) && (
        <div style={{ background: '#eff6ff', border: '1px solid #93c5fd', borderRadius: 16, padding: 14, display: 'grid', gap: 8 }}>
          <div style={{ fontSize: '.76rem', color: '#1d4ed8', fontWeight: 800 }}>권장 학습 분량</div>
          {stage?.estimated_minutes ? (
            <div style={{ fontSize: '1rem', lineHeight: 1.55, color: C.ink, fontWeight: 800 }}>{lessonLabel(stageKey)}은 약 {stage.estimated_minutes}분 분량으로 설계되었습니다.</div>
          ) : null}
          {stage?.completion_rule ? (
            <div style={{ color: C.muted, fontSize: '.92rem', lineHeight: 1.6 }}>{stage.completion_rule}</div>
          ) : null}
        </div>
      )}

      {(stage?.learning_why || stage?.learning_outcome) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10 }}>
          {stage?.learning_why ? (
            <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontSize: '.82rem', color: C.accent, fontWeight: 900, marginBottom: 6 }}>왜 이 과정을 하나</div>
              <div style={{ color: C.ink, fontSize: '.95rem', lineHeight: 1.6 }}>{stage.learning_why}</div>
            </div>
          ) : null}
          {stage?.learning_outcome ? (
            <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontSize: '.82rem', color: C.accent, fontWeight: 900, marginBottom: 6 }}>끝나면 무엇이 달라지나</div>
              <div style={{ color: C.ink, fontSize: '.95rem', lineHeight: 1.6 }}>{stage.learning_outcome}</div>
            </div>
          ) : null}
        </div>
      )}

      {!!stage?.foundation_concepts?.length && (
        <div id={curriculumDetailBlockId(stageKey, 1)} style={{ scrollMarginTop: 18, display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>먼저 알아야 할 기초지식</div>
          <div style={{ color: C.faint, fontSize: '.86rem', lineHeight: 1.55 }}>
            미션부터 밀어붙이지 않고, 지금부터 무엇을 왜 하는지 먼저 이해합니다. 기술 용어를 외우는 시간이 아니라 불안과 막막함을 줄이는 시간입니다.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
            {stage.foundation_concepts.map((item, index) => (
              <div key={`${item.title}-${index}`} style={{ background: '#f8fafc', border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
                <div style={{ fontWeight: 900, color: C.ink, marginBottom: 6 }}>{item.title}</div>
                <div style={{ color: C.muted, fontSize: '.92rem', lineHeight: 1.6 }}>{item.body}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!!stage?.schedule_blocks?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>오늘의 1시간+ 학습 플로우</div>
          <div style={{ color: C.faint, fontSize: '.86rem', lineHeight: 1.55 }}>
            아래 순서를 모두 따라가야 그날 학습이 끝난 것으로 봅니다. 중간에 한 미션만 하고 멈추지 않도록, 실제 학습 시간을 기준으로 설계했습니다.
          </div>
          {stage.schedule_blocks.map((item, index) => (
            <div id={curriculumBlockId(stageKey, index)} key={`${item.title}-${index}`} style={{ background: '#ffffff', border: `1px solid ${C.border}`, borderRadius: 16, padding: 14, display: 'grid', gridTemplateColumns: '76px 1fr', gap: 12, alignItems: 'start' }}>
              <div style={{ background: '#111827', color: '#ffffff', borderRadius: 12, padding: '8px 10px', textAlign: 'center', fontWeight: 900, fontSize: '.92rem' }}>{item.minutes}분</div>
              <div>
                <div style={{ fontWeight: 800, color: C.ink, marginBottom: 4 }}>{index + 1}. {item.title}</div>
                <div style={{ color: C.muted, fontSize: '.92rem', lineHeight: 1.55 }}>{item.goal}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!!stage?.tutorial_steps?.length && (
        <div id={curriculumDetailBlockId(stageKey, 2)} style={{ scrollMarginTop: 18, display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>튜토리얼</div>
          {stage.tutorial_steps.map((item, index) => (
            <div key={item.id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontWeight: 800, color: C.ink, marginBottom: 4 }}>{index + 1}. {item.title}</div>
              <div style={{ color: C.muted, fontSize: '.95rem', lineHeight: 1.6 }}>{item.body}</div>
            </div>
          ))}
        </div>
      )}

      {stage?.required_action && (
        <div id={curriculumDetailBlockId(stageKey, 3)} style={{ scrollMarginTop: 18, background: C.accentSoft, border: `1px solid ${C.accent}`, borderRadius: 16, padding: 14 }}>
          <div style={{ fontSize: '.76rem', color: C.accent, fontWeight: 800, marginBottom: 6 }}>오늘 바로 해야 할 일</div>
          <div style={{ fontSize: '1rem', lineHeight: 1.65, color: C.ink, fontWeight: 700 }}>{stage.required_action}</div>
        </div>
      )}

      {!!stage?.checklist?.length && (
        <div id={curriculumDetailBlockId(stageKey, 4)} style={{ scrollMarginTop: 18, display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>체크리스트</div>
          {stage.checklist.map((item) => (
            <div key={item.id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontWeight: 800, color: C.ink, marginBottom: 4 }}>{item.title}</div>
              <div style={{ color: C.muted, fontSize: '.95rem', lineHeight: 1.6 }}>{item.instruction}</div>
              <div style={{ color: C.faint, fontSize: '.82rem', marginTop: 6 }}>잘 되면: {item.success_signal}</div>
            </div>
          ))}
        </div>
      )}

      {!!stage?.sample_materials?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>실전 교보재</div>
          {stage.sample_materials.map((item) => (
            <div key={item.kit_id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14, display: 'grid', gap: 8 }}>
              <div style={{ fontWeight: 800, color: C.ink }}>{item.title}</div>
              <div style={{ color: C.muted, fontSize: '.95rem', lineHeight: 1.6 }}>{item.description}</div>
              <div style={{ color: C.faint, fontSize: '.82rem', lineHeight: 1.5 }}>포함 파일: {item.files.join(', ')}</div>
              <button type="button" onClick={() => {
                onInteraction('download_material', { kit_id: item.kit_id })
                void downloadKit(item.download_url, item.kit_id)
              }} style={{ justifySelf: 'start', background: '#111827', color: '#fff', border: 'none', borderRadius: 12, padding: '11px 14px', fontWeight: 800, cursor: 'pointer' }}>
                샘플 파일 내려받기
              </button>
            </div>
          ))}
        </div>
      )}

      {!!stage?.home_priority_missions?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>오늘 가장 먼저 해볼 생활형 미션</div>
          <div style={{ color: C.faint, fontSize: '.86rem', lineHeight: 1.55 }}>
            무엇부터 시작할지 막히면 아래 4개 중 하나를 그대로 고르면 됩니다. 주부/학부모가 가장 자주 부딪히는 장면만 먼저 추렸습니다.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
            {stage.home_priority_missions.map((item, index) => (
              <div key={`${item.title}-${index}`} style={{ background: '#fff7ed', border: '1px solid #fdba74', borderRadius: 16, padding: 14, display: 'grid', gap: 8 }}>
                <div style={{ fontWeight: 900, color: C.ink }}>{item.title}</div>
                <div style={{ color: C.muted, fontSize: '.9rem', lineHeight: 1.55 }}>{item.why}</div>
                <div style={{ color: C.faint, fontSize: '.84rem', lineHeight: 1.5 }}>언제 쓰나: {item.use_when}</div>
                <div style={{ color: C.faint, fontSize: '.84rem', lineHeight: 1.5 }}>결과 형태: {item.result_shape}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!!stage?.scenario_bank?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>가정 주부 실전 시나리오 뱅크</div>
          <div style={{ color: C.faint, fontSize: '.86rem', lineHeight: 1.55 }}>
            아래 장면 중 하나를 그대로 골라 오늘 실습에 써도 됩니다. 생활 장면을 많이 넣어 두었으니, VP나 일반 고객 모두 바로 공감 가능한 출발점으로 쓸 수 있습니다.
          </div>
          <div style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, borderRadius: 16, padding: 14 }}>
            <div style={{ fontWeight: 900, color: C.ink, marginBottom: 6 }}>VP에게 가장 먼저 권하는 장면</div>
            <div style={{ color: C.muted, fontSize: '.92rem', lineHeight: 1.6 }}>
              학원 시간표와 학교 일정 충돌, 긴 가정통신문 핵심 뽑기, 진학 설명회 메모 정리, 엄마모임과 가족모임 시간 충돌 정리부터 먼저 해보는 것이 가장 현실적입니다.
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10 }}>
            {stage.scenario_bank.map((item, index) => (
              <div key={`${item.title}-${index}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14, display: 'grid', gap: 8 }}>
                <div style={{ fontWeight: 800, color: C.ink }}>{item.title}</div>
                <div style={{ color: C.muted, fontSize: '.92rem', lineHeight: 1.55 }}>{item.situation}</div>
                <div style={{ color: C.faint, fontSize: '.82rem', lineHeight: 1.5 }}>{item.prompt}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!!stage?.home_life_recommended_learning?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>맘카페/학부모 RAG 추천</div>
          {stage.home_life_recommended_learning.map((item, index) => (
            <div key={`${item.title}-${index}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontWeight: 800, color: C.ink }}>{item.title}</div>
              <div style={{ color: C.faint, fontSize: '.82rem', marginTop: 4 }}>{item.source_kind}</div>
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer" style={{ display: 'inline-block', marginTop: 8, color: C.accent, fontWeight: 800, textDecoration: 'none' }}>
                  자료 열기
                </a>
              ) : (
                <div style={{ color: C.faint, fontSize: '.82rem', marginTop: 8 }}>링크가 없는 내부 추천 자료</div>
              )}
            </div>
          ))}
        </div>
      )}

      {stage?.practice_prompt_template && (
        <div style={{ background: '#fefce8', border: `1px solid ${C.warn}`, borderRadius: 16, padding: 14 }}>
          <div style={{ fontSize: '.76rem', color: C.warn, fontWeight: 800, marginBottom: 6 }}>바로 붙여 넣을 프롬프트</div>
          <div style={{ fontSize: '.95rem', lineHeight: 1.65, color: C.ink, whiteSpace: 'pre-wrap' }}>{stage.practice_prompt_template}</div>
        </div>
      )}

      {!!stage?.recommended_learning?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>RAG 추천 자료</div>
          {stage.recommended_learning.map((item, index) => (
            <div key={`${item.title}-${index}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontWeight: 800, color: C.ink }}>{item.title}</div>
              <div style={{ color: C.faint, fontSize: '.82rem', marginTop: 4 }}>{item.source_kind}</div>
              {item.url ? (
                <a href={item.url} target="_blank" rel="noreferrer" style={{ display: 'inline-block', marginTop: 8, color: C.accent, fontWeight: 800, textDecoration: 'none' }}>
                  자료 열기
                </a>
              ) : (
                <div style={{ color: C.faint, fontSize: '.82rem', marginTop: 8 }}>링크가 없는 내부 추천 자료</div>
              )}
            </div>
          ))}
        </div>
      )}

      {!!stage?.evidence_cards?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
            <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>근거 묶음</div>
            <div style={{ fontSize: '.78rem', color: C.faint }}>
              mode={stage.retrieval_mode} · safe={String(stage.customer_facing_safe)} · fallback={String(stage.fallback_used)}
            </div>
          </div>
          {stage.evidence_cards.map((item, idx) => (
            <div key={`${item.title}-${idx}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontWeight: 800, color: C.ink }}>{item.title}</div>
              <div style={{ fontSize: '.82rem', color: C.accent, margin: '4px 0 6px' }}>{item.source_kind}</div>
              <div style={{ color: C.muted, fontSize: '.92rem', lineHeight: 1.55 }}>{item.snippet}</div>
              {item.cite && <div style={{ color: C.faint, fontSize: '.8rem', lineHeight: 1.45, marginTop: 6 }}>{item.cite}</div>}
              {item.url && (
                <a href={item.url} target="_blank" rel="noreferrer" style={{ display: 'inline-block', marginTop: 8, color: C.accent, fontWeight: 800, textDecoration: 'none' }}>
                  원문 열기
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gap: 10 }}>
        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>증거 결과물</span>
          <textarea value={proof} onChange={(e) => setProof(e.target.value)} onKeyDown={(e) => onInteraction('proof_keydown', { key: e.key, field: 'proof_artifact' })} rows={5} placeholder={stage?.proof_artifact_hint || '실제로 만든 결과를 붙여 넣으세요.'} style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>어디서 막혔나</span>
          <select value={blocked} onChange={(e) => setBlocked(e.target.value)} onClick={() => onInteraction('blocked_step_click', { field: 'blocked_at_step' })} style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', fontFamily: 'inherit', background: C.surface, boxSizing: 'border-box' }}>
            <option value="">막힌 단계 없음</option>
            {(stage?.blocked_step_options || []).map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>메모</span>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} onKeyDown={(e) => onInteraction('notes_keydown', { key: e.key, field: 'notes' })} rows={3} placeholder="어디서 이해가 잘 됐고, 어디서 막혔는지 적으세요." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: C.ink, fontSize: '.9rem', fontWeight: 700 }}>
          <input type="checkbox" checked={completed} onChange={(e) => {
            setCompleted(e.target.checked)
            onInteraction('toggle_completed', { checked: e.target.checked })
          }} />
          이 단계는 실제로 끝까지 해봤다
        </label>

        <button onClick={() => {
          onInteraction('save_stage_click', { stage: stageKey })
          onSave(stageKey, { proof_artifact: proof, blocked_at_step: blocked, notes, completed })
        }} disabled={saving} style={{ background: saving ? '#cbd5e1' : '#111827', color: '#fff', border: 'none', borderRadius: 14, padding: '13px 16px', fontSize: '.95rem', fontWeight: 800, cursor: saving ? 'wait' : 'pointer' }}>
          {saving ? '저장 중…' : '이 단계 저장'}
        </button>

        {showContinue && (
          <div style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, borderRadius: 16, padding: 14, display: 'grid', gap: 10 }}>
            <div style={{ color: C.ink, fontWeight: 800 }}>이어서 다음 단계로 진행할까요?</div>
            <button type="button" onClick={() => {
              onInteraction('continue_click', { from: stageKey })
              onContinue()
            }} style={{ justifySelf: 'start', background: C.accent, color: '#fff', border: 'none', borderRadius: 12, padding: '11px 14px', fontWeight: 800, cursor: 'pointer' }}>
              다음 단계로 이어서 하기
            </button>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gap: 10, background: '#f8fafc', border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
        <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>VP 피드백 메뉴</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10 }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.82rem', color: C.muted, fontWeight: 700 }}>공감도</span>
            <select value={empathyScore} onChange={(e) => setEmpathyScore(Number(e.target.value))} onClick={() => onInteraction('feedback_score_click', { field: 'empathy_score' })} style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 10, background: C.surface }}>
              {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
            </select>
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.82rem', color: C.muted, fontWeight: 700 }}>명확성</span>
            <select value={clarityScore} onChange={(e) => setClarityScore(Number(e.target.value))} onClick={() => onInteraction('feedback_score_click', { field: 'clarity_score' })} style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 10, background: C.surface }}>
              {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
            </select>
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.82rem', color: C.muted, fontWeight: 700 }}>학습욕구</span>
            <select value={motivationScore} onChange={(e) => setMotivationScore(Number(e.target.value))} onClick={() => onInteraction('feedback_score_click', { field: 'motivation_score' })} style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 10, background: C.surface }}>
              {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
            </select>
          </label>
        </div>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>가장 크게 막힌 지점</span>
          <input value={biggestBlocker} onChange={(e) => setBiggestBlocker(e.target.value)} onKeyDown={(e) => onInteraction('feedback_keydown', { key: e.key, field: 'biggest_blocker' })} placeholder="예: 파일을 어디서 열어야 하는지 처음엔 헷갈렸음" style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }} />
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>자유 피드백</span>
          <textarea value={freeformFeedback} onChange={(e) => setFreeformFeedback(e.target.value)} onKeyDown={(e) => onInteraction('feedback_keydown', { key: e.key, field: 'freeform_feedback' })} rows={4} placeholder="무엇이 좋았는지, 무엇이 어렵거나 피상적으로 느껴졌는지 적으세요." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </label>

        <button onClick={() => {
          onInteraction('save_feedback_click', { stage: stageKey })
          onSaveFeedback(stageKey, { empathy_score: empathyScore, clarity_score: clarityScore, motivation_score: motivationScore, biggest_blocker: biggestBlocker, freeform_feedback: freeformFeedback })
        }} disabled={feedbackSaving} style={{ background: feedbackSaving ? '#cbd5e1' : C.accent, color: '#fff', border: 'none', borderRadius: 14, padding: '13px 16px', fontSize: '.95rem', fontWeight: 800, cursor: feedbackSaving ? 'wait' : 'pointer' }}>
          {feedbackSaving ? '피드백 저장 중…' : 'VP 피드백 저장'}
        </button>
        {stage?.vp_feedback?.submitted_at && <div style={{ fontSize: '.8rem', color: C.faint }}>최근 저장: {stage.vp_feedback.submitted_at}</div>}
      </div>
    </section>
  )
}

export function EduVpTrainingPage({ apiBase, authHeaders, currentRole }: Props) {
  const embeddedMode = Boolean(currentRole)
  const [isMobile, setIsMobile] = useState(false)
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authName, setAuthName] = useState('')
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authLoading, setAuthLoading] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [trainingAuthToken, setTrainingAuthToken] = useState('')
  const [preferredLlm, setPreferredLlm] = useState('gemini')
  const [currentDevice, setCurrentDevice] = useState('android')
  const [desktopOs, setDesktopOs] = useState('windows')
  const [loading, setLoading] = useState(false)
  const [savingStage, setSavingStage] = useState<StageKey | null>(null)
  const [savingFeedbackStage, setSavingFeedbackStage] = useState<StageKey | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [caseId, setCaseId] = useState<number | null>(null)
  const [trainingState, setTrainingState] = useState<TrainingState | null>(null)
  const [uiState, setUiState] = useState<UiState>({})
  const [caseHistory, setCaseHistory] = useState<CaseItem[]>([])
  const [showCaseArchive, setShowCaseArchive] = useState(false)
  const [selectedStage, setSelectedStage] = useState<StageKey>('day0')
  const [showContinueFrom, setShowContinueFrom] = useState<StageKey | null>(null)
  const [activeCurriculumIndex, setActiveCurriculumIndex] = useState(0)
  const [resettingCases, setResettingCases] = useState(false)
  const navigatorRef = useRef<HTMLElement | null>(null)
  const latestUiStateRef = useRef<UiState>({})
  const latestAuthEmailRef = useRef('')
  const latestCaseIdRef = useRef<number | null>(null)
  const syncSeqRef = useRef(0)
  const curriculumScrollLockUntilRef = useRef(0)
  const observedContentScrollTopRef = useRef(0)
  const navigatorTargetOffsetRef = useRef(0)
  const navigatorDisplayOffsetRef = useRef(0)
  const navigatorAnimationFrameRef = useRef(0)
  const archivedCases = caseHistory.filter((item) => item.case_id !== caseId)
  const hasCaseHistory = archivedCases.length > 0
  const hasStoredCases = caseHistory.length > 0

  function trainingHeaders() {
    const headers = { ...authHeaders() }
    if (trainingAuthToken.trim()) headers['X-Edu-Training-Auth'] = trainingAuthToken.trim()
    return headers
  }

  function persistSessionCache(email: string, nextCaseId: number, nextTrainingState: TrainingState | null, nextUiState: UiState) {
    const safeEmail = email.trim().toLowerCase()
    if (!safeEmail) return
    window.localStorage.setItem(caseStorageKey(safeEmail), String(nextCaseId))
    window.localStorage.setItem(sessionCacheKey(safeEmail), JSON.stringify({
      case_id: nextCaseId,
      training_state: nextTrainingState,
      ui_state: nextUiState,
      cached_at: new Date().toISOString(),
    }))
  }

  function applyTrainingSession(email: string, nextCaseId: number, nextTrainingStateRaw: TrainingState | null | undefined) {
    const nextTrainingState = normalizeTrainingState(nextTrainingStateRaw) || null
    const day0Done = Boolean(nextTrainingState?.day0?.completed)
    const rawUiState = nextTrainingState?.ui_state || {}
    const nextUiState: UiState = {
      ...rawUiState,
      selected_stage: day0Done ? (rawUiState.selected_stage || resumeStageFromState(nextTrainingState)) : 'day0',
      show_continue_from: day0Done ? (rawUiState.show_continue_from || '') : '',
    }
    const nextStage = nextUiState.selected_stage || resumeStageFromState(nextTrainingState)
    setAuthEmail(email)
    setIsAuthenticated(true)
    setCaseId(nextCaseId)
    setTrainingState(nextTrainingState)
    setUiState(nextUiState)
    setSelectedStage(nextStage)
    setShowContinueFrom(nextUiState.show_continue_from === 'day0' || nextUiState.show_continue_from === 'day1' ? nextUiState.show_continue_from : null)
    setShowCaseArchive(Boolean(nextUiState.show_case_archive))
    setActiveCurriculumIndex(Math.max(0, Number(nextUiState.active_curriculum_index || 0)))
    setPreferredLlm(nextUiState.preferred_llm || nextTrainingState?.primary_llm_path || preferredLlm)
    setCurrentDevice(nextUiState.current_device || currentDevice)
    setDesktopOs(nextUiState.desktop_os || desktopOs)
    latestUiStateRef.current = nextUiState
    latestAuthEmailRef.current = email
    latestCaseIdRef.current = nextCaseId
    syncSeqRef.current = Math.max(syncSeqRef.current, Number(nextUiState.last_client_seq || 0))
    persistSessionCache(email, nextCaseId, nextTrainingState, nextUiState)
  }

  function hydrateFromLocalCache(email: string) {
    try {
      const raw = window.localStorage.getItem(sessionCacheKey(email))
      if (!raw) return false
      const parsed = JSON.parse(raw) as { case_id?: number; training_state?: TrainingState; ui_state?: UiState }
      const cachedCaseId = Number(parsed.case_id)
      if (!Number.isFinite(cachedCaseId) || cachedCaseId < 0) return false
      const cachedState = normalizeTrainingState(parsed.training_state || null)
      if (!cachedState) return false
      if (parsed.ui_state && !cachedState.ui_state) cachedState.ui_state = parsed.ui_state
      applyTrainingSession(email, cachedCaseId, cachedState)
      return true
    } catch {
      return false
    }
  }

  async function loadCases(explicitEmail?: string, options?: { silentError?: boolean }) {
    const safeEmail = (explicitEmail || authEmail).trim().toLowerCase()
    if (!safeEmail) return [] as CaseItem[]
    const res = await fetch(`${apiBase}/api/edu/vp-training/cases?email=${encodeURIComponent(safeEmail)}`, {
      headers: trainingHeaders(),
    })
    const { raw, data } = await readJsonSafe(res)
    if (res.ok) {
      const cases = Array.isArray(data.cases) ? data.cases : []
      setCaseHistory(cases)
      return cases as CaseItem[]
    }
    if (!options?.silentError) {
      setError(typeof data.detail === 'string' ? data.detail : raw || 'case history load failed')
    }
    return [] as CaseItem[]
  }

  async function submitAuth() {
    const safeEmail = authEmail.trim().toLowerCase()
    if (!safeEmail || !authPassword.trim()) {
      setError('이메일과 비밀번호를 입력하세요.')
      return
    }
    setAuthLoading(true)
    setError(null)
    try {
      const endpoint = authMode === 'login'
        ? '/api/edu/vp-training/account/login'
        : '/api/edu/vp-training/account/register'
      const payload = authMode === 'login'
        ? { email: safeEmail, password: authPassword }
        : { email: safeEmail, password: authPassword, name: authName }
      const res = await fetch(`${apiBase}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...trainingHeaders() },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setAuthEmail(safeEmail)
      setIsAuthenticated(true)
      window.localStorage.setItem(VP_TRAINING_AUTH_EMAIL_KEY, safeEmail)
      const nextToken = typeof data?.training_auth_token === 'string' ? data.training_auth_token : ''
      setTrainingAuthToken(nextToken)
      if (nextToken) window.localStorage.setItem(VP_TRAINING_AUTH_TOKEN_KEY, nextToken)
      setAuthPassword('')
      const resumed = await resumeTrainingSession(safeEmail)
      if (!resumed) await buildTrainingSlice(undefined, false, safeEmail)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'account auth failed')
    } finally {
      setAuthLoading(false)
    }
  }

  function logoutTrainingAccount() {
    if (embeddedMode) return
    setIsAuthenticated(false)
    setAuthEmail('')
    setAuthPassword('')
    setAuthName('')
    setCaseId(null)
    setTrainingState(null)
    setUiState({})
    setCaseHistory([])
    setShowCaseArchive(false)
    setSelectedStage('day0')
    setShowContinueFrom(null)
    window.localStorage.removeItem(VP_TRAINING_AUTH_EMAIL_KEY)
    window.localStorage.removeItem(VP_TRAINING_AUTH_TOKEN_KEY)
    setTrainingAuthToken('')
    if (authEmail.trim()) {
      window.localStorage.removeItem(caseStorageKey(authEmail.trim().toLowerCase()))
      window.localStorage.removeItem(sessionCacheKey(authEmail.trim().toLowerCase()))
    }
  }

  async function resumeTrainingSession(explicitEmail?: string, targetCaseId?: number | null, options?: { silentError?: boolean }) {
    const safeEmail = (explicitEmail || authEmail).trim().toLowerCase()
    if (!safeEmail) return false
    setLoading(true)
    if (!options?.silentError) setError(null)
    try {
      const params = new URLSearchParams({ email: safeEmail })
      if (targetCaseId != null) params.set('case_id', String(targetCaseId))
      const res = await fetch(`${apiBase}/api/edu/vp-training/session?${params.toString()}`, { headers: trainingHeaders() })
      const { raw, data } = await readJsonSafe(res)
      const detail = typeof data.detail === 'string' ? data.detail : ''
      if (!res.ok) throw new Error(detail || raw || `HTTP ${res.status}`)
      if (!data.exists) {
        if (targetCaseId != null && !options?.silentError) setError('이 케이스에는 복원 가능한 진행 기록이 없습니다.')
        return false
      }
      const nextCaseId = typeof data.case_id === 'number' ? data.case_id : Number(data.case_id)
      applyTrainingSession(safeEmail, nextCaseId, (data.training_state as TrainingState | null | undefined) || null)
      if (showCaseArchive) await loadCases(safeEmail, { silentError: true })
      return true
    } catch (err) {
      if (!options?.silentError) setError(err instanceof Error ? err.message : 'session resume failed')
      return false
    } finally {
      setLoading(false)
    }
  }

  async function buildTrainingSlice(targetCaseId?: number | null, restart?: boolean, explicitEmail?: string, options?: { silentError?: boolean }) {
    setLoading(true)
    if (!options?.silentError) setError(null)
    try {
      const safeEmail = (explicitEmail || authEmail).trim().toLowerCase()
      if (!safeEmail) {
        setLoading(false)
        return
      }
      let resolvedCaseId = restart ? null : (targetCaseId ?? caseId)
      if (!restart && resolvedCaseId == null) {
        const existingCases = await loadCases(safeEmail, { silentError: options?.silentError })
        const restorableCase = existingCases.find((item) => item.has_training_state)
        if (restorableCase) {
          resolvedCaseId = restorableCase.case_id
        }
      }
      const res = await fetch(`${apiBase}/api/edu/vp-training/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...trainingHeaders() },
        body: JSON.stringify({
          case_id: resolvedCaseId,
          email: safeEmail,
          preferred_llm: preferredLlm,
          current_device: currentDevice,
          desktop_os: desktopOs,
          ai_experience: 'beginner',
          biggest_friction: '',
          learning_goal: '',
          force_new: restart ?? false,
        }),
      })
      const { raw, data } = await readJsonSafe(res)
      const detail = typeof data.detail === 'string' ? data.detail : ''
      if (!res.ok) throw new Error(detail || raw || `HTTP ${res.status}`)
      const nextCaseId = typeof data.case_id === 'number' ? data.case_id : Number(data.case_id)
      const nextTrainingState = normalizeTrainingState((data.training_state as TrainingState | null | undefined) || null)
      applyTrainingSession(safeEmail, nextCaseId, nextTrainingState)
      if (showCaseArchive) await loadCases(safeEmail)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'VP training flow build failed'
      if (message.includes('case not found')) {
        const staleEmail = (explicitEmail || authEmail).trim().toLowerCase()
        if (staleEmail) {
          window.localStorage.removeItem(caseStorageKey(staleEmail))
          window.localStorage.removeItem(sessionCacheKey(staleEmail))
        }
        if (!restart && (targetCaseId ?? caseId)) {
          await buildTrainingSlice(undefined, false, explicitEmail || authEmail, options)
          return
        }
        if (!options?.silentError) setError(null)
      } else {
        if (!options?.silentError) {
          setError(message)
        } else {
          setCaseId(null)
          setTrainingState(null)
          setUiState({})
        }
      }
    } finally {
      setLoading(false)
    }
  }

  async function saveStage(stage: StageKey, payload: { proof_artifact: string; blocked_at_step: string; notes: string; completed: boolean }) {
    if (caseId == null) return
    setSavingStage(stage)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/artifact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...trainingHeaders() },
        body: JSON.stringify({ case_id: caseId, stage, ...payload }),
      })
      const { raw, data } = await readJsonSafe(res)
      const detail = typeof data.detail === 'string' ? data.detail : ''
      if (!res.ok) throw new Error(detail || raw || `HTTP ${res.status}`)
      const nextTrainingState = normalizeTrainingState((data.training_state as TrainingState | null | undefined) || null)
      setTrainingState(nextTrainingState)
      setShowContinueFrom(stage)
      setUiState((prev) => ({ ...prev, show_continue_from: stage }))
      if (authEmail.trim()) persistSessionCache(authEmail.trim().toLowerCase(), caseId, nextTrainingState, { ...latestUiStateRef.current, show_continue_from: stage })
      if (showCaseArchive) await loadCases()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'stage save failed')
    } finally {
      setSavingStage(null)
    }
  }

  async function saveFeedback(stage: StageKey, payload: { empathy_score: number; clarity_score: number; motivation_score: number; biggest_blocker: string; freeform_feedback: string }) {
    if (caseId == null) return
    setSavingFeedbackStage(stage)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...trainingHeaders() },
        body: JSON.stringify({ case_id: caseId, stage, ...payload }),
      })
      const { raw, data } = await readJsonSafe(res)
      const detail = typeof data.detail === 'string' ? data.detail : ''
      if (!res.ok) throw new Error(detail || raw || `HTTP ${res.status}`)
      const nextTrainingState = normalizeTrainingState((data.training_state as TrainingState | null | undefined) || null)
      setTrainingState(nextTrainingState)
      if (authEmail.trim()) persistSessionCache(authEmail.trim().toLowerCase(), caseId, nextTrainingState, latestUiStateRef.current)
      if (showCaseArchive) await loadCases()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'feedback save failed')
    } finally {
      setSavingFeedbackStage(null)
    }
  }

  async function resetAllCases() {
    const safeEmail = authEmail.trim().toLowerCase()
    if (!safeEmail || resettingCases) return
    const confirmed = window.confirm('현재 계정의 VP 훈련 케이스를 모두 삭제하고 처음부터 다시 시작할까요?')
    if (!confirmed) return
    setResettingCases(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/cases/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...trainingHeaders() },
        body: JSON.stringify({ email: safeEmail }),
      })
      const { raw, data } = await readJsonSafe(res)
      const detail = typeof data.detail === 'string' ? data.detail : ''
      if (!res.ok) throw new Error(detail || raw || `HTTP ${res.status}`)
      window.localStorage.removeItem(caseStorageKey(safeEmail))
      window.localStorage.removeItem(sessionCacheKey(safeEmail))
      setCaseId(null)
      setTrainingState(null)
      setUiState({})
      setCaseHistory([])
      setShowCaseArchive(false)
      setSelectedStage('day0')
      setShowContinueFrom(null)
    } catch (err) {
      setError(err instanceof TypeError ? '전체 초기화 요청이 서버에 닿지 않았습니다. 잠시 후 다시 시도하세요.' : err instanceof Error ? err.message : 'case reset failed')
    } finally {
      setResettingCases(false)
    }
  }

  useEffect(() => {
    latestUiStateRef.current = uiState
    latestAuthEmailRef.current = authEmail.trim().toLowerCase()
    latestCaseIdRef.current = caseId
  }, [uiState, authEmail, caseId])

  async function syncSessionState(eventType: string, eventName: string, eventPayload?: Record<string, unknown>, overrideUiState?: UiState) {
    const safeEmail = latestAuthEmailRef.current
    const activeCaseId = latestCaseIdRef.current
    if (!safeEmail || activeCaseId == null) return
    const payloadUiState = overrideUiState || latestUiStateRef.current
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/session/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...trainingHeaders() },
        body: JSON.stringify({
          case_id: activeCaseId,
          email: safeEmail,
          selected_stage: payloadUiState.selected_stage || selectedStage,
          active_curriculum_index: payloadUiState.active_curriculum_index ?? activeCurriculumIndex,
          show_case_archive: Boolean(payloadUiState.show_case_archive ?? showCaseArchive),
          show_continue_from: payloadUiState.show_continue_from || '',
          preferred_llm: payloadUiState.preferred_llm || preferredLlm,
          current_device: payloadUiState.current_device || currentDevice,
          desktop_os: payloadUiState.desktop_os || desktopOs,
          stage_drafts: payloadUiState.stage_drafts || {},
          client_seq: ++syncSeqRef.current,
          event_type: eventType,
          event_name: eventName,
          event_payload: eventPayload || {},
        }),
      })
      const { data } = await readJsonSafe(res)
      if (!res.ok) {
        console.warn('VP training session sync failed', { status: res.status, eventType, eventName })
        return
      }
      if (data.ignored_stale_sync && data.training_state) {
        const nextCaseId = typeof data.case_id === 'number' ? data.case_id : Number(data.case_id)
        const serverUiState = (data.ui_state || (data.training_state as TrainingState).ui_state || {}) as UiState
        const serverSeq = Number(serverUiState.last_client_seq || 0)
        if (Number.isFinite(nextCaseId) && latestCaseIdRef.current === nextCaseId && serverSeq >= syncSeqRef.current) {
          applyTrainingSession(safeEmail, nextCaseId, data.training_state as TrainingState)
        }
      }
    } catch (err) {
      console.warn('VP training session sync network failure', err)
      return
    }
  }

  function mergeUiState(patch: Partial<UiState>) {
    setUiState((prev) => {
      const next: UiState = {
        ...prev,
        ...patch,
        stage_drafts: {
          ...(prev.stage_drafts || {}),
          ...(patch.stage_drafts || {}),
        },
      }
      latestUiStateRef.current = next
      return next
    })
  }

  function trackInteraction(eventName: string, payload?: Record<string, unknown>) {
    const nextUiState: UiState = {
      ...latestUiStateRef.current,
      selected_stage: selectedStage,
      active_curriculum_index: activeCurriculumIndex,
      show_case_archive: showCaseArchive,
      show_continue_from: showContinueFrom ?? '',
      preferred_llm: preferredLlm,
      current_device: currentDevice,
      desktop_os: desktopOs,
    }
    void syncSessionState('interaction', eventName, payload, nextUiState)
  }

  function updateStageDraft(stageKey: StageKey, draft: UiStageDraft) {
    const nextUiState: UiState = {
      ...latestUiStateRef.current,
      selected_stage: selectedStage,
      active_curriculum_index: activeCurriculumIndex,
      show_case_archive: showCaseArchive,
      show_continue_from: showContinueFrom ?? '',
      preferred_llm: preferredLlm,
      current_device: currentDevice,
      desktop_os: desktopOs,
      stage_drafts: {
        ...(latestUiStateRef.current.stage_drafts || {}),
        [stageKey]: draft,
      },
    }
    latestUiStateRef.current = nextUiState
    setUiState(nextUiState)
    void syncSessionState('draft', 'draft_changed', { stage: stageKey }, nextUiState)
  }

  useEffect(() => {
    const syncViewport = () => setIsMobile(window.innerWidth < 900)
    syncViewport()
    window.addEventListener('resize', syncViewport)
    return () => window.removeEventListener('resize', syncViewport)
  }, [])

  useEffect(() => {
    const savedEmail = embeddedMode
      ? resolveTrainingEmail(currentRole)
      : window.localStorage.getItem(VP_TRAINING_AUTH_EMAIL_KEY)
    if (savedEmail) {
      setAuthEmail(savedEmail)
      setIsAuthenticated(true)
      const savedToken = window.localStorage.getItem(VP_TRAINING_AUTH_TOKEN_KEY) || ''
      if (savedToken) setTrainingAuthToken(savedToken)
      if (!embeddedMode) {
        window.localStorage.setItem(VP_TRAINING_AUTH_EMAIL_KEY, savedEmail)
      }
      hydrateFromLocalCache(savedEmail)
    }
    if (!savedEmail) return
    const stored = window.localStorage.getItem(caseStorageKey(savedEmail))
    const parsed = stored == null ? null : Number(stored)
    void (async () => {
      const resumed = await resumeTrainingSession(savedEmail, parsed != null && Number.isFinite(parsed) && parsed >= 0 ? parsed : null, { silentError: true })
      if (resumed) return
      const existingCases = await loadCases(savedEmail, { silentError: true })
      for (const item of existingCases.filter((caseItem) => caseItem.has_training_state)) {
        const fallbackResumed = await resumeTrainingSession(savedEmail, item.case_id, { silentError: true })
        if (fallbackResumed) return
      }
    })()
  }, [])

  useEffect(() => {
    if (!embeddedMode || !currentRole) return
    const nextEmail = resolveTrainingEmail(currentRole)
    if (!nextEmail) return
    if (nextEmail === authEmail && isAuthenticated) return
    setAuthEmail(nextEmail)
    setIsAuthenticated(true)
    if (!embeddedMode) {
      const savedToken = window.localStorage.getItem(VP_TRAINING_AUTH_TOKEN_KEY) || ''
      if (savedToken) setTrainingAuthToken(savedToken)
    }
    setCaseId(null)
    setTrainingState(null)
    setUiState({})
    setCaseHistory([])
    setSelectedStage('day0')
    setShowCaseArchive(false)
    setShowContinueFrom(null)
    hydrateFromLocalCache(nextEmail)
    const stored = window.localStorage.getItem(caseStorageKey(nextEmail))
    const parsed = stored == null ? null : Number(stored)
    void (async () => {
      const resumed = await resumeTrainingSession(nextEmail, parsed != null && Number.isFinite(parsed) && parsed >= 0 ? parsed : null, { silentError: true })
      if (resumed) return
      const existingCases = await loadCases(nextEmail, { silentError: true })
      for (const item of existingCases.filter((caseItem) => caseItem.has_training_state)) {
        const fallbackResumed = await resumeTrainingSession(nextEmail, item.case_id, { silentError: true })
        if (fallbackResumed) return
      }
      await buildTrainingSlice(undefined, false, nextEmail, { silentError: true })
    })()
  }, [currentRole])

  useEffect(() => {
    if (isAuthenticated) void loadCases()
  }, [isAuthenticated, authEmail])

  useEffect(() => {
    if (!isAuthenticated) return
    const nextUiState: UiState = {
      ...latestUiStateRef.current,
      selected_stage: selectedStage,
      active_curriculum_index: activeCurriculumIndex,
      show_case_archive: showCaseArchive,
      show_continue_from: showContinueFrom || '',
      preferred_llm: preferredLlm,
      current_device: currentDevice,
      desktop_os: desktopOs,
    }
    latestUiStateRef.current = nextUiState
    setUiState(nextUiState)
    if (authEmail.trim() && caseId != null && trainingState) {
      persistSessionCache(authEmail.trim().toLowerCase(), caseId, trainingState, nextUiState)
    }
  }, [isAuthenticated, selectedStage, activeCurriculumIndex, showCaseArchive, showContinueFrom, preferredLlm, currentDevice, desktopOs, authEmail, caseId, trainingState])

  const stage = selectedStage === 'day0' ? trainingState?.day0 : trainingState?.day1
  const day0Completed = Boolean(trainingState?.day0?.completed)
  const stageOrder: StageKey[] = day0Completed ? ['day0', 'day1'] : ['day0']
  const currentIndex = stageOrder.indexOf(selectedStage)
  const nextStage = currentIndex >= 0 && currentIndex < stageOrder.length - 1 ? stageOrder[currentIndex + 1] : null

  useEffect(() => {
    const count = stage?.schedule_blocks?.length || 0
    setActiveCurriculumIndex(curriculumActiveIndex(selectedStage, stage?.blocked_at_step, stage?.completed, count))
  }, [selectedStage, stage?.blocked_at_step, stage?.completed, stage?.schedule_blocks?.length])

  useEffect(() => {
    const count = stage?.schedule_blocks?.length || 0
    if (!count) return

    let frame = 0
    const anchorY = isMobile ? 96 : 128

    const syncCurriculumFromScroll = () => {
      frame = 0
      if (Date.now() < curriculumScrollLockUntilRef.current) return
      let nextIndex = 0
      for (let index = 0; index < count; index += 1) {
        const block = document.getElementById(curriculumDetailBlockId(selectedStage, index))
          || document.getElementById(curriculumBlockId(selectedStage, index))
        if (!block) continue
        if (block.getBoundingClientRect().top <= anchorY) nextIndex = index
      }

      setActiveCurriculumIndex((prev) => {
        if (prev === nextIndex) return prev
        window.setTimeout(() => {
          scrollCurriculumNavItemIntoView(selectedStage, nextIndex)
        }, 0)
        return nextIndex
      })
    }

    const animateNavigatorOffset = () => {
      navigatorAnimationFrameRef.current = 0
      const node = navigatorRef.current
      if (!node) return
      const current = navigatorDisplayOffsetRef.current
      const target = navigatorTargetOffsetRef.current
      const next = current + (target - current) * 0.16
      navigatorDisplayOffsetRef.current = Math.abs(target - next) < 0.5 ? target : next
      node.style.transform = isMobile ? '' : `translate3d(0, ${navigatorDisplayOffsetRef.current}px, 0)`
      if (Math.abs(target - navigatorDisplayOffsetRef.current) >= 0.5) {
        navigatorAnimationFrameRef.current = window.requestAnimationFrame(animateNavigatorOffset)
      }
    }

    const updateNavigatorTarget = () => {
      if (isMobile) {
        navigatorTargetOffsetRef.current = 0
        navigatorDisplayOffsetRef.current = 0
        if (navigatorRef.current) navigatorRef.current.style.transform = ''
        return
      }
      const pageScrollable = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
      const navigatorScrollable = Math.max(0, document.documentElement.scrollHeight - (navigatorRef.current?.offsetHeight || 0) - 48)
      const maxOffset = Math.max(0, Math.min(pageScrollable, navigatorScrollable))
      navigatorTargetOffsetRef.current = Math.max(0, Math.min(maxOffset, observedContentScrollTopRef.current))
      if (!navigatorAnimationFrameRef.current) {
        navigatorAnimationFrameRef.current = window.requestAnimationFrame(animateNavigatorOffset)
      }
    }

    const scheduleSync = (event?: Event) => {
      const target = event?.target as Element | Document | null
      const targetScrollTop = target && 'scrollTop' in target ? Number((target as Element).scrollTop || 0) : 0
      observedContentScrollTopRef.current = Math.max(window.scrollY || 0, document.documentElement.scrollTop || 0, targetScrollTop)
      if (frame) return
      frame = window.requestAnimationFrame(() => {
        updateNavigatorTarget()
        syncCurriculumFromScroll()
      })
    }

    const documentScrollOptions: AddEventListenerOptions = { capture: true, passive: true }
    window.addEventListener('scroll', scheduleSync, { passive: true })
    document.addEventListener('scroll', scheduleSync, documentScrollOptions)
    window.addEventListener('resize', scheduleSync)
    scheduleSync()
    return () => {
      window.removeEventListener('scroll', scheduleSync)
      document.removeEventListener('scroll', scheduleSync, true)
      window.removeEventListener('resize', scheduleSync)
      if (frame) window.cancelAnimationFrame(frame)
      if (navigatorAnimationFrameRef.current) window.cancelAnimationFrame(navigatorAnimationFrameRef.current)
    }
  }, [selectedStage, stage?.schedule_blocks?.length, isMobile])

  let reminder: string | null = null
  if (selectedStage === 'day1' && trainingState?.day0 && !trainingState.day0.completed) {
    reminder = 'Day 0의 첫 실행과 복붙 흐름이 아직 충분히 남지 않았습니다. 답이 잘 안 떠오르면 Day 0로 돌아가 첫 질문과 결과 저장부터 다시 연습하세요.'
  }
  if (selectedStage === 'day1' && trainingState?.day0?.completed && !(trainingState.day0.proof_artifact || '').trim()) {
    reminder = 'Day 0는 완료로 표시됐지만 남겨진 결과물이 거의 없습니다. 기억이 흐리면 Day 0의 샘플 파일을 다시 열어 복습하는 편이 좋습니다.'
  }

  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: isMobile ? '10px 10px 32px' : '12px 12px 40px', color: C.ink }}>
      <div style={{ display: 'grid', gap: 16 }}>
        <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: isMobile ? 20 : 26, padding: isMobile ? 16 : 22 }}>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'minmax(0, 1.2fr) minmax(280px, 0.8fr)', gap: isMobile ? 14 : 18, alignItems: 'center' }}>
            <div style={{ display: 'grid', gap: 12 }}>
              <div style={{ fontSize: '.8rem', color: C.accent, fontWeight: 900, letterSpacing: '.08em' }}>AI TRAINING CENTER</div>
              <p style={{ margin: 0, color: C.muted, lineHeight: isMobile ? 1.65 : 1.75, fontSize: isMobile ? '.95rem' : '1rem' }}>
                본 화면은 명확한 목표를 향해 부대표님을 체계적으로 성장시키는 실전 훈련 플로우입니다. 일상적인 AI 활용의 기초 단계에서 출발하여, 궁극적으로 전문가 수준의 고도화된 AI 운용 역량을 갖추는 것을 목표로 합니다.
              </p>
            </div>
            <div style={{ maxWidth: isMobile ? '100%' : undefined }}>
              <TrainingHeroVisual />
            </div>
          </div>
        </section>

        <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: isMobile ? 20 : 24, padding: isMobile ? 14 : 18, display: 'grid', gap: 14 }}>
          {!embeddedMode && !isAuthenticated && (
            <div style={{ display: 'grid', gap: 12, paddingBottom: 12, borderBottom: `1px solid ${C.border}` }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" onClick={() => setAuthMode('login')} style={{ background: authMode === 'login' ? '#111827' : C.bg, color: authMode === 'login' ? '#fff' : C.ink, border: `1px solid ${C.border}`, borderRadius: 12, padding: '10px 12px', fontWeight: 800, cursor: 'pointer' }}>
                  로그인
                </button>
                <button type="button" onClick={() => setAuthMode('register')} style={{ background: authMode === 'register' ? '#111827' : C.bg, color: authMode === 'register' ? '#fff' : C.ink, border: `1px solid ${C.border}`, borderRadius: 12, padding: '10px 12px', fontWeight: 800, cursor: 'pointer' }}>
                  회원가입
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
                <label style={{ display: 'grid', gap: 6 }}>
                  <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>이메일</span>
                  <input value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem' }} />
                </label>
                <label style={{ display: 'grid', gap: 6 }}>
                  <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>비밀번호</span>
                  <input type="password" value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem' }} />
                </label>
                {authMode === 'register' && (
                  <label style={{ display: 'grid', gap: 6 }}>
                    <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>이름</span>
                    <input value={authName} onChange={(e) => setAuthName(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem' }} />
                  </label>
                )}
              </div>
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>사용할 AI</span>
              <select value={preferredLlm} onChange={(e) => {
                setPreferredLlm(e.target.value)
                trackInteraction('preferred_llm_changed', { value: e.target.value })
              }} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="gpt">ChatGPT</option>
                <option value="claude">Claude</option>
                <option value="gemini">Gemini</option>
                <option value="local">로컬 모델</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>현재 모바일 기기</span>
              <select value={currentDevice} onChange={(e) => {
                setCurrentDevice(e.target.value)
                trackInteraction('current_device_changed', { value: e.target.value })
              }} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="android">Android</option>
                <option value="iphone">iPhone</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>PC / Mac 경로</span>
              <select value={desktopOs} onChange={(e) => {
                setDesktopOs(e.target.value)
                trackInteraction('desktop_os_changed', { value: e.target.value })
              }} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="windows">Windows PC</option>
                <option value="mac">Mac</option>
              </select>
            </label>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', flexDirection: isMobile ? 'column' : 'row' }}>
            {!embeddedMode && !isAuthenticated ? (
              <button type="button" onClick={() => void submitAuth()} disabled={authLoading} style={{ width: isMobile ? '100%' : undefined, background: '#111827', color: '#fff', border: 'none', borderRadius: 14, padding: '12px 16px', fontWeight: 800, cursor: authLoading ? 'wait' : 'pointer' }}>
                {authLoading ? '처리 중…' : authMode === 'login' ? '로그인' : '회원가입'}
              </button>
            ) : (
              <>
                <button type="button" onClick={() => void (trainingState ? resumeTrainingSession(authEmail, caseId) : buildTrainingSlice(caseId, false))} disabled={loading || resettingCases} style={{ width: isMobile ? '100%' : undefined, background: '#111827', color: '#fff', border: 'none', borderRadius: 14, padding: '12px 16px', fontWeight: 800, cursor: loading || resettingCases ? 'wait' : 'pointer' }}>
                  {loading ? '불러오는 중…' : trainingState ? 'VP AI 훈련 이어서 하기' : 'VP AI 훈련 시작'}
                </button>
                <button type="button" onClick={() => void buildTrainingSlice(undefined, true)} disabled={loading || resettingCases} style={{ width: isMobile ? '100%' : undefined, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: '12px 14px', fontWeight: 800, cursor: loading || resettingCases ? 'wait' : 'pointer' }}>
                  새 케이스로 다시 시작
                </button>
                {hasStoredCases && (
                  <button type="button" onClick={() => void resetAllCases()} disabled={loading || resettingCases} style={{ width: isMobile ? '100%' : undefined, background: '#fee2e2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: 14, padding: '12px 14px', fontWeight: 800, cursor: loading || resettingCases ? 'wait' : 'pointer' }}>
                    {resettingCases ? '전체 초기화 중…' : '전체 초기화'}
                  </button>
                )}
                {!embeddedMode && (
                  <button type="button" onClick={logoutTrainingAccount} style={{ width: isMobile ? '100%' : undefined, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: '12px 14px', fontWeight: 800, cursor: 'pointer' }}>
                    다른 계정으로 전환
                  </button>
                )}
              </>
            )}
            {isAuthenticated && hasCaseHistory && (
              <button type="button" onClick={() => {
                const next = !showCaseArchive
                setShowCaseArchive(next)
                mergeUiState({ show_case_archive: next })
                trackInteraction('toggle_case_archive', { visible: next })
                if (next) void loadCases()
              }} style={{ width: isMobile ? '100%' : undefined, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: '12px 14px', fontWeight: 800, cursor: 'pointer' }}>
                {showCaseArchive ? '과거 케이스 숨기기' : '과거 케이스 보기'}
              </button>
            )}
          </div>
          {error && <div style={{ color: '#b91c1c', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12, padding: 12, fontSize: '.9rem' }}>{error}</div>}
        </section>

        {isAuthenticated && showCaseArchive && !!archivedCases.length && (
          <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 24, padding: 18, display: 'grid', gap: 12 }}>
            <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>과거 케이스</div>
            <div style={{ display: 'grid', gap: 10 }}>
              {archivedCases.map((item) => (
                <div key={item.case_id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14, display: 'grid', gap: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
                    <div style={{ fontWeight: 800, color: C.ink }}>{item.case_label || `케이스 ${item.case_id}`}</div>
                    <div style={{ color: C.faint, fontSize: '.84rem' }}>{item.updated_at || ''}</div>
                  </div>
                  {progressBar(item.progress_pct)}
                  <div style={{ color: C.muted, fontSize: '.86rem' }}>진행률 {item.progress_pct}%</div>
                  <button type="button" onClick={() => void resumeTrainingSession(authEmail, item.case_id)} style={{ justifySelf: 'start', background: C.accent, color: '#fff', border: 'none', borderRadius: 12, padding: '10px 12px', fontWeight: 800, cursor: 'pointer' }}>
                    이 케이스 이어서 보기
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {isAuthenticated && trainingState && (
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'minmax(250px, 300px) minmax(0, 1fr)', gap: 16, alignItems: 'start' }}>
            <aside ref={navigatorRef} style={{ display: 'grid', gap: 14, position: 'sticky', top: isMobile ? 8 : 12, alignSelf: 'start', maxHeight: isMobile ? 'calc(100dvh - 16px)' : 'calc(100dvh - 24px)', overflowY: 'auto', zIndex: 4, order: isMobile ? 0 : 0, paddingRight: isMobile ? 0 : 2, willChange: 'transform' }}>
              <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 22, padding: 16, display: 'grid', gap: 12 }}>
                <div style={{ fontSize: '.82rem', color: C.muted, fontWeight: 900 }}>FLOW MENU</div>
                <div style={{ color: C.ink, fontWeight: 800 }}>전체 진행률 {trainingState.progress?.pct ?? 0}%</div>
                {progressBar(trainingState.progress?.pct ?? 0)}
                <div style={{ color: C.faint, fontSize: '.84rem' }}>case_id: {caseId} · 진행 내용은 자동 저장되어 언제든 다시 불러올 수 있습니다.</div>
                {(trainingState.flow_outline || []).map((item) => (
                  stageOrder.includes(item.key) ? <button
                    key={item.key}
                    type="button"
                    onClick={() => {
                      setSelectedStage(item.key)
                      setShowContinueFrom(null)
                      mergeUiState({ selected_stage: item.key, show_continue_from: '' })
                      trackInteraction('select_day', { day: item.key })
                    }}
                    style={{
                      textAlign: 'left',
                      border: selectedStage === item.key ? `2px solid ${C.accent}` : `1px solid ${C.border}`,
                      background: selectedStage === item.key ? C.accentSoft : C.bg,
                      borderRadius: 16,
                      padding: 14,
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontWeight: 900, color: C.ink }}>{item.label}</div>
                    <div style={{ color: C.muted, fontSize: '.88rem', lineHeight: 1.45, marginTop: 4 }}>{displayStageTitle(item.title)}</div>
                    <div style={{ color: C.faint, fontSize: '.8rem', marginTop: 6 }}>{item.completed ? '완료됨' : '복습 가능'} · {item.pct}%</div>
                  </button> : null
                ))}
              </section>

              {!!stage?.schedule_blocks?.length && (
                <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 22, padding: 16, display: 'grid', gap: 12 }}>
                  <div style={{ fontSize: '.82rem', color: C.muted, fontWeight: 900 }}>{selectedStage === 'day0' ? 'DAY 0 목차' : 'DAY 1 목차'}</div>
                  <div style={{ display: 'grid', gap: 8, paddingRight: isMobile ? undefined : 2 }}>
                    {stage.schedule_blocks.map((item, index) => (
                      <button
                        id={curriculumNavId(selectedStage, index)}
                        key={`${item.title}-${index}`}
                        type="button"
                        onClick={() => {
                          curriculumScrollLockUntilRef.current = Date.now() + 900
                          setActiveCurriculumIndex(index)
                          mergeUiState({ active_curriculum_index: index })
                          trackInteraction('select_curriculum_block', { index, day: selectedStage })
                          window.requestAnimationFrame(() => {
                            window.requestAnimationFrame(() => {
                              scrollCurriculumBlockToTop(selectedStage, index)
                            })
                          })
                        }}
                        style={{
                          textAlign: 'left',
                          border: index === activeCurriculumIndex ? `2px solid ${C.accent}` : `1px solid ${C.border}`,
                          background: index === activeCurriculumIndex ? C.accentSoft : C.bg,
                          borderRadius: 14,
                          padding: 12,
                          cursor: 'pointer',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                          <div style={{ fontWeight: 800, color: C.ink }}>{index + 1}. {item.title}</div>
                          <div style={{ fontSize: '.78rem', color: index === activeCurriculumIndex ? C.accent : C.faint, fontWeight: 800 }}>{item.minutes}분</div>
                        </div>
                        <div style={{ color: C.muted, fontSize: '.84rem', lineHeight: 1.45, marginTop: 4 }}>{item.goal}</div>
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {trainingState.persona_library?.unlocked && (
                <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 22, padding: 16, display: 'grid', gap: 12 }}>
                  <div style={{ fontSize: '.82rem', color: C.muted, fontWeight: 900 }}>PERSONA LIBRARY</div>
                  <div style={{ color: C.ink, fontWeight: 800 }}>현재 코어 페르소나: 주부/학부모</div>
                  <div style={{ color: C.muted, fontSize: '.88rem', lineHeight: 1.55 }}>
                    {trainingState.persona_library?.unlock_rule}
                  </div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    {(trainingState.persona_library?.personas || []).map((item) => (
                      <div key={item.key} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                          <div style={{ fontWeight: 800, color: C.ink }}>{item.label}</div>
                          <div style={{ fontSize: '.76rem', color: C.accent, fontWeight: 800 }}>
                            추가 학습 가능
                          </div>
                        </div>
                        <div style={{ color: C.faint, fontSize: '.8rem', marginTop: 4 }}>{item.group}</div>
                        <div style={{ color: C.muted, fontSize: '.88rem', lineHeight: 1.5, marginTop: 6 }}>{item.description}</div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </aside>

            <div style={{ order: isMobile ? 1 : 1 }}>
              <StageCard
                stage={stage}
                stageKey={selectedStage}
                draft={uiState.stage_drafts?.[selectedStage]}
                onSave={saveStage}
                onSaveFeedback={saveFeedback}
                onDraftChange={updateStageDraft}
                onInteraction={trackInteraction}
                onContinue={() => {
                  if (nextStage) {
                    setSelectedStage(nextStage)
                    setShowContinueFrom(null)
                    mergeUiState({ selected_stage: nextStage, show_continue_from: '' })
                    trackInteraction('stage_continue', { next_stage: nextStage })
                  }
                }}
                saving={savingStage === selectedStage}
                feedbackSaving={savingFeedbackStage === selectedStage}
                apiBase={apiBase}
                authHeaders={authHeaders}
                showContinue={showContinueFrom === selectedStage && Boolean(nextStage)}
                reminder={reminder}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
