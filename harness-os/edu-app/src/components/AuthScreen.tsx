import { useState } from 'react'
import { AlertCircle, GraduationCap, Loader2, Lock, Mail, User } from 'lucide-react'

/*
 * AuthScreen — 로그인 / 가입 진입 화면 (모바일 우선).
 * 아래 Props 시그니처는 컨테이너(App.tsx)와의 계약이므로 v0 재생성 시에도 이 형태를 유지한다.
 * 색/간격은 src/index.css 의 DESIGN.md 토큰만 사용한다.
 */
export type AuthScreenProps = {
  onLogin: (v: { email: string; password: string }) => Promise<void>
  onRegister: (v: { name: string; email: string; password: string }) => Promise<void>
  loading?: boolean
  error?: string | null
}

type Mode = 'login' | 'register'

function Field({
  icon,
  ...props
}: { icon: React.ReactNode } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="relative flex items-center">
      <span className="pointer-events-none absolute left-3.5 text-text-faint">{icon}</span>
      <input
        {...props}
        className="h-12 w-full rounded-[10px] border border-border bg-card pl-11 pr-3.5 text-[15px] text-ink outline-none transition placeholder:text-text-faint focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 disabled:opacity-60"
      />
    </label>
  )
}

export default function AuthScreen({ onLogin, onRegister, loading, error }: AuthScreenProps) {
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const isLogin = mode === 'login'
  const canSubmit =
    !loading &&
    email.trim().length > 3 &&
    password.length >= 4 &&
    (isLogin || name.trim().length > 0)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    if (isLogin) await onLogin({ email: email.trim(), password })
    else await onRegister({ name: name.trim(), email: email.trim(), password })
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[440px] flex-col justify-center gap-7 px-5 py-10">
      <header className="flex flex-col items-center gap-3 text-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
          <GraduationCap size={28} strokeWidth={2.2} />
        </span>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-cyan">
            Harness · 훈련
          </span>
          <h1 className="text-[26px] font-bold leading-tight text-ink-strong">부대표 훈련</h1>
          <p className="text-sm text-text-muted">
            {isLogin ? '로그인하고 오늘의 훈련을 이어가세요.' : '계정을 만들고 첫 훈련을 시작하세요.'}
          </p>
        </div>
      </header>

      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="mb-5 grid grid-cols-2 gap-1 rounded-[12px] bg-secondary p-1">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
              className={`h-10 rounded-[9px] text-sm font-semibold transition ${
                mode === m
                  ? 'bg-card text-ink-strong shadow-sm'
                  : 'text-text-muted hover:text-ink'
              }`}
            >
              {m === 'login' ? '로그인' : '가입'}
            </button>
          ))}
        </div>

        {error ? (
          <div className="mb-4 flex items-start gap-2 rounded-[10px] bg-danger-soft px-3.5 py-3 text-sm text-danger">
            <AlertCircle size={17} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <form onSubmit={submit} className="flex flex-col gap-3">
          {!isLogin ? (
            <Field
              icon={<User size={18} />}
              placeholder="이름"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              disabled={loading}
            />
          ) : null}
          <Field
            icon={<Mail size={18} />}
            placeholder="이메일"
            type="email"
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            disabled={loading}
          />
          <Field
            icon={<Lock size={18} />}
            placeholder="비밀번호"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            disabled={loading}
          />

          <button
            type="submit"
            disabled={!canSubmit}
            className="mt-2 flex h-12 items-center justify-center gap-2 rounded-[10px] bg-primary text-[15px] font-semibold text-primary-foreground transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : null}
            {loading ? '처리 중…' : isLogin ? '로그인' : '가입하기'}
          </button>
        </form>
      </div>

      <p className="text-center text-xs leading-relaxed text-text-faint">
        {isLogin ? '계정이 없으신가요? 위 ‘가입’ 탭을 눌러주세요.' : '훈련 데이터는 안전하게 보관됩니다.'}
      </p>
    </div>
  )
}
