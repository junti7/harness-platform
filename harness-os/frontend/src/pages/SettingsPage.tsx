import { useState, useEffect } from 'react'

type Settings = {
  theme: 'light' | 'dark'
  exchangeRate: number
  refreshInterval: number // seconds
  nickname: string
  welcomeMessage: string
  exchangeRateMode: 'realtime' | 'manual'
}

const defaultSettings = {
  ceo: {
    theme: 'dark' as const,
    exchangeRate: 1400,
    refreshInterval: 60,
    nickname: '대표님',
    welcomeMessage: 'Harness OS의 최종 의사결정 및 자산 지배 통제 센터에 오신 것을 환영합니다.',
    exchangeRateMode: 'realtime' as const,
  },
  vp: {
    theme: 'light' as const,
    exchangeRate: 1400,
    refreshInterval: 60,
    nickname: '부대표님',
    welcomeMessage: 'Physical AI 리서치 분석 및 콘텐츠 품질 1차 관제 데스크입니다.',
    exchangeRateMode: 'realtime' as const,
  },
}

type Props = {
  onSettingsChange: (role: 'ceo' | 'vp', settings: Settings) => void
  currentRole: 'ceo' | 'vp'
  onLogout: () => void
  apiBase: string
  authHeaders: () => Record<string, string>
}

