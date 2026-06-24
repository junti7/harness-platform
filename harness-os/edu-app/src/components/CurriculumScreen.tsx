import { useEffect, useState } from 'react'
import { ArrowLeft, Loader2, Sparkles, TrendingUp } from 'lucide-react'
import {
  fetchPersonalizedCurriculum,
  type CurriculumAttrs,
  type PersonalizedCurriculum,
} from '@/lib/vpTraining'

/*
 * CurriculumScreen — 맞춤 커리큘럼 미리보기 (모바일 우선).
 * 사용자가 속성(LLM·수준·동기·환경·직업)을 바꾸면 백엔드가 미리 적재된 evidence 풀을
 * 요청 시점에 재편(파이프라인 무재실행)해 학습 순서를 즉시 다시 보여준다.
 * Props 는 컨테이너(App.tsx)와의 계약이다.
 */
export type CurriculumScreenProps = {
  email: string
  onBack: () => void
}

type Opt<T extends string> = { value: T; label: string }

const LLMS: Opt<string>[] = [
  { value: 'chatgpt', label: 'ChatGPT' },
  { value: '제미나이', label: '제미나이' },
  { value: '클로드', label: '클로드' },
  { value: '', label: '전체' },
]
const LEVELS: Opt<NonNullable<CurriculumAttrs['level']>>[] = [
  { value: 'beginner', label: '왕초보' },
  { value: 'intermediate', label: '중급' },
  { value: 'advanced', label: '고급' },
]
const MOTIVATIONS: Opt<NonNullable<CurriculumAttrs['motivation']>>[] = [
  { value: 'work', label: '업무' },
  { value: 'child_study', label: '자녀학습' },
  { value: 'daily', label: '일상' },
  { value: 'writing', label: '글쓰기' },
]
const ENVS: Opt<NonNullable<CurriculumAttrs['env']>>[] = [
  { value: 'mobile', label: '모바일' },
  { value: 'pc', label: 'PC' },
  { value: 'voice', label: '음성' },
]
const JOBS: Opt<string>[] = [
  { value: '학부모', label: '학부모' },
  { value: '직장인', label: '직장인' },
]

function Selector<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: Opt<T>[]
  onChange: (v: T) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold text-text-faint">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => (
          <button
            key={o.value || '_'}
            type="button"
            onClick={() => onChange(o.value)}
            className={
              'rounded-full border px-3 py-1.5 text-[13px] font-medium transition ' +
              (value === o.value
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-text-muted hover:text-ink')
            }
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function CurriculumScreen({ email, onBack }: CurriculumScreenProps) {
  const [attrs, setAttrs] = useState<CurriculumAttrs>({
    llm: 'chatgpt',
    level: 'beginner',
    motivation: 'work',
    env: 'mobile',
    job: '학부모',
  })
  const [data, setData] = useState<PersonalizedCurriculum | null>(null)
  // 초기/속성변경 로딩은 effect 내 async 경로에서만 setState 하도록 lazy 초기값을 true 로 둔다.
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // setState 는 effect 동기 본문이 아니라 async IIFE 안에서만 호출(react-hooks/set-state-in-effect 회피).
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        const r = await fetchPersonalizedCurriculum(email, attrs)
        if (!cancelled) setData(r)
      } catch {
        if (!cancelled) setError('커리큘럼을 불러오지 못했습니다.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [email, attrs])

  const maxW = data?.order?.length ? Math.max(...data.order.map((o) => o.weight)) : 1

  function set<K extends keyof CurriculumAttrs>(k: K, v: CurriculumAttrs[K]) {
    setAttrs((prev) => ({ ...prev, [k]: v }))
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7">
      <header className="mb-5 flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card text-text-muted transition hover:text-ink"
          aria-label="뒤로"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex flex-col">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-text-faint">
            맞춤 커리큘럼
          </span>
          <h1 className="flex items-center gap-1.5 text-xl font-bold text-ink-strong">
            <Sparkles size={18} className="text-accent-cyan" />내게 맞는 학습 순서
          </h1>
        </div>
      </header>

      <div className="mb-5 flex flex-col gap-3.5 rounded-[14px] border border-border bg-card/60 p-4">
        <Selector label="현재 쓰는 LLM" value={attrs.llm ?? ''} options={LLMS} onChange={(v) => set('llm', v)} />
        <Selector label="사용 수준" value={attrs.level ?? 'beginner'} options={LEVELS} onChange={(v) => set('level', v)} />
        <Selector label="학습 동기" value={attrs.motivation ?? 'work'} options={MOTIVATIONS} onChange={(v) => set('motivation', v)} />
        <Selector label="사용 환경" value={attrs.env ?? 'mobile'} options={ENVS} onChange={(v) => set('env', v)} />
        <Selector label="역할" value={attrs.job ?? '학부모'} options={JOBS} onChange={(v) => set('job', v)} />
      </div>

      {loading ? (
        <div className="flex flex-col items-center gap-2 py-10 text-text-faint">
          <Loader2 size={22} className="animate-spin" />
          <span className="text-sm">재편 중…</span>
        </div>
      ) : error ? (
        <div className="rounded-[12px] border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : !data?.available ? (
        <div className="rounded-[12px] border border-border bg-card px-4 py-6 text-center text-sm text-text-muted">
          아직 커리큘럼 데이터가 준비되지 않았습니다.
          <br />
          (수집·정제 파이프라인 적재 후 표시됩니다)
        </div>
      ) : (
        <>
          <div className="mb-3 flex items-center justify-between text-xs text-text-faint">
            <span>맞춤 학습 순서</span>
            <span>기준 풀: {data.base_pool}</span>
          </div>
          <ol className="flex flex-col gap-2">
            {data.order.slice(0, 10).map((o, i) => (
              <li
                key={o.topic}
                className="flex items-center gap-3 rounded-[12px] border border-border bg-card px-3.5 py-3"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[13px] font-bold text-primary">
                  {i + 1}
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="truncate text-[14px] font-medium text-ink">{o.topic}</span>
                  <span className="h-1.5 w-full overflow-hidden rounded-full bg-border">
                    <span
                      className="block h-full rounded-full bg-accent-cyan"
                      style={{ width: `${Math.max(6, (o.weight / maxW) * 100)}%` }}
                    />
                  </span>
                </div>
              </li>
            ))}
          </ol>

          {data.overlay.length > 0 && (
            <div className="mt-6">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-faint">
                <TrendingUp size={14} />당신의 도구 기준 최신 신호
              </div>
              <div className="flex flex-wrap gap-2">
                {data.overlay.slice(0, 6).map((o) => (
                  <span
                    key={o.model}
                    className="rounded-full border border-accent-cyan/30 bg-accent-cyan/10 px-3 py-1 text-[12px] font-medium text-ink"
                  >
                    {o.model} · {o.freshness.toFixed(1)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
