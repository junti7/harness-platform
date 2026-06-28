import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '@/lib/api'
import { clearSession, loadSession, saveSession, type Session } from '@/lib/session'
import {
  deleteCase,
  listCases,
  loginAccount,
  registerAccount,
  startNewCase,
  type TrainingCase,
} from '@/lib/vpTraining'
import AuthScreen from '@/components/AuthScreen'
import CaseSelectScreen from '@/components/CaseSelectScreen'
import TrainingScreen from '@/components/TrainingScreen'
import CurriculumScreen from '@/components/CurriculumScreen'
import FontSizeScreen from '@/components/FontSizeScreen'
import { applyFontScale, loadFontScale } from '@/lib/fontSettings'

/*
 * 컨테이너 골격. 화면(AuthScreen/CaseSelectScreen/TrainingScreen)은 v0 출력으로 교체되며,
 * 로그인 세션 · 라우팅 · api 배선 · 에러 처리는 이 파일이 담당한다.
 */

type View = 'auth' | 'cases' | 'training' | 'curriculum' | 'fontSize'

function errMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403) return '인증에 실패했습니다. 다시 확인해주세요.'
    return e.message || '요청 처리 중 문제가 발생했습니다.'
  }
  return '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
}

function App() {
  // 저장된 세션은 lazy initializer 로 복원한다(effect 내 setState 회피).
  const [session, setSession] = useState<Session | null>(() => loadSession())
  const [view, setView] = useState<View>(() => (session ? 'cases' : 'auth'))
  const [cases, setCases] = useState<TrainingCase[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [casesError, setCasesError] = useState<string | null>(null)
  const [authLoading, setAuthLoading] = useState(false)
  // 세션 복원 시 곧바로 케이스를 fetch 하므로 초기값을 그에 맞춘다.
  const [casesLoading, setCasesLoading] = useState<boolean>(() => session !== null)

  useEffect(() => {
    applyFontScale(loadFontScale())
  }, [])

  // setState 는 await 이후(비동기)에만 발생 → effect 경로에서 호출해도 안전.
  // 로딩 true 는 이 함수를 호출하는 이벤트 핸들러/initializer 에서 설정한다.
  const refreshCases = useCallback(async (email: string) => {
    try {
      setCasesError(null)
      setCases(await listCases(email))
    } catch (e) {
      console.error('listCases failed', e)
      setCases([])
      setCasesError(errMessage(e))
    } finally {
      setCasesLoading(false)
    }
  }, [])

  // 세션이 생기거나(로그인) 마운트 시 케이스를 불러온다. 단일 fetch 출처.
  // setState 는 중첩 async 안에서만 일어나므로 effect 동기 본문을 오염시키지 않는다.
  useEffect(() => {
    if (!session) return
    void (async () => {
      await refreshCases(session.email)
    })()
  }, [session, refreshCases])

  const enterSession = useCallback((next: Session) => {
    saveSession(next)
    setCasesLoading(true) // 이벤트 핸들러에서 설정(effect 가 곧 fetch).
    setSession(next)
    setView('cases')
  }, [])

  const handleLogin = useCallback(
    async ({ email, password }: { email: string; password: string }) => {
      setAuthLoading(true)
      setAuthError(null)
      try {
        await enterSession(await loginAccount(email, password))
      } catch (e) {
        setAuthError(errMessage(e))
      } finally {
        setAuthLoading(false)
      }
    },
    [enterSession],
  )

  const handleRegister = useCallback(
    async ({ name, email, password }: { name: string; email: string; password: string }) => {
      setAuthLoading(true)
      setAuthError(null)
      try {
        await enterSession(await registerAccount(name, email, password))
      } catch (e) {
        setAuthError(errMessage(e))
      } finally {
        setAuthLoading(false)
      }
    },
    [enterSession],
  )

  const handleNew = useCallback(async () => {
    if (!session) return
    setCasesLoading(true)
    try {
      const newCaseId = await startNewCase(session.email, session.name)
      await refreshCases(session.email)
      if (newCaseId != null) {
        setSelectedCaseId(newCaseId)
        setView('training')
      }
    } catch (e) {
      console.error('startNewCase failed', e)
      setCasesLoading(false)
    }
  }, [session, refreshCases])

  const handleSelect = useCallback((caseId: number) => {
    setSelectedCaseId(caseId)
    setView('training')
  }, [])

  const handleDelete = useCallback(
    async (caseId: number) => {
      if (!session) return
      const previousCases = cases
      setCases((prev) => prev.filter((c) => c.case_id !== caseId))
      try {
        await deleteCase(session.email, caseId)
      } catch (e) {
        setCases(previousCases)
        throw e
      } finally {
        await refreshCases(session.email)
      }
    },
    [session, cases, refreshCases],
  )

  const handleLogout = useCallback(() => {
    clearSession()
    setSession(null)
    setCases([])
    setCasesError(null)
    setSelectedCaseId(null)
    setView('auth')
  }, [])

  if (view === 'auth' || !session) {
    return (
      <AuthScreen
        onLogin={handleLogin}
        onRegister={handleRegister}
        loading={authLoading}
        error={authError}
      />
    )
  }

  if (view === 'training' && selectedCaseId != null) {
    return (
      <TrainingScreen
        caseId={selectedCaseId}
        email={session.email}
        onBack={() => setView('cases')}
      />
    )
  }

  if (view === 'curriculum') {
    return <CurriculumScreen email={session.email} onBack={() => setView('cases')} />
  }

  if (view === 'fontSize') {
    return <FontSizeScreen onBack={() => setView('cases')} />
  }

  return (
    <CaseSelectScreen
      userName={session.name}
      cases={cases}
      loading={casesLoading}
      error={casesError}
      onSelect={handleSelect}
      onNew={handleNew}
      onLogout={handleLogout}
      onDelete={handleDelete}
      onOpenCurriculum={() => setView('curriculum')}
      onOpenFontSize={() => setView('fontSize')}
    />
  )
}

export default App
