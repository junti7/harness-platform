import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Clock, Loader2, MessageCircleQuestion, PlayCircle, Sparkles, TrendingUp } from 'lucide-react'
import {
  fetchPersonalizedCurriculum,
  type CurriculumAttrs,
  type PersonalizedCurriculum,
} from '@/lib/vpTraining'

/*
 * CurriculumScreen — 맞춤 커리큘럼 (모바일 우선).
 * 사용자가 속성을 바꾸면 백엔드가 미리 적재된 evidence 풀을 요청 시점에 재편(파이프라인 무재실행).
 * 추상 라벨이 아니라 수집 데이터의 *구체적 알맹이*(실제 고민·최신 관련글·내 도구 신호)를 보여줘
 * "내 상황을 안다 / 최신이다" 라는 감을 만든다. 선택 상태는 localStorage 에 저장/복원한다.
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
const MEDIA: Opt<NonNullable<CurriculumAttrs['media_preference']>>[] = [
  { value: 'mixed', label: '혼합' },
  { value: 'video', label: '영상' },
  { value: 'visual', label: '이미지' },
  { value: 'text', label: '글' },
]

const STORE_KEY = 'vp_curriculum_attrs'
const DEFAULT_ATTRS: CurriculumAttrs = {
  llm: 'chatgpt',
  level: 'beginner',
  motivation: 'work',
  env: 'mobile',
  job: '학부모',
  learning_goal: '',
  biggest_friction: '',
  media_preference: 'mixed',
}

function loadAttrs(): CurriculumAttrs {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (raw) return { ...DEFAULT_ATTRS, ...(JSON.parse(raw) as CurriculumAttrs) }
  } catch {
    /* ignore */
  }
  return DEFAULT_ATTRS
}

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

