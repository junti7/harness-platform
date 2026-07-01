/*
 * VP 훈련 API 클라이언트 (data layer).
 *
 * 경계(중요): 이 앱은 secret 티어의 `/api/edu/vp-training/*` 만 호출한다.
 *  - 내부 콘솔 API(/api/dashboard, /api/approvals, /api/trading 등) 호출 금지.
 *  - 대외 public 티어(/api/public/edu/*)는 App #3 에서 사용한다(여기서 쓰지 않는다).
 *
 * vp-training 엔드포인트는 모두 X-Harness-Secret 을 요구한다(_require_secret).
 * 따라서 pilot 앱은 접근 제어 전제이며 완전 공개 URL 로 노출하지 않는다(README 참조).
 *
 * 요청/응답 payload 의 정확한 형태는 기존 화면
 *   harness-os/frontend/src/pages/EduVpTrainingPage.tsx 가 단일 출처다.
 * v0 로 새 화면을 만들 때 그 로직을 이 클라이언트 위로 이식한다.
 */

const API_BASE = import.meta.env.VITE_HARNESS_OS_API_BASE ?? ''
const SECRET = import.meta.env.VITE_HARNESS_SECRET ?? ''
const REQUEST_TIMEOUT_MS = 16_000

export const VP_TRAINING = {
  accountRegister: '/api/edu/vp-training/account/register',
  accountLogin: '/api/edu/vp-training/account/login',
  accountUpdateEmail: '/api/edu/vp-training/account/update-email',
  cases: '/api/edu/vp-training/cases',
  casesDelete: '/api/edu/vp-training/cases/delete',
  casesReset: '/api/edu/vp-training/cases/reset',
  session: '/api/edu/vp-training/session',
  sessionSync: '/api/edu/vp-training/session/sync',
  intake: '/api/edu/vp-training/intake',
  artifact: '/api/edu/vp-training/artifact',
  curriculum: '/api/edu/vp-training/curriculum',
  feedback: '/api/edu/vp-training/feedback',
  safetyRoute: '/api/edu/vp-training/safety-route',
  safetyCoach: '/api/edu/vp-training/safety-coach',
  safetyCoachFeedback: '/api/edu/vp-training/safety-coach/feedback',
  materials: (kitId: string) => `/api/edu/vp-training/materials/${encodeURIComponent(kitId)}`,
} as const

// 로그인 세션의 훈련 토큰. 백엔드는 X-Edu-Training-Auth 헤더로 검증한다.
// 세션 storage(session.ts)가 로그인/로그아웃 시 이 값을 동기화한다.
let currentTrainingToken: string | null = null

export function setTrainingAuthToken(token: string | null): void {
  currentTrainingToken = token && token.trim() ? token.trim() : null
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  if (SECRET) headers['X-Harness-Secret'] = SECRET
  if (currentTrainingToken) headers['X-Edu-Training-Auth'] = currentTrainingToken
  return headers
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(input, { ...init, signal: controller.signal })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ApiError(408, '요청 시간이 초과되었습니다. 다시 시도해주세요.')
    }
    throw e
  } finally {
    window.clearTimeout(timeout)
  }
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const detail =
      (data && typeof data === 'object' && 'detail' in data && String(data.detail)) ||
      res.statusText
    throw new ApiError(res.status, detail)
  }
  return data as T
}

/** GET 헬퍼. query 는 자동 직렬화된다. */
export async function vpGet<T = unknown>(
  path: string,
  query: Record<string, string | number | undefined> = {},
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined) qs.set(k, String(v))
  }
  const url = `${API_BASE}${path}${qs.toString() ? `?${qs}` : ''}`
  const res = await fetchWithTimeout(url, { headers: authHeaders() }, timeoutMs)
  return parse<T>(res)
}

/** POST(JSON) 헬퍼. */
export async function vpPost<T = unknown>(path: string, body: unknown = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const res = await fetchWithTimeout(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  }, timeoutMs)
  return parse<T>(res)
}

export const isSecretConfigured = () => Boolean(SECRET)
