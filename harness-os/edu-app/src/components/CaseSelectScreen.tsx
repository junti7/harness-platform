import { ChevronRight, GraduationCap, LogOut, Plus } from 'lucide-react'
import type { TrainingCase } from '@/lib/vpTraining'

/*
 * CaseSelectScreen — 내 훈련 목록 (모바일 우선).
 * Props 시그니처는 컨테이너(App.tsx)와의 계약이므로 v0 재생성 시에도 이 형태를 유지한다.
 */
export type CaseSelectScreenProps = {
  userName: string
  cases: TrainingCase[]
  loading?: boolean
  onSelect: (caseId: number) => void
  onNew: () => void
  onLogout: () => void
}

type Tone = 'success' | 'primary' | 'neutral'

/** 백엔드 status 문자열을 색 톤으로 매핑(미지의 값은 neutral). */
function statusTone(status: string): Tone {
  const s = status.toLowerCase()
  if (s.includes('complete') || s.includes('done') || s.includes('완료')) return 'success'
  if (s.includes('progress') || s.includes('active') || s.includes('진행')) return 'primary'
  return 'neutral'
}

const TONE_CLASS: Record<Tone, string> = {
  success: 'bg-success-soft text-success',
  primary: 'bg-accent text-accent-foreground',
  neutral: 'bg-secondary text-text-muted',
}

function clampPct(n: number): number {
  if (!Number.isFinite(n)) return 0
  return Math.min(100, Math.max(0, Math.round(n)))
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
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7">
      <header className="mb-6 flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-text-faint">
            내 훈련
          </span>
          <h1 className="text-xl font-bold text-ink-strong">
            {(userName || '사용자').trim()}님
          </h1>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-text-muted transition hover:text-ink"
        >
          <LogOut size={14} />
          로그아웃
        </button>
      </header>

      <button
        type="button"
        onClick={onNew}
        disabled={loading}
        className="mb-5 flex h-13 items-center justify-center gap-2 rounded-[12px] bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-sm transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Plus size={18} strokeWidth={2.4} />새 훈련 시작
      </button>

      {loading ? (
        <ul className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <li
              key={i}
              className="h-[92px] animate-pulse rounded-2xl border border-border bg-secondary"
            />
          ))}
        </ul>
      ) : cases.length === 0 ? (
        <div className="mt-6 flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card px-6 py-12 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-accent-foreground">
            <GraduationCap size={24} />
          </span>
          <p className="text-sm font-medium text-ink">아직 시작한 훈련이 없어요</p>
          <p className="text-xs leading-relaxed text-text-faint">
            위 ‘새 훈련 시작’을 눌러 첫 훈련을 시작해보세요.
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {cases.map((c) => {
            const pct = clampPct(c.progress_pct)
            const tone = statusTone(c.status)
            return (
              <li key={c.case_id}>
                <button
                  type="button"
                  onClick={() => onSelect(c.case_id)}
                  className="group w-full rounded-2xl border border-border bg-card p-4 text-left shadow-sm transition hover:border-border active:scale-[0.99]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="font-semibold leading-snug text-ink">{c.case_label}</span>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${TONE_CLASS[tone]}`}
                    >
                      {c.status}
                    </span>
                  </div>

                  <div className="mt-3.5 flex items-center gap-2.5">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-primary transition-[width]"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-9 shrink-0 text-right text-xs font-semibold tabular-nums text-text-muted">
                      {pct}%
                    </span>
                  </div>

                  <div className="mt-2.5 flex items-center justify-between">
                    <span className="text-xs text-text-faint">수정 {c.updated_at}</span>
                    <ChevronRight
                      size={16}
                      className="text-text-faint transition group-hover:translate-x-0.5"
                    />
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
