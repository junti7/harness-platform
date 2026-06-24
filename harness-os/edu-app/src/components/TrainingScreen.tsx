import { ArrowLeft, Hammer, Sparkles } from 'lucide-react'

/*
 * TrainingScreen — 훈련 단계 화면.
 * 본격 단계 로직(레슨/퀴즈/진행률)은 /api/edu/vp-training/session · /session/sync 위에 얹는
 * 다음 작업이다. 지금은 케이스 진입 컨텍스트를 보여주는 마감된 안내 화면이다.
 * Props 시그니처는 컨테이너(App.tsx)와의 계약이다.
 */
export type TrainingScreenProps = {
  caseId: number
  onBack: () => void
}

export default function TrainingScreen({ caseId, onBack }: TrainingScreenProps) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7">
      <header className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          aria-label="목록으로"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card text-text-muted transition hover:text-ink"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex flex-col">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-text-faint">
            훈련 세션
          </span>
          <h1 className="text-lg font-bold text-ink-strong">훈련 #{caseId}</h1>
        </div>
      </header>

      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
          <Hammer size={26} />
        </span>
        <div className="flex flex-col gap-1.5">
          <h2 className="text-base font-bold text-ink-strong">훈련 단계 화면 준비 중</h2>
          <p className="max-w-[280px] text-sm leading-relaxed text-text-muted">
            레슨 · 퀴즈 · 진행률 흐름을 곧 이 화면에 연결합니다. 지금은 케이스 진입까지
            확인할 수 있습니다.
          </p>
        </div>
        <span className="mt-1 inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-text-muted">
          <Sparkles size={13} className="text-accent-cyan" />
          다음 단계에서 제작
        </span>
      </div>
    </div>
  )
}
