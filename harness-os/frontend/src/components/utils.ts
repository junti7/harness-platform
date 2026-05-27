export function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`
}

export function formatUsd(value: number) {
  return `$${value.toFixed(1)}`
}

export function formatKrw(value?: number) {
  if (!value) return '₩0'
  return `₩${value.toLocaleString('ko-KR')}`
}

export function formatUsdAndKrw(usdValue: number, exchangeRate: number = 1400) {
  const krwValue = Math.round(usdValue * exchangeRate)
  return `$${usdValue.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} (₩${krwValue.toLocaleString('ko-KR')})`
}

export function formatUsdAndKrwDetailed(usdValue: number, exchangeRate: number = 1400) {
  const krwValue = Math.round(usdValue * exchangeRate)
  return `$${usdValue.toFixed(1)} (₩${krwValue.toLocaleString('ko-KR')})`
}

export function platformLabel(value: string) {
  const normalized = value.trim().toLowerCase()
  if (normalized === 'all') return 'All'
  if (normalized === 'substack') return 'Substack'
  if (normalized === 'maily') return 'Maily'
  return value
}

export function boolLabel(value: boolean | null | undefined) {
  if (value === true) return 'yes'
  if (value === false) return 'no'
  return 'unknown'
}

export function formatMaybeNumber(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return 'n/a'
  if (typeof value === 'number') return value.toLocaleString('en-US')
  const numeric = Number(value)
  if (!Number.isNaN(numeric) && value.trim() !== '') return numeric.toLocaleString('en-US')
  return value
}

export function freshnessLabel(value?: string) {
  if (value === 'fresh') return 'Fresh'
  if (value === 'aging') return 'Aging'
  if (value === 'stale') return 'Stale'
  return 'Unknown'
}

export function parseDueDate(value: string): Date | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const ymd = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (ymd) {
    const date = new Date(Number(ymd[1]), Number(ymd[2]) - 1, Number(ymd[3]))
    return Number.isNaN(date.getTime()) ? null : date
  }
  const md = trimmed.match(/^(\d{2})-(\d{2})$/)
  if (md) {
    const now = new Date()
    const date = new Date(now.getFullYear(), Number(md[1]) - 1, Number(md[2]))
    return Number.isNaN(date.getTime()) ? null : date
  }
  return null
}

export function formatDueDateWithCountdown(value: string): string {
  const due = parseDueDate(value)
  if (!due) return value
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate())
  const diff = Math.round((dueDay.getTime() - today.getTime()) / 86_400_000)
  const mm = String(dueDay.getMonth() + 1).padStart(2, '0')
  const dd = String(dueDay.getDate()).padStart(2, '0')
  if (diff > 0) return `${mm}-${dd}(D-${diff}일)`
  if (diff === 0) return `${mm}-${dd}(D-day)`
  return `${mm}-${dd}(D+${Math.abs(diff)}일)`
}

const PERSONA_BASE_MAP: Record<string, string> = {
  tars: 'TARS', 타르: 'TARS', friday: 'Friday', 금요일: 'Friday', 프라이데이: 'Friday',
  kitt: 'KITT', 키트: 'KITT', jarvis: 'Jarvis', 자비스: 'Jarvis', ledger: 'Ledger',
  비전: 'Vision', vision: 'Vision', c3po: 'C3PO', coach: 'Coach', watchman: 'Watchman', scribe: 'Scribe',
}
const PERSONA_TEAM_MAP: Record<string, string> = {
  TARS: '엔지니어링팀', Friday: '사업운영팀', KITT: '법무팀', Jarvis: '비서실장',
  Ledger: '재무팀', Vision: '상품기획팀', C3PO: '마케팅팀', Coach: '인사팀',
  Watchman: '리스크팀', Scribe: 'QA팀',
}

export function normalizePersonaLabel(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return value
  const matched = trimmed.match(/^(.+?)\s*\((.+)\)$/)
  const rawBase = (matched?.[1] ?? trimmed).trim()
  const normalizedBase = PERSONA_BASE_MAP[rawBase.toLowerCase()] ?? rawBase
  const resolvedTeam = PERSONA_TEAM_MAP[normalizedBase] ?? matched?.[2]?.trim() ?? ''
  if (!resolvedTeam) return normalizedBase
  return `${normalizedBase}(${resolvedTeam})`
}
