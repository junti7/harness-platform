import { useRef, useState } from 'react'
import { AlertTriangle, ChevronRight, GraduationCap, Loader2, LogOut, Plus, Sparkles, Trash2, Type } from 'lucide-react'
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
  creating?: boolean
  error?: string | null
  onSelect: (caseId: number) => void
  onNew: () => void
  onLogout: () => void
  onDelete: (caseId: number) => Promise<void>
  onOpenCurriculum: () => void
  onOpenFontSize: () => void
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
  creating,
  error,
  onSelect,
  onNew,
  onLogout,
  onDelete,
  onOpenCurriculum,
  onOpenFontSize,
}: CaseSelectScreenProps) {
  const [menuFor, setMenuFor] = useState<TrainingCase | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [handoffNotice, setHandoffNotice] = useState<string | null>(() => {
    try {
      const value = sessionStorage.getItem('vp_training_handoff_notice')
      if (value) sessionStorage.removeItem('vp_training_handoff_notice')
      return value
    } catch {
      return null
    }
  })
  const timerRef = useRef<number | null>(null)
  const longPressedRef = useRef(false)
  // 누르기 시작 좌표 — 임계값을 넘는 '실제 스크롤/드래그' 일 때만 취소한다.
  // (이전엔 onPointerMove 마다 무조건 취소해, 손가락 미세 흔들림에도 long-press 가 즉시 깨졌다.)
  const startPosRef = useRef<{ x: number; y: number } | null>(null)
  const MOVE_CANCEL_PX = 12

  function clearTimer() {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
    startPosRef.current = null
  }

  function startPress(c: TrainingCase, e: React.PointerEvent) {
    longPressedRef.current = false
    clearTimer()
    startPosRef.current = { x: e.clientX, y: e.clientY }
    timerRef.current = window.setTimeout(() => {
      longPressedRef.current = true
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(12)
      setMenuFor(c)
    }, LONG_PRESS_MS)
  }

  // 임계값(MOVE_CANCEL_PX)을 넘는 이동(스크롤/드래그)일 때만 long-press 취소.
  function handleMove(e: React.PointerEvent) {
    const s = startPosRef.current
    if (!s) return
    if (Math.abs(e.clientX - s.x) > MOVE_CANCEL_PX || Math.abs(e.clientY - s.y) > MOVE_CANCEL_PX) {
      clearTimer()
    }
  }

  function handleClick(caseId: number) {
    // 길게누르기로 메뉴를 띄운 직후의 click 은 무시(탭 진입 방지).
    if (longPressedRef.current) {
      longPressedRef.current = false
      return
    }
    setHandoffNotice(null)
    onSelect(caseId)
  }

  async function confirmDelete() {
    if (!menuFor || deleting) return
    const caseId = menuFor.case_id
    setDeleting(true)
    setDeleteError(null)
    setMenuFor(null)
    try {
      await onDelete(caseId)
    } catch (e) {
      console.error('deleteCase failed', e)
      setDeleteError('삭제하지 못했어요. 새로고침 후 다시 시도해주세요.')
    } finally {
      setDeleting(false)
    }
  }

  const busyCreating = Boolean(creating)

  return (
    <div className="relative mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-5 py-7 sm:max-w-[760px] sm:px-6 lg:max-w-[960px] xl:max-w-[1120px] xl:px-8">
      {busyCreating ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-card/85 px-5 text-center backdrop-blur-sm">
          <div className="flex w-full max-w-[320px] flex-col items-center gap-3 rounded-2xl border border-primary/20 bg-card px-6 py-5 shadow-lg">
            <span className="flex h-12 w-12 items-center justify-center rounded-[14px] bg-primary text-primary-foreground">
              <Loader2 size={24} className="animate-spin" />
            </span>
            <div className="text-base font-bold text-ink-strong">새 훈련을 만들고 있어요</div>
            <p className="text-sm leading-relaxed text-text-muted">
              선택한 AI 도구와 학습 목적에 맞춰 Day 0, Day 1 화면을 준비하는 중입니다.
            </p>
          </div>
        </div>
      ) : null}
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
        disabled={loading || busyCreating}
        className="mb-5 flex h-13 items-center justify-center gap-2 rounded-[12px] bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-sm transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {busyCreating ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} strokeWidth={2.4} />}
        {busyCreating ? '새 훈련 준비 중…' : '새 훈련 시작'}
      </button>

      <button
        type="button"
        onClick={onOpenCurriculum}
        className="mb-5 flex items-center justify-center gap-2 rounded-[12px] border border-accent-cyan/30 bg-accent-cyan/10 py-3 text-[14px] font-semibold text-ink transition hover:bg-accent-cyan/20"
      >
        <Sparkles size={16} className="text-accent-cyan" />맞춤 커리큘럼 미리보기
      </button>

      <button
        type="button"
        onClick={onOpenFontSize}
        className="mb-5 flex items-center justify-center gap-2 rounded-[12px] border border-border bg-card py-3 text-[14px] font-semibold text-ink transition hover:bg-secondary"
      >
        <Type size={16} className="text-primary" />글자 크기 설정
      </button>

      {handoffNotice ? (
        <div className="mb-5 rounded-[12px] border border-primary/20 bg-primary/5 px-4 py-3 text-sm leading-relaxed text-ink">
          {handoffNotice} 이 기기에서 다시 이어가려면 아래 훈련 카드를 누르세요.
        </div>
      ) : null}

      {loading && !busyCreating ? (
        <ul className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <li
              key={i}
              className="h-[92px] animate-pulse rounded-2xl border border-border bg-secondary"
            />
          ))}
        </ul>
      ) : error ? (
        <div className="mt-6 flex flex-col items-center gap-3 rounded-2xl border border-danger/20 bg-danger-soft px-6 py-10 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-card text-danger">
            <AlertTriangle size={24} />
          </span>
          <p className="text-sm font-semibold text-danger">훈련 목록을 불러오지 못했어요</p>
          <p className="text-xs leading-relaxed text-text-muted">{error}</p>
        </div>
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
                    onPointerDown={(e) => startPress(c, e)}
                    onPointerUp={clearTimer}
                    onPointerLeave={clearTimer}
                    onPointerMove={handleMove}
                    onPointerCancel={clearTimer}
                    onContextMenu={(e) => {
                      e.preventDefault()
                      setDeleteError(null)
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
            if (!deleting) {
              setDeleteError(null)
              setMenuFor(null)
            }
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
                onClick={() => {
                  setDeleteError(null)
                  setMenuFor(null)
                }}
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
            {deleteError ? (
              <p className="mt-3 rounded-[10px] bg-danger-soft px-3 py-2 text-sm font-medium text-danger">
                {deleteError}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
