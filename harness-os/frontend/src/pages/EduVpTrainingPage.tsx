import { useState } from 'react'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

type TrainingStage = {
  title?: string
  required_action?: string
  proof_artifact_hint?: string
  pass_fail_rubric?: string[]
  sample_materials?: Array<{ kit_id: string; title: string; description: string; files: string[]; download_url: string }>
  blocked_step_options?: string[]
  checklist?: Array<{ id: string; title: string; instruction: string; success_signal: string }>
  practice_prompt_template?: string
  evidence_bundle_id?: string
  retrieval_mode?: string
  customer_facing_safe?: boolean
  fallback_used?: boolean
  external_reuse_safe?: boolean
  evidence_cards?: Array<{ title: string; source_kind: string; cite: string; snippet: string }>
  proof_artifact?: string
  blocked_at_step?: string
  notes?: string
  completed?: boolean
  vp_feedback?: {
    empathy_score?: number
    clarity_score?: number
    motivation_score?: number
    jargon_flag?: boolean
    biggest_blocker?: string
    freeform_feedback?: string
    submitted_at?: string
  }
}

type TrainingState = {
  program_objective?: string
  primary_llm_path?: string
  intake?: Record<string, string>
  week0?: TrainingStage
  week1?: TrainingStage
}

const CEO_REVIEW_POINTS = [
  '고정 목표가 흔들리지 않고 첫 화면에서 바로 보이는가',
  'Week 0이 설명이 아니라 실제 행동 4단계로 보이는가',
  'Week 1 장면이 VP 일상과 업무에 바로 닿는가',
  'proof artifact / blocked step / notes가 저장되는가',
  'RAG 근거가 비어 있더라도 retrieval mode가 투명하게 보이는가',
]

const C = {
  ink: '#0f172a',
  muted: '#475569',
  faint: '#64748b',
  accent: '#2563eb',
  accentSoft: '#dbeafe',
  surface: '#ffffff',
  border: '#dbe4ee',
  success: '#059669',
  successSoft: '#d1fae5',
  warn: '#d97706',
  warnSoft: '#fef3c7',
  bg: '#f8fafc',
}