export function SettingsPage({ onSettingsChange, currentRole, onLogout, apiBase, authHeaders }: Props) {
  const [runtimeHealth, setRuntimeHealth] = useState<{
    ok: boolean
    target?: string
    account?: string
    count?: number
    lastSuccessAt?: string | null
    error?: string | null
  } | null>(null)

  // 역할별 설정
  const [settings, setSettings] = useState<Settings>(() => {
    const saved = localStorage.getItem(`harness-settings-${currentRole}`)
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Settings
        if (!parsed.exchangeRateMode) {
          parsed.exchangeRateMode = defaultSettings[currentRole].exchangeRateMode
        }
        return parsed
      } catch (e) {
        console.error(e)
      }
    }
    return defaultSettings[currentRole]
  })

  // 비밀번호 변경 관련 로컬 상태
  const [currentPasswordInput, setCurrentPasswordInput] = useState('')
  const [newPasswordInput, setNewPasswordInput] = useState('')
  const [confirmPasswordInput, setConfirmPasswordInput] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState<string | null>(null)

  // 역할이 바뀌면 설정을 다시 로드
  useEffect(() => {
    const saved = localStorage.getItem(`harness-settings-${currentRole}`)
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Settings
        if (!parsed.exchangeRateMode) {
          parsed.exchangeRateMode = defaultSettings[currentRole].exchangeRateMode
        }
        setSettings(parsed)
      } catch {
        setSettings(defaultSettings[currentRole])
      }
    } else {
      setSettings(defaultSettings[currentRole])
    }
    setCurrentPasswordInput('')
    setNewPasswordInput('')
    setConfirmPasswordInput('')
    setPwError(null)
    setPwSuccess(null)
  }, [currentRole])

  useEffect(() => {
    let cancelled = false
    const loadRuntimeHealth = async () => {
      try {
        const res = await fetch(
          `${apiBase}/api/gmail/search?q=${encodeURIComponent('in:inbox newer_than:14d -category:promotions')}&limit=1`,
          { headers: authHeaders() },
        )
        if (!res.ok) throw new Error(`Gmail API ${res.status}`)
        const data = await res.json()
        if (cancelled) return
        setRuntimeHealth({
          ok: true,
          target: data?.runtime?.target,
          account: data?.runtime?.account,
          count: data?.count,
          lastSuccessAt: new Date().toISOString(),
          error: null,
        })
      } catch (err) {
        if (cancelled) return
        setRuntimeHealth(prev => ({
          ok: false,
          target: prev?.target,
          account: prev?.account,
          count: prev?.count,
          lastSuccessAt: prev?.lastSuccessAt ?? null,
          error: err instanceof Error ? err.message : 'Runtime health check failed',
        }))
      }
    }
    void loadRuntimeHealth()
    return () => {
      cancelled = true
    }
  }, [apiBase, authHeaders])

  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    const newSettings = { ...settings, [key]: value }
    setSettings(newSettings)
    localStorage.setItem(`harness-settings-${currentRole}`, JSON.stringify(newSettings))
    onSettingsChange(currentRole, newSettings)
  }

  // 비밀번호 변경 액션 핸들러 (서버 API 기반)
  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwError(null)
    setPwSuccess(null)

    if (!newPasswordInput) {
      setPwError('새 비밀번호를 입력해 주십시오.')
      return
    }
    if (newPasswordInput !== confirmPasswordInput) {
      setPwError('새 비밀번호와 확인 입력이 일치하지 않습니다.')
      return
    }

    try {
      const res = await fetch(`${apiBase}/api/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          role: currentRole,
          current_password: currentPasswordInput,
          new_password: newPasswordInput,
        }),
      })
      if (res.ok) {
        setPwSuccess('비밀번호가 서버에 안전하게 저장되었습니다.')
        setCurrentPasswordInput('')
        setNewPasswordInput('')
        setConfirmPasswordInput('')
      } else {
        const data = await res.json().catch(() => ({}))
        if (res.status === 401) {
          setPwError('이전 비밀번호가 올바르지 않습니다.')
        } else {
          setPwError(data?.detail ?? '비밀번호 변경에 실패했습니다.')
        }
      }
    } catch {
      setPwError('서버에 연결할 수 없습니다.')
    }
  }

  const handleReset = () => {
    const defaults = defaultSettings[currentRole]
    setSettings(defaults)
    localStorage.setItem(`harness-settings-${currentRole}`, JSON.stringify(defaults))
    onSettingsChange(currentRole, defaults)
    setPwError(null)
    setPwSuccess(null)
    setCurrentPasswordInput('')
    setNewPasswordInput('')
    setConfirmPasswordInput('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <section className="panel">
        <div className="panel-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.4rem', margin: 0, fontWeight: 800, letterSpacing: '-0.5px' }}>
              Console Preferences
            </h2>
            <p className="subtitle" style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginTop: '0.3rem', fontWeight: 500 }}>
              {currentRole === 'ceo' ? '대표님' : '부대표님'} 계정의 시스템 테마, 기준 환율 공식, 비밀번호 및 작동 환경을 관리합니다.
            </p>
          </div>
          <button
            onClick={onLogout}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: '1px solid var(--color-danger)',
              background: 'transparent',
              color: 'var(--color-danger)',
              fontWeight: 600,
              fontSize: '0.8rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            로그아웃
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', alignItems: 'start', paddingBottom: '1.2rem', borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>자동화 서버 연결 상태</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>대표 메일과 내부 자동화가 읽기 전용으로 연결되어 있는지 확인합니다.</span>
            </div>
            <div style={{
              border: '1px solid var(--color-border)',
              borderRadius: '14px',
              padding: '1rem 1.1rem',
              background: 'var(--color-surface-lighter)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.65rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                <strong style={{ fontSize: '0.96rem', color: 'var(--color-text)' }}>자동화 서버 상태</strong>
                <span style={{
                  padding: '0.28rem 0.68rem',
                  borderRadius: '999px',
                  border: `1px solid ${runtimeHealth?.ok ? 'color-mix(in srgb, var(--color-accent) 35%, var(--color-border))' : 'color-mix(in srgb, var(--color-danger) 35%, var(--color-border))'}`,
                  color: runtimeHealth?.ok ? 'var(--color-accent)' : 'var(--color-danger)',
                  background: 'var(--color-surface)',
                  fontSize: '0.76rem',
                  fontWeight: 800,
                }}>
                  {runtimeHealth === null ? '확인 중' : runtimeHealth.ok ? '자동화 서버 연결됨' : '연결 점검 필요'}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                <div>
                  <span style={{ display: 'block', fontSize: '0.74rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>연결 대상</span>
                  <strong style={{ fontSize: '0.88rem', color: 'var(--color-text)' }}>{runtimeHealth?.target ?? '자동화 서버'}</strong>
                </div>
                <div>
                  <span style={{ display: 'block', fontSize: '0.74rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>연결된 계정</span>
                  <strong style={{ fontSize: '0.88rem', color: 'var(--color-text)' }}>{runtimeHealth?.account ?? '대표 Gmail 계정'}</strong>
                </div>
                <div>
                  <span style={{ display: 'block', fontSize: '0.74rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>점검 결과</span>
                  <strong style={{ fontSize: '0.88rem', color: 'var(--color-text)' }}>
                    {runtimeHealth?.ok ? `최근 메일 ${runtimeHealth.count ?? 0}건 확인` : 'Gmail probe 실패'}
                  </strong>
                </div>
                <div>
                  <span style={{ display: 'block', fontSize: '0.74rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>Last successful probe</span>
                  <strong style={{ fontSize: '0.88rem', color: 'var(--color-text)' }}>
                    {runtimeHealth?.lastSuccessAt ? new Date(runtimeHealth.lastSuccessAt).toLocaleString('ko-KR') : '기록 없음'}
                  </strong>
                </div>
              </div>
              {runtimeHealth?.error && (
                <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-danger)', fontWeight: 600 }}>
                  {runtimeHealth.error}
                </p>
              )}
            </div>
          </div>

          {/* 1. Theme Configuration */}
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', alignItems: 'center', paddingBottom: '1.2rem', borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>대시보드 전용 테마</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>기본 브라우저 설정을 우회하고 고정합니다.</span>
            </div>
            <div style={{ display: 'flex', gap: '0.8rem' }}>
              <button
                type="button"
                onClick={() => updateSetting('theme', 'dark')}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  border: '1px solid var(--color-border)',
                  background: settings.theme === 'dark' ? 'var(--color-surface-lighter)' : 'transparent',
                  color: settings.theme === 'dark' ? 'var(--color-accent)' : 'var(--color-text-muted)',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                다크 모드 (Dark Mode)
              </button>
              <button
                type="button"
                onClick={() => updateSetting('theme', 'light')}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  border: '1px solid var(--color-border)',
                  background: settings.theme === 'light' ? 'var(--color-surface-lighter)' : 'transparent',
                  color: settings.theme === 'light' ? 'var(--color-accent)' : 'var(--color-text-muted)',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                라이트 모드 (Light Mode)
              </button>
            </div>
          </div>

          {/* 2. Exchange Rate Selector (실시간 환율 적용 vs 기준환율 수동설정) */}
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', alignItems: 'start', paddingBottom: '1.2rem', borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>기준 환율 공식 설정</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>통계 수치 연산에 적용할 환율 연동 방식입니다.</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', width: '100%' }}>
              <div style={{ display: 'flex', gap: '0.8rem' }}>
                <button
                  type="button"
                  onClick={() => updateSetting('exchangeRateMode', 'realtime')}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    border: settings.exchangeRateMode === 'realtime' ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                    background: settings.exchangeRateMode === 'realtime' ? 'var(--color-accent)' : 'var(--color-surface-lighter)',
                    color: settings.exchangeRateMode === 'realtime' ? '#fff' : 'var(--color-text-muted)',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: settings.exchangeRateMode === 'realtime' ? '0 2px 6px rgba(9, 132, 227, 0.2)' : 'none',
                  }}
                >
                  실시간 환율 적용 (Real-time)
                </button>
                <button
                  type="button"
                  onClick={() => updateSetting('exchangeRateMode', 'manual')}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    border: settings.exchangeRateMode === 'manual' ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                    background: settings.exchangeRateMode === 'manual' ? 'var(--color-accent)' : 'var(--color-surface-lighter)',
                    color: settings.exchangeRateMode === 'manual' ? '#fff' : 'var(--color-text-muted)',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: settings.exchangeRateMode === 'manual' ? '0 2px 6px rgba(9, 132, 227, 0.2)' : 'none',
                  }}
                >
                  기준환율 수동 설정 (Manual)
                </button>
              </div>

              {/* 수동 설정 옵션 선택 시에만 우아하게 노출되는 초콤팩트 슬라이더 */}
              {settings.exchangeRateMode === 'manual' && (
                <div 
                  className="compact-slider-panel"
                  style={{ 
                    marginTop: '0.5rem', 
                    padding: '0.5rem 0.8rem', 
                    background: 'var(--color-surface-lighter)', 
                    borderRadius: '6px', 
                    border: '1px solid var(--color-border)',
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.6rem',
                    maxWidth: '300px', // 극도로 콤팩트화
                    width: '100%',
                    boxSizing: 'border-box',
                    animation: 'fadeIn 0.2s ease'
                  }}
                >
                  <button
                    type="button"
                    onClick={() => updateSetting('exchangeRate', Math.max(1300, settings.exchangeRate - 5))}
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '4px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      fontWeight: 'bold',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      userSelect: 'none',
                      transition: 'all 0.1s ease'
                    }}
                  >
                    -
                  </button>
                  <input
                    type="range"
                    min="1300"
                    max="1500"
                    step="5"
                    value={settings.exchangeRate}
                    onChange={e => updateSetting('exchangeRate', Number(e.target.value))}
                    className="compact-slider"
                    style={{ 
                      flex: 1, 
                      cursor: 'pointer', 
                      height: '4px',
                      borderRadius: '2px',
                      minWidth: '80px',
                      maxWidth: '120px'
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => updateSetting('exchangeRate', Math.min(1500, settings.exchangeRate + 5))}
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '4px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text)',
                      fontWeight: 'bold',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      userSelect: 'none',
                      transition: 'all 0.1s ease'
                    }}
                  >
                    +
                  </button>
                  <strong style={{ fontSize: '0.85rem', color: 'var(--color-accent)', fontFamily: 'monospace', minWidth: '55px', textAlign: 'right' }}>
                    {settings.exchangeRate}원
                  </strong>
                </div>
              )}
            </div>
          </div>

          {/* 3. Refresh Interval */}
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', alignItems: 'center', paddingBottom: '1.2rem', borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>자동 동기화 주기</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>백엔드 통계 데이터의 자동 갱신 빈도를 정합니다.</span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {[30, 60, 300, 600, 1800].map(sec => {
                const isSelected = settings.refreshInterval === sec
                return (
                  <button
                    key={sec}
                    type="button"
                    onClick={() => updateSetting('refreshInterval', sec)}
                    style={{
                      padding: '0.4rem 0.8rem',
                      borderRadius: '6px',
                      border: isSelected ? '1px solid var(--color-accent)' : '1px solid var(--color-border)',
                      background: isSelected ? 'var(--color-accent)' : 'var(--color-surface-lighter)',
                      color: isSelected ? '#fff' : 'var(--color-text-muted)',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      boxShadow: isSelected ? '0 2px 6px rgba(9, 132, 227, 0.2)' : 'none',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {sec >= 60 ? `${sec / 60}분` : `${sec}초`}
                  </button>
                )
              })}
            </div>
          </div>

          {/* 4. Password Update Form (비밀번호 변경 및 보안 2차 검증) */}
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', alignItems: 'start', paddingBottom: '1.2rem', borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>비밀번호 변경</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>이전 비밀번호와 새 비밀번호 교차 검증을 수행합니다.</span>
            </div>
            <form onSubmit={handlePasswordUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxWidth: '300px', width: '100%' }}>
              <input
                type="password"
                placeholder="이전 비밀번호"
                value={currentPasswordInput}
                onChange={e => setCurrentPasswordInput(e.target.value)}
                className="settings-password-input"
              />
              <input
                type="password"
                placeholder="새 비밀번호"
                value={newPasswordInput}
                onChange={e => setNewPasswordInput(e.target.value)}
                className="settings-password-input"
              />
              <input
                type="password"
                placeholder="새 비밀번호 확인"
                value={confirmPasswordInput}
                onChange={e => setConfirmPasswordInput(e.target.value)}
                className="settings-password-input"
              />
              {pwError && (
                <span style={{ color: 'var(--color-danger)', fontSize: '0.75rem', fontWeight: 600 }}>
                  {pwError}
                </span>
              )}
              {pwSuccess && (
                <span style={{ color: 'var(--color-ok)', fontSize: '0.75rem', fontWeight: 600 }}>
                  {pwSuccess}
                </span>
              )}
              <button
                type="submit"
                style={{
                  padding: '0.5rem',
                  borderRadius: '6px',
                  border: 'none',
                  background: 'var(--color-accent)',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  boxShadow: '0 2px 6px rgba(9, 132, 227, 0.2)',
                  transition: 'all 0.15s ease',
                  marginTop: '0.2rem'
                }}
              >
                비밀번호 업데이트
              </button>
            </form>
          </div>

          {/* 5. Nickname */}
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', alignItems: 'center', paddingBottom: '1.2rem', borderBottom: '1px solid var(--color-border)' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>호칭 및 닉네임 설정</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>탑바 및 메시지 패널에 반영될 개인 호칭입니다.</span>
            </div>
            <input
              type="text"
              value={settings.nickname}
              onChange={e => updateSetting('nickname', e.target.value)}
              style={{
                maxWidth: '300px',
                width: '100%',
                padding: '0.6rem',
                borderRadius: '6px',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface-lighter)',
                color: 'var(--color-text)',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          {/* 6. Welcome Message */}
          <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', alignItems: 'start', paddingBottom: '1.2rem' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>상단 퍼스널 웰컴 문구</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>로그인 완료 시 대시보드 첫머리에 표기되는 지시선 문장입니다.</span>
            </div>
            <textarea
              value={settings.welcomeMessage}
              onChange={e => updateSetting('welcomeMessage', e.target.value)}
              rows={3}
              style={{
                width: '100%',
                padding: '0.6rem',
                borderRadius: '6px',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface-lighter)',
                color: 'var(--color-text)',
                fontSize: '0.9rem',
                outline: 'none',
                resize: 'vertical',
              }}
            />
          </div>
        </div>

        <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', justifyContent: 'flex-end', borderTop: '1px solid var(--color-border)', paddingTop: '1.5rem' }}>
          <button
            onClick={handleReset}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: '1px solid var(--color-border)',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            기본값 초기화
          </button>
        </div>
      </section>
    </div>
  )
}
export type { Settings }
