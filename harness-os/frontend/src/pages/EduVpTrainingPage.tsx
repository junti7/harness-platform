import { useEffect, useState } from 'react'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
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

type LearningLink = {
  title: string
  url: string
  source_kind: string
}

type TrainingStage = {
  title?: string
  required_action?: string
  proof_artifact_hint?: string
  pass_fail_rubric?: string[]
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
  key: 'week0' | 'week1'
  label: string
  title: string
  completed: boolean
  pct: number
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
  week0?: TrainingStage
  week1?: TrainingStage
}

type CaseItem = {
  case_id: number
  status?: string
  updated_at?: string
  progress_pct: number
  flow_outline?: FlowItem[]
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

function FlowIllustration() {
  return (
    <svg viewBox="0 0 520 120" style={{ width: '100%', height: 'auto', display: 'block' }} aria-hidden="true">
      <rect x="0" y="0" width="520" height="120" rx="22" fill="#fff7ed" />
      <circle cx="58" cy="60" r="22" fill="#111827" />
      <text x="49" y="67" fill="#fff" fontSize="18" fontWeight="700">D0</text>
      <path d="M84 60 H222" stroke="#fdba74" strokeWidth="8" strokeLinecap="round" />
      <circle cx="260" cy="60" r="22" fill="#0f766e" />
      <text x="251" y="67" fill="#fff" fontSize="18" fontWeight="700">D1</text>
      <path d="M286 60 H430" stroke="#fdba74" strokeWidth="8" strokeLinecap="round" />
      <rect x="438" y="38" width="46" height="44" rx="12" fill="#ffffff" stroke="#dbe4ee" strokeWidth="2" />
      <text x="445" y="66" fill="#111827" fontSize="15" fontWeight="700">END</text>
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

function StageCard({
  stage,
  stageKey,
  onSave,
  onSaveFeedback,
  onContinue,
  saving,
  feedbackSaving,
  apiBase,
  authHeaders,
  showContinue,
  reminder,
}: {
  stage: TrainingStage | undefined
  stageKey: 'week0' | 'week1'
  onSave: (stageKey: 'week0' | 'week1', payload: { proof_artifact: string; blocked_at_step: string; notes: string; completed: boolean }) => void
  onSaveFeedback: (stageKey: 'week0' | 'week1', payload: { empathy_score: number; clarity_score: number; motivation_score: number; biggest_blocker: string; freeform_feedback: string }) => void
  onContinue: () => void
  saving: boolean
  feedbackSaving: boolean
  apiBase: string
  authHeaders: () => Record<string, string>
  showContinue: boolean
  reminder?: string | null
}) {
  const [proof, setProof] = useState(stage?.proof_artifact || '')
  const [blocked, setBlocked] = useState(stage?.blocked_at_step || '')
  const [notes, setNotes] = useState(stage?.notes || '')
  const [completed, setCompleted] = useState(Boolean(stage?.completed))
  const [empathyScore, setEmpathyScore] = useState(stage?.vp_feedback?.empathy_score || 3)
  const [clarityScore, setClarityScore] = useState(stage?.vp_feedback?.clarity_score || 3)
  const [motivationScore, setMotivationScore] = useState(stage?.vp_feedback?.motivation_score || 3)
  const [biggestBlocker, setBiggestBlocker] = useState(stage?.vp_feedback?.biggest_blocker || '')
  const [freeformFeedback, setFreeformFeedback] = useState(stage?.vp_feedback?.freeform_feedback || '')

  useEffect(() => {
    setProof(stage?.proof_artifact || '')
    setBlocked(stage?.blocked_at_step || '')
    setNotes(stage?.notes || '')
    setCompleted(Boolean(stage?.completed))
    setEmpathyScore(stage?.vp_feedback?.empathy_score || 3)
    setClarityScore(stage?.vp_feedback?.clarity_score || 3)
    setMotivationScore(stage?.vp_feedback?.motivation_score || 3)
    setBiggestBlocker(stage?.vp_feedback?.biggest_blocker || '')
    setFreeformFeedback(stage?.vp_feedback?.freeform_feedback || '')
  }, [stageKey, stage])

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
    <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 24, padding: 20, display: 'grid', gap: 16 }}>
      <div>
        <div style={{ fontSize: '.82rem', color: C.accent, fontWeight: 900, letterSpacing: '.05em', marginBottom: 6 }}>{stageKey === 'week0' ? 'DAY 0' : 'DAY 1'}</div>
        <h2 style={{ margin: 0, fontSize: '1.55rem', lineHeight: 1.3, color: '#000000' }}>{stage?.title || '준비 중'}</h2>
      </div>

      {reminder && (
        <div style={{ background: C.warnSoft, border: '1px solid #fdba74', borderRadius: 16, padding: 14, color: C.ink, lineHeight: 1.55 }}>
          <strong style={{ display: 'block', marginBottom: 4 }}>복습 제안</strong>
          {reminder}
        </div>
      )}

      {stage?.required_action && (
        <div style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, borderRadius: 16, padding: 14 }}>
          <div style={{ fontSize: '.76rem', color: C.accent, fontWeight: 800, marginBottom: 6 }}>오늘 바로 해야 할 일</div>
          <div style={{ fontSize: '1rem', lineHeight: 1.65, color: C.ink, fontWeight: 700 }}>{stage.required_action}</div>
        </div>
      )}

      <FlowIllustration />

      {!!stage?.tutorial_steps?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>튜토리얼</div>
          {stage.tutorial_steps.map((item, index) => (
            <div key={item.id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontWeight: 800, color: C.ink, marginBottom: 4 }}>{index + 1}. {item.title}</div>
              <div style={{ color: C.muted, fontSize: '.95rem', lineHeight: 1.6 }}>{item.body}</div>
            </div>
          ))}
        </div>
      )}

      {!!stage?.checklist?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
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
              <button type="button" onClick={() => void downloadKit(item.download_url, item.kit_id)} style={{ justifySelf: 'start', background: '#111827', color: '#fff', border: 'none', borderRadius: 12, padding: '11px 14px', fontWeight: 800, cursor: 'pointer' }}>
                샘플 파일 내려받기
              </button>
            </div>
          ))}
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
          <textarea value={proof} onChange={(e) => setProof(e.target.value)} rows={5} placeholder={stage?.proof_artifact_hint || '실제로 만든 결과를 붙여 넣으세요.'} style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>어디서 막혔나</span>
          <select value={blocked} onChange={(e) => setBlocked(e.target.value)} style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', fontFamily: 'inherit', background: C.surface, boxSizing: 'border-box' }}>
            <option value="">막힌 단계 없음</option>
            {(stage?.blocked_step_options || []).map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>메모</span>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="어디서 이해가 잘 됐고, 어디서 막혔는지 적으세요." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: C.ink, fontSize: '.9rem', fontWeight: 700 }}>
          <input type="checkbox" checked={completed} onChange={(e) => setCompleted(e.target.checked)} />
          이 단계는 실제로 끝까지 해봤다
        </label>

        <button onClick={() => onSave(stageKey, { proof_artifact: proof, blocked_at_step: blocked, notes, completed })} disabled={saving} style={{ background: saving ? '#cbd5e1' : '#111827', color: '#fff', border: 'none', borderRadius: 14, padding: '13px 16px', fontSize: '.95rem', fontWeight: 800, cursor: saving ? 'wait' : 'pointer' }}>
          {saving ? '저장 중…' : '이 단계 저장'}
        </button>

        {showContinue && (
          <div style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, borderRadius: 16, padding: 14, display: 'grid', gap: 10 }}>
            <div style={{ color: C.ink, fontWeight: 800 }}>이어서 다음 단계로 진행할까요?</div>
            <button type="button" onClick={onContinue} style={{ justifySelf: 'start', background: C.accent, color: '#fff', border: 'none', borderRadius: 12, padding: '11px 14px', fontWeight: 800, cursor: 'pointer' }}>
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
            <select value={empathyScore} onChange={(e) => setEmpathyScore(Number(e.target.value))} style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 10, background: C.surface }}>
              {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
            </select>
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.82rem', color: C.muted, fontWeight: 700 }}>명확성</span>
            <select value={clarityScore} onChange={(e) => setClarityScore(Number(e.target.value))} style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 10, background: C.surface }}>
              {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
            </select>
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.82rem', color: C.muted, fontWeight: 700 }}>학습욕구</span>
            <select value={motivationScore} onChange={(e) => setMotivationScore(Number(e.target.value))} style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 10, background: C.surface }}>
              {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
            </select>
          </label>
        </div>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>가장 크게 막힌 지점</span>
          <input value={biggestBlocker} onChange={(e) => setBiggestBlocker(e.target.value)} placeholder="예: 파일을 어디서 열어야 하는지 처음엔 헷갈렸음" style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }} />
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>자유 피드백</span>
          <textarea value={freeformFeedback} onChange={(e) => setFreeformFeedback(e.target.value)} rows={4} placeholder="무엇이 좋았는지, 무엇이 어렵거나 피상적으로 느껴졌는지 적으세요." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </label>

        <button onClick={() => onSaveFeedback(stageKey, { empathy_score: empathyScore, clarity_score: clarityScore, motivation_score: motivationScore, biggest_blocker: biggestBlocker, freeform_feedback: freeformFeedback })} disabled={feedbackSaving} style={{ background: feedbackSaving ? '#cbd5e1' : C.accent, color: '#fff', border: 'none', borderRadius: 14, padding: '13px 16px', fontSize: '.95rem', fontWeight: 800, cursor: feedbackSaving ? 'wait' : 'pointer' }}>
          {feedbackSaving ? '피드백 저장 중…' : 'VP 피드백 저장'}
        </button>
        {stage?.vp_feedback?.submitted_at && <div style={{ fontSize: '.8rem', color: C.faint }}>최근 저장: {stage.vp_feedback.submitted_at}</div>}
      </div>
    </section>
  )
}

