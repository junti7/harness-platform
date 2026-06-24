/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 백엔드 API base. 비우면 same-origin(프록시) 사용. 예: https://harness.example */
  readonly VITE_HARNESS_OS_API_BASE?: string
  /** secret 티어(vp-training) 호출용 X-Harness-Secret. pilot 전용. App #3(public)에서는 불필요. */
  readonly VITE_HARNESS_SECRET?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
