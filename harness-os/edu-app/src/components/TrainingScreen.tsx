/*
 * PLACEHOLDER — 훈련 단계 화면. 다음 v0 프롬프트에서 본격 제작한다.
 * 지금은 케이스 선택 → 진입 흐름만 확인하는 자리표시자다.
 * (세션/단계 로직은 /api/edu/vp-training/session, /session/sync 위로 이식 예정)
 */
export type TrainingScreenProps = {
  caseId: number
  onBack: () => void
}

export default function TrainingScreen({ caseId, onBack }: TrainingScreenProps) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col gap-5 px-4 py-8">
      <header className="flex items-center gap-3">
        <button type="button" onClick={onBack} className="text-sm text-text-faint underline">
          ← 목록
        </button>
        <h1 className="text-xl font-bold text-ink-strong">훈련 #{caseId}</h1>
      </header>
      <div className="rounded-lg border border-dashed bg-secondary p-6 text-center">
        <p className="text-sm text-text-muted">
          훈련 단계 화면은 다음 v0 단계에서 제작합니다.
        </p>
      </div>
    </div>
  )
}