function StageCard({
  title,
  stage,
  stageKey,
  onSave,
  onSaveFeedback,
  saving,
  feedbackSaving,
  apiBase,
  authHeaders,
}: {
  title: string
  stage: TrainingStage | undefined
  stageKey: 'week0' | 'week1'
  onSave: (stageKey: 'week0' | 'week1', payload: { proof_artifact: string; blocked_at_step: string; notes: string; completed: boolean }) => void
  onSaveFeedback: (stageKey: 'week0' | 'week1', payload: { empathy_score: number; clarity_score: number; motivation_score: number; jargon_flag: boolean; biggest_blocker: string; freeform_feedback: string }) => void
  saving: boolean
  feedbackSaving: boolean
  apiBase: string
  authHeaders: () => Record<string, string>
}) {
  const [proof, setProof] = useState(stage?.proof_artifact || '')
  const [blocked, setBlocked] = useState(stage?.blocked_at_step || '')
  const [notes, setNotes] = useState(stage?.notes || '')
  const [completed, setCompleted] = useState(Boolean(stage?.completed))
  const [empathyScore, setEmpathyScore] = useState(stage?.vp_feedback?.empathy_score || 3)
  const [clarityScore, setClarityScore] = useState(stage?.vp_feedback?.clarity_score || 3)
  const [motivationScore, setMotivationScore] = useState(stage?.vp_feedback?.motivation_score || 3)
  const [jargonFlag, setJargonFlag] = useState(Boolean(stage?.vp_feedback?.jargon_flag))
  const [biggestBlocker, setBiggestBlocker] = useState(stage?.vp_feedback?.biggest_blocker || '')
  const [freeformFeedback, setFreeformFeedback] = useState(stage?.vp_feedback?.freeform_feedback || '')

  async function downloadKit(downloadUrl: string, kitId: string) {
    const res = await fetch(`${apiBase}${downloadUrl}`, {
      headers: { ...authHeaders() },
    })
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
    <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 18, padding: 18, display: 'grid', gap: 14 }}>
      <div>
        <div style={{ fontSize: '.76rem', color: C.accent, fontWeight: 900, letterSpacing: '.04em', marginBottom: 6 }}>{title}</div>
        <h3 style={{ margin: 0, fontSize: '1.1rem', lineHeight: 1.35, color: C.ink }}>{stage?.title || '준비 중'}</h3>
      </div>

      {stage?.required_action && (
        <div style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, borderRadius: 14, padding: 14 }}>
          <div style={{ fontSize: '.74rem', color: C.accent, fontWeight: 800, marginBottom: 6 }}>이번 단계 목표</div>
          <div style={{ fontSize: '.95rem', lineHeight: 1.6, color: C.ink, fontWeight: 700 }}>{stage.required_action}</div>
        </div>
      )}

      {!!stage?.checklist?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.86rem', color: C.muted, fontWeight: 800 }}>실행 체크리스트</div>
          {stage.checklist.map((item) => (
            <div key={item.id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: 12 }}>
              <div style={{ fontWeight: 800, color: C.ink, marginBottom: 4 }}>{item.title}</div>
              <div style={{ color: C.muted, fontSize: '.9rem', lineHeight: 1.55 }}>{item.instruction}</div>
              <div style={{ color: C.faint, fontSize: '.8rem', lineHeight: 1.5, marginTop: 6 }}>잘 되면: {item.success_signal}</div>
            </div>
          ))}
        </div>
      )}

      {stage?.practice_prompt_template && (
        <div style={{ background: '#fefce8', border: `1px solid ${C.warn}`, borderRadius: 14, padding: 14 }}>
          <div style={{ fontSize: '.74rem', color: C.warn, fontWeight: 800, marginBottom: 6 }}>바로 써볼 프롬프트</div>
          <div style={{ fontSize: '.92rem', lineHeight: 1.6, color: C.ink, whiteSpace: 'pre-wrap' }}>{stage.practice_prompt_template}</div>
        </div>
      )}

      {!!stage?.sample_materials?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: '.86rem', color: C.muted, fontWeight: 800 }}>실전 교보재</div>
          {stage.sample_materials.map((item) => (
            <div key={item.kit_id} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, display: 'grid', gap: 8 }}>
              <div style={{ fontWeight: 800, color: C.ink }}>{item.title}</div>
              <div style={{ color: C.muted, fontSize: '.9rem', lineHeight: 1.55 }}>{item.description}</div>
              <div style={{ color: C.faint, fontSize: '.8rem', lineHeight: 1.5 }}>포함 파일: {item.files.join(', ')}</div>
              <div>
                <button
                  type="button"
                  onClick={() => void downloadKit(item.download_url, item.kit_id)}
                  style={{ display: 'inline-block', background: C.accent, color: '#fff', textDecoration: 'none', borderRadius: 12, padding: '10px 12px', fontSize: '.88rem', fontWeight: 800 }}
                >
                  샘플 파일 내려받기
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!!stage?.pass_fail_rubric?.length && (
        <div>
          <div style={{ fontSize: '.86rem', color: C.muted, fontWeight: 800, marginBottom: 8 }}>통과 기준</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {stage.pass_fail_rubric.map((item) => (
              <div key={item} style={{ fontSize: '.9rem', color: C.ink, lineHeight: 1.5, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: '8px 10px' }}>
                {item}
              </div>
            ))}
          </div>
        </div>
      )}

      {!!stage?.evidence_cards?.length && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
            <div style={{ fontSize: '.86rem', color: C.muted, fontWeight: 800 }}>Harness RAG 근거 묶음</div>
            <div style={{ fontSize: '.76rem', color: C.faint }}>
              mode={stage.retrieval_mode} · safe={String(stage.customer_facing_safe)} · fallback={String(stage.fallback_used)}
            </div>
          </div>
          {stage.evidence_cards.map((item, idx) => (
            <div key={`${item.title}-${idx}`} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 14, padding: 12 }}>
              <div style={{ fontWeight: 800, color: C.ink, marginBottom: 4 }}>{item.title}</div>
              <div style={{ fontSize: '.78rem', color: C.accent, marginBottom: 6 }}>{item.source_kind}</div>
              <div style={{ color: C.muted, fontSize: '.9rem', lineHeight: 1.55 }}>{item.snippet}</div>
              {item.cite && <div style={{ color: C.faint, fontSize: '.78rem', lineHeight: 1.5, marginTop: 6 }}>{item.cite}</div>}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gap: 10 }}>
        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>증거 결과물</span>
          <textarea
            value={proof}
            onChange={(e) => setProof(e.target.value)}
            rows={5}
            placeholder={stage?.proof_artifact_hint || '실제로 만든 결과를 붙여 넣으세요.'}
            style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }}
          />
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>어디서 막혔나</span>
          <select
            value={blocked}
            onChange={(e) => setBlocked(e.target.value)}
            style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', fontFamily: 'inherit', background: C.surface, boxSizing: 'border-box' }}
          >
            <option value="">막힌 단계 없음</option>
            {(stage?.blocked_step_options || []).map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>

        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>메모</span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="어려웠던 표현, 감정적으로 걸렸던 지점, 다시 해보고 싶은 점"
            style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }}
          />
        </label>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: C.ink, fontSize: '.9rem', fontWeight: 700 }}>
          <input type="checkbox" checked={completed} onChange={(e) => setCompleted(e.target.checked)} />
          이 단계는 실제로 해봤다
        </label>

        <button
          onClick={() => onSave(stageKey, { proof_artifact: proof, blocked_at_step: blocked, notes, completed })}
          disabled={saving}
          style={{
            background: saving ? C.border : C.accent,
            color: '#fff',
            border: 'none',
            borderRadius: 14,
            padding: '13px 16px',
            fontSize: '.95rem',
            fontWeight: 800,
            cursor: saving ? 'wait' : 'pointer',
          }}
        >
          {saving ? '저장 중…' : '이 단계 저장'}
        </button>
      </div>

      <div style={{ display: 'grid', gap: 10, background: '#f8fafc', border: `1px solid ${C.border}`, borderRadius: 14, padding: 14 }}>
        <div style={{ fontSize: '.86rem', color: C.muted, fontWeight: 800 }}>VP 피드백 메뉴</div>
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
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: C.ink, fontSize: '.9rem', fontWeight: 700 }}>
          <input type="checkbox" checked={jargonFlag} onChange={(e) => setJargonFlag(e.target.checked)} />
          영어/전문용어가 많아서 거슬렸다
        </label>
        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>가장 크게 막힌 지점</span>
          <input value={biggestBlocker} onChange={(e) => setBiggestBlocker(e.target.value)} placeholder="예: 파일을 어디서 열어야 하는지 모르겠음" style={{ border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }} />
        </label>
        <label style={{ display: 'grid', gap: 6 }}>
          <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>자유 피드백</span>
          <textarea value={freeformFeedback} onChange={(e) => setFreeformFeedback(e.target.value)} rows={4} placeholder="어디가 좋았는지, 어디가 허세처럼 느껴졌는지, 무엇을 더 바꾸면 좋을지 적으세요." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.5, resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </label>
        <button
          onClick={() => onSaveFeedback(stageKey, { empathy_score: empathyScore, clarity_score: clarityScore, motivation_score: motivationScore, jargon_flag: jargonFlag, biggest_blocker: biggestBlocker, freeform_feedback: freeformFeedback })}
          disabled={feedbackSaving}
          style={{ background: feedbackSaving ? C.border : '#0f766e', color: '#fff', border: 'none', borderRadius: 14, padding: '13px 16px', fontSize: '.95rem', fontWeight: 800, cursor: feedbackSaving ? 'wait' : 'pointer' }}
        >
          {feedbackSaving ? '피드백 저장 중…' : 'VP 피드백 저장'}
        </button>
        {stage?.vp_feedback?.submitted_at && <div style={{ fontSize: '.8rem', color: C.faint }}>최근 저장: {stage.vp_feedback.submitted_at}</div>}
      </div>
    </section>
  )
}

