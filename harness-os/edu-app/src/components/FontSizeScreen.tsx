import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Check, RotateCcw, Type } from 'lucide-react'
import {
  applyFontScale,
  DEFAULT_FONT_SCALE,
  fontScaleLabel,
  loadFontScale,
  MAX_FONT_SCALE,
  MIN_FONT_SCALE,
  saveFontScale,
} from '@/lib/fontSettings'

export type FontSizeScreenProps = {
  onBack: () => void
}

const PRESETS = [
  { label: '기본', value: 1 },
  { label: '크게', value: 1.15 },
  { label: '더 크게', value: 1.25 },
  { label: '아주 크게', value: 1.35 },
]

export default function FontSizeScreen({ onBack }: FontSizeScreenProps) {
  const [savedScale, setSavedScale] = useState(() => loadFontScale())
  const [draftScale, setDraftScale] = useState(savedScale)
  const savedLabel = useMemo(() => fontScaleLabel(savedScale), [savedScale])
  const draftLabel = useMemo(() => fontScaleLabel(draftScale), [draftScale])

  useEffect(() => {
    applyFontScale(draftScale)
  }, [draftScale])

  function handleBack() {
    applyFontScale(savedScale)
    onBack()
  }

  function handleSave() {
    const next = saveFontScale(draftScale)
    setSavedScale(next)
    setDraftScale(next)
    onBack()
  }

  function handleReset() {
    setDraftScale(DEFAULT_FONT_SCALE)
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6 lg:max-w-[960px] xl:max-w-[1120px] xl:px-8">
      <header className="mb-5 flex items-center gap-3">
        <button
          type="button"
          onClick={handleBack}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card text-text-muted transition hover:text-ink"
          aria-label="뒤로"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex min-w-0 flex-col">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-text-faint">
            보기 설정
          </span>
          <h1 className="flex items-center gap-1.5 text-xl font-bold text-ink-strong">
            <Type size={19} className="text-primary" />글자 크기 설정
          </h1>
        </div>
      </header>

      <section className="rounded-2xl border border-border bg-card p-4">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-bold text-ink-strong">현재 미리보기 크기</div>
            <p className="mt-1 text-xs leading-relaxed text-text-muted">
              저장된 크기 {savedLabel}. 아래 값을 움직이면 샘플 문장이 바로 바뀝니다.
            </p>
          </div>
          <div className="shrink-0 rounded-full bg-primary px-3 py-1 text-sm font-bold text-primary-foreground">
            {draftLabel}
          </div>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {PRESETS.map((item) => {
            const active = Math.abs(draftScale - item.value) < 0.01
            return (
              <button
                key={item.label}
                type="button"
                onClick={() => setDraftScale(item.value)}
                className={`h-11 rounded-[11px] border text-sm font-semibold transition ${
                  active
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-secondary text-ink hover:bg-card'
                }`}
              >
                {item.label}
              </button>
            )
          })}
        </div>

        <label className="block">
          <div className="mb-2 flex items-center justify-between text-xs font-semibold text-text-muted">
            <span>작게</span>
            <span>크게</span>
          </div>
          <input
            type="range"
            min={MIN_FONT_SCALE}
            max={MAX_FONT_SCALE}
            step={0.05}
            value={draftScale}
            onChange={(event) => setDraftScale(Number(event.target.value))}
            className="w-full accent-primary"
            aria-label="글자 크기"
          />
        </label>
      </section>

      <section className="mt-4 rounded-2xl border border-primary/20 bg-primary/5 p-4">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-primary">샘플 보기</div>
        <div className="space-y-3 rounded-[14px] border border-border bg-card p-4">
          <div>
            <div className="text-xs font-semibold text-text-faint">작은 안내문</div>
            <p className="mt-1 text-xs leading-relaxed text-text-muted">
              삭제한 질문은 제외하고, Day별 질문과 AI 코치 답변만 따로 봅니다.
            </p>
          </div>
          <div>
            <div className="text-sm font-semibold text-ink">본문 예시</div>
            <p className="mt-1 text-sm leading-relaxed text-text-muted">
              AI 답은 초안으로만 보고, 중요한 일정·비용·건강·법률·돈 문제는 반드시 원문이나 사람에게 다시 확인합니다.
            </p>
          </div>
          <div>
            <div className="text-base font-bold text-ink-strong">카드 제목 예시</div>
            <p className="mt-1 text-base leading-relaxed text-ink">
              글자가 편하게 읽히는지 확인한 뒤 이 크기로 적용하세요.
            </p>
          </div>
        </div>
      </section>

      <div className="mt-5 grid grid-cols-2 gap-2.5">
        <button
          type="button"
          onClick={handleReset}
          className="flex h-12 items-center justify-center gap-2 rounded-[12px] border border-border bg-card text-sm font-semibold text-ink transition hover:bg-secondary"
        >
          <RotateCcw size={17} />기본값
        </button>
        <button
          type="button"
          onClick={handleSave}
          className="flex h-12 items-center justify-center gap-2 rounded-[12px] bg-primary text-sm font-semibold text-primary-foreground transition hover:brightness-105"
        >
          <Check size={18} />이 크기로 적용
        </button>
      </div>
    </div>
  )
}