export function EduVpTrainingPage({ apiBase, authHeaders }: Props) {
  const [email, setEmail] = useState('')
  const [preferredLlm, setPreferredLlm] = useState('gpt')
  const [currentDevice, setCurrentDevice] = useState('android')
  const [desktopOs, setDesktopOs] = useState('windows')
  const [aiExperience, setAiExperience] = useState('beginner')
  const [biggestFriction, setBiggestFriction] = useState('')
  const [learningGoal, setLearningGoal] = useState('')
  const [forceNew, setForceNew] = useState(true)
  const [loading, setLoading] = useState(false)
  const [savingStage, setSavingStage] = useState<'week0' | 'week1' | null>(null)
  const [savingFeedbackStage, setSavingFeedbackStage] = useState<'week0' | 'week1' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [caseId, setCaseId] = useState<number | null>(null)
  const [trainingState, setTrainingState] = useState<TrainingState | null>(null)
  const [caseHistory, setCaseHistory] = useState<CaseItem[]>([])
  const [selectedStage, setSelectedStage] = useState<'week0' | 'week1'>('week0')
  const [showContinueFrom, setShowContinueFrom] = useState<'week0' | 'week1' | null>(null)

  async function loadCases(targetEmail: string) {
    if (!targetEmail.trim()) return
    const res = await fetch(`${apiBase}/api/edu/vp-training/cases?email=${encodeURIComponent(targetEmail.trim())}`, {
      headers: { ...authHeaders() },
    })
    const data = await res.json()
    if (res.ok) setCaseHistory(data.cases || [])
  }

  async function buildTrainingSlice(targetCaseId?: number | null, restart?: boolean) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          case_id: targetCaseId ?? caseId,
          email,
          preferred_llm: preferredLlm,
          current_device: currentDevice,
          desktop_os: desktopOs,
          ai_experience: aiExperience,
          biggest_friction: biggestFriction,
          learning_goal: learningGoal,
          force_new: restart ?? forceNew,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setCaseId(data.case_id)
      setTrainingState(data.training_state || null)
      setSelectedStage('week0')
      await loadCases(email)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'VP training flow build failed')
    } finally {
      setLoading(false)
    }
  }

  async function saveStage(stage: 'week0' | 'week1', payload: { proof_artifact: string; blocked_at_step: string; notes: string; completed: boolean }) {
    if (!caseId) return
    setSavingStage(stage)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/artifact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ case_id: caseId, stage, ...payload }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setTrainingState(data.training_state || null)
      setShowContinueFrom(stage)
      await loadCases(email)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'stage save failed')
    } finally {
      setSavingStage(null)
    }
  }

  async function saveFeedback(stage: 'week0' | 'week1', payload: { empathy_score: number; clarity_score: number; motivation_score: number; biggest_blocker: string; freeform_feedback: string }) {
    if (!caseId) return
    setSavingFeedbackStage(stage)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ case_id: caseId, stage, ...payload }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setTrainingState(data.training_state || null)
      await loadCases(email)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'feedback save failed')
    } finally {
      setSavingFeedbackStage(null)
    }
  }

  const stage = selectedStage === 'week0' ? trainingState?.week0 : trainingState?.week1
  const stageOrder: Array<'week0' | 'week1'> = ['week0', 'week1']
  const currentIndex = stageOrder.indexOf(selectedStage)
  const nextStage = currentIndex >= 0 && currentIndex < stageOrder.length - 1 ? stageOrder[currentIndex + 1] : null

  let reminder: string | null = null
  if (selectedStage === 'week1' && trainingState?.week0 && !trainingState.week0.completed) {
    reminder = 'Day 0의 첫 실행과 복붙 흐름이 아직 충분히 남지 않았습니다. 답이 잘 안 떠오르면 Day 0로 돌아가 첫 질문과 결과 저장부터 다시 연습하세요.'
  }
  if (selectedStage === 'week1' && trainingState?.week0?.completed && !(trainingState.week0.proof_artifact || '').trim()) {
    reminder = 'Day 0는 완료로 표시됐지만 남겨진 결과물이 거의 없습니다. 기억이 흐리면 Day 0의 샘플 파일을 다시 열어 복습하는 편이 좋습니다.'
  }

  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: '12px 12px 40px', color: C.ink }}>
      <div style={{ display: 'grid', gap: 16 }}>
        <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 26, padding: 22 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(280px, 0.8fr)', gap: 18, alignItems: 'center' }}>
            <div style={{ display: 'grid', gap: 12 }}>
              <div style={{ fontSize: '.8rem', color: C.accent, fontWeight: 900, letterSpacing: '.08em' }}>VP TRAINING CENTER</div>
              <h1 style={{ margin: 0, fontSize: '1.8rem', lineHeight: 1.25, color: '#000000' }}>VP AI 훈련</h1>
              <p style={{ margin: 0, color: C.muted, lineHeight: 1.75, fontSize: '1rem' }}>
                본 화면은 명확한 목표를 향해 부대표님을 체계적으로 성장시키는 실전 훈련 플로우입니다. 일상적인 AI 활용의 기초 단계에서 출발하여, 궁극적으로 전문가 수준의 고도화된 AI 운용 역량을 갖추는 것을 목표로 합니다.
              </p>
              {trainingState?.program_objective && (
                <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14, fontSize: '.92rem', lineHeight: 1.6 }}>
                  <strong style={{ display: 'block', marginBottom: 4 }}>현재 고정 목표</strong>
                  {trainingState.program_objective}
                </div>
              )}
            </div>
            <TrainingHeroVisual />
          </div>
        </section>

        <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 24, padding: 18, display: 'grid', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>이메일</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem' }} />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>Primary LLM</span>
              <select value={preferredLlm} onChange={(e) => setPreferredLlm(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="gpt">ChatGPT</option>
                <option value="claude">Claude</option>
                <option value="gemini">Gemini</option>
                <option value="local">로컬 모델</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>현재 모바일 기기</span>
              <select value={currentDevice} onChange={(e) => setCurrentDevice(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="android">Android</option>
                <option value="iphone">iPhone</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>PC / Mac 경로</span>
              <select value={desktopOs} onChange={(e) => setDesktopOs(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="windows">Windows PC</option>
                <option value="mac">Mac</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>현재 수준</span>
              <select value={aiExperience} onChange={(e) => setAiExperience(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="beginner">완전 초보</option>
                <option value="light">가끔 써봄</option>
                <option value="weekly">주 1회 이상</option>
              </select>
            </label>
          </div>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>지금 제일 막히는 지점</span>
            <textarea value={biggestFriction} onChange={(e) => setBiggestFriction(e.target.value)} rows={3} placeholder="예: 무엇을 시켜야 할지 감이 안 오고, 영어처럼 보이면 바로 겁이 납니다." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', lineHeight: 1.5, resize: 'vertical', boxSizing: 'border-box' }} />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>만들고 싶은 변화</span>
            <textarea value={learningGoal} onChange={(e) => setLearningGoal(e.target.value)} rows={3} placeholder="예: 답장 쓰기, 회의 메모 정리, 일정 정리 같은 일을 AI로 더 빨리 끝내고 싶습니다." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', lineHeight: 1.5, resize: 'vertical', boxSizing: 'border-box' }} />
          </label>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.92rem', fontWeight: 700 }}>
              <input type="checkbox" checked={forceNew} onChange={(e) => setForceNew(e.target.checked)} />
              새로운 케이스로 다시 시작
            </label>
            <button type="button" onClick={() => void loadCases(email)} disabled={!email.trim()} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: '12px 14px', fontWeight: 800, cursor: !email.trim() ? 'not-allowed' : 'pointer' }}>
              기존 케이스 불러오기
            </button>
            <button type="button" onClick={() => void buildTrainingSlice()} disabled={loading || !email.trim()} style={{ background: '#111827', color: '#fff', border: 'none', borderRadius: 14, padding: '12px 16px', fontWeight: 800, cursor: loading ? 'wait' : 'pointer' }}>
              {loading ? 'Day 플로우 생성 중…' : 'VP AI 훈련 시작'}
            </button>
          </div>
          {error && <div style={{ color: '#b91c1c', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12, padding: 12, fontSize: '.9rem' }}>{error}</div>}
        </section>

        {!!caseHistory.length && (
          <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 24, padding: 18, display: 'grid', gap: 12 }}>
            <div style={{ fontSize: '.9rem', color: C.muted, fontWeight: 900 }}>저장된 케이스</div>
            <div style={{ display: 'grid', gap: 10 }}>
              {caseHistory.map((item) => (
                <div key={item.case_id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 16, padding: 14, display: 'grid', gap: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
                    <div style={{ fontWeight: 800, color: C.ink }}>case #{item.case_id}</div>
                    <div style={{ color: C.faint, fontSize: '.84rem' }}>{item.updated_at || ''}</div>
                  </div>
                  {progressBar(item.progress_pct)}
                  <div style={{ color: C.muted, fontSize: '.86rem' }}>진행률 {item.progress_pct}%</div>
                  <button type="button" onClick={() => void buildTrainingSlice(item.case_id, false)} style={{ justifySelf: 'start', background: C.accent, color: '#fff', border: 'none', borderRadius: 12, padding: '10px 12px', fontWeight: 800, cursor: 'pointer' }}>
                    이 케이스 이어서 보기
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {trainingState && (
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(250px, 300px) minmax(0, 1fr)', gap: 16, alignItems: 'start' }}>
            <aside style={{ display: 'grid', gap: 14, position: 'sticky', top: 12 }}>
              <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 22, padding: 16, display: 'grid', gap: 12 }}>
                <div style={{ fontSize: '.82rem', color: C.muted, fontWeight: 900 }}>FLOW MENU</div>
                <div style={{ color: C.ink, fontWeight: 800 }}>전체 진행률 {trainingState.progress?.pct ?? 0}%</div>
                {progressBar(trainingState.progress?.pct ?? 0)}
                <div style={{ color: C.faint, fontSize: '.84rem' }}>case_id: {caseId} · 진행 내용은 자동 저장되어 언제든 다시 불러올 수 있습니다.</div>
                {(trainingState.flow_outline || []).map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => {
                      setSelectedStage(item.key)
                      setShowContinueFrom(null)
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
                    <div style={{ color: C.muted, fontSize: '.88rem', lineHeight: 1.45, marginTop: 4 }}>{item.title}</div>
                    <div style={{ color: C.faint, fontSize: '.8rem', marginTop: 6 }}>{item.completed ? '완료됨' : '복습 가능'} · {item.pct}%</div>
                  </button>
                ))}
              </section>

              <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 22, padding: 16, display: 'grid', gap: 12 }}>
                <div style={{ fontSize: '.82rem', color: C.muted, fontWeight: 900 }}>FLOW OVERVIEW</div>
                <FlowIllustration />
                <div style={{ color: C.muted, fontSize: '.9rem', lineHeight: 1.6 }}>
                  Duolingo처럼 지금 해야 할 1개 단계에만 집중하고, 필요하면 왼쪽 목차에서 언제든 이전 단계로 돌아가 다시 복습할 수 있게 설계했습니다.
                </div>
              </section>

              <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 22, padding: 16, display: 'grid', gap: 12 }}>
                <div style={{ fontSize: '.82rem', color: C.muted, fontWeight: 900 }}>PERSONA LIBRARY</div>
                <div style={{ color: C.ink, fontWeight: 800 }}>현재 코어 페르소나: 주부/학부모</div>
                <div style={{ color: C.muted, fontSize: '.88rem', lineHeight: 1.55 }}>
                  {trainingState.persona_library?.unlock_rule}
                </div>
                <div style={{ display: 'grid', gap: 8 }}>
                  {(trainingState.persona_library?.personas || []).map((item) => (
                    <div key={item.key} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, opacity: trainingState.persona_library?.unlocked ? 1 : 0.72 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                        <div style={{ fontWeight: 800, color: C.ink }}>{item.label}</div>
                        <div style={{ fontSize: '.76rem', color: trainingState.persona_library?.unlocked ? C.accent : C.faint, fontWeight: 800 }}>
                          {trainingState.persona_library?.unlocked ? '추가 학습 가능' : '코어 완료 후 오픈'}
                        </div>
                      </div>
                      <div style={{ color: C.faint, fontSize: '.8rem', marginTop: 4 }}>{item.group}</div>
                      <div style={{ color: C.muted, fontSize: '.88rem', lineHeight: 1.5, marginTop: 6 }}>{item.description}</div>
                    </div>
                  ))}
                </div>
              </section>
            </aside>

            <StageCard
              stage={stage}
              stageKey={selectedStage}
              onSave={saveStage}
              onSaveFeedback={saveFeedback}
              onContinue={() => {
                if (nextStage) {
                  setSelectedStage(nextStage)
                  setShowContinueFrom(null)
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
        )}
      </div>
    </div>
  )
}
