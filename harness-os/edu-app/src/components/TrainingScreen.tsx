import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  Check,
  ChevronDown,
  Clock,
  Loader2,
  Lock,
  Sparkles,
  Target,
} from 'lucide-react'
import { ApiError } from '@/lib/api'
import {
  fetchSession,
  saveStageArtifact,
  syncSession,
  type ChecklistItem,
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

function PersonalizedDay0Block({
  curriculum,
  learnerName,
}: {
  curriculum: PersonalizedCurriculum
  learnerName: string
}) {
  if (!curriculum.available) return null
  const attrs = curriculum.attrs ?? {}
  const fresh = curriculum.fresh_note
  const concern = curriculum.top_concerns[0]?.concern
  const topTopics = curriculum.order.slice(0, 3)
  const highlights = curriculum.highlights.slice(0, 2)
  const overlays = curriculum.overlay.slice(0, 2)
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
        <div className="mt-3 grid gap-2">
          {highlights.map((h) => (
            <article key={`${h.title}-${h.days_ago}`} className="rounded-[12px] border border-border bg-card p-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-accent-cyan">{ageLabel(h.days_ago)} 자료</span>
                {h.models[0] ? (
                  <span className="shrink-0 text-[11px] font-medium text-text-faint">{h.models[0]}</span>
                ) : null}
              </div>
              <p className="line-clamp-2 text-xs font-medium leading-relaxed text-ink">{h.title}</p>
            </article>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-text-faint">
        <span>
          근거 {fresh.pool_total}개 중 최근 30일 {fresh.recent_30d}개
        </span>
        {overlays.length ? <span>{overlays.map((o) => o.model).join(' · ')} 최신 신호</span> : null}
      </div>
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
        seqRef.current = Math.max(seqRef.current, Number(r.state.ui_state?.last_client_seq ?? 0))
        setState(r.state)
        hydrateStageInputs(r.state, pickStage(r.state))
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
