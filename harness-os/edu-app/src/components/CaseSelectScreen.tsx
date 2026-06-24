import { useRef, useState } from 'react'
import { AlertTriangle, ChevronRight, GraduationCap, Loader2, LogOut, Plus, Trash2 } from 'lucide-react'
import type { TrainingCase } from '@/lib/vpTraining'

/*
 * CaseSelectScreen — 내 훈련 목록 (모바일 우선).
 * 케이스를 길게 누르면(또는 우클릭) 삭제 확인 시트가 뜨고, 확인하면 완전 삭제된다.
 * Props 시그니처는 컨테이너(App.tsx)와의 계약이다.
 */
export type CaseSelectScreenProps = {
  userName: string
  cases: TrainingCase[]
  loading?: boolean
  onSelect: (caseId: number) => void
  onNew: () => void
  onLogout: () => void
  onDelete: (caseId: number) => Promise<void>
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

const LONG_PRESS_MS = 500

export default function CaseSelectScreen({
  userName,
  cases,
  loading,
  onSelect,
  onNew,
  onLogout,
  onDelete,
}: CaseSelectScreenProps) {
  const [menuFor, setMenuFor] = useState<TrainingCase | null>(null)
  const [deleting, setDeleting] = useState(false)
  const timerRef = useRef<number | null>(null)
  const longPressedRef = useRef(false)

  function clearTimer() {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  function startPress(c: TrainingCase) {
    longPressedRef.current = false
    clearTimer()
    timerRef.current = window.setTimeout(() => {
      longPressedRef.current = true
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(12)
      setMenuFor(c)
    }, LONG_PRESS_MS)
  }

  function handleClick(caseId: number) {
    // 길게누르기로 메뉴를 띄운 직후의 click 은 무시(탭 진입 방지).
    if (longPressedRef.current) {
      longPressedRef.current = false
      return
    }
    onSelect(caseId)
  }

  async function confirmDelete() {
    if (!menuFor || deleting) return
    setDeleting(true)
    try {
      await onDelete(menuFor.case_id)
      setMenuFor(null)
    } catch (e) {
      console.error('deleteCase failed', e)
    } finally {
      setDeleting(false)
    }
  }

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
        <>
          <ul className="flex flex-col gap-3">
            {cases.map((c) => {
              const pct = clampPct(c.progress_pct)
              const tone = statusTone(c.status)
              return (
                <li key={c.case_id}>
                  <button
                    type="button"
                    onClick={() => handleClick(c.case_id)}
                    onPointerDown={() => startPress(c)}
                    onPointerUp={clearTimer}
                    onPointerLeave={clearTimer}
                    onPointerMove={clearTimer}
                    onPointerCancel={clearTimer}
                    onContextMenu={(e) => {
                      e.preventDefault()
                      setMenuFor(c)
                    }}
                    style={{ WebkitTouchCallout: 'none' }}
                    className="group w-full select-none rounded-2xl border border-border bg-card p-4 text-left shadow-sm transition hover:border-border active:scale-[0.99]"
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
          <p className="mt-4 text-center text-xs text-text-faint">
            훈련을 길게 누르면 삭제할 수 있어요.
          </p>
        </>
      )}

      {/* 삭제 확인 시트 */}
      {menuFor ? (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink-strong/40 px-4 pb-4"
          onClick={() => {
            if (!deleting) setMenuFor(null)
          }}
        >
          <div
            className="w-full max-w-[480px] rounded-2xl border border-border bg-card p-5 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-danger-soft text-danger">
                <AlertTriangle size={20} />
              </span>
              <div className="flex min-w-0 flex-col gap-0.5">
                <h2 className="text-base font-bold text-ink-strong">훈련 삭제</h2>
                <p className="truncate text-sm text-text-muted">{menuFor.case_label}</p>
              </div>
            </div>
            <p className="mb-5 text-sm leading-relaxed text-text-muted">
              이 훈련의 모든 진행 기록이 <span className="font-semibold text-danger">영구히 삭제</span>되며
              되돌릴 수 없어요. 정말 삭제할까요?
            </p>
            <div className="flex gap-2.5">
              <button
                type="button"
                onClick={() => setMenuFor(null)}
                disabled={deleting}
                className="h-12 flex-1 rounded-[10px] border border-border bg-card text-[15px] font-semibold text-ink transition hover:bg-secondary disabled:opacity-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={deleting}
                className="flex h-12 flex-1 items-center justify-center gap-2 rounded-[10px] bg-danger text-[15px] font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleting ? <Loader2 size={18} className="animate-spin" /> : <Trash2 size={17} />}
                {deleting ? '삭제 중…' : '완전 삭제'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