function freshLabel(d: number | null): string {
  if (d == null) return ''
  if (d <= 0) return '오늘 들어온 자료까지'
  if (d === 1) return '어제 들어온 자료까지'
  return `${d}일 전 자료까지`
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

export default function CurriculumScreen({ email, onBack }: CurriculumScreenProps) {
  const [attrs, setAttrs] = useState<CurriculumAttrs>(() => loadAttrs())
  const [debouncedAttrs, setDebouncedAttrs] = useState<CurriculumAttrs>(() => loadAttrs())
  const [data, setData] = useState<PersonalizedCurriculum | null>(null)
  const hasDataRef = useRef(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 선택 변경 시 localStorage 에 저장(다시 들어와도 복원).
  useEffect(() => {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(attrs))
    } catch {
      /* ignore */
    }
  }, [attrs])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedAttrs(attrs), 700)
    return () => window.clearTimeout(timer)
  }, [attrs])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      if (hasDataRef.current) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }
      setError(null)
      try {
        const r = await fetchPersonalizedCurriculum(email, debouncedAttrs)
        if (!cancelled) {
          hasDataRef.current = true
          setData(r)
        }
      } catch {
        if (!cancelled) setError('커리큘럼을 불러오지 못했습니다.')
      } finally {
        if (!cancelled) {
          setLoading(false)
          setRefreshing(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [email, debouncedAttrs])

  const maxW = data?.order?.length ? Math.max(...data.order.map((o) => o.weight)) : 1

  function set<K extends keyof CurriculumAttrs>(k: K, v: CurriculumAttrs[K]) {
    setAttrs((prev) => ({ ...prev, [k]: v }))
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6 lg:max-w-[960px] xl:max-w-[1120px] xl:px-8">
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
        <Selector label="선호 자료" value={attrs.media_preference ?? 'mixed'} options={MEDIA} onChange={(v) => set('media_preference', v)} />
        <div className="rounded-[10px] border border-border bg-secondary px-3 py-2 text-xs leading-relaxed text-text-muted">
          여기서 바꾼 값은 미리보기와 새 훈련 시작에만 적용됩니다. 이미 시작한 훈련의 진행 내용은 바뀌지 않습니다.
        </div>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-semibold text-text-faint">도달 목표</span>
          <textarea
            value={attrs.learning_goal ?? ''}
            onChange={(e) => set('learning_goal', e.target.value)}
            rows={3}
            placeholder="예: 왕초보에서 시작해 3개월 안에 업무 자동화까지, 하루 15분씩 영상과 실습 위주로 배우고 싶어요."
            className="resize-none rounded-[12px] border border-border bg-card px-3 py-2.5 text-sm leading-relaxed text-ink outline-none focus:border-primary"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-semibold text-text-faint">지금 가장 막히는 장면</span>
          <textarea
            value={attrs.biggest_friction ?? ''}
            onChange={(e) => set('biggest_friction', e.target.value)}
            rows={3}
            placeholder="예: Gemini를 켜도 첫 질문을 어떻게 써야 할지 모르겠고, 아이 숙제에 어디까지 써도 되는지 불안해요."
            className="resize-none rounded-[12px] border border-border bg-card px-3 py-2.5 text-sm leading-relaxed text-ink outline-none focus:border-primary"
          />
        </label>
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
        </div>
      ) : (
        <>
          {/* 최신성 배지 — "방금까지 반영" 신뢰감 */}
          {data.fresh_note?.newest_days_ago != null && (
            <div className="mb-4 flex items-center gap-2 rounded-[12px] border border-accent-cyan/30 bg-accent-cyan/10 px-3.5 py-2.5 text-[13px] text-ink">
              <Clock size={15} className="text-accent-cyan" />
              <span>
                <b>{freshLabel(data.fresh_note.newest_days_ago)}</b> 분석 · 최근 30일{' '}
                {data.fresh_note.recent_30d}건 반영
              </span>
              {refreshing ? <Loader2 size={14} className="ml-auto animate-spin text-accent-cyan" /> : null}
            </div>
          )}

          {/* 요즘 같은 분들의 실제 고민 — "내 얘기네" */}
          {data.top_concerns?.length > 0 && (
            <section className="mb-5">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-faint">
                <MessageCircleQuestion size={14} />요즘 같은 분들이 가장 많이 찾는 고민
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.top_concerns.slice(0, 6).map((c) => (
                  <span
                    key={c.concern}
                    className="rounded-full border border-border bg-secondary px-3 py-1 text-[12.5px] font-medium text-ink"
                  >
                    {c.concern}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* 최근 들어온 관련 글 — 구체·신선 */}
          {data.highlights?.length > 0 && (
            <section className="mb-6">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-text-faint">
                <Sparkles size={14} className="text-accent-cyan" />최근 들어온, 내 상황과 맞는 자료
              </div>
              <ul className="flex flex-col gap-2">
                {data.highlights.map((h, i) => (
                  <li
                    key={`${h.title}-${i}`}
                    className="flex flex-col gap-1.5 rounded-[12px] border border-border bg-card px-3.5 py-3"
                  >
                    <span className="text-[14px] font-medium leading-snug text-ink">{h.title}</span>
                    <div className="flex flex-wrap items-center gap-1.5 text-[11.5px]">
                      <span className="rounded-full bg-accent-cyan/15 px-2 py-0.5 font-semibold text-accent-cyan">
                        {h.media_kind === 'video' ? '영상' : h.media_kind === 'paper' ? '논문/근거' : '자료'}
                      </span>
                      {h.url && (
                        <button
                          type="button"
                          onClick={() => openSourceUrl(h.url)}
                          className="inline-flex items-center gap-1 font-semibold text-primary"
                        >
                          {h.media_kind === 'video' ? 'YouTube 열기' : '바로 열기'} <PlayCircle size={12} />
                        </button>
                      )}
                      {h.concern && <span className="text-text-faint">관심사 · {h.concern}</span>}
                      {h.models.slice(0, 2).map((m) => (
                        <span key={m} className="text-text-faint">
                          #{m}
                        </span>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* 맞춤 학습 순서 */}
          <div className="mb-3 flex items-center justify-between text-xs text-text-faint">
            <span>맞춤 학습 순서</span>
            <span>기준 풀: {data.base_pool}</span>
          </div>
          <ol className="flex flex-col gap-2">
            {data.order.slice(0, 8).map((o, i) => (
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
                <TrendingUp size={14} />당신의 도구({attrs.llm || '전체'}) 기준 최신 신호
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