export function EduVpTrainingPage({ apiBase, authHeaders }: Props) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [preferredLlm, setPreferredLlm] = useState('claude')
  const [currentDevice, setCurrentDevice] = useState('iphone')
  const [desktopOs, setDesktopOs] = useState('mac')
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

  async function buildTrainingSlice() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/edu/vp-training/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          case_id: caseId,
          name,
          email,
          preferred_llm: preferredLlm,
          current_device: currentDevice,
          desktop_os: desktopOs,
          ai_experience: aiExperience,
          biggest_friction: biggestFriction,
          learning_goal: learningGoal,
          force_new: forceNew,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setCaseId(data.case_id)
      setTrainingState(data.training_state || null)
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
        body: JSON.stringify({
          case_id: caseId,
          stage,
          ...payload,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setTrainingState(data.training_state || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'stage save failed')
    } finally {
      setSavingStage(null)
    }
  }

  async function saveFeedback(stage: 'week0' | 'week1', payload: { empathy_score: number; clarity_score: number; motivation_score: number; jargon_flag: boolean; biggest_blocker: string; freeform_feedback: string }) {
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'feedback save failed')
    } finally {
      setSavingFeedbackStage(null)
    }
  }

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: '8px 10px 28px', color: C.ink }}>
      <div style={{ display: 'grid', gap: 14, marginBottom: 18 }}>
        <section style={{ background: `linear-gradient(135deg, ${C.accentSoft}, #eff6ff)`, border: `1px solid ${C.accent}`, borderRadius: 22, padding: 20 }}>
          <div style={{ fontSize: '.78rem', color: C.accent, fontWeight: 900, letterSpacing: '.05em', marginBottom: 8 }}>ZERO-BASE VP TRAINING</div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', lineHeight: 1.3 }}>VP AI 훈련 · Week 0 / Week 1</h1>
          <p style={{ margin: '10px 0 0', color: C.muted, lineHeight: 1.7, fontSize: '.98rem' }}>
            이 화면은 기존 edu pilot의 떠도는 만담형 대화를 무시하고, 이미 정해진 목표를 향해 VP를 단계적으로 이동시키는 실제 훈련 플로우입니다.
            목적은 생활형 AI 초보 상태에서 출발해, 장기적으로 CEO 수준의 AI handling에 가까워지는 것입니다.
          </p>
          {trainingState?.program_objective && (
            <div style={{ marginTop: 12, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.92rem', lineHeight: 1.6 }}>
              <strong style={{ display: 'block', marginBottom: 4 }}>현재 고정 목표</strong>
              {trainingState.program_objective}
            </div>
          )}
        </section>

        <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 18, padding: 18, display: 'grid', gap: 14 }}>
          <div>
            <div style={{ fontSize: '.78rem', color: C.faint, marginBottom: 6 }}>FIRST COHORT SLICE</div>
            <h2 style={{ margin: 0, fontSize: '1.15rem' }}>Week 0 + Week 1 + primary LLM 1개 + handoff 1개</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>이름</span>
              <input value={name} onChange={(e) => setName(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem' }} />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>이메일</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem' }} />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>Primary LLM</span>
              <select value={preferredLlm} onChange={(e) => setPreferredLlm(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="claude">Claude</option>
                <option value="gpt">ChatGPT</option>
                <option value="gemini">Gemini</option>
                <option value="local">로컬 모델</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>현재 모바일 기기</span>
              <select value={currentDevice} onChange={(e) => setCurrentDevice(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="iphone">iPhone</option>
                <option value="android">Android</option>
              </select>
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>PC / Mac 경로</span>
              <select value={desktopOs} onChange={(e) => setDesktopOs(e.target.value)} style={{ border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', background: C.surface }}>
                <option value="mac">Mac</option>
                <option value="windows">Windows PC</option>
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
            <textarea value={biggestFriction} onChange={(e) => setBiggestFriction(e.target.value)} rows={3} placeholder="예: 영어라서 무섭고, 뭘 질문해야 할지도 모르겠어요." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', lineHeight: 1.5, resize: 'vertical', boxSizing: 'border-box' }} />
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: '.84rem', color: C.muted, fontWeight: 700 }}>이번 2주 안에 만들고 싶은 변화</span>
            <textarea value={learningGoal} onChange={(e) => setLearningGoal(e.target.value)} rows={3} placeholder="예: 답장 쓰기, 회의 메모 정리, 일정 정리 같은 일을 AI로 더 빨리 끝내고 싶어요." style={{ width: '100%', border: `1px solid ${C.border}`, borderRadius: 14, padding: 12, fontSize: '.95rem', lineHeight: 1.5, resize: 'vertical', boxSizing: 'border-box' }} />
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.92rem', fontWeight: 700 }}>
            <input type="checkbox" checked={forceNew} onChange={(e) => setForceNew(e.target.checked)} />
            새 케이스로 다시 시작
          </label>
          <button onClick={() => void buildTrainingSlice()} disabled={loading || !email.trim()} style={{ background: loading ? C.border : C.accent, color: '#fff', border: 'none', borderRadius: 14, padding: '14px 18px', fontSize: '1rem', fontWeight: 800, cursor: loading ? 'wait' : 'pointer' }}>
            {loading ? 'Week 0 / Week 1 생성 중…' : 'Week 0 / Week 1 플로우 만들기'}
          </button>
          {error && <div style={{ color: '#b91c1c', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12, padding: 12, fontSize: '.9rem' }}>{error}</div>}
        </section>
      </div>

      {trainingState && (
        <div style={{ display: 'grid', gap: 16 }}>
          <section style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 18, padding: 16 }}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: '.84rem', color: C.muted }}>
              <span>case_id: <b style={{ color: C.ink }}>{caseId}</b></span>
              <span>primary_llm: <b style={{ color: C.ink }}>{trainingState.primary_llm_path}</b></span>
              <span>track: <b style={{ color: C.ink }}>beginner_practice</b></span>
            </div>
          </section>

          <section style={{ background: '#fff7ed', border: '1px solid #fdba74', borderRadius: 18, padding: 16, display: 'grid', gap: 10 }}>
            <div style={{ fontSize: '.78rem', color: '#c2410c', fontWeight: 900, letterSpacing: '.05em' }}>CEO REVIEW MODE</div>
            <h2 style={{ margin: 0, fontSize: '1.05rem', color: C.ink }}>사전 테스트 때 바로 볼 검수 포인트</h2>
            <div style={{ display: 'grid', gap: 8 }}>
              {CEO_REVIEW_POINTS.map((item) => (
                <div key={item} style={{ background: '#ffffff', border: '1px solid #fed7aa', borderRadius: 12, padding: '10px 12px', fontSize: '.9rem', color: C.ink, lineHeight: 1.55 }}>
                  {item}
                </div>
              ))}
            </div>
          </section>

          <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
            <StageCard title="Week 0" stage={trainingState.week0} stageKey="week0" onSave={saveStage} onSaveFeedback={saveFeedback} saving={savingStage === 'week0'} feedbackSaving={savingFeedbackStage === 'week0'} apiBase={apiBase} authHeaders={authHeaders} />
            <StageCard title="Week 1" stage={trainingState.week1} stageKey="week1" onSave={saveStage} onSaveFeedback={saveFeedback} saving={savingStage === 'week1'} feedbackSaving={savingFeedbackStage === 'week1'} apiBase={apiBase} authHeaders={authHeaders} />
          </div>
        </div>
      )}
    </div>
  )
}
