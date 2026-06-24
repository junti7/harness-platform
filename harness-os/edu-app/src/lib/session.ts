import { setTrainingAuthToken } from './api'

/** 로그인 세션. vp-training 계정 식별 + X-Edu-Training-Auth 토큰. */
export type Session = {
  customerId: number
  email: string
  name: string
  token: string
}

const KEY = 'vp_training_session'

/** 저장된 세션을 읽고, api 클라이언트의 훈련 토큰도 함께 복원한다. */
export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<Session>
    if (!parsed?.email || !parsed?.token) {
      localStorage.removeItem(KEY)
      return null
    }
    const session: Session = {
      customerId: Number(parsed.customerId ?? 0),
      email: String(parsed.email),
      name: String(parsed.name ?? ''),
      token: String(parsed.token),
    }
    setTrainingAuthToken(session.token)
    return session
  } catch {
    localStorage.removeItem(KEY)
    setTrainingAuthToken(null)
    return null
  }
}

export function saveSession(session: Session): void {
  localStorage.setItem(KEY, JSON.stringify(session))
  setTrainingAuthToken(session.token)
}

export function clearSession(): void {
  localStorage.removeItem(KEY)
  setTrainingAuthToken(null)
}
