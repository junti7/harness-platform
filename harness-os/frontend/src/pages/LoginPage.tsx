import { useState, useEffect, useRef } from 'react'

type Role = 'ceo' | 'vp'

type Props = {
  onLogin: (role: Role) => void
  apiBase: string
  authHeaders: () => Record<string, string>
}

export function LoginPage({ onLogin, apiBase, authHeaders }: Props) {
  const [role, setRole] = useState<Role>('ceo')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [shake, setShake] = useState(false)
  const [loading, setLoading] = useState(false)
  const pwRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPassword('')
      setError('')
      pwRef.current?.focus()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [role])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (loading) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiBase}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ role, password }),
      })
      if (res.ok) {
        onLogin(role)
      } else {
        setError('비밀번호가 올바르지 않습니다.')
        setShake(true)
        setTimeout(() => setShake(false), 500)
        setPassword('')
        setTimeout(() => pwRef.current?.focus(), 50)
      }
    } catch {
      setError('서버에 연결할 수 없습니다.')
      setShake(true)
      setTimeout(() => setShake(false), 500)
      setPassword('')
      setTimeout(() => pwRef.current?.focus(), 50)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100dvh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--color-bg)',
      padding: 'calc(20px + var(--safe-top)) calc(16px + var(--safe-right)) calc(20px + var(--safe-bottom)) calc(16px + var(--safe-left))',
      overflow: 'hidden',
    }}>
      <div style={{
        width: 'min(400px, calc(100vw - 32px))',
        minWidth: 0,
        boxSizing: 'border-box',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" style={{ color: 'var(--color-accent)' }}>
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--color-text)' }}>
              Harness OS
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            종합 관제 콘솔 · 대표님 통제실
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: '12px',
          padding: 'clamp(1.25rem, 6vw, 2rem)',
          animation: shake ? 'shake 0.4s ease' : undefined,
        }}>
          <h2 style={{ margin: '0 0 1.5rem 0', fontSize: '1.05rem', fontWeight: 700, color: 'var(--color-text)' }}>
            로그인
          </h2>

          <form onSubmit={handleSubmit}>
            {/* Role selector */}
            <div style={{ marginBottom: '1.25rem' }}>
              <p style={{ margin: '0 0 0.6rem 0', fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                역할 선택
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.5rem' }}>
                {(['ceo', 'vp'] as const).map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    style={{
                      padding: '0.75rem',
                      borderRadius: '8px',
                      border: role === r
                        ? '2px solid var(--color-accent)'
                        : '2px solid var(--color-border)',
                      background: role === r
                        ? 'color-mix(in srgb, var(--color-accent) 12%, transparent)'
                        : 'var(--color-surface-lighter)',
                      color: role === r ? 'var(--color-accent)' : 'var(--color-text-muted)',
                      fontWeight: role === r ? 800 : 500,
                      fontSize: 'clamp(0.78rem, 3.4vw, 0.9rem)',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                      textAlign: 'center',
                      minWidth: 0,
                      whiteSpace: 'normal',
                    }}
                  >
                    {r === 'ceo' ? '대표님 (CEO)' : '부대표님 (VP)'}
                  </button>
                ))}
              </div>
            </div>

            {/* Password */}
            <div style={{ marginBottom: '1.5rem' }}>
              <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                비밀번호
              </p>
              <input
                ref={pwRef}
                type="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError('') }}
                placeholder="비밀번호 입력"
                autoFocus
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  border: error ? '1.5px solid var(--color-danger)' : '1.5px solid var(--color-border)',
                  background: 'var(--color-surface-lighter)',
                  color: 'var(--color-text)',
                  fontSize: '0.95rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.15s',
                  opacity: loading ? 0.6 : 1,
                }}
              />
              {error && (
                <p style={{ margin: '0.4rem 0 0 0', fontSize: '0.8rem', color: 'var(--color-danger)' }}>
                  {error}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.85rem',
                borderRadius: '8px',
                border: 'none',
                background: 'var(--color-accent)',
                color: '#fff',
                fontSize: '0.95rem',
                fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                letterSpacing: '0.02em',
                opacity: loading ? 0.7 : 1,
                transition: 'opacity 0.15s',
              }}
            >
              {loading ? '확인 중...' : '로그인'}
            </button>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
          30분 미활동 시 자동 로그아웃됩니다
        </p>
      </div>

      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-8px); }
          40% { transform: translateX(8px); }
          60% { transform: translateX(-6px); }
          80% { transform: translateX(6px); }
        }
      `}</style>
    </div>
  )
}
