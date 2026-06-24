import { VP_TRAINING, vpGet, vpPost } from './api'
import type { Session } from './session'

/** 케이스 선택 화면이 쓰는 케이스 요약. (백엔드 /cases 응답) */
export type TrainingCase = {
  case_id: number
  status: string
  updated_at: string
  progress_pct: number
  case_label: string
  has_training_state: boolean
  flow_outline?: Array<Record<string, unknown>>
}

type AccountResponse = {
  ok: boolean
  customer_id: number
  email: string
  name?: string
  training_auth_token: string
}

export async function loginAccount(email: string, password: string): Promise<Session> {
  const r = await vpPost<AccountResponse>(VP_TRAINING.accountLogin, { email, password })
  return {
    customerId: r.customer_id,
    email: r.email,
    name: r.name ?? '',
    token: r.training_auth_token,
  }
}

export async function registerAccount(
  name: string,
  email: string,
  password: string,
): Promise<Session> {
  const r = await vpPost<AccountResponse>(VP_TRAINING.accountRegister, { name, email, password })
  // register 응답엔 name 이 없으므로 입력값을 사용한다.
  return {
    customerId: r.customer_id,
    email: r.email,
    name: name || r.name || '',
    token: r.training_auth_token,
  }
}

export async function listCases(email: string): Promise<TrainingCase[]> {
  const r = await vpGet<{ ok: boolean; cases: TrainingCase[] }>(VP_TRAINING.cases, { email })
  return r.cases ?? []
}

/** 새 훈련 케이스 시작(intake force_new). 인테이크 상세값은 추후 화면에서 수집. */
export async function startNewCase(email: string, name: string): Promise<void> {
  await vpPost(VP_TRAINING.intake, {
    email,
    name,
    preferred_llm: 'claude',
    current_device: 'iphone',
    desktop_os: 'mac',
    ai_experience: 'beginner',
    biggest_friction: '',
    learning_goal: '',
    force_new: true,
  })
}
