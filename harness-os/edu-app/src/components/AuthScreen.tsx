import { useState } from 'react'

/*
 * PLACEHOLDER — v0 로 생성한 화면이 이 파일을 교체한다.
 * 아래 Props 시그니처는 컨테이너(App.tsx)와의 계약이므로 v0 출력도 이 형태를 유지해야 한다.
 * 지금은 백엔드 연동을 테스트할 수 있는 최소 폼이다.
 */
export type AuthScreenProps = {
  onLogin: (v: { email: string; password: string }) => Promise<void>
  onRegister: (v: { name: string; email: string; password: string }) => Promise<void>
  loading?: boolean
  error?: string | null
}

export default function AuthScreen({ onLogin, onRegister, loading, error }: AuthScreenProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (loading) return
    if (mode === 'login') await onLogin({ email, password })
    else await onRegister({ name, email, password })
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col justify-center gap-6 px-4 py-8">
      <header className="flex flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-accent-cyan">
          Harness · 훈련
        </span>
        <h1 className="text-2xl font-bold text-ink-strong">부대표 훈련</h1>
        <p className="text-sm text-text-muted">로그인하고 오늘의 훈련을 이어가세요.</p>
      </header>

      <div className="rounded-lg border bg-card p-4">
        <div className="mb-4 flex gap-2">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`flex-1 rounded-md px-3 py-2 text-sm font-semibold transition ${
                mode === m ? 'bg-primary text-primary-foreground' : 'bg-secondary text-text-muted'
              }`}
            >
              {m === 'login' ? '로그인' : '가입'}
            </button>
          ))}
        </div>

        {error ? (
          <p className="mb-3 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>
        ) : null}

        <form onSubmit={submit} className="flex flex-col gap-3">
          {mode === 'register' ? (
            <input
              className="rounded-md border bg-surface px-3 py-2 text-sm text-ink"
              placeholder="이름"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
            />
          ) : null}
          <input
            className="rounded-md border bg-surface px-3 py-2 text-sm text-ink"
            placeholder="이메일"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <input
            className="rounded-md border bg-surface px-3 py-2 text-sm text-ink"
            placeholder="비밀번호"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          />
          <button
            type="submit"
            disabled={loading}
            className="mt-1 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
          >
            {loading ? '처리 중…' : mode === 'login' ? '로그인' : '가입하기'}
          </button>
        </form>
      </div>

      <p className="text-center text-xs text-text-faint">v0 화면 교체 예정 (placeholder)</p>
    </div>
  )
}
