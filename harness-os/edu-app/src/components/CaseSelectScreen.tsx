import type { TrainingCase } from '@/lib/vpTraining'

/*
 * PLACEHOLDER — v0 로 생성한 화면이 이 파일을 교체한다.
 * Props 시그니처는 컨테이너(App.tsx)와의 계약이므로 v0 출력도 이 형태를 유지한다.
 */
export type CaseSelectScreenProps = {
  userName: string
  cases: TrainingCase[]
  loading?: boolean
  onSelect: (caseId: number) => void
  onNew: () => void
  onLogout: () => void
}

export default function CaseSelectScreen({
  userName,
  cases,
  loading,
  onSelect,
  onNew,
  onLogout,
}: CaseSelectScreenProps) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col gap-5 px-4 py-8">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-ink-strong">내 훈련</h1>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-text-muted">{userName || '사용자'}</span>
          <button type="button" onClick={onLogout} className="text-text-faint underline">
            로그아웃
          </button>
        </div>
      </header>

      <button
        type="button"
        onClick={onNew}
        disabled={loading}
        className="rounded-md bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground disabled:opacity-60"
      >
        + 새 훈련 시작
      </button>

      {loading ? (
        <p className="text-sm text-text-muted">불러오는 중…</p>
      ) : cases.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-secondary p-6 text-center">
          <p className="text-sm text-text-muted">아직 시작한 훈련이 없어요.</p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {cases.map((c) => (
            <li key={c.case_id}>
              <button
                type="button"
                onClick={() => onSelect(c.case_id)}
                className="w-full rounded-lg border bg-card p-4 text-left"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-ink">{c.case_label}</span>
                  <span className="rounded-pill border bg-surface-muted px-2 py-0.5 text-xs text-text-muted">
                    {c.status}
                  </span>
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-pill bg-secondary">
                  <div
                    className="h-full rounded-pill bg-primary"
                    style={{ width: `${Math.min(100, Math.max(0, c.progress_pct))}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-text-faint">수정 {c.updated_at}</p>
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-auto text-center text-xs text-text-faint">v0 화면 교체 예정 (placeholder)</p>
    </div>
  )
}
